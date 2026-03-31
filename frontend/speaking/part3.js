(function () {
    'use strict';

    const app = window.IELTSApp;
    const speaking = app.speaking;
    const refs = app.sharedRefs;
    const state = refs.state;
    const api = refs.api;
    const UI_TEXT = refs.UI_TEXT;

    async function loadPart3() {
        try {
            const data = await api(`/api/exam/sessions/${state.sessionId}/part3-questions`);
            state.part3Category = data.category;
            state.part3Questions = [data.first_question];
            state.part3Index = 0;
            renderPart3Question();
        } catch {
            state.part3Category = 'general';
            state.part3Questions = ['How has technology changed the way people communicate in society?'];
            state.part3Index = 0;
            renderPart3Question();
        }
    }

    function renderPart3Question() {
        const q = state.part3Questions[state.part3Index];
        document.getElementById('part3QuestionText').textContent = q;
        document.getElementById('part3Progress').textContent = `Q${state.part3Index + 1} of 5`;
        document.getElementById('part3Transcript').classList.add('hidden');
        document.getElementById('p3RecordingIndicator').classList.add('hidden');
        document.getElementById('btnP3Record').disabled = false;
        speaking.setHtml('btnP3Record', UI_TEXT.answerQuestion);
        speaking.playExaminerAudio(q);
    }

    async function toggleP3Recording() {
        if (state.isRecording && state.currentRecordingTarget === 'part3') {
            const stopRecordingFn = typeof window.stopRecording === 'function' ? window.stopRecording : speaking.stopRecording;
            stopRecordingFn(async (wavBlob, clientTranscript) => {
                await speaking.uploadAndNext('part3', wavBlob, clientTranscript);
            });
        } else {
            const startRecordingFn = typeof window.startRecording === 'function' ? window.startRecording : speaking.startRecording;
            await startRecordingFn('part3');
            speaking.setHtml('btnP3Record', UI_TEXT.stopAndSubmit);
            document.getElementById('p3RecordingIndicator').classList.remove('hidden');
        }
    }

    speaking.loadPart3 = loadPart3;
    speaking.renderPart3Question = renderPart3Question;
    speaking.toggleP3Recording = toggleP3Recording;
})();
