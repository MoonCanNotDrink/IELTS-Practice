const { test, expect } = require('@playwright/test');

test('free practice reuses the part2 speaking and scoring flow', async ({ page }) => {
    const requestOrder = [];

    await page.addInitScript(() => {
        localStorage.setItem('ielts_token', 'playwright-token');
        window.alert = () => {};
    });

    await page.route('**/api/dashboard/history?limit=5', async (route) => {
        requestOrder.push('history');
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: '[]',
        });
    });

    await page.route('**/api/part2/sessions', async (route) => {
        requestOrder.push('create');
        const payload = JSON.parse(route.request().postData() || '{}');
        expect(payload).toEqual({ custom_topic: 'Describe a skill you learned online.' });
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ session_id: 42, topic_id: null, custom_topic: payload.custom_topic, status: 'in_progress' }),
        });
    });

    await page.route('**/api/part2/sessions/42/upload-audio', async (route) => {
        requestOrder.push('upload');
        const postData = route.request().postData() || '';
        expect(postData).toContain('name="question_text"');
        expect(postData).toContain('Describe a skill you learned online.');
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
                recording_id: 7,
                transcript: 'I learned this skill from online tutorials and daily practice.',
                word_count: 11,
                duration_seconds: 90,
            }),
        });
    });

    await page.route('**/api/part2/sessions/42/score', async (route) => {
        requestOrder.push('score');
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
                session_id: 42,
                exam_scope: 'part2_only',
                is_full_flow: false,
                missing_parts: ['part1', 'part3'],
                scores: {
                    fluency: 6.5,
                    vocabulary: 6.0,
                    grammar: 6.0,
                    pronunciation: 6.5,
                    overall: 6.5,
                },
                feedback: {
                    fluency: 'Clear progression throughout the answer.',
                    vocabulary: 'Good control of topic vocabulary.',
                    grammar: 'Mostly accurate sentence control.',
                    pronunciation: 'Easy to follow overall.',
                    overall: 'A solid free-practice response.',
                },
                key_improvements: ['Add one more specific example.'],
                sample_answer: 'A stronger answer would add a concrete success story.',
            }),
        });
    });

    await page.goto('/');

    await page.evaluate(() => {
        window.startRecording = async (target) => {
            state.isRecording = true;
            state.currentRecordingTarget = target;
            state.audioChunks = [];
        };

        window.stopRecording = (onDone) => {
            state.isRecording = false;
            onDone(new Blob([new Uint8Array([82, 73, 70, 70, 0, 0, 0, 0, 87, 65, 86, 69])], { type: 'audio/wav' }), 'I learned this skill from online tutorials and daily practice.');
        };
    });

    await page.locator('#btnFreePractice').click();
    await expect(page.locator('#freePracticePanel')).toBeVisible();

    await page.locator('#fpTypeToggle .btn[data-target="custom"]').click();
    await page.locator('#freePracticePrompt').fill('Describe a skill you learned online.');
    await page.locator('#freePracticeCustomSeconds').fill('90');
    await page.locator('#btnStartFreePractice').click();

    await expect(page.locator('#examFlow')).toBeVisible();
    await expect(page.locator('#part2CueTitle')).toHaveText('Free Practice Prompt');
    await expect(page.locator('#part2TopicDisplay')).toContainText('Describe a skill you learned online.');
    await expect(page.locator('#part2Timer')).toHaveText('01:30');
    await expect(page.locator('#part2Badge')).toHaveText('90 Sec');

    await page.locator('#btnP2Record').click();
    await expect(page.locator('#btnP2Record')).toContainText('Stop Recording');
    await page.locator('#btnP2Record').click();

    await expect(page.locator('#scoreSection')).toBeVisible();
    await expect(page.locator('#scoreResults')).toBeVisible();
    await expect(page.locator('#transcriptDisplay')).toContainText('I learned this skill from online tutorials and daily practice.');
    await expect(page.locator('#scoresGrid')).toContainText('Overall Band Score');
    await expect(page.locator('#feedbackSection')).toContainText('A solid free-practice response.');
    expect(requestOrder).toEqual(['history', 'create', 'upload', 'score']);
});
