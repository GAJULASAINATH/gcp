from app.core.state import AgentState
from app.services.openai_service import OpenAIService
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig
import json
import logging
import re

logger = logging.getLogger(__name__)

ROUTER_PROMPT = """
You are an Intelligent Intent Classifier for a Real Estate Bot.

### CONVERSATION HISTORY
{history}

### YOUR GOAL
Classify the user's latest message into one of the following intents.

### INTENTS

1. **"PROPERTY_SEARCH"**
   - User is STARTING a search (e.g., "I want a room", "Show me rentals").
   - User is CONTINUING a search (e.g., providing Budget, Location, Date, Gender).
   - User is PAGINATING (e.g., "Yes", "Next", "Show more").
   - **CRITICAL:** If user provides a short answer like "2000" or "Male" or "Bedok", assume it is for the search.

2. **"APPOINTMENT"**
   - User wants to book a viewing, schedule a visit, or check availability.
   - Keywords: "Book viewing", "Schedule visit", "When can I see it?", "Arrange viewing".
   - **Context:** If Bot asked "Want to book?" and User says "Yes", this is APPOINTMENT.

3. **"HUMAN_HANDOFF"**
   - User explicitly asks for a human agent or support.
   - Keywords: "Talk to agent", "Human please", "Support", "Call me".
   - **Context:** If Bot asked "Contact human?" and User says "Yes", this is HUMAN_HANDOFF.

4. **"SWITCH_SEARCH"**
   - User explicitly wants to CHANGE property type (e.g., "Actually, I want to buy instead", "Switch to commercial").

5. **"CLARIFICATION"**
   - User's request is ambiguous (e.g., "I want a room" -> Co-living vs Standard).
   - You must ask the user to clarify.

6. **"INTELLIGENT_CHAT"**
   - **Everything else goes here.**
   - General Chat: "Hi", "Thanks", "Who are you?".
   - Knowledge Base: "What are your fees?", "UEN?", "Policies?".
   - Property QA: "Does the first one have a gym?", "Is it near the airport?".

### OUTPUT JSON FORMAT
{{
  "intent": "PROPERTY_SEARCH" | "APPOINTMENT" | "HUMAN_HANDOFF" | "SWITCH_SEARCH" | "CLARIFICATION" | "INTELLIGENT_CHAT",
  "target_table": "table_name" (Required if intent is PROPERTY_SEARCH or SWITCH_SEARCH),
  "clarification_question": "Question" (Required if intent is CLARIFICATION)
}}

### AVAILABLE TABLES
- coliving_property
- rooms_for_rent
- residential_properties_for_rent
- residential_properties_for_resale
- residential_properties_for_sale_by_developers
- commercial_properties_for_rent
- commercial_properties_for_resale
- commercial_properties_for_sale_by_developers
"""

