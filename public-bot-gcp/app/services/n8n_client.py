import httpx
import logging
import json
from typing import Dict, Any, List, Optional, Union

logger = logging.getLogger(__name__)

class N8NClient:
    def __init__(self):
        # Replace with your actual N8N Webhook URLs
        self.get_slots_url = "https://rajigenzi.app.n8n.cloud/webhook/get_calender_events"
        self.schedule_url = "https://rajigenzi.app.n8n.cloud/webhook/schedule_appointment"
        self.human_handoff_url = "https://rajigenzi.app.n8n.cloud/webhook/human-agent" 

    async def trigger_workflow(self, workflow_type: str, payload: Union[Dict[str, Any], List[Dict[str, Any]]]) -> str:
        """
        Generic handler for simple workflows (like Human Handoff).
        """
        url = ""
        if workflow_type == "HUMAN_HANDOFF":
            url = self.human_handoff_url
        
        if not url:
            return "Configuration Error: Webhook URL not found."

        try:
            async with httpx.AsyncClient() as client:
                logger.info(f"🚀 Triggering {workflow_type} workflow...")
                
                response = await client.post(url, json=payload, timeout=15.0)
                response.raise_for_status()
                
                # --- RESPONSE PARSING (Updated) ---
                try:
                    result = response.json()
                    
                    # Helper to find the message in common keys
                    def extract_msg(data_dict):
                        return (
                            data_dict.get("response") or  # <--- ADDED THIS
                            data_dict.get("message") or 
                            data_dict.get("text") or 
                            data_dict.get("output")
                        )

                    # Case A: JSON Object {"response": "..."}
                    if isinstance(result, dict):
                        return extract_msg(result) or "Request processed successfully."
                    
                    # Case B: JSON List [{"response": "..."}]
                    if isinstance(result, list) and len(result) > 0:
                        first_item = result[0]
                        if isinstance(first_item, dict):
                            return extract_msg(first_item) or "Request processed successfully."
                    
                    return str(result)
                    
                except json.JSONDecodeError:
                    return response.text or "Request processed."
                    
        except Exception as e:
            logger.error(f"Failed to trigger n8n workflow {workflow_type}: {e}")
            return "I'm having a little trouble connecting to our support system right now, but I've logged your request internally."

    async def get_available_slots(self, agent_id: str, preference: str) -> Optional[List[dict]]:
        """
        Fetches available slots from N8N. 
        The endpoint expects a list with a single object containing agent_id and prefered_time.
        """
        payload = {
            "body": [{
                "agent_id": agent_id,
                "prefered_time": preference
            }]
        }
        
        try:
            async with httpx.AsyncClient() as client:
                logger.info(f"📅 Fetching slots for {agent_id} ({preference})...")
                logger.info(f"Sending request to: {self.get_slots_url}")
                logger.info(f"Request payload: {payload}")
                
                # Send the payload directly as JSON
                resp = await client.post(
                    self.get_slots_url,
                    json=payload,
                    timeout=15.0,
                    headers={"Content-Type": "application/json"}
                )
                logger.info(f"Response status: {resp.status_code}")
                logger.info(f"Response headers: {dict(resp.headers)}")
                
                # Log response text before parsing as JSON
                response_text = resp.text
                logger.info(f"Raw response: {response_text[:500]}")  # Log first 500 chars of response
                
                resp.raise_for_status()
                
                try:
                    response_data = resp.json()
                    logger.info(f"Parsed JSON response: {response_data}")
                except json.JSONDecodeError as je:
                    logger.error(f"Failed to parse JSON response: {je}")
                    logger.error(f"Response content: {response_text}")
                    return None
                
                # 1. Unwrap N8N Structure
                if isinstance(response_data, list) and len(response_data) > 0:
                    if isinstance(response_data[0], list):
                        return response_data[0]
                    if isinstance(response_data[0], dict):
                        if "slots_string" in response_data[0]:
                            response_data = response_data[0]
                        elif "error" in response_data[0]:
                            logger.error(f"N8N Error: {response_data[0].get('error')}")
                            return None

                # 2. Extract the String Field
                if isinstance(response_data, dict):
                    if "error" in response_data:
                        logger.error(f"N8N Error: {response_data.get('error')}")
                        return None
                        
                    raw_string = response_data.get("slots_string")
                    if raw_string:
                        try:
                            slots_list = json.loads(raw_string)
                            return slots_list
                        except json.JSONDecodeError as je:
                            logger.error(f"Failed to parse slots string: {je}")
                            logger.error(f"Raw slots string: {raw_string}")
                            return None
                            
                # 3. Fallback - return as is if it's a list
                if isinstance(response_data, list):
                    return response_data
                    
                logger.error(f"Unexpected response format: {response_data}")
                return None
                
        except httpx.HTTPStatusError as he:
            logger.error(f"HTTP Error {he.response.status_code}: {he.response.text}")
            return None
        except httpx.RequestError as re:
            logger.error(f"Request failed: {re}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in get_available_slots: {e}", exc_info=True)
            return None

    async def schedule_appointment(self, payload: List[Dict[str, Any]]) -> bool:
        """
        Sends final booking details. 
        Checks for explicit success/error in response.
        """
        try:
            async with httpx.AsyncClient() as client:
                logger.info("📅 Scheduling appointment...")
                resp = await client.post(self.schedule_url, json=payload, timeout=15.0)
                
                if resp.status_code != 200:
                    logger.error(f"N8N HTTP Error: {resp.status_code} - {resp.text}")
                    return False
                
                try:
                    data = resp.json()
                    if isinstance(data, dict) and (data.get("status") == "error" or "error" in data):
                        logger.error(f"N8N Workflow Error: {data}")
                        return False
                except:
                    pass

                return True

        except Exception as e:
            logger.error(f"N8N Schedule Exception: {e}")
            return False