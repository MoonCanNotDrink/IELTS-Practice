(() => {
    const app = window.IELTSApp;
    const speaking = app?.speaking;
    const refs = app?.sharedRefs;

    if (refs?.UI_TEXT) {
        window.UI_TEXT = refs.UI_TEXT;
    }
    if (typeof refs?.DEFAULT_PART2_SPEAKING_SECONDS === 'number') {
        window.DEFAULT_PART2_SPEAKING_SECONDS = refs.DEFAULT_PART2_SPEAKING_SECONDS;
    }

    if (typeof speaking?.formatTimerValue === 'function') {
        window.formatTimerValue = speaking.formatTimerValue;
    }
    if (typeof speaking?.formatDurationBadge === 'function') {
        window.formatDurationBadge = speaking.formatDurationBadge;
    }
    if (typeof speaking?.formatSpeakingDuration === 'function') {
        window.formatSpeakingDuration = speaking.formatSpeakingDuration;
    }
    if (typeof speaking?.renderTopicCard === 'function') {
        window.renderTopicCard = speaking.renderTopicCard;
    }

    if (typeof window.DEFAULT_PART2_SPEAKING_SECONDS !== 'number') {
        window.DEFAULT_PART2_SPEAKING_SECONDS = 120;
    }
    if (!window.UI_TEXT) {
        window.UI_TEXT = {
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
    }

    if (typeof window.formatTimerValue !== 'function') {
        window.formatTimerValue = (seconds) => {
            const totalSeconds = Math.max(0, Math.round(Number(seconds) || 0));
            const minutes = Math.floor(totalSeconds / 60);
            const remainder = totalSeconds % 60;
            return `${String(minutes).padStart(2, '0')}:${String(remainder).padStart(2, '0')}`;
        };
    }

    if (typeof window.formatDurationBadge !== 'function') {
        window.formatDurationBadge = (seconds) => {
            const totalSeconds = Math.max(1, Math.round(Number(seconds) || window.DEFAULT_PART2_SPEAKING_SECONDS));
            return totalSeconds % 60 === 0 ? `${totalSeconds / 60} Min` : `${totalSeconds} Sec`;
        };
    }

    if (typeof window.formatSpeakingDuration !== 'function') {
        window.formatSpeakingDuration = (seconds) => {
            const totalSeconds = Math.max(1, Math.round(Number(seconds) || window.DEFAULT_PART2_SPEAKING_SECONDS));
            const minutes = Math.floor(totalSeconds / 60);
            const remainder = totalSeconds % 60;
            const parts = [];

            if (minutes) parts.push(`${minutes} ${minutes === 1 ? 'minute' : 'minutes'}`);
            if (remainder) parts.push(`${remainder} ${remainder === 1 ? 'second' : 'seconds'}`);

            return parts.join(' ');
        };
    }

    if (typeof window.renderTopicCard !== 'function') {
        window.renderTopicCard = (topic) => {
            const safeTopic = topic || {};
            const points = Array.isArray(safeTopic.points) ? safeTopic.points : [];
            return `
        ${safeTopic.categoryLabel ? `<div class="category-badge">${window.escapeHtml(safeTopic.categoryLabel)}</div>` : ''}
        <h3 class="topic-title">${window.escapeHtml(safeTopic.title || '')}</h3>
        <p style="color:var(--text-muted);font-size:0.85rem;margin-bottom:12px;">${window.escapeHtml(safeTopic.introLabel || 'You should say:')}</p>
        <ul class="topic-points">
            ${points.map((point) => `<li>${window.escapeHtml(point)}</li>`).join('')}
        </ul>`;
        };
    }
})();
