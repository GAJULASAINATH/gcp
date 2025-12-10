import httpx
import logging

logger = logging.getLogger(__name__)

class WhatsAppClient:
    # 1. REMOVE arguments from __init__. 
    # We don't want to lock this client to one agent.
    def __init__(self):
        self.api_version = "v18.0"
        self.base_url = f"https://graph.facebook.com/{self.api_version}"

    # 2. PASS credentials here instead
    async def send_text_message(self, to_number: str, text: str, phone_number_id: str, access_token: str):
        """
        Sends a text message using the specific agent's credentials.
        """
        url = f"{self.base_url}/{phone_number_id}/messages"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_number,
            "type": "text",
            "text": {"body": text}
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                logger.info(f"Message sent to {to_number}")
                return response.json()
            except httpx.HTTPStatusError as e:
                # Log the specific error from Facebook (very helpful for debugging)
                logger.error(f"Failed to send message: {e.response.text}")
                return None
            except Exception as e:
                logger.error(f"WhatsApp Client Error: {e}")
                return None