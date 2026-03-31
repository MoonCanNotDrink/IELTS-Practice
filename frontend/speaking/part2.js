(function () {
    'use strict';

    const app = window.IELTSApp;
    const speaking = app.speaking;
    const refs = app.sharedRefs;
    const state = refs.state;
    const api = refs.api;
    const UI_TEXT = refs.UI_TEXT;

    function startPrep() {
        const startPrepButton = document.getElementById('btnStartPrep');
        if (startPrepButton) {
            startPrepButton.disabled = true;
        }
        document.getElementById('notesInput').focus();
        speaking.startTimer(60, 'part2Timer', () => speaking.setPhase('part2speak'));
    }

    function skipPrep() {
        speaking.clearTimer();
        speaking.setPhase('part2speak');
    }

    async function toggleP2Recording() {
        const btn = document.getElementById('btnP2Record');
        if (state.isRecording && state.currentRecordingTarget === 'part2') {
            btn.disabled = true;
            btn.innerHTML = UI_TEXT.converting;
            speaking.clearTimer();
            const stopRecordingFn = typeof window.stopRecording === 'function' ? window.stopRecording : speaking.stopRecording;
            stopRecordingFn(async (wavBlob, clientTranscript) => {
                document.getElementById('p2RecordingIndicator').classList.add('hidden');
                await uploadPart2(wavBlob, clientTranscript);
            });
        } else {
            const startRecordingFn = typeof window.startRecording === 'function' ? window.startRecording : speaking.startRecording;
            await startRecordingFn('part2');
            btn.innerHTML = UI_TEXT.stopRecording;
            document.getElementById('p2RecordingIndicator').classList.remove('hidden');
            speaking.startTimer(state.part2SpeakingSeconds, 'part2Timer', () => {
                if (state.isRecording && state.currentRecordingTarget === 'part2') {
                    const btn2 = document.getElementById('btnP2Record');
                    if (btn2) btn2.click();
                }
            });
        }
    }

    async function uploadPart2(wavBlob, clientTranscript = '') {
        const form = new FormData();
        form.append('audio', wavBlob, `part2_${Date.now()}.wav`);
        form.append('notes', document.getElementById('notesInput').value || '');
        if (clientTranscript.trim()) form.append('client_transcript', clientTranscript.trim());
        form.append('practice_source', state.practiceSource || 'custom');
        if (state.mode === 'free_practice' && state.part2QuestionText.trim()) {
            form.append('question_text', state.part2QuestionText.trim());
        }

        try {
            const result = await api(`/api/part2/sessions/${state.sessionId}/upload-audio`, {
                method: 'POST',
                body: form,
            });
            state.transcripts.part2 = result.transcript || '';

            if (state.mode === 'full') {
                await speaking.loadPart3();
                speaking.setPhase('part3');
            } else {
                await speaking.triggerPart2OnlyScoring();
            }
        } catch (e) {
            alert('Part 2 upload failed: ' + e.message);
        }
    }

    speaking.startPrep = startPrep;
    speaking.skipPrep = skipPrep;
    speaking.toggleP2Recording = toggleP2Recording;
    speaking.uploadPart2 = uploadPart2;
})();
