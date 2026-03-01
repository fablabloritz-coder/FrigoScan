import json
from pathlib import Path

json_file = Path('server/data/marmiton_fallback.json')
with open(json_file) as f:
    recipes = json.load(f)

print(f'📦 Total recettes: {len(recipes)}')
print(f'🖼️  Recettes avec images: {sum(1 for r in recipes if r.get("image_url"))}')
print()
print('Exemples:')
for i, recipe in enumerate(recipes[:3]):
    print(f'{i+1}. {recipe["title"]}')
    print(f'   Image: {recipe.get("image_url", "manquante")}')
    print()
