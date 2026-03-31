/**
 * IELTS Speaking Practice - Full 3-Part Exam Frontend
 * State machine: home -> topic -> part1 -> part2(prep+speak) -> part3 -> scoring
 */

// ========== Config ==========
const API_BASE = '';  // Same-origin - FastAPI serves both
const DEFAULT_PART2_SPEAKING_SECONDS = 120;

const UI_TEXT = {
    topicIcon: '&#127922;',
    drawTopicStart: '&#127922; Draw Topic & Start Exam',
    drawAnother: '&#128260; Draw Another',
    answerQuestion: '&#127908; Answer this Question',
    startPrep: '&#9203; Start 1-Min Prep',
    skipToSpeaking: '&#9197; Skip to Speaking',
    startRecording: '&#127908; Start Recording',
    stopAndSubmit: '&#9209; Stop & Submit',
    loading: '&#9203; Loading...',
    transcribing: '&#9203; Transcribing...',
    converting: '&#9203; Converting...',
    stopRecording: '&#9209; Stop Recording',
    tryAgain: '&#127908; Try Again',
    examinerThinking: '&#129300; Examiner is thinking...',
    startFreePractice: '&#127908; Start Answering',
};

function setHtml(id, html) {
    const el = document.getElementById(id);
    if (el) el.innerHTML = html;
}

function formatTimerValue(seconds) {
    const totalSeconds = Math.max(0, Math.round(Number(seconds) || 0));
    const minutes = Math.floor(totalSeconds / 60);
    const remainder = totalSeconds % 60;
    return `${String(minutes).padStart(2, '0')}:${String(remainder).padStart(2, '0')}`;
}

function formatDurationBadge(seconds) {
    const totalSeconds = Math.max(1, Math.round(Number(seconds) || DEFAULT_PART2_SPEAKING_SECONDS));
    return totalSeconds % 60 === 0 ? `${totalSeconds / 60} Min` : `${totalSeconds} Sec`;
}

function formatSpeakingDuration(seconds) {
    const totalSeconds = Math.max(1, Math.round(Number(seconds) || DEFAULT_PART2_SPEAKING_SECONDS));
    const minutes = Math.floor(totalSeconds / 60);
    const remainder = totalSeconds % 60;
    const parts = [];

    if (minutes) parts.push(`${minutes} ${minutes === 1 ? 'minute' : 'minutes'}`);
    if (remainder) parts.push(`${remainder} ${remainder === 1 ? 'second' : 'seconds'}`);

    return parts.join(' ');
}

// ========== State ==========
const state = {
    mode: null,
    sessionId: null,
    topic: null,
    phase: 'home',       // home|topic|part1|part2prep|part2speak|part3|scoring

    // Part 1
    part1Questions: [],
    part1Topic: '',
    part1Index: 0,

    // Part 3
    part3Questions: [],
    part3Category: '',
    part3Index: 0,

    // Timer
    timerInterval: null,
    timeRemaining: 0,
    part2SpeakingSeconds: DEFAULT_PART2_SPEAKING_SECONDS,
    part2QuestionText: '',

    // Recording (shared)
    mediaRecorder: null,
    audioChunks: [],
    isRecording: false,
    recordingStream: null,
    currentRecordingTarget: null,  // 'part1' | 'part2' | 'part3'
    speechRecognition: null,
    clientTranscripts: { part1: '', part2: '', part3: '' },

    // Transcripts for display
    transcripts: { part1: '', part2: '', part3: '' },
    freePracticeTopicLibrary: {
        officialTopics: [],
        savedTopics: [],
        loaded: false,
        loading: false,
    },
    freePracticeMode: 'library', // 'library' or 'custom'
    freePracticeSelectedSource: null, // 'official' or 'saved'
    freePracticeSelectedId: null,
    
    // Writing
    writingTaskType: null,
    writingPromptId: null,
    writingFpMode: 'library',
    writingFpCustomTaskType: 'task2',
    writingFpTopicLibrary: { prompts: [], loaded: false, loading: false },
    writingFpSelectedPromptId: null,
    writingFpTimerMinutes: 0,
    writingTimerInterval: null,
    writingFpCustomPrompt: null,
};

