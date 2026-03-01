"""
FrigoScan — Router Menu de la semaine.
"""

from fastapi import APIRouter, HTTPException
from server.database import get_db, dict_from_row, rows_to_list
from server.models import MenuEntry
from datetime import date, timedelta, datetime
import json

router = APIRouter(prefix="/api/menus", tags=["Menu semaine"])


def _get_week_start(d: date = None) -> str:
    """Retourne le lundi de la semaine."""
    if d is None:
        d = date.today()
    monday = d - timedelta(days=d.weekday())
    return monday.isoformat()


@router.get("/")
def get_current_menu(week_start: str = None):
    """Récupère le menu de la semaine courante."""
    if week_start is None:
        week_start = _get_week_start()
    db = get_db()
    try:
        rows = db.execute(
            "SELECT * FROM weekly_menu WHERE week_start = ? ORDER BY day_of_week, meal_type",
            (week_start,)
        ).fetchall()
        menu = rows_to_list(rows)
        return {"success": True, "week_start": week_start, "menu": menu}
    finally:
        db.close()


@router.post("/")
def add_menu_entry(entry: MenuEntry):
    """Ajoute une entrée au menu."""
    db = get_db()
    try:
        # Vérifier si une entrée existe déjà pour ce créneau
        existing = db.execute(
            "SELECT id FROM weekly_menu WHERE week_start=? AND day_of_week=? AND meal_type=?",
            (entry.week_start, entry.day_of_week, entry.meal_type)
        ).fetchone()
        if existing:
            db.execute(
                "UPDATE weekly_menu SET recipe_id=?, recipe_title=?, notes=?, servings=? WHERE id=?",
                (entry.recipe_id, entry.recipe_title, entry.notes, entry.servings, existing["id"])
            )
        else:
            db.execute(
                """INSERT INTO weekly_menu (week_start, day_of_week, meal_type, recipe_id, recipe_title, notes, servings)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (entry.week_start, entry.day_of_week, entry.meal_type,
                 entry.recipe_id, entry.recipe_title, entry.notes, entry.servings)
            )
        db.commit()
        return {"success": True, "message": "Menu mis à jour."}
    finally:
        db.close()


@router.patch("/{entry_id}/pin")
def toggle_pin(entry_id: int):
    """Basculer l'état épinglé d'une entrée du menu."""
    db = get_db()
    try:
        row = db.execute("SELECT id, is_pinned FROM weekly_menu WHERE id=?", (entry_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Entrée introuvable.")
        new_val = 0 if row["is_pinned"] else 1
        db.execute("UPDATE weekly_menu SET is_pinned=? WHERE id=?", (new_val, entry_id))
        db.commit()
        return {"success": True, "is_pinned": bool(new_val), "message": "Épinglé !" if new_val else "Désépinglé."}
    finally:
        db.close()


@router.patch("/swap")
def swap_entries(payload: dict):
    """Échange deux entrées du menu (drag & drop)."""
    id_a = payload.get("id_a")
    id_b = payload.get("id_b")
    if not id_a or not id_b:
        raise HTTPException(400, "Deux IDs requis.")
    db = get_db()
    try:
        a = db.execute("SELECT * FROM weekly_menu WHERE id=?", (id_a,)).fetchone()
        b = db.execute("SELECT * FROM weekly_menu WHERE id=?", (id_b,)).fetchone()
        if not a or not b:
            raise HTTPException(404, "Entrée(s) introuvable(s).")
        # Échanger recipe_id, recipe_title, notes, servings, is_pinned, recipe_data_json
        db.execute(
            "UPDATE weekly_menu SET recipe_id=?, recipe_title=?, notes=?, servings=?, is_pinned=?, recipe_data_json=? WHERE id=?",
            (b["recipe_id"], b["recipe_title"], b["notes"], b["servings"], b["is_pinned"], b["recipe_data_json"], id_a)
        )
        db.execute(
            "UPDATE weekly_menu SET recipe_id=?, recipe_title=?, notes=?, servings=?, is_pinned=?, recipe_data_json=? WHERE id=?",
            (a["recipe_id"], a["recipe_title"], a["notes"], a["servings"], a["is_pinned"], a["recipe_data_json"], id_b)
        )
        db.commit()
        return {"success": True, "message": "Entrées échangées."}
    finally:
        db.close()


@router.get("/{entry_id}/recipe")
def get_menu_recipe_detail(entry_id: int):
    """Récupère le détail complet d'une recette du menu."""
    db = get_db()
    try:
        entry = db.execute("SELECT * FROM weekly_menu WHERE id=?", (entry_id,)).fetchone()
        if not entry:
            raise HTTPException(404, "Entrée introuvable.")
        recipe_id = entry["recipe_id"]
        if recipe_id:
            recipe = db.execute("SELECT * FROM recipes WHERE id=?", (recipe_id,)).fetchone()
            if recipe:
                return {"success": True, "recipe": dict_from_row(recipe)}
        # Essayer recipe_data_json (recettes issues de TheMealDB)
        if entry["recipe_data_json"]:
            try:
                recipe_data = json.loads(entry["recipe_data_json"])
                return {"success": True, "recipe": recipe_data}
            except Exception:
                pass
        # Pas de recette en base — retourner les infos basiques
        return {
            "success": True,
            "recipe": {
                "title": entry["recipe_title"] or "Repas libre",
                "ingredients_json": "[]",
                "instructions": "",
                "servings": entry["servings"] or 4,
                "image_url": "",
            }
        }
    finally:
        db.close()


@router.post("/generate")
async def generate_menu(week_start: str = None, servings: int = 4, mode: str = "fridge"):
    """
    Génère automatiquement un menu de la semaine.
    mode='fridge' : priorise les recettes correspondant au frigo.
    mode='scratch' : ignore le frigo, utilise juste les réglages de régime.
    """
    if week_start is None:
        week_start = _get_week_start()

    db = get_db()
    try:
        # Récupérer réglages
        diets_row = db.execute("SELECT value FROM settings WHERE key='diets'").fetchone()
        allergens_row = db.execute("SELECT value FROM settings WHERE key='allergens'").fetchone()
        diets = json.loads(diets_row["value"]) if diets_row else []
        allergens = json.loads(allergens_row["value"]) if allergens_row else []

        # Exclusions personnalisées
        custom_excl_row = db.execute("SELECT value FROM settings WHERE key='custom_exclusions'").fetchone()
        custom_exclusions = json.loads(custom_excl_row["value"]) if custom_excl_row else []

        # Recettes bannies
        banned_rows = db.execute("SELECT LOWER(title) as title FROM banned_recipes").fetchall()
        banned_titles = set(r["title"] for r in banned_rows)

        from server.services.recipe_service import (
            load_local_recipes, compute_match_score, filter_by_diet,
            get_random_recipes, search_recipes_online
        )

        # Récupérer recettes locales (base + fichier)
        db_recipes = rows_to_list(db.execute("SELECT * FROM recipes").fetchall())
        local_recipes = load_local_recipes()
        all_recipes = db_recipes + local_recipes

        if mode == "fridge":
            # Récupérer contenu du frigo
            fridge_items = rows_to_list(
                db.execute("SELECT * FROM fridge_items WHERE status='active'").fetchall()
            )

            # Si le frigo est trop vide, compléter avec des recettes en ligne
            if fridge_items:
                fridge_names = [item["name"] for item in fridge_items[:8]]
                import random as rnd
                rnd.shuffle(fridge_names)
                for name in fridge_names[:4]:
                    online = await search_recipes_online(name)
                    all_recipes.extend(online)
                # Ajouter aussi des recettes aléatoires pour plus de variété
                extra = await get_random_recipes(10)
                all_recipes.extend(extra)

            # Filtrer par régime
            all_recipes = filter_by_diet(all_recipes, diets, allergens, custom_exclusions)

            # Scorer par rapport au frigo
            for recipe in all_recipes:
                score, missing = compute_match_score(recipe.get("ingredients_json", "[]"), fridge_items)
                recipe["match_score"] = score

            all_recipes.sort(key=lambda r: r.get("match_score", 0), reverse=True)
        else:
            # Mode scratch : pas de score frigo, juste filtrer par régime
            # Chercher beaucoup de recettes en ligne pour de la variété
            random_recipes = await get_random_recipes(20)
            all_recipes.extend(random_recipes)

            # Chercher aussi des termes variés pour plus de diversité
            variety_terms = [
                "poulet", "salade", "pâtes", "soupe", "poisson", "riz", "légumes",
                "curry", "tarte", "gratin", "pizza", "steak", "cake", "pie",
                "noodle", "sandwich", "sushi", "vegetable", "seafood", "dessert",
                "wrap", "grill", "roast", "pancake", "omelette", "quiche",
            ]
            import random as rnd
            rnd.shuffle(variety_terms)
            for term in variety_terms[:4]:
                online = await search_recipes_online(term)
                all_recipes.extend(online)

            all_recipes = filter_by_diet(all_recipes, diets, allergens, custom_exclusions)

        # Dédupliquer par titre
        seen_titles = set()
        unique_recipes = []
        for r in all_recipes:
            title = r.get("title", "").lower().strip()
            if title and title not in seen_titles and title not in banned_titles:
                seen_titles.add(title)
                unique_recipes.append(r)
        all_recipes = unique_recipes

        # S'assurer qu'on a assez de recettes (14 slots = 7 jours x 2 repas)
        if len(all_recipes) < 14:
            extra = await get_random_recipes(max(0, 20 - len(all_recipes)))
            for r in extra:
                title = r.get("title", "").lower().strip()
                if title and title not in seen_titles:
                    seen_titles.add(title)
                    all_recipes.append(r)

        # Mélanger un peu pour éviter toujours le même ordre
        import random as rnd
        if mode == "fridge" and len(all_recipes) > 14:
            # Garder les meilleurs mais mélanger les ex-aequo
            top = all_recipes[:6]
            rest = all_recipes[6:]
            rnd.shuffle(rest)
            all_recipes = top + rest
        elif mode == "scratch":
            rnd.shuffle(all_recipes)

        # Effacer le menu existant pour cette semaine (sauf entrées épinglées)
        pinned_rows = db.execute(
            "SELECT * FROM weekly_menu WHERE week_start = ? AND is_pinned = 1",
            (week_start,)
        ).fetchall()
        pinned_slots = set()
        pinned_titles = set()
        for pr in pinned_rows:
            pinned_slots.add((pr["day_of_week"], pr["meal_type"]))
            if pr["recipe_title"]:
                pinned_titles.add(pr["recipe_title"].lower().strip())

        db.execute("DELETE FROM weekly_menu WHERE week_start = ? AND is_pinned = 0", (week_start,))

        # Générer le menu : déjeuner + dîner pour 7 jours (sauter les slots épinglés)
        menu = []
        recipe_idx = 0
        meal_types = ["lunch", "dinner"]
        for day in range(7):
            for meal in meal_types:
                if (day, meal) in pinned_slots:
                    # Ce slot est épinglé, ne pas le toucher
                    continue
                recipe = all_recipes[recipe_idx % len(all_recipes)] if all_recipes else None
                if recipe:
                    title = recipe.get("title", "Repas libre")
                    # Éviter de réutiliser un titre déjà épinglé
                    if title.lower().strip() in pinned_titles:
                        recipe_idx += 1
                        recipe = all_recipes[recipe_idx % len(all_recipes)] if all_recipes else None
                        title = recipe.get("title", "Repas libre") if recipe else "Repas libre"
                    recipe_id = recipe.get("id") if recipe else None
                    recipe_data = json.dumps(recipe) if recipe else None
                    db.execute(
                        """INSERT INTO weekly_menu (week_start, day_of_week, meal_type, recipe_id, recipe_title, servings, recipe_data_json)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (week_start, day, meal, recipe_id, title, servings, recipe_data)
                    )
                    menu.append({"day_of_week": day, "meal_type": meal, "recipe_title": title, "recipe_id": recipe_id})
                    recipe_idx += 1
                else:
                    db.execute(
                        """INSERT INTO weekly_menu (week_start, day_of_week, meal_type, recipe_title, servings)
                           VALUES (?, ?, ?, ?, ?)""",
                        (week_start, day, meal, "Repas libre", servings)
                    )
                    menu.append({"day_of_week": day, "meal_type": meal, "recipe_title": "Repas libre"})

        db.commit()
        mode_label = "selon le frigo" if mode == "fridge" else "de zéro"
        return {"success": True, "week_start": week_start, "menu": menu,
                "message": f"Menu généré {mode_label} — {len(all_recipes)} recettes disponibles."}
    finally:
        db.close()


@router.delete("/{entry_id}")
def delete_menu_entry(entry_id: int):
    db = get_db()
    try:
        db.execute("DELETE FROM weekly_menu WHERE id = ?", (entry_id,))
        db.commit()
        return {"success": True, "message": "Entrée supprimée."}
    finally:
        db.close()


@router.delete("/week/{week_start}")
def clear_week_menu(week_start: str):
    db = get_db()
    try:
        db.execute("DELETE FROM weekly_menu WHERE week_start = ?", (week_start,))
        db.commit()
        return {"success": True, "message": "Menu de la semaine vidé."}
    finally:
        db.close()


@router.get("/shopping-list")
def generate_shopping_from_menu(week_start: str = None):
    """Génère une liste de courses à partir du menu de la semaine."""
    if week_start is None:
        week_start = _get_week_start()

    db = get_db()
    try:
        menu_rows = db.execute(
            "SELECT * FROM weekly_menu WHERE week_start = ?", (week_start,)
        ).fetchall()

        fridge_items = rows_to_list(
            db.execute("SELECT * FROM fridge_items WHERE status='active'").fetchall()
        )
        fridge_names = set(item["name"].lower() for item in fridge_items)

        basic_ingredients = {"water", "salt", "pepper", "oil", "eau", "sel", "poivre", "huile"}
        needed = {}
        for row in menu_rows:
            ingredients = None
            recipe_id = row["recipe_id"]
            if recipe_id:
                recipe = db.execute("SELECT * FROM recipes WHERE id=?", (recipe_id,)).fetchone()
                if recipe:
                    try:
                        ingredients = json.loads(recipe["ingredients_json"])
                    except Exception:
                        pass
            # Fallback : recipe_data_json (recettes TheMealDB)
            if ingredients is None and row["recipe_data_json"]:
                try:
                    recipe_data = json.loads(row["recipe_data_json"])
                    ingredients = json.loads(recipe_data.get("ingredients_json", "[]"))
                except Exception:
                    pass
            if ingredients:
                for ing in ingredients:
                    name = ing.get("name", "").strip()
                    if name and name.lower() not in fridge_names and name.lower() not in basic_ingredients:
                        needed[name.lower()] = {"name": name, "measure": ing.get("measure", "")}

        shopping = list(needed.values())
        return {"success": True, "shopping_list": shopping, "count": len(shopping)}
    finally:
        db.close()
