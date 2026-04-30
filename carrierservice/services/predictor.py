import os
import json
import logging
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

load_dotenv()
logger = logging.getLogger(__name__)

model = ChatOpenAI(
    model="gpt-4.1-mini",
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    temperature=0.3,  # lower temperature for more consistent predictions
)

PREDICTOR_SYSTEM_PROMPT = """
You are an expert logistics AI that predicts estimated delivery dates for shipments.

You will receive shipment tracking data from the DHL API in JSON format. Analyze:
1. The current status of the shipment
2. The timestamps and progression of all tracking events
3. Time gaps between consecutive events
4. The shipment service type (e.g. express, standard, parcel)
5. Origin and destination information if available

Based on your analysis, return a JSON object with EXACTLY this structure (no markdown, no code fences, just raw JSON):
{
    "estimated_delivery": "YYYY-MM-DD",
    "estimated_time_range": "Morning (8AM-12PM) | Afternoon (12PM-5PM) | Evening (5PM-9PM) | Unknown",
    "confidence": 85,
    "status_summary": "A one-line plain English summary of the current shipment status",
    "reasoning": "2-3 sentences explaining why you predicted this date based on the tracking patterns",
    "risk_factors": ["factor1", "factor2"]
}

Rules:
- "confidence" must be an integer from 0 to 100
- If the package is already delivered, set confidence to 100 and use the actual delivery date
- If the package is in pre-transit with no movement, set confidence to 30-50 range
- If there are customs or exception events, lower confidence and note it in risk_factors
- If you cannot determine an ETA at all, set estimated_delivery to "Unknown" and confidence to 0
- NEVER wrap the output in markdown code fences or backticks. Return ONLY raw JSON.
"""


def predict_delivery(tracking_data: dict) -> dict:
    """
    Analyze shipment tracking data and predict delivery ETA.
    
    Args:
        tracking_data: Raw JSON response from DHL tracking API
        
    Returns:
        dict with keys: estimated_delivery, confidence, status_summary,
        reasoning, risk_factors, estimated_time_range
    """
    fallback = {
        "estimated_delivery": "Unknown",
        "estimated_time_range": "Unknown",
        "confidence": 0,
        "status_summary": "Unable to analyze tracking data",
        "reasoning": "The tracking data could not be processed for prediction.",
        "risk_factors": [],
    }

    try:
        messages = [
            SystemMessage(content=PREDICTOR_SYSTEM_PROMPT),
            HumanMessage(content=f"Analyze this shipment tracking data and predict the delivery date:\n\n{json.dumps(tracking_data, indent=2)}")
        ]

        response = model.invoke(messages)
        raw = response.content.strip()

        # Strip markdown code fences if the model wraps them anyway
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]  # remove first line
            if raw.endswith("```"):
                raw = raw[:-3]
            raw = raw.strip()

        prediction = json.loads(raw)

        # Validate required keys exist
        required = ["estimated_delivery", "confidence", "status_summary", "reasoning"]
        for key in required:
            if key not in prediction:
                prediction[key] = fallback[key]

        # Clamp confidence to 0-100
        prediction["confidence"] = max(0, min(100, int(prediction.get("confidence", 0))))

        # Ensure risk_factors is a list
        if not isinstance(prediction.get("risk_factors"), list):
            prediction["risk_factors"] = []

        if "estimated_time_range" not in prediction:
            prediction["estimated_time_range"] = "Unknown"

        return prediction

    except json.JSONDecodeError as e:
        logger.error(f"ETA Predictor: Failed to parse LLM response as JSON: {e}")
        return fallback
    except Exception as e:
        logger.error(f"ETA Predictor: Unexpected error: {e}")
        return fallback
