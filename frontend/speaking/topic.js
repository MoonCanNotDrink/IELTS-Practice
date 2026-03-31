(function () {
    'use strict';

    const app = window.IELTSApp;
    const speaking = app.speaking;
    const refs = app.sharedRefs;
    const state = refs.state;
    const api = refs.api;
    const UI_TEXT = refs.UI_TEXT;

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

            if (state.mode === 'full') {
                await speaking.loadPart1();
                speaking.setPhase('part1');
            } else {
                const session = await api('/api/part2/sessions', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ topic_id: topic.id }),
                });
                state.sessionId = session.session_id;
                speaking.setPhase('part2prep');
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
        ${safeTopic.categoryLabel ? `<div class="category-badge">${window.escapeHtml(safeTopic.categoryLabel)}</div>` : ''}
        <h3 class="topic-title">${window.escapeHtml(safeTopic.title || '')}</h3>
        <p style="color:var(--text-muted);font-size:0.85rem;margin-bottom:12px;">${window.escapeHtml(safeTopic.introLabel || 'You should say:')}</p>
        <ul class="topic-points">
            ${points.map((point) => `<li>${window.escapeHtml(point)}</li>`).join('')}
        </ul>`;
    }

    speaking.drawTopic = drawTopic;
    speaking.renderTopicCard = renderTopicCard;
})();
