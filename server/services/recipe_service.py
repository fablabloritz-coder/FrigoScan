"""
FrigoScan — Service de recettes.
Recherche de recettes en ligne (Marmiton API).
Calcul du score de correspondance avec le contenu du frigo.
"""

import httpx
import json
import logging
import re
from pathlib import Path
from typing import Optional

from .marmiton_service import (
    search_marmiton_recipes,
    get_random_marmiton_recipes,
    get_marmiton_categories,
)

logger = logging.getLogger("frigoscan.recipes")

MEALDB_SEARCH = "https://www.themealdb.com/api/json/v1/1/search.php"
MEALDB_LOOKUP = "https://www.themealdb.com/api/json/v1/1/lookup.php"
MEALDB_RANDOM = "https://www.themealdb.com/api/json/v1/1/random.php"
MEALDB_FILTER = "https://www.themealdb.com/api/json/v1/1/filter.php"
MEALDB_CATEGORIES = "https://www.themealdb.com/api/json/v1/1/list.php?c=list"
TIMEOUT = 15.0

# API de traduction gratuite MyMemory
TRANSLATION_API = "https://api.mymemory.translated.net/get"
TRANSLATION_TIMEOUT = 3.0

# Dictionnaire de traductions de titres courants EN -> FR
RECIPE_TITLES_FR = {
    "chicken curry": "curry de poulet",
    "chicken fried rice": "riz frit au poulet",
    "beef bourguignon": "boeuf bourguignon",
    "beef stew": "ragoût de boeuf",
    "fish and chips": "poisson frit et frites",
    "fish tacos": "tacos au poisson",
    "pork chops": "côtelettes de porc",
    "lamb roast": "rôti d'agneau",
    "spaghetti carbonara": "spaghetti carbonara",
    "lasagne": "lasagne",
    "pizza margherita": "pizza margherita",
    "grilled vegetables": "legumes grilles",
    "vegetable stir fry": "saute de legumes",
    "caesar salad": "salade cesar",
    "greek salad": "salade grecque",
    "french onion soup": "soupe à l'oignon",
    "mushroom soup": "soupe aux champignons",
    "tomato soup": "soupe à la tomate",
    "chocolate cake": "gateau au chocolat",
    "carrot cake": "gateau aux carottes",
    "apple pie": "tarte aux pommes",
    "cheesecake": "gateau fromage",
    "tiramisu": "tiramisu",
    "brownies": "brownies",
    "ice cream": "glace",
    "pancakes": "crepes",
    "waffles": "gaufres",
    "omelette": "omelette",
    "scrambled eggs": "oeufs brouilles",
    "french toast": "pain perdu",
    "breakfast": "petit-dejeuner",
    "salmon": "saumon",
    "tuna": "thon",
    "shrimp": "crevettes",
    "mussels": "moules",
    "paella": "paella",
    "risotto": "risotto",
    "couscous": "couscous",
    "tajine": "tajine",
    "ramen": "ramen",
    "pad thai": "pad thai",
    "thai green curry": "curry vert thai",
    "tom yum": "tom yum",
    "butter chicken": "poulet au beurre",
    "tandoori chicken": "poulet tandoori",
    "samosa": "samoussa",
    "naan": "naan",
    "biryani": "biryani",
    "falafel": "falafel",
    "hummus": "houmous",
    "shawarma": "shawarma",
    "tempura": "tempura",
    "sushi": "sushi",
    "dim sum": "dim sum",
    "peking duck": "canard de pekin",
    "dumplings": "raviolis",
    "goulash": "goulasch",
    "pierogi": "pierogis",
    "borscht": "bortsch",
    "croissant": "croissant",
    "baguette": "baguette",
    "macaron": "macaron",
    "eclair": "eclair",
    "mille-feuille": "mille-feuille",
}

LOCAL_RECIPES_PATH = Path(__file__).parent.parent / "data" / "local_recipes.json"

# ---- Traduction anglais → français ------------------------------------------------

