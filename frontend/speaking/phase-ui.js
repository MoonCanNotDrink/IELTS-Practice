(function () {
    'use strict';

    const app = window.IELTSApp;
    const speaking = app.speaking;
    const refs = app.sharedRefs;
    const state = refs.state;
    const UI_TEXT = refs.UI_TEXT;

    function setPhase(phase) {
        state.phase = phase;
        const all = ['topic', 'part1', 'part2', 'part3', 'score'];
        const phaseToStep = {
            topic: 'topic',
            part1: 'part1',
            part2prep: 'part2',
            part2speak: 'part2',
            part3: 'part3',
            scoring: 'score'
        };
        const curStep = phaseToStep[phase] || phase;
        const curIdx = all.indexOf(curStep);

        all.forEach((s, i) => {
            const el = document.getElementById(`step-${s}`);
            if (!el) return;
            el.classList.remove('active', 'completed');
            if (i < curIdx) el.classList.add('completed');
            if (i === curIdx) el.classList.add('active');
        });

        show('topicCard', phase === 'topic');
        show('part2CueCard', ['part2prep', 'part2speak', 'part1', 'topic'].includes(phase) === false
            ? false
            : ['part2prep', 'part2speak'].includes(phase));
        show('part1Section', phase === 'part1');
        show('part2Section', phase === 'part2prep' || phase === 'part2speak');
        show('part3Section', phase === 'part3');
        show('scoreSection', phase === 'scoring');
        show('sessionActions', phase !== 'home' && phase !== 'scoring');

        if (phase === 'part2prep') {
            document.getElementById('part2CueTitle').textContent = 'Part 2 - Cue Card';
            document.getElementById('part2TopicDisplay').innerHTML = speaking.renderTopicCard(state.topic);
            show('part2CueCard', true);
            const notesEl = document.getElementById('notesInput');
            notesEl.classList.remove('hidden');
            notesEl.readOnly = false;
            notesEl.style.opacity = '';
            notesEl.style.cursor = '';
            document.getElementById('part2PhaseTitle').textContent = 'Preparation Phase';
            document.getElementById('part2Badge').textContent = '1 Min';
            document.getElementById('part2Badge').className = 'status-badge prep';
            document.getElementById('part2TimerLabel').textContent = 'Preparation Time';
            document.getElementById('part2Controls').innerHTML = `
            <button class="btn btn-primary" onclick="startPrep()">${UI_TEXT.startPrep}</button>
            <button class="btn btn-ghost" onclick="skipPrep()">${UI_TEXT.skipToSpeaking}</button>`;

            if (state.topic) {
                speaking.playExaminerAudio("Now I'm going to give you a topic and I'd like you to talk about it for one to two minutes. Before you talk, you'll have one minute to think about what you're going to say. You can make some notes if you wish. Here is your topic: " + state.topic.title);
            }
        }

        if (phase === 'part2speak') {
            speaking.clearTimer();
            document.getElementById('part2CueTitle').textContent = state.mode === 'free_practice'
                ? 'Free Practice Prompt'
                : 'Part 2 - Cue Card';
            document.getElementById('part2TopicDisplay').innerHTML = speaking.renderTopicCard(state.topic);
            show('part2CueCard', true);
            const notesEl = document.getElementById('notesInput');
            notesEl.classList.toggle('hidden', state.mode === 'free_practice');
            notesEl.readOnly = true;
            notesEl.style.opacity = state.mode === 'free_practice' ? '' : '0.7';
            notesEl.style.cursor = state.mode === 'free_practice' ? '' : 'default';
            document.getElementById('part2PhaseTitle').textContent = 'Speaking Phase';
            document.getElementById('part2Badge').textContent = speaking.formatDurationBadge(state.part2SpeakingSeconds);
            document.getElementById('part2Badge').className = 'status-badge speaking';
            document.getElementById('part2TimerLabel').textContent = 'Speaking Time';
            document.getElementById('part2Timer').textContent = speaking.formatTimerValue(state.part2SpeakingSeconds);
            document.getElementById('part2Timer').classList.remove('warning', 'danger');
            document.getElementById('part2Controls').innerHTML = `
            <button class="btn btn-danger btn-full" id="btnP2Record" onclick="toggleP2Recording()">
                ${UI_TEXT.startRecording}</button>`;
        }
    }

    function show(id, visible) {
        const el = document.getElementById(id);
        if (!el) return;
        el.classList.toggle('hidden', !visible);
        if (visible) el.classList.add('fade-in');
    }

    speaking.setPhase = setPhase;
    speaking.show = show;
})();
