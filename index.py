import requests
import json

client_id = r'c327e788f16c4a8087ead33508afe41c'
client_secret = r'57d64ecd557fa27171becc2b742903c315a45cb052c2af2e2cef66d8524c62ad'

auth_data = {
    'grant_type': 'client_credentials',
    'client_id': client_id,
    'client_secret': client_secret,
    'scope': 'read_content read_financial_data read_product_data read_user_profile'
}

# create session instance
session = requests.Session()

# make a POST to retrieve access_token
auth_request = session.post(
    'https://idfs.gs.com/as/token.oauth2', data=auth_data)
access_token_dict = json.loads(auth_request.text)
access_token = access_token_dict['access_token']

print("Authenticated!")
session.headers.update({"Authorization": "Bearer " + access_token})


request_url = "https://api.marquee.gs.com/v1/data/datasets"

request = session.get(url=request_url)
results = json.loads(request.text)
print(access_token)
