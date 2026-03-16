const { test, expect } = require('@playwright/test');

test('audio examiner falls back to browser speech when server tts is unavailable', async ({ page }) => {
    await page.addInitScript(() => {
        window.__spokenTexts = [];
        const speechProto = window.speechSynthesis && Object.getPrototypeOf(window.speechSynthesis);
        if (!speechProto) return;

        Object.defineProperty(speechProto, 'cancel', {
            configurable: true,
            value() {},
        });
        Object.defineProperty(speechProto, 'speak', {
            configurable: true,
            value(utterance) {
                window.__spokenTexts.push({
                    text: utterance.text,
                    lang: utterance.lang,
                    rate: utterance.rate,
                });
            },
        });
    });

    await page.goto('/');
    await page.evaluate(() => {
        const toggle = document.getElementById('audioModeToggle');
        toggle.checked = true;
        toggle.dispatchEvent(new Event('change', { bubbles: true }));
    });

    await page.evaluate(async () => {
        await window.playExaminerAudio('Please describe your hometown.');
    });

    await expect.poll(() => page.evaluate(() => window.__spokenTexts.length)).toBe(1);
    await expect.poll(() => page.evaluate(() => window.__spokenTexts[0]?.text)).toBe('Please describe your hometown.');
    await expect.poll(() => page.evaluate(() => window.__spokenTexts[0]?.lang)).toBe('en-US');
    await expect
        .poll(() => page.evaluate(() => Number(window.__spokenTexts[0]?.rate?.toFixed(2))))
        .toBe(0.9);
});
