const { test, expect } = require('@playwright/test');

const WRITING_PROMPTS = [
    { id: 1, slug: 'task1-bar-chart', task_type: 'task1', title: 'Bar Chart Description', prompt_text: 'The bar chart below shows...', prompt_details: null },
    { id: 2, slug: 'task1-pie-chart', task_type: 'task1', title: 'Pie Chart Description', prompt_text: 'The pie chart illustrates...', prompt_details: null },
    { id: 3, slug: 'task2-environment', task_type: 'task2', title: 'Environmental Protection', prompt_text: 'Some people believe that environmental problems should be solved on a global scale...', prompt_details: null },
    { id: 4, slug: 'task2-technology', task_type: 'task2', title: 'Technology in Education', prompt_text: 'Many people think that technology has made our lives easier...', prompt_details: null },
    { id: 5, slug: 'task2-remote-work', task_type: 'task2', title: 'Remote Work', prompt_text: 'Working from home has become increasingly common...', prompt_details: null },
];

function addAuthToken(page) {
    return page.addInitScript(() => {
        localStorage.setItem('ielts_token', 'fake-token');
    });
}

function routeWritingPrompts(page, payload = WRITING_PROMPTS) {
    return page.route('**/api/writing/prompts', async (route) => {
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(payload),
        });
    });
}

function makeWritingAttemptResult(overrides = {}) {
    return {
        id: 321,
        module_type: 'writing',
        task_type: 'task2',
        prompt: 'Some people believe that environmental problems should be solved on a global scale...',
        essay_text: 'Sample essay text.',
        word_count: 3,
        scores: {
            task: 6.5,
            coherence: 6.5,
            lexical: 6.0,
            grammar: 6.5,
            overall: 6.5,
        },
        feedback: {
            overall: 'Good effort.',
            task: 'You addressed the prompt.',
            coherence: 'The structure is mostly clear.',
            lexical: 'Vocabulary range is adequate.',
            grammar: 'Grammar is generally controlled.',
        },
        key_improvements: ['Add one specific example.'],
        sample_answer: 'A stronger sample answer goes here.',
        ...overrides,
    };
}

test('Writing Free Practice button is visible on /writing page', async ({ page }) => {
    await addAuthToken(page);
    await page.goto('/writing');

    await expect(page.locator('#btnWritingFreePractice')).toBeVisible();
});

test('Back-to-Home link is visible on /writing initial screen', async ({ page }) => {
    await addAuthToken(page);
    await page.goto('/writing');

    await expect(page.locator('a[href="/"]').filter({ hasText: 'Back to Home' }).first()).toBeVisible();
});

test('Back-to-Home link is visible on /speaking initial screen', async ({ page }) => {
    await addAuthToken(page);
    await page.goto('/speaking');

    await expect(page.locator('a[href="/"]').filter({ hasText: 'Back to Home' }).first()).toBeVisible();
});

test('Writing free practice panel shows/hides on button click', async ({ page }) => {
    await addAuthToken(page);
    await routeWritingPrompts(page);
    await page.goto('/writing');

    await page.locator('#btnWritingFreePractice').click();
    await expect(page.locator('#writingFreePracticePanel')).toBeVisible();

    await page.locator('#writingFreePracticePanel button.btn-ghost', { hasText: 'Cancel' }).click();
    await expect(page.locator('#writingFreePracticePanel')).toBeHidden();
});

test('Writing free practice library mode: select prompt and start writing', async ({ page }) => {
    let attemptPayload = null;

    await addAuthToken(page);
    await routeWritingPrompts(page);
    await page.route('**/api/writing/attempts', async (route) => {
        attemptPayload = JSON.parse(route.request().postData() || '{}');
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(makeWritingAttemptResult({
                prompt: WRITING_PROMPTS[2].prompt_text,
                essay_text: 'This essay is for free practice library mode.',
                word_count: 8,
            })),
        });
    });

    await page.goto('/writing');
    await page.locator('#btnWritingFreePractice').click();

    await expect(page.locator('#writingFpTopicSelect option', { hasText: 'Loading prompts...' })).toHaveCount(0);
    await page.locator('#writingFpTopicSelect').selectOption('3');
    await page.locator('#btnStartWritingFreePractice').click();

    await expect(page.locator('#writingFlow')).toBeVisible();
    await expect(page.locator('#writingPromptSection')).toBeVisible();
    await expect(page.locator('#writingPromptText')).toContainText(WRITING_PROMPTS[2].prompt_text);

    await page.locator('#writingEssayInput').fill('This essay is for free practice library mode.');
    await page.locator('#btnSubmitWriting').click();

    await expect(page.locator('#writingScoreSection')).toBeVisible();
    expect(attemptPayload).toEqual({
        essay_text: 'This essay is for free practice library mode.',
        prompt_id: 3,
    });
});

test('Writing free practice custom mode: enter prompt and start writing', async ({ page }) => {
    let attemptPayload = null;
    const customPrompt = 'Discuss whether remote work should remain a long-term option for employees.';
    const customEssay = 'Remote work should remain an option because it improves flexibility and productivity for many workers.';

    await addAuthToken(page);
    await routeWritingPrompts(page);
    await page.route('**/api/writing/attempts', async (route) => {
        attemptPayload = JSON.parse(route.request().postData() || '{}');
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(makeWritingAttemptResult({
                prompt: customPrompt,
                essay_text: customEssay,
                task_type: 'task2',
                word_count: 15,
            })),
        });
    });

    await page.goto('/writing');
    await page.locator('#btnWritingFreePractice').click();
    await page.locator('#wfpTypeToggle .btn[data-target="custom"]').click();

    await expect(page.locator('#wfp-custom-view')).toBeVisible();
    await expect(page.locator('#wfp-library-view')).toBeHidden();

    await page.locator('#writingFpCustomPrompt').fill(customPrompt);
    await page.locator('#btnStartWritingFreePractice').click();

    await expect(page.locator('#writingFlow')).toBeVisible();
    await expect(page.locator('#writingPromptSection')).toBeVisible();
    await expect(page.locator('#writingPromptText')).toContainText(customPrompt);

    await page.locator('#writingEssayInput').fill(customEssay);
    await page.locator('#btnSubmitWriting').click();

    await expect(page.locator('#writingScoreSection')).toBeVisible();
    expect(attemptPayload).toEqual({
        essay_text: customEssay,
        custom_prompt: customPrompt,
        custom_task_type: 'task2',
    });
});

test('Writing free practice validates empty selection in library mode', async ({ page }) => {
    await addAuthToken(page);
    await routeWritingPrompts(page);
    await page.goto('/writing');

    await page.locator('#btnWritingFreePractice').click();
    await expect(page.locator('#writingFpTopicSelect option', { hasText: 'Loading prompts...' })).toHaveCount(0);

    await page.locator('#btnStartWritingFreePractice').click();

    await expect(page.locator('#writingFpError')).toBeVisible();
    await expect(page.locator('#writingFpError')).toContainText('Please select a prompt');
});

test('Writing free practice validates empty prompt in custom mode', async ({ page }) => {
    await addAuthToken(page);
    await routeWritingPrompts(page);
    await page.goto('/writing');

    await page.locator('#btnWritingFreePractice').click();
    await page.locator('#wfpTypeToggle .btn[data-target="custom"]').click();
    await page.locator('#writingFpCustomPrompt').fill('');
    await page.locator('#btnStartWritingFreePractice').click();

    await expect(page.locator('#writingFpError')).toBeVisible();
    await expect(page.locator('#writingFpError')).toContainText('Enter a custom prompt');
});
