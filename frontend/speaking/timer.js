(function () {
    'use strict';

    const app = window.IELTSApp;
    const speaking = app.speaking;
    const state = app.sharedRefs.state;

    function updateTimer(id) {
        const el = document.getElementById(id);
        if (!el) return;
        const m = Math.floor(state.timeRemaining / 60);
        const s = state.timeRemaining % 60;
        el.textContent = `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
        el.classList.remove('warning', 'danger');
        if (state.timeRemaining <= 10) el.classList.add('danger');
        else if (state.timeRemaining <= 30) el.classList.add('warning');
    }

    function startTimer(seconds, elementId, onComplete) {
        state.timeRemaining = seconds;
        updateTimer(elementId);
        state.timerInterval = setInterval(() => {
            state.timeRemaining--;
            updateTimer(elementId);
            if (state.timeRemaining <= 0) {
                clearTimer();
                onComplete?.();
            }
        }, 1000);
    }

    function clearTimer() {
        if (state.timerInterval) {
            clearInterval(state.timerInterval);
            state.timerInterval = null;
        }
    }

    speaking.updateTimer = updateTimer;
    speaking.startTimer = startTimer;
    speaking.clearTimer = clearTimer;
})();
