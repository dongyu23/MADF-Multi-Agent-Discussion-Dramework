import requests
import json
import time
import sys

# Configuration
BASE_URL = "http://127.0.0.1:8000/api/v1"
# Assuming we have a test user or register one
USERNAME = "test_verifier"
PASSWORD = "password123"

def print_pass(msg):
    print(f"✅ PASS: {msg}")

def print_fail(msg):
    print(f"❌ FAIL: {msg}")
    # Don't exit immediately to allow other tests to run if possible, 
    # but for critical failures we might want to stop.
    
def get_auth_token():
    # 1. Register (ignore if exists)
    try:
        requests.post(f"{BASE_URL}/auth/register", json={
            "username": USERNAME, 
            "password": PASSWORD,
            "role": "god" # Need god role for some operations
        })
    except:
        pass
        
    # 2. Login
    resp = requests.post(f"{BASE_URL}/auth/login", data={
        "username": USERNAME,
        "password": PASSWORD
    })
    if resp.status_code != 200:
        print_fail(f"Login failed: {resp.text}")
        sys.exit(1)
        
    return resp.json()["access_token"]

def verify_persona_lifecycle():
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    print("\n--- 1. Testing Persona Creation & Visibility ---")
    
    # B. Verify Visibility (List) - Immediate check to verify cache invalidation
    # First, let's force a cache population by calling list before creation
    requests.get(f"{BASE_URL}/personas/", headers=headers)
    
    # Now create
    persona_data = {
        "name": f"TestPersona_{int(time.time())}",
        "title": "Tester",
        "bio": "A test persona",
        "theories": ["Testing", "Automation"],
        "stance": "Neutral",
        "is_public": False
    }
    
    create_resp = requests.post(f"{BASE_URL}/personas/", json=persona_data, headers=headers)
    if create_resp.status_code != 200:
        print_fail(f"Create persona failed: {create_resp.text}")
        return
        
    created_persona = create_resp.json()
    pid = created_persona["id"]
    print_pass(f"Created persona ID {pid}")

    # Wait for DB consistency?
    time.sleep(1)

    # Now check list again - should be updated if cache was invalidated
    list_resp = requests.get(f"{BASE_URL}/personas/", headers=headers)
    personas = list_resp.json()
    print(f"DEBUG: Found {len(personas)} personas in list")
    
    found = any(p["id"] == pid for p in personas)
    if found:
        print_pass("New persona found in list (Cache invalidated correctly)")
    else:
        print_fail(f"New persona NOT found in list (Cache invalidation failed). List IDs: {[p['id'] for p in personas]}")
    
    found = any(p["id"] == pid for p in personas)
    if found:
        print_pass("New persona found in list (Cache invalidated correctly)")
    else:
        print_fail("New persona NOT found in list (Cache invalidation failed)")
        
    print("\n--- 2. Testing Persona Deletion & Idempotency ---")
    
    # C. Delete Persona
    del_resp = requests.delete(f"{BASE_URL}/personas/{pid}", headers=headers)
    if del_resp.status_code == 200:
        print_pass("Delete request successful")
    else:
        print_fail(f"Delete request failed: {del_resp.text}")
        
    # D. Verify Deletion (List)
    list_resp_after = requests.get(f"{BASE_URL}/personas/", headers=headers)
    personas_after = list_resp_after.json()
    found_after = any(p["id"] == pid for p in personas_after)
    
    if not found_after:
        print_pass("Persona removed from list")
    else:
        print_fail("Persona still exists in list after deletion")
        
    # E. Verify Idempotency (Delete again)
    del_again = requests.delete(f"{BASE_URL}/personas/{pid}", headers=headers)
    if del_again.status_code == 200:
        print_pass("Idempotent delete successful (returned 200 OK)")
        if "already deleted" in del_again.text:
            print_pass("Correctly identified as already deleted")
    else:
        print_fail(f"Idempotent delete failed with status {del_again.status_code}")

if __name__ == "__main__":
    try:
        verify_persona_lifecycle()
    except Exception as e:
        print_fail(f"Test script crashed: {e}")
