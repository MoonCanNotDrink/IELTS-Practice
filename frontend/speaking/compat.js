(function () {
    'use strict';

    const app = window.IELTSApp;
    const speaking = app.speaking;
    const refs = app.sharedRefs;

    window.state = refs.state;
    window.api = refs.api;
    window.UI_TEXT = refs.UI_TEXT;
    window.DEFAULT_PART2_SPEAKING_SECONDS = refs.DEFAULT_PART2_SPEAKING_SECONDS;

    const exports = [
        'setHtml',
        'formatTimerValue',
        'formatDurationBadge',
        'formatSpeakingDuration',
        'refreshAccessToken',
        'startMode',
        'stopActiveCapture',
        'interruptPractice',
        'backToHome',
        'setPhase',
        'show',
        'drawTopic',
        'renderTopicCard',
        'loadPart1',
        'renderPart1Question',
        'toggleP1Recording',
        'uploadAndNext',
        'advanceQuestion',
        'startPrep',
        'skipPrep',
        'toggleP2Recording',
        'uploadPart2',
        'loadPart3',
        'renderPart3Question',
        'toggleP3Recording',
        'audioBlob2Wav',
        'startRecording',
        'stopRecording',
        'startClientTranscription',
        'stopClientTranscription',
        'startTimer',
        'clearTimer',
        'updateTimer',
        'stopExaminerAudio',
        'speakExaminerFallback',
        'playExaminerAudio',
        'triggerScoring',
        'triggerPart2OnlyScoring',
        'showScoringError',
        'updateFlowStatusBanner',
        'displayResults',
        'showTranscript',
        'loadHistory',
        'viewHistoryDetail',
        'initSpeakingRuntime',
    ];

    exports.forEach((name) => {
        if (typeof speaking[name] === 'function') {
            Object.defineProperty(window, name, {
                configurable: true,
                enumerable: true,
                get() { return speaking[name]; },
                set(v) { speaking[name] = v; },
            });
        }
    });
})();
