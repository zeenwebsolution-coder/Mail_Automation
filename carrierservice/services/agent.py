import os
import requests
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain.agents import create_agent
from tenacity import retry, stop_after_attempt, wait_exponential

load_dotenv()

# --- Tools for the Agent ---

@tool
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def get_dhl_tracking_info(tracking_number: str, country: str = None):
    """
    Fetches real-time tracking information for a shipment from the DHL API.
    Has built-in retry logic for network stability.
    """
    url = os.getenv("DHL_SHIPMENT_TRACKING")
    api_key = os.getenv("DHL_API_KEY")
    # In a real scenario, we might use 'country' to switch URLs or parameters.
    # For now, we'll log it or use it to filter results.
    
    try:
        response = requests.get(
            url, 
            params={"trackingNumber": tracking_number}, 
            headers={"DHL-API-Key": api_key}
        )
        data = response.json()
        
        if "shipments" in data and len(data["shipments"]) > 0:
            shipment = data["shipments"][0]
            status = shipment.get("status", {})
            events = shipment.get("events", [])[:5]
            return {
                "current_status": status.get("status"),
                "description": status.get("description"),
                "last_location": status.get("location", {}).get("address", {}).get("addressLocality", "Unknown"),
                "recent_events": events
            }
        return data
    except Exception as e:
        return f"Error fetching DHL data: {str(e)}"

@tool
def get_fedex_tracking_info(tracking_number: str, country: str = None):
    """
    Fetches tracking information for FedEx shipments. Use country to help routing.
    """
    # Placeholder for FedEx regional API logic
    return {
        "current_status": "In Transit",
        "description": f"Package is moving within {country if country else 'the network'}",
        "last_location": "Memphis, TN",
        "recent_events": [{"timestamp": "2026-04-30T10:00:00Z", "description": "Left FedEx origin facility"}]
    }

@tool
def get_ups_tracking_info(tracking_number: str, country: str = None):
    """
    Fetches tracking information for UPS shipments. Use country to help routing.
    """
    # Placeholder for UPS regional API logic
    return {
        "current_status": "Delayed",
        "description": f"Weather delay reported in {country if country else 'transit'}",
        "last_location": "Louisville, KY",
        "recent_events": [{"timestamp": "2026-04-30T08:00:00Z", "description": "Arrival Scan"}]
    }

@tool
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5))
def get_coordinates(location_name: str):
    """
    Converts a location name (e.g., 'Berlin, DE') into latitude and longitude coordinates.
    """
    try:
        url = "https://nominatim.openstreetmap.org/search"
        headers = {'User-Agent': 'CarrierTrackerAgent/1.0'}
        response = requests.get(url, params={'q': location_name, 'format': 'json'}, headers=headers)
        data = response.json()
        if data:
            return {"lat": float(data[0]['lat']), "lng": float(data[0]['lon'])}
        return {"error": "Location not found"}
    except Exception as e:
        return {"error": str(e)}

# --- Agent Setup ---

tools = [get_dhl_tracking_info, get_fedex_tracking_info, get_ups_tracking_info, get_coordinates]
# Using gpt-4o-mini for 10x faster response time and lower cost
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

system_prompt = (
    "You are a global logistics expert. Return a JSON object ONLY.\n"
    "JSON structure:\n"
    "{\n"
    "  'status': 'Current status',\n"
    "  'summary': 'Short human summary',\n"
    "  'coordinates': [{'lat': 0.0, 'lng': 0.0, 'name': 'City'}],\n"
    "  'events': ['Event 1', 'Event 2']\n"
    "}\n"
    "Use 'get_coordinates' for all locations. If only the country is known, geocode the country."
)

agent = create_agent(
    model=llm, 
    tools=tools, 
    system_prompt=system_prompt
)

def ask_agent(user_query: str):
    """
    Allows the user to ask questions and get structured tracking data.
    Ensures the response is a JSON string containing status, coordinates, and summary.
    """
    # The new API expects a list of messages
    inputs = {"messages": [{"role": "user", "content": user_query}]}
    
    # Invoke the agent graph
    result = agent.invoke(inputs)
    
    # The result contains the message history. The last message is the AI's response.
    final_message = result["messages"][-1]
    
    # Return the content of the final message
    # Handle both string and list content (some models return lists of dicts)
    if isinstance(final_message.content, list):
        return final_message.content[0].get("text", "")
    return final_message.content
