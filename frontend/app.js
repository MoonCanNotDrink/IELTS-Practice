/**
 * IELTS Speaking Practice 鈥?Full 3-Part Exam Frontend
 * State machine: home 鈫?topic 鈫?part1 鈫?part2(prep+speak) 鈫?part3 鈫?scoring
 */

// ========== Config ==========
const API_BASE = '';  // Same-origin 鈥?FastAPI serves both

// ========== State ==========
const state = {
    mode: null,          // 'full' | 'part2'
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
};

// ========== API & Auth ==========
async function api(endpoint, options = {}) {
    const token = localStorage.getItem('ielts_token');
    if (token) {
        options.headers = {
            ...options.headers,
            'Authorization': `Bearer ${token}`
        };
    }

    const res = await fetch(endpoint, options);
    
    if (res.status === 401 && !endpoint.includes('/auth/')) {
        showAuth();
        throw new Error("Please log in to continue.");
    }
    
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return res.json();
}

let isAuthModeLogin = true;

function toggleAuthMode() {
    isAuthModeLogin = !isAuthModeLogin;
    document.getElementById('authSubtitle').textContent = isAuthModeLogin ? "Please log in to save your practice history." : "Create an account to track your progress.";
    document.getElementById('btnSubmitAuth').textContent = isAuthModeLogin ? "Log In" : "Register";
    document.getElementById('authToggleText').innerHTML = isAuthModeLogin ? 'No account? <a onclick="toggleAuthMode()">Register here</a>' : 'Have an account? <a onclick="toggleAuthMode()">Log in</a>';
    document.getElementById('inviteCodeGroup').style.display = isAuthModeLogin ? 'none' : 'block';
    document.getElementById('authError').style.display = 'none';
}

function showAuth() {
    document.getElementById('authModal').classList.add('show');
}

function hideAuth() {
    document.getElementById('authModal').classList.remove('show');
}

async function submitAuth() {
    const user = document.getElementById('authUsername').value.trim();
    const pass = document.getElementById('authPassword').value;
    const errEl = document.getElementById('authError');
    errEl.style.display = 'none';

    if(!user || !pass) {
        errEl.textContent = 'Please enter username and password.';
        errEl.style.display = 'block';
        return;
    }

    try {
        let res;
        if (isAuthModeLogin) {
            const fd = new URLSearchParams();
            fd.append('username', user);
            fd.append('password', pass);
            res = await fetch('/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: fd
            });
        } else {
            const invite = document.getElementById('authInviteCode').value.trim();
            res = await fetch('/api/auth/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username: user, password: pass, invite_code: invite })
            });
        }
        
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Authentication failed');

        localStorage.setItem('ielts_token', data.access_token);
        hideAuth();
        document.getElementById('btnLogout').style.display = 'block';
        // Resume initialization if needed
        loadHistory();
    } catch (err) {
        errEl.textContent = err.message;
        errEl.style.display = 'block';
    }
}

function logout() {
    localStorage.removeItem('ielts_token');
    window.location.reload();
}

// ========== Home ==========
function startMode(mode) {
    state.mode = mode;
    document.getElementById('modeSelector').classList.add('hidden');
    document.getElementById('examFlow').classList.remove('hidden');

    if (mode === 'part2') {
        // Skip Part 1/3 steps
        setPhase('topic');
    } else {
        setPhase('topic');
    }
}

