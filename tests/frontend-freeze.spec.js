const { test, expect } = require('@playwright/test');

test('homepage remains interactive after a DOM mutation', async ({ page }) => {
    const consoleErrors = [];
    const pageErrors = [];
    const failedRequests = [];

    page.on('console', (message) => {
        if (message.type() === 'error') {
            if (message.text().includes('fonts.googleapis.com') || message.text().includes('ERR_CONNECTION_CLOSED')) {
                return;
            }
            consoleErrors.push(message.text());
        }
    });
    page.on('pageerror', (error) => {
        pageErrors.push(error.message);
    });
    page.on('requestfailed', (request) => {
        if (request.url().startsWith('https://fonts.googleapis.com/')) {
            return;
        }
        failedRequests.push({
            url: request.url(),
            errorText: request.failure()?.errorText || 'unknown',
        });
    });

    await page.goto('/');

    await expect(page.locator('#modeSelector')).toBeVisible();

    await page.evaluate(() => {
        const marker = document.createElement('span');
        marker.id = 'dom-mutation-marker';
        marker.textContent = 'mutated';
        document.getElementById('historyContent').appendChild(marker);
    });

    await page.evaluate(() => {
        document.body.dataset.afterMutation = 'ok';
    });

    await expect(page.locator('body')).toHaveAttribute('data-after-mutation', 'ok');
    await expect(page.locator('#dom-mutation-marker')).toHaveText('mutated');

    await page.locator('#btnFullExam').click();

    await expect(page.locator('#examFlow')).toBeVisible();
    await expect(page.locator('#modeSelector')).toHaveClass(/hidden/);
    expect(pageErrors).toEqual([]);
    expect(failedRequests).toEqual([]);
    expect(consoleErrors).toEqual([]);
});