async def _translate_text_api(text: str, source_lang: str = "en", target_lang: str = "fr") -> str:
    """
    Traduit un texte via l'API MyMemory (gratuite, sans clé).
    Retourne le texte original en cas d'erreur.
    """
    if not text or not text.strip():
        return text
    
    text_lower = text.lower().strip()
    
    # Vérifier le dictionnaire de fallback d'abord
    if text_lower in RECIPE_TITLES_FR:
        return RECIPE_TITLES_FR[text_lower]
    
    # Cherche un mot-clé dans le titre
    for en_key, fr_value in RECIPE_TITLES_FR.items():
        if en_key in text_lower:
            # Remplacer le mot-clé par sa traduction
            translated = text
            for word_en in en_key.split():
                for key, val in RECIPE_TITLES_FR.items():
                    if word_en in key:
                        # Trouver les mots en français correspondants
                        translated = translated.replace(word_en, val.split()[0] if val.split() else val)
                        break
            if translated != text:
                return translated
    
    try:
        async with httpx.AsyncClient(timeout=TRANSLATION_TIMEOUT) as client:
            params = {
                "q": text,
                "langpair": f"{source_lang}|{target_lang}"
            }
            resp = await client.get(TRANSLATION_API, params=params)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("responseStatus") == 200:
                    translated = data.get("responseData", {}).get("translatedText", "")
                    if translated and translated.strip() and translated != text:
                        return translated
    except Exception as e:
        logger.warning(f"Erreur traduction API '{text}': {e}")
    
    # En cas d'erreur, retourner l'original
    return text


# Mapping des catégories TheMealDB → français
CATEGORY_FR = {
    "Beef": "Bœuf", "Breakfast": "Petit-déjeuner", "Chicken": "Poulet",
    "Dessert": "Dessert", "Goat": "Chèvre", "Lamb": "Agneau",
    "Miscellaneous": "Divers", "Pasta": "Pâtes", "Pork": "Porc",
    "Seafood": "Fruits de mer", "Side": "Accompagnement", "Starter": "Entrée",
    "Vegan": "Végan", "Vegetarian": "Végétarien",
}
CATEGORY_EN = {v: k for k, v in CATEGORY_FR.items()}  # reverse

