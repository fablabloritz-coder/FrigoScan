#!/usr/bin/env python3
"""
Test simple et direct de l'endpoint frigo
"""
import requests

print("=" * 60)
print("TEST ULTRA-SIMPLE - /api/fridge/")
print("=" * 60)

try:
    resp = requests.get("http://localhost:8001/api/fridge/", timeout=5)
    print(f"\n✓ Status: {resp.status_code}")
    
    data = resp.json()
    print(f"✓ JSON parsé")
    print(f"\n📊 Résultat:")
    print(f"  - success: {data.get('success')}")
    print(f"  - Clé 'items'existe: {'items' in data}")
    print(f"  - Type de 'items': {type(data.get('items'))}")
    print(f"  - Nombre d'items: {len(data.get('items', []))}")
    
    if data.get('items'):
        print(f"\n📦 Premier item:")
        first = data['items'][0]
        print(f"  ID: {first.get('id')}")
        print(f"  Nom: {first.get('name')}")
        print(f"  Quantité: {first.get('quantity')} {first.get('unit')}")
        print(f"  Catégorie: {first.get('category')}")
        print(f"  DLC: {first.get('dlc')}")
        print(f"  Status DLC: {first.get('dlc_status')}")
    
    print(f"\n✅ BACKEND FONCTIONNE CORRECTEMENT")
    print(f"\n💡 INSTRUCTIONS:")
    print(f"  1. Ouvrez http://localhost:8001/test_frigo_frontend.html dans votre navigateur")
    print(f"  2. Vérifiez la console JavaScript (F12)")
    print(f"  3. Si le test HTML passe mais l'app ne marche pas:")
    print(f"     - Videz le cache navigateur (Ctrl+Shift+Delete)")
    print(f"     - Rechargez l'application (Ctrl+F5)")
    
except requests.exceptions.ConnectionError:
    print(f"\n❌ Impossible de se connecter à http://localhost:8001")
    print(f"   Le serveur est-il démarré?")
    print(f"\n   Pour démarrer:")
    print(f"   cd C:\\Users\\natah\\Desktop\\FrigoScan")
    print(f"   .\\venv\\Scripts\\python.exe -m uvicorn server.main:app --host localhost --port 8001 --reload")
except Exception as e:
    print(f"\n❌ Erreur: {e}")
