"""
Test 2: Vérifier que la validation des inputs est correcte
"""
import requests
import os
import sys

BASE_URL = os.getenv("TEST_URL", "http://localhost:8000")
TIMEOUT = 10

TESTS = [
    # (description, payload, should_accept)
    (
        "Nom vide",
        {"name": "", "quantity": 1},
        False  # Devrait être rejeté
    ),
    (
        "Nom trop long (>200 chars)",
        {"name": "x" * 201, "quantity": 1},
        False
    ),
    (
        "Quantité négative",
        {"name": "Lait", "quantity": -5},
        False
    ),
    (
        "Quantité trop grande (>10000)",
        {"name": "Lait", "quantity": 10001},
        False
    ),
    (
        "Format DLC invalide",
        {"name": "Lait", "dlc": "2025-13-40"},
        False
    ),
    (
        "Nom avec accents (valide)",
        {"name": "Lait écrémé à la vanille", "quantity": 1},
        True
    ),
    (
        "Quantité float (valide)",
        {"name": "Lait", "quantity": 1.5},
        True
    ),
    (
        "Nom normal (valide)",
        {"name": "Lait demi-écrémé", "quantity": 2, "dlc": "2025-12-25"},
        True
    ),
]

def test_input_validation():
    """Teste la validation d'input sur chaque cas."""
    
    print("🧪 Test 2: Input Validation")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for desc, payload, should_accept in TESTS:
        try:
            resp = requests.post(
                f"{BASE_URL}/api/fridge",
                json=payload,
                timeout=TIMEOUT
            )
            
            is_success = resp.status_code == 200
            
            if is_success == should_accept:
                status = "✅ PASS"
                passed += 1
            else:
                status = "❌ FAIL"
                failed += 1
                
            expected = "ACCEPT" if should_accept else "REJECT"
            actual = "ACCEPT" if is_success else "REJECT"
            
            print(f"{status}: {desc}")
            print(f"       Expected: {expected}, Got: {actual} (Status: {resp.status_code})")
            
            if not is_success:
                try:
                    error_msg = resp.json().get("detail", resp.text)
                    print(f"       Error: {error_msg[:100]}")
                except:
                    print(f"       Error: {resp.text[:100]}")
        
        except Exception as e:
            print(f"❌ FAIL: {desc}")
            print(f"       Exception: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"📊 Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("✅ PASS: Validation correcte")
        return True
    else:
        print("⚠️  FAIL: Validation incomplète")
        return False

if __name__ == "__main__":
    result = test_input_validation()
    print("=" * 60)
    sys.exit(0 if result else 1)
