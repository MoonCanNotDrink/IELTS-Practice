(function () {
    'use strict';

    const app = window.IELTSApp;
    const speaking = app.speaking;

    function initSpeakingRuntime() {
        const token = localStorage.getItem('ielts_token');
        const btnLogin = document.getElementById('btnLogin');
        const btnLogout = document.getElementById('btnLogout');

        if (token) {
            if (btnLogin) btnLogin.style.display = 'none';
            if (btnLogout) btnLogout.style.display = 'block';
        } else {
            if (btnLogin) btnLogin.style.display = 'block';
            if (btnLogout) btnLogout.style.display = 'none';
        }

        if (document.getElementById('examFlow')) {
            speaking.setPhase('home');
        }
        window.initThemeMode();
        if (document.getElementById('freePracticePanel')) {
            if (typeof window.resetFreePracticeSetup === 'function') {
                window.resetFreePracticeSetup();
            }
        }
        const audioToggle = document.getElementById('audioModeToggle');
        if (audioToggle) {
            audioToggle.checked = false;
            audioToggle.addEventListener('change', () => {
                if (!audioToggle.checked) {
                    speaking.stopExaminerAudio();
                }
            });
        }
        if (document.getElementById('historyContent')) {
            speaking.loadHistory();
        }
        console.log('IELTS Speaking Practice v0.2.9 initialized');
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initSpeakingRuntime);
    } else {
        initSpeakingRuntime();
    }

    speaking.initSpeakingRuntime = initSpeakingRuntime;
})();
