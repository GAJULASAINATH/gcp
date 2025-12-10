from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from app.core.state import AgentState
from app.tools.knowledge_base import KnowledgeBaseTool
from app.services.openai_service import OpenAIService
from app.services.n8n_client import N8NClient
import json
from datetime import datetime
import pytz
import logging

logger = logging.getLogger(__name__)

# UPDATED PROMPT: Relaxed Guardrails + Slang Support
SUPER_SYSTEM_PROMPT = """
You are {agent_name}, a warm, engaging, and helpful Real Estate Agent at {company_name}. 🏠

### 1. COMPANY KNOWLEDGE (Policies, Fees, Rules)
{kb_context}

### 2. CURRENT SEARCH RESULTS (Properties discussed)
{properties_json}

### INSTRUCTIONS

1. **Analyze the Question:**
   - If it's about **company rules, contracts, viewings, deposits, policies** → Use Section 1.
   - If it's about a **specific property** already discussed → Use Section 2.
   - If it's about **Singapore living, nearby amenities, transport, neighbourhoods, safety, lifestyle, restaurants, gyms, malls, schools**, or anything a real estate agent normally knows → Use your **general knowledge**.
   - If it's **small talk or greetings** → Be warm.

2. **THE RULE OF RELEVANCE (Guardrails):**
   - You should answer **ANY question related to housing, living, lifestyle, locations, neighbourhoods, property surroundings, cost of living, or Singapore**.
   - ONLY decline questions that are **clearly unrelated** to a real estate agent’s job.  
     Examples of “unrelated”:
       - “Write Python code”
       - “Do my math homework”
       - “Who won the World Cup?”
       - “Hack something”
   - If it's even *slightly* connected to living or staying in Singapore (restaurants, noise level, safety, commute, MRT distance, ambience, nearby malls), **DO NOT DECLINE**.

3. **THE RULE OF TRUTH (Auto-Handoff):**
   - If the user asks a **valid and relevant** question, but the answer is NOT in:
       - Section 1 (company knowledge),
       - Section 2 (properties),
       - or your general Singapore real estate knowledge,
   - **Do NOT guess.**
   - Respond with exactly:
     `NO_DATA_HANDOFF`

4. **Tone:**
   - Sound like a friendly human.
   - Keep answers to 3–4 sentences.
   - Natural, warm, conversational.

5. **Greeting:** {greeting_instruction}

### USER MESSAGE
"{user_message}"
"""

async def intelligent_chat_node(state: AgentState, config: RunnableConfig):
    db = config.get("configurable", {}).get("db_session")
    agent_id = state["agent_id"]
    last_message = state["messages"][-1].content
    
    # 1. Fetch Contexts
    kb_tool = KnowledgeBaseTool(db)
    kb_context = await kb_tool.search(agent_id, last_message) or "No specific company documents found."

    properties = state.get("found_properties", [])
    if properties:
        context_props = []
        for i, p in enumerate(properties[:3]):
            p_copy = p.copy()
            p_copy['reference_index'] = i + 1
            context_props.append(p_copy)
        props_json = json.dumps(context_props, indent=2, default=str)
    else:
        props_json = "No active search results."

    # 2. Determine Greeting
    tz = pytz.timezone('Asia/Singapore')
    h = datetime.now(tz).hour
    greeting = "Good morning" if 5<=h<12 else "Good afternoon" if 12<=h<18 else "Good evening"
    
    is_first_interaction = len(state["messages"]) <= 1
    if is_first_interaction:
        agent_name = state.get("agent_name") or "Aba"
        company_name = state.get("company_name") or "Adobha"
        greeting_instruction = f"Start with '{greeting}! I'm {agent_name} from {company_name}. What can I do for you today?'"
    else:
        greeting_instruction = "Do NOT start with a formal greeting. Answer naturally."

    # 3. Call AI
    llm = OpenAIService().client
    agent_name = state.get("agent_name") or "Aba"
    company_name = state.get("company_name") or "Adobha"
    
    response = await llm.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SUPER_SYSTEM_PROMPT.format(
                agent_name=agent_name,
                company_name=company_name,
                kb_context=kb_context,
                properties_json=props_json,
                user_message=last_message,
                time_greeting=greeting,
                greeting_instruction=greeting_instruction
            )}
        ],
        temperature=0.3
    )
    
    ai_reply = response.choices[0].message.content.strip()

    # --- 4. AUTO-HANDOFF LOGIC ---
    if "NO_DATA_HANDOFF" in ai_reply:
        logger.info(f"🤖 Bot cannot answer: '{last_message}'. Triggering Auto Handoff.")
        
        # A. Construct Payload
        filters = state.get("filters")
        filter_dict = filters.model_dump() if filters else {}
        def get_f(k): return filter_dict.get(k, "-")
        
        prop = state.get("selected_property") or {}
        appt = state.get("appointment_state") or {}

        payload = [{
            "agent_id": state["agent_id"],
            "clientmessage": last_message, 
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
            "chatsummary": f"Auto-Handoff: Bot could not answer question: '{last_message}'"
        }]

        # B. Call N8N Silently
        n8n = N8NClient()
        await n8n.trigger_workflow("HUMAN_HANDOFF", payload)
        
        # C. Return specific failure message
        return {
            "messages": [AIMessage(content="I am sorry currently I don't have an answer for that! I have forwarded your message to human agent!")]
        }

    # Normal Reply
    return {"messages": [AIMessage(content=ai_reply)]}