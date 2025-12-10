from langchain_core.runnables import RunnableConfig
from app.core.state import AgentState
import logging

logger = logging.getLogger(__name__)

async def clear_memory_node(state: AgentState, config: RunnableConfig):
    """
    Wipes the 'filters' from the state to start a fresh search.
    This is triggered when the user explicitly switches context 
    (e.g. from 'Rent Room' to 'Buy Commercial').
    """
    new_target = state.get("target_table")
    logger.info(f"🧹 [DEBUG] Clearing Search History. New Target: {new_target}")
    
    # We return 'filters': None to wipe the previous form data.
    # The 'target_table' was already updated by the Router before reaching here.
    return {
        "filters": None, 
        "next_step": "CHECK_CAPABILITY" # Proceed to verify if agent handles the new request
    }