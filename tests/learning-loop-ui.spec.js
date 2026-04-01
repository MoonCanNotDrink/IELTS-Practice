const { test, expect } = require('@playwright/test');

const makeSpeakingSession = (overrides = {}) => ({
    id: 1,
    module_type: 'speaking',
    task_type: 'full_exam',
    title: 'Speaking Session',
    date: '2024-01-01T10:00:00Z',
    scores: { overall: 6.5 },
    scoring_status: 'completed',
    detail_api_path: '/api/exam/sessions/1/score',
    attempt_count: 1,
    has_retry_match: false,
    has_coaching: false,
    ...overrides,
});

const emptyWeaknessSummary = {
    top_recurring_tags: [],
    trend_direction: {},
    actionable_suggestions: [],
};

test('history list shows attempt badge and hint icons when flags are set', async ({ page }) => {
    const mockHistory = [
        makeSpeakingSession({
            attempt_count: 3,
            has_retry_match: true,
            has_coaching: true,
            title: 'Speaking with Badges',
        }),
    ];

    await page.route('**/api/dashboard/history**', async route => {
        await route.fulfill({ json: mockHistory });
    });

    await page.addInitScript(() => {
        localStorage.setItem('ielts_token', 'fake-token');
    });

    await page.goto('/history');

    await expect(page.getByTestId('history-attempt-badge')).toBeVisible();
    await expect(page.getByTestId('history-attempt-badge')).toContainText('×3');
    await expect(page.getByTestId('history-retry-hint')).toBeVisible();
    await expect(page.getByTestId('history-coaching-hint')).toBeVisible();
});

test('history list hides attempt badge and hint icons when flags are not set', async ({ page }) => {
    const mockHistory = [
        makeSpeakingSession({
            attempt_count: 1,
            has_retry_match: false,
            has_coaching: false,
            title: 'Speaking No Badges',
        }),
    ];

    await page.route('**/api/dashboard/history**', async route => {
        await route.fulfill({ json: mockHistory });
    });

    await page.addInitScript(() => {
        localStorage.setItem('ielts_token', 'fake-token');
    });

    await page.goto('/history');

    await expect(page.getByTestId('history-attempt-badge')).toHaveCount(0);
    await expect(page.getByTestId('history-retry-hint')).toHaveCount(0);
    await expect(page.getByTestId('history-coaching-hint')).toHaveCount(0);
});

test('history detail overlay shows comparison block with score deltas and diff', async ({ page }) => {
    const mockHistory = [
        makeSpeakingSession({
            attempt_count: 2,
            has_retry_match: true,
            has_coaching: false,
            title: 'Detail Session',
        }),
    ];

    const mockDetail = {
        title: 'Detail Session',
        date: '2024-01-01T10:00:00Z',
        scores: { overall: 6.5, fluency: 6.0, vocabulary: 7.0, grammar: 6.0, pronunciation: 6.5 },
        feedback: {},
        transcripts: {},
        answer_learning: [
            {
                recording_id: 42,
                part: 'part1',
                attempt_count: 2,
                has_retry_match: true,
                has_coaching: false,
                weakness_tags: ['short_answer'],
            },
        ],
    };

    const mockComparison = {
        attempt_count: 2,
        comparison: {
            score_deltas: { overall: 0.5, fluency: 1.0, vocabulary: 0, grammar: -0.5, pronunciation: 0.5 },
            transcript_diff: ['- old line', '+ new line', '  unchanged line'],
            weakness_follow_through: {
                addressed_tags: ['filler_words'],
                unchanged_tags: ['short_answer'],
                new_tags: [],
            },
        },
    };

    await page.route('**/api/dashboard/history**', async route => {
        await route.fulfill({ json: mockHistory });
    });
    await page.route('**/api/exam/sessions/1/score**', async route => {
        await route.fulfill({ json: mockDetail });
    });
    await page.route('**/api/speaking/comparisons/42**', async route => {
        await route.fulfill({ json: mockComparison });
    });
    await page.route('**/api/speaking/weakness-summary**', async route => {
        await route.fulfill({ json: emptyWeaknessSummary });
    });

    await page.addInitScript(() => {
        localStorage.setItem('ielts_token', 'fake-token');
    });

    await page.goto('/history');

    await page.getByTestId('history-session-item').first().click();

    await expect(page.getByTestId('comparison-block')).toBeVisible({ timeout: 5000 });
    await expect(page.getByTestId('comparison-delta-overall')).toContainText('+0.5');
    await expect(page.getByTestId('comparison-diff')).toBeVisible();
    await expect(page.getByTestId('comparison-weakness-followthrough')).toBeVisible();
});

