(function () {
    'use strict';

    const app = window.IELTSApp;
    const refs = app.sharedRefs;
    const DEFAULT_PART2_SPEAKING_SECONDS = refs.DEFAULT_PART2_SPEAKING_SECONDS;

    const state = {
        mode: null,
        sessionId: null,
        topic: null,
        phase: 'home',

        part1Questions: [],
        part1Topic: '',
        part1Index: 0,

        part3Questions: [],
        part3Category: '',
        part3Index: 0,

        timerInterval: null,
        timeRemaining: 0,
        part2SpeakingSeconds: DEFAULT_PART2_SPEAKING_SECONDS,
        part2QuestionText: '',

        mediaRecorder: null,
        audioChunks: [],
        isRecording: false,
        recordingStream: null,
        currentRecordingTarget: null,
        speechRecognition: null,
        clientTranscripts: { part1: '', part2: '', part3: '' },

        transcripts: { part1: '', part2: '', part3: '' },
        freePracticeTopicLibrary: {
            officialTopics: [],
            savedTopics: [],
            loaded: false,
            loading: false,
        },
        freePracticeMode: 'library',
        freePracticeSelectedSource: null,
        freePracticeSelectedId: null,

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

    refs.state = state;
    window.state = state;
})();
