"""
Tests d'intégration des endpoints Marmiton API
Valide que les endpoints /api/recipes retournent les recettes Marmiton normalisées
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "server"))

import httpx


async def test_endpoints():
    """Teste les principaux endpoints."""
    
    base_url = "http://127.0.0.1:8000"
    timeout = 10
    
    print("\n" + "="*70)
    print("TEST DES ENDPOINTS RECIPE AVEC MARMITON")
    print("="*70 + "\n")
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            
            # Test 1: Recherche de recettes
            print("1. Recherche de recettes (/api/recipes/search?q=pâtes)")
            try:
                response = await client.get(f"{base_url}/api/recipes/search?q=pâtes")
                data = response.json()
                
                if response.status_code == 200:
                    recipes = data.get("recipes", [])
                    print(f"   ✓ Statut: 200")
                    print(f"   ✓ Recettes trouvées: {len(recipes)}")
                    
                    if recipes:
                        recipe = recipes[0]
                        print(f"   ✓ Première recette: {recipe.get('title', 'N/A')}")
                        
                        # Valider le format
                        required_fields = ["id", "title", "ingredients_json", "instructions", "difficulty"]
                        missing = [f for f in required_fields if f not in recipe]
                        if missing:
                            print(f"   ⚠ Champs manquants: {missing}")
                        else:
                            print(f"   ✓ Tous les champs requis présents")
                else:
                    print(f"   ✗ Erreur {response.status_code}: {response.text}")
            except Exception as e:
                print(f"   ✗ Erreur: {e}")
            
            print()
            
            # Test 2: Recettes aléatoires
            print("2. Recettes aléatoires (/api/recipes/suggest/random?max_results=3)")
            try:
                response = await client.get(f"{base_url}/api/recipes/suggest/random?max_results=3")
                data = response.json()
                
                if response.status_code == 200:
                    recipes = data.get("recipes", [])
                    print(f"   ✓ Statut: 200")
                    print(f"   ✓ Recettes retournées: {len(recipes)}")
                    
                    for i, recipe in enumerate(recipes[:2], 1):
                        print(f"   ✓ Recette {i}: {recipe.get('title', 'N/A')}")
                else:
                    print(f"   ✗ Erreur {response.status_code}: {response.text}")
            except Exception as e:
                print(f"   ✗ Erreur: {e}")
            
            print()
            
            # Test 3: Catégories
            print("3. Catégories (/api/recipes/categories)")
            try:
                response = await client.get(f"{base_url}/api/recipes/categories")
                data = response.json()
                
                if response.status_code == 200:
                    categories = data.get("categories", [])
                    print(f"   ✓ Statut: 200")
                    print(f"   ✓ Catégories disponibles: {len(categories)}")
                    if categories:
                        # Les catégories sont des dicts avec id et label
                        cat_names = [c.get("label", c.get("id", "")) for c in categories[:3]]
                        print(f"   ✓ Exemples: {', '.join(cat_names)}")
                else:
                    print(f"   ✗ Erreur {response.status_code}: {response.text}")
            except Exception as e:
                print(f"   ✗ Erreur: {e}")
            
            print()
            
            # Test 4: Recettes par catégorie (si endpoint existe)
            print("4. Vérification du format des ingrédients")
            try:
                response = await client.get(f"{base_url}/api/recipes/search?q=oeufs")
                data = response.json()
                
                if response.status_code == 200:
                    recipes = data.get("recipes", [])
                    
                    if recipes:
                        recipe = recipes[0]
                        try:
                            ingredients = json.loads(recipe["ingredients_json"])
                            print(f"   ✓ Statut: 200")
                            print(f"   ✓ Ingrédients JSON valide pour '{recipe['title']}'")
                            print(f"   ✓ Nombre d'ingrédients: {len(ingredients)}")
                            
                            if ingredients:
                                ing = ingredients[0]
                                print(f"   ✓ Exemple d'ingrédient: {ing}")
                        except json.JSONDecodeError as e:
                            print(f"   ✗ Erreur JSON ingrédients: {e}")
                    else:
                        print(f"   ⚠ Aucune recette trouvée")
                else:
                    print(f"   ✗ Erreur {response.status_code}")
            except Exception as e:
                print(f"   ✗ Erreur: {e}")
            
            print()
            
            # Test 5: Vérification des tags
            print("5. Vérification du format des tags")
            try:
                response = await client.get(f"{base_url}/api/recipes/search?q=dessert")
                data = response.json()
                
                if response.status_code == 200:
                    recipes = data.get("recipes", [])
                    
                    if recipes:
                        recipe = recipes[0]
                        try:
                            tags = json.loads(recipe.get("tags_json", "[]"))
                            print(f"   ✓ Tags JSON valide pour '{recipe['title']}'")
                            print(f"   ✓ Nombre de tags: {len(tags)}")
                            if tags:
                                print(f"   ✓ Exemples de tags: {', '.join(tags[:3])}")
                        except json.JSONDecodeError as e:
                            print(f"   ✗ Erreur JSON tags: {e}")
                    else:
                        print(f"   ⚠ Aucune recette trouvée")
                else:
                    print(f"   ✗ Erreur {response.status_code}")
            except Exception as e:
                print(f"   ✗ Erreur: {e}")
            
    except Exception as e:
        print(f"✗ Erreur globale: {e}")
    
    print("\n" + "="*70)
    print("✓ TESTS DES ENDPOINTS TERMINES")
    print("="*70 + "\n")


if __name__ == "__main__":
    asyncio.run(test_endpoints())
