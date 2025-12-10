from typing import TypedDict, Annotated, List, Optional, Dict, Any
from langgraph.graph.message import add_messages
from app.schemas.property_search import PropertySearchFilters

def replace_value(existing, new):
    if new is None:
        return existing
    return new

class AgentState(TypedDict):
    # 1. Chat History
    messages: Annotated[List, add_messages]
    
    # 2. The "Form" we are filling out
    filters: Optional[PropertySearchFilters]
    
    # 3. Context
    agent_id: str
    user_mobile: str
    user_name: str
    agent_name: str
    company_name: str
    agent_bio: str
    
    # 4. Internal Logic Flags
    next_step: Optional[str]
    target_table: Optional[str]
    clarification_question: Optional[str]
    
    # --- CRITICAL MISSING FIELD ---
    active_flow: Optional[str] # <--- ADD THIS ("APPOINTMENT", "SEARCH", etc.)

    # 5. Search Results
    found_properties: Optional[List[Dict[str, Any]]]
    shown_count: Optional[int]
    last_extraction_was_empty: Optional[bool]
    validation_error: Optional[str]

    # 6. Appointment Data
    selected_property: Optional[Dict[str, Any]] 
    appointment_state: Optional[Dict[str, Any]] 
    available_slots: Optional[str]

    handoff_data: Annotated[Optional[Dict[str, Any]], replace_value]
    inventory_check_status: Annotated[Optional[str], replace_value]