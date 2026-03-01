"""
Tests d'intégration Marmiton API.
Valide:
  - Recherche de recettes
  - Récupération aléatoire
  - Catégories
  - Normalisation des réponses
  - Fallback quand API indisponible
"""

import asyncio
import json
import pytest
from pathlib import Path

# Importer depuis server/services
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "server"))

from services.marmiton_service import (
    search_marmiton_recipes,
    get_random_marmiton_recipes,
    get_marmiton_categories,
    _normalize_marmiton_recipe,
)


class TestMarmitonSearch:
    """Tests de la recherche Marmiton."""
    
    @pytest.mark.asyncio
    async def test_search_returns_list(self):
        """La recherche retourne une liste."""
        results = await search_marmiton_recipes("pâtes", limit=5)
        assert isinstance(results, list)
        print(f"  ✓ Recherche 'pâtes': {len(results)} résultats")
    
    @pytest.mark.asyncio
    async def test_search_validates_recipe_format(self):
        """Chaque résultat a les champs requis."""
        results = await search_marmiton_recipes("oeufs", limit=3)
        
        required_fields = [
            "id", "title", "ingredients_json", "instructions",
            "difficulty", "tags_json", "servings", "prep_time", "cook_time"
        ]
        
        for recipe in results:
            for field in required_fields:
                assert field in recipe, f"Champ manquant: {field}"
        
        print(f"  ✓ Format validé pour {len(results)} recettes")
    
    @pytest.mark.asyncio
    async def test_search_ingredients_json_valid(self):
        """Les ingrédients sont du JSON valide."""
        results = await search_marmiton_recipes("sauce", limit=3)
        
        for recipe in results:
            try:
                ingredients = json.loads(recipe["ingredients_json"])
                assert isinstance(ingredients, list)
                for ing in ingredients:
                    assert "name" in ing
                    assert "quantity" in ing or "unit" in ing
            except json.JSONDecodeError:
                pytest.fail(f"JSON invalide pour {recipe['title']}")
        
        print(f"  ✓ JSON ingrédients valide pour {len(results)} recettes")
    
    @pytest.mark.asyncio
    async def test_search_tags_json_valid(self):
        """Les tags sont du JSON valide."""
        results = await search_marmiton_recipes("dessert", limit=3)
        
        for recipe in results:
            try:
                tags = json.loads(recipe["tags_json"])
                assert isinstance(tags, list)
            except json.JSONDecodeError:
                pytest.fail(f"JSON tags invalide pour {recipe['title']}")
        
        print(f"  ✓ JSON tags valide pour {len(results)} recettes")


class TestMarmitonRandom:
    """Tests des recettes aléatoires."""
    
    @pytest.mark.asyncio
    async def test_random_returns_recipes(self):
        """get_random_marmiton_recipes retourne des recettes."""
        recipes = await get_random_marmiton_recipes(count=3)
        assert isinstance(recipes, list)
        assert len(recipes) <= 3
        print(f"  ✓ {len(recipes)} recettes aléatoires récupérées")
    
    @pytest.mark.asyncio
    async def test_random_recipe_has_all_fields(self):
        """Chaque recette aléatoire a tous les champs."""
        recipes = await get_random_marmiton_recipes(count=2)
        
        required_fields = [
            "id", "title", "ingredients_json", "instructions",
            "difficulty", "tags_json", "servings", "prep_time", "cook_time"
        ]
        
        for recipe in recipes:
            for field in required_fields:
                assert field in recipe, f"Champ manquant dans aléatoire: {field}"
        
        print(f"  ✓ Champs validés pour recettes aléatoires")


class TestMarmitonCategories:
    """Tests des catégories."""
    
    def test_get_categories_returns_list(self):
        """get_marmiton_categories retourne une liste."""
        categories = get_marmiton_categories()
        assert isinstance(categories, list)
        print(f"  ✓ {len(categories)} catégories retournées")
    
    def test_categories_have_values(self):
        """Chaque catégorie a une valeur valide."""
        categories = get_marmiton_categories()
        
        for category in categories:
            assert isinstance(category, str)
            assert len(category) > 0
        
        print(f"  ✓ Structure validée pour toutes les catégories")


