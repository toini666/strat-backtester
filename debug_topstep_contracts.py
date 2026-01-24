import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

USERNAME = os.getenv("TOPSTEP_USERNAME") or os.getenv("TOPSTEPX_USERNAME")
TOKEN = os.getenv("TOPSTEPX_TOKEN")
BASE_URL = "https://api.topstepx.com"

def get_token():
    url = f"{BASE_URL}/api/Auth/loginKey"
    payload = {"userName": USERNAME, "apiKey": TOKEN}
    resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
    return resp.json().get("token")

def check_contracts(live_flag):
    token = get_token()
    if not token:
        print("❌ Login failed")
        return

    url = f"{BASE_URL}/api/Contract/available"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {"live": live_flag}
    
    print(f"Testing with live={live_flag}...")
    resp = requests.post(url, headers=headers, json=payload)
    data = resp.json()
    
    if data.get("success"):
        contracts = data.get("contracts", [])
        print(f"✅ Found {len(contracts)} contracts.")
        if len(contracts) > 0:
            print(f"Sample: {contracts[0]['name']}")
    else:
        print(f"❌ Error: {data}")

if __name__ == "__main__":
    check_contracts(True)
    check_contracts(False)
