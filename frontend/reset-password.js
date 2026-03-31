(() => {
    function getResetToken() {
        return new URLSearchParams(window.location.search).get('token') || '';
    }

    function hideResetMessages() {
        const errorEl = document.getElementById('resetPasswordError');
        const statusEl = document.getElementById('resetPasswordStatus');
        if (errorEl) {
            errorEl.textContent = '';
            errorEl.style.display = 'none';
        }
        if (statusEl) {
            statusEl.textContent = '';
            statusEl.style.display = 'none';
        }
    }

    function showResetError(message) {
        hideResetMessages();
        const errorEl = document.getElementById('resetPasswordError');
        errorEl.textContent = message;
        errorEl.style.display = 'block';
    }

    function showResetStatus(message) {
        hideResetMessages();
        const statusEl = document.getElementById('resetPasswordStatus');
        statusEl.textContent = message;
        statusEl.style.display = 'block';
    }

    async function validateResetToken(token) {
        const response = await fetch('/api/auth/password-reset/validate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ token }),
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || 'Invalid or expired reset token.');
        }
        return data;
    }

    async function submitResetPassword(event) {
        event.preventDefault();
        const token = getResetToken();
        const password = document.getElementById('resetPasswordInput').value;
        const confirmPassword = document.getElementById('resetPasswordConfirmInput').value;

        if (!password) {
            showResetError('Please enter a new password.');
            return;
        }
        if (!confirmPassword) {
            showResetError('Please confirm your new password.');
            return;
        }
        if (password !== confirmPassword) {
            showResetError('Passwords do not match.');
            return;
        }

        const response = await fetch('/api/auth/password-reset/confirm', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ token, new_password: password }),
        });
        const data = await response.json();
        if (!response.ok) {
            showResetError(data.detail || 'Failed to reset password.');
            return;
        }

        localStorage.removeItem('ielts_token');
        localStorage.removeItem('ielts_refresh_token');
        showResetStatus(data.message || 'Password has been reset successfully.');
        document.getElementById('resetPasswordForm').classList.add('hidden');
        document.getElementById('resetPasswordIntro').textContent = 'Your password has been updated. You can log in again now.';
    }

    async function initializeResetPasswordPage() {
        const token = getResetToken();
        const introEl = document.getElementById('resetPasswordIntro');
        const formEl = document.getElementById('resetPasswordForm');
        hideResetMessages();

        if (!token) {
            introEl.textContent = 'This reset link is missing a token.';
            showResetError('Invalid or expired reset token.');
            return;
        }

        try {
            await validateResetToken(token);
            introEl.textContent = 'Enter your new password below.';
            formEl.classList.remove('hidden');
        } catch (err) {
            introEl.textContent = 'This reset link is no longer valid.';
            showResetError(err.message || 'Invalid or expired reset token.');
        }
    }

    document.addEventListener('DOMContentLoaded', () => {
        const formEl = document.getElementById('resetPasswordForm');
        if (formEl) {
            formEl.addEventListener('submit', submitResetPassword);
        }
        initializeResetPasswordPage();
    });
})();
