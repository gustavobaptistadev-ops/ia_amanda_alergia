import logging
import httpx
import json
from app.core.config import settings

logger = logging.getLogger(__name__)

async def evaluate_transcript_via_langflow(transcript: str, contact_id: str) -> str:
    """
    Calls a Langflow visual API endpoint to evaluate the given transcript.
    The Langflow flow must be configured to receive 'chat_transcript' or similar as input
    and return an evaluation string.
    """
    if not settings.LANGFLOW_API_URL or not settings.LANGFLOW_FLOW_ID:
        logger.warning("Langflow configuration is missing. Returning 'NONE'.")
        return "NONE"

    url = f"{settings.LANGFLOW_API_URL.rstrip('/')}/api/v1/run/{settings.LANGFLOW_FLOW_ID}"
    
    headers = {
        "Content-Type": "application/json"
    }
    if settings.LANGFLOW_API_KEY:
        headers["Authorization"] = f"Bearer {settings.LANGFLOW_API_KEY}"

    try:
        tweaks = json.loads(settings.LANGFLOW_TWEAKS)
    except Exception:
        tweaks = {}

    payload = {
        "input_value": transcript,
        "output_type": "chat",
        "input_type": "chat",
        "tweaks": tweaks
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            # Parse standard Langflow V1.0 run output
            if "outputs" in data and len(data["outputs"]) > 0:
                results = data["outputs"][0].get("outputs", [])
                if results and "results" in results[0]:
                    message = results[0]["results"].get("message", {})
                    if hasattr(message, "get"):
                        return message.get("text", "NONE").strip()
                    elif hasattr(message, "text"):
                        return message.text.strip()
            
            # Fallback if structure is different
            return str(data)

    except Exception as e:
        logger.error(f"Failed to evaluate transcript via Langflow for contact {contact_id}: {e}")
        return "NONE"