# Dictionnaire d'ingrédients EN→FR fréquents
INGREDIENT_FR = {
    "chicken": "poulet", "chicken breast": "blanc de poulet", "chicken thighs": "cuisses de poulet",
    "beef": "bœuf", "pork": "porc", "lamb": "agneau", "salmon": "saumon",
    "tuna": "thon", "shrimp": "crevettes", "prawns": "crevettes",
    "egg": "œuf", "eggs": "œufs", "butter": "beurre", "oil": "huile",
    "olive oil": "huile d'olive", "vegetable oil": "huile végétale",
    "salt": "sel", "pepper": "poivre", "sugar": "sucre", "flour": "farine",
    "milk": "lait", "cream": "crème", "heavy cream": "crème épaisse",
    "sour cream": "crème aigre", "cheese": "fromage", "parmesan cheese": "parmesan",
    "cheddar cheese": "cheddar", "mozzarella": "mozzarella",
    "onion": "oignon", "onions": "oignons", "garlic": "ail", "garlic clove": "gousse d'ail",
    "garlic cloves": "gousses d'ail", "tomato": "tomate", "tomatoes": "tomates",
    "potato": "pomme de terre", "potatoes": "pommes de terre",
    "carrot": "carotte", "carrots": "carottes",
    "celery": "céleri", "mushrooms": "champignons", "mushroom": "champignon",
    "spinach": "épinards", "broccoli": "brocoli", "zucchini": "courgette",
    "bell pepper": "poivron", "red pepper": "poivron rouge", "green pepper": "poivron vert",
    "lettuce": "laitue", "cucumber": "concombre", "avocado": "avocat",
    "lemon": "citron", "lemon juice": "jus de citron", "lime": "citron vert",
    "orange": "orange", "apple": "pomme", "banana": "banane",
    "rice": "riz", "pasta": "pâtes", "noodles": "nouilles", "bread": "pain",
    "spaghetti": "spaghetti", "penne": "penne", "macaroni": "macaroni",
    "water": "eau", "stock": "bouillon", "chicken stock": "bouillon de poulet",
    "beef stock": "bouillon de bœuf", "vegetable stock": "bouillon de légumes",
    "wine": "vin", "red wine": "vin rouge", "white wine": "vin blanc",
    "soy sauce": "sauce soja", "tomato sauce": "sauce tomate",
    "tomato paste": "concentré de tomate", "tomato puree": "purée de tomate",
    "worcestershire sauce": "sauce Worcestershire", "hot sauce": "sauce piquante",
    "mustard": "moutarde", "ketchup": "ketchup", "mayonnaise": "mayonnaise",
    "vinegar": "vinaigre", "balsamic vinegar": "vinaigre balsamique",
    "honey": "miel", "maple syrup": "sirop d'érable",
    "cinnamon": "cannelle", "cumin": "cumin", "paprika": "paprika",
    "oregano": "origan", "basil": "basilic", "thyme": "thym",
    "rosemary": "romarin", "parsley": "persil", "bay leaf": "feuille de laurier",
    "bay leaves": "feuilles de laurier", "chili": "piment", "ginger": "gingembre",
    "nutmeg": "noix de muscade", "turmeric": "curcuma", "coriander": "coriandre",
    "vanilla": "vanille", "vanilla extract": "extrait de vanille",
    "chocolate": "chocolat", "cocoa": "cacao",
    "baking powder": "levure chimique", "baking soda": "bicarbonate de soude",
    "yeast": "levure", "cornstarch": "fécule de maïs",
    "bacon": "bacon", "ham": "jambon", "sausage": "saucisse",
    "coconut milk": "lait de coco", "coconut": "noix de coco",
    "peanut butter": "beurre de cacahuète", "almonds": "amandes",
    "walnuts": "noix", "cashews": "noix de cajou", "pine nuts": "pignons de pin",
    "sesame oil": "huile de sésame", "sesame seeds": "graines de sésame",
    "breadcrumbs": "chapelure", "plain flour": "farine", "self-raising flour": "farine avec levure",
    "double cream": "crème épaisse", "single cream": "crème liquide",
    "spring onions": "oignons verts", "red onion": "oignon rouge", "red onions": "oignons rouges",
    "cherry tomatoes": "tomates cerise", "chopped tomatoes": "tomates concassées",
    "canned tomatoes": "tomates en conserve", "sun-dried tomatoes": "tomates séchées",
    "green beans": "haricots verts", "kidney beans": "haricots rouges",
    "chickpeas": "pois chiches", "lentils": "lentilles",
    "frozen peas": "petits pois surgelés", "peas": "petits pois",
    "sweetcorn": "maïs doux", "corn": "maïs",
    "chili powder": "poudre de piment", "cayenne pepper": "poivre de Cayenne",
    "black pepper": "poivre noir", "white pepper": "poivre blanc",
    "fish sauce": "sauce poisson (nuoc-mâm)", "oyster sauce": "sauce huître",
    "rice vinegar": "vinaigre de riz", "mirin": "mirin",
    "dried oregano": "origan séché", "dried basil": "basilic séché",
    "dried thyme": "thym séché", "mixed herbs": "herbes mélangées",
    "salsa": "salsa", "pesto": "pesto",
    "cream cheese": "fromage frais", "ricotta": "ricotta",
    "feta": "feta", "gouda": "gouda", "gruyere": "gruyère",
    "whipping cream": "crème fouettée", "ice cream": "glace",
    "brown sugar": "sucre roux", "icing sugar": "sucre glace",
    "caster sugar": "sucre en poudre", "demerara sugar": "cassonade",
    "dark chocolate": "chocolat noir", "white chocolate": "chocolat blanc",
    "milk chocolate": "chocolat au lait",
    "strawberries": "fraises", "blueberries": "myrtilles", "raspberries": "framboises",
    "mango": "mangue", "pineapple": "ananas", "peach": "pêche",
    "apricot": "abricot", "plum": "prune", "pear": "poire", "grapes": "raisin",
    "leek": "poireau", "turnip": "navet", "cabbage": "chou",
    "cauliflower": "chou-fleur", "kale": "chou frisé", "aubergine": "aubergine",
    "eggplant": "aubergine", "courgette": "courgette", "asparagus": "asperges",
    "artichoke": "artichaut", "beetroot": "betterave", "radish": "radis",
    "fennel": "fenouil", "endive": "endive",
    "tofu": "tofu", "tempeh": "tempeh",
}

def _translate_ingredient_name(name_en: str) -> str:
    """Traduit un nom d'ingrédient anglais en français."""
    key = name_en.lower().strip()
    if key in INGREDIENT_FR:
        return INGREDIENT_FR[key]
    # Essayer sans 's' final
    if key.endswith('s') and key[:-1] in INGREDIENT_FR:
        return INGREDIENT_FR[key[:-1]]
    # Retourner tel quel si pas de traduction
    return name_en