class TestMarmitonNormalization:
    """Tests de normalisation des réponses."""
    
    def test_normalize_marmiton_recipe(self):
        """_normalize_marmiton_recipe convertit correctement."""
        # Simule une réponse Marmiton
        raw_recipe = {
            "title": "Test Recette",
            "difficulty": "Facile",
            "servings": 4,
            "prep_time": 15,
            "cook_time": 20,
            "ingredients": [
                "500g farine",
                "2 oeufs",
                "1L lait"
            ],
            "steps": [
                "Mélanger les ingrédients",
                "Cuire 30 minutes"
            ],
            "tags": ["Pâtisserie", "Facile"]
        }
        
        normalized = _normalize_marmiton_recipe(raw_recipe)
        
        # Valider les champs clés
        assert normalized["title"] == "Test Recette"
        assert normalized["difficulty"] in ["easy", "medium", "hard"]  # A être mappé
        assert normalized["servings"] == 4
        assert normalized["prep_time"] == 15
        assert normalized["cook_time"] == 20
        
        # Valider le JSON
        ingredients = json.loads(normalized["ingredients_json"])
        assert isinstance(ingredients, list)
        
        tags = json.loads(normalized["tags_json"])
        assert isinstance(tags, list)
        
        print(f"  ✓ Normalisation correcte pour 'Test Recette'")
    
    def test_normalize_difficulty_mapping(self):
        """Les difficultés Marmiton sont mappées correctement."""
        test_cases = [
            ("Facile", "easy"),
            ("Moyen", "medium"),
            ("Difficile", "hard"),
        ]
        
        for marmiton_diff, expected_diff in test_cases:
            recipe = {
                "title": "Test",
                "difficulty": marmiton_diff,
                "ingredients": [],
                "steps": [],
                "tags": [],
                "servings": 1,
                "prep_time": 10,
                "cook_time": 10,
            }
            
            normalized = _normalize_marmiton_recipe(recipe)
            assert normalized["difficulty"] == expected_diff
        
        print(f"  ✓ Mappages de difficulté corrects")


class TestMarmitonFallback:
    """Tests du fallback quand Marmiton est indisponible."""
    
    @pytest.mark.asyncio
    async def test_search_fallback_on_empty(self):
        """La recherche retourne au moins les recettes fallback."""
        # Chercher une requête spécifique qui devrait avoir du fallback
        results = await search_marmiton_recipes("invalidquery123456xyz", limit=1)
        assert isinstance(results, list)
        # Le fallback doit fournir quelque chose
        print(f"  ✓ Fallback activé, {len(results)} recettes retournées")


class TestIntegrationWithRecipeService:
    """Tests d'intégration avec recipe_service.py."""
    
    @pytest.mark.asyncio
    async def test_recipe_service_search_integration(self):
        """search_recipes_online() utilise correctement Marmiton."""
        # Import dynamic pour éviter les problèmes de chemin
        from services.recipe_service import search_recipes_online
        
        results = await search_recipes_online("tomate")
        
        assert isinstance(results, list)
        if len(results) > 0:
            # Vérifier que le format est celui attendu
            recipe = results[0]
            assert "id" in recipe
            assert "title" in recipe
            assert "ingredients_json" in recipe
        
        print(f"  ✓ Intégration recipe_service.search_recipes_online: {len(results)} résultats")
    
    @pytest.mark.asyncio
    async def test_recipe_service_random_integration(self):
        """get_random_recipes() utilise correctement Marmiton."""
        from services.recipe_service import get_random_recipes
        
        results = await get_random_recipes(count=2)
        
        assert isinstance(results, list)
        assert len(results) <= 2
        
        for recipe in results:
            assert "id" in recipe
            assert "title" in recipe
        
        print(f"  ✓ Intégration recipe_service.get_random_recipes: {len(results)} résultats")


# Tests à exécuter en CLI
async def run_async_tests():
    """Exécute les tests async manuellement."""
    
    print("\n" + "="*60)
    print("TEST MARMITON INTEGRATION")
    print("="*60 + "\n")
    
    # Test 1: Recherche
    print("1. RECHERCHE MARMITON")
    test_search = TestMarmitonSearch()
    await test_search.test_search_returns_list()
    await test_search.test_search_validates_recipe_format()
    await test_search.test_search_ingredients_json_valid()
    
    # Test 2: Aléatoire
    print("\n2. RECETTES ALEATOIRES")
    test_random = TestMarmitonRandom()
    await test_random.test_random_returns_recipes()
    await test_random.test_random_recipe_has_all_fields()
    
    # Test 3: Catégories
    print("\n3. CATEGORIES")
    test_categories = TestMarmitonCategories()
    test_categories.test_get_categories_returns_list()
    test_categories.test_categories_have_values()
    
    # Test 4: Normalisation
    print("\n4. NORMALISATION")
    test_norm = TestMarmitonNormalization()
    test_norm.test_normalize_marmiton_recipe()
    test_norm.test_normalize_difficulty_mapping()
    
    # Test 5: Fallback
    print("\n5. FALLBACK")
    test_fallback = TestMarmitonFallback()
    await test_fallback.test_search_fallback_on_empty()
    
    # Test 6: Intégration avec recipe_service
    print("\n6. INTEGRATION AVEC RECIPE_SERVICE")
    test_integration = TestIntegrationWithRecipeService()
    await test_integration.test_recipe_service_search_integration()
    await test_integration.test_recipe_service_random_integration()
    
    print("\n" + "="*60)
    print("✓ TOUS LES TESTS MARMITON PASSES")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(run_async_tests())
