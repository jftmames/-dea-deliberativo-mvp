# /src/session_manager.py
# --- CÓDIGO COMPLETO Y DEFINITIVO ---

import streamlit as st
import uuid
import datetime
from typing import Optional, Dict, Any

# Se importa solo para type hinting, no crea dependencia circular.
from inquiry_engine import InquiryEngine

def initialize_global_state():
    """Inicializa el estado global de la sesión si no existe."""
    if 'scenarios' not in st.session_state:
        st.session_state.scenarios = {}
        st.session_state.active_scenario_id = None
        st.session_state.global_df = None
        st.session_state.inquiry_engine = InquiryEngine()
        st.session_state.epistemic_events = []

def log_epistemic_event(event_type: str, data: Dict[str, Any]):
    """Registra un evento deliberativo en el log de la sesión."""
    event = {
        "timestamp": datetime.datetime.now().isoformat(),
        "event_type": event_type,
        "data": data
    }
    if 'epistemic_events' in st.session_state:
        st.session_state.epistemic_events.append(event)

def get_active_scenario() -> Optional[Dict[str, Any]]:
    """Devuelve el diccionario del escenario actualmente activo."""
    active_id = st.session_state.get('active_scenario_id')
    if active_id and active_id in st.session_state.scenarios:
        return st.session_state.scenarios[active_id]
    return None

def create_new_scenario(name: str = "Modelo Base", source_scenario_id: str = None):
    """Crea un nuevo escenario, ya sea en blanco o clonando uno existente."""
    new_id = str(uuid.uuid4())
    
    if source_scenario_id and source_scenario_id in st.session_state.scenarios:
        import copy
        source_scenario = st.session_state.scenarios[source_scenario_id]
        new_scenario = copy.deepcopy(source_scenario)
        new_scenario['name'] = f"Copia de {source_scenario['name']}"
        new_scenario['dea_results'] = None
        new_scenario['inquiry_tree_node'] = None
        new_scenario['user_justifications'] = {}
        st.session_state.scenarios[new_id] = new_scenario
    else:
        st.session_state.scenarios[new_id] = {
            "name": name, "df": st.session_state.get("global_df"),
            "app_status": "data_loaded", # Estado inicial correcto
            "proposals_data": None, "selected_proposal": None, "dea_config": {},
            "dea_results": None, "inquiry_tree_node": None, "tree_explanation": None,
            "user_justifications": {}, "data_overview": {}
        }
    st.session_state.active_scenario_id = new_id

def reset_all():
    """Reinicia la aplicación a su estado inicial."""
    st.cache_data.clear()
    st.cache_resource.clear()
    for key in list(st.session_state.keys()):
        del st.session_state[key]
