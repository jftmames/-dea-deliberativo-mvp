# jftmames/-dea-deliberativo-mvp/-dea-deliberativo-mvp-b44b8238c978ae0314af30717b9399634d28f8f9/src/main.py
import sys
import os
import pandas as pd
import streamlit as st

# --- 0) Ajuste del PYTHONPATH ---
script_dir = os.path.dirname(__file__)
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

# --- 1) Importaciones ---
from results import mostrar_resultados
from data_validator import validate as validate_data
from inquiry_engine import generate_inquiry, to_plotly_tree
from epistemic_metrics import compute_eee
from openai_helpers import explain_orientation

# --- 2) Configuración de la página ---
st.set_page_config(layout="wide", page_title="DEA Deliberativo con IA")

# --- 3) Funciones de inicialización y callbacks ---
def initialize_state():
    """Inicializa el estado de la sesión para un nuevo fichero."""
    for key in list(st.session_state.keys()):
        if not key.startswith('_'):
            del st.session_state[key]
    
    # Inicializa las claves necesarias para evitar KeyErrors
    st.session_state.app_status = "initial"
    st.session_state.df = None
    st.session_state.validation_results = None
    st.session_state.orientation_explanation = None
    st.session_state.dea_results = None
    st.session_state.inquiry_tree = None

def reset_analysis_state():
    """Resetea el estado cuando cambia la configuración del modelo."""
    st.session_state.app_status = "file_loaded"
    st.session_state.validation_results = None
    st.session_state.orientation_explanation = None
    st.session_state.dea_results = None
    st.session_state.inquiry_tree = None

if 'app_status' not in st.session_state:
    initialize_state()

@st.cache_data
def run_dea_analysis(_df, dmu_col, input_cols, output_cols):
    """Encapsula los cálculos DEA para ser cacheados."""
    return mostrar_resultados(_df.copy(), dmu_col, input_cols, output_cols)

@st.cache_data
def run_inquiry_engine(root_question, _context):
    """Encapsula la llamada al motor de indagación para ser cacheada."""
    return generate_inquiry(root_question, context=_context)

# --- 4) Flujo principal de la aplicación ---
st.title("💡 DEA Deliberativo con IA")
st.markdown("Una herramienta para analizar la eficiencia y razonar sobre sus causas con ayuda de Inteligencia Artificial.")

# --- ETAPA 1: Carga de datos ---
st.header("Paso 1: Carga tus Datos", divider="blue")
uploaded_file = st.file_uploader("Sube un fichero CSV con tus datos", type=["csv"])

if uploaded_file:
    # Si es un fichero nuevo, reseteamos todo el estado
    if st.session_state.get('_file_id') != uploaded_file.file_id:
        initialize_state()
        st.session_state._file_id = uploaded_file.file_id
        try:
            st.session_state.df = pd.read_csv(uploaded_file)
        except Exception:
            uploaded_file.seek(0)
            st.session_state.df = pd.read_csv(uploaded_file, sep=';')
        st.session_state.app_status = "file_loaded"
        st.rerun()

