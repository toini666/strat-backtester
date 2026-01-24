import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TOPSTEPX_TOKEN")
BASE_URL = "https://api.topstepx.com"

def check_contracts():
    if not TOKEN:
        print("❌ No TOPSTEPX_TOKEN found in .env")
        return

    url = f"{BASE_URL}/api/Contract/available"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    payload = {
        "live": False # Simulated environment usually? Or just list all?
    }
    
    # Try listing contracts
    try:
        print(f"Sending request to {url}...")
        response = requests.post(url, headers=headers, json=payload)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                print("✅ Topstep API Connection Successful!")
                contracts = data.get("contracts", [])
                print(f"Found {len(contracts)} available contracts.")
                # Print first 5
                for c in contracts[:5]:
                    print(f" - {c['name']} (ID: {c['id']})")
            else:
                print(f"❌ API returned success=False: {data}")
        else:
            print(f"❌ HTTP Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    check_contracts()
