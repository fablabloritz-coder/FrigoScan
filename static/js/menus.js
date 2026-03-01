/**
 * FrigoScan — Module Menu de la semaine (menus.js)
 * v2.6 — Clic détail, pin, drag & drop, sauvegarder, courses.
 */

(function () {
    const Menus = {};
    FrigoScan.Menus = Menus;

    const DAYS = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche'];
    const MEAL_LABELS = { breakfast: 'Petit-déj', lunch: 'Déjeuner', dinner: 'Dîner', snack: 'Goûter' };

    let currentWeekStart = getMonday(new Date());
    let currentEntries = [];
    let dragSourceId = null;

    function getMonday(d) {
        const date = new Date(d);
        const day = date.getDay();
        const diff = date.getDate() - day + (day === 0 ? -6 : 1);
        date.setDate(diff);
        return date.toISOString().split('T')[0];
    }

    function shiftWeek(offset) {
        const d = new Date(currentWeekStart);
        d.setDate(d.getDate() + offset * 7);
        currentWeekStart = d.toISOString().split('T')[0];
        Menus.load();
    }

    Menus.load = async function () {
        document.getElementById('btn-menu-prev').onclick = () => shiftWeek(-1);
        document.getElementById('btn-menu-next').onclick = () => shiftWeek(1);
        document.getElementById('btn-generate-menu-fridge').onclick = () => generateMenu('fridge');
        document.getElementById('btn-generate-menu-scratch').onclick = () => generateMenu('scratch');
        document.getElementById('btn-clear-menu').onclick = clearWeekMenu;

        const btnShopping = document.getElementById('btn-menu-shopping');
        if (btnShopping) btnShopping.onclick = addAllToShopping;

        const weekDate = new Date(currentWeekStart);
        const options = { day: 'numeric', month: 'long', year: 'numeric' };
        document.getElementById('menu-week-label').textContent =
            `Semaine du ${weekDate.toLocaleDateString('fr-FR', options)}`;

        const data = await FrigoScan.API.get(`/api/menus/?week_start=${currentWeekStart}`);
        currentEntries = data.menu || [];
        renderMenu(currentEntries);
    };

    function renderMenu(entries) {
        const grid = document.getElementById('menu-grid');

        const byDay = {};
        for (let i = 0; i < 7; i++) byDay[i] = {};
        entries.forEach(e => {
            byDay[e.day_of_week] = byDay[e.day_of_week] || {};
            byDay[e.day_of_week][e.meal_type] = e;
        });

        grid.innerHTML = '';

        DAYS.forEach((dayName, idx) => {
            const meals = byDay[idx] || {};
            const mealTypes = ['lunch', 'dinner'];

            const dayCard = document.createElement('div');
            dayCard.className = 'menu-day-card';
            dayCard.innerHTML = `<h4><i class="fas fa-calendar-day"></i> ${dayName}</h4>`;

            mealTypes.forEach(mt => {
                const entry = meals[mt];
                const mealDiv = document.createElement('div');
                mealDiv.className = 'menu-meal' + (entry && entry.is_pinned ? ' pinned' : '');

                if (entry && entry.id) {
                    mealDiv.setAttribute('draggable', 'true');
                    mealDiv.dataset.entryId = entry.id;

                    mealDiv.addEventListener('dragstart', (e) => {
                        dragSourceId = entry.id;
                        mealDiv.classList.add('dragging');
                        e.dataTransfer.effectAllowed = 'move';
                        e.dataTransfer.setData('text/plain', entry.id);
                    });
                    mealDiv.addEventListener('dragend', () => {
                        mealDiv.classList.remove('dragging');
                        document.querySelectorAll('.menu-meal.drag-over').forEach(el => el.classList.remove('drag-over'));
                        dragSourceId = null;
                    });
                    mealDiv.addEventListener('dragover', (e) => {
                        e.preventDefault();
                        e.dataTransfer.dropEffect = 'move';
                        if (String(entry.id) !== String(dragSourceId)) {
                            mealDiv.classList.add('drag-over');
                        }
                    });
                    mealDiv.addEventListener('dragleave', () => {
                        mealDiv.classList.remove('drag-over');
                    });
                    mealDiv.addEventListener('drop', async (e) => {
                        e.preventDefault();
                        mealDiv.classList.remove('drag-over');
                        const fromId = e.dataTransfer.getData('text/plain');
                        if (fromId && String(fromId) !== String(entry.id)) {
                            const res = await FrigoScan.API.patch('/api/menus/swap', { id_a: parseInt(fromId), id_b: entry.id });
                            if (res.success) {
                                FrigoScan.toast('Recettes échangées !', 'success');
                                Menus.load();
                            }
                        }
                    });
                }

                const typeSpan = document.createElement('span');
                typeSpan.className = 'menu-meal-type';
                typeSpan.textContent = MEAL_LABELS[mt] || mt;

                const recipeSpan = document.createElement('span');
                recipeSpan.className = 'menu-meal-recipe';
                recipeSpan.textContent = entry ? entry.recipe_title : '—';

                if (entry && entry.recipe_title && entry.recipe_title !== 'Repas libre') {
                    recipeSpan.style.cursor = 'pointer';
                    recipeSpan.title = 'Cliquer pour voir le détail';
                    recipeSpan.addEventListener('click', (e) => {
                        e.stopPropagation();
                        showMenuRecipeDetail(entry);
                    });
                }

                const actions = document.createElement('div');
                actions.className = 'menu-meal-actions';

                if (entry && entry.id) {
                    const pinBtn = document.createElement('button');
                    pinBtn.className = 'btn btn-sm menu-action-btn' + (entry.is_pinned ? ' pinned' : '');
                    pinBtn.title = entry.is_pinned ? 'Désépingler' : 'Épingler (survit à la régénération)';
                    pinBtn.innerHTML = '<i class="fas fa-thumbtack"></i>';
                    pinBtn.addEventListener('click', async (e) => {
                        e.stopPropagation();
                        const res = await FrigoScan.API.patch(`/api/menus/${entry.id}/pin`);
                        if (res.success) {
                            FrigoScan.toast(res.message, 'success');
                            Menus.load();
                        }
                    });

                    const saveBtn = document.createElement('button');
                    saveBtn.className = 'btn btn-sm menu-action-btn';
                    saveBtn.title = 'Sauvegarder dans Mes recettes';
                    saveBtn.innerHTML = '<i class="fas fa-bookmark"></i>';
                    saveBtn.addEventListener('click', async (e) => {
                        e.stopPropagation();
                        await saveMenuRecipe(entry);
                    });

                    const delBtn = document.createElement('button');
                    delBtn.className = 'btn btn-sm btn-danger menu-action-btn';
                    delBtn.title = 'Supprimer';
                    delBtn.innerHTML = '<i class="fas fa-times"></i>';
                    delBtn.addEventListener('click', async (e) => {
                        e.stopPropagation();
                        await Menus.removeEntry(entry.id);
                    });

                    actions.appendChild(pinBtn);
                    actions.appendChild(saveBtn);
                    actions.appendChild(delBtn);
                }

                mealDiv.appendChild(typeSpan);
                mealDiv.appendChild(recipeSpan);
                mealDiv.appendChild(actions);
                dayCard.appendChild(mealDiv);
            });

            grid.appendChild(dayCard);
        });
    }

    // ---- Détail d'une recette du menu ----
    async function showMenuRecipeDetail(entry) {
        let recipe = null;
        try {
            const data = await FrigoScan.API.get(`/api/menus/${entry.id}/recipe`);
            if (data.success && data.recipe) recipe = data.recipe;
        } catch (e) {}

        if (!recipe) {
            recipe = {
                title: entry.recipe_title || 'Repas libre',
                ingredients_json: '[]',
                instructions: '',
                servings: entry.servings || 4,
                image_url: '',
            };
        }

        const modal = document.getElementById('recipe-detail-modal');
        const content = document.getElementById('recipe-detail-content');
        if (!modal || !content) { FrigoScan.toast('Détail non disponible.', 'warning'); return; }

        let ingredients = [];
        try { ingredients = JSON.parse(recipe.ingredients_json || '[]'); } catch (e) {}

        let tags = [];
        try { tags = JSON.parse(recipe.tags_json || '[]'); } catch (e) {}

        const nbPersons = parseInt(localStorage.getItem('frigoscan-nb-persons') || '4');
        const recipeServings = recipe.servings || 4;
        const portionRatio = nbPersons / recipeServings;

        let fridgeNames = new Set();
        try {
            const fridgeData = await FrigoScan.API.get('/api/fridge/');
            if (fridgeData.success && fridgeData.items) {
                fridgeData.items.forEach(item => {
                    const name = (item.name || '').toLowerCase().trim();
                    fridgeNames.add(name);
                    name.split(' ').forEach(w => { if (w.length > 2) fridgeNames.add(w); });
                });
            }
        } catch (e) {}

        const basicIngredients = ["water", "salt", "pepper", "oil", "eau", "sel", "poivre", "huile"];

        const imgHtml = recipe.image_url
            ? `<img src="${recipe.image_url}" alt="${recipe.title}" style="width:100%;max-height:300px;object-fit:cover;border-radius:var(--radius-sm);margin-bottom:16px;">`
            : '';

        function adjustMeasure(measure) {
            if (!measure || portionRatio === 1) return measure;
            const numMatch = measure.match(/^([\d.,/]+)\s*(.*)/);
            if (numMatch) {
                let num = numMatch[1];
                const rest = numMatch[2];
                if (num.includes('/')) { const p = num.split('/'); num = parseFloat(p[0]) / parseFloat(p[1]); }
                else { num = parseFloat(num.replace(',', '.')); }
                if (!isNaN(num)) { const adj = Math.round(num * portionRatio * 10) / 10; return `${adj} ${rest}`.trim(); }
            }
            return measure;
        }

        function parseMeasure(measure) {
            if (!measure || !measure.trim()) return { qty: 1, unit: 'unité' };
            const m = measure.trim();
            const match = m.match(/^([\d.,/]+)\s*(.*)/);
            if (match) {
                let num = match[1];
                let unitStr = (match[2] || '').trim();
                if (num.includes('/')) { const p = num.split('/'); num = parseFloat(p[0]) / parseFloat(p[1]); }
                else { num = parseFloat(num.replace(',', '.')); }
                if (isNaN(num)) return { qty: 1, unit: m };
                const unitMap = { 'g': 'g', 'gr': 'g', 'kg': 'kg', 'ml': 'mL', 'cl': 'cL', 'l': 'L', 'cup': 'cup', 'cups': 'cup', 'tbsp': 'c. à soupe', 'tsp': 'c. à café', 'oz': 'oz', 'lb': 'lb' };
                return { qty: Math.round(num * 10) / 10, unit: unitMap[unitStr.toLowerCase()] || unitStr || 'unité' };
            }
            return { qty: 1, unit: m || 'unité' };
        }

        const ingredientPills = ingredients.map(ing => {
            const ingName = (ing.name || '').toLowerCase().trim();
            const isBasic = basicIngredients.some(b => ingName.includes(b));
            let isAvailable = isBasic;
            if (!isBasic) { for (const fn of fridgeNames) { if (fn.includes(ingName) || ingName.includes(fn)) { isAvailable = true; break; } } }
            const cls = isAvailable ? 'ingredient-pill available' : 'ingredient-pill missing';
            const icon = isAvailable ? '<i class="fas fa-check"></i>' : '<i class="fas fa-cart-plus"></i>';
            const adjustedMeasure = adjustMeasure(ing.measure);
            const measureText = adjustedMeasure ? `${adjustedMeasure} ` : '';
            const addBtn = !isAvailable
                ? ` <button class="btn-add-ingredient" data-name="${(ing.name || '').replace(/"/g, '&quot;')}" data-measure="${(adjustedMeasure || '').replace(/"/g, '&quot;')}" title="Ajouter aux courses">+</button>`
                : '';
            return `<span class="${cls}">${icon} ${measureText}${ing.name}${addBtn}</span>`;
        }).join('');

        const portionInfo = portionRatio !== 1
            ? `<div style="padding:8px 12px;background:var(--bg-hover);border-radius:var(--radius-sm);margin-bottom:12px;font-size:0.85rem;">
                   <i class="fas fa-info-circle"></i> Quantités ajustées pour <strong>${nbPersons} personnes</strong> (recette originale : ${recipeServings} pers.)
               </div>`
            : '';

        content.innerHTML = `
            ${imgHtml}
            <h2 style="margin-bottom:12px;">${recipe.title}</h2>
            <div style="display:flex;gap:12px;margin-bottom:16px;flex-wrap:wrap;">
                ${(recipe.prep_time || recipe.cook_time) ? `<span class="badge"><i class="fas fa-clock"></i> Prépa: ${recipe.prep_time || 0}min — Cuisson: ${recipe.cook_time || 0}min</span>` : ''}
                <span class="badge"><i class="fas fa-users"></i> ${nbPersons} personnes</span>
            </div>
            ${portionInfo}
            ${tags.length ? `<div style="margin-bottom:12px;">${tags.map(t => `<span class="badge" style="margin:2px;">${t}</span>`).join('')}</div>` : ''}
            ${ingredients.length ? `
                <h3 style="margin-bottom:8px;">Ingrédients</h3>
                <div class="ingredients-pills" style="margin-bottom:16px;">${ingredientPills}</div>
                <div style="font-size:0.78rem;color:var(--text-muted);margin-bottom:16px;">
                    <span class="ingredient-pill available" style="font-size:0.7rem;padding:2px 6px;"><i class="fas fa-check"></i> Dans le frigo</span>
                    <span class="ingredient-pill missing" style="font-size:0.7rem;padding:2px 6px;"><i class="fas fa-cart-plus"></i> Manquant</span>
                </div>
                <button class="btn btn-warning btn-add-all-missing-menu" style="margin-bottom:16px;">
                    <i class="fas fa-cart-plus"></i> Ajouter les manquants aux courses
                </button>
            ` : '<p style="color:var(--text-muted);margin-bottom:16px;"><i class="fas fa-info-circle"></i> Pas d\'ingrédient détaillé pour cette recette.</p>'}
            ${recipe.instructions ? `<h3 style="margin-bottom:8px;">Instructions</h3><div style="white-space:pre-line;line-height:1.7;">${recipe.instructions}</div>` : ''}
            ${recipe.source_url ? `<a href="${recipe.source_url}" target="_blank" class="btn btn-secondary" style="margin-top:16px;"><i class="fas fa-external-link-alt"></i> Voir la source</a>` : ''}
            <div style="margin-top:16px;display:flex;gap:8px;flex-wrap:wrap;">
                <button class="btn btn-success btn-save-menu-recipe"><i class="fas fa-bookmark"></i> Sauvegarder dans Mes recettes</button>
            </div>
        `;

        modal.classList.remove('hidden');

        content.querySelectorAll('.btn-add-ingredient').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const name = btn.dataset.name;
                const measure = btn.dataset.measure || '';
                const { qty, unit } = parseMeasure(measure);
                const res = await FrigoScan.API.post('/api/shopping/', { product_name: name, quantity: qty, unit: unit });
                if (res.success) { FrigoScan.toast(`"${name}" ajouté aux courses`, 'success'); btn.parentElement.classList.remove('missing'); btn.parentElement.classList.add('available'); btn.remove(); }
            });
        });

        const addAllBtnMenu = content.querySelector('.btn-add-all-missing-menu');
        if (addAllBtnMenu) {
            addAllBtnMenu.addEventListener('click', async () => {
                const btns = content.querySelectorAll('.btn-add-ingredient');
                let added = 0;
                for (const btn of btns) {
                    const { qty, unit } = parseMeasure(btn.dataset.measure || '');
                    const res = await FrigoScan.API.post('/api/shopping/', { product_name: btn.dataset.name, quantity: qty, unit: unit });
                    if (res.success) { added++; btn.parentElement.classList.remove('missing'); btn.parentElement.classList.add('available'); btn.remove(); }
                }
                FrigoScan.toast(`${added} ingrédient(s) ajouté(s) aux courses`, 'success');
                addAllBtnMenu.disabled = true; addAllBtnMenu.textContent = '✓ Ajoutés';
            });
        }

        const saveRecipeBtn = content.querySelector('.btn-save-menu-recipe');
        if (saveRecipeBtn) {
            saveRecipeBtn.addEventListener('click', async () => {
                const res = await FrigoScan.API.post('/api/recipes/', {
                    title: recipe.title, ingredients_json: recipe.ingredients_json || '[]',
                    instructions: recipe.instructions || '', prep_time: recipe.prep_time || 0,
                    cook_time: recipe.cook_time || 0, servings: recipe.servings || 4,
                    source_url: recipe.source_url || '', image_url: recipe.image_url || '',
                    tags_json: recipe.tags_json || '[]', diet_tags_json: recipe.diet_tags_json || '[]',
                });
                if (res.success) {
                    FrigoScan.toast('Recette sauvegardée dans "Mes recettes" !', 'success');
                    saveRecipeBtn.disabled = true;
                    saveRecipeBtn.innerHTML = '<i class="fas fa-check"></i> Sauvegardée';
                    saveRecipeBtn.style.background = '#6b7280'; saveRecipeBtn.style.color = '#fff';
                }
            });
        }
    }

    async function saveMenuRecipe(entry) {
        if (!entry.recipe_id) { FrigoScan.toast('Pas de recette associée.', 'warning'); return; }
        try {
            const data = await FrigoScan.API.get(`/api/menus/${entry.id}/recipe`);
            if (data.success && data.recipe) {
                const r = data.recipe;
                const res = await FrigoScan.API.post('/api/recipes/', {
                    title: r.title, ingredients_json: r.ingredients_json || '[]',
                    instructions: r.instructions || '', prep_time: r.prep_time || 0,
                    cook_time: r.cook_time || 0, servings: r.servings || 4,
                    source_url: r.source_url || '', image_url: r.image_url || '',
                    tags_json: r.tags_json || '[]', diet_tags_json: r.diet_tags_json || '[]',
                });
                if (res.success) FrigoScan.toast(`"${r.title}" sauvegardée dans Mes recettes !`, 'success');
            }
        } catch (e) { FrigoScan.toast('Erreur lors de la sauvegarde.', 'error'); }
    }

    async function addAllToShopping() {
        try {
            const data = await FrigoScan.API.get(`/api/menus/shopping-list?week_start=${currentWeekStart}`);
            if (data.success) {
                const items = data.shopping_list || [];
                if (items.length === 0) { FrigoScan.toast('Aucun ingrédient manquant \u2014 votre frigo a tout !', 'info'); return; }
                FrigoScan.toast(`Ajout de ${items.length} ingrédient(s) aux courses...`, 'info');
                let added = 0;
                for (const item of items) {
                    const res = await FrigoScan.API.post('/api/shopping/', { product_name: item.name, quantity: 1, unit: item.measure || 'unité' });
                    if (res.success) added++;
                }
                FrigoScan.toast(`${added} ingrédient(s) ajouté(s) aux courses !`, 'success');
            } else {
                FrigoScan.toast('Erreur lors de la génération de la liste.', 'error');
            }
        } catch (e) {
            FrigoScan.toast('Erreur de connexion.', 'error');
        }
    }

    async function generateMenu(mode) {
        const nbPersons = parseInt(localStorage.getItem('frigoscan-nb-persons') || '4');
        const modeLabel = mode === 'fridge' ? 'selon le frigo' : 'de zéro';
        FrigoScan.toast(`Génération du menu ${modeLabel} en cours...`, 'info');
        const data = await FrigoScan.API.post(`/api/menus/generate?week_start=${currentWeekStart}&servings=${nbPersons}&mode=${mode}`);
        if (data.success) { FrigoScan.toast(data.message || 'Menu généré !', 'success'); Menus.load(); }
    }

    async function clearWeekMenu() {
        const ok = await FrigoScan.confirm('Vider le menu', 'Supprimer tout le menu de cette semaine (y compris les épinglés) ?');
        if (!ok) return;
        const data = await FrigoScan.API.del(`/api/menus/week/${currentWeekStart}`);
        if (data.success) { FrigoScan.toast('Menu vidé.', 'success'); Menus.load(); }
    }

    Menus.removeEntry = async function (entryId) {
        const data = await FrigoScan.API.del(`/api/menus/${entryId}`);
        if (data.success) { FrigoScan.toast('Entrée supprimée.', 'success'); Menus.load(); }
    };

})();