function backToHome() {
    // Reset everything
    if (state.speechRecognition) {
        try {
            state.speechRecognition.stop();
        } catch (e) {
            console.warn('Failed to stop browser speech recognition during reset:', e);
        }
        state.speechRecognition = null;
    }
    Object.assign(state, {
        mode: null, sessionId: null, topic: null, phase: 'home',
        part1Questions: [], part1Topic: '', part1Index: 0,
        part3Questions: [], part3Category: '', part3Index: 0,
        audioChunks: [], isRecording: false,
        clientTranscripts: { part1: '', part2: '', part3: '' },
        transcripts: { part1: '', part2: '', part3: '' },
    });
    clearTimer();

    document.getElementById('modeSelector').classList.remove('hidden');
    document.getElementById('examFlow').classList.add('hidden');

    // Reset UI elements
    document.getElementById('topicContent').innerHTML = `
        <div class="empty-state"><span class="big-icon">馃幉</span>
        <p>Draw a random Part 2 topic to begin your mock exam</p></div>`;
    document.getElementById('btnDrawTopic').textContent = '馃幉 Draw Topic & Start Exam';
    document.getElementById('btnDrawTopic').disabled = false;
    document.getElementById('notesInput').value = '';
    document.getElementById('part2Timer').textContent = '01:00';
    document.getElementById('part2Timer').classList.remove('warning', 'danger');
    document.getElementById('part1Transcript').classList.add('hidden');
    document.getElementById('part3Transcript').classList.add('hidden');
    const flowBanner = document.getElementById('flowStatusBanner');
    if (flowBanner) {
        flowBanner.classList.add('hidden');
        flowBanner.innerHTML = '';
    }

    loadHistory();
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

    if (phase === 'part2prep') {
        // Show cue card and prep controls
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
            <button class="btn btn-primary" onclick="startPrep()">鈴?Start 1-Min Prep</button>
            <button class="btn btn-ghost" onclick="skipPrep()">鈴笍 Skip to Speaking</button>`;
            
        if (state.topic) {
            playExaminerAudio("Now I'm going to give you a topic and I'd like you to talk about it for one to two minutes. Before you talk, you'll have one minute to think about what you're going to say. You can make some notes if you wish. Here is your topic: " + state.topic.title);
        }
    }

    if (phase === 'part2speak') {
        show('part2CueCard', true);
        // Keep notes visible but read-only so user can refer to them while speaking
        const notesEl = document.getElementById('notesInput');
        notesEl.classList.remove('hidden');
        notesEl.readOnly = true;
        notesEl.style.opacity = '0.7';
        notesEl.style.cursor = 'default';
        document.getElementById('part2PhaseTitle').textContent = 'Speaking Phase';
        document.getElementById('part2Badge').textContent = '2 Min';
        document.getElementById('part2Badge').className = 'status-badge speaking';
        document.getElementById('part2TimerLabel').textContent = 'Speaking Time';
        document.getElementById('part2Timer').textContent = '02:00';
        document.getElementById('part2Timer').classList.remove('warning', 'danger');
        document.getElementById('part2Controls').innerHTML = `
            <button class="btn btn-danger btn-full" id="btnP2Record" onclick="toggleP2Recording()">
                馃帳 Start Recording</button>`;
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
    btn.textContent = '鈴?Loading...';

    try {
        const topic = await api('/api/part2/topics/random');
        state.topic = topic;

        document.getElementById('topicContent').innerHTML = renderTopicCard(topic);
        document.getElementById('topicContent').classList.add('fade-in');

        btn.textContent = '馃攧 Draw Another';
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
        btn.textContent = '馃幉 Draw Topic & Start Exam';
        btn.disabled = false;
    }
}

function renderTopicCard(topic) {
    return `
        <h3 class="topic-title">${topic.title}</h3>
        <p style="color:var(--text-muted);font-size:0.85rem;margin-bottom:12px;">You should say:</p>
        <ul class="topic-points">
            ${topic.points.map(p => `<li>${p}</li>`).join('')}
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
    document.getElementById('part1Progress').textContent = `Topic: ${state.part1Topic} 鈥?Q${state.part1Index + 1} of 5`;
    document.getElementById('part1TopicBadge').textContent = state.part1Topic;
    document.getElementById('part1Transcript').classList.add('hidden');
    document.getElementById('btnP1Record').disabled = false;
    document.getElementById('btnP1Record').textContent = '馃帳 Answer this Question';
    playExaminerAudio(q);
}

async function toggleP1Recording() {
    if (state.isRecording && state.currentRecordingTarget === 'part1') {
        stopRecording(async (wavBlob, clientTranscript) => {
            await uploadAndNext('part1', wavBlob, clientTranscript);
        });
    } else {
        await startRecording('part1');
        document.getElementById('btnP1Record').textContent = '鈴?Stop & Submit';
        document.getElementById('p1RecordingIndicator').classList.remove('hidden');
    }
}

async function uploadAndNext(part, wavBlob, clientTranscript = '') {
    document.getElementById(`p${part.slice(-1)}RecordingIndicator`).classList.add('hidden');
    const btn = part === 'part1' ? document.getElementById('btnP1Record')
               : document.getElementById('btnP3Record');
    btn.disabled = true;
    btn.textContent = '鈴?Transcribing...';

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
        btn.textContent = '馃帳 Try Again';
    }
}

