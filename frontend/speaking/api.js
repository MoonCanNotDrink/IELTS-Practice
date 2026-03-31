(function () {
    'use strict';

    const app = window.IELTSApp;
    const refs = app.sharedRefs;

    let refreshRequestPromise = null;

    async function refreshAccessToken() {
        if (refreshRequestPromise) return refreshRequestPromise;

        const refreshToken = localStorage.getItem('ielts_refresh_token');
        if (!refreshToken) {
            throw new Error('No refresh token available');
        }

        refreshRequestPromise = (async () => {
            const res = await fetch('/api/auth/refresh', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ refresh_token: refreshToken }),
            });

            const data = await res.json().catch(() => ({}));
            if (!res.ok || !data.access_token) {
                throw new Error(data.detail || 'Token refresh failed');
            }

            localStorage.setItem('ielts_token', data.access_token);
            if (data.refresh_token) {
                localStorage.setItem('ielts_refresh_token', data.refresh_token);
            }

            return data.access_token;
        })().finally(() => {
            refreshRequestPromise = null;
        });

        return refreshRequestPromise;
    }

    async function api(endpoint, options = {}, retryAttempted = false) {
        const requestOptions = {
            ...options,
            headers: {
                ...(options.headers || {}),
            },
        };

        const token = localStorage.getItem('ielts_token');
        if (token) {
            requestOptions.headers.Authorization = `Bearer ${token}`;
        }

        const res = await fetch(endpoint, requestOptions);

        if (res.status === 401 && !endpoint.includes('/auth/') && !retryAttempted) {
            const hasRefreshToken = Boolean(localStorage.getItem('ielts_refresh_token'));
            if (hasRefreshToken) {
                try {
                    await refreshAccessToken();
                    return api(endpoint, options, true);
                } catch {
                    localStorage.removeItem('ielts_token');
                    localStorage.removeItem('ielts_refresh_token');
                }
            }

            window.showAuth();
            throw new Error('Please log in to continue.');
        }

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || `HTTP ${res.status}`);
        }
        return res.json();
    }

    refs.api = api;
    app.speaking.refreshAccessToken = refreshAccessToken;
    app.speaking.api = api;
    window.api = api;
})();