test('history detail overlay shows weakness summary with recurring tags', async ({ page }) => {
    const mockHistory = [
        makeSpeakingSession({
            id: 2,
            attempt_count: 2,
            has_retry_match: false,
            detail_api_path: '/api/exam/sessions/2/score',
            title: 'Weakness Session',
        }),
    ];

    const mockDetail = {
        title: 'Weakness Session',
        date: '2024-01-01T10:00:00Z',
        scores: { overall: 6.0 },
        feedback: {},
        transcripts: {},
        answer_learning: [],
    };

    const mockWeaknessSummary = {
        recent_count: 8,
        sample_size_label: 'recurring_pattern',
        sample_size_note: 'Enough sessions.',
        top_recurring_tags: [
            { tag: 'short_answer', count: 5 },
            { tag: 'filler_words', count: 3 },
        ],
        trend_direction: { overall: 'up' },
        actionable_suggestions: [
            { tag: 'short_answer', suggestion: 'Add more concrete examples.' },
        ],
    };

    await page.route('**/api/dashboard/history**', async route => {
        await route.fulfill({ json: mockHistory });
    });
    await page.route('**/api/exam/sessions/2/score**', async route => {
        await route.fulfill({ json: mockDetail });
    });
    await page.route('**/api/speaking/weakness-summary**', async route => {
        await route.fulfill({ json: mockWeaknessSummary });
    });

    await page.addInitScript(() => {
        localStorage.setItem('ielts_token', 'fake-token');
    });

    await page.goto('/history');

    await page.getByTestId('history-session-item').first().click();

    await expect(page.getByTestId('weakness-block')).toBeVisible({ timeout: 5000 });
    await expect(page.getByTestId('weakness-tag').first()).toContainText('short_answer');
});

test('history detail overlay shows per-recording answer_learning list', async ({ page }) => {
    const mockHistory = [
        makeSpeakingSession({
            attempt_count: 2,
            has_retry_match: true,
            has_coaching: false,
            title: 'Answer Learning Session',
        }),
    ];

    const mockDetail = {
        title: 'Answer Learning Session',
        date: '2024-01-01T10:00:00Z',
        scores: { overall: 6.5, fluency: 6.0, vocabulary: 7.0, grammar: 6.0, pronunciation: 6.5 },
        feedback: {},
        transcripts: {},
        answer_learning: [
            {
                recording_id: 42,
                part: 'part1',
                attempt_count: 2,
                has_retry_match: true,
                has_coaching: false,
                weakness_tags: ['short_answer'],
            },
        ],
    };

    const mockComparison = {
        attempt_count: 2,
        comparison: {
            score_deltas: { overall: 0.5 },
            transcript_diff: [],
            weakness_follow_through: { addressed_tags: [], unchanged_tags: [], new_tags: [] },
        },
    };

    await page.route('**/api/dashboard/history**', async route => {
        await route.fulfill({ json: mockHistory });
    });
    await page.route('**/api/exam/sessions/1/score**', async route => {
        await route.fulfill({ json: mockDetail });
    });
    await page.route('**/api/speaking/comparisons/42**', async route => {
        await route.fulfill({ json: mockComparison });
    });
    await page.route('**/api/speaking/weakness-summary**', async route => {
        await route.fulfill({ json: emptyWeaknessSummary });
    });

    await page.addInitScript(() => {
        localStorage.setItem('ielts_token', 'fake-token');
    });

    await page.goto('/history');

    await page.getByTestId('history-session-item').first().click();

    await expect(page.getByTestId('answer-learning-block')).toBeVisible({ timeout: 5000 });
    await expect(page.getByTestId('answer-learning-item').first()).toContainText('part1');
});

