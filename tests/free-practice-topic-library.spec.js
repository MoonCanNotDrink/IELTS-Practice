const { test, expect } = require('@playwright/test');

const LIBRARY_RESPONSE = {
    official_topics: [
        { id: 1, title: 'Describe a famous person you would like to meet.', category: 'people' },
        { id: 2, title: 'Describe a shopping mall.', category: 'places' },
    ],
    saved_topics: [
        { id: 10, prompt_text: 'Describe your morning routine', category: 'general', title: 'Describe your morning routine' },
    ],
};

function addCommonInitScript(page) {
    return page.addInitScript(() => {
        localStorage.setItem('ielts_token', 'playwright-token');
        window.alert = () => {};
    });
}

function stubRecording(page) {
    return page.evaluate(() => {
        window.startRecording = async (target) => {
            state.isRecording = true;
            state.currentRecordingTarget = target;
            state.audioChunks = [];
        };

        window.stopRecording = (onDone) => {
            state.isRecording = false;
            onDone(
                new Blob(
                    [new Uint8Array([82, 73, 70, 70, 0, 0, 0, 0, 87, 65, 86, 69])],
                    { type: 'audio/wav' },
                ),
                'Test transcript from browser speech.',
            );
        };
    });
}

function routeCommonEndpoints(page, libraryPayload = LIBRARY_RESPONSE) {
    return Promise.all([
        page.route('**/api/part2/free-practice-topics', async (route) => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify(libraryPayload),
            });
        }),
    ]);
}

async function openFreePracticePanel(page) {
    await page.goto('/speaking');
    await page.locator('#btnFreePractice').click();
    await expect(page.locator('#freePracticePanel')).toBeVisible();
}

async function openTopicDropdown(page) {
    await page.locator('#fpTopicSelectBtn').click();
    await expect(page.locator('#fpTopicDropdown')).toBeVisible();
}

async function selectTopicOption(page, optionText) {
    await openTopicDropdown(page);
    await page.locator('#fpTopicOptions .custom-select-option').filter({ hasText: optionText }).first().click();
}

