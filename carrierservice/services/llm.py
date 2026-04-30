import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

load_dotenv()
model=ChatOpenAI(
    model="gpt-4.1-mini",
    openai_api_key=os.getenv("OPENAI_API_KEY")
)
messages=[
    SystemMessage(
        content="""
        You are an AI Assistant that helps users track packages and also used to send mail to the customer.
        You can do two task:
        1. you will get the package status, through an api in json format. 
        2. you have to find the previous order status and current order status and compare them and return the result in a mail.
        3. The mail format should always be the same.   
        the expecfted result is like :
         shipments: [
        {'shipments': [{'id': 'JVGL06218507000372709959', 'service': 'parcel-nl', 'status': {'timestamp': '2026-04-13T09:02:21.001+02:00', 'statusCode': 'pre-transit', 'status': 'PRENOTIFICATION_RECEIVED', 'description': 'Shipment not yet received or processed'}, 'events': [{'timestamp': '2026-04-13T09:02:21.001+02:00', 'statusCode': 'pre-transit', 'status': 'PRENOTIFICATION_RECEIVED', 'description': 'Shipment not yet received or processed'}, {'timestamp': '2026-04-13T09:02:21+02:00', 'statusCode': 'pre-transit', 'status': 'DATA_RECEIVED_WITH_PREFIX_LABEL', 'description': 'Shipment not yet received or processed'}]}]}

        """
    )
]


def generate_mail(package_status):
    messages.append(HumanMessage(content=f"""
    This is the {package_status} 
    """))

    response = model.invoke(messages)
    return response.content
