document.addEventListener('DOMContentLoaded', () => {
    const toggleBtn = document.getElementById('darkModeToggle');
    const root = document.documentElement;
    const toggleIcon = toggleBtn ? toggleBtn.querySelector('i') : null;
    const bootstrapApi = window.bootstrap;

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
