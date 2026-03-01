"""
Test 4: Vérifier que la pagination fonctionne
"""
import requests
import os
import sys

BASE_URL = os.getenv("TEST_URL", "http://localhost:8000")
TIMEOUT = 10

def test_pagination():
    """Test basic pagination."""
    
    print("🧪 Test 4: Pagination")
    print("=" * 60)
    
    try:
        # Page 1 avec limit 10
        print("\nFetching /api/fridge?page=1&limit=10...")
        
        resp = requests.get(
            f"{BASE_URL}/api/fridge?page=1&limit=10",
            timeout=TIMEOUT
        )
        
        print(f"Status: {resp.status_code}")
        
        if resp.status_code != 200:
            print(f"❌ FAIL: Got status {resp.status_code}")
            print(f"Response: {resp.text[:200]}")
            return False
        
        data = resp.json()
        print(f"Response keys: {list(data.keys())}")
        
        # ✅ ATTENDU:
        # {
        #   "data": [...],
        #   "page": 1,
        #   "limit": 10,
        #   "total": 42,
        #   "pages": 5
        # }
        
        expected_keys = {"data", "page", "limit", "total", "pages"}
        actual_keys = set(data.keys())
        
        if not expected_keys.issubset(actual_keys):
            print(f"❌ FAIL: Missing keys {expected_keys - actual_keys}")
            print(f"Got keys: {actual_keys}")
            return False
        
        print("✅ Required pagination fields present")
        print(f"   - page: {data['page']}")
        print(f"   - limit: {data['limit']}")
        print(f"   - total: {data['total']}")
        print(f"   - pages: {data['pages']}")
        print(f"   - items returned: {len(data['data'])}")
        
        # Vérifier les valeurs
        if data['page'] != 1:
            print(f"❌ FAIL: page should be 1, got {data['page']}")
            return False
        
        if data['limit'] != 10:
            print(f"❌ FAIL: limit should be 10, got {data['limit']}")
            return False
        
        if len(data['data']) > data['limit']:
            print(f"❌ FAIL: returned {len(data['data'])} items but limit is {data['limit']}")
            return False
        
        # Test limit invalide
        print("\nTesting limit validation (limit=1000)...")
        resp = requests.get(
            f"{BASE_URL}/api/fridge?page=1&limit=1000",
            timeout=TIMEOUT
        )
        
        if resp.status_code == 422:  # Validation error
            print("✅ PASS: Limit max (500) enforced")
        else:
            print(f"⚠️ WARNING: limit=1000 accepted (status {resp.status_code})")
            if resp.status_code == 200:
                data = resp.json()
                if data.get('limit', 1000) > 500:
                    print("❌ FAIL: limit > 500 should be rejected")
                    return False
        
        print("\n✅ PASS: Pagination working correctly")
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Exception - {e}")
        return False

if __name__ == "__main__":
    result = test_pagination()
    print("=" * 60)
    sys.exit(0 if result else 1)
