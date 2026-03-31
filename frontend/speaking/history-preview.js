(function () {
    'use strict';

    const app = window.IELTSApp;
    const speaking = app.speaking;
    const refs = app.sharedRefs;
    const api = refs.api;

    async function loadHistory() {
        try {
            const history = await api('/api/dashboard/history?limit=5');
            const el = document.getElementById('historyContent');
            if (!history.length) return;

            el.innerHTML = history.map((s) => {
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
                                ${window.escapeHtml(s.title || 'Practice Session')}</div>
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

                window.renderWritingResult(result);
            } else {
                document.getElementById('examFlow').classList.remove('hidden');
                speaking.setPhase('scoring');
                document.getElementById('scoringLoader').classList.add('hidden');
                document.getElementById('scoreResults').classList.remove('hidden');
                speaking.displayResults(result, result.transcripts || {});

                const scoreSection = document.getElementById('scoreSection');
                if (scoreSection && !scoreSection.querySelector('.history-back-btn')) {
                    const backBtn = document.createElement('button');
                    backBtn.className = 'btn btn-ghost history-back-btn';
                    backBtn.style = 'margin-bottom:16px;';
                    backBtn.textContent = 'Back to Home';
                    backBtn.onclick = speaking.backToHome;
                    scoreSection.insertBefore(backBtn, scoreSection.firstChild);
                }
            }
        } catch (e) {
            alert('Failed to load session details: ' + e.message);
        }
    }

    speaking.loadHistory = loadHistory;
    speaking.viewHistoryDetail = viewHistoryDetail;
})();
