import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

load_dotenv()
import json
import re

model=ChatOpenAI(
    model="gpt-4.1-mini",
    openai_api_key=os.getenv("OPENAI_API_KEY")
)

def generate_mail(package_status):
    system_prompt = """
    You are an AI Assistant that generates tracking update emails for customers.
    You will receive raw JSON data from a carrier API.
    Analyze the data and create a helpful, friendly email.
    
    Return your response EXCLUSIVELY in this JSON format:
    {
        "subject": "Clear and concise subject line",
        "body": "Friendly and detailed email body"
    }
    """
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Generate an update email for this shipment data: {json.dumps(package_status)}")
    ]

    response = model.invoke(messages)
    content = response.content.strip()
    
    # Clean markdown if present
    json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
    if json_match:
        content = json_match.group(1).strip()
    else:
        start = content.find('{')
        end = content.rfind('}')
        if start != -1 and end != -1:
            content = content[start:end+1]
            
    try:
        return json.loads(content)
    except:
        return {
            "subject": "Update on your shipment",
            "body": content # Fallback
        }
