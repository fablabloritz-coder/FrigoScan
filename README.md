# 🧊 FrigoScan

> **Refonte complète v2.0** — Cette version est une réécriture intégrale de la première version du projet, repensée de zéro à partir du cahier des charges.

**FrigoScan** est une application web tactile de gestion de frigo, optimisée pour Surface Pro, tablettes et PC. Elle facilite l'ajout, le suivi et la gestion des produits alimentaires, propose des recettes adaptées, aide à limiter le gaspillage, et accompagne l'utilisateur dans l'organisation de ses courses et repas.

![FrigoScan](images/logo_frigoscan.png)

---

## ✨ Fonctionnalités

### 📷 Scan rapide
- Scan par **webcam** ou **douchette USB** (code-barres EAN)
- Multi-caméra, résolution et focus configurables
- Bip sonore configurable (fréquence, volume)
- Recherche automatique via **Open Food Facts** (nom, marque, nutrition, image)
- Panier temporaire avant transfert au frigo
- Saisie vocale de la DLC

### ➕ Ajout manuel
- 15 catégories d'aliments avec 150+ produits prédéfinis
- Grille tactile avec emojis, saisie rapide de quantité et DLC estimée
- Possibilité d'ajouter des produits personnalisés dans chaque catégorie
- Personnalisation des icônes (emojis) depuis les réglages

### 🧊 Gestion du frigo
- Liste complète : nom, image, date d'ajout, DLC, catégorie
- Filtres : tout, bientôt périmés, DLC dépassée
- Tri : date d'ajout, DLC, nom, catégorie
- Actions rapides : consommer, prolonger DLC, supprimer

### 🍳 Recettes & Suggestions
- Suggestions basées sur le contenu du frigo avec **score de correspondance**
- Sources : **TheMealDB** (en ligne) + base locale de secours (12 recettes françaises)
- Filtrage par régime alimentaire (végétarien, végan, pesco-végétarien, halal, casher, sans gluten, sans lactose, régime personnalisé)
- Affichage visuel des ingrédients disponibles/manquants
- Ajout des ingrédients manquants à la liste de courses
- Détection des allergènes
- Sauvegarde de recettes favorites

### 🌿 Produits de saison
- Fruits et légumes de saison en France, mois par mois
- Grille tactile avec emojis et catégories

### 🛒 Liste de courses
- Ajout manuel ou automatique (stocks bas, menu de la semaine)
- Gestion des articles achetés/restants

### 📊 Statistiques
- KPI : produits consommés, gaspillage
- Graphiques : top produits, par catégorie, par jour, par mois

### ⚙️ Réglages
- Profil alimentaire : régimes (multi-sélection), allergènes, régime personnalisé
- Configuration scanner : caméra, résolution, bip, intervalle
- Personnalisation des icônes d'ajout manuel
- Export/import (JSON, CSV), sauvegarde/restauration BDD
- Thème sombre/clair
- Zone dangereuse : vider le frigo, réinitialiser l'application

---

## 🏗️ Architecture technique

| Couche | Technologie |
|--------|-------------|
| **Backend** | Python 3.10+ / FastAPI / Uvicorn |
| **Base de données** | SQLite (mode WAL) |
| **Frontend** | HTML5 / CSS3 / JavaScript vanilla (SPA) |
| **Scan** | html5-qrcode (webcam) + support douchette USB |
| **API produits** | Open Food Facts (gratuit, open-source) |
| **API recettes** | TheMealDB (gratuit) |
| **Icônes** | Font Awesome 6.5.1 |

### Structure du projet

```
FrigoScan/
├── index.html                 # SPA principale
├── start.bat                  # Script de lancement Windows
├── requirements.txt           # Dépendances Python
├── server/
│   ├── main.py               # Point d'entrée FastAPI
│   ├── database.py           # Schéma SQLite, helpers
│   ├── models.py             # Modèles Pydantic
│   ├── routers/              # 8 routers API
│   │   ├── scan.py           # Scan code-barres
│   │   ├── fridge.py         # Gestion du frigo
│   │   ├── recipes.py        # Recettes
│   │   ├── shopping.py       # Liste de courses
│   │   ├── stats.py          # Statistiques
│   │   ├── settings.py       # Réglages
│   │   ├── seasonal.py       # Produits de saison
│   │   └── export_import.py  # Export/Import
│   ├── services/             # Services métier
│   │   ├── openfoodfacts.py  # API Open Food Facts
│   │   ├── recipe_service.py # API TheMealDB + filtres
│   │   └── seasonal_service.py
│   └── data/
│       ├── seasonal_products.json  # Produits de saison (France)
│       └── local_recipes.json      # Recettes locales de secours
└── static/
    ├── css/style.css         # CSS responsive, dark/light
    └── js/
        ├── app.js            # Core SPA, navigation, API
        ├── scanner.js        # Scan webcam/douchette
        ├── manual-add.js     # Ajout manuel par catégorie
        ├── fridge.js         # Affichage frigo
        ├── recipes.js        # Recherche/suggestions recettes
        ├── seasonal.js       # Produits de saison
        ├── shopping.js       # Liste de courses
        ├── stats.js          # Statistiques
        └── settings.js       # Réglages
```

---

## 🚀 Installation & Lancement

### Prérequis
- **Python 3.10+** installé et dans le PATH
- Connexion internet (pour le premier `pip install` et les API en ligne)

### Lancement rapide (Windows)
```bash
# Double-cliquer sur start.bat
# Ou depuis un terminal :
start.bat
```

Le script `start.bat` :
1. Vérifie et libère le port 8000
2. Crée un environnement virtuel Python si nécessaire
3. Installe les dépendances
4. Lance le serveur sur http://localhost:8000
5. Ouvre le navigateur automatiquement

### Lancement manuel
```bash
# Créer l'environnement virtuel
python -m venv venv
venv\Scripts\activate

# Installer les dépendances
pip install -r requirements.txt

# Lancer le serveur
uvicorn server.main:app --host 0.0.0.0 --port 8000
```

Accéder à l'application : **http://localhost:8000**

---

## 📡 API

L'application expose une API REST complète :

| Endpoint | Description |
|----------|-------------|
| `GET /api/scan/barcode/{code}` | Recherche produit par code-barres |
| `GET/POST /api/fridge/` | Liste / Ajoute des produits au frigo |
| `POST /api/fridge/{id}/consume` | Consommer un produit |
| `GET /api/recipes/suggest` | Suggestions de recettes |
| `GET /api/seasonal/` | Produits de saison |
| `GET/POST /api/shopping/` | Liste de courses |
| `GET /api/stats/summary` | Statistiques de consommation |
| `GET/PUT /api/settings/` | Réglages utilisateur |
| `GET /api/export/all/json` | Export complet |

Documentation interactive : **http://localhost:8000/docs**

---

## 📋 Cahier des charges

Le développement suit le [cahier des charges](CAHIER_DES_CHARGES.txt) qui détaille l'ensemble des fonctionnalités, contraintes et choix techniques du projet.

---

## 📝 Licence

Projet développé par [FabLab Loritz](https://github.com/fablabloritz-coder).

---

## 🔄 Historique

- **v2.0** — Refonte complète. Réécriture intégrale du frontend et du backend. Nouvelle architecture SPA, nouveaux services, nouvelle base de données, interface tactile repensée.
- **v1.0** — Première version (obsolète).
