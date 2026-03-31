(function () {
    'use strict';

    const state = window.state;
    const api = window.api;

    function buildFreePracticeTopic(prompt, speakingSeconds) {
        return {
            title: prompt,
            categoryLabel: 'Free Practice',
            introLabel: 'Use this prompt',
            points: [
                `Speak for ${window.formatSpeakingDuration(speakingSeconds)}.`,
                'Give reasons, examples, and a clear structure in your answer.',
            ],
        };
    }

    function clearFreePracticeError() {
        const errorEl = document.getElementById('freePracticeError');
        if (!errorEl) return;
        errorEl.textContent = '';
        errorEl.classList.add('hidden');
    }

    function showFreePracticeError(message) {
        const errorEl = document.getElementById('freePracticeError');
        if (!errorEl) return;
        errorEl.textContent = message;
        errorEl.classList.remove('hidden');
    }

    function setFreePracticePreset(seconds) {
        const panel = document.getElementById('freePracticePanel');
        const customInput = document.getElementById('freePracticeCustomSeconds');

        document.querySelectorAll('[data-free-practice-preset]').forEach((btn) => {
            btn.classList.toggle('is-selected', Number(btn.dataset.seconds) === seconds);
        });

        if (panel) {
            panel.dataset.durationSource = 'preset';
            panel.dataset.durationSeconds = String(seconds);
        }

        if (customInput) customInput.value = '';
        clearFreePracticeError();
    }

    function resetFreePracticeSetup() {
        const panel = document.getElementById('freePracticePanel');
        const promptInput = document.getElementById('freePracticePrompt');
        const startButton = document.getElementById('btnStartFreePractice');

        if (panel) {
            panel.classList.add('hidden');
            panel.dataset.durationSource = 'preset';
            panel.dataset.durationSeconds = String(window.DEFAULT_PART2_SPEAKING_SECONDS);
        }

        if (promptInput) promptInput.value = '';
        if (startButton) {
            startButton.disabled = false;
            startButton.innerHTML = window.UI_TEXT.startFreePractice;
        }

        setFreePracticePreset(window.DEFAULT_PART2_SPEAKING_SECONDS);
    }

    function showFreePracticeSetup() {
        const panel = document.getElementById('freePracticePanel');
        if (!panel) return;

        panel.classList.remove('hidden');
        if (!panel.dataset.durationSeconds) {
            setFreePracticePreset(window.DEFAULT_PART2_SPEAKING_SECONDS);
        }
        clearFreePracticeError();
        document.getElementById('freePracticePrompt')?.focus();
        loadFpTopics();
        setFpType('library');
    }

    function hideFreePracticeSetup() {
        resetFreePracticeSetup();
    }

    function handleFreePracticeCustomDurationInput() {
        const panel = document.getElementById('freePracticePanel');
        const customInput = document.getElementById('freePracticeCustomSeconds');
        if (!panel || !customInput) return;

        if (customInput.value.trim()) {
            panel.dataset.durationSource = 'custom';
            panel.dataset.durationSeconds = '';
            document.querySelectorAll('[data-free-practice-preset]').forEach((btn) => {
                btn.classList.remove('is-selected');
            });
        } else {
            setFreePracticePreset(window.DEFAULT_PART2_SPEAKING_SECONDS);
        }

        clearFreePracticeError();
    }

    async function startFreePractice() {
        const promptInput = document.getElementById('freePracticePrompt');
        const customInput = document.getElementById('freePracticeCustomSeconds');
        const startButton = document.getElementById('btnStartFreePractice');
        const panel = document.getElementById('freePracticePanel');

        let payload = {};
        let promptText = '';

        if (state.freePracticeMode === 'library') {
            if (!state.freePracticeSelectedSource || !state.freePracticeSelectedId) {
                showFreePracticeError('Please select a topic from the library, or switch to "Write my own".');
                return;
            }
            if (state.freePracticeSelectedSource === 'official') {
                payload = { topic_id: state.freePracticeSelectedId };
                const topic = state.freePracticeTopicLibrary.officialTopics.find((t) => t.id === state.freePracticeSelectedId);
                promptText = topic ? topic.title : 'Official Topic';
            } else {
                payload = { saved_topic_id: state.freePracticeSelectedId };
                const topic = state.freePracticeTopicLibrary.savedTopics.find((t) => t.id === state.freePracticeSelectedId);
                promptText = topic ? (topic.prompt_text || topic.title) : 'Saved Topic';
            }
        } else {
            const prompt = promptInput?.value.trim() || '';
            if (!prompt) {
                showFreePracticeError('Enter a custom prompt to start free practice.');
                return;
            }
            payload = { custom_topic: prompt };
            promptText = prompt;
        }

        let speakingSeconds = Number(panel?.dataset.durationSeconds || window.DEFAULT_PART2_SPEAKING_SECONDS);
        if (customInput?.value.trim()) {
            speakingSeconds = Number(customInput.value.trim());
            if (!Number.isFinite(speakingSeconds) || speakingSeconds <= 0) {
                showFreePracticeError('Enter a positive speaking duration in seconds.');
                return;
            }
            speakingSeconds = Math.round(speakingSeconds);
        }

        if (startButton) {
            startButton.disabled = true;
            startButton.innerHTML = window.UI_TEXT.loading;
        }

        try {
            const session = await api('/api/part2/sessions', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            state.mode = 'free_practice';
            state.sessionId = session.session_id;
            state.topic = buildFreePracticeTopic(promptText, speakingSeconds);
            state.part2QuestionText = promptText;
            state.part2SpeakingSeconds = speakingSeconds;
            state.practiceSource = state.freePracticeMode === 'library' ? state.freePracticeSelectedSource : 'custom';
            state.transcripts.part2 = '';
            state.clientTranscripts.part2 = '';
            document.getElementById('notesInput').value = '';

            document.getElementById('modeSelector').classList.add('hidden');
            document.getElementById('examFlow').classList.remove('hidden');
            window.setPhase('part2speak');
        } catch (e) {
            showFreePracticeError('Failed to start free practice: ' + e.message);
            if (startButton) {
                startButton.disabled = false;
                startButton.innerHTML = window.UI_TEXT.startFreePractice;
            }
        }
    }

    async function loadFpTopics() {
        const token = localStorage.getItem('ielts_token');
        if (!token) return;
        if (state.freePracticeTopicLibrary.loaded || state.freePracticeTopicLibrary.loading) return;

        state.freePracticeTopicLibrary.loading = true;
        renderFpTopicOptions();

        try {
            const res = await fetch('/api/part2/free-practice-topics', {
                headers: { 'Authorization': `Bearer ${token}` },
            });
            if (res.ok) {
                const data = await res.json();
                state.freePracticeTopicLibrary.officialTopics = data.official_topics || [];
                state.freePracticeTopicLibrary.savedTopics = data.saved_topics || [];
                state.freePracticeTopicLibrary.loaded = true;
            }
        } catch (err) {
            console.error('Failed to load topics', err);
        } finally {
            state.freePracticeTopicLibrary.loading = false;
            renderFpTopicOptions();
        }
    }

    function setFpType(type) {
        state.freePracticeMode = type;
        document.querySelectorAll('.fp-type-toggle .btn').forEach((button) => {
            button.classList.remove('active');
        });

        const activeButton = document.querySelector(`.fp-type-toggle .btn[data-target="${type}"]`);
        if (activeButton) activeButton.classList.add('active');

        document.getElementById('library-view').classList.toggle('hidden', type !== 'library');
        document.getElementById('library-view').classList.toggle('active', type === 'library');
        document.getElementById('custom-view').classList.toggle('hidden', type !== 'custom');
        document.getElementById('custom-view').classList.toggle('active', type === 'custom');
    }

    function toggleFpTopicDropdown(e) {
        if (e) e.stopPropagation();
        const container = document.getElementById('fpTopicSelectContainer');
        const dropdown = document.getElementById('fpTopicDropdown');
        const btn = document.getElementById('fpTopicSelectBtn');

        if (!container || !dropdown || !btn) return;

        const isOpen = !dropdown.classList.contains('hidden');

        if (isOpen) {
            dropdown.classList.add('hidden');
            container.classList.remove('open');
            btn.setAttribute('aria-expanded', 'false');
        } else {
            renderFpTopicOptions(document.getElementById('fpTopicSearchInput')?.value || '');
            dropdown.classList.remove('hidden');
            container.classList.add('open');
            btn.setAttribute('aria-expanded', 'true');
            document.getElementById('fpTopicSearchInput')?.focus();
        }
    }

    function selectFpTopic(source, id, title) {
        state.freePracticeSelectedSource = source;
        state.freePracticeSelectedId = id;

        document.getElementById('fpTopicSelectText').textContent = title;
        document.getElementById('freePracticeTopicSelect').value = `${source}:${id}`;

        const dropdown = document.getElementById('fpTopicDropdown');
        const container = document.getElementById('fpTopicSelectContainer');
        const btn = document.getElementById('fpTopicSelectBtn');

        dropdown.classList.add('hidden');
        container.classList.remove('open');
        if (btn) {
            btn.setAttribute('aria-expanded', 'false');
            btn.focus();
        }
        clearFreePracticeError();
    }

    function renderFpTopicOptions(searchTerm = '') {
        const list = document.getElementById('fpTopicOptions');
        if (!list) return;

        const { loading, officialTopics, savedTopics } = state.freePracticeTopicLibrary;

        if (loading) {
            list.innerHTML = `
            <div class="custom-select-loading">
                <div style="width:100%">
                    <div class="shimmer-line"></div>
                    <div class="shimmer-line medium"></div>
                    <div class="shimmer-line short"></div>
                </div>
            </div>
        `;
            return;
        }

        const lowerSearch = searchTerm.toLowerCase();
        const filterFn = (t) => t.title?.toLowerCase().includes(lowerSearch) || t.prompt_text?.toLowerCase().includes(lowerSearch);

        const filteredOfficial = officialTopics.filter(filterFn);
        const filteredSaved = savedTopics.filter(filterFn);

        let html = '';

        if (filteredOfficial.length > 0) {
            const officialCountLabel = `${filteredOfficial.length} ${filteredOfficial.length === 1 ? 'item' : 'items'}`;
            html += `
            <div class="custom-select-optgroup" id="fpTopicGroupOfficialLabel">
                Official Topics
            </div>
            <span class="sr-only" id="fpTopicGroupOfficialCount">${officialCountLabel}</span>
            <div class="custom-select-optgroup-wrap" role="group" aria-labelledby="fpTopicGroupOfficialLabel fpTopicGroupOfficialCount">
        `;
            filteredOfficial.forEach((t) => {
                const isSelected = state.freePracticeSelectedSource === 'official' && state.freePracticeSelectedId === t.id;
                const optionTitle = t.title || '';
                html += `
                <div class="custom-select-option ${isSelected ? 'selected' : ''}"
                     role="option"
                     tabindex="-1"
                     aria-selected="${isSelected ? 'true' : 'false'}"
                     data-source="official"
                     data-id="${t.id}"
                     data-title="${window.escapeHtml(optionTitle)}">
                    ${window.escapeHtml(optionTitle)}
                </div>
            `;
            });
            html += '</div>';
        }

        if (filteredSaved.length > 0) {
            const savedCountLabel = `${filteredSaved.length} ${filteredSaved.length === 1 ? 'item' : 'items'}`;
            html += `
            <div class="custom-select-optgroup" id="fpTopicGroupSavedLabel">
                Your Saved Topics
            </div>
            <span class="sr-only" id="fpTopicGroupSavedCount">${savedCountLabel}</span>
            <div class="custom-select-optgroup-wrap" role="group" aria-labelledby="fpTopicGroupSavedLabel fpTopicGroupSavedCount">
        `;
            filteredSaved.forEach((t) => {
                const isSelected = state.freePracticeSelectedSource === 'saved' && state.freePracticeSelectedId === t.id;
                const optionTitle = t.title || t.prompt_text || '';
                html += `
                <div class="custom-select-option ${isSelected ? 'selected' : ''}"
                     role="option"
                     tabindex="-1"
                     aria-selected="${isSelected ? 'true' : 'false'}"
                     data-source="saved"
                     data-id="${t.id}"
                     data-title="${window.escapeHtml(optionTitle)}">
                    ${window.escapeHtml(optionTitle)}
                </div>
            `;
            });
            html += '</div>';
        }

        if (!filteredOfficial.length && !filteredSaved.length) {
            html = '<div class="custom-select-empty">No topics found</div>';
        }

        list.innerHTML = html;
    }

    function filterFpTopics(e) {
        renderFpTopicOptions(e.target.value);
    }

    function closeFpTopicDropdown({ focusTrigger = false } = {}) {
        const dropdown = document.getElementById('fpTopicDropdown');
        const container = document.getElementById('fpTopicSelectContainer');
        const btn = document.getElementById('fpTopicSelectBtn');
        if (!dropdown || !container) return;

        dropdown.classList.add('hidden');
        container.classList.remove('open');
        if (btn) {
            btn.setAttribute('aria-expanded', 'false');
            if (focusTrigger) btn.focus();
        }
    }

    document.addEventListener('click', (e) => {
        const dropdown = document.getElementById('fpTopicDropdown');
        const container = document.getElementById('fpTopicSelectContainer');
        const btn = document.getElementById('fpTopicSelectBtn');
        if (container && !container.contains(e.target) && dropdown && !dropdown.classList.contains('hidden')) {
            dropdown.classList.add('hidden');
            container.classList.remove('open');
            if (btn) btn.setAttribute('aria-expanded', 'false');
        }

        const themeSwitcher = document.getElementById('themeSwitcher');
        if (themeSwitcher && !themeSwitcher.contains(e.target)) {
            window.closeThemeMenu();
        }
    });

    document.addEventListener('DOMContentLoaded', () => {
        const container = document.getElementById('fpTopicSelectContainer');
        const optionsList = document.getElementById('fpTopicOptions');
        if (!container) return;

        if (optionsList) {
            optionsList.addEventListener('click', (e) => {
                const option = e.target.closest('.custom-select-option');
                if (!option) return;

                selectFpTopic(
                    option.dataset.source || '',
                    Number(option.dataset.id),
                    option.dataset.title || '',
                );
            });
        }

        container.addEventListener('keydown', (e) => {
            const dropdown = document.getElementById('fpTopicDropdown');
            const searchInput = document.getElementById('fpTopicSearchInput');
            const isOpen = !dropdown.classList.contains('hidden');

            if (e.key === 'Escape') {
                if (isOpen) {
                    closeFpTopicDropdown({ focusTrigger: true });
                    e.preventDefault();
                    e.stopPropagation();
                }
                return;
            }

            if (e.key === 'Tab' && isOpen) {
                closeFpTopicDropdown();
                return;
            }

            if (e.key === 'ArrowDown' && !isOpen) {
                if (document.activeElement === document.getElementById('fpTopicSelectBtn')) {
                    toggleFpTopicDropdown();
                    e.preventDefault();
                }
                return;
            }

            if (isOpen && (e.key === 'ArrowDown' || e.key === 'ArrowUp')) {
                const options = Array.from(document.querySelectorAll('#fpTopicOptions .custom-select-option'));
                if (options.length === 0) return;

                e.preventDefault();

                const currentFocus = document.activeElement;
                const currentIndex = options.indexOf(currentFocus);

                if (e.key === 'ArrowDown') {
                    if (currentFocus === searchInput || currentIndex === -1) {
                        options[0].focus();
                    } else if (currentIndex >= 0 && currentIndex < options.length - 1) {
                        options[currentIndex + 1].focus();
                    }
                } else if (e.key === 'ArrowUp') {
                    if (currentFocus === searchInput || currentIndex === -1) {
                        options[options.length - 1].focus();
                    } else if (currentIndex === 0) {
                        searchInput.focus();
                    } else if (currentIndex > 0) {
                        options[currentIndex - 1].focus();
                    }
                }
            }

            if (isOpen && (e.key === 'Enter' || e.key === ' ')) {
                if (document.activeElement.classList.contains('custom-select-option')) {
                    e.preventDefault();
                    document.activeElement.click();
                }
            }
        });
    });

    window.buildFreePracticeTopic = buildFreePracticeTopic;
    window.clearFreePracticeError = clearFreePracticeError;
    window.showFreePracticeError = showFreePracticeError;
    window.setFreePracticePreset = setFreePracticePreset;
    window.resetFreePracticeSetup = resetFreePracticeSetup;
    window.showFreePracticeSetup = showFreePracticeSetup;
    window.hideFreePracticeSetup = hideFreePracticeSetup;
    window.handleFreePracticeCustomDurationInput = handleFreePracticeCustomDurationInput;
    window.startFreePractice = startFreePractice;
    window.loadFpTopics = loadFpTopics;
    window.setFpType = setFpType;
    window.toggleFpTopicDropdown = toggleFpTopicDropdown;
    window.selectFpTopic = selectFpTopic;
    window.renderFpTopicOptions = renderFpTopicOptions;
    window.filterFpTopics = filterFpTopics;
    window.closeFpTopicDropdown = closeFpTopicDropdown;
})();
