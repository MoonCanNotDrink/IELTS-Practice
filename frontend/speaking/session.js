(function () {
    'use strict';

    const app = window.IELTSApp;
    const speaking = app.speaking;
    const refs = app.sharedRefs;
    const state = refs.state;
    const DEFAULT_PART2_SPEAKING_SECONDS = refs.DEFAULT_PART2_SPEAKING_SECONDS;

    function startMode(mode) {
        if (typeof window.resetFreePracticeSetup === 'function') {
            window.resetFreePracticeSetup();
        }
        state.mode = mode;
        state.part2SpeakingSeconds = DEFAULT_PART2_SPEAKING_SECONDS;
        state.part2QuestionText = '';
        document.getElementById('modeSelector').classList.add('hidden');
        document.getElementById('examFlow').classList.remove('hidden');

        if (mode === 'part2') {
            speaking.setPhase('topic');
        } else {
            speaking.setPhase('topic');
        }
    }

    function stopActiveCapture() {
        if (state.mediaRecorder) {
            try {
                state.mediaRecorder.ondataavailable = null;
                state.mediaRecorder.onstop = null;
                if (state.mediaRecorder.state !== 'inactive') {
                    state.mediaRecorder.stop();
                }
            } catch (e) {
                console.warn('Failed to stop media recorder during reset:', e);
            }
        }

        if (state.recordingStream) {
            try {
                state.recordingStream.getTracks().forEach((track) => {
                    track.stop();
                });
            } catch (e) {
                console.warn('Failed to stop recording stream during reset:', e);
            }
        }

        if (state.speechRecognition) {
            try {
                state.speechRecognition.stop();
            } catch (e) {
                console.warn('Failed to stop browser speech recognition during reset:', e);
            }
        }

        state.mediaRecorder = null;
        state.recordingStream = null;
        state.speechRecognition = null;
        state.audioChunks = [];
        state.isRecording = false;
        state.currentRecordingTarget = null;
    }

    function interruptPractice() {
        if (state.phase === 'home' && state.mode !== 'writing') return;
        const confirmed = window.confirm('Stop current practice and return to home? Current progress will be discarded.');
        if (!confirmed) return;
        if (typeof window.stopWritingTimer === 'function') {
            window.stopWritingTimer();
        }
        backToHome();
    }

    function backToHome() {
        speaking.clearTimer();
        stopActiveCapture();
        speaking.stopExaminerAudio();
        if (typeof window.stopWritingTimer === 'function') {
            window.stopWritingTimer();
        }
        window.location.href = '/';
    }

    speaking.startMode = startMode;
    speaking.stopActiveCapture = stopActiveCapture;
    speaking.interruptPractice = interruptPractice;
    speaking.backToHome = backToHome;
})();
