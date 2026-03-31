(function () {
    'use strict';

    const state = window.state;
    const api = window.api;
    let currentChartInstances = [];

    function destroyWritingCharts() {
        for (const chart of currentChartInstances) {
            chart.destroy();
        }
        currentChartInstances = [];
        const container = document.getElementById('writingChartContainer');
        if (container) container.classList.add('hidden');
        const tableEl = document.getElementById('writingTableContainer');
        if (tableEl) tableEl.innerHTML = '';
        const multiEl = document.getElementById('writingMultiPieContainer');
        if (multiEl) multiEl.innerHTML = '';
    }

    function renderWritingChart(chartData) {
        destroyWritingCharts();
        if (!chartData?.type) return;

        const container = document.getElementById('writingChartContainer');
        if (!container) return;
        container.classList.remove('hidden');

        const chartType = chartData.type;

        if (chartType === 'table') {
            const tableEl = document.getElementById('writingTableContainer');
            if (!tableEl) return;
            let html = '';
            if (chartData.title) html += `<h4 style="text-align:center; margin-bottom:12px; color:var(--text-primary); font-size:0.95rem;">${window.escapeHtml(chartData.title)}</h4>`;
            html += '<table style="width:100%; border-collapse:collapse; font-size:0.9rem;">';
            if (chartData.headers) {
                html += '<thead><tr>';
        for (const h of chartData.headers) html += `<th style="padding:8px 12px; border:1px solid var(--border-subtle); background:var(--bg-card); font-weight:600; text-align:left;">${window.escapeHtml(h)}</th>`;
                html += '</tr></thead>';
            }
            if (chartData.rows) {
                html += '<tbody>';
                for (const row of chartData.rows) {
                    html += '<tr>';
        for (const cell of row) html += `<td style="padding:8px 12px; border:1px solid var(--border-subtle);">${window.escapeHtml(String(cell))}</td>`;
                    html += '</tr>';
                }
                html += '</tbody>';
            }
            html += '</table>';
            tableEl.innerHTML = html;
            return;
        }

        if (chartType === 'pie' && chartData.multi && chartData.charts) {
            const multiEl = document.getElementById('writingMultiPieContainer');
            if (!multiEl) return;
            multiEl.innerHTML = '';
            for (const sub of chartData.charts) {
                const wrapper = document.createElement('div');
                wrapper.style.cssText = 'flex:1; min-width:250px; max-width:350px;';
                const subTitle = document.createElement('h4');
                subTitle.textContent = sub.title || '';
                subTitle.style.cssText = 'text-align:center; margin-bottom:8px; color:var(--text-primary); font-size:0.95rem;';
                wrapper.appendChild(subTitle);
                const canvas = document.createElement('canvas');
                wrapper.appendChild(canvas);
                multiEl.appendChild(wrapper);
                const chart = new Chart(canvas, {
                    type: 'pie',
                    data: sub.data,
                    options: { responsive: true, plugins: { legend: { position: 'bottom' } } }
                });
                currentChartInstances.push(chart);
            }
            return;
        }

        const canvas = document.getElementById('writingChartCanvas');
        if (!canvas) return;
        const chart = new Chart(canvas, {
            type: chartType,
            data: chartData.data,
            options: chartData.options || { responsive: true }
        });
        currentChartInstances.push(chart);
    }

    function renderWritingImage(imageMeta) {
        destroyWritingCharts();
        if (!imageMeta?.url) return;

        const container = document.getElementById('writingChartContainer');
        const tableEl = document.getElementById('writingTableContainer');
        if (!container || !tableEl) return;

        container.classList.remove('hidden');
        tableEl.innerHTML = `
            <img
                src="${window.escapeHtml(imageMeta.url)}"
                alt="${window.escapeHtml(imageMeta.alt || 'Writing task visual')}"
                loading="lazy"
                referrerpolicy="no-referrer"
                style="display:block; max-width:100%; height:auto; margin:0 auto; border:1px solid var(--border-subtle); border-radius:12px; background:var(--bg-card);"
            >
        `;
    }

    function renderWritingVisual(promptDetails) {
        const chartData = promptDetails?.chart_data;
        if (chartData) {
            renderWritingChart(chartData);
            return;
        }

        const chartImage = promptDetails?.chart_image;
        if (chartImage) {
            renderWritingImage(chartImage);
            return;
        }

        destroyWritingCharts();
    }

    async function startWritingMode(taskType) {
        if (typeof window.resetFreePracticeSetup === 'function') {
            window.resetFreePracticeSetup();
        }
        state.mode = 'writing';
        state.writingTaskType = taskType;
        state.writingPromptId = null;
        state.writingFpCustomPrompt = null;

        document.getElementById('modeSelector').classList.add('hidden');
        document.getElementById('examFlow')?.classList.add('hidden');
        document.getElementById('writingFlow').classList.remove('hidden');

        document.getElementById('writingPromptSection').classList.remove('hidden');
        document.getElementById('writingScoreSection').classList.add('hidden');
        document.getElementById('writingEssayInput').value = '';
        document.getElementById('writingWordCount').textContent = '0';
        destroyWritingCharts();

        document.getElementById('writingTaskTitle').innerText = taskType === 'task1' ? 'Writing Task 1' : 'Writing Task 2';
        document.getElementById('writingTaskIcon').innerText = taskType === 'task1' ? '📊' : '✍️';
        document.getElementById('writingPromptText').innerHTML = '<span class="spinner" style="display:inline-block;width:16px;height:16px;border-width:2px;margin-right:8px;"></span>Loading prompt...';

        const btn = document.getElementById('btnSubmitWriting');
        btn.disabled = true;

        try {
            const prompt = await api(`/api/writing/prompts/random?task_type=${taskType}`);
            state.writingPromptId = prompt.id;
            document.getElementById('writingPromptText').textContent = prompt.prompt_text;
            renderWritingVisual(prompt.prompt_details);
            btn.disabled = false;

            document.getElementById('writingEssayInput').addEventListener('input', updateWritingWordCount);
        } catch (e) {
            document.getElementById('writingPromptText').textContent = 'Failed to load prompt: ' + e.message;
        }
    }

    function updateWritingWordCount() {
        const text = document.getElementById('writingEssayInput').value.trim();
        const count = text ? text.split(/\s+/).length : 0;
        document.getElementById('writingWordCount').textContent = count;
    }

    async function submitWriting() {
        const essayText = document.getElementById('writingEssayInput').value.trim();
        if (!essayText) {
            alert('Please write an essay before submitting.');
            return;
        }

        const btn = document.getElementById('btnSubmitWriting');
        btn.disabled = true;
        stopWritingTimer();

        document.getElementById('writingPromptSection').classList.add('hidden');
        document.getElementById('writingScoreSection').classList.remove('hidden');
        document.getElementById('writingScoringLoader').classList.remove('hidden');
        document.getElementById('writingScoreResults').classList.add('hidden');

        try {
            const payload = { essay_text: essayText };
            if (state.writingPromptId) {
                payload.prompt_id = state.writingPromptId;
            } else if (state.writingFpCustomPrompt) {
                payload.custom_prompt = state.writingFpCustomPrompt;
                payload.custom_task_type = state.writingFpCustomTaskType;
            } else if (state.writingPromptId === null && !state.writingFpCustomPrompt) {
                payload.prompt_id = state.writingPromptId;
            }

            const attempt = await api('/api/writing/attempts', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            renderWritingResult(attempt);
        } catch (e) {
            document.getElementById('writingScoringLoader').innerHTML = `
            <div style="text-align:center; color:var(--accent-red);">
                <p style="font-size:1.5rem; margin-bottom:12px;">X</p>
                <p style="font-weight:600;">Submission Failed</p>
                <p style="font-size:0.85rem; color:var(--text-muted); margin-top:8px;">${e.message}</p>
                <button class="btn btn-ghost" style="margin-top:16px;" onclick="backToHome()">Try Again</button>
            </div>`;
        }
    }

    function renderWritingResult(result) {
        document.getElementById('writingScoringLoader').classList.add('hidden');
        document.getElementById('writingScoreResults').classList.remove('hidden');
        document.getElementById('writingScoreResults').classList.add('fade-in');

        const scores = result.scores || {};
        const feedback = result.feedback || {};
        const improvements = result.key_improvements || [];
        const sample = result.sample_answer || '';

        const isTask1 = result.task_type === 'task1';
        const taLabel = isTask1 ? 'Task Achievement' : 'Task Response';

        const items = [
            { label: taLabel, key: 'task', icon: '📝' },
            { label: 'Coherence & Cohesion', key: 'coherence', icon: '🔗' },
            { label: 'Lexical Resource', key: 'lexical', icon: '📚' },
            { label: 'Grammar', key: 'grammar', icon: '✍️' },
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
        <div class="score-value ${overall >= 7 ? 'high' : overall >= 5.5 ? 'mid' : 'low'}">${overall.toFixed(1)}</div>
    </div>`;

        document.getElementById('writingScoresGrid').innerHTML = grid;

        document.getElementById('writingEssayDisplay').textContent = result.essay_text || '';

        let fbHtml = '';

        if (result.prompt) {
            const promptText = typeof result.prompt === 'object' ? result.prompt.prompt_text : result.prompt;
            fbHtml += `
            <div class="feedback-item">
                <h3>Prompt</h3>
                <p style="white-space: pre-wrap;">${window.escapeHtml(promptText)}</p>
            </div>`;
        }

        const FEEDBACK_LABELS = [
            ['task', taLabel],
            ['coherence', 'Coherence & Cohesion'],
            ['lexical', 'Lexical Resource'],
            ['grammar', 'Grammatical Range & Accuracy'],
            ['overall', 'Overall Feedback'],
        ];

        for (const [key, label] of FEEDBACK_LABELS) {
            if (feedback[key]) fbHtml += `
            <div class="feedback-item">
                <h3>${label}</h3>
                <p>${window.escapeHtml(feedback[key])}</p>
            </div>`;
        }

        if (improvements.length > 0) fbHtml += `
        <div class="feedback-item">
            <h3>Key Improvements</h3>
            <ul class="improvements-list">
                ${improvements.map(i => `<li>${window.escapeHtml(i)}</li>`).join('')}
            </ul>
        </div>`;

        if (sample) fbHtml += `
        <div class="sample-answer">
            <h3>Band 7+ Sample Answer</h3>
            <p style="white-space: pre-wrap;">${window.escapeHtml(sample)}</p>
        </div>`;

        document.getElementById('writingFeedbackSection').innerHTML = fbHtml;
    }

    function showWritingFreePracticeSetup() {
        const panel = document.getElementById('writingFreePracticePanel');
        if (!panel) return;
        panel.classList.remove('hidden');
        clearWritingFpError();
        loadWritingFpTopics();
        setWfpType('library');
    }

    function hideWritingFreePracticeSetup() {
        const panel = document.getElementById('writingFreePracticePanel');
        if (panel) panel.classList.add('hidden');
        clearWritingFpError();
    }

    function clearWritingFpError() {
        const el = document.getElementById('writingFpError');
        if (el) {
            el.textContent = '';
            el.classList.add('hidden');
        }
    }

    function showWritingFpError(msg) {
        const el = document.getElementById('writingFpError');
        if (el) {
            el.textContent = msg;
            el.classList.remove('hidden');
        }
    }

    function setWfpType(type) {
        state.writingFpMode = type;
        document.querySelectorAll('#wfpTypeToggle .btn').forEach((b) => { b.classList.remove('active'); });
        const active = document.querySelector(`#wfpTypeToggle .btn[data-target="${type}"]`);
        if (active) active.classList.add('active');

        const libView = document.getElementById('wfp-library-view');
        const customView = document.getElementById('wfp-custom-view');
        if (libView) {
            libView.classList.toggle('hidden', type !== 'library');
            libView.classList.toggle('active', type === 'library');
        }
        if (customView) {
            customView.classList.toggle('hidden', type !== 'custom');
            customView.classList.toggle('active', type === 'custom');
        }
    }

    function setWfpCustomTaskType(taskType) {
        state.writingFpCustomTaskType = taskType;
        const btn1 = document.getElementById('wfpCustomTask1Btn');
        const btn2 = document.getElementById('wfpCustomTask2Btn');
        if (btn1) btn1.classList.toggle('is-selected', taskType === 'task1');
        if (btn2) btn2.classList.toggle('is-selected', taskType === 'task2');
    }

    function setWfpTimer(minutes) {
        state.writingFpTimerMinutes = minutes;
        document.querySelectorAll('[data-wfp-timer]').forEach((btn) => {
            btn.classList.toggle('is-selected', Number(btn.dataset.minutes) === minutes);
        });
    }

    async function loadWritingFpTopics() {
        const lib = state.writingFpTopicLibrary;
        if (lib.loaded || lib.loading) return;
        lib.loading = true;

        const select = document.getElementById('writingFpTopicSelect');
        if (select) select.innerHTML = '<option value="">Loading prompts...</option>';

        try {
            const prompts = await api('/api/writing/prompts');
            lib.prompts = prompts || [];
            lib.loaded = true;
            renderWritingFpTopicOptions();
        } catch (err) {
            console.error('Failed to load writing prompts', err);
            if (select) select.innerHTML = '<option value="">Failed to load prompts</option>';
        } finally {
            lib.loading = false;
        }
    }

    function renderWritingFpTopicOptions() {
        const select = document.getElementById('writingFpTopicSelect');
        if (!select) return;
        const prompts = state.writingFpTopicLibrary.prompts;
        if (prompts.length === 0) {
            select.innerHTML = '<option value="">No prompts available</option>';
            return;
        }
        let html = '<option value="">Select a prompt...</option>';
        const task1 = prompts.filter((p) => p.task_type === 'task1');
        const task2 = prompts.filter((p) => p.task_type === 'task2');
        if (task1.length) {
            html += '<optgroup label="Task 1">';
            for (const p of task1) html += `<option value="${p.id}">${window.escapeHtml(p.title || p.prompt_text)}</option>`;
            html += '</optgroup>';
        }
        if (task2.length) {
            html += '<optgroup label="Task 2">';
            for (const p of task2) html += `<option value="${p.id}">${window.escapeHtml(p.title || p.prompt_text)}</option>`;
            html += '</optgroup>';
        }
        select.innerHTML = html;
    }

    async function startWritingFreePractice() {
        clearWritingFpError();

        let promptText = '';
        let promptId = null;
        let customPrompt = null;
        let customTaskType = null;
        let taskType = null;

        if (state.writingFpMode === 'library') {
            const select = document.getElementById('writingFpTopicSelect');
            const selectedId = select ? Number(select.value) : null;
            if (!selectedId) {
                showWritingFpError('Please select a prompt from the library, or switch to "Write My Own".');
                return;
            }
            promptId = selectedId;
            const prompt = state.writingFpTopicLibrary.prompts.find((p) => p.id === selectedId);
            promptText = prompt ? prompt.prompt_text : '';
            taskType = prompt ? prompt.task_type : 'task2';
        } else {
            const textarea = document.getElementById('writingFpCustomPrompt');
            const text = textarea ? textarea.value.trim() : '';
            if (!text) {
                showWritingFpError('Enter a custom prompt to start free practice.');
                return;
            }
            customPrompt = text;
            customTaskType = state.writingFpCustomTaskType;
            taskType = customTaskType;
            promptText = text;
        }

        state.mode = 'writing';
        state.writingTaskType = taskType;
        state.writingPromptId = promptId;

        document.getElementById('modeSelector').classList.add('hidden');
        document.getElementById('writingFlow').classList.remove('hidden');
        document.getElementById('writingPromptSection').classList.remove('hidden');
        document.getElementById('writingScoreSection').classList.add('hidden');
        document.getElementById('writingEssayInput').value = '';
        document.getElementById('writingWordCount').textContent = '0';
        destroyWritingCharts();

        const isTask1 = taskType === 'task1';
        document.getElementById('writingTaskTitle').innerText = isTask1 ? 'Writing Task 1' : 'Writing Task 2';
        document.getElementById('writingTaskIcon').innerText = isTask1 ? '📊' : '✍️';
        document.getElementById('writingPromptText').textContent = promptText;

        if (promptId) {
            const prompt = state.writingFpTopicLibrary.prompts.find((p) => p.id === promptId);
            renderWritingVisual(prompt?.prompt_details);
        }

        if (customPrompt && taskType === 'task1') {
            try {
                const result = await api('/api/writing/generate-chart', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ prompt_text: customPrompt }),
                });
                if (result?.chart_data) {
                    renderWritingChart(result.chart_data);
                }
            } catch (e) {
                console.warn('Chart generation failed, continuing without chart:', e.message);
            }
        }

        state.writingFpCustomPrompt = customPrompt;
        state.writingFpCustomTaskType = customTaskType || taskType;

        document.getElementById('btnSubmitWriting').disabled = false;
        document.getElementById('writingEssayInput').addEventListener('input', updateWritingWordCount);

        if (state.writingFpTimerMinutes > 0) {
            startWritingTimer(state.writingFpTimerMinutes * 60);
        }
    }

    function startWritingTimer(totalSeconds) {
        const existing = document.getElementById('writingTimerDisplay');
        if (existing) existing.remove();

        const timerDiv = document.createElement('div');
        timerDiv.id = 'writingTimerDisplay';
        timerDiv.style.cssText = 'text-align:center; font-size:1.5rem; font-weight:700; color:var(--accent-blue); margin-bottom:16px; font-variant-numeric:tabular-nums;';

        const promptSection = document.getElementById('writingPromptSection');
        if (promptSection) promptSection.parentNode.insertBefore(timerDiv, promptSection);

        let remaining = totalSeconds;
        function tick() {
            const m = Math.floor(remaining / 60);
            const s = remaining % 60;
            timerDiv.textContent = `⏱ ${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
            if (remaining <= 0) {
                timerDiv.textContent = '⏱ Time is up!';
                timerDiv.style.color = 'var(--accent-red)';
                clearInterval(state.writingTimerInterval);
                return;
            }
            remaining--;
        }
        tick();
        state.writingTimerInterval = setInterval(tick, 1000);
    }

    function stopWritingTimer() {
        if (state.writingTimerInterval) {
            clearInterval(state.writingTimerInterval);
            state.writingTimerInterval = null;
        }
        const el = document.getElementById('writingTimerDisplay');
        if (el) el.remove();
    }

    window.startWritingMode = startWritingMode;
    window.updateWritingWordCount = updateWritingWordCount;
    window.submitWriting = submitWriting;
    window.renderWritingResult = renderWritingResult;
    window.showWritingFreePracticeSetup = showWritingFreePracticeSetup;
    window.hideWritingFreePracticeSetup = hideWritingFreePracticeSetup;
    window.clearWritingFpError = clearWritingFpError;
    window.showWritingFpError = showWritingFpError;
    window.setWfpType = setWfpType;
    window.setWfpCustomTaskType = setWfpCustomTaskType;
    window.setWfpTimer = setWfpTimer;
    window.loadWritingFpTopics = loadWritingFpTopics;
    window.renderWritingFpTopicOptions = renderWritingFpTopicOptions;
    window.renderWritingChart = renderWritingChart;
    window.renderWritingImage = renderWritingImage;
    window.renderWritingVisual = renderWritingVisual;
    window.destroyWritingCharts = destroyWritingCharts;
    window.startWritingFreePractice = startWritingFreePractice;
    window.startWritingTimer = startWritingTimer;
    window.stopWritingTimer = stopWritingTimer;
})();