test('coaching card appears on scoring results page when coaching data is present', async ({ page }) => {
    await page.route('**/api/**', async route => {
        await route.fulfill({ json: {} });
    });

    await page.addInitScript(() => {
        localStorage.setItem('ielts_token', 'fake-token');
    });

    await page.goto('/speaking');

    await page.evaluate(() => {
        const mockResult = {
            scores: { overall: 6.5, fluency: 6.0, vocabulary: 7.0, grammar: 6.5, pronunciation: 6.0 },
            feedback: { fluency: 'Good fluency.' },
            question_text: 'Talk about a memorable trip.',
            transcripts: {},
            coaching: {
                recordings: [
                    {
                        recording_id: 1,
                        part: 'part2',
                        weakness_tags: ['short_answer', 'filler_words'],
                        has_coaching_payload: true,
                        retry_prompt: 'Talk about a memorable trip.',
                    },
                ],
            },
        };

        const examFlow = document.getElementById('examFlow');
        if (examFlow) examFlow.classList.remove('hidden');
        window.IELTSApp.speaking.setPhase('scoring');
        window.IELTSApp.speaking.displayResults(mockResult, {});
    });

    await expect(page.getByTestId('coaching-card')).toBeVisible({ timeout: 5000 });
    await expect(page.getByTestId('coaching-retry-btn')).toBeVisible();
    await expect(page.getByTestId('coaching-card')).toContainText('short_answer');
});

test('coaching card is hidden when coaching recordings are empty', async ({ page }) => {
    await page.route('**/api/**', async route => {
        await route.fulfill({ json: {} });
    });

    await page.addInitScript(() => {
        localStorage.setItem('ielts_token', 'fake-token');
    });

    await page.goto('/speaking');

    await page.evaluate(() => {
        const mockResult = {
            scores: { overall: 6.0, fluency: 6.0, vocabulary: 6.0, grammar: 6.0, pronunciation: 6.0 },
            feedback: {},
            question_text: '',
            transcripts: {},
            coaching: {
                recordings: [],
            },
        };

        const examFlow = document.getElementById('examFlow');
        if (examFlow) examFlow.classList.remove('hidden');
        window.IELTSApp.speaking.setPhase('scoring');
        window.IELTSApp.speaking.displayResults(mockResult, {});
    });

    await expect(page.getByTestId('coaching-card')).toHaveCount(0);
});

test('retry button sets sessionStorage ielts_retry_prompt and navigates to /speaking', async ({ page }) => {
    await page.route('**/api/**', async route => {
        await route.fulfill({ json: {} });
    });

    await page.addInitScript(() => {
        localStorage.setItem('ielts_token', 'fake-token');
    });

    await page.goto('/speaking');

    await page.evaluate(() => {
        const mockResult = {
            scores: { overall: 6.5, fluency: 6.0, vocabulary: 7.0, grammar: 6.5, pronunciation: 6.0 },
            feedback: {},
            question_text: 'Talk about a memorable trip.',
            transcripts: {},
            coaching: {
                recordings: [
                    {
                        recording_id: 1,
                        part: 'part2',
                        weakness_tags: ['short_answer'],
                        has_coaching_payload: true,
                        retry_prompt: 'Talk about a memorable trip.',
                    },
                ],
            },
        };

        const examFlow = document.getElementById('examFlow');
        if (examFlow) examFlow.classList.remove('hidden');
        window.IELTSApp.speaking.setPhase('scoring');
        window.IELTSApp.speaking.displayResults(mockResult, {});
    });

    await expect(page.getByTestId('coaching-retry-btn')).toBeVisible({ timeout: 5000 });

    await Promise.all([
        page.waitForNavigation({ waitUntil: 'load' }),
        page.getByTestId('coaching-retry-btn').click(),
    ]);

    const retryPrompt = await page.evaluate(() => sessionStorage.getItem('ielts_retry_prompt'));
    expect(retryPrompt).toBeNull();

    await expect(page.locator('#freePracticePanel')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('#freePracticePrompt')).toHaveValue('Talk about a memorable trip.');
});
