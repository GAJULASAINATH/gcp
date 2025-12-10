from fastapi import APIRouter, Request, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.messages import HumanMessage

from app.db.session import get_db
from app.core.agent_resolver import AgentResolver
from app.services.whatsapp_client import WhatsAppClient
from app.services.conversation_service import ConversationService # <--- Import Service

# --- UPDATED IMPORTS ---
from app.core.persistence import get_checkpointer
from app.graphs.master_graph import get_master_graph 
import os
import logging

# Initialize Router and Logger
router = APIRouter()
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN") 

# ==============================================================================
# 1. VERIFICATION ENDPOINT (GET)
# ==============================================================================
@router.get("/webhook")
async def verify_webhook(
    mode: str = Query(..., alias="hub.mode"),
    token: str = Query(..., alias="hub.verify_token"),
    challenge: str = Query(..., alias="hub.challenge")
):
    if mode == "subscribe" and token == VERIFY_TOKEN:
        logger.info("Webhook verified successfully!")
        return int(challenge)
    
    logger.warning("Webhook verification failed: Invalid token.")
    raise HTTPException(status_code=403, detail="Verification failed")


# ==============================================================================
# 2. MESSAGE RECEIVER (POST)
# ==============================================================================
@router.post("/webhook")
async def receive_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Receives WhatsApp events, resolves the agent, logs chat, and runs the Master Graph flow.
    """
    try:
        payload = await request.json()
        
        # --- A. FILTER OUT STATUS UPDATES ---
        if 'entry' in payload and payload['entry']:
             changes = payload['entry'][0].get('changes', [])
             if changes and 'statuses' in changes[0]['value']:
                 return {"status": "ignored", "reason": "status_update"}

        # --- B. RESOLVE THE AGENT ---
        resolver = AgentResolver(db)
        agent = await resolver.resolve_from_webhook(payload)
        
        if not agent:
            logger.warning("Received message for unknown Agent ID.")
            return {"status": "ignored", "reason": "agent_not_found"}

        if not agent.chatbot_enabled:
            logger.info(f"⛔ Agent {agent.name} is disabled. Sending default reply.")
            wa_client = WhatsAppClient()
            changes = payload['entry'][0]['changes'][0]['value']
            user_mobile = changes['messages'][0]['from']
            
            await wa_client.send_text_message(
                to_number=user_mobile,
                text="Hello! I am currently offline. I will get back to you as soon as I am available.",
                phone_number_id=agent.whatsapp_phone_number_id,
                access_token=agent.whatsapp_access_token
            )
            return {"status": "ignored", "reason": "chatbot_disabled"}
        
        # --- C. EXTRACT DATA ---
        value = payload['entry'][0]['changes'][0]['value']
        messages = value.get('messages', [])
        contacts = value.get('contacts', [])
        
        if not messages:
            return {"status": "ok", "message": "No text message found"}
            
        user_message_data = messages[0]
        user_mobile = user_message_data.get('from') 
        msg_type = user_message_data.get('type')
        
        user_name = "there"
        if contacts:
            user_name = contacts[0].get('profile', {}).get('name', "there")
        
        # --- D. PROCESS MESSAGE WITH MASTER GRAPH ---
        if msg_type == "text":
            message_text = user_message_data['text']['body']
            logger.info(f"🟢 AGENT '{agent.name}' received from {user_name} ({user_mobile}): {message_text}")

            # --- 1. LOG USER MESSAGE (CONVERSATION SERVICE) ---
            conv_service = ConversationService(db)
            session_id = await conv_service.get_active_session_id(user_mobile)
            
            await conv_service.log_message(
                session_id=session_id,
                user_id=user_mobile,
                agent_id=agent.agent_id,
                sender="user",
                message=message_text
            )
            await db.commit() # Commit early so it's saved

            # --- 2. SETUP PERSISTENCE ---
            checkpointer = await get_checkpointer(db.bind)
            
            # --- 3. GET MASTER GRAPH ---
            graph = get_master_graph(checkpointer)

            # --- 4. CONFIGURE THREAD ---
            config = {
                "configurable": {
                    "thread_id": user_mobile, 
                    "db_session": db 
                }
            }

            # --- 5. PREPARE INPUT ---
            input_data = {
                "messages": [HumanMessage(content=message_text)],
                "agent_id": agent.agent_id,
                "user_mobile": user_mobile,
                "user_name": user_name,
                "agent_name": agent.chatbot_name,
                "company_name": agent.company_name,
                "agent_bio": agent.bio 
            }

            # --- 6. RUN GRAPH ---
            final_state = await graph.ainvoke(input_data, config=config)
            
            # --- 7. GET REPLY & SEND ---
            ai_reply = final_state["messages"][-1].content
            
            # Log AI Response
            await conv_service.log_message(
                session_id=session_id,
                user_id=user_mobile,
                agent_id=agent.agent_id,
                sender="assistant",
                message=ai_reply,
                metadata={"flow": final_state.get("active_flow")}
            )
            await db.commit()

            # Send to WhatsApp
            wa_client = WhatsAppClient()
            await wa_client.send_text_message(
                to_number=user_mobile,
                text=ai_reply,
                phone_number_id=agent.whatsapp_phone_number_id,
                access_token=agent.whatsapp_access_token
            )
            
        else:
            logger.info(f"Received non-text message type: {msg_type}")

    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return {"status": "error", "detail": str(e)}
    
    return {"status": "received"}