async function advanceQuestion(part) {
    const btnId = part === 'part1' ? 'btnP1Record' : 'btnP3Record';
    const btn = document.getElementById(btnId);
    
    // We want the user to be able to read their transcript for a few seconds.
    // So we don't clear the transcript immediately.
    btn.disabled = true;
    btn.textContent = '馃 Examiner is thinking...';

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
        btn.textContent = '馃帳 Try Again';
    }
}

// ========== Part 2 ==========
function startPrep() {
    document.getElementById('btnStartPrep') && (document.getElementById('btnStartPrep').disabled = true);
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
        btn.textContent = '鈴?Converting...';
        stopRecording(async (wavBlob, clientTranscript) => {
            document.getElementById('p2RecordingIndicator').classList.add('hidden');
            await uploadPart2(wavBlob, clientTranscript);
        });
    } else {
        await startRecording('part2');
        btn.textContent = '鈴?Stop Recording';
        document.getElementById('p2RecordingIndicator').classList.remove('hidden');
        startTimer(120, 'part2Timer', () => {
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
    document.getElementById('btnP3Record').disabled = false;
    document.getElementById('btnP3Record').textContent = '馃帳 Answer this Question';
    playExaminerAudio(q);
}

async function toggleP3Recording() {
    if (state.isRecording && state.currentRecordingTarget === 'part3') {
        stopRecording(async (wavBlob, clientTranscript) => {
            await uploadAndNext('part3', wavBlob, clientTranscript);
        });
    } else {
        await startRecording('part3');
        document.getElementById('btnP3Record').textContent = '鈴?Stop & Submit';
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
    const audioCtx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
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

    // Float32 PCM 鈫?Int16 PCM
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
        state.recordingStream?.getTracks().forEach(t => t.stop());
        const clientTranscript = await stopClientTranscription(state.currentRecordingTarget);
        const rawBlob = new Blob(state.audioChunks, { type: 'audio/webm' });
        // Convert to WAV so Azure Speech SDK can decode it natively
        const wavBlob = await audioBlob2Wav(rawBlob);
        onDone(wavBlob, clientTranscript);
    };
    state.mediaRecorder.stop();
    clearTimer();
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

    let finalTranscript = '';
    const recognition = new SpeechRecognition();
    recognition.lang = 'en-US';
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;

    recognition.onresult = (event) => {
        let interimTranscript = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
            const chunk = event.results[i][0]?.transcript || '';
            if (event.results[i].isFinal) {
                finalTranscript = `${finalTranscript} ${chunk}`.trim();
            } else {
                interimTranscript = `${interimTranscript} ${chunk}`.trim();
            }
        }
        state.clientTranscripts[target] = `${finalTranscript} ${interimTranscript}`.trim();
    };

    recognition.onerror = (event) => {
        console.warn('Browser speech recognition error:', event.error);
    };

    recognition.onend = () => {
        if (state.speechRecognition === recognition) {
            state.speechRecognition = null;
        }
        state.clientTranscripts[target] = finalTranscript.trim() || state.clientTranscripts[target];
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
    clearTimer();
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

function stopExaminerAudio() {
    if (currentExaminerAudio) {
        currentExaminerAudio.pause();
        currentExaminerAudio = null;
    }
    if (currentExaminerAudioUrl) {
        URL.revokeObjectURL(currentExaminerAudioUrl);
        currentExaminerAudioUrl = null;
    }
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
            return;
        }
        
        const blob = await res.blob();
        currentExaminerAudioUrl = URL.createObjectURL(blob);
        currentExaminerAudio = new Audio(currentExaminerAudioUrl);
        currentExaminerAudio.onended = stopExaminerAudio;
        await currentExaminerAudio.play();
    } catch (e) {
        console.error("Audio Examiner error:", e);
        stopExaminerAudio();
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
        ? '\u975e\u5168\u6d41\u7a0b\u6210\u7ee9\uff08Part 2 \u5355\u9879\u7ec3\u4e60\uff09'
        : '\u975e\u5168\u6d41\u7a0b\u6210\u7ee9';
    const missingText = missingParts.length
        ? missingParts.map((p) => partLabels[p] || p).join(' / ')
        : 'Part 1 / Part 2 / Part 3';

    banner.innerHTML = `
        <div class="flow-status-title">${scopeTitle}</div>
        <div class="flow-status-text">\u672c\u6b21\u8bc4\u5206\u672a\u8986\u76d6\u5b8c\u6574 IELTS \u53e3\u8bed\u5168\u6d41\u7a0b\u3002\u7f3a\u5931\u90e8\u5206\uff1a${missingText}</div>
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
        const history = await api('/api/scoring/history?limit=5');
        const el = document.getElementById('historyContent');
        if (!history.length) return;

        el.innerHTML = history.map(s => {
            const date = s.date ? new Date(s.date).toLocaleDateString('zh-CN') : '';
            const overall = s.scores?.overall ?? '--';
            const scoreColor = (overall >= 7) ? 'var(--accent-green)'
                             : (overall >= 5.5) ? 'var(--accent-amber)'
                             : 'var(--accent-red)';
            return `
                <div onclick="viewSessionDetail(${s.session_id})"
                    style="display:flex;justify-content:space-between;align-items:center;
                    padding:10px;border-radius:var(--radius-sm);background:var(--bg-glass);
                    margin-bottom:8px;cursor:pointer;transition:background 0.15s;"
                    onmouseenter="this.style.background='rgba(255,255,255,0.07)'"
                    onmouseleave="this.style.background='var(--bg-glass)'">
                    <div>
                        <div style="font-size:0.875rem;font-weight:600;color:var(--text-primary);
                            white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:250px;">
                            ${s.topic_title}</div>
                        <div style="font-size:0.75rem;color:var(--text-muted);">${date}</div>
                    </div>
                    <div style="display:flex;align-items:center;gap:8px;flex-shrink:0;margin-left:12px;">
                        <div style="font-family:var(--font-mono);font-size:1.4rem;font-weight:700;
                            color:${scoreColor};">${overall}</div>
                        <span style="color:var(--text-muted);font-size:0.9rem;">-</span>
                    </div>
                </div>`;
        }).join('');
        document.getElementById('btnLogout').style.display = 'block';
    } catch {
        // Silently fail: history is optional
    }
}

async function viewSessionDetail(sessionId) {
    try {
        const result = await api(`/api/scoring/sessions/${sessionId}/detail`);
        // Hide the mode-selector, show the exam flow in scoring phase
        document.getElementById('modeSelector').classList.add('hidden');
        document.getElementById('examFlow').classList.remove('hidden');
        // Show scoring section only
        setPhase('scoring');
        document.getElementById('scoringLoader').classList.add('hidden');
        document.getElementById('scoreResults').classList.remove('hidden');
        displayResults(result, result.transcripts || {});
        // Add a back-to-home button at the top of the scoring area
        const backBtn = document.createElement('button');
        backBtn.className = 'btn btn-ghost';
        backBtn.style = 'margin-bottom:16px;';
        backBtn.textContent = 'Back to Home';
        backBtn.onclick = backToHome;
        const scoreSection = document.getElementById('scoreSection');
        if (scoreSection && !scoreSection.querySelector('.history-back-btn')) {
            backBtn.classList.add('history-back-btn');
            scoreSection.insertBefore(backBtn, scoreSection.firstChild);
        }
    } catch(e) {
        alert('Failed to load history: ' + e.message);
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
    setPhase('home');
    const audioToggle = document.getElementById('audioModeToggle');
    if (audioToggle) {
        audioToggle.checked = false;
        audioToggle.addEventListener('change', () => {
            if (!audioToggle.checked) {
                stopExaminerAudio();
            }
        });
    }
    loadHistory();
    console.log('IELTS Speaking Practice v0.2.8 initialized');
});

