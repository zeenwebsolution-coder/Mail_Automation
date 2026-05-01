import sys
import os
import django
import json

# Setup django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'carrierservice.settings')
django.setup()

from carrierservice.services.agent import ask_agent

query = "Track DHL package 1234567890."
print("Sending query to agent...")
response = ask_agent(query)
print("\n--- Agent Response ---")
print(response)
print("----------------------\n")

# Try to parse it
try:
    if response.startswith("```json"):
        response = response.strip("```json").strip("```").strip()
    data = json.loads(response)
    print("Successfully parsed JSON!")
    print(json.dumps(data, indent=2))
except Exception as e:
    print(f"Failed to parse JSON: {e}")
