(function () {
    'use strict';

    const app = window.IELTSApp;
    const speaking = app.speaking;
    const refs = app.sharedRefs;
    const state = refs.state;
    const api = refs.api;

    async function triggerScoring() {
        speaking.setPhase('scoring');
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
        speaking.setPhase('scoring');
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

        const tabsEl = document.getElementById('transcriptTabs');
        const displayEl = document.getElementById('transcriptDisplay');
        const parts = Object.entries(transcripts).filter(([, v]) => v && v.trim());

        tabsEl.innerHTML = parts.map(([part], i) => `
        <button class="btn btn-ghost" style="padding:6px 14px;font-size:0.8rem;${i === 0 ? 'border-color:var(--accent-blue);color:var(--accent-blue)' : ''}"
            id="tab-${part}" onclick="showTranscript('${part}', this)">${part.toUpperCase()}</button>
    `).join('');

        if (parts.length > 0) {
            displayEl.textContent = parts[0][1];
            window._transcriptData = transcripts;
        }

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
            if (feedback[key]) {
                fbHtml += `
            <div class="feedback-item">
                <h3>${label}</h3>
                <p>${feedback[key]}</p>
            </div>`;
            }
        }
        if (improvements.length > 0) {
            fbHtml += `
        <div class="feedback-item">
            <h3>Key Improvements</h3>
            <ul class="improvements-list">
                ${improvements.map((i) => `<li>${i}</li>`).join('')}
            </ul>
        </div>`;
        }
        if (sample) {
            fbHtml += `
        <div class="sample-answer">
            <h3>Band 7+ Sample Answer</h3>
            <p>${sample}</p>
        </div>`;
        }

        document.getElementById('feedbackSection').innerHTML = fbHtml;
    }

    function showTranscript(part, btn) {
        document.getElementById('transcriptDisplay').textContent =
        (window._transcriptData || {})[part] || '(no transcript)';
        document.querySelectorAll('#transcriptTabs .btn').forEach((b) => {
            b.style.borderColor = '';
            b.style.color = '';
        });
        btn.style.borderColor = 'var(--accent-blue)';
        btn.style.color = 'var(--accent-blue)';
    }

    speaking.triggerScoring = triggerScoring;
    speaking.triggerPart2OnlyScoring = triggerPart2OnlyScoring;
    speaking.showScoringError = showScoringError;
    speaking.updateFlowStatusBanner = updateFlowStatusBanner;
    speaking.displayResults = displayResults;
    speaking.showTranscript = showTranscript;
})();