// ========== API & Auth ==========
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

        showAuth();
        throw new Error('Please log in to continue.');
    }

    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return res.json();
}

window.state = state;
window.api = api;
window.UI_TEXT = UI_TEXT;
window.DEFAULT_PART2_SPEAKING_SECONDS = DEFAULT_PART2_SPEAKING_SECONDS;

// ========== Home ==========
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
        // Skip Part 1/3 steps
        setPhase('topic');
    } else {
        setPhase('topic');
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
    clearTimer();
    stopActiveCapture();
    stopExaminerAudio();
    if (typeof window.stopWritingTimer === 'function') {
        window.stopWritingTimer();
    }
    window.location.href = '/';
}

// ========== Phase Management ==========
function setPhase(phase) {
    state.phase = phase;
    const all = ['topic', 'part1', 'part2', 'part3', 'score'];
    const phaseToStep = {
        'topic': 'topic', 'part1': 'part1',
        'part2prep': 'part2', 'part2speak': 'part2',
        'part3': 'part3', 'scoring': 'score'
    };
    const curStep = phaseToStep[phase] || phase;
    const curIdx = all.indexOf(curStep);

    all.forEach((s, i) => {
        const el = document.getElementById(`step-${s}`);
        if (!el) return;
        el.classList.remove('active', 'completed');
        if (i < curIdx) el.classList.add('completed');
        if (i === curIdx) el.classList.add('active');
    });

    // Show/hide sections
    show('topicCard', phase === 'topic');
    show('part2CueCard', ['part2prep', 'part2speak', 'part1', 'topic'].includes(phase) === false
        ? false
        : ['part2prep', 'part2speak'].includes(phase));
    show('part1Section', phase === 'part1');
    show('part2Section', phase === 'part2prep' || phase === 'part2speak');
    show('part3Section', phase === 'part3');
    show('scoreSection', phase === 'scoring');
    show('sessionActions', phase !== 'home' && phase !== 'scoring');

    if (phase === 'part2prep') {
        // Show cue card and prep controls
        document.getElementById('part2CueTitle').textContent = 'Part 2 - Cue Card';
        document.getElementById('part2TopicDisplay').innerHTML = renderTopicCard(state.topic);
        show('part2CueCard', true);
        const notesEl = document.getElementById('notesInput');
        notesEl.classList.remove('hidden');
        notesEl.readOnly = false;
        notesEl.style.opacity = '';
        notesEl.style.cursor = '';
        document.getElementById('part2PhaseTitle').textContent = 'Preparation Phase';
        document.getElementById('part2Badge').textContent = '1 Min';
        document.getElementById('part2Badge').className = 'status-badge prep';
        document.getElementById('part2TimerLabel').textContent = 'Preparation Time';
        document.getElementById('part2Controls').innerHTML = `
            <button class="btn btn-primary" onclick="startPrep()">${UI_TEXT.startPrep}</button>
            <button class="btn btn-ghost" onclick="skipPrep()">${UI_TEXT.skipToSpeaking}</button>`;
            
        if (state.topic) {
            playExaminerAudio("Now I'm going to give you a topic and I'd like you to talk about it for one to two minutes. Before you talk, you'll have one minute to think about what you're going to say. You can make some notes if you wish. Here is your topic: " + state.topic.title);
        }
    }

    if (phase === 'part2speak') {
        clearTimer();
        document.getElementById('part2CueTitle').textContent = state.mode === 'free_practice'
            ? 'Free Practice Prompt'
            : 'Part 2 - Cue Card';
        document.getElementById('part2TopicDisplay').innerHTML = renderTopicCard(state.topic);
        show('part2CueCard', true);
        const notesEl = document.getElementById('notesInput');
        notesEl.classList.toggle('hidden', state.mode === 'free_practice');
        notesEl.readOnly = true;
        notesEl.style.opacity = state.mode === 'free_practice' ? '' : '0.7';
        notesEl.style.cursor = state.mode === 'free_practice' ? '' : 'default';
        document.getElementById('part2PhaseTitle').textContent = 'Speaking Phase';
        document.getElementById('part2Badge').textContent = formatDurationBadge(state.part2SpeakingSeconds);
        document.getElementById('part2Badge').className = 'status-badge speaking';
        document.getElementById('part2TimerLabel').textContent = 'Speaking Time';
        document.getElementById('part2Timer').textContent = formatTimerValue(state.part2SpeakingSeconds);
        document.getElementById('part2Timer').classList.remove('warning', 'danger');
        document.getElementById('part2Controls').innerHTML = `
            <button class="btn btn-danger btn-full" id="btnP2Record" onclick="toggleP2Recording()">
                ${UI_TEXT.startRecording}</button>`;
    }
}

