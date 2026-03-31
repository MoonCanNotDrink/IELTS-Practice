(function () {
    let trendChartInstance = null;
    let radarChartInstance = null;
    let cachedHistoryData = [];

    const BLUE = '#3b82f6';
    const GREEN = '#10b981';
    const AMBER = '#f59e0b';
    const PURPLE = '#8b5cf6';
    const PINK = '#ec4899';

    function applyChartThemeDefaults() {
        if (!window.Chart) return;
        Chart.defaults.color = getCssVar('--text-secondary', '#94a3b8');
        Chart.defaults.borderColor = getCssVar('--border-subtle', 'rgba(255,255,255,0.06)');
        Chart.defaults.font.family = "'Inter', sans-serif";
    }

    function renderHistoryData(history) {
        renderStats(history);
        renderSessionList(history);
        if (!window.Chart) return;
        renderTrendChart(history);
        renderRadarChart(history);
    }

    function makeGradient(ctx, color) {
        const gradient = ctx.createLinearGradient(0, 0, 0, 280);
        gradient.addColorStop(0, color + '40');
        gradient.addColorStop(1, color + '00');
        return gradient;
    }

    function hasScore(value) {
        return value !== null && value !== undefined;
    }

    function formatScore(value) {
        return hasScore(value) ? Number(value).toFixed(1) : '\u2014';
    }

    function getScoreColor(value) {
        if (!hasScore(value)) return '#64748b';
        if (value >= 7) return 'var(--accent-green)';
        if (value >= 5.5) return 'var(--accent-amber)';
        return 'var(--accent-red)';
    }

    function isSuccessfulScore(session) {
        return session?.scoring_status !== 'error' && hasScore(session?.scores?.overall);
    }

    function getScoredHistory(history) {
        return history.filter(isSuccessfulScore);
    }

    async function loadHistory() {
        const token = localStorage.getItem('ielts_token');
        if (!token) {
            showAuth();
            return;
        }

        const moduleValue = document.getElementById('moduleFilter')?.value || 'all';
        const taskValue = document.getElementById('taskFilter')?.value || 'all';
        const query = new URLSearchParams({ limit: '20' });
        if (moduleValue !== 'all') query.set('module_type', moduleValue);
        if (taskValue !== 'all') query.set('task_type', taskValue);

        const res = await fetch(`/api/dashboard/history?${query.toString()}`, {
            headers: { Authorization: `Bearer ${token}` },
        });

        if (res.status === 401) {
            localStorage.removeItem('ielts_token');
            showAuth();
            return;
        }

        const history = await res.json();
        cachedHistoryData = Array.isArray(history) ? history : [];
        renderHistoryData(cachedHistoryData);
        document.getElementById('btnLogin').style.display = 'none';
        document.getElementById('btnLogout').style.display = 'block';
    }

    function renderStats(history) {
        const complete = getScoredHistory(history);
        document.getElementById('statTotal').textContent = complete.length || '0';

        if (!complete.length) {
            ['statBest', 'statAvg', 'statLatest'].forEach((id) => {
                document.getElementById(id).textContent = '\u2014';
            });
            return;
        }

        const scores = complete.map((session) => session.scores.overall);
        document.getElementById('statBest').textContent = formatScore(Math.max(...scores));
        document.getElementById('statAvg').textContent = formatScore(scores.reduce((sum, score) => sum + score, 0) / scores.length);

        const latestEl = document.getElementById('statLatest');
        const latest = scores[0];
        latestEl.textContent = formatScore(latest);
        latestEl.className = 'score-value ' + (latest >= 7 ? 'high' : latest >= 5.5 ? 'mid' : 'low');
    }

    function renderTrendChart(history) {
        if (trendChartInstance) {
            trendChartInstance.destroy();
            trendChartInstance = null;
        }

        const data = [...getScoredHistory(history)].reverse();
        const labels = data.map((session, index) => {
            const date = session.date ? new Date(session.date) : null;
            return date ? `${date.getMonth() + 1}/${date.getDate()}` : `#${index + 1}`;
        });
        const modules = new Set(data.map((item) => item.module_type));
        const speakingOnly = modules.size === 1 && modules.has('speaking');
        const writingOnly = modules.size === 1 && modules.has('writing');
        const legend = document.getElementById('trendLegend');

        if (legend) {
            const legendItems = speakingOnly
                ? [
                    ['var(--accent-blue)', 'Overall'],
                    ['var(--accent-green)', 'Fluency'],
                    ['var(--accent-amber)', 'Vocabulary'],
                    ['var(--accent-purple)', 'Grammar'],
                    ['#ec4899', 'Pronunciation'],
                ]
                : writingOnly
                    ? [
                        ['var(--accent-blue)', 'Overall'],
                        ['var(--accent-green)', 'Task'],
                        ['var(--accent-amber)', 'Coherence'],
                        ['var(--accent-purple)', 'Lexical'],
                        ['#ec4899', 'Grammar'],
                    ]
                    : [['var(--accent-blue)', 'Overall']];
            legend.innerHTML = legendItems.map(([color, label]) => `<span class="legend-item" style="color:${color}">● ${label}</span>`).join('');
        }

        const ctx = document.getElementById('trendChart').getContext('2d');
        const datasets = [
            {
                label: 'Overall',
                data: data.map((session) => session.scores?.overall ?? null),
                borderColor: BLUE,
                backgroundColor: makeGradient(ctx, BLUE),
                tension: 0.4,
                fill: true,
                pointRadius: 5,
                pointHoverRadius: 7,
                borderWidth: 2.5,
            },
        ];

        if (speakingOnly) {
            datasets.push(
                {
                    label: 'Fluency',
                    data: data.map((session) => session.scores?.fluency ?? null),
                    borderColor: GREEN,
                    tension: 0.4,
                    fill: false,
                    pointRadius: 3,
                    borderWidth: 1.5,
                    borderDash: [4, 4],
                },
                {
                    label: 'Vocabulary',
                    data: data.map((session) => session.scores?.vocabulary ?? null),
                    borderColor: AMBER,
                    tension: 0.4,
                    fill: false,
                    pointRadius: 3,
                    borderWidth: 1.5,
                    borderDash: [4, 4],
                },
                {
                    label: 'Grammar',
                    data: data.map((session) => session.scores?.grammar ?? null),
                    borderColor: PURPLE,
                    tension: 0.4,
                    fill: false,
                    pointRadius: 3,
                    borderWidth: 1.5,
                    borderDash: [4, 4],
                },
                {
                    label: 'Pronunciation',
                    data: data.map((session) => session.scores?.pronunciation ?? null),
                    borderColor: PINK,
                    tension: 0.4,
                    fill: false,
                    pointRadius: 3,
                    borderWidth: 1.5,
                    borderDash: [4, 4],
                },
            );
        } else if (writingOnly) {
            datasets.push(
                {
                    label: 'Task',
                    data: data.map((session) => session.scores?.task ?? null),
                    borderColor: GREEN,
                    tension: 0.4,
                    fill: false,
                    pointRadius: 3,
                    borderWidth: 1.5,
                    borderDash: [4, 4],
                },
                {
                    label: 'Coherence',
                    data: data.map((session) => session.scores?.coherence ?? null),
                    borderColor: AMBER,
                    tension: 0.4,
                    fill: false,
                    pointRadius: 3,
                    borderWidth: 1.5,
                    borderDash: [4, 4],
                },
                {
                    label: 'Lexical',
                    data: data.map((session) => session.scores?.lexical ?? null),
                    borderColor: PURPLE,
                    tension: 0.4,
                    fill: false,
                    pointRadius: 3,
                    borderWidth: 1.5,
                    borderDash: [4, 4],
                },
                {
                    label: 'Grammar',
                    data: data.map((session) => session.scores?.grammar ?? null),
                    borderColor: PINK,
                    tension: 0.4,
                    fill: false,
                    pointRadius: 3,
                    borderWidth: 1.5,
                    borderDash: [4, 4],
                },
            );
        }

        trendChartInstance = new Chart(ctx, {
            type: 'line',
            data: { labels, datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: getCssVar('--bg-secondary', '#111827'),
                        padding: 12,
                        cornerRadius: 8,
                        titleColor: getCssVar('--text-primary', '#f1f5f9'),
                        bodyColor: getCssVar('--text-secondary', '#94a3b8'),
                    },
                },
                scales: {
                    y: {
                        min: 0,
                        max: 9,
                        ticks: { stepSize: 1 },
                        grid: { color: getCssVar('--border-subtle', 'rgba(255,255,255,0.06)') },
                    },
                    x: { grid: { display: false } },
                },
            },
        });
    }

    function renderRadarChart(history) {
        if (radarChartInstance) {
            radarChartInstance.destroy();
            radarChartInstance = null;
        }

        const recent = getScoredHistory(history).slice(0, 5);
        const radarCard = document.getElementById('radarCard');
        const modules = new Set(recent.map((item) => item.module_type));
        if (!recent.length || modules.size > 1) {
            radarCard.style.display = recent.length ? 'none' : '';
            return;
        }
        radarCard.style.display = '';

        const avg = (key) => {
            const values = recent.map((session) => session.scores?.[key]).filter(hasScore);
            return values.length ? values.reduce((sum, score) => sum + score, 0) / values.length : 0;
        };

        const writingOnly = modules.has('writing');
        const labels = writingOnly
            ? ['Task', 'Coherence', 'Lexical', 'Grammar']
            : ['Fluency', 'Vocabulary', 'Grammar', 'Pronunciation'];
        const keys = writingOnly
            ? ['task', 'coherence', 'lexical', 'grammar']
            : ['fluency', 'vocabulary', 'grammar', 'pronunciation'];

        const ctx = document.getElementById('radarChart').getContext('2d');
        radarChartInstance = new Chart(ctx, {
            type: 'radar',
            data: {
                labels,
                datasets: [{
                    label: 'Average (last 5)',
                    data: keys.map(avg),
                    backgroundColor: 'rgba(59,130,246,0.15)',
                    borderColor: BLUE,
                    borderWidth: 2,
                    pointBackgroundColor: BLUE,
                    pointRadius: 4,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    r: {
                        min: 0,
                        max: 9,
                        ticks: { stepSize: 1.5, backdropColor: 'transparent' },
                        grid: { color: getCssVar('--border-subtle', 'rgba(255,255,255,0.06)') },
                        angleLines: { color: getCssVar('--border-subtle', 'rgba(255,255,255,0.06)') },
                        pointLabels: { color: getCssVar('--text-secondary', '#94a3b8'), font: { size: 12 } },
                    },
                },
            },
        });
    }

    function renderSessionList(history) {
        const el = document.getElementById('historyList');
        if (!history.length) {
            el.innerHTML = '<p style="color:var(--text-muted);text-align:center;padding:24px;">No completed sessions yet. Start practicing!</p>';
            return;
        }

        el.innerHTML = history.map((session) => {
            const overall = session.scores?.overall;
            const scoreReady = isSuccessfulScore(session);
            const scoreColor = scoreReady ? getScoreColor(overall) : '#64748b';
            const date = session.date ? new Date(session.date).toLocaleString('zh-CN', {
                month: 'numeric',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
            }) : '';
            const scores = session.scores || {};
            const statusText = session.scoring_status === 'error'
                ? 'Scoring fallback used'
                : (session.scoring_status === 'pending' ? 'Scoring pending' : '');

            let icon = '🗣️';
            if (session.module_type === 'writing') {
                icon = session.task_type === 'task1' ? '📊' : '✍️';
            } else {
                icon = session.task_type === 'full_exam' ? '🎓' : (session.task_type === 'part2_only' ? '📝' : '🗣️');
            }

            let dimsHtml = '';
            if (session.module_type === 'writing') {
                const writingDims = ['task', 'coherence', 'lexical', 'grammar'];
                dimsHtml = writingDims.map((key) => `
                    <span style="font-size:0.72rem;color:var(--text-secondary);">
                        ${key.slice(0, 4).toUpperCase()} <b style="color:${scoreReady ? getScoreColor(scores[key]) : '#64748b'}">${scoreReady ? formatScore(scores[key]) : '\u2014'}</b>
                    </span>`).join('');
            } else {
                dimsHtml = ['fluency', 'vocabulary', 'grammar', 'pronunciation'].map((key) => `
                    <span style="font-size:0.72rem;color:var(--text-secondary);">
                        ${key.slice(0, 4).toUpperCase()} <b style="color:${scoreReady ? getScoreColor(scores[key]) : '#64748b'}">${scoreReady ? formatScore(scores[key]) : '\u2014'}</b>
                    </span>`).join('');
            }

            return `
            <div data-testid="history-session-item" onclick="viewSessionDetail('${session.detail_api_path}', '${session.module_type}')" style="padding:14px;border-radius:var(--radius-md);background:var(--bg-glass);
                border:1px solid var(--border-subtle);margin-bottom:10px;
                cursor:pointer;transition:border-color 0.2s,background 0.15s;"
                onmouseenter="this.style.borderColor='var(--border-accent)';this.style.background='rgba(255,255,255,0.06)'"
                onmouseleave="this.style.borderColor='var(--border-subtle)';this.style.background='var(--bg-glass)'">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;">
                    <div style="font-size:1.4rem;flex-shrink:0;">${icon}</div>
                    <div style="flex:1;min-width:0;">
                        <div data-testid="history-session-title" style="font-size:0.875rem;font-weight:600;color:var(--text-primary);
                            margin-bottom:4px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">
                            ${escapeText(session.title || 'Practice Session')}</div>
                        <div style="font-size:0.75rem;color:var(--text-muted);">${date}</div>
                        ${statusText ? `<div style="font-size:0.72rem;color:var(--accent-amber);margin-top:6px;">${statusText}</div>` : ''}
                        <div style="display:flex;gap:12px;margin-top:8px;flex-wrap:wrap;">
                            ${dimsHtml}
                        </div>
                    </div>
                    <div style="display:flex;align-items:center;gap:8px;flex-shrink:0;">
                        <div data-testid="history-session-score" style="font-family:var(--font-mono);font-size:1.8rem;font-weight:700;
                            color:${scoreColor};">${scoreReady ? formatScore(overall) : '\u2014'}</div>
                        <span style="color:var(--text-muted);font-size:1rem;">›</span>
                    </div>
                </div>
            </div>`;
        }).join('');
    }

    async function viewSessionDetail(apiPath, moduleType) {
        if (!apiPath) return;
        const overlay = document.getElementById('detailOverlay');
        const content = document.getElementById('detailContent');
        content.innerHTML = '<div style="text-align:center;padding:32px;"><div class="spinner"></div><p style="color:var(--text-muted);margin-top:12px;">Loading...</p></div>';
        overlay.style.display = 'block';
        document.body.style.overflow = 'hidden';

        try {
            const token = localStorage.getItem('ielts_token');
            const res = await fetch(apiPath, {
                headers: { Authorization: `Bearer ${token}` },
            });
            const result = await res.json();

            const scores = result.scores || {};
            const feedback = result.feedback || {};
            const improvements = result.key_improvements || [];
            const sample = result.sample_answer || '';
            const date = result.date ? new Date(result.date).toLocaleString('zh-CN') : '';
            const hasScoringError = result.scoring_status === 'error';
            const detailScore = (value) => hasScoringError ? '\u2014' : formatScore(value);
            const detailColor = (value) => hasScoringError ? '#64748b' : getScoreColor(value);

            let dimLabels = [];
            if (moduleType === 'writing') {
                const taskLabel = result.task_type === 'task1' ? 'Task Achievement' : 'Task Response';
                dimLabels = [
                    ['task', `📝 ${taskLabel}`],
                    ['coherence', '🔗 Coherence & Cohesion'],
                    ['lexical', '📚 Lexical Resource'],
                    ['grammar', '✍️ Grammatical Range'],
                ];
            } else {
                dimLabels = [
                    ['fluency', '🗣️ Fluency & Coherence'],
                    ['vocabulary', '📚 Vocabulary'],
                    ['grammar', '✍️ Grammar Accuracy'],
                    ['pronunciation', '🔊 Pronunciation'],
                ];
            }

            let html = `
                <h2 style="font-size:1.1rem;margin:0 0 4px;padding-right:40px;color:var(--text-primary);">${result.title || result.topic_title || 'Practice Session'}</h2>
                <p style="font-size:0.78rem;color:var(--text-muted);margin:0 0 20px;">${date}</p>
                ${hasScoringError ? `<div style="background:rgba(245,158,11,0.08);border:1px solid rgba(245,158,11,0.24);border-radius:var(--radius-md);padding:12px 14px;margin-bottom:16px;"><div style="font-size:0.82rem;color:var(--accent-amber);font-weight:600;margin-bottom:4px;">Scoring fallback used</div><div style="font-size:0.8rem;color:var(--text-secondary);">${result.scoring_error_detail || result.scoring_error || 'The model could not produce a normal score for this session.'}</div></div>` : ''}
                <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:10px;margin-bottom:20px;">
                    ${dimLabels.map(([key, label]) => `
                        <div style="background:var(--bg-glass);border-radius:var(--radius-md);padding:12px;text-align:center;">
                            <div style="font-size:0.7rem;color:var(--text-muted);margin-bottom:6px;">${label}</div>
                            <div style="font-size:1.6rem;font-weight:700;color:${detailColor(scores[key])};">${detailScore(scores[key])}</div>
                        </div>`).join('')}
                    <div style="background:var(--bg-glass);border-radius:var(--radius-md);padding:12px;text-align:center;border:1px solid var(--border-accent);">
                        <div style="font-size:0.7rem;color:var(--text-muted);margin-bottom:6px;">⭐ Overall</div>
                        <div style="font-size:1.6rem;font-weight:700;color:${detailColor(scores.overall)};">${detailScore(scores.overall)}</div>
                    </div>
                </div>`;

            if (moduleType === 'writing') {
                if (result.prompt) {
                    const promptText = typeof result.prompt === 'object' ? result.prompt.prompt_text : result.prompt;
                    html += `<div style="margin-bottom:14px;">
                        <h3 style="font-size:0.85rem;color:var(--text-secondary);margin:0 0 6px;">Prompt</h3>
                        <div style="font-size:0.875rem;color:var(--text-primary);line-height:1.6;background:var(--bg-glass);border-radius:var(--radius-sm);padding:10px;white-space:pre-wrap;">${escapeText(promptText)}</div>
                    </div>`;
                }
                if (result.essay_text) {
                    html += `<div style="margin-bottom:14px;">
                        <h3 style="font-size:0.85rem;color:var(--text-secondary);margin:0 0 6px;">Your Essay (${result.word_count || 0} words)</h3>
                        <div style="font-size:0.875rem;color:var(--text-primary);line-height:1.6;background:var(--bg-glass);border-radius:var(--radius-sm);padding:10px;white-space:pre-wrap;">${escapeText(result.essay_text)}</div>
                    </div>`;
                }

                for (const [key, label] of dimLabels) {
                    if (feedback[key]) {
                        html += `
                        <div style="margin-bottom:14px;">
                            <h3 style="font-size:0.85rem;color:var(--text-secondary);margin:0 0 6px;">${label}</h3>
                            <p style="font-size:0.875rem;color:var(--text-primary);margin:0;line-height:1.6;">${escapeText(feedback[key])}</p>
                        </div>`;
                    }
                }

                if (feedback.overall) {
                    html += `
                    <div style="margin-bottom:14px;">
                        <h3 style="font-size:0.85rem;color:var(--text-secondary);margin:0 0 6px;">📋 Overall Feedback</h3>
                        <p style="font-size:0.875rem;color:var(--text-primary);margin:0;line-height:1.6;">${escapeText(feedback.overall)}</p>
                    </div>`;
                }
            } else {
                for (const [key, label] of dimLabels) {
                    if (feedback[key]) {
                        html += `
                        <div style="margin-bottom:14px;">
                            <h3 style="font-size:0.85rem;color:var(--text-secondary);margin:0 0 6px;">${label}</h3>
                            <p style="font-size:0.875rem;color:var(--text-primary);margin:0;line-height:1.6;">${escapeText(feedback[key])}</p>
                        </div>`;
                    }
                }
                if (feedback.overall) {
                    html += `
                    <div style="margin-bottom:14px;">
                        <h3 style="font-size:0.85rem;color:var(--text-secondary);margin:0 0 6px;">📋 Overall Feedback</h3>
                        <p style="font-size:0.875rem;color:var(--text-primary);margin:0;line-height:1.6;">${escapeText(feedback.overall)}</p>
                    </div>`;
                }
            }

            if (improvements.length) {
                html += `<div style="margin-bottom:14px;">
                    <h3 style="font-size:0.85rem;color:var(--accent-amber);margin:0 0 8px;">💡 Suggestions</h3>
                    <ul style="margin:0;padding-left:20px;">
                        ${improvements.map((item) => `<li style="font-size:0.875rem;color:var(--text-primary);margin-bottom:4px;line-height:1.5;">${escapeText(item)}</li>`).join('')}
                    </ul></div>`;
            }
            if (sample) {
                html += `<div style="background:rgba(59,130,246,0.08);border:1px solid rgba(59,130,246,0.2);border-radius:var(--radius-md);padding:16px;margin-bottom:8px;">
                    <h3 style="font-size:0.85rem;color:var(--accent-blue);margin:0 0 8px;">✨ Sample Answer</h3>
                    <p style="font-size:0.875rem;color:var(--text-primary);margin:0;line-height:1.7;white-space:pre-wrap;">${escapeText(sample)}</p>
                </div>`;
            }

            if (moduleType === 'speaking') {
                const transcripts = result.transcripts || {};
                const transcriptParts = Object.entries(transcripts).filter(([, value]) => value?.trim());
                if (transcriptParts.length) {
                    html += `<div style="margin-top:16px;"><h3 style="font-size:0.85rem;color:var(--text-secondary);margin:0 0 8px;">🎙️ Your Response</h3>`;
                    for (const [part, text] of transcriptParts) {
                        html += `<div style="margin-bottom:10px;"><div style="font-size:0.72rem;color:var(--text-muted);margin-bottom:4px;">${part.toUpperCase()}</div>
                            <p style="font-size:0.825rem;color:var(--text-primary);line-height:1.6;margin:0;background:var(--bg-glass);border-radius:var(--radius-sm);padding:10px;">${escapeText(text)}</p></div>`;
                    }
                    html += '</div>';
                }
            }

            content.innerHTML = html;
        } catch (error) {
            content.innerHTML = `<p style="color:var(--accent-red);text-align:center;padding:32px;">Load failed: ${error.message}</p>`;
        }
    }

    function closeDetail() {
        document.getElementById('detailOverlay').style.display = 'none';
        document.body.style.overflow = '';
    }

    document.addEventListener('theme-changed', () => {
        applyChartThemeDefaults();
        if (cachedHistoryData.length) {
            renderHistoryData(cachedHistoryData);
        }
    });

    function initHistoryPage() {
        if (!document.getElementById('btnThemeToggle') || !document.getElementById('authModal')) {
            window.requestAnimationFrame(initHistoryPage);
            return;
        }

        initThemeMode();

        document.getElementById('detailOverlay').addEventListener('click', (event) => {
            if (event.target === document.getElementById('detailOverlay')) {
                closeDetail();
            }
        });
        document.getElementById('moduleFilter').addEventListener('change', loadHistory);
        document.getElementById('taskFilter').addEventListener('change', loadHistory);

        loadHistory();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initHistoryPage);
    } else {
        initHistoryPage();
    }

    window.loadHistory = loadHistory;
    window.viewSessionDetail = viewSessionDetail;
    window.closeDetail = closeDetail;
})();