# El resto de la app solo se muestra si hay un DataFrame cargado
if st.session_state.app_status != "initial":
    df = st.session_state.df
    st.dataframe(df.head())

    # --- ETAPA 2: Configuración y Validación IA ---
    st.header("Paso 2: Configura y Valida tu Modelo", divider="blue")
    col_dmu, col_inputs, col_outputs, col_orientation = st.columns(4)
    with col_dmu:
        st.selectbox("Columna de DMU (ID único)", df.columns, key="dmu_col", on_change=reset_analysis_state)
    with col_inputs:
        st.multiselect("Columnas de Inputs", [c for c in df.columns if c != st.session_state.dmu_col], key="input_cols", on_change=reset_analysis_state)
    with col_outputs:
        st.multiselect("Columnas de Outputs", [c for c in df.columns if c not in [st.session_state.dmu_col] + st.session_state.input_cols], key="output_cols", on_change=reset_analysis_state)
    with col_orientation:
        st.radio("Orientación del Modelo", ["input", "output"], key="orientation", on_change=reset_analysis_state)
    
    if st.button("Validar Selección con IA", use_container_width=True):
        if not st.session_state.input_cols or not st.session_state.output_cols:
            st.error("Por favor, selecciona al menos un input y un output.")
        else:
            with st.spinner("Consultando al experto de IA..."):
                st.session_state.validation_results = validate_data(df, st.session_state.input_cols, st.session_state.output_cols)
                st.session_state.orientation_explanation = explain_orientation(st.session_state.input_cols, st.session_state.output_cols, st.session_state.orientation)
                st.session_state.app_status = "validated"

    # Se muestra la validación solo si existe en el estado
    if st.session_state.get("validation_results"):
        st.subheader("Análisis de la IA sobre tu Modelo", anchor=False)
        val_res = st.session_state.validation_results
        
        col1, col2 = st.columns(2)
        with col1:
            if st.session_state.get("orientation_explanation"):
                st.info(st.session_state.orientation_explanation.get('text', "Sin comentarios sobre la orientación."))
            
            if not val_res["formal_issues"] and val_res["llm"]["ready"]:
                st.success("✅ ¡Todo parece correcto para la IA! Puedes proceder al análisis.")
            if val_res["formal_issues"]:
                st.warning("⚠️ Problemas formales encontrados:", icon="📑")
                for issue in val_res["formal_issues"]: st.markdown(f"- {issue}")
        with col2:
            if val_res["llm"].get("issues"):
                st.warning("Sugerencias del experto IA:", icon="🤖")
                for issue in val_res["llm"]["issues"]: st.markdown(f"- {issue}")
                if val_res["llm"].get("suggested_fixes"):
                    st.markdown("**Posibles soluciones:**")
                    for fix in val_res["llm"]["suggested_fixes"]: st.markdown(f"- {fix}")

    # --- ETAPA 3: Ejecutar Análisis ---
    st.header("Paso 3: Ejecuta el Análisis DEA", divider="blue")
    validation_passed = st.session_state.get("validation_results") and not st.session_state.validation_results["formal_issues"]
    
    if st.button("Calcular Eficiencias", type="primary", use_container_width=True, disabled=not validation_passed):
        with st.spinner("Realizando análisis DEA..."):
            st.session_state.dea_results = run_dea_analysis(df, st.session_state.dmu_col, st.session_state.input_cols, st.session_state.output_cols)
            st.session_state.app_status = "results_ready"

    # Las etapas 4 y 5 solo se muestran si el análisis DEA se ha completado
    if st.session_state.get("dea_results"):
        # --- ETAPA 4: Razonamiento sobre Resultados ---
        st.header("Paso 4: Razona sobre la Ineficiencia con IA", divider="blue")
        st.markdown("Usa la IA para generar un árbol de hipótesis sobre las posibles causas de la ineficiencia detectada.")

        if st.button("Generar Hipótesis de Ineficiencia con IA", use_container_width=True):
            with st.spinner("La IA está razonando sobre los resultados..."):
                dea_results = st.session_state.dea_results
                avg_eff = dea_results["df_ccr"]["tec_efficiency_ccr"].mean()
                inefficient_count = (dea_results["df_ccr"]["tec_efficiency_ccr"] < 0.999).sum()
                
                context = {"inputs": st.session_state.input_cols, "outputs": st.session_state.output_cols, "avg_efficiency_ccr": avg_eff, "inefficient_units_count": int(inefficient_count), "total_units_count": len(df)}
                root_question = f"Considerando los inputs y outputs, ¿cuáles son las principales causas de la ineficiencia (eficiencia < 1.0) en {inefficient_count} de {len(df)} unidades?"
                
                tree, error = run_inquiry_engine(root_question, context)
                if error:
                    st.error(f"Error en el motor de indagación: {error}")
                st.session_state.inquiry_tree = tree
        
        if st.session_state.get("inquiry_tree"):
            col_tree, col_eee = st.columns([2, 1])
            with col_tree:
                st.subheader("Árbol de Indagación", anchor=False)
                st.plotly_chart(to_plotly_tree(st.session_state.inquiry_tree), use_container_width=True)
            with col_eee:
                st.subheader("Calidad del Razonamiento (EEE)", anchor=False)
                eee_metrics = compute_eee(st.session_state.inquiry_tree, depth_limit=3, breadth_limit=5)
                st.metric(label="Índice de Equilibrio Erotético (EEE)", value=f"{eee_metrics['score']:.2%}")
                st.caption("Mide la calidad y balance del árbol de preguntas generado por la IA.")
                
                with st.expander("Ver desglose del EEE"):
                    st.markdown(f"- **D1: Profundidad ({eee_metrics['D1']:.2f})**: ¿Cuán profundo es el razonamiento?")
                    st.markdown(f"- **D2: Pluralidad ({eee_metrics['D2']:.2f})**: ¿Cuántas hipótesis principales se exploran?")
                    st.markdown(f"- **D3: Trazabilidad ({eee_metrics['D3']:.2f})**: ¿Hay múltiples caminos de investigación?")
                    st.markdown(f"- **D4: Reversibilidad ({eee_metrics['D4']:.2f})**: Placeholder para futuras métricas.")
                    st.markdown(f"- **D5: Robustez ({eee_metrics['D5']:.2f})**: ¿Se pueden debatir las hipótesis?")

        # --- ETAPA 5: Resultados Detallados ---
        st.header("Paso 5: Explora los Resultados Detallados", divider="blue")
        tab_ccr, tab_bcc = st.tabs(["**Resultados CCR**", "**Resultados BCC**"])
        results = st.session_state.dea_results
        
        with tab_ccr:
            st.dataframe(results.get("df_ccr"))
            if results.get("hist_ccr"):
                col1, col2 = st.columns(2)
                with col1: st.plotly_chart(results["hist_ccr"], use_container_width=True)
                with col2: st.plotly_chart(results["scatter3d_ccr"], use_container_width=True)

        with tab_bcc:
            st.dataframe(results.get("df_bcc"))
            if results.get("hist_bcc"):
                st.plotly_chart(results["hist_bcc"], use_container_width=True)
