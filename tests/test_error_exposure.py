"""
Test 1: Vérifier que les erreurs ne révèlent pas la stacktrace en production
"""
import requests
import os
import sys

BASE_URL = os.getenv("TEST_URL", "http://localhost:8000")
TIMEOUT = 10

def test_error_exposure():
    """Trigger une erreur et vérifier que la stacktrace est masquée."""
    
    print("🧪 Test 1: Stack Trace Exposure")
    print("=" * 60)
    
    try:
        # Essayer une requête invalide pour trigger une erreur
        resp = requests.get(
            f"{BASE_URL}/api/recipes/search?q=",
            timeout=TIMEOUT
        )
        
        print(f"Status: {resp.status_code}")
        
        try:
            data = resp.json()
            error_str = str(data)
            
            print(f"Response: {error_str[:200]}...")
            
            # Chercher les signes d'une stacktrace exposée
            bad_signs = [
                "Traceback",
                'File "',
                "raise ",
                "line ",
                "in ",
                "python",
                "exec",
            ]
            
            exposed = False
            for sign in bad_signs:
                if sign.lower() in error_str.lower():
                    print(f"❌ FAIL: Found '{sign}' in error response")
                    exposed = True
            
            if not exposed:
                print("✅ PASS: Stack traces correctly masked")
                return True
            else:
                print("❌ FAIL: Stack trace is exposed!")
                return False
                
        except Exception as e:
            print(f"❌ Error parsing response: {e}")
            return False
            
    except Exception as e:
        print(f"⚠️  Connection error: {e}")
        print("Make sure server is running on http://localhost:8000")
        return False

if __name__ == "__main__":
    result = test_error_exposure()
    print("=" * 60)
    sys.exit(0 if result else 1)
