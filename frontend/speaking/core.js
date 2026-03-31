(function () {
    'use strict';

    const existingApp = window.IELTSApp || {};
    window.IELTSApp = existingApp;
    const app = existingApp;
    app.speaking = app.speaking || {};
    app.sharedRefs = app.sharedRefs || {};

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

    app.sharedRefs.DEFAULT_PART2_SPEAKING_SECONDS = DEFAULT_PART2_SPEAKING_SECONDS;
    app.sharedRefs.UI_TEXT = UI_TEXT;

    app.speaking.setHtml = setHtml;
    app.speaking.formatTimerValue = formatTimerValue;
    app.speaking.formatDurationBadge = formatDurationBadge;
    app.speaking.formatSpeakingDuration = formatSpeakingDuration;
})();
