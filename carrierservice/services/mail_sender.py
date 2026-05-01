import os 
from mailjet_rest import Client
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=5)
) 
def send_status_email(to_email, subject, body_text):
    api_key=os.getenv("MAILJET_API_KEY")
    api_secret=os.getenv('MAILJET_API_SECRET')
    sender_email=os.getenv('MAILJET_SENDER_EMAIL')
    mailjet=Client(auth=(api_key,api_secret), version='v3.1')

    data = {
    'Messages':[
        {
        "From": {
            "Email": sender_email,
            "Name": "Carrier automation update"
        },
        "To": [
            {
            "Email": to_email,
            "Name": "User"
            }
        ],
        "Subject": subject,
        "TextPart": body_text,
        }
    ]
    }
    result = mailjet.send.create(data=data)
    return result.status_code