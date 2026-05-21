/* =====================================================================
   Main JS — Particles, анимациялар, тема, іздеу, toast
   ===================================================================== */

// ============ 1. tsParticles фондық бөлшектер ============
document.addEventListener('DOMContentLoaded', () => {
    if (typeof tsParticles !== 'undefined') {
        tsParticles.load({
            id: "tsparticles",
            options: {
                fpsLimit: 60,
                particles: {
                    number: { value: 70, density: { enable: true, area: 900 } },
                    color: { value: ["#d4ff00", "#a8e024", "#ffffff", "#c5f82a"] },
                    shape: { type: "circle" },
                    opacity: { value: { min: 0.2, max: 0.6 }, random: true },
                    size: { value: { min: 1, max: 3 }, random: true },
                    move: {
                        enable: true,
                        speed: 1.2,
                        direction: "none",
                        random: true,
                        straight: false,
                        outModes: { default: "bounce" }
                    },
                    links: {
                        enable: true,
                        color: "#d4ff00",
                        opacity: 0.2,
                        distance: 150,
                        width: 1
                    }
                },
                interactivity: {
                    events: {
                        onHover: { enable: true, mode: "grab" },
                        onClick: { enable: true, mode: "push" }
                    },
                    modes: {
                        grab: { distance: 160, links: { opacity: 0.4 } },
                        push: { quantity: 4 }
                    }
                },
                detectRetina: true,
                background: { color: "transparent" }
            }
        });
    }

    initThemeToggle();
    initLanguageToggle();
    initCounters();
    initFlashMessages();
    initLiveSearch();
});

// ============ 2. Тақырып ауыстыру (Dark / Light) ============
function initThemeToggle() {
    const toggle = document.getElementById('themeToggle');
    if (!toggle) return;

    const icon = toggle.querySelector('i');
    const saved = localStorage.getItem('theme');
    const prefersLight = window.matchMedia('(prefers-color-scheme: light)').matches;

    const applyTheme = (theme) => {
        document.body.classList.toggle('light-mode', theme === 'light');
        if (icon) {
            icon.className = theme === 'light' ? 'fa-solid fa-sun' : 'fa-solid fa-moon';
        }
    };

    applyTheme(saved || (prefersLight ? 'light' : 'dark'));

    toggle.addEventListener('click', () => {
        const isLight = document.body.classList.toggle('light-mode');
        const theme = isLight ? 'light' : 'dark';
        localStorage.setItem('theme', theme);
        icon.className = isLight ? 'fa-solid fa-sun' : 'fa-solid fa-moon';
        icon.style.transform = 'rotate(360deg) scale(1.2)';
        setTimeout(() => icon.style.transform = '', 400);
    });
}

// ============ 3. Тіл ауыстыру (KZ / RU / EN) ============
function initLanguageToggle() {
    const btn = document.getElementById('langToggle');
    if (!btn) return;

    const labelEl = document.getElementById('langCurrent');
    const langs = ['kk', 'ru', 'en'];
    const labels = { kk: 'KZ', ru: 'RU', en: 'EN' };

    let current = localStorage.getItem('lang') || 'kk';
    applyLanguage(current);
    labelEl.textContent = labels[current];

    btn.addEventListener('click', () => {
        const idx = (langs.indexOf(current) + 1) % langs.length;
        current = langs[idx];
        localStorage.setItem('lang', current);
        labelEl.textContent = labels[current];
        document.body.style.opacity = '0.5';
        setTimeout(() => {
            applyLanguage(current);
            document.body.style.transition = 'opacity 0.4s';
            document.body.style.opacity = '1';
        }, 200);
    });
}

function applyLanguage(lang) {
    if (!window.I18N) return;
    const dict = window.I18N[lang] || window.I18N.kk;

    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.dataset.i18n;
        if (dict[key]) {
            let text = dict[key];
            if (text.includes('{year}')) {
                text = text.replace('{year}', new Date().getFullYear());
            }
            el.textContent = text;
        }
    });

    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
        const key = el.dataset.i18nPlaceholder;
        if (dict[key]) el.placeholder = dict[key];
    });

    document.querySelectorAll('[data-i18n-title]').forEach(el => {
        const key = el.dataset.i18nTitle;
        if (dict[key]) el.title = dict[key];
    });

    document.querySelectorAll('[data-i18n-confirm]').forEach(el => {
        const key = el.dataset.i18nConfirm;
        const form = el.closest('form') || el;
        if (dict[key]) {
            form.dataset.i18nMsg = dict[key];
        }
    });

    document.documentElement.lang = lang === 'kk' ? 'kk' : (lang === 'ru' ? 'ru' : 'en');

    const titleKey = document.body.dataset.titleKey;
    if (titleKey && dict[titleKey]) {
        document.title = dict[titleKey];
    }

    document.querySelectorAll('[data-search-query]').forEach(el => {
        const q = el.dataset.searchQuery;
        const tpl = dict['home.searchEmpty'];
        if (tpl && q) el.textContent = tpl.replace('{q}', q);
    });
}

