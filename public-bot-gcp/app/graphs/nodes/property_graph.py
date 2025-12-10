from langgraph.graph import StateGraph, END
from app.core.state import AgentState
from app.graphs.nodes.extractor import extractor_node
from app.graphs.nodes.decision import decision_node
from app.graphs.nodes.generator import generator_node
from app.tools.property_search import PropertySearchTool
from app.services.query_builder import build_property_query
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig

# --- 1. WRAPPER FOR DECISION LOGIC ---
def decision_node(state: AgentState):
    """
    Wraps the pure Python logic to update the State.
    """
    return check_missing_fields(state)

# --- 2. WRAPPER FOR SEARCH TOOL ---
async def search_node(state: AgentState, config: RunnableConfig):
    """
    Executes the search and generates a summary message.
    """
    # Get DB Session from config
    db = config.get("configurable", {}).get("db_session")
    agent_id = state["agent_id"]
    filters = state["filters"]
    
    # Initialize Tool
    tool = PropertySearchTool(db, location_iq_key="pk.eeda1ccce3fecedc524d0fb6b83421ec")
    
    # 1. Geocode
    lat, lng = None, None
    if filters.location_query:
        coords = await tool.get_coordinates(filters.location_query)
        if coords:
            lat, lng = coords
            
    # 2. Build Query
    # Note: filters.dict() works for Pydantic v1. If using v2, use filters.model_dump()
    query, params = build_property_query(filters.model_dump(), agent_id, lat, lng)
    
    # 3. Execute
    result = await db.execute(query, params)
    properties = result.mappings().all()
    
    # 4. Generate Summary
    if not properties:
        msg = f"I searched in {filters.location_query} (Budget: ${filters.budget_max}) but didn't find any matches nearby."
    else:
        msg = f"Great news! I found {len(properties)} properties matching your criteria:\n\n"
        for p in properties:
            # Handle potential None values safely
            name = p.get('property_name') or "Coliving Unit"
            rent = p.get('monthly_rent') or "N/A"
            rtype = p.get('room_type') or "Room"
            mrt = p.get('nearest_mrt') or "nearby transport"
            
            msg += f"🏠 *{name}*\n"
            msg += f"💰 ${rent}/mo | 🛏 {rtype}\n"
            msg += f"📍 Near {mrt}\n\n"
        msg += "Would you like to arrange a viewing for any of these?"

    return {"messages": [AIMessage(content=msg)], "next_step": "complete"}

# --- 3. BUILD THE GRAPH ---
workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("extractor", extractor_node)
workflow.add_node("decision", decision_node)
workflow.add_node("generator", generator_node)
workflow.add_node("search_tool", search_node)

# Add Edges
workflow.set_entry_point("extractor")
workflow.add_edge("extractor", "decision")

def route_decision(state: AgentState):
    step = state.get("next_step")
    if step == "execute_search":
        return "search_tool"
    else:
        return "generator"

workflow.add_conditional_edges(
    "decision",
    route_decision,
    {
        "search_tool": "search_tool",
        "generator": "generator"
    }
)

workflow.add_edge("generator", END)
workflow.add_edge("search_tool", END)

# --- CRITICAL CHANGE FOR PERSISTENCE ---
# We do NOT compile globally anymore.
# We expose a function that accepts the checkpointer.
def get_graph(checkpointer):
    return workflow.compile(checkpointer=checkpointer)