(function () {
    'use strict';

    const app = window.IELTSApp;
    const speaking = app.speaking;
    const refs = app.sharedRefs;
    const state = refs.state;
    const api = refs.api;
    const UI_TEXT = refs.UI_TEXT;

    async function loadPart1() {
        const data = await api('/api/exam/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ topic_id: state.topic.id }),
        });
        state.sessionId = data.session_id;
        state.part1Questions = [data.question_text];
        state.part1Topic = data.part1_topic;
        state.part1Index = 0;
        renderPart1Question();
    }

    function renderPart1Question() {
        const q = state.part1Questions[state.part1Index];
        document.getElementById('part1QuestionText').textContent = q;
        document.getElementById('part1Progress').textContent = `Topic: ${state.part1Topic} | Q${state.part1Index + 1} of 5`;
        document.getElementById('part1TopicBadge').textContent = state.part1Topic;
        document.getElementById('part1Transcript').classList.add('hidden');
        document.getElementById('btnP1Record').disabled = false;
        speaking.setHtml('btnP1Record', UI_TEXT.answerQuestion);
        speaking.playExaminerAudio(q);
    }

    async function toggleP1Recording() {
        if (state.isRecording && state.currentRecordingTarget === 'part1') {
            const stopRecordingFn = typeof window.stopRecording === 'function' ? window.stopRecording : speaking.stopRecording;
            stopRecordingFn(async (wavBlob, clientTranscript) => {
                await uploadAndNext('part1', wavBlob, clientTranscript);
            });
        } else {
            const startRecordingFn = typeof window.startRecording === 'function' ? window.startRecording : speaking.startRecording;
            await startRecordingFn('part1');
            speaking.setHtml('btnP1Record', UI_TEXT.stopAndSubmit);
            document.getElementById('p1RecordingIndicator').classList.remove('hidden');
        }
    }

    async function uploadAndNext(part, wavBlob, clientTranscript = '') {
        document.getElementById(`p${part.slice(-1)}RecordingIndicator`).classList.add('hidden');
        const btn = part === 'part1'
            ? document.getElementById('btnP1Record')
            : document.getElementById('btnP3Record');
        btn.disabled = true;
        btn.innerHTML = UI_TEXT.transcribing;

        try {
            const qText = part === 'part1'
                ? state.part1Questions[state.part1Index]
                : state.part3Questions[state.part3Index];

            const form = new FormData();
            form.append('audio', wavBlob, `${part}_${Date.now()}.wav`);
            form.append('part', part);
            form.append('question_index', part === 'part1' ? state.part1Index : state.part3Index);
            form.append('question_text', qText);
            if (clientTranscript.trim()) form.append('client_transcript', clientTranscript.trim());

            const result = await api(`/api/exam/sessions/${state.sessionId}/upload-part-audio`, {
                method: 'POST',
                body: form,
            });

            const transcriptId = `${part === 'part1' ? 'part1' : 'part3'}Transcript`;
            const transcriptEl = document.getElementById(transcriptId);
            transcriptEl.textContent = result.transcript || '(transcription pending)';
            transcriptEl.classList.remove('hidden');

            if (part === 'part1') state.transcripts.part1 += (result.transcript + ' ');
            else state.transcripts.part3 += (result.transcript + ' ');

            await advanceQuestion(part);
        } catch (e) {
            alert('Upload failed: ' + e.message);
            btn.disabled = false;
            btn.innerHTML = UI_TEXT.tryAgain;
        }
    }

    async function advanceQuestion(part) {
        const btnId = part === 'part1' ? 'btnP1Record' : 'btnP3Record';
        const btn = document.getElementById(btnId);

        btn.disabled = true;
        btn.innerHTML = UI_TEXT.examinerThinking;

        const topicName = part === 'part1' ? state.part1Topic : state.part3Category;
        const currentIndex = part === 'part1' ? state.part1Index : state.part3Index;

        try {
            const nextQ = await api(`/api/exam/sessions/${state.sessionId}/next-question`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    part,
                    topic_name: topicName || 'general',
                    current_index: currentIndex
                })
            });

            setTimeout(() => {
                if (nextQ.is_final || currentIndex >= 4) {
                    if (part === 'part1') {
                        speaking.setPhase('part2prep');
                    } else {
                        speaking.triggerScoring();
                    }
                } else if (part === 'part1') {
                    state.part1Index++;
                    state.part1Questions[state.part1Index] = nextQ.question;
                    renderPart1Question();
                } else {
                    state.part3Index++;
                    state.part3Questions[state.part3Index] = nextQ.question;
                    speaking.renderPart3Question();
                }
            }, 2000);
        } catch (e) {
            alert('Failed to get next question: ' + e.message);
            btn.disabled = false;
            btn.innerHTML = UI_TEXT.tryAgain;
        }
    }

    speaking.loadPart1 = loadPart1;
    speaking.renderPart1Question = renderPart1Question;
    speaking.toggleP1Recording = toggleP1Recording;
    speaking.uploadAndNext = uploadAndNext;
    speaking.advanceQuestion = advanceQuestion;
})();
