"""
FrigoScan — Service de recettes.
Recherche de recettes en ligne (TheMealDB) et base locale de secours.
Calcul du score de correspondance avec le contenu du frigo.
"""

import httpx
import json
import logging
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger("frigoscan.recipes")

MEALDB_SEARCH = "https://www.themealdb.com/api/json/v1/1/search.php"
MEALDB_LOOKUP = "https://www.themealdb.com/api/json/v1/1/lookup.php"
MEALDB_RANDOM = "https://www.themealdb.com/api/json/v1/1/random.php"
MEALDB_FILTER = "https://www.themealdb.com/api/json/v1/1/filter.php"
MEALDB_CATEGORIES = "https://www.themealdb.com/api/json/v1/1/list.php?c=list"
TIMEOUT = 8.0

LOCAL_RECIPES_PATH = Path(__file__).parent.parent / "data" / "local_recipes.json"

# ---- Traduction anglais → français ------------------------------------------------

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


def _translate_instructions(text: str) -> str:
    """Traduction basique des instructions anglaises → français (mots-clés courants)."""
    if not text:
        return text
    replacements = [
        ("Preheat the oven to", "Préchauffer le four à"),
        ("Preheat oven to", "Préchauffer le four à"),
        ("Heat the oil", "Chauffer l'huile"),
        ("Heat oil", "Chauffer l'huile"),
        ("Heat the butter", "Chauffer le beurre"),
        ("Add the", "Ajouter les"), ("Add", "Ajouter"),
        ("Mix well", "Bien mélanger"), ("Mix together", "Mélanger ensemble"),
        ("Stir in", "Incorporer"), ("Stir well", "Bien remuer"),
        ("Season with salt and pepper", "Assaisonner de sel et poivre"),
        ("Season to taste", "Assaisonner à votre goût"),
        ("Bring to a boil", "Porter à ébullition"),
        ("Bring to the boil", "Porter à ébullition"),
        ("Simmer for", "Laisser mijoter pendant"),
        ("Simmer", "Laisser mijoter"),
        ("Cook for", "Cuire pendant"), ("Cook until", "Cuire jusqu'à ce que"),
        ("Bake for", "Cuire au four pendant"), ("Bake", "Cuire au four"),
        ("Fry", "Faire frire"), ("Fry until", "Faire frire jusqu'à"),
        ("Sauté", "Faire sauter"), ("Sautee", "Faire sauter"),
        ("Chop", "Hacher"), ("Dice", "Couper en dés"),
        ("Slice", "Trancher"), ("Mince", "Émincer"),
        ("Peel", "Éplucher"), ("Grate", "Râper"),
        ("Drain", "Égoutter"), ("Rinse", "Rincer"),
        ("Serve", "Servir"), ("Serve immediately", "Servir immédiatement"),
        ("Serve hot", "Servir chaud"), ("Serve cold", "Servir froid"),
        ("Garnish with", "Garnir de"), ("Top with", "Garnir de"),
        ("Let it rest", "Laisser reposer"), ("Let rest", "Laisser reposer"),
        ("Cover and", "Couvrir et"), ("Remove from heat", "Retirer du feu"),
        ("Set aside", "Réserver"), ("Meanwhile", "Pendant ce temps"),
        ("In a large bowl", "Dans un grand bol"),
        ("In a large pan", "Dans une grande poêle"),
        ("In a large pot", "Dans une grande casserole"),
        ("In a medium bowl", "Dans un bol moyen"),
        ("In a small bowl", "Dans un petit bol"),
        ("minutes", "minutes"), ("hours", "heures"),
        ("until golden", "jusqu'à ce que ce soit doré"),
        ("until crispy", "jusqu'à ce que ce soit croustillant"),
        ("until tender", "jusqu'à ce que ce soit tendre"),
        ("until soft", "jusqu'à ce que ce soit tendre"),
    ]
    result = text
    for en, fr in replacements:
        result = re.sub(re.escape(en), fr, result, flags=re.IGNORECASE)
    return result


def _translate_recipe(recipe: dict) -> dict:
    """Traduit une recette normalisée (titre inchangé, ingrédients et instructions traduits)."""
    # Traduire les ingrédients
    try:
        ingredients = json.loads(recipe.get("ingredients_json", "[]"))
        for ing in ingredients:
            if ing.get("name"):
                ing["name"] = _translate_ingredient_name(ing["name"])
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
                return []
            data = resp.json()
            meals = data.get("meals") or []
            rnd.shuffle(meals)
            meals = meals[:max_results]
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
                            recipe = _translate_recipe(recipe)
                            recipes.append(recipe)
                except Exception:
                    continue
    except Exception as e:
        logger.warning(f"Erreur recettes par catégorie: {e}")
    return recipes


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
    """Recherche de recettes via TheMealDB."""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(MEALDB_SEARCH, params={"s": query})
            if resp.status_code != 200:
                return []
            data = resp.json()
            meals = data.get("meals") or []
            return [_translate_recipe(_normalize_mealdb(m)) for m in meals]
    except Exception as e:
        logger.warning(f"Erreur recherche recettes: {e}")
        return []


async def get_random_recipes(count: int = 5) -> list[dict]:
    """Récupère des recettes aléatoires."""
    recipes = []
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            for _ in range(count):
                resp = await client.get(MEALDB_RANDOM)
                if resp.status_code == 200:
                    data = resp.json()
                    meals = data.get("meals") or []
                    for m in meals:
                        recipes.append(_translate_recipe(_normalize_mealdb(m)))
    except Exception as e:
        logger.warning(f"Erreur recettes aléatoires: {e}")
    return recipes


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
        "lactose": ["milk", "cream", "cheese", "butter", "lait", "crème", "fromage", "beurre"],
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
            "pancetta", "prosciutto", "salami",
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
            "steak", "gibier",
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
