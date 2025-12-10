from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from app.core.state import AgentState
from sqlalchemy import text

async def capability_check_node(state: AgentState, config: RunnableConfig):
    """
    Checks if the agent is authorized for the requested target_table.
    If rejected, provides a personalized list of available services.
    """
    db = config.get("configurable", {}).get("db_session")
    agent_id = state["agent_id"]
    target_table = state["target_table"]
    
    # 1. Map Table Names to DB Columns & Human Friendly Names
    # Key: Table Name (from Router)
    # Value: (DB Column Name, Readable Name)
    service_map = {
        "coliving_property": ("co_living_property", "Co-living Spaces"),
        "rooms_for_rent": ("rooms_for_rent", "Standard Rooms"),
        "residential_properties_for_rent": ("residential_property_rent", "Whole Unit Rentals"),
        "residential_properties_for_resale": ("residential_property_resale", "Residential Sales"),
        "residential_properties_for_sale_by_developers": ("residential_property_developer", "New Launch Residential"),
        "commercial_properties_for_rent": ("commercial_property_rent", "Commercial Rentals"),
        "commercial_properties_for_resale": ("commercial_property_resale", "Commercial Sales"),
        "commercial_properties_for_sale_by_developers": ("commercial_property_developer", "New Launch Commercial")
    }
    
    # Get target details
    target_info = service_map.get(target_table)
    
    if not target_info:
        # Fallback for unknown tables
        return {"next_step": "GENERAL"}

    target_column, target_human_name = target_info

    # 2. Query ALL capability columns for this agent at once
    # We construct the SELECT statement dynamically
    db_columns = [val[0] for val in service_map.values()]
    cols_sql = ", ".join(db_columns)
    
    query = text(f"SELECT {cols_sql} FROM agent WHERE agent_id = :aid")
    result = await db.execute(query, {"aid": agent_id})
    agent_row = result.mappings().first()
    
    if not agent_row:
        return {"next_step": "GENERAL"} 

    # 3. Check if the specific requested feature is enabled
    is_allowed = agent_row.get(target_column)
    
    if is_allowed:
        # Success! Proceed to extraction
        return {"next_step": "PROPERTY_SEARCH_APPROVED"}
    
    # 4. Failure Case: Generate Personalized Alternatives
    # Find what they CAN do
    available_services = []
    for table_key, (col_name, human_name) in service_map.items():
        if agent_row.get(col_name):
            available_services.append(human_name)
            
    if available_services:
        services_str = ", ".join(available_services)
        msg = (
            f"I apologize, but I currently don't handle **{target_human_name}**. "
            f"However, I specialize in: **{services_str}**. \n\n"
            "Would you like to explore one of these options instead?"
        )
    else:
        msg = "I apologize, but I am not currently configuring to handle property searches. Please contact our main office."

    return {
        "messages": [AIMessage(content=msg)],
        "next_step": "end"
    }