// ============ 4. Сан санауыш анимациясы (Counter) ============
function initCounters() {
    const counters = document.querySelectorAll('[data-counter]');
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting && !entry.target.dataset.animated) {
                entry.target.dataset.animated = '1';
                animateCounter(entry.target, parseInt(entry.target.dataset.counter) || 0);
            }
        });
    }, { threshold: 0.3 });
    counters.forEach(c => observer.observe(c));
}

function animateCounter(el, target) {
    const duration = 1500;
    const startTime = performance.now();
    function step(now) {
        const progress = Math.min((now - startTime) / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        el.textContent = Math.floor(target * eased);
        if (progress < 1) requestAnimationFrame(step);
        else el.textContent = target;
    }
    requestAnimationFrame(step);
}

// ============ 5. Flash хабарламалар → Toast (аудармамен) ============
function initFlashMessages() {
    const el = document.getElementById('flashMessages');
    if (!el) return;
    try {
        const messages = JSON.parse(el.dataset.messages || '[]');
        messages.forEach(([category, msg], i) => {
            const translated = translateFlash(msg);
            setTimeout(() => showToast(translated, category), i * 300);
        });
    } catch (_) {}
    el.remove();
}

function translateFlash(msg) {
    if (!window.I18N) return msg;
    const lang = localStorage.getItem('lang') || 'kk';
    if (lang === 'kk') return msg;
    const dict = window.I18N[lang] || {};
    const kk = window.I18N.kk || {};
    for (const key in kk) {
        if (key.startsWith('flash.') && kk[key] === msg && dict[key]) {
            return dict[key];
        }
    }
    return msg;
}

// ============ 6. Toast хабарлама ============
window.showToast = function(message, type = 'success') {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    const icons = {
        success: '<i class="fa-solid fa-circle-check"></i>',
        error:   '<i class="fa-solid fa-circle-xmark"></i>',
        warning: '<i class="fa-solid fa-circle-exclamation"></i>',
        info:    '<i class="fa-solid fa-circle-info"></i>'
    };

    toast.innerHTML = `
        <div class="icon">${icons[type] || icons.info}</div>
        <div>${message}</div>
    `;

    container.appendChild(toast);
    requestAnimationFrame(() => toast.classList.add('show'));

    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 500);
    }, 4000);
};

// ============ 7. Live Search dropdown ============
function initLiveSearch() {
    const input = document.getElementById('searchInput');
    const dropdown = document.getElementById('searchDropdown');
    if (!input || !dropdown) return;

    let timeout;
    input.addEventListener('input', () => {
        clearTimeout(timeout);
        const q = input.value.trim();
        if (q.length < 2) {
            dropdown.classList.remove('open');
            return;
        }
        timeout = setTimeout(async () => {
            try {
                const res = await fetch(`/api/search?q=${encodeURIComponent(q)}`);
                const results = await res.json();
                renderSearchResults(results);
            } catch (err) {
                console.error(err);
            }
        }, 250);
    });

    document.addEventListener('click', (e) => {
        if (!e.target.closest('.search-container')) {
            dropdown.classList.remove('open');
        }
    });

    input.addEventListener('focus', () => {
        if (dropdown.innerHTML.trim()) dropdown.classList.add('open');
    });
}

function renderSearchResults(results) {
    const dropdown = document.getElementById('searchDropdown');
    if (!dropdown) return;
    if (!results.length) {
        const noRes = _t('search.noResults') || 'Ештеңе табылмады';
        dropdown.innerHTML = `<div class="search-result"><span>${noRes}</span></div>`;
    } else {
        const fallback = _t('search.fallbackDept') || 'Оқытушы';
        dropdown.innerHTML = results.map(r => {
            const photo = r.PhotoPath
                ? `/static/${r.PhotoPath}`
                : `https://ui-avatars.com/api/?name=${encodeURIComponent(r.FullName)}&background=0f3460&color=fff`;
            return `
                <a href="/teacher/${r.TeacherId}" class="search-result">
                    <img src="${photo}" alt="${r.FullName}">
                    <div class="sr-info">
                        <div class="sr-name">${r.FullName}</div>
                        <div class="sr-dept">${r.Department || fallback}</div>
                    </div>
                    <div class="sr-score">⭐ ${r.TotalScore}</div>
                </a>
            `;
        }).join('');
    }
    dropdown.classList.add('open');
}

// ============ i18n helper — аударма кілтті оқу ============
function _t(key) {
    if (!window.I18N) return '';
    const lang = localStorage.getItem('lang') || 'kk';
    const dict = window.I18N[lang] || window.I18N.kk;
    return dict[key] || '';
}
window._t = _t;

// ============ 8. IntersectionObserver — жалпы пайда болу ============
const revealObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.style.animationPlayState = 'running';
        }
    });
}, { threshold: 0.1 });

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.teacher-card, .stat-card, .chart-card').forEach(el => {
        revealObserver.observe(el);
    });
});

// ============ 9. Жаңа орындалған IntersectionObserver — progress bars ============
document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => {
        document.querySelectorAll('.progress-bar').forEach(bar => {
            const w = bar.getAttribute('data-width');
            if (w) bar.style.width = Math.min(parseInt(w), 100) + '%';
        });
    }, 500);
});
