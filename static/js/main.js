function initDashboardSidebar() {
    const wrap = document.querySelector('.dashboard-wrap');
    const sidebar = document.getElementById('dashboardSidebar');
    const backdrop = document.getElementById('dashboardSidebarBackdrop');
    const toggle = document.getElementById('sidebarToggle');
    if (!wrap || !sidebar || !toggle) {
        return;
    }

    const mq = window.matchMedia('(max-width: 991.98px)');

    function isMobileLayout() {
        return mq.matches;
    }

    function closeMobile() {
        sidebar.classList.remove('show');
        if (backdrop) {
            backdrop.classList.remove('is-visible');
            backdrop.setAttribute('aria-hidden', 'true');
        }
    }

    function openMobile() {
        sidebar.classList.add('show');
        if (backdrop) {
            backdrop.classList.add('is-visible');
            backdrop.setAttribute('aria-hidden', 'false');
        }
    }

    function syncToggleAria() {
        if (isMobileLayout()) {
            toggle.setAttribute('aria-expanded', sidebar.classList.contains('show') ? 'true' : 'false');
        } else {
            const collapsed = wrap.classList.contains('dashboard-sidebar-collapsed');
            toggle.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
        }
    }

    function onLayoutChange() {
        if (isMobileLayout()) {
            wrap.classList.remove('dashboard-sidebar-collapsed');
        }
        closeMobile();
        syncToggleAria();
    }

    mq.addEventListener('change', onLayoutChange);
    onLayoutChange();

    toggle.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (isMobileLayout()) {
            if (sidebar.classList.contains('show')) {
                closeMobile();
            } else {
                openMobile();
            }
        } else {
            wrap.classList.toggle('dashboard-sidebar-collapsed');
        }
        syncToggleAria();
    });

    if (backdrop) {
        backdrop.addEventListener('click', () => {
            if (isMobileLayout()) {
                closeMobile();
                syncToggleAria();
            }
        });
    }

    document.addEventListener('click', (e) => {
        if (!isMobileLayout() || !sidebar.classList.contains('show')) {
            return;
        }
        if (sidebar.contains(e.target) || toggle.contains(e.target)) {
            return;
        }
        closeMobile();
        syncToggleAria();
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && isMobileLayout() && sidebar.classList.contains('show')) {
            closeMobile();
            syncToggleAria();
            toggle.focus();
        }
    });
}

document.addEventListener('DOMContentLoaded', () => {
    const toggleBtn = document.getElementById('darkModeToggle');
    const root = document.documentElement;
    const toggleIcon = toggleBtn ? toggleBtn.querySelector('i') : null;
    const bootstrapApi = window.bootstrap;

    initDashboardSidebar();

    function applyTheme(theme) {
        root.setAttribute('data-theme', theme);
        root.style.colorScheme = theme;
        localStorage.setItem('darkMode', String(theme === 'dark'));

        if (toggleIcon) {
            toggleIcon.className = theme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
        }
    }

    // Load preference
    const isDark = localStorage.getItem('darkMode') === 'true';
    applyTheme(isDark ? 'dark' : 'light');

    if (toggleBtn) {
        toggleBtn.addEventListener('click', () => {
            const currentTheme = root.getAttribute('data-theme');
            applyTheme(currentTheme === 'dark' ? 'light' : 'dark');
        });
    }

    // Initialize toasts
    if (bootstrapApi && bootstrapApi.Toast) {
        var toastElList = [].slice.call(document.querySelectorAll('.toast'));
        var toastList = toastElList.map(function (toastEl) {
            return new bootstrapApi.Toast(toastEl);
        });
        toastList.forEach(toast => toast.show());
    }
});
