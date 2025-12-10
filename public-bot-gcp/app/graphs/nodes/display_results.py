from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from app.core.state import AgentState
import json

async def display_results_node(state: AgentState, config: RunnableConfig):
    """
    Formats and displays properties in batches of 3.
    Now includes Description, Room Number, and Image Link.
    """
    properties = state.get("found_properties") or []
    start_idx = state.get("shown_count", 0)
    batch_size = 3
    
    # Slice the list (e.g., index 0 to 3)
    current_batch = properties[start_idx : start_idx + batch_size]
    
    # --- CASE A: NO RESULTS AT ALL ---
    if not properties:
        # Safe access to filters
        filters = state.get('filters')
        loc = filters.location_query if filters else "your area"
        bud = filters.budget_max if filters else "your budget"
        
        msg = (
            f"I searched based on your criteria (Location: {loc}, "
            f"Budget: ${bud}), but I couldn't find any exact matches nearby.\n\n"
            "Would you like to try a different location or adjust your budget?"
        )
        return {
            "messages": [AIMessage(content=msg)],
            "next_step": "complete"
        }

    # --- CASE B: RAN OUT OF RESULTS ---
    if not current_batch:
        msg = "That's all the properties I have matching your current criteria! Would you like to arrange a viewing for any of the ones above?"
        return {
            "messages": [AIMessage(content=msg)],
            "next_step": "complete"
        }

    # --- CASE C: DISPLAY BATCH ---
    msg = ""
    if start_idx == 0:
        msg = f"Great news! I found {len(properties)} properties. Here are the top {len(current_batch)}:\n\n"
    else:
        msg = "Here are a few more options:\n\n"

    for p in current_batch:
        # 1. Extract Basic Info
        name = p.get('property_name') or "Coliving Unit"
        rent = p.get('monthly_rent') or "N/A"
        rtype = p.get('room_type') or "Room"
        mrt = p.get('nearest_mrt') or "nearby transport"
        room_no = p.get('room_number') or ""
        desc = p.get('description') or ""
        
        # 2. Parse Media (Get the first image)
        media_str = p.get('media')
        image_url = ""
        if media_str:
            try:
                # If it's a JSON string list '["url1", "url2"]'
                if isinstance(media_str, str) and media_str.startswith('['):
                    media_list = json.loads(media_str)
                    if media_list and isinstance(media_list, list):
                        image_url = media_list[0]
                # If it's just a string URL
                elif isinstance(media_str, str):
                    image_url = media_str
                # If it's already a list
                elif isinstance(media_str, list) and media_str:
                    image_url = media_str[0]
            except Exception:
                pass # Fallback to no image if parsing fails

        # 3. Format the Message Card
        msg += f"🏠 *{name}* {f'(Room {room_no})' if room_no else ''}\n"
        msg += f"💰 ${rent}/mo | 🛏 {rtype}\n"
        msg += f"📍 Near {mrt}\n"
        
        if desc:
            # Truncate description to ~100 chars to keep WhatsApp message clean
            short_desc = (desc[:100] + '...') if len(desc) > 100 else desc
            msg += f"📝 _{short_desc}_\n"
            
        if image_url:
            msg += f"🖼 {image_url}\n"
        
        msg += "\n" + "-"*20 + "\n" # Separator

    # Calculate counters for next turn
    new_count = start_idx + len(current_batch)
    remaining = len(properties) - new_count
    
    # Add the "Call to Action"
    if remaining > 0:
        msg += f"I have {remaining} more options. Should I show them?"
    else:
        msg += "That's all the matches! Would you like to arrange a viewing for any of these?"
    
    return {
        "messages": [AIMessage(content=msg)],
        "shown_count": new_count,
        "next_step": "waiting_for_user" 
    }