function show(id, visible) {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.toggle('hidden', !visible);
    if (visible) el.classList.add('fade-in');
}

// ========== Topic Drawing ==========
async function drawTopic() {
    const btn = document.getElementById('btnDrawTopic');
    btn.disabled = true;
    btn.innerHTML = UI_TEXT.loading;

    try {
        const topic = await api('/api/part2/topics/random');
        state.topic = topic;

        document.getElementById('topicContent').innerHTML = renderTopicCard(topic);
        document.getElementById('topicContent').classList.add('fade-in');

        btn.innerHTML = UI_TEXT.drawAnother;
        btn.disabled = false;

        // Next step depends on mode
        if (state.mode === 'full') {
            await loadPart1();
            setPhase('part1');
        } else {
            const session = await api('/api/part2/sessions', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ topic_id: topic.id }),
            });
            state.sessionId = session.session_id;
            setPhase('part2prep');
        }

    } catch (e) {
        alert('Failed to load topic: ' + e.message);
        btn.innerHTML = UI_TEXT.drawTopicStart;
        btn.disabled = false;
    }
}

function renderTopicCard(topic) {
    const safeTopic = topic || {};
    const points = Array.isArray(safeTopic.points) ? safeTopic.points : [];
    return `
        ${safeTopic.categoryLabel ? `<div class="category-badge">${escapeHtml(safeTopic.categoryLabel)}</div>` : ''}
        <h3 class="topic-title">${escapeHtml(safeTopic.title || '')}</h3>
        <p style="color:var(--text-muted);font-size:0.85rem;margin-bottom:12px;">${escapeHtml(safeTopic.introLabel || 'You should say:')}</p>
        <ul class="topic-points">
            ${points.map((point) => `<li>${escapeHtml(point)}</li>`).join('')}
        </ul>`;
}

