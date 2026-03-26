const { test, expect } = require('@playwright/test');

test('completes a Writing Task 1 flow', async ({ page }) => {
    await page.route('/api/writing/prompts/random?task_type=task1', async route => {
        await route.fulfill({
            json: {
                id: 1,
                task_type: 'task1',
                prompt_text: 'The chart below shows the number of men and women in further education in Britain...'
            }
        });
    });

    await page.route('/api/writing/attempts', async route => {
        await route.fulfill({
            json: {
                id: 100,
                module_type: 'writing',
                task_type: 'task1',
                prompt: 'The chart below shows the number of men and women in further education in Britain...',
                essay_text: 'This is a test essay for Task 1. It has a few words.',
                word_count: 13,
                scores: {
                    task: 6.5,
                    coherence: 7.0,
                    lexical: 6.0,
                    grammar: 6.5,
                    overall: 6.5
                },
                feedback: {
                    overall: 'Good effort.',
                    task: 'Addressed the main features.',
                    coherence: 'Logical progression.',
                    lexical: 'Adequate vocabulary.',
                    grammar: 'Some complex structures used.'
                },
                key_improvements: ['Use more varied vocabulary.'],
                sample_answer: 'A model answer would look like this...'
            }
        });
    });

    await page.addInitScript(() => {
        localStorage.setItem('ielts_token', 'fake-token');
    });

    await page.goto('/writing');

    await expect(page.locator('#btnWritingTask1')).toBeVisible();
    
    await page.locator('#btnWritingTask1').click();
    
    await expect(page.locator('#writingFlow')).not.toHaveClass(/hidden/);
    await expect(page.locator('#writingPromptSection')).not.toHaveClass(/hidden/);

    await expect(page.locator('#writingPromptText')).toHaveText('The chart below shows the number of men and women in further education in Britain...');

    await page.locator('#writingEssayInput').fill('This is a test essay for Task 1. It has a few words.');
    await expect(page.locator('#writingWordCount')).toHaveText('13');

    await page.locator('#btnSubmitWriting').click();

    await expect(page.locator('#writingPromptSection')).toHaveClass(/hidden/);
    await expect(page.locator('#writingScoreSection')).not.toHaveClass(/hidden/);
    await expect(page.locator('#writingScoreResults')).toBeVisible();

    const overallScore = page.locator('.score-item.overall .score-value');
    await expect(overallScore).toHaveText('6.5');
    
    await expect(page.locator('#writingEssayDisplay')).toHaveText('This is a test essay for Task 1. It has a few words.');
    await expect(page.locator('#writingFeedbackSection')).toContainText('Good effort.');
    await expect(page.locator('#writingFeedbackSection')).toContainText('Addressed the main features.');
});
