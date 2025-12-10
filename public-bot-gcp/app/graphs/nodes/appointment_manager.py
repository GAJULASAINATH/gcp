from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from app.core.state import AgentState
from app.services.n8n_client import N8NClient
from app.services.openai_service import OpenAIService
import json
import logging
import re

logger = logging.getLogger(__name__)

# Prompt for generating the summary
SUMMARY_PROMPT = """
You are a helpful assistant summarizing a real estate conversation for a human agent.
Generate a concise but detailed summary of the user's requirements and the booking context.

CONTEXT:
- User Name: {user_name}
- Property: {property_name}
- Viewing Type: {viewing_type}
- Extracted Filters: {filters}

CHAT HISTORY:
{history}

OUTPUT FORMAT:
Start with "User [Name] is looking for...". Include budget, location preferences, move-in date, and any specific questions they asked (e.g. cooking, visitors). Mention they have scheduled a {viewing_type} viewing.
"""

async def appointment_manager_node(state: AgentState, config: RunnableConfig):
    appt = state.get("appointment_state") or {}
    last_message = state["messages"][-1].content.strip()
    last_lower = last_message.lower()
    
    # --- 1. IDENTIFY PROPERTY ---
    found_props = state.get("found_properties") or []
    selected_prop_name = appt.get("property_reference")
    target_property = state.get("selected_property") 
    
    # Only try to identify if not already selected
    if not target_property:
        # CASE A: Only 1 result -> Auto-select
        if len(found_props) == 1:
            target_property = found_props[0]
            
        # CASE B: User gave input (e.g. "2nd one", "Melville")
        elif found_props:
            # Check if user input contains ordinal words
            index = -1
            if any(w in last_lower for w in ["1st", "first", "one"]): index = 0
            elif any(w in last_lower for w in ["2nd", "second", "two"]): index = 1
            elif any(w in last_lower for w in ["3rd", "third", "three"]): index = 2
            
            # Check if user input contains a digit (1, 2, 3) acting as an index
            if index == -1:
                # FIX: Use global re import, do not import inside function
                digits = re.findall(r"\b[1-3]\b", last_lower)
                if digits and len(last_lower) < 10: 
                    index = int(digits[0]) - 1

            # If index found, select property
            if index > -1 and index < len(found_props):
                target_property = found_props[index]
            
            # CASE C: Name Matching (Fuzzy)
            if not target_property:
                for p in found_props:
                    p_name = p.get("property_name", "").lower()
                    if p_name in last_lower or last_lower in p_name:
                        target_property = p
                        break
            
            # CASE D: Room Number Matching
            if not target_property:
                for p in found_props:
                    r_num = str(p.get("room_number", "")).lower()
                    if r_num and r_num in last_lower:
                        target_property = p
                        break

        # If still failed, ask user
        if not target_property:
            return {
                "messages": [AIMessage(content="Got it! Which place are you thinking about? You can tell me the name, the number, or even say something like 'the second one'.")],
                "next_step": "APPOINTMENT_LOOP"
            }
    
    # --- 2. COLLECT DETAILS ---
    
    # Define the state update (Always ensure property is saved)
    state_update = {"selected_property": target_property, "next_step": "APPOINTMENT_LOOP"}

    if not appt.get("email"):
        return {
            **state_update,
            "messages": [AIMessage(content=f"Awesome choice! 🎉 To lock in a viewing for **{target_property.get('property_name')}**, could you share your email with me?")]
        }

    if not appt.get("pass_type"):
        return {
            **state_update,
            "messages": [AIMessage(content="Perfect! And what type of pass do you hold? (EP, SP, Student Pass, PR, Citizen… anything works!)")]
        }

    if not appt.get("lease_months"):
        return {
            **state_update,
            "messages": [AIMessage(content="Got it! How long are you planning to stay? (We need at least a 3-month minimum.)")]
        }

    # --- 3. COLLECT PREFERENCES ---
    if not appt.get("viewing_type"):
        return {
            **state_update,
            "messages": [AIMessage(content="How would you like to view the place — a quick **Virtual tour**, or should we book an **In-Person** viewing?")]
        }

    time_pref = appt.get("time_preference")
    if not time_pref:
        return {
            **state_update,
            "messages": [AIMessage(content="Sweet! What time usually works best for you — **Morning**, **After Lunch**, or **After Work**?")]
        }

    # --- 4. FETCH & SHOW SLOTS ---
    if not state.get("available_slots"):
        logger.info("🔍 Fetching available slots from N8N...")
        n8n = N8NClient()
        slots_data = await n8n.get_available_slots(state["agent_id"], time_pref)
        
        if not slots_data:
            return {
                **state_update,
                "messages": [AIMessage(content="I couldn't find available slots for that time preference. Would you like to try a different time? (Morning, After Lunch, or After Work)")],
                "appointment_state": {**appt, "time_preference": None}
            }
        
        msg_lines = ["Here are the available slots:\n"]
        if isinstance(slots_data, dict): slots_data = [slots_data]
        if not isinstance(slots_data, list): slots_data = []

        display_slots = slots_data[:5]
        slot_lines = []
        
        for day_obj in display_slots:
            if not isinstance(day_obj, dict): continue
            date_str = day_obj.get("date", "")
            day_name = day_obj.get("day", "")
            slots = day_obj.get("slots", [])
            
            if slots:
                time_slots = ", ".join(slots)
                slot_lines.append(f"• *{day_name}* ({date_str}): {time_slots}")
        
        if not slot_lines:
             return {
                **state_update,
                "messages": [AIMessage(content="No slots available for that time. Would you like to try a different time preference?")],
                "appointment_state": {**appt, "time_preference": None}
            }

        message = "📅 *Available Slots (Next 5 Days)*\n\n"
        message += "\n".join(slot_lines)
        message += "\n\n💬 Reply with your choice"
        
        return {
            **state_update,
            "messages": [AIMessage(content=message)],
            "available_slots": slots_data, 
            "appointment_state": {**appt, "step": "select_slot"}
        }

    # --- 5. FINALIZE BOOKING ---
    logger.info("✅ Finalizing booking...")
    selected_slot = appt.get("selected_slot") or last_message

    # ---------------------------------------------------------------------
    # 🔥 FIXED DATE + TIME PARSING
    # ---------------------------------------------------------------------
    slot_text = selected_slot.strip()

    # 1. Extract proper YYYY-MM-DD date first
    date_match = re.search(r"\b\d{4}-\d{2}-\d{2}\b", slot_text)
    clean_date = date_match.group(0) if date_match else "UNKNOWN-DATE"

    # 2. Remove the date from the text so it doesn't interfere with time parsing
    #    (This fixes the bug where "12-05" was read as "12 PM - 5 AM")
    text_for_time = slot_text
    if date_match:
        text_for_time = slot_text.replace(clean_date, "")

    # 3. Extract time range like "14-15" from the remaining text
    time_match = re.search(r"\b(\d{1,2})\s*-\s*(\d{1,2})\b", text_for_time)

    clean_time = None
    if time_match:
        start_h = int(time_match.group(1))
        end_h = int(time_match.group(2))
        # Keep original format as requested: "14:00 - 15:00"
        clean_time = f"{start_h:02d}:00 - {end_h:02d}:00"
    else:
        clean_time = "UNKNOWN-TIME"
    # ---------------------------------------------------------------------

    filters = state.get("filters")
    filter_dict = filters.model_dump() if filters else {}
    def get_f(k): return filter_dict.get(k, "-")

    # Summary
    llm = OpenAIService().client
    chat_summary = f"User {state.get('user_name')} booked {target_property.get('property_name')}."
    try:
        history_str = "\n".join([f"{m.type}: {m.content}" for m in state["messages"][-10:]])
        summary_res = await llm.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": SUMMARY_PROMPT.format(
                user_name=state.get("user_name"),
                property_name=target_property.get("property_name"),
                viewing_type=appt.get("viewing_type"),
                filters=json.dumps(filter_dict, default=str),
                history=history_str
            )}],
            temperature=0.5
        )
        chat_summary = summary_res.choices[0].message.content
    except:
        pass

    # Payload
    payload = [{
        "agent_id": state["agent_id"],
        "name": state.get("user_name"),
        "clientgender": get_f("tenant_gender"),
        "clientnationality": get_f("tenant_nationality"),
        "property": target_property.get("property_name"),
        "property_address": target_property.get("property_address"),
        "roomnumber": target_property.get("room_number", "N/A"),
        "monthly_rent": target_property.get("monthly_rent"),
        "session_id": state["user_mobile"],
        "email": appt["email"],
        "userpass": appt["pass_type"],
        "clientleaseperiod": str(appt["lease_months"]),
        "appointment_date": clean_date,
        "time": clean_time,
        "appointment_time_from": time_pref,
        "clientmoveindate": get_f("move_in_date"),
        "chatsummary": chat_summary
    }]

    n8n = N8NClient()
    success = await n8n.schedule_appointment(payload)

    if success:
        return {
            "messages": [AIMessage(content=f"✅ **Appointment Confirmed!**\n\n**Date:** {clean_date}\n**Time:** {clean_time}\n\nYou will receive a confirmation email shortly at {appt['email']}. Is there anything else I can help you with?")],
            "active_flow": None,
            "appointment_state": None,
            "available_slots": None,
            "selected_property": None,
            "next_step": "END"
        }
    else:
        return {
            "messages": [AIMessage(content="I apologize, but I couldn't finalize the booking automatically. I've notified a human agent to assist you.")],
            "active_flow": None,
            "appointment_state": None,
            "next_step": "END"
        }