// ========== Part 1 ==========
async function loadPart1() {
    const data = await api(`/api/exam/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic_id: state.topic.id }),
    });
    // Use the session_id from exam start (replaces the part2 session)
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
    setHtml('btnP1Record', UI_TEXT.answerQuestion);
    playExaminerAudio(q);
}

async function toggleP1Recording() {
    if (state.isRecording && state.currentRecordingTarget === 'part1') {
        stopRecording(async (wavBlob, clientTranscript) => {
            await uploadAndNext('part1', wavBlob, clientTranscript);
        });
    } else {
        await startRecording('part1');
        setHtml('btnP1Record', UI_TEXT.stopAndSubmit);
        document.getElementById('p1RecordingIndicator').classList.remove('hidden');
    }
}

async function uploadAndNext(part, wavBlob, clientTranscript = '') {
    document.getElementById(`p${part.slice(-1)}RecordingIndicator`).classList.add('hidden');
    const btn = part === 'part1' ? document.getElementById('btnP1Record')
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
            method: 'POST', body: form,
        });

        // Show transcript
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
    
    // We want the user to be able to read their transcript for a few seconds.
    // So we don't clear the transcript immediately.
    btn.disabled = true;
    btn.innerHTML = UI_TEXT.examinerThinking;

    const topicName = part === 'part1' ? state.part1Topic : state.part3Category;
    const currentIndex = part === 'part1' ? state.part1Index : state.part3Index;

    try {
        const nextQ = await api(`/api/exam/sessions/${state.sessionId}/next-question`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                part: part,
                topic_name: topicName || 'general',
                current_index: currentIndex
            })
        });

        // Add an artificial delay so the user can read the transcript of their last answer
        setTimeout(() => {
            if (nextQ.is_final || currentIndex >= 4) {
                // End of this part
                if (part === 'part1') {
                    setPhase('part2prep');
                } else {
                    triggerScoring();
                }
            } else {
                // Advance index and add question
                if (part === 'part1') {
                    state.part1Index++;
                    state.part1Questions[state.part1Index] = nextQ.question;
                    renderPart1Question();
                } else {
                    state.part3Index++;
                    state.part3Questions[state.part3Index] = nextQ.question;
                    renderPart3Question();
                }
            }
        }, 2000);
    } catch(e) {
        alert('Failed to get next question: ' + e.message);
        btn.disabled = false;
        btn.innerHTML = UI_TEXT.tryAgain;
    }
}

// ========== Part 2 ==========
function startPrep() {
    const startPrepButton = document.getElementById('btnStartPrep');
    if (startPrepButton) {
        startPrepButton.disabled = true;
    }
    document.getElementById('notesInput').focus();
    startTimer(60, 'part2Timer', () => setPhase('part2speak'));
}

function skipPrep() {
    clearTimer();
    setPhase('part2speak');
}

async function toggleP2Recording() {
    const btn = document.getElementById('btnP2Record');
    if (state.isRecording && state.currentRecordingTarget === 'part2') {
        btn.disabled = true;
        btn.innerHTML = UI_TEXT.converting;
        clearTimer();
        stopRecording(async (wavBlob, clientTranscript) => {
            document.getElementById('p2RecordingIndicator').classList.add('hidden');
            await uploadPart2(wavBlob, clientTranscript);
        });
    } else {
        await startRecording('part2');
        btn.innerHTML = UI_TEXT.stopRecording;
        document.getElementById('p2RecordingIndicator').classList.remove('hidden');
        startTimer(state.part2SpeakingSeconds, 'part2Timer', () => {
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
            method: 'POST', body: form,
        });
        state.transcripts.part2 = result.transcript || '';

        if (state.mode === 'full') {
            await loadPart3();
            setPhase('part3');
        } else {
            await triggerPart2OnlyScoring();
        }
    } catch (e) {
        alert('Part 2 upload failed: ' + e.message);
    }
}

// ========== Part 3 ==========
async function loadPart3() {
    try {
        const data = await api(`/api/exam/sessions/${state.sessionId}/part3-questions`);
        state.part3Category = data.category;
        state.part3Questions = [data.first_question];
        state.part3Index = 0;
        renderPart3Question();
    } catch {
        state.part3Category = "general";
        state.part3Questions = ["How has technology changed the way people communicate in society?"];
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
    setHtml('btnP3Record', UI_TEXT.answerQuestion);
    playExaminerAudio(q);
}

async function toggleP3Recording() {
    if (state.isRecording && state.currentRecordingTarget === 'part3') {
        stopRecording(async (wavBlob, clientTranscript) => {
            await uploadAndNext('part3', wavBlob, clientTranscript);
        });
    } else {
        await startRecording('part3');
        setHtml('btnP3Record', UI_TEXT.stopAndSubmit);
        document.getElementById('p3RecordingIndicator').classList.remove('hidden');
    }
}

// ========== Recording + Audio Conversion ==========

/**
 * Convert any browser audio Blob (WebM/Opus, OGG, MP4, etc.) into a standard
 * 16 kHz mono WAV file using the Web Audio API.
 * WAV is universally accepted by Azure Speech SDK without any format conversion.
 *
 * @param {Blob} blob - Audio blob from MediaRecorder
 * @returns {Promise<Blob>} WAV Blob
 */
async function audioBlob2Wav(blob) {
    const arrayBuffer = await blob.arrayBuffer();
    const AudioContextCtor = window.AudioContext || window['webkitAudioContext'];
    const audioCtx = new AudioContextCtor({ sampleRate: 16000 });
    let audioBuffer;
    try {
        audioBuffer = await audioCtx.decodeAudioData(arrayBuffer);
    } catch (e) {
        console.warn('AudioContext.decodeAudioData failed, sending original blob:', e);
        return blob; // Fall back to original if decode fails
    } finally {
        audioCtx.close();
    }

    // Downmix to mono, resample to 16kHz (AudioContext already resampled)
    const samples = audioBuffer.getChannelData(0); // mono channel
    const wavBuffer = new ArrayBuffer(44 + samples.length * 2);
    const view = new DataView(wavBuffer);

    function writeStr(offset, str) {
        for (let i = 0; i < str.length; i++) view.setUint8(offset + i, str.charCodeAt(i));
    }

    const sampleRate = 16000;
    const numChannels = 1;
    const bitsPerSample = 16;
    const byteRate = sampleRate * numChannels * bitsPerSample / 8;
    const blockAlign = numChannels * bitsPerSample / 8;
    const dataSize = samples.length * 2;

    writeStr(0, 'RIFF');
    view.setUint32(4, 36 + dataSize, true);
    writeStr(8, 'WAVE');
    writeStr(12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);           // PCM format
    view.setUint16(22, numChannels, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, byteRate, true);
    view.setUint16(32, blockAlign, true);
    view.setUint16(34, bitsPerSample, true);
    writeStr(36, 'data');
    view.setUint32(40, dataSize, true);

    // Float32 PCM -> Int16 PCM
    let offset = 44;
    for (let i = 0; i < samples.length; i++, offset += 2) {
        const s = Math.max(-1, Math.min(1, samples[i]));
        view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
    }

    return new Blob([wavBuffer], { type: 'audio/wav' });
}

async function startRecording(target) {
    const stream = await navigator.mediaDevices.getUserMedia({
        audio: { channelCount: 1, sampleRate: 16000, echoCancellation: true, noiseSuppression: true }
    });
    state.recordingStream = stream;
    state.audioChunks = [];
    state.currentRecordingTarget = target;

    const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus' : 'audio/webm';
    state.mediaRecorder = new MediaRecorder(stream, { mimeType });
    state.mediaRecorder.ondataavailable = e => { if (e.data.size > 0) state.audioChunks.push(e.data); };
    state.mediaRecorder.start(1000);
    state.isRecording = true;
    startClientTranscription(target);
}

function stopRecording(onDone) {
    if (!state.mediaRecorder || !state.isRecording) return;
    state.isRecording = false;
    state.mediaRecorder.onstop = async () => {
        state.recordingStream?.getTracks().forEach((track) => {
            track.stop();
        });
        const clientTranscript = await stopClientTranscription(state.currentRecordingTarget);
        const rawBlob = new Blob(state.audioChunks, { type: 'audio/webm' });
        // Convert to WAV so Azure Speech SDK can decode it natively
        const wavBlob = await audioBlob2Wav(rawBlob);
        onDone(wavBlob, clientTranscript);
    };
    state.mediaRecorder.stop();
}

function startClientTranscription(target) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    state.clientTranscripts[target] = '';
    if (!SpeechRecognition) return;

    if (state.speechRecognition) {
        try {
            state.speechRecognition.stop();
        } catch (e) {
            console.warn('Failed to stop previous speech recognition session:', e);
        }
        state.speechRecognition = null;
    }

    const recognition = new SpeechRecognition();
    recognition._target = target;
    recognition._finalTranscript = '';
    recognition.lang = 'en-US';
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;

    recognition.onresult = (event) => {
        for (let i = event.resultIndex; i < event.results.length; i++) {
            const chunk = event.results[i][0]?.transcript || '';
            if (event.results[i].isFinal) {
                recognition._finalTranscript = `${recognition._finalTranscript} ${chunk}`.trim();
            }
        }
        state.clientTranscripts[target] = recognition._finalTranscript.trim();
    };

    recognition.onerror = (event) => {
        console.warn('Browser speech recognition error:', event.error);
    };

    recognition.onend = () => {
        if (state.speechRecognition === recognition) {
            state.speechRecognition = null;
        }
        state.clientTranscripts[target] = recognition._finalTranscript.trim();
    };

    try {
        recognition.start();
        state.speechRecognition = recognition;
    } catch (e) {
        console.warn('Browser speech recognition unavailable:', e);
    }
}

function stopClientTranscription(target) {
    const transcript = () => (state.clientTranscripts[target] || '').trim();
    const recognition = state.speechRecognition;
    if (!recognition) return Promise.resolve(transcript());

    return new Promise((resolve) => {
        let settled = false;
        const previousOnEnd = recognition.onend;
        const finish = () => {
            if (settled) return;
            settled = true;
            if (state.speechRecognition === recognition) {
                state.speechRecognition = null;
            }
            resolve(transcript());
        };

        const timer = setTimeout(finish, 500);
        recognition.onend = () => {
            previousOnEnd?.();
            clearTimeout(timer);
            finish();
        };

        try {
            recognition.stop();
        } catch (e) {
            clearTimeout(timer);
            console.warn('Failed to stop browser speech recognition:', e);
            finish();
        }
    });
}

// ========== Timer ==========
function startTimer(seconds, elementId, onComplete) {
    state.timeRemaining = seconds;
    updateTimer(elementId);
    state.timerInterval = setInterval(() => {
        state.timeRemaining--;
        updateTimer(elementId);
        if (state.timeRemaining <= 0) { clearTimer(); onComplete?.(); }
    }, 1000);
}

function clearTimer() {
    if (state.timerInterval) { clearInterval(state.timerInterval); state.timerInterval = null; }
}

// ========== Audio Examiner TTS ==========
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
    const Utterance = window.SpeechSynthesisUtterance || window['webkitSpeechSynthesisUtterance'];
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
        if (token) headers['Authorization'] = `Bearer ${token}`;

        const res = await fetch('/api/scoring/tts', {
            method: 'POST',
            headers: headers,
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
        console.error("Audio Examiner error:", e);
        stopExaminerAudio();
        speakExaminerFallback(text);
    }
}

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

// ========== Scoring ==========
async function triggerScoring() {
    setPhase('scoring');
    document.getElementById('scoringLoader').classList.remove('hidden');
    document.getElementById('scoreResults').classList.add('hidden');
    const flowBanner = document.getElementById('flowStatusBanner');
    if (flowBanner) flowBanner.classList.add('hidden');

    try {
        const result = await api(`/api/scoring/sessions/${state.sessionId}/score`, { method: 'POST' });
        displayResults(result, result.transcripts || {});
    } catch (e) {
        showScoringError(e.message);
    }
}

async function triggerPart2OnlyScoring() {
    setPhase('scoring');
    document.getElementById('scoringLoader').classList.remove('hidden');
    document.getElementById('scoreResults').classList.add('hidden');
    const flowBanner = document.getElementById('flowStatusBanner');
    if (flowBanner) flowBanner.classList.add('hidden');

    try {
        const result = await api(`/api/part2/sessions/${state.sessionId}/score`, { method: 'POST' });
        displayResults(result, { part2: state.transcripts.part2 });
    } catch (e) {
        showScoringError(e.message);
    }
}

function showScoringError(msg) {
    document.getElementById('scoringLoader').innerHTML = `
        <div style="text-align:center; color:var(--accent-red);">
            <p style="font-size:1.5rem; margin-bottom:12px;">X</p>
            <p style="font-weight:600;">Scoring Failed</p>
            <p style="font-size:0.85rem; color:var(--text-muted); margin-top:8px;">${msg}</p>
            <button class="btn btn-ghost" style="margin-top:16px;" onclick="backToHome()">Try Again</button>
        </div>`;
}

function updateFlowStatusBanner(result, transcripts) {
    const banner = document.getElementById('flowStatusBanner');
    if (!banner) return;

    const partLabels = { part1: 'Part 1', part2: 'Part 2', part3: 'Part 3' };
    const inferredMissing = ['part1', 'part2', 'part3'].filter(
        (part) => !((transcripts?.[part] || '').trim())
    );
    const missingParts = Array.isArray(result?.missing_parts) ? result.missing_parts : inferredMissing;
    const isFullFlow = typeof result?.is_full_flow === 'boolean'
        ? result.is_full_flow
        : missingParts.length === 0;

    if (isFullFlow) {
        banner.classList.add('hidden');
        banner.innerHTML = '';
        return;
    }

    const scopeTitle = result?.exam_scope === 'part2_only'
        ? 'Partial Assessment (Part 2 Only)'
        : 'Partial Assessment';
    const missingText = missingParts.length
        ? missingParts.map((p) => partLabels[p] || p).join(' / ')
        : 'Part 1 / Part 2 / Part 3';

    banner.innerHTML = `
        <div class="flow-status-title">${scopeTitle}</div>
        <div class="flow-status-text">This score does not cover the full IELTS speaking flow. Missing parts: ${missingText}</div>
    `;
    banner.classList.remove('hidden');
}
function displayResults(result, transcripts) {
    document.getElementById('scoringLoader').classList.add('hidden');
    document.getElementById('scoreResults').classList.remove('hidden');
    document.getElementById('scoreResults').classList.add('fade-in');
    updateFlowStatusBanner(result, transcripts);

    const scores = result.scores || {};
    const items = [
        { label: 'Fluency & Coherence', key: 'fluency', icon: '[F]' },
        { label: 'Lexical Resource', key: 'vocabulary', icon: '[V]' },
        { label: 'Grammar', key: 'grammar', icon: '[G]' },
        { label: 'Pronunciation', key: 'pronunciation', icon: '[P]' },
    ];

    let grid = '';
    for (const { label, key, icon } of items) {
        const val = scores[key] ?? 0;
        const cls = val >= 7 ? 'high' : val >= 5.5 ? 'mid' : 'low';
        grid += `<div class="score-item">
            <div class="score-label">${icon} ${label}</div>
            <div class="score-value ${cls}">${val.toFixed(1)}</div>
        </div>`;
    }
    const overall = scores.overall ?? 0;
    grid += `<div class="score-item overall">
        <div class="score-label">Overall Band Score</div>
        <div class="score-value">${overall.toFixed(1)}</div>
    </div>`;
    document.getElementById('scoresGrid').innerHTML = grid;

    // Transcripts
    const tabsEl = document.getElementById('transcriptTabs');
    const displayEl = document.getElementById('transcriptDisplay');
    const parts = Object.entries(transcripts).filter(([, v]) => v && v.trim());

    tabsEl.innerHTML = parts.map(([part], i) => `
        <button class="btn btn-ghost" style="padding:6px 14px;font-size:0.8rem;${i===0?'border-color:var(--accent-blue);color:var(--accent-blue)':''}"
            id="tab-${part}" onclick="showTranscript('${part}', this)">${part.toUpperCase()}</button>
    `).join('');

    if (parts.length > 0) {
        displayEl.textContent = parts[0][1];
        window._transcriptData = transcripts;
    }

    // Feedback
    const feedback = result.feedback || {};
    const improvements = result.key_improvements || [];
    const sample = result.sample_answer || '';

    const FEEDBACK_LABELS = [
        ['fluency', 'Fluency & Coherence'],
        ['vocabulary', 'Lexical Resource'],
        ['grammar', 'Grammar & Accuracy'],
        ['pronunciation', 'Pronunciation'],
        ['overall', 'Overall Feedback'],
    ];

    let fbHtml = '';
    for (const [key, label] of FEEDBACK_LABELS) {
        if (feedback[key]) fbHtml += `
            <div class="feedback-item">
                <h3>${label}</h3>
                <p>${feedback[key]}</p>
            </div>`;
    }
    if (improvements.length > 0) fbHtml += `
        <div class="feedback-item">
            <h3>Key Improvements</h3>
            <ul class="improvements-list">
                ${improvements.map(i => `<li>${i}</li>`).join('')}
            </ul>
        </div>`;
    if (sample) fbHtml += `
        <div class="sample-answer">
            <h3>Band 7+ Sample Answer</h3>
            <p>${sample}</p>
        </div>`;

    document.getElementById('feedbackSection').innerHTML = fbHtml;
}

function showTranscript(part, btn) {
    document.getElementById('transcriptDisplay').textContent =
        (window._transcriptData || {})[part] || '(no transcript)';
    document.querySelectorAll('#transcriptTabs .btn').forEach(b => {
        b.style.borderColor = '';
        b.style.color = '';
    });
    btn.style.borderColor = 'var(--accent-blue)';
    btn.style.color = 'var(--accent-blue)';
}

// ========== History ==========
async function loadHistory() {
    try {
        const history = await api('/api/dashboard/history?limit=5');
        const el = document.getElementById('historyContent');
        if (!history.length) return;

        el.innerHTML = history.map(s => {
            const dateStr = s.date ? new Date(s.date).toLocaleDateString() : '';
            const isScoring = s.scoring_status === 'pending';
            const overall = s.scores?.overall ?? (isScoring ? '...' : '--');
            const scoreColor = (overall >= 7) ? 'var(--accent-green)'
                             : (overall >= 5.5) ? 'var(--accent-amber)'
                             : (overall === '...') ? 'var(--text-muted)'
                             : 'var(--accent-red)';
            
            let icon = '🗣️';
            if (s.module_type === 'writing') {
                icon = s.task_type === 'task1' ? '📊' : '✍️';
            } else {
                icon = s.task_type === 'full_exam' ? '🎓' : (s.task_type === 'part2_only' ? '📝' : '🗣️');
            }

            return `
                <div onclick="viewHistoryDetail('${s.detail_api_path}', '${s.module_type}')"
                    style="display:flex;justify-content:space-between;align-items:center;
                    padding:10px;border-radius:var(--radius-sm);background:var(--bg-glass);
                    margin-bottom:8px;cursor:pointer;transition:background 0.15s;"
                    onmouseenter="this.style.background='rgba(255,255,255,0.07)'"
                    onmouseleave="this.style.background='var(--bg-glass)'">
                    <div style="display:flex;align-items:center;gap:12px;overflow:hidden;">
                        <div style="font-size:1.2rem;flex-shrink:0;">${icon}</div>
                        <div style="overflow:hidden;">
                            <div style="font-size:0.875rem;font-weight:600;color:var(--text-primary);
                                white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:200px;">
                                ${escapeHtml(s.title || 'Practice Session')}</div>
                            <div style="font-size:0.75rem;color:var(--text-muted);">${dateStr}</div>
                        </div>
                    </div>
                    <div style="display:flex;align-items:center;gap:8px;flex-shrink:0;margin-left:8px;">
                        <div style="font-family:var(--font-mono);font-size:1.4rem;font-weight:700;
                            color:${scoreColor};">${overall}</div>
                    </div>
                </div>`;
        }).join('');
        document.getElementById('btnLogout').style.display = 'block';
    } catch {
    }
}

async function viewHistoryDetail(apiPath, moduleType) {
    if (!apiPath) return;
    
    try {
        const result = await api(apiPath);
        document.getElementById('modeSelector').classList.add('hidden');
        
        if (moduleType === 'writing') {
            document.getElementById('writingFlow').classList.remove('hidden');
            document.getElementById('writingPromptSection').classList.add('hidden');
            
            document.getElementById('writingTaskTitle').innerText = result.task_type === 'task1' ? 'Writing Task 1' : 'Writing Task 2';
            document.getElementById('writingTaskIcon').innerText = result.task_type === 'task1' ? '📊' : '✍️';
            
            renderWritingResult(result);
        } else {
            document.getElementById('examFlow').classList.remove('hidden');
            setPhase('scoring');
            document.getElementById('scoringLoader').classList.add('hidden');
            document.getElementById('scoreResults').classList.remove('hidden');
            displayResults(result, result.transcripts || {});
            
            const scoreSection = document.getElementById('scoreSection');
            if (scoreSection && !scoreSection.querySelector('.history-back-btn')) {
                const backBtn = document.createElement('button');
                backBtn.className = 'btn btn-ghost history-back-btn';
                backBtn.style = 'margin-bottom:16px;';
                backBtn.textContent = 'Back to Home';
                backBtn.onclick = backToHome;
                scoreSection.insertBefore(backBtn, scoreSection.firstChild);
            }
        }
    } catch (e) {
        alert('Failed to load session details: ' + e.message);
    }
}

// ========== Initialization ==========
document.addEventListener('DOMContentLoaded', () => {
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
});

// ========== Init ==========
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('examFlow')) {
        setPhase('home');
    }
    initThemeMode();
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
                stopExaminerAudio();
            }
        });
    }
    if (document.getElementById('historyContent')) {
        loadHistory();
    }
    console.log('IELTS Speaking Practice v0.2.9 initialized');
});