def _translate_measure(measure_en: str) -> str:
    """Traduit les unités de mesure anglaises en français."""
    if not measure_en:
        return measure_en
    m = measure_en.strip().lower()
    # Mapping des unités
    units_map = {
        'teaspoon': 'c. à café', 'teaspoons': 'c. à café', 'tsp': 'c. à café',
        'tablespoon': 'c. à soupe', 'tablespoons': 'c. à soupe', 'tbsp': 'c. à soupe',
        'cup': 'tasse', 'cups': 'tasse',
        'ounce': 'once', 'ounces': 'once', 'oz': 'once',
        'pound': 'livre', 'pounds': 'livre', 'lb': 'livre', 'lbs': 'livre',
        'gram': 'g', 'grams': 'g', 'g': 'g', 'gr': 'g',
        'kilogram': 'kg', 'kg': 'kg',
        'milliliter': 'mL', 'milliliters': 'mL', 'ml': 'mL',
        'centiliter': 'cL', 'centiliters': 'cL', 'cl': 'cL',
        'liter': 'L', 'liters': 'L', 'l': 'L',
        'pinch': 'pincée', 'pinches': 'pincée',
        'dash': 'trait', 'dashes': 'trait',
        'splash': 'trait', 'splashes': 'trait',
    }
    # Chercher l'unité (la partie sans les chiffres)
    import re
    match = re.match(r'^([\d.,/\s]*)(.*)$', measure_en.strip())
    if match:
        qty_part = match.group(1).strip()  # e.g. "1/2", "250"
        unit_part = match.group(2).strip().lower()  # e.g. "cup", "ml"
        
        # Traduire l'unité
        translated_unit = units_map.get(unit_part, unit_part)
        
        # Recombiner
        if qty_part:
            return f"{qty_part} {translated_unit}".strip()
        else:
            return translated_unit
    return measure_en


async def _translate_instructions_full(text: str) -> str:
    """
    Traduit les instructions COMPLÈTEMENT de l'anglais vers le français via API.
    Cela évite les mélanges français/anglais.
    """
    if not text or len(text.strip()) < 10:
        return text
    
    # Ne pas traduire si déjà en français (heuristique)
    french_words = ['cuire', 'ajouter', 'mélanger', 'chauffer', 'versez', 'pendant', 
                    'jusqu\'à', 'servir', 'égoutter', 'metter', 'mettre', 'laisser']
    text_lower = text.lower()
    french_count = sum(1 for word in french_words if word in text_lower)
    if french_count > len(french_words) * 0.3:  # Si > 30% de mots français
        return text
    
    try:
        async with httpx.AsyncClient(timeout=TRANSLATION_TIMEOUT) as client:
            params = {
                "q": text,
                "langpair": "en|fr"
            }
            resp = await client.get(TRANSLATION_API, params=params)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("responseStatus") == 200:
                    translated = data.get("responseData", {}).get("translatedText", "")
                    if translated and translated.strip() and translated != text:
                        logger.info(f"Instructions traduites avec succès ({len(text)} chars -> {len(translated)} chars)")
                        return translated
    except Exception as e:
        logger.warning(f"Erreur traduction instructions: {e}")
    
    return text


def _translate_recipe(recipe: dict) -> dict:
    """Traduit une recette normalisée (titre, ingrédients et instructions traduits)."""
    # Traduire le titre (garder l'original si échec)
    # Note : la traduction du titre sera faite de manière asynchrone dans get_recipes_by_category
    
    # Traduire les ingrédients
    try:
        ingredients = json.loads(recipe.get("ingredients_json", "[]"))
        for ing in ingredients:
            if ing.get("name"):
                ing["name"] = _translate_ingredient_name(ing["name"])
            if ing.get("measure"):
                ing["measure"] = _translate_measure(ing["measure"])
        recipe["ingredients_json"] = json.dumps(ingredients)
    except Exception:
        pass

    # Traduire les instructions
    if recipe.get("instructions"):
        recipe["instructions"] = _translate_instructions(recipe["instructions"])

    # Traduire les tags
    try:
        tags = json.loads(recipe.get("tags_json", "[]"))
        recipe["tags_json"] = json.dumps([CATEGORY_FR.get(t, t) for t in tags])
    except Exception:
        pass

    return recipe


async def _translate_recipe_async(recipe: dict) -> dict:
    """
    Traduit une recette de manière asynchrone (titre + ingrédients + instructions).
    Utilise l'API MyMemory pour traduire le titre et les instructions.
    """
    # Traduire le titre via API
    if recipe.get("title"):
        original_title = recipe["title"]
        translated_title = await _translate_text_api(original_title, "en", "fr")
        recipe["title"] = translated_title
    
    # Traduire les ingrédients
    try:
        ingredients = json.loads(recipe.get("ingredients_json", "[]"))
        for ing in ingredients:
            if ing.get("name"):
                ing["name"] = _translate_ingredient_name(ing["name"])
            if ing.get("measure"):
                ing["measure"] = _translate_measure(ing["measure"])
        recipe["ingredients_json"] = json.dumps(ingredients)
    except Exception:
        pass

    # Traduire les instructions COMPLÈTEMENT
    if recipe.get("instructions"):
        recipe["instructions"] = await _translate_instructions_full(recipe["instructions"])

    # Traduire les tags
    try:
        tags = json.loads(recipe.get("tags_json", "[]"))
        recipe["tags_json"] = json.dumps([CATEGORY_FR.get(t, t) for t in tags])
    except Exception:
        pass

    return recipe