async def router_node(state: AgentState, config: RunnableConfig):
    messages = state["messages"]
    last_message_content = messages[-1].content.strip()
    msg_lower = last_message_content.lower()
    llm = OpenAIService().client

    # --- 1. CONTEXT & KEYWORD OVERRIDES ---
    
    # A. Check Active Flow (Lock user into Appointment flow until done/cancelled)
    active_flow = state.get("active_flow")
    if active_flow == "APPOINTMENT":
        # Allow exit keywords to break the lock
        if not any(w in msg_lower for w in ["stop", "cancel", "back", "exit","don't want"]):
            return {"next_step": "APPOINTMENT"}

    if active_flow == "HUMAN_HANDOFF":
        # If user says stop, break the flow
        if any(w in msg_lower for w in ["stop", "cancel", "nevermind"]):
            return {"active_flow": None, "next_step": "GENERAL"}
        # Otherwise, treat input as the "Reason" and send back to node
        return {"next_step": "HUMAN_HANDOFF"}

    # B. Pagination
    target_table = state.get("target_table")
    pagination_keywords = ["yes", "yeah", "yep", "sure", "show more", "next", "continue"]
    
    # Only treat "Yes" as pagination if we aren't in an appointment context
    # (If bot asked "Book viewing?", "Yes" should go to APPOINTMENT via AI logic)
    last_bot_msg = messages[-2].content.lower() if len(messages) > 1 else ""
    is_booking_question = "book" in last_bot_msg or "viewing" in last_bot_msg or "appointment" in last_bot_msg
    
    if target_table and any(w in msg_lower for w in pagination_keywords) and not is_booking_question:
        return {"next_step": "PROPERTY_SEARCH"}

    # C. Specific Room Reference (QA)
    room_pattern = r"\b(room\s+\d+|r\d+)\b"
    if re.search(room_pattern, msg_lower):
        logger.info("✅ Specific Room ID detected. Routing to INTELLIGENT_CHAT.")
        return {"next_step": "INTELLIGENT_CHAT"}

    # D. Booking / Appointment Keywords (CRITICAL MISSING PIECE)
    booking_keywords = ["book", "booking", "schedule", "arrange", "appointment", "viewing", "visit"]
    if any(w in msg_lower for w in booking_keywords):
        logger.info("✅ Booking keyword found. Routing to APPOINTMENT.")
        return {"next_step": "APPOINTMENT", "active_flow": "APPOINTMENT"}

    # E. Property Type Hard-Match (Happy Path)
    if any(k in msg_lower for k in ["co-living", "coliving", "room", "rooms"]):
        if any(x in msg_lower for x in ["standard", "traditional", "landlord", "owner"]):
            return {"next_step": "CHECK_CAPABILITY", "target_table": "rooms_for_rent"}
        
        if not target_table:
            logger.info("✅ Generic 'Room' request. Defaulting to 'coliving_property'.")
            return {"next_step": "CHECK_CAPABILITY", "target_table": "coliving_property"}

    # --- 2. BUILD HISTORY ---
    recent_messages = messages[-7:] 
    history_str = ""
    for msg in recent_messages:
        role = "User" if isinstance(msg, HumanMessage) else "Bot"
        history_str += f"{role}: {msg.content}\n"

    # --- 3. AI CLASSIFICATION ---
    try:
        response = await llm.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": ROUTER_PROMPT.format(history=history_str)},
                {"role": "user", "content": f"Classify: {last_message_content}"}
            ],
            response_format={"type": "json_object"},
            temperature=0 
        )
        
        data = json.loads(response.choices[0].message.content)
        intent = data.get("intent", "INTELLIGENT_CHAT")
        
        logger.info(f"🛤️ Router classified: {intent}")

        # HANDLE INTENTS
        
        if intent == "APPOINTMENT":
            return {"next_step": "APPOINTMENT", "active_flow": "APPOINTMENT"}
            
        if intent == "HUMAN_HANDOFF":
            return {"next_step": "HUMAN_HANDOFF"}

        if intent == "PROPERTY_SEARCH":
            new_table = data.get("target_table")
            
            # SAFEGUARD: If AI forgets table, keep old one
            if not new_table and target_table:
                return {"next_step": "PROPERTY_SEARCH"} 
            
            # SAFEGUARD: Prevent Implicit Switching
            if new_table and target_table and new_table != target_table:
                explicit_switch_keywords = ["buy", "rent", "commercial", "residential", "office", "shop", "store"]
                if not any(k in msg_lower for k in explicit_switch_keywords):
                    return {"next_step": "PROPERTY_SEARCH"} 
                
                return {"next_step": "RESET_MEMORY", "target_table": new_table}

            return {"next_step": "CHECK_CAPABILITY", "target_table": new_table or target_table}

        elif intent == "SWITCH_SEARCH":
             return {"next_step": "RESET_MEMORY", "target_table": data.get("target_table")}
            
        elif intent == "CLARIFICATION":
             return {
                "next_step": "ASK_CLARIFICATION", 
                "clarification_question": data.get("clarification_question")
             }
            
        else:
            return {"next_step": "INTELLIGENT_CHAT"}

    except Exception as e:
        logger.error(f"Router Error: {e}")
        return {"next_step": "INTELLIGENT_CHAT"}