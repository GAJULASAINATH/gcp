from langchain_core.runnables import RunnableConfig
from app.core.state import AgentState
from app.tools.property_search import PropertySearchTool
from app.services.query_builder import build_property_query
from sqlalchemy import text
import logging
import re
import os
logger = logging.getLogger(__name__)

async def search_node(state: AgentState, config: RunnableConfig):
    """
    Hybrid Search Strategy:
    1. Try DB Text Search (Cleaned string).
    2. If 0 results, Geocode -> Radius Search.
    """
    db = config.get("configurable", {}).get("db_session")
    agent_id = state["agent_id"]
    filters = state["filters"]
    filter_dict = filters.model_dump() if filters else {}
    
    # ⚠️ REPLACE WITH YOUR REAL KEY
    tool = PropertySearchTool(db, location_iq_key=os.getenv("LOCATION_IQ_KEY"))
    
    properties = []
    location_str = filters.location_query
    
    # --- STRATEGY 1: DIRECT DB TEXT SEARCH ---
    if location_str:
        # CLEANUP: Remove noise words to increase DB match rate
        # e.g. "near admiralty mrt" -> "admiralty"
        # 1. Remove common prepositions
        clean_loc = location_str.lower()
        for word in ["near", "around", "at", "in", "area", "location"]:
            clean_loc = clean_loc.replace(word, "")
            
        # 2. Remove "mrt" or "station" (often not in DB column)
        clean_loc = clean_loc.replace("mrt", "").replace("station", "")
        
        # 3. Strip spaces
        clean_loc = clean_loc.strip()
        
        logger.info(f"🔍 Text Search: Original='{location_str}' -> Clean='{clean_loc}'")
        
        # Only run if we have a word left
        if len(clean_loc) > 2:
            query_text, params = build_property_query(
                filters=filter_dict, 
                agent_id=agent_id, 
                lat=None, 
                lng=None, 
                text_search_term=clean_loc # Pass the cleaned word
            )
            
            # Use Limit 10 for pagination buffer
            final_query_str = str(query_text).replace("LIMIT 5", "LIMIT 10")
            
            result = await db.execute(text(final_query_str), params)
            properties = [dict(row) for row in result.mappings().all()]
            
            if properties:
                logger.info(f"✅ Text Search found {len(properties)} matches.")

    # --- STRATEGY 2: FALLBACK TO GEOCODING ---
    # Only run if Text Search failed
    if not properties and location_str:
        logger.info(f"⚠️ Text Search failed. Trying Geocoding for: '{location_str}'")
        
        coords = await tool.get_coordinates(location_str)
        if coords:
            lat, lng = coords
            
            query_text, params = build_property_query(
                filters=filter_dict, 
                agent_id=agent_id, 
                lat=lat, 
                lng=lng
            )
            
            final_query_str = str(query_text).replace("LIMIT 5", "LIMIT 10")
            result = await db.execute(text(final_query_str), params)
            properties = [dict(row) for row in result.mappings().all()]
        else:
            logger.warning("❌ Geocoding also failed/returned None.")

    # Save to State
    return {
        "found_properties": properties, 
        "shown_count": 0, 
        "next_step": "display_results" 
    }