# Mapping des catégories françaises pour l'UI
RECIPE_CATEGORIES_FR = [
    # Catégories TheMealDB (filtre par catégorie)
    {"id": "Chicken", "label": "Poulet", "type": "filter"},
    {"id": "Beef", "label": "Bœuf", "type": "filter"},
    {"id": "Pork", "label": "Porc", "type": "filter"},
    {"id": "Lamb", "label": "Agneau", "type": "filter"},
    {"id": "Seafood", "label": "Fruits de mer", "type": "filter"},
    {"id": "Pasta", "label": "Pâtes", "type": "filter"},
    {"id": "Vegetarian", "label": "Végétarien", "type": "filter"},
    {"id": "Vegan", "label": "Végan", "type": "filter"},
    {"id": "Dessert", "label": "Dessert", "type": "filter"},
    {"id": "Breakfast", "label": "Petit-déjeuner", "type": "filter"},
    {"id": "Starter", "label": "Entrée", "type": "filter"},
    {"id": "Side", "label": "Accompagnement", "type": "filter"},
    # Par type de repas (multi-recherche pour plus de variété)
    {"id": "lunch", "label": "Déjeuner", "type": "multi", "terms": ["salad", "sandwich", "soup", "wrap", "omelette", "quiche", "lunch"]},
    {"id": "dinner", "label": "Dîner", "type": "multi", "terms": ["stew", "roast", "curry", "casserole", "pie", "gratin", "dinner"]},
    # Par mot-clé (recherche)
    {"id": "soup", "label": "Soupes", "type": "search"},
    {"id": "salad", "label": "Salades", "type": "search"},
    {"id": "rice", "label": "Riz", "type": "search"},
    {"id": "curry", "label": "Curry", "type": "search"},
    {"id": "cake", "label": "Gâteaux", "type": "search"},
    {"id": "Miscellaneous", "label": "Divers", "type": "filter"},
]


async def get_recipes_by_category(category: str, max_results: int = 12) -> list[dict]:
    """Récupère des recettes par catégorie (filter TheMealDB), recherche ou multi-recherche."""
    import random as rnd

    # Chercher le type de catégorie
    cat_info = next((c for c in RECIPE_CATEGORIES_FR if c["id"] == category), None)
    cat_type = (cat_info or {}).get("type", "filter")

    if cat_type == "search":
        results = await search_recipes_online(category)
        rnd.shuffle(results)
        return results[:max_results]

    if cat_type == "multi":
        terms = (cat_info or {}).get("terms", [category])
        all_recipes = []
        rnd.shuffle(terms)
        for term in terms[:4]:
            results = await search_recipes_online(term)
            all_recipes.extend(results)
        rnd.shuffle(all_recipes)
        seen = set()
        unique = []
        for r in all_recipes:
            t = r.get("title", "").lower().strip()
            if t and t not in seen:
                seen.add(t)
                unique.append(r)
        return unique[:max_results]

    # Type "filter" — catégorie TheMealDB
    recipes = []
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(MEALDB_FILTER, params={"c": category})
            if resp.status_code != 200:
                # Fallback : chercher par mot-clé
                logger.info(f"Catégorie {category} ne retourne rien, fallback recherche")
                return await search_recipes_online(category)
            data = resp.json()
            meals = data.get("meals") or []
            if not meals:
                # Fallback : chercher par mot-clé
                return await search_recipes_online(category)
            rnd.shuffle(meals)
            meals = meals[:max_results + 5]  # Charger plus au cas où certains échouent
            for meal in meals:
                meal_id = meal.get("idMeal")
                if not meal_id:
                    continue
                try:
                    detail_resp = await client.get(MEALDB_LOOKUP, params={"i": meal_id})
                    if detail_resp.status_code == 200:
                        detail_data = detail_resp.json()
                        detail_meals = detail_data.get("meals") or []
                        if detail_meals:
                            recipe = _normalize_mealdb(detail_meals[0])
                            recipe = await _translate_recipe_async(recipe)
                            recipes.append(recipe)
                    if len(recipes) >= max_results:
                        break  # Arrêter une fois qu'on a assez
                except Exception as e:
                    logger.warning(f"Erreur lookup {meal_id}: {e}")
                    continue
    except Exception as e:
        logger.warning(f"Erreur recettes par catégorie {category}: {e}")
        # Dernière tentative : recherche par mot-clé
        try:
            return await search_recipes_online(category)
        except Exception:
            pass
    return recipes[:max_results]


