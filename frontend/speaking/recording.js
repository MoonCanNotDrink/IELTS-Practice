(function () {
    'use strict';

    const app = window.IELTSApp;
    const speaking = app.speaking;
    const state = app.sharedRefs.state;

    async function audioBlob2Wav(blob) {
        const arrayBuffer = await blob.arrayBuffer();
        const AudioContextCtor = window.AudioContext || window.webkitAudioContext;
        const audioCtx = new AudioContextCtor({ sampleRate: 16000 });
        let audioBuffer;
        try {
            audioBuffer = await audioCtx.decodeAudioData(arrayBuffer);
        } catch (e) {
            console.warn('AudioContext.decodeAudioData failed, sending original blob:', e);
            return blob;
        } finally {
            audioCtx.close();
        }

        const samples = audioBuffer.getChannelData(0);
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
        view.setUint16(20, 1, true);
        view.setUint16(22, numChannels, true);
        view.setUint32(24, sampleRate, true);
        view.setUint32(28, byteRate, true);
        view.setUint16(32, blockAlign, true);
        view.setUint16(34, bitsPerSample, true);
        writeStr(36, 'data');
        view.setUint32(40, dataSize, true);

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
        state.mediaRecorder.ondataavailable = (e) => {
            if (e.data.size > 0) state.audioChunks.push(e.data);
        };
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

    speaking.audioBlob2Wav = audioBlob2Wav;
    speaking.startRecording = startRecording;
    speaking.stopRecording = stopRecording;
    speaking.startClientTranscription = startClientTranscription;
    speaking.stopClientTranscription = stopClientTranscription;
})();
