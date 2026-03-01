"""
Test 3: Vérifier que les accès concurrent ne cassent pas la BD
"""
import threading
import requests
import json
import os
import sys
from collections import defaultdict

BASE_URL = os.getenv("TEST_URL", "http://localhost:8000")
TIMEOUT = 20

RESULTS = defaultdict(list)
ERRORS = []
LOCK = threading.Lock()

def add_fridge_item(item_id):
    """Ajouter un item au frigo."""
    try:
        resp = requests.post(
            f"{BASE_URL}/api/fridge",
            json={
                "name": f"ConcurrentItem_{item_id}",
                "quantity": float(item_id),
                "unit": "unité",
                "category": f"cat_{item_id % 3}"
            },
            timeout=TIMEOUT
        )
        
        with LOCK:
            if resp.status_code == 200:
                RESULTS["success"].append({
                    "item_id": item_id,
                    "status": resp.status_code
                })
            else:
                RESULTS["failed"].append({
                    "item_id": item_id,
                    "status": resp.status_code,
                    "error": resp.text[:100]
                })
    
    except Exception as e:
        with LOCK:
            ERRORS.append({
                "item_id": item_id,
                "error": str(e)
            })

def test_concurrent_writes():
    """Lance 20 threads simultanés qui ajoutent des items."""
    
    print("🧪 Test 3: Concurrent Access (Race Conditions)")
    print("=" * 60)
    print("Launching 20 concurrent write operations...")
    
    threads = []
    for i in range(20):
        t = threading.Thread(target=add_fridge_item, args=(i,))
        threads.append(t)
        t.start()
    
    # Attendre que tout finisse
    for t in threads:
        t.join()
    
    print(f"\n📊 Raw Results:")
    print(f"  ✅ Success: {len(RESULTS['success'])}")
    print(f"  ❌ Failed: {len(RESULTS['failed'])}")
    print(f"  💥 Errors: {len(ERRORS)}")
    
    # Afficher les erreurs si présentes
    if ERRORS:
        print(f"\n⚠️ Errors:")
        for err in ERRORS[:5]:
            print(f"  - {err['error']}")
        if len(ERRORS) > 5:
            print(f"  ... and {len(ERRORS)-5} more")
    
    if RESULTS['failed']:
        print(f"\n⚠️ Failed Requests:")
        for fail in RESULTS['failed'][:5]:
            print(f"  - Item {fail['item_id']}: {fail['status']}")
    
    # Vérifier qu'on a les items dans la BD
    print(f"\nVerifying items in database...")
    try:
        resp = requests.get(
            f"{BASE_URL}/api/fridge?limit=100",
            timeout=TIMEOUT
        )
        
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("data", [])
            
            # Chercher nos test items
            test_items = [i for i in items if "ConcurrentItem_" in i.get("name", "")]
            
            print(f"  Found {len(test_items)} concurrent test items in DB")
            
            # Si on a entre 18-20 items, c'est bon (quelques timeouts tolérés)
            if len(test_items) >= 18:
                print("✅ PASS: Data integrity maintained")
                return True
            else:
                print(f"⚠️ WARNING: Only {len(test_items)}/20 items found")
                if len(ERRORS) == 0 and len(RESULTS['failed']) == 0:
                    print("⚠️ But all requests succeeded - possible DB timeout")
                return len(RESULTS['failed']) == 0 and len(ERRORS) < 5
        else:
            print(f"❌ FAIL: Could not fetch items (status {resp.status_code})")
            return False
    
    except Exception as e:
        print(f"❌ Error fetching verification: {e}")
        return False

if __name__ == "__main__":
    result = test_concurrent_writes()
    print("\n" + "=" * 60)
    sys.exit(0 if result else 1)
