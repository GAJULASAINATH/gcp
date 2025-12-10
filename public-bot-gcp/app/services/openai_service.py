from openai import AsyncOpenAI
import os
import logging

logger = logging.getLogger(__name__)

class OpenAIService:
    def __init__(self):
        # FIX: Initialize client here so it belongs to the instance
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("OPENAI_API_KEY is missing in environment variables!")
        
        self.client = AsyncOpenAI(api_key=api_key)

    async def get_chat_response(self, system_prompt: str, user_message: str):
        """
        Sends the prompt and user message to OpenAI and gets a response.
        """
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI Error: {e}")
            return "I'm having a little trouble connecting right now. Can you try again in a moment?"