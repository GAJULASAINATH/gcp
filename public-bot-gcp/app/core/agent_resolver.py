from fastapi import HTTPException
from app.db.repositories.agent_repository import AgentRepository
import logging

logger = logging.getLogger(__name__)

class AgentResolver:
    def __init__(self, db):
        self.repository = AgentRepository(db)

    async def resolve_from_webhook(self, payload: dict):
        try:
            # 1. Extract ID
            changes = payload['entry'][0]['changes'][0]['value']
            phone_number_id = changes['metadata']['phone_number_id']
            
            # 2. Query DB (Async)
            agent = await self.repository.get_agent_by_whatsapp_id(phone_number_id)
            
            if agent:
                logger.info(f"Resolved Agent: {agent.name} (ID: {agent.agent_id})")
                return agent
            else:
                logger.warning(f"No agent found for WhatsApp ID: {phone_number_id}")
                return None

        except (KeyError, IndexError) as e:
            # This catches issues if the JSON structure is wrong
            logger.error(f"Malformed WhatsApp Payload: {e}")
            # It's better to return None here than raise an exception, 
            # so your main loop doesn't crash on a bad packet.
            return None