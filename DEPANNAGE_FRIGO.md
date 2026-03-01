# DÉPANNAGE: Mon Frigo n'affiche rien

## ✅ Backend vérifié - FONCTIONNE
- L'endpoint `/api/fridge/` retourne bien **50 items**
- La structure est correcte: `{"success": true, "items": [...]}`
- Le serveur est opérationnel sur `http://localhost:8001`

## 🔍 Diagnostic du problème

Le backend fonctionne, donc le problème vient du **navigateur**:

### Problème #1: Cache du navigateur (TRÈS FRÉQUENT)
Le navigateur a peut-être mis en cache l'ancienne version du code qui utilisait `data.data` au lieu de `data.items`.

**SOLUTION:**
1. **Ouvrez l'application** `http://localhost:8001`
2. **Videz le cache:**
   - **Chrome/Edge**: Ctrl+Shift+Delete → Cocher "Images et fichiers en cache" → Effacer
   - **Firefox**: Ctrl+Shift+Delete → Cocher "Cache" → Effacer maintenant
3. **Rechargez FORT**: Ctrl+F5 (ou Ctrl+Shift+R)

### Problème #2: Erreur JavaScript silencieuse
Une erreur JavaScript empêche le code de s'exécuter.

**SOLUTION:**
1. **Ouvrez la console** (F12)
2. **Allez dans l'onglet "Mon Frigo"**
3. **Cherchez des erreurs en rouge** dans la console
4. Si vous voyez une erreur, **copiez-la ici**

### Problème #3: Le serveur ne tourne pas sur le bon port

**VÉRIFICATION:**
1. Le serveur doit tourner sur `http://localhost:8001`
2. L'application doit être ouverte sur `http://localhost:8001`
3. **PAS sur** `http://127.0.0.1:8000` ou un autre port

## 🧪 Tests de diagnostic

### Test 1: Backend direct (FAIT ✅)
```bash
python test_simple_frigo.py
```
**Résultat:** ✅ 50 items retournés

### Test 2: Frontend isolé
**Instructions:**
1. Ouvrez `http://localhost:8001/test_frigo_frontend.html` dans votre navigateur
2. Vous devriez voir une page avec des statuts verts
3. Si des statuts rouges apparaissent, **notez le message d'erreur**

### Test 3: Console JavaScript
1. Ouvrez `http://localhost:8001` (l'application principale)
2. Appuyez sur **F12** pour ouvrir les outils développeur
3. Allez dans l'onglet **Console**
4. Cliquez sur "Mon Frigo" dans l'application
5. **Regardez les messages dans la console:**
   - **Messages verts/bleus** = OK
   - **Messages rouges** = ERREUR (copiez le message)

### Test 4: Network (Réseau)
1. **F12** → Onglet **Network** (Réseau)
2. Cliquez sur "Mon Frigo"
3. Cherchez la requête `/api/fridge/`
4. Vérifiez:
   - **Status:** Doit être 200
   - **Response:** Doit contenir `"items":[...]`

## 📝 Actions correctives

### Action 1: Vider le cache (À FAIRE EN PREMIER)
```
1. Ctrl+Shift+Delete
2. Cocher "Cache" et "Images en cache"
3. Vider
4. Fermer le navigateur complètement
5. Rouvrir et aller sur http://localhost:8001
6. Ctrl+F5 pour forcer le rechargement
```

### Action 2: Vérifier que tous les fichiers JS sont chargés
Dans la console (F12), tapez:
```javascript
console.log('FrigoScan:', FrigoScan);
console.log('FrigoScan.Fridge:', FrigoScan.Fridge);
console.log('FrigoScan.Fridge.load:', FrigoScan.Fridge?.load);
```

**Résultat attendu:**
- `FrigoScan: Object {...}`
- `FrigoScan.Fridge: Object {...}`
- `FrigoScan.Fridge.load: function()`

**Si undefined:** Le fichier `fridge.js` n'est pas chargé → vérifier l'index.html

### Action 3: Forcer le rechargement de fridge.js
Ajoutez un paramètre de version dans l'URL:
1. Éditez `index.html` ligne 805
2. Changez:
   ```html
   <script src="/static/js/fridge.js"></script>
   ```
   En:
   ```html
   <script src="/static/js/fridge.js?v=2"></script>
   ```
3. Sauvegardez et rechargez

### Action 4: Test manuel dans la console
Dans F12 → Console, tapez:
```javascript
fetch('http://localhost:8001/api/fridge/')
  .then(r => r.json())
  .then(data => {
    console.log('Success:', data.success);
    console.log('Items count:', data.items?.length);
    console.log('First item:', data.items?.[0]);
  })
  .catch(err => console.error('Error:', err));
```

**Si ça fonctionne:** Le problème est dans le code fridge.js
**Si ça échoue:** Problème réseau/CORS

## 🎯 Solution la plus probable

**CACHE DU NAVIGATEUR** (95% des cas)

1. **Fermez complètement le navigateur**
2. **Rouvrez-le**
3. **Videz le cache** (Ctrl+Shift+Delete)
4. **Allez sur** `http://localhost:8001`
5. **Rechargez fort** (Ctrl+F5)
6. **Testez "Mon Frigo"**

Si ça ne marche toujours pas:
- Ouvrez F12 → Console
- Copiez TOUS les messages rouges
- Envoyez-les pour diagnostic

## 📞 Données à fournir si le problème persiste

Si après toutes ces étapes le problème persiste, fournissez:

1. **Navigateur utilisé:** Chrome/Firefox/Edge/Safari + version
2. **URL dans la barre d'adresse:** (localhost:8001? 127.0.0.1:8000?)
3. **Messages d'erreur console:** (Copie complète des erreurs rouges)
4. **Résultat du Test 2:** (test_frigo_frontend.html affiche quoi?)
5. **Console Network:** La requête /api/fridge/ retourne quoi? (Status + Response)

---

## ✅ Checklist rapide

- [ ] Serveur démarré sur port 8001
- [ ] Application ouverte sur http://localhost:8001
- [ ] Cache navigateur vidé
- [ ] Rechargement fort (Ctrl+F5)
- [ ] Console JavaScript vérifiée (F12)
- [ ] test_frigo_frontend.html testé
- [ ] Onglet Network vérifié
