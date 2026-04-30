import requests
from dotenv import load_dotenv
import os

load_dotenv()

url = os.getenv('DHL_SHIPMENT_TRACKING')

headers = {
    'DHL-API-Key':os.getenv('DHL_API_KEY')
}

response=requests.get(url,params={'trackingNumber':'JVGL06218507000372709959'},headers=headers)

print(response.json())