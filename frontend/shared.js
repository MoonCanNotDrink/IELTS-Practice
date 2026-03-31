(() => {
    const THEME_MODE_STORAGE_KEY = 'ielts_theme_mode';
    const THEME_MODE_LABELS = {
        system: 'System',
        light: 'Light',
        dark: 'Dark',
    };

    const AUTH_MODE = {
        LOGIN: 'login',
        REGISTER: 'register',
        RESET: 'reset',
        ACCOUNT: 'account',
    };

    let authMode = AUTH_MODE.LOGIN;
    let authProfile = null;

    const AUTH_MODAL_HTML = `<div id="authModal" class="auth-overlay">
    <div class="auth-card">
        <div class="auth-header">
            <h2 id="authTitle">Welcome Back</h2>
            <p id="authSubtitle">Please log in to save your practice history.</p>
            <p id="authMeta" class="auth-helper-note hidden"></p>
        </div>
        <div id="authError" class="auth-error"></div>
        <div id="authStatus" class="auth-status"></div>
        <div class="form-group" id="usernameGroup">
            <label for="authUsername">Username</label>
            <input type="text" id="authUsername" placeholder="Enter username" autocomplete="username">
        </div>
        <div class="form-group hidden" id="emailGroup">
            <label for="authEmail">Email</label>
            <input type="email" id="authEmail" placeholder="Enter your email" autocomplete="email">
        </div>
        <div class="form-group" id="passwordGroup">
            <label for="authPassword">Password</label>
            <div class="password-input-wrap">
                <input type="password" id="authPassword" placeholder="Enter password" autocomplete="current-password">
                <button type="button" class="password-toggle hidden" id="authPasswordToggle" onclick="togglePasswordVisibility('authPassword', 'authPasswordToggle')" aria-label="Show password" aria-pressed="false">Show</button>
            </div>
        </div>
        <div class="form-group hidden" id="confirmPasswordGroup">
            <label for="authConfirmPassword">Confirm Password</label>
            <div class="password-input-wrap">
                <input type="password" id="authConfirmPassword" placeholder="Re-enter password" autocomplete="new-password">
                <button type="button" class="password-toggle hidden" id="authConfirmPasswordToggle" onclick="togglePasswordVisibility('authConfirmPassword', 'authConfirmPasswordToggle')" aria-label="Show password confirmation" aria-pressed="false">Show</button>
            </div>
        </div>
        <div class="form-group hidden" id="inviteCodeGroup">
            <label for="authInviteCode">Invite Code</label>
            <input type="password" id="authInviteCode" placeholder="Required for new accounts">
        </div>
        <div class="auth-secondary-action hidden" id="forgotPasswordGroup">
            <a data-testid="forgot-password-link" onclick="showPasswordResetRequest()">Forgot password?</a>
        </div>
        <button type="button" class="btn btn-primary btn-full" id="btnSubmitAuth" style="margin-top:20px;" onclick="submitAuth()">Log In</button>
        <div class="auth-toggle" id="authToggleWrap">
            <span id="authToggleText">No account? <a data-testid="auth-mode-toggle" onclick="toggleAuthMode()">Register here</a></span>
        </div>
    </div>
</div>`;

    const ACCOUNT_BUTTON_HTML = '<button type="button" id="btnAccount" class="btn btn-ghost header-btn-compact auth-logout-hidden" onclick="showAccountSettings()">Account</button>';

    const THEME_SWITCHER_HTML = `<div class="theme-switcher" id="themeSwitcher">
    <button type="button" id="btnThemeToggle" class="btn btn-ghost theme-toggle" aria-haspopup="menu" aria-expanded="false" aria-controls="themeMenu">
        <span aria-hidden="true">🎨</span>
        <span id="currentThemeLabel">System</span>
    </button>
    <div id="themeMenu" class="theme-menu hidden" role="menu" aria-label="Theme mode">
        <button type="button" class="theme-option" data-testid="theme-option-system" data-theme-mode="system" role="menuitemradio" aria-checked="true">Follow System</button>
        <button type="button" class="theme-option" data-testid="theme-option-light" data-theme-mode="light" role="menuitemradio" aria-checked="false">Light Mode</button>
        <button type="button" class="theme-option" data-testid="theme-option-dark" data-theme-mode="dark" role="menuitemradio" aria-checked="false">Dark Mode</button>
    </div>
</div>`;

    function injectSharedHtml() {
        if (!document.getElementById('authModal')) {
            document.body.insertAdjacentHTML('afterbegin', AUTH_MODAL_HTML);
        }

        const headerControls = document.querySelector('.header-controls');
        if (headerControls) {
            if (!document.getElementById('btnAccount')) {
                const btnLogout = document.getElementById('btnLogout');
                if (btnLogout) {
                    btnLogout.insertAdjacentHTML('beforebegin', ACCOUNT_BUTTON_HTML);
                } else {
                    headerControls.insertAdjacentHTML('beforeend', ACCOUNT_BUTTON_HTML);
                }
            }

            if (!document.getElementById('themeSwitcher')) {
                headerControls.insertAdjacentHTML('afterbegin', THEME_SWITCHER_HTML);
            }
        }
    }

    function escapeText(value) {
        return String(value ?? '').replace(/[&<>"']/g, (char) => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#39;',
        }[char]));
    }

    function getCssVar(name, fallback = '') {
        const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
        return value || fallback;
    }

    function getSystemTheme() {
        return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }

    function getStoredThemeMode() {
        const storedMode = localStorage.getItem(THEME_MODE_STORAGE_KEY);
        return storedMode === 'light' || storedMode === 'dark' || storedMode === 'system'
            ? storedMode
            : 'system';
    }

    function closeThemeMenu() {
        const menu = document.getElementById('themeMenu');
        const trigger = document.getElementById('btnThemeToggle');
        if (!menu || !trigger) return;
        menu.classList.add('hidden');
        trigger.setAttribute('aria-expanded', 'false');
    }

    function syncThemeMenuState(mode) {
        const currentLabel = document.getElementById('currentThemeLabel');
        if (currentLabel) currentLabel.textContent = THEME_MODE_LABELS[mode] || THEME_MODE_LABELS.system;

        document.querySelectorAll('#themeMenu .theme-option').forEach((option) => {
            const isActive = option.dataset.themeMode === mode;
            option.classList.toggle('active', isActive);
            option.setAttribute('aria-checked', isActive ? 'true' : 'false');
        });
    }

    function applyThemeMode(mode, { persist = true } = {}) {
        const normalizedMode = mode === 'light' || mode === 'dark' ? mode : 'system';
        const resolvedTheme = normalizedMode === 'system' ? getSystemTheme() : normalizedMode;

        document.documentElement.dataset.themeMode = normalizedMode;
        document.documentElement.dataset.theme = resolvedTheme;

        syncThemeMenuState(normalizedMode);
        if (persist) localStorage.setItem(THEME_MODE_STORAGE_KEY, normalizedMode);

        document.dispatchEvent(new CustomEvent('theme-changed', {
            detail: {
                mode: normalizedMode,
                theme: resolvedTheme,
                persist,
            },
        }));
    }

    function initThemeMode() {
        const trigger = document.getElementById('btnThemeToggle');
        const menu = document.getElementById('themeMenu');
        const themeSwitcher = document.getElementById('themeSwitcher');
        if (!trigger || !menu || !themeSwitcher) return;

        applyThemeMode(getStoredThemeMode(), { persist: false });

        trigger.addEventListener('click', (event) => {
            event.stopPropagation();
            const isHidden = menu.classList.contains('hidden');
            menu.classList.toggle('hidden', !isHidden);
            trigger.setAttribute('aria-expanded', isHidden ? 'true' : 'false');
        });

        menu.addEventListener('click', (event) => {
            const option = event.target.closest('.theme-option');
            if (!option) return;
            applyThemeMode(option.dataset.themeMode || 'system');
            closeThemeMenu();
            trigger.focus();
        });

        document.addEventListener('click', (event) => {
            if (!themeSwitcher.contains(event.target)) {
                closeThemeMenu();
            }
        });

        const mediaQuery = window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)') : null;
        if (mediaQuery) {
            const handleChange = () => {
                if ((document.documentElement.dataset.themeMode || 'system') === 'system') {
                    applyThemeMode('system', { persist: false });
                }
            };

            if (typeof mediaQuery.addEventListener === 'function') {
                mediaQuery.addEventListener('change', handleChange);
            } else if (typeof mediaQuery.addListener === 'function') {
                mediaQuery.addListener(handleChange);
            }
        }
    }

    function setHidden(id, hidden) {
        const element = typeof id === 'string' ? document.getElementById(id) : id;
        if (!element) return;
        element.classList.toggle('hidden', Boolean(hidden));
    }

    function setPasswordVisibility(inputId, buttonId, visible) {
        const input = document.getElementById(inputId);
        const button = document.getElementById(buttonId);
        if (!input || !button) return;

        const isVisible = Boolean(visible);
        input.type = isVisible ? 'text' : 'password';
        button.textContent = isVisible ? 'Hide' : 'Show';
        button.setAttribute('aria-pressed', isVisible ? 'true' : 'false');
        button.setAttribute('aria-label', isVisible
            ? `Hide ${inputId === 'authConfirmPassword' ? 'password confirmation' : 'password'}`
            : `Show ${inputId === 'authConfirmPassword' ? 'password confirmation' : 'password'}`);
    }

    function resetAuthPasswordVisibility() {
        setPasswordVisibility('authPassword', 'authPasswordToggle', false);
        setPasswordVisibility('authConfirmPassword', 'authConfirmPasswordToggle', false);
    }

    function togglePasswordVisibility(inputId, buttonId) {
        const input = document.getElementById(inputId);
        if (!input) return;
        setPasswordVisibility(inputId, buttonId, input.type === 'password');
    }

    function clearAuthMessages() {
        const errEl = document.getElementById('authError');
        const statusEl = document.getElementById('authStatus');
        if (errEl) {
            errEl.textContent = '';
            errEl.style.display = 'none';
        }
        if (statusEl) {
            statusEl.textContent = '';
            statusEl.style.display = 'none';
        }
    }

    function setAuthError(message) {
        clearAuthMessages();
        const errEl = document.getElementById('authError');
        if (!errEl) return;
        errEl.textContent = message;
        errEl.style.display = 'block';
    }

    function setAuthStatus(message) {
        clearAuthMessages();
        const statusEl = document.getElementById('authStatus');
        if (!statusEl) return;
        statusEl.textContent = message;
        statusEl.style.display = 'block';
    }

    function updateAuthButtons() {
        const token = localStorage.getItem('ielts_token');
        const btnLogin = document.getElementById('btnLogin');
        const btnLogout = document.getElementById('btnLogout');
        const btnAccount = document.getElementById('btnAccount');

        if (btnLogin) btnLogin.style.display = token ? 'none' : 'block';
        if (btnLogout) btnLogout.style.display = token ? 'block' : 'none';
        if (btnAccount) {
            btnAccount.style.display = token ? 'block' : 'none';
            btnAccount.textContent = authProfile && !authProfile.email ? 'Bind Email' : 'Account';
        }
    }

    function clearStoredAuth() {
        authProfile = null;
        localStorage.removeItem('ielts_token');
        localStorage.removeItem('ielts_refresh_token');
        updateAuthButtons();
    }

    async function loadAuthProfile() {
        const token = localStorage.getItem('ielts_token');
        if (!token) {
            authProfile = null;
            updateAuthButtons();
            return null;
        }

        try {
            const response = await fetch('/api/auth/me', {
                headers: {
                    Authorization: `Bearer ${token}`,
                },
            });
            if (response.status === 401) {
                clearStoredAuth();
                return null;
            }
            if (!response.ok) {
                return authProfile;
            }
            authProfile = await response.json();
            updateAuthButtons();
            return authProfile;
        } catch {
            return authProfile;
        }
    }

    function getAuthModeConfig(mode) {
        switch (mode) {
        case AUTH_MODE.REGISTER:
            return {
                title: 'Create Account',
                subtitle: 'Create an account to track your progress.',
                submitText: 'Register',
                showUsername: true,
                showEmail: true,
                showPassword: true,
                showConfirm: true,
                showInvite: true,
                showForgot: false,
                showToggle: true,
                meta: '',
                toggleHtml: 'Have an account? <a data-testid="auth-mode-toggle" onclick="toggleAuthMode()">Log in</a>',
            };
        case AUTH_MODE.RESET:
            return {
                title: 'Reset Password',
                subtitle: 'Enter your recovery email and we will send you a reset link.',
                submitText: 'Send Reset Link',
                showUsername: false,
                showEmail: true,
                showPassword: false,
                showConfirm: false,
                showInvite: false,
                showForgot: false,
                showToggle: true,
                meta: '',
                toggleHtml: 'Remembered it? <a onclick="setAuthMode(\'login\')">Back to log in</a>',
            };
        case AUTH_MODE.ACCOUNT:
            return {
                title: 'Account Settings',
                subtitle: 'Bind or update your recovery email for password reset.',
                submitText: 'Save Email',
                showUsername: false,
                showEmail: true,
                showPassword: false,
                showConfirm: false,
                showInvite: false,
                showForgot: false,
                showToggle: false,
                meta: authProfile ? `Signed in as ${authProfile.username}` : '',
                toggleHtml: '',
            };
        default:
            return {
                title: 'Welcome Back',
                subtitle: 'Please log in to save your practice history.',
                submitText: 'Log In',
                showUsername: true,
                showEmail: false,
                showPassword: true,
                showConfirm: false,
                showInvite: false,
                showForgot: true,
                showToggle: true,
                meta: '',
                toggleHtml: 'No account? <a data-testid="auth-mode-toggle" onclick="toggleAuthMode()">Register here</a>',
            };
        }
    }

    function setAuthMode(mode) {
        authMode = mode;
        const config = getAuthModeConfig(mode);
        const titleEl = document.getElementById('authTitle');
        const subtitleEl = document.getElementById('authSubtitle');
        const submitEl = document.getElementById('btnSubmitAuth');
        const toggleTextEl = document.getElementById('authToggleText');
        const metaEl = document.getElementById('authMeta');

        if (titleEl) titleEl.textContent = config.title;
        if (subtitleEl) subtitleEl.textContent = config.subtitle;
        if (submitEl) submitEl.textContent = config.submitText;
        if (toggleTextEl) toggleTextEl.innerHTML = config.toggleHtml;
        if (metaEl) {
            metaEl.textContent = config.meta;
            metaEl.classList.toggle('hidden', !config.meta);
        }

        setHidden('usernameGroup', !config.showUsername);
        setHidden('emailGroup', !config.showEmail);
        setHidden('passwordGroup', !config.showPassword);
        setHidden('confirmPasswordGroup', !config.showConfirm);
        setHidden('inviteCodeGroup', !config.showInvite);
        setHidden('forgotPasswordGroup', !config.showForgot);
        setHidden('authToggleWrap', !config.showToggle);
        setHidden('authPasswordToggle', mode !== AUTH_MODE.REGISTER);
        setHidden('authConfirmPasswordToggle', mode !== AUTH_MODE.REGISTER);

        const passwordInput = document.getElementById('authPassword');
        if (passwordInput) {
            passwordInput.setAttribute('autocomplete', mode === AUTH_MODE.LOGIN ? 'current-password' : 'new-password');
        }

        if (mode === AUTH_MODE.ACCOUNT && authProfile) {
            document.getElementById('authEmail').value = authProfile.email || '';
        }
        if (mode !== AUTH_MODE.REGISTER) {
            document.getElementById('authConfirmPassword').value = '';
            document.getElementById('authInviteCode').value = '';
        }
        if (mode !== AUTH_MODE.ACCOUNT) {
            document.getElementById('authMeta').textContent = '';
        }

        resetAuthPasswordVisibility();
        clearAuthMessages();
    }

    function toggleAuthMode() {
        setAuthMode(authMode === AUTH_MODE.LOGIN ? AUTH_MODE.REGISTER : AUTH_MODE.LOGIN);
    }

    async function showAuth(mode = null) {
        if (localStorage.getItem('ielts_token') && mode !== AUTH_MODE.LOGIN && mode !== AUTH_MODE.REGISTER && mode !== AUTH_MODE.RESET) {
            await loadAuthProfile();
            setAuthMode(AUTH_MODE.ACCOUNT);
        } else {
            setAuthMode(mode || AUTH_MODE.LOGIN);
        }
        document.getElementById('authModal').classList.add('show');
    }

    function hideAuth() {
        document.getElementById('authModal').classList.remove('show');
        clearAuthMessages();
    }

    function ensureAuthInput(id) {
        return document.getElementById(id)?.value.trim() || '';
    }

    async function submitLogin() {
        const user = ensureAuthInput('authUsername');
        const pass = document.getElementById('authPassword').value;

        if (!user || !pass) {
            setAuthError('Please enter username and password.');
            return;
        }

        const fd = new URLSearchParams();
        fd.append('username', user);
        fd.append('password', pass);
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: fd,
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || 'Authentication failed');

        localStorage.setItem('ielts_token', data.access_token);
        if (data.refresh_token) {
            localStorage.setItem('ielts_refresh_token', data.refresh_token);
        }
        await loadAuthProfile();
        updateAuthButtons();

        if (authProfile && !authProfile.email) {
            setAuthMode(AUTH_MODE.ACCOUNT);
            setAuthStatus('Add a recovery email to enable password reset.');
            return;
        }

        hideAuth();
        if (typeof loadHistory === 'function') loadHistory();
    }

    async function submitRegister() {
        const user = ensureAuthInput('authUsername');
        const email = ensureAuthInput('authEmail');
        const pass = document.getElementById('authPassword').value;
        const confirmPass = document.getElementById('authConfirmPassword').value;
        const invite = ensureAuthInput('authInviteCode');

        if (!user || !email || !pass) {
            setAuthError('Please enter username, email, and password.');
            return;
        }
        if (!confirmPass) {
            setAuthError('Please confirm your password.');
            return;
        }
        if (pass !== confirmPass) {
            setAuthError('Passwords do not match.');
            return;
        }

        const response = await fetch('/api/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: user, email, password: pass, invite_code: invite }),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || 'Authentication failed');

        localStorage.setItem('ielts_token', data.access_token);
        if (data.refresh_token) {
            localStorage.setItem('ielts_refresh_token', data.refresh_token);
        }
        authProfile = { username: user, email, email_verified: false };
        updateAuthButtons();
        hideAuth();
        if (typeof loadHistory === 'function') loadHistory();
    }

    async function submitPasswordResetRequest() {
        const email = ensureAuthInput('authEmail');
        if (!email) {
            setAuthError('Please enter your email address.');
            return;
        }
        const response = await fetch('/api/auth/password-reset/request', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email }),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || 'Request failed');
        setAuthStatus(data.message || 'If the email exists, a reset link has been sent.');
    }

    async function submitEmailBinding() {
        const email = ensureAuthInput('authEmail');
        const token = localStorage.getItem('ielts_token');
        if (!token) {
            setAuthMode(AUTH_MODE.LOGIN);
            setAuthError('Please log in again.');
            updateAuthButtons();
            return;
        }
        if (!email) {
            setAuthError('Please enter your email address.');
            return;
        }

        const response = await fetch('/api/auth/email', {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({ email }),
        });

        if (response.status === 401) {
            clearStoredAuth();
            setAuthMode(AUTH_MODE.LOGIN);
            setAuthError('Your session expired. Please log in again.');
            return;
        }

        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || 'Failed to save email');

        authProfile = data;
        updateAuthButtons();
        setAuthStatus('Recovery email saved.');
    }

    async function submitAuth() {
        try {
            if (authMode === AUTH_MODE.LOGIN) {
                await submitLogin();
                return;
            }
            if (authMode === AUTH_MODE.REGISTER) {
                await submitRegister();
                return;
            }
            if (authMode === AUTH_MODE.RESET) {
                await submitPasswordResetRequest();
                return;
            }
            if (authMode === AUTH_MODE.ACCOUNT) {
                await submitEmailBinding();
            }
        } catch (err) {
            setAuthError(err.message || 'Authentication failed');
        }
    }

    function showPasswordResetRequest() {
        document.getElementById('authEmail').value = authProfile?.email || '';
        setAuthMode(AUTH_MODE.RESET);
        document.getElementById('authModal').classList.add('show');
    }

    async function showAccountSettings() {
        if (!localStorage.getItem('ielts_token')) {
            setAuthMode(AUTH_MODE.LOGIN);
            showAuth(AUTH_MODE.LOGIN);
            return;
        }
        await loadAuthProfile();
        setAuthMode(AUTH_MODE.ACCOUNT);
        document.getElementById('authModal').classList.add('show');
    }

    function logout() {
        clearStoredAuth();
        window.location.reload();
    }

    async function initializeAuthUi() {
        updateAuthButtons();
        if (localStorage.getItem('ielts_token')) {
            await loadAuthProfile();
            updateAuthButtons();
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', injectSharedHtml);
        document.addEventListener('DOMContentLoaded', initializeAuthUi);
    } else {
        injectSharedHtml();
        initializeAuthUi();
    }

    window.escapeText = escapeText;
    window.escapeHtml = escapeText;
    window.getCssVar = getCssVar;

    window.submitAuth = submitAuth;
    window.toggleAuthMode = toggleAuthMode;
    window.showAuth = showAuth;
    window.hideAuth = hideAuth;
    window.logout = logout;
    window.togglePasswordVisibility = togglePasswordVisibility;
    window.setPasswordVisibility = setPasswordVisibility;
    window.resetAuthPasswordVisibility = resetAuthPasswordVisibility;
    window.showPasswordResetRequest = showPasswordResetRequest;
    window.showAccountSettings = showAccountSettings;
    window.setAuthMode = setAuthMode;
    window.loadAuthProfile = loadAuthProfile;
    window.updateAuthButtons = updateAuthButtons;

    window.initThemeMode = initThemeMode;
    window.applyThemeMode = applyThemeMode;
    window.getStoredThemeMode = getStoredThemeMode;
    window.syncThemeMenuState = syncThemeMenuState;
    window.closeThemeMenu = closeThemeMenu;
    window.getSystemTheme = getSystemTheme;
})();
