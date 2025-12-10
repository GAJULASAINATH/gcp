from sqlalchemy import select
from sqlalchemy.orm import load_only
from app.db.models import Agent
from sqlalchemy.ext.asyncio import AsyncSession

class AgentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_agent_by_whatsapp_id(self, whatsapp_id: str):
        # We specify EXACTLY which columns to load. 
        # All other columns will be empty (deferred).
        query = (
            select(Agent)
            .where(Agent.whatsapp_phone_number_id == whatsapp_id)
            .options(
                load_only(
                    Agent.agent_id,
                    Agent.name,
                    Agent.chatbot_enabled,       # Needed for your new check
                    Agent.chatbot_name,          # Needed for AI Prompt
                    Agent.company_name,          # Needed for AI Prompt
                    Agent.bio,                   # Needed for AI Prompt
                    Agent.registration_no,       # Needed for AI Prompt
                    Agent.whatsapp_access_token, # Needed to reply
                    Agent.whatsapp_phone_number_id
                )
            )
        )
        result = await self.db.execute(query)
        return result.scalars().first()