from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import logging

logger = logging.getLogger(__name__)

class ProspectRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def upsert_prospect(self, data: dict):
        """
        Inserts a new prospect or updates existing one based on user_id (phone) + agent_id.
        
        CRITICAL: Since 'email' is a Primary Key but we don't have it initially,
        we use a dummy placeholder format: {phone}@whatsapp.user
        """
        user_id = data.get("user_id") # Phone Number
        agent_id = data.get("agent_id")
        
        if not user_id or not agent_id:
            logger.error("Cannot upsert prospect: Missing user_id or agent_id")
            return

        # 1. LOGIC: Determine the Email Identity
        # If we collected a real email in this turn, use it. 
        # If not, fall back to the unique dummy identity.
        provided_email = data.get("email")
        dummy_email = f"{user_id}@whatsapp.user"
        
        target_email = provided_email if provided_email else dummy_email

        # 2. PREPARE PARAMETERS (Default missing fields to None or '-')
        params = {
            "user_id": user_id,
            "agent_id": agent_id,
            "email": target_email, 
            "phone": user_id, # Phone is same as user_id in WhatsApp
            "name": data.get("name"),
            "gender": data.get("gender"),
            "nationality": data.get("nationality"),
            "pass_type": data.get("pass_type", "-"),
            "profession": data.get("profession"),
            "move_in_date": data.get("move_in_date"),
            "session_id": data.get("session_id"),
            # Add other fields if you extract them (budget, location, etc.)
        }

        # 3. EXECUTE UPSERT (Insert or Update)
        # We use ON CONFLICT (email, agent_id) because that is your PK.
        query = text("""
            INSERT INTO public.prospect_info (
                user_id, agent_id, email, phone, name, gender, nationality, 
                pass, profession, move_in_date, session_id, last_interaction
            )
            VALUES (
                :user_id, :agent_id, :email, :phone, :name, :gender, :nationality, 
                :pass_type, :profession, :move_in_date, :session_id, NOW()
            )
            ON CONFLICT (email, agent_id) 
            DO UPDATE SET
                last_interaction = NOW(),
                phone = EXCLUDED.phone,
                -- Only overwrite fields if the new data is NOT NULL (COALESCE)
                name = COALESCE(EXCLUDED.name, prospect_info.name),
                gender = COALESCE(EXCLUDED.gender, prospect_info.gender),
                nationality = COALESCE(EXCLUDED.nationality, prospect_info.nationality),
                pass = COALESCE(EXCLUDED.pass, prospect_info.pass),
                profession = COALESCE(EXCLUDED.profession, prospect_info.profession),
                move_in_date = COALESCE(EXCLUDED.move_in_date, prospect_info.move_in_date),
                session_id = COALESCE(EXCLUDED.session_id, prospect_info.session_id);
        """)

        try:
            await self.db.execute(query, params)
            await self.db.commit()
        except Exception as e:
            logger.error(f"Error upserting prospect: {e}")
            await self.db.rollback()

    async def update_real_email(self, agent_id: str, phone_number: str, new_real_email: str):
        """
        Call this function ONLY when the user explicitly provides their real email address.
        It swaps the dummy placeholder (@whatsapp.user) for the real email.
        """
        dummy_email = f"{phone_number}@whatsapp.user"

        try:
            # 1. CHECK CONFLICT: Does 'real@gmail.com' already exist?
            # (e.g. they registered on the website before chatting)
            check_query = text("SELECT 1 FROM prospect_info WHERE email = :real_email AND agent_id = :agent_id")
            result = await self.db.execute(check_query, {"real_email": new_real_email, "agent_id": agent_id})
            
            if result.scalar():
                # SCENARIO A: Target email exists. MERGE identities.
                # We update the old existing web-record with the new phone number & chat session
                # and delete the temporary dummy chat record.
                logger.info(f"Email {new_real_email} exists. Merging identities.")
                
                merge_query = text("""
                    UPDATE prospect_info 
                    SET phone = :phone, last_interaction = NOW()
                    WHERE email = :real_email AND agent_id = :agent_id
                """)
                await self.db.execute(merge_query, {"phone": phone_number, "real_email": new_real_email, "agent_id": agent_id})
                
                # Delete the dummy now that we merged
                del_query = text("DELETE FROM prospect_info WHERE email = :dummy AND agent_id = :agent_id")
                await self.db.execute(del_query, {"dummy": dummy_email, "agent_id": agent_id})
                
            else:
                # SCENARIO B: Brand new email. SWAP identities.
                # Just rename the Primary Key of the current row.
                logger.info(f"Updating dummy email {dummy_email} to {new_real_email}")
                
                swap_query = text("""
                    UPDATE prospect_info 
                    SET email = :new_email 
                    WHERE email = :dummy_email AND agent_id = :agent_id
                """)
                await self.db.execute(swap_query, {
                    "new_email": new_real_email,
                    "dummy_email": dummy_email,
                    "agent_id": agent_id
                })

            await self.db.commit()
            
        except Exception as e:
            logger.error(f"Error updating real email: {e}")
            await self.db.rollback()