def load_local_recipes() -> list[dict]:
    """Charge les recettes locales de secours."""
    if LOCAL_RECIPES_PATH.exists():
        try:
            with open(LOCAL_RECIPES_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


async def search_recipes_online(query: str) -> list[dict]:
    """Recherche de recettes via Marmiton API."""
    try:
        recipes = await search_marmiton_recipes(query)
        logger.info(f"Marmiton: {len(recipes)} recettes trouvées pour '{query}'")
        return recipes
    except Exception as e:
        logger.warning(f"Erreur recherche recettes Marmiton: {e}")
        return []


async def get_random_recipes(count: int = 5) -> list[dict]:
    """Récupère des recettes aléatoires via Marmiton API."""
    try:
        recipes = await get_random_marmiton_recipes(count)
        logger.info(f"Marmiton: {len(recipes)} recettes aléatoires récupérées")
        return recipes
    except Exception as e:
        logger.warning(f"Erreur recettes aléatoires Marmiton: {e}")
        return []


def _normalize_mealdb(meal: dict) -> dict:
    """Normalise une recette TheMealDB."""
    ingredients = []
    for i in range(1, 21):
        ing = (meal.get(f"strIngredient{i}") or "").strip()
        measure = (meal.get(f"strMeasure{i}") or "").strip()
        if ing:
            ingredients.append({"name": ing, "measure": measure})

    tags = []
    if meal.get("strTags"):
        tags = [t.strip() for t in meal["strTags"].split(",")]
    if meal.get("strCategory"):
        tags.append(meal["strCategory"])

    return {
        "title": meal.get("strMeal", ""),
        "ingredients_json": json.dumps(ingredients),
        "instructions": meal.get("strInstructions", ""),
        "prep_time": 30,
        "cook_time": 30,
        "servings": 4,
        "source_url": meal.get("strSource", ""),
        "image_url": meal.get("strMealThumb", ""),
        "tags_json": json.dumps(tags),
        "diet_tags_json": "[]",
    }


def compute_match_score(recipe_ingredients_json: str, fridge_items: list[dict]) -> tuple[float, list[str]]:
    """
    Calcule le score de correspondance entre une recette et le contenu du frigo.
    Retourne (score 0-100, liste des ingrédients manquants).
    """
    try:
        ingredients = json.loads(recipe_ingredients_json)
    except Exception:
        return (0.0, [])

    if not ingredients:
        return (0.0, [])

    fridge_names = set()
    for item in fridge_items:
        name = (item.get("name") or "").lower().strip()
        fridge_names.add(name)
        # Ajout de variantes sans accents simplifié
        for word in name.split():
            fridge_names.add(word)

    matched = 0
    missing = []
    for ing in ingredients:
        ing_name = (ing.get("name") or "").lower().strip()
        found = False
        for fn in fridge_names:
            if fn in ing_name or ing_name in fn:
                found = True
                break
        if found:
            matched += 1
        else:
            # On ignore les ingrédients basiques (eau, sel, poivre, huile)
            basic = ["water", "salt", "pepper", "oil", "eau", "sel", "poivre", "huile"]
            if any(b in ing_name for b in basic):
                matched += 1
            else:
                missing.append(ing.get("name", ing_name))

    total = len(ingredients)
    score = round((matched / total) * 100, 1) if total > 0 else 0
    return (score, missing)


def _expand_custom_exclusions(custom_exclusions: list[str]) -> list[str]:
    """Transforme les catégories d'exclusion en mots-clés concrets."""
    category_keywords = {
        "viande_rouge": ["beef", "boeuf", "bœuf", "lamb", "agneau", "veau", "steak", "gibier"],
        "viande_blanche": ["chicken", "poulet", "dinde", "lapin", "canard"],
        "porc": ["pork", "porc", "lardon", "lardons", "bacon", "jambon", "saucisson", "saucisse",
                 "chorizo", "rosette", "andouille", "andouillette", "boudin", "pancetta", "rillettes"],
        "charcuterie": ["lardon", "lardons", "saucisson", "jambon", "bacon", "chorizo", "rosette",
                        "rillettes", "pâté", "andouille", "andouillette", "boudin", "salami",
                        "pancetta", "prosciutto", "merguez"],
        "poisson": ["fish", "poisson", "saumon", "thon", "cabillaud", "sardine", "truite",
                     "maquereau", "dorade", "bar", "anchois"],
        "fruits_de_mer": ["shrimp", "crab", "lobster", "crevette", "crabe", "homard",
                          "moule", "huître", "coquille", "langoustine", "crustacé"],
        "oeufs": ["egg", "oeuf", "oeufs"],
        "produits_laitiers": ["milk", "cream", "cheese", "butter", "lait", "crème", "fromage",
                              "beurre", "yaourt", "mozzarella", "emmental", "comté", "camembert",
                              "crème fraîche"],
        "gluten": ["wheat", "flour", "bread", "pasta", "blé", "farine", "pain", "pâte"],
        "alcool": ["wine", "vin", "beer", "bière", "alcool", "alcohol", "rhum", "vodka", "whisky"],
        "sucre": ["sugar", "sucre", "sirop", "caramel", "chocolat"],
        "friture": ["frit", "frites", "friture", "beignet", "panure"],
    }

    expanded = set()
    for excl in custom_exclusions:
        key = excl.lower().replace(" ", "_")
        if key in category_keywords:
            expanded.update(category_keywords[key])
        else:
            # Mot-clé libre
            expanded.add(key)
    return list(expanded)


def filter_by_diet(recipes: list[dict], diets: list[str], allergens: list[str], custom_exclusions: list[str] = None) -> list[dict]:
    """
    Filtre les recettes selon les régimes et allergènes.
    Retourne les recettes compatibles.
    custom_exclusions : liste de mots-clés supplémentaires pour le régime personnalisé.
    """
    if not diets and not allergens:
        return recipes

    allergen_keywords = {
        "gluten": ["wheat", "flour", "bread", "pasta", "blé", "farine", "pain", "pâte"],
        "lactose": ["milk", "cream", "cheese", "butter", "lait", "crème", "fromage", "beurre",
                     "mozzarella", "ricotta", "parmesan", "emmental", "camembert", "comté", 
                     "chèvre", "roquefort", "crème fraîche", "yaourt", "yogurt"],
        "arachides": ["peanut", "arachide", "cacahuète"],
        "fruits_a_coque": ["almond", "walnut", "hazelnut", "amande", "noix", "noisette"],
        "oeufs": ["egg", "oeuf"],
        "poisson": ["fish", "poisson"],
        "crustaces": ["shrimp", "crab", "lobster", "crevette", "crabe", "homard"],
        "soja": ["soy", "soja", "tofu"],
        "celeri": ["celery", "céleri"],
        "moutarde": ["mustard", "moutarde"],
        "sesame": ["sesame", "sésame"],
        "sulfites": ["wine", "vin", "sulfite"],
        "lupin": ["lupin"],
        "mollusques": ["mussel", "oyster", "moule", "huître", "mollusque"],
    }

    diet_exclude = {
        "végétarien": [
            "chicken", "beef", "pork", "lamb", "poulet", "boeuf", "bœuf", "porc",
            "agneau", "viande", "meat", "fish", "poisson", "lardon", "lardons",
            "saucisse", "saucisson", "jambon", "bacon", "canard", "dinde", "veau",
            "lapin", "steak", "merguez", "chorizo", "rosette", "rillettes",
            "pâté", "gibier", "andouille", "andouillette", "boudin",
            "pancetta", "prosciutto", "salami", "oxtail", "queue",
            "steak haché", "ground beef", "hachis", "salmon", "saumon", "tuna", "thon",
            "shrimp", "crevette", "crevettes", "crabe", "crab", "lobster", "homard",
            "mussel", "moule", "moules", "huître", "oyster", "seiche", "calamar",
            "mollusque", "fruits de mer", "seafood", "squid", "poulpe",
        ],
        "végan": [
            "chicken", "beef", "pork", "lamb", "poulet", "boeuf", "bœuf", "porc",
            "agneau", "viande", "meat", "fish", "poisson", "lardon", "lardons",
            "saucisse", "saucisson", "jambon", "bacon", "canard", "dinde", "veau",
            "lapin", "steak", "merguez", "chorizo", "rosette", "rillettes",
            "pâté", "gibier", "andouille", "andouillette", "boudin",
            "pancetta", "prosciutto", "salami",
            "milk", "cream", "cheese", "butter", "egg", "honey",
            "lait", "crème", "fromage", "beurre", "oeuf", "oeufs", "miel",
            "yaourt", "yogurt", "mozzarella", "emmental", "comté", "camembert",
            "crème fraîche",
            # Crustacés et mollusques
            "shrimp", "crevette", "crevettes", "crabe", "crab", "lobster", "homard",
            "mussel", "moule", "moules", "huître", "oyster", "seiche", "calamar",
            "mollusque", "fruits de mer", "seafood",
        ],
        "pesco_végétarien": [
            "chicken", "beef", "pork", "lamb", "poulet", "boeuf", "bœuf", "porc",
            "agneau", "viande", "meat", "lardon", "lardons",
            "saucisse", "saucisson", "jambon", "bacon", "canard", "dinde", "veau",
            "lapin", "steak", "merguez", "chorizo", "rosette", "rillettes",
            "pâté", "gibier", "andouille", "andouillette", "boudin",
            "pancetta", "prosciutto", "salami",
        ],
        "flexitarien": [
            "beef", "boeuf", "bœuf", "lamb", "agneau", "veau",
            "steak", "gibier", "oxtail", "queue",
        ], 
        "sans_gluten": allergen_keywords.get("gluten", []),
        "sans_lactose": allergen_keywords.get("lactose", []),
        "halal": [
            "pork", "porc", "lard", "lardon", "lardons", "bacon", "ham", "jambon",
            "saucisson", "rosette", "rillettes", "chorizo", "andouille", "andouillette",
            "boudin", "pancetta", "prosciutto", "salami",
            "wine", "vin", "alcool", "alcohol", "beer", "bière",
        ],
        "casher": ["pork", "porc", "shellfish", "crustacé", "lardon", "lardons"],
    }

    filtered = []
    for recipe in recipes:
        ingredients_str = recipe.get("ingredients_json", "").lower()
        title_str = recipe.get("title", "").lower()
        search_str = ingredients_str + " " + title_str
        is_ok = True

        # Vérifier régimes
        for diet in diets:
            diet_key = diet.lower().replace(" ", "_")

            # Régime personnalisé : utiliser les exclusions custom
            if diet_key == "régime_personnalisé" and custom_exclusions:
                expanded = _expand_custom_exclusions(custom_exclusions)
                for word in expanded:
                    if word.lower() in search_str:
                        is_ok = False
                        break
            else:
                excluded = diet_exclude.get(diet_key, [])
                for word in excluded:
                    if word in search_str:
                        is_ok = False
                        break
            if not is_ok:
                break

        # Vérifier allergènes
        if is_ok:
            for allergen in allergens:
                allergen_key = allergen.lower().replace(" ", "_")
                keywords = allergen_keywords.get(allergen_key, [allergen.lower()])
                for kw in keywords:
                    if kw in ingredients_str:
                        is_ok = False
                        break
                if not is_ok:
                    break

        if is_ok:
            filtered.append(recipe)

    return filtered


def suggest_alternatives(missing_ingredient: str) -> list[str]:
    """Suggère des alternatives pour un ingrédient manquant."""
    alternatives_map = {
        "butter": ["huile d'olive", "margarine", "huile de coco"],
        "beurre": ["huile d'olive", "margarine", "huile de coco"],
        "cream": ["lait de coco", "crème de soja", "yaourt"],
        "crème": ["lait de coco", "crème de soja", "yaourt"],
        "milk": ["lait d'amande", "lait de soja", "lait d'avoine"],
        "lait": ["lait d'amande", "lait de soja", "lait d'avoine"],
        "egg": ["compote de pommes", "graines de chia", "banane"],
        "oeuf": ["compote de pommes", "graines de chia", "banane"],
        "flour": ["farine de riz", "fécule de maïs", "farine de sarrasin"],
        "farine": ["farine de riz", "fécule de maïs", "farine de sarrasin"],
        "chicken": ["tofu", "tempeh", "seitan"],
        "poulet": ["tofu", "tempeh", "seitan"],
        "beef": ["lentilles", "champignons", "protéines de soja"],
        "boeuf": ["lentilles", "champignons", "protéines de soja"],
        "rice": ["quinoa", "boulgour", "couscous"],
        "riz": ["quinoa", "boulgour", "couscous"],
        "pasta": ["nouilles de riz", "spirales de courgette", "gnocchi"],
        "pâtes": ["nouilles de riz", "spirales de courgette", "gnocchi"],
    }
    key = missing_ingredient.lower().strip()
    for k, v in alternatives_map.items():
        if k in key or key in k:
            return v
    return []
