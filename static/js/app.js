/**
 * FrigoScan — Module principal (app.js)
 * Navigation SPA, thème, toast, API helper, initialisation.
 */

const FrigoScan = window.FrigoScan || {};
window.FrigoScan = FrigoScan;

// =====================================================================
// API Helper
// =====================================================================
FrigoScan.API = {
    async get(url) {
        try {
            const resp = await fetch(url);
            if (!resp.ok) throw new Error(`Erreur HTTP ${resp.status}`);
            return await resp.json();
        } catch (e) {
            console.error('GET error:', url, e);
            FrigoScan.toast(e.message || 'Erreur réseau.', 'error');
            return { success: false, error: e.message };
        }
    },
    async post(url, data) {
        try {
            const resp = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data),
            });
            if (!resp.ok) {
                const err = await resp.json().catch(() => ({}));
                throw new Error(err.detail || err.message || `Erreur HTTP ${resp.status}`);
            }
            return await resp.json();
        } catch (e) {
            console.error('POST error:', url, e);
            FrigoScan.toast(e.message || 'Erreur réseau.', 'error');
            return { success: false, error: e.message };
        }
    },
    async put(url, data) {
        try {
            const resp = await fetch(url, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data),
            });
            if (!resp.ok) {
                const err = await resp.json().catch(() => ({}));
                throw new Error(err.detail || err.message || `Erreur HTTP ${resp.status}`);
            }
            return await resp.json();
        } catch (e) {
            console.error('PUT error:', url, e);
            FrigoScan.toast(e.message || 'Erreur réseau.', 'error');
            return { success: false, error: e.message };
        }
    },
    async del(url) {
        try {
            const resp = await fetch(url, { method: 'DELETE' });
            if (!resp.ok) throw new Error(`Erreur HTTP ${resp.status}`);
            return await resp.json();
        } catch (e) {
            console.error('DELETE error:', url, e);
            FrigoScan.toast(e.message || 'Erreur réseau.', 'error');
            return { success: false, error: e.message };
        }
    },
    async patch(url, data) {
        try {
            const resp = await fetch(url, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data || {}),
            });
            if (!resp.ok) {
                const err = await resp.json().catch(() => ({}));
                throw new Error(err.detail || err.message || `Erreur HTTP ${resp.status}`);
            }
            return await resp.json();
        } catch (e) {
            console.error('PATCH error:', url, e);
            FrigoScan.toast(e.message || 'Erreur réseau.', 'error');
            return { success: false, error: e.message };
        }
    },
};

// =====================================================================
// Toast notifications
// =====================================================================
FrigoScan.toast = function (message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    const icons = { success: 'check-circle', error: 'exclamation-circle', warning: 'exclamation-triangle', info: 'info-circle' };
    toast.innerHTML = `<i class="fas fa-${icons[type] || 'info-circle'}"></i> ${message}`;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 3800);
};

// =====================================================================
// Confirmation modal
// =====================================================================
FrigoScan.confirm = function (title, message) {
    return new Promise((resolve) => {
        const modal = document.getElementById('confirm-modal');
        document.getElementById('confirm-title').textContent = title;
        document.getElementById('confirm-message').textContent = message;
        modal.classList.remove('hidden');

        const yes = document.getElementById('confirm-yes');
        const no = document.getElementById('confirm-no');

        function cleanup() {
            modal.classList.add('hidden');
            yes.removeEventListener('click', onYes);
            no.removeEventListener('click', onNo);
        }
        function onYes() { cleanup(); resolve(true); }
        function onNo() { cleanup(); resolve(false); }

        yes.addEventListener('click', onYes);
        no.addEventListener('click', onNo);
    });
};

// =====================================================================
// Navigation
// =====================================================================
FrigoScan.currentView = 'dashboard';

