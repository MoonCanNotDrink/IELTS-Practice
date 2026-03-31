(function () {
    'use strict';

    const app = window.IELTSApp;
    const speaking = app.speaking;

    let currentExaminerAudio = null;
    let currentExaminerAudioUrl = null;
    const EXAMINER_SPEECH_RATE = 0.9;

    function stopExaminerAudio() {
        if (window.speechSynthesis) {
            window.speechSynthesis.cancel();
        }
        if (currentExaminerAudio) {
            currentExaminerAudio.pause();
            currentExaminerAudio = null;
        }
        if (currentExaminerAudioUrl) {
            URL.revokeObjectURL(currentExaminerAudioUrl);
            currentExaminerAudioUrl = null;
        }
    }

    function speakExaminerFallback(text) {
        const synth = window.speechSynthesis;
        const Utterance = window.SpeechSynthesisUtterance || window.webkitSpeechSynthesisUtterance;
        if (!synth || !Utterance) return false;

        const utterance = new Utterance(text);
        utterance.lang = 'en-US';
        utterance.rate = EXAMINER_SPEECH_RATE;
        synth.cancel();
        synth.speak(utterance);
        return true;
    }

    async function playExaminerAudio(text) {
        const toggle = document.getElementById('audioModeToggle');
        if (!toggle || !toggle.checked) return;

        stopExaminerAudio();

        try {
            const token = localStorage.getItem('ielts_token');
            const headers = { 'Content-Type': 'application/json' };
            if (token) headers.Authorization = `Bearer ${token}`;

            const res = await fetch('/api/scoring/tts', {
                method: 'POST',
                headers,
                body: JSON.stringify({ text })
            });

            if (!res.ok) {
                console.error('TTS failed:', await res.text());
                speakExaminerFallback(text);
                return;
            }

            const blob = await res.blob();
            currentExaminerAudioUrl = URL.createObjectURL(blob);
            currentExaminerAudio = new Audio(currentExaminerAudioUrl);
            currentExaminerAudio.defaultPlaybackRate = EXAMINER_SPEECH_RATE;
            currentExaminerAudio.playbackRate = EXAMINER_SPEECH_RATE;
            currentExaminerAudio.onended = stopExaminerAudio;
            await currentExaminerAudio.play();
        } catch (e) {
            console.error('Audio Examiner error:', e);
            stopExaminerAudio();
            speakExaminerFallback(text);
        }
    }

    speaking.stopExaminerAudio = stopExaminerAudio;
    speaking.speakExaminerFallback = speakExaminerFallback;
    speaking.playExaminerAudio = playExaminerAudio;
})();
