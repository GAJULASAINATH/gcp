from app.core.state import AgentState

def decision_node(state: AgentState):
    """
    Traffic Cop Logic:
    Checks the 'filters' state to decide what to do next.
    """
    filters = state.get("filters")
    inv_status = state.get("inventory_check_status")

    props = state.get("found_properties")
    shown = state.get("shown_count", 0)

    if inv_status == "PENDING":
        return {"next_step": "check_inventory"}

    if props and shown < len(props):
        last_msg = state["messages"][-1].content.lower()
        positive_keywords = ["yes", "show", "more", "next", "okay", "sure", "go ahead", "yup","yeah","yea","please"]
        
        # If user says "Yes/More", go to display node
        if any(w in last_msg for w in positive_keywords):
            return {"next_step": "display_results"}
        
    # --- PRIORITY 1: CRITICAL SEARCH FIELDS ---
    if not filters.location_query:
        return {"next_step": "ask_location"}
    
    if not filters.budget_max:
        return {"next_step": "ask_budget"}
    
    if not filters.move_in_date:
        return {"next_step": "ask_date"}

    # --- PRIORITY 2: ESSENTIAL DEMOGRAPHICS ---
    if not filters.tenant_gender:
        return {"next_step": "ask_gender"}

    if not filters.tenant_nationality:
        return {"next_step": "ask_nationality"}

    # --- IF ALL FIELDS ARE PRESENT ---
    return {"next_step": "execute_search"}