FrigoScan.navigate = function (viewName) {
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    const target = document.getElementById(`view-${viewName}`);
    if (target) {
        target.classList.add('active');
        FrigoScan.currentView = viewName;
    }

    // Header
    const backBtn = document.getElementById('btn-back');
    const title = document.getElementById('page-title');
    const logo = '<img src="/static/images/logo_frigoscan.png" alt="FrigoScan" class="header-logo">';
    const viewTitles = {
        dashboard: `${logo} FrigoScan`,
        scanner: `${logo} <span>Scan rapide</span>`,
        'manual-add': `${logo} <span>Ajout manuel</span>`,
        fridge: `${logo} <span>Mon frigo</span>`,
        recipes: `${logo} <span>Recettes</span>`,
        seasonal: `${logo} <span>De saison</span>`,
        shopping: `${logo} <span>Liste de courses</span>`,
        stats: `${logo} <span>Statistiques</span>`,
        settings: `${logo} <span>Réglages</span>`,
    };
    title.innerHTML = viewTitles[viewName] || viewTitles.dashboard;
    if (viewName === 'dashboard') {
        backBtn.classList.add('hidden');
    } else {
        backBtn.classList.remove('hidden');
    }

    // Callbacks d'entrée de vue
    const callbacks = {
        fridge: () => FrigoScan.Fridge && FrigoScan.Fridge.load(),
        recipes: () => {
            // Charger le badge des recettes sauvegardées
            if (FrigoScan.Recipes) {
                FrigoScan.API.get('/api/recipes/').then(data => {
                    if (data.success) {
                        const badge = document.getElementById('badge-saved-recipes');
                        if (badge) badge.textContent = (data.recipes || []).length;
                    }
                });
            }
        },
        seasonal: () => FrigoScan.Seasonal && FrigoScan.Seasonal.load(),
        shopping: () => FrigoScan.Shopping && FrigoScan.Shopping.load(),
        stats: () => FrigoScan.Stats && FrigoScan.Stats.load(),
        settings: () => FrigoScan.Settings && FrigoScan.Settings.load(),
        scanner: () => FrigoScan.Scanner && FrigoScan.Scanner.init(),
        dashboard: () => FrigoScan.loadDashboard(),
    };
    if (callbacks[viewName]) callbacks[viewName]();

    window.scrollTo({ top: 0, behavior: 'smooth' });
};

// =====================================================================
// Dashboard
// =====================================================================
FrigoScan.loadDashboard = async function () {
    const data = await FrigoScan.API.get('/api/fridge/stats/summary');
    if (data.success) {
        document.getElementById('badge-fridge').textContent = data.total || 0;
        document.getElementById('summary-expiring').querySelector('span').textContent =
            `${data.expiring_soon || 0} produit(s) bientôt périmé(s)`;
        document.getElementById('summary-expired').querySelector('span').textContent =
            `${data.expired || 0} produit(s) périmé(s)`;

        // Masquer les badges si 0
        document.getElementById('summary-expiring').style.display = data.expiring_soon ? 'flex' : 'none';
        document.getElementById('summary-expired').style.display = data.expired ? 'flex' : 'none';
    }
    // Badge courses
    const shop = await FrigoScan.API.get('/api/shopping/?show_purchased=false');
    if (shop.success) {
        document.getElementById('badge-shopping').textContent = shop.count || 0;
    }
};

// =====================================================================
// Thème
// =====================================================================
FrigoScan.toggleTheme = function () {
    const html = document.documentElement;
    const current = html.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-theme', next);
    localStorage.setItem('frigoscan-theme', next);
    const icon = document.querySelector('#btn-theme i');
    icon.className = next === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
};

FrigoScan.loadTheme = function () {
    const saved = localStorage.getItem('frigoscan-theme') || 'light';
    document.documentElement.setAttribute('data-theme', saved);
    const icon = document.querySelector('#btn-theme i');
    icon.className = saved === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
};

// =====================================================================
// Barcode input listener (douchette USB)
// =====================================================================
FrigoScan.barcodeBuffer = '';
FrigoScan.barcodeTimeout = null;

FrigoScan.handleBarcodeInput = function (e) {
    // Les douchettes USB envoient les caractères rapidement puis Enter
    if (FrigoScan.currentView !== 'scanner' && FrigoScan.currentView !== 'dashboard') return;
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') return;

    if (e.key === 'Enter' && FrigoScan.barcodeBuffer.length >= 8) {
        const barcode = FrigoScan.barcodeBuffer.trim();
        FrigoScan.barcodeBuffer = '';
        // Naviguer vers le scanner et lancer la recherche
        if (FrigoScan.currentView !== 'scanner') FrigoScan.navigate('scanner');
        if (FrigoScan.Scanner) FrigoScan.Scanner.lookupBarcode(barcode);
    } else if (e.key.length === 1) {
        FrigoScan.barcodeBuffer += e.key;
        clearTimeout(FrigoScan.barcodeTimeout);
        FrigoScan.barcodeTimeout = setTimeout(() => { FrigoScan.barcodeBuffer = ''; }, 300);
    }
};

// =====================================================================
// Init
// =====================================================================
document.addEventListener('DOMContentLoaded', () => {
    FrigoScan.loadTheme();

    // Navigation widgets
    document.querySelectorAll('.widget-card').forEach(card => {
        card.addEventListener('click', () => {
            const view = card.dataset.view;
            if (view) FrigoScan.navigate(view);
        });
    });

    // Bouton retour
    document.getElementById('btn-back').addEventListener('click', () => FrigoScan.navigate('dashboard'));

    // Thème
    document.getElementById('btn-theme').addEventListener('click', FrigoScan.toggleTheme);

    // Douchette USB
    document.addEventListener('keydown', FrigoScan.handleBarcodeInput);

    // Charger le dashboard
    FrigoScan.loadDashboard();
});