test.describe('free-practice topic library', () => {
    test('history titles are rendered as plain text instead of HTML markup', async ({ page }) => {
        await addCommonInitScript(page);
        await page.route('**/api/dashboard/history**', (route) =>
            route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify([
                    {
                        session_id: 1,
                        title: '<strong>Unsafe history title</strong>',
                        date: '2026-03-19T10:00:00Z',
                        module_type: 'speaking',
                        task_type: 'part2_only',
                        scores: { overall: 6.5 },
                    },
                ]),
            }),
        );
        await page.route('**/api/part2/free-practice-topics', async (route) => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify(LIBRARY_RESPONSE),
            });
        });

        await page.goto('/history');

        const historyList = page.getByTestId('history-list');
        await expect(historyList).toContainText('<strong>Unsafe history title</strong>', { timeout: 15000 });
        await expect(page.locator('#historyList strong')).toHaveCount(0);
    });

    test('grouped custom dropdown renders official and saved topic sections', async ({ page }) => {
        await addCommonInitScript(page);
        await routeCommonEndpoints(page);
        await openFreePracticePanel(page);

        await expect(page.locator('#fpTopicSelectBtn')).toBeVisible();
        await openTopicDropdown(page);

        await expect(page.locator('.custom-select-optgroup')).toHaveText([
            'Official Topics',
            'Your Saved Topics',
        ]);
        await expect(page.locator('#fpTopicOptions [role="group"]')).toHaveCount(2);
        await expect(page.locator('#fpTopicGroupOfficialCount')).toHaveText('2 items');
        await expect(page.locator('#fpTopicGroupSavedCount')).toHaveText('1 item');
        await expect(page.locator('#fpTopicOptions [role="group"]').nth(0)).toHaveAttribute('aria-labelledby', 'fpTopicGroupOfficialLabel fpTopicGroupOfficialCount');
        await expect(page.locator('#fpTopicOptions [role="group"]').nth(1)).toHaveAttribute('aria-labelledby', 'fpTopicGroupSavedLabel fpTopicGroupSavedCount');
        await expect(page.locator('.custom-select-option')).toHaveText([
            'Describe a famous person you would like to meet.',
            'Describe a shopping mall.',
            'Describe your morning routine',
        ]);
    });

    
    test('custom dropdown supports keyboard navigation', async ({ page }) => {
        await addCommonInitScript(page);
        await routeCommonEndpoints(page);
        await openFreePracticePanel(page);

        const trigger = page.locator('#fpTopicSelectBtn');
        await trigger.focus();
        await expect(trigger).toHaveAttribute('aria-labelledby', 'fpTopicSelectLabel fpTopicSelectText');
        await expect(page.locator('#fpTopicOptions')).toHaveAttribute('aria-labelledby', 'fpTopicSelectLabel');

        await page.keyboard.press('Enter');
        await expect(page.locator('#fpTopicDropdown')).toBeVisible();
        await expect(trigger).toHaveAttribute('aria-expanded', 'true');
        await expect(page.locator('#fpTopicSearchInput')).toBeFocused();
        await expect(page.locator('#fpTopicSearchInput')).toHaveAttribute('aria-label', 'Search topics');

        await page.keyboard.press('Escape');
        await expect(page.locator('#fpTopicDropdown')).toBeHidden();
        await expect(trigger).toHaveAttribute('aria-expanded', 'false');
        await expect(trigger).toBeFocused();

        await page.keyboard.press('ArrowDown');
        await expect(page.locator('#fpTopicDropdown')).toBeVisible();
        await expect(trigger).toHaveAttribute('aria-expanded', 'true');
        await expect(page.locator('#fpTopicSearchInput')).toBeFocused();
        await expect(page.locator('.custom-select-option').nth(0)).toBeVisible();

        await page.keyboard.press('ArrowUp');
        await expect(page.locator('.custom-select-option').nth(2)).toBeFocused();

        await page.keyboard.press('ArrowDown');
        await expect(page.locator('.custom-select-option').nth(2)).toBeFocused();

        await page.locator('#fpTopicSearchInput').focus();
        await page.keyboard.press('ArrowDown');
        await expect(page.locator('.custom-select-option').nth(0)).toBeFocused();

        await page.keyboard.press('ArrowDown');
        await expect(page.locator('.custom-select-option').nth(1)).toBeFocused();

        await page.keyboard.press('ArrowUp');
        await expect(page.locator('.custom-select-option').nth(0)).toBeFocused();

        await page.keyboard.press('Enter');
        await expect(page.locator('#fpTopicDropdown')).toBeHidden();
        await expect(trigger).toHaveAttribute('aria-expanded', 'false');
        await expect(page.locator('#fpTopicSelectText')).toHaveText('Describe a famous person you would like to meet.');
        expect(await page.locator('#freePracticeTopicSelect').inputValue()).toBe('official:1');

        await trigger.focus();
        await page.keyboard.press('ArrowDown');
        await expect(page.locator('#fpTopicDropdown')).toBeVisible();
        await page.keyboard.press('Tab');
        await expect(page.locator('#fpTopicDropdown')).toBeHidden();
    });

    test('search filters custom dropdown options and shows the empty state', async ({ page }) => {
        await addCommonInitScript(page);
        await routeCommonEndpoints(page);
        await openFreePracticePanel(page);
        await openTopicDropdown(page);

        await page.locator('#fpTopicSearchInput').fill('mall');
        await expect(page.locator('.custom-select-option')).toHaveCount(1);
        await expect(page.locator('.custom-select-option').first()).toHaveText('Describe a shopping mall.');

        await page.locator('#fpTopicSearchInput').fill('zzzz');
        await expect(page.locator('.custom-select-empty')).toBeVisible();
        await expect(page.locator('.custom-select-empty')).toHaveText('No topics found');
    });

    test('topic text is rendered as plain text instead of HTML markup', async ({ page }) => {
        await addCommonInitScript(page);
        await routeCommonEndpoints(page, {
            official_topics: [
                { id: 1, title: '<strong>Unsafe topic</strong>', category: 'safety' },
            ],
            saved_topics: [
                { id: 10, prompt_text: '<img src=x onerror=alert(1)>', category: 'general', title: '<img src=x onerror=alert(1)>' },
            ],
        });
        await openFreePracticePanel(page);
        await openTopicDropdown(page);

        await expect(page.locator('.custom-select-option').nth(0)).toHaveText('<strong>Unsafe topic</strong>');
        await expect(page.locator('.custom-select-option').nth(1)).toHaveText('<img src=x onerror=alert(1)>');
        await expect(page.locator('#fpTopicOptions strong')).toHaveCount(0);
        await expect(page.locator('#fpTopicOptions img')).toHaveCount(0);
    });

    test('selecting a saved topic updates the trigger label and hidden value', async ({ page }) => {
        await addCommonInitScript(page);
        await routeCommonEndpoints(page);
        await openFreePracticePanel(page);

        await selectTopicOption(page, 'Describe your morning routine');

        await expect(page.locator('#fpTopicSelectText')).toHaveText('Describe your morning routine');
        expect(await page.locator('#freePracticeTopicSelect').inputValue()).toBe('saved:10');
        await expect(page.locator('#fpTopicDropdown')).toBeHidden();
    });

    test('reopening dropdown preserves selected option state', async ({ page }) => {
        await addCommonInitScript(page);
        await routeCommonEndpoints(page);
        await openFreePracticePanel(page);

        await selectTopicOption(page, 'Describe your morning routine');
        await openTopicDropdown(page);

        const savedOption = page.locator('#fpTopicOptions .custom-select-option').filter({ hasText: 'Describe your morning routine' }).first();
        await expect(savedOption).toHaveClass(/selected/);
        await expect(savedOption).toHaveAttribute('aria-selected', 'true');
    });

    test('starting with a saved topic sends saved_topic_id in session creation', async ({ page }) => {
        let sessionPayload = null;

        await addCommonInitScript(page);
        await routeCommonEndpoints(page);

        await page.route('**/api/part2/sessions', async (route) => {
            sessionPayload = JSON.parse(route.request().postData() || '{}');
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    session_id: 99,
                    topic_id: null,
                    custom_topic: null,
                    status: 'in_progress',
                }),
            });
        });

        await openFreePracticePanel(page);
        await stubRecording(page);
        await selectTopicOption(page, 'Describe your morning routine');

        await page.locator('#btnStartFreePractice').click();
        await expect(page.locator('#examFlow')).toBeVisible();
        expect(sessionPayload).toEqual({ saved_topic_id: 10 });
    });

    test('starting with a custom prompt sends custom_topic in session creation', async ({ page }) => {
        let sessionPayload = null;

        await addCommonInitScript(page);
        await routeCommonEndpoints(page);

        await page.route('**/api/part2/sessions', async (route) => {
            sessionPayload = JSON.parse(route.request().postData() || '{}');
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    session_id: 100,
                    topic_id: null,
                    custom_topic: 'Describe a hobby you recently started.',
                    status: 'in_progress',
                }),
            });
        });

        await openFreePracticePanel(page);
        await stubRecording(page);
        await page.locator('#fpTypeToggle .btn[data-target="custom"]').click();
        await page.locator('#freePracticePrompt').fill('Describe a hobby you recently started.');

        await page.locator('#btnStartFreePractice').click();
        await expect(page.locator('#examFlow')).toBeVisible();
        expect(sessionPayload).toEqual({ custom_topic: 'Describe a hobby you recently started.' });
    });

    test('starting with an official topic sends topic_id in session creation', async ({ page }) => {
        let sessionPayload = null;

        await addCommonInitScript(page);
        await routeCommonEndpoints(page);

        await page.route('**/api/part2/sessions', async (route) => {
            sessionPayload = JSON.parse(route.request().postData() || '{}');
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    session_id: 200,
                    topic_id: 1,
                    custom_topic: null,
                    status: 'in_progress',
                }),
            });
        });

        await openFreePracticePanel(page);
        await stubRecording(page);
        await selectTopicOption(page, 'Describe a famous person you would like to meet.');

        await expect(page.locator('#fpTopicSelectText')).toHaveText('Describe a famous person you would like to meet.');
        expect(await page.locator('#freePracticeTopicSelect').inputValue()).toBe('official:1');

        await page.locator('#btnStartFreePractice').click();
        await expect(page.locator('#examFlow')).toBeVisible();
        expect(sessionPayload).toEqual({ topic_id: 1 });
    });
});
