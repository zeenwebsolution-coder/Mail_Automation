import requests

url = "http://127.0.0.1:8000/api/track/"
headers = {"Content-Type": "application/json", "Accept": "application/json"}
data = {"email": "test@test.com", "tracking_number": "123", "carrier": "DHL"}

response = requests.post(url, json=data, headers=headers)
print("Status Code:", response.status_code)
print("Headers:", response.headers)
print("Body:", response.text[:500])
