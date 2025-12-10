from sqlalchemy import text
from app.core.state import AgentState
import uuid
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class ConversationService:
    def __init__(self, db_session):
        self.db = db_session

    async def get_active_session_id(self, user_id: str) -> str:
        """
        Retrieves the current session ID or creates a new one if the 
        last interaction was more than 30 minutes ago.
        """
        # 1. Get the most recent message for this user
        query = text("""
            SELECT session_id, created_at 
            FROM chat_history_whatsapp 
            WHERE user_id = :user_id 
            ORDER BY created_at DESC 
            LIMIT 1
        """)
        
        result = await self.db.execute(query, {"user_id": user_id})
        last_record = result.mappings().first()

        # 2. Check Expiration (30 Minutes)
        if last_record:
            last_time = last_record['created_at']
            # Ensure last_time is timezone-aware or naive consistent with datetime.now()
            # Postgres usually returns offset-aware.
            if last_time.tzinfo:
                from datetime import timezone
                now = datetime.now(timezone.utc)
            else:
                now = datetime.now()

            time_diff = now - last_time
            
            if time_diff < timedelta(minutes=30):
                return last_record['session_id']

        # 3. Create New Session (If no history OR expired)
        new_session = str(uuid.uuid4())
        logger.info(f"🆕 Starting new session: {new_session} for user {user_id}")
        return new_session

    async def log_message(self, 
                          session_id: str, 
                          user_id: str, 
                          agent_id: str, 
                          sender: str, 
                          message: str, 
                          metadata: dict = None):
        """
        Logs a message (User or Bot) into the database.
        """
        try:
            query = text("""
                INSERT INTO chat_history_whatsapp (session_id, user_id, agent_id, sender, message, metadata)
                VALUES (:sid, :uid, :aid, :sender, :msg, :meta)
            """)
            
            await self.db.execute(query, {
                "sid": session_id,
                "uid": user_id,
                "aid": agent_id,
                "sender": sender,
                "msg": message,
                "meta": import_json_dump(metadata) if metadata else "{}"
            })
            # Note: The caller (endpoints/whatsapp.py) usually handles the commit
            # But if you want auto-commit here, uncomment next line:
            # await self.db.commit()
            
        except Exception as e:
            logger.error(f"Failed to log chat message: {e}")

def import_json_dump(data):
    import json
    return json.dumps(data, default=str)