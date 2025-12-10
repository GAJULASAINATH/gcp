from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from app.core.state import AgentState
from app.services.n8n_client import N8NClient
import logging

logger = logging.getLogger(__name__)

async def human_handoff_node(state: AgentState, config: RunnableConfig):
    """
    Manages Human Handoff.
    """
    handoff = state.get("handoff_data") or {}
    reason = handoff.get("reason")
    
    logger.info(f"🤝 Human Handoff Node. Reason found: {reason}")

    # --- STEP 1: ASK FOR REASON (If missing) ---
    if not reason:
        return {
            "messages": [AIMessage(content="I can certainly connect you with a human agent. To help them assist you better, could you briefly describe your question or issue?")],
            "active_flow": "HUMAN_HANDOFF", # Lock the flow
            "next_step": "HUMAN_HANDOFF"
        }

    # --- STEP 2: SEND TO N8N (If Reason exists) ---
    filters = state.get("filters")
    filter_dict = filters.model_dump() if filters else {}
    def get_f(k): return filter_dict.get(k, "-")
    
    appt = state.get("appointment_state") or {}
    prop = state.get("selected_property") or {}

    # Construct Payload (Your exact requested structure)
    payload = [{
        "agent_id": state["agent_id"],
        "clientmessage": reason,
        "clientname": state.get("user_name") or "Unknown",
        "clientphone": state["user_mobile"],
        "clientemail": appt.get("email") or "-",
        
        "clientgender": get_f("tenant_gender"),
        "clientnationality": get_f("tenant_nationality"),
        "clientPass": appt.get("pass_type") or "-",
        "clientprofession": "-", 
        "clientnoofpax": "1", 
        
        "propertyname": prop.get("property_name") or "-",
        "roomnumber": prop.get("room_number") or "-",
        "clientmoveindate": get_f("move_in_date"),
        "clientleaseperiod": str(appt.get("lease_months") or "-"),
        
        "chatsummary": f"User requested human help. Reason: {reason}"
    }]

    logger.info(f"📤 Sending Handoff to N8N: {payload}")
    
    n8n = N8NClient()
    # Call trigger_workflow (make sure n8n_client.py has this method restored!)
    response_text = await n8n.trigger_workflow("HUMAN_HANDOFF", payload)
    
    if not response_text:
        response_text = "I've forwarded your request to our team. Someone will contact you shortly via WhatsApp!"

    return {
        "messages": [AIMessage(content=response_text)],
        "active_flow": None, # Unlock flow
        "handoff_data": None, # Clear data
        "next_step": "END"
    }