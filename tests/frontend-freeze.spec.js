const { test, expect } = require('@playwright/test');

test('landing page shows speaking and writing entry links without SPA controls', async ({ page }) => {
    const pageErrors = [];
    const failedRequests = [];

    page.on('pageerror', (error) => {
        pageErrors.push(error.message);
    });
    page.on('requestfailed', (request) => {
        if (request.url().startsWith('https://fonts.googleapis.com/')) return;
        failedRequests.push({ url: request.url(), errorText: request.failure()?.errorText || 'unknown' });
    });

    await page.goto('/');

    await expect(page.locator('a[href="/speaking"]')).toBeVisible();
    await expect(page.locator('a[href="/writing"]')).toBeVisible();

    await expect(page.locator('#btnFullExam')).toHaveCount(0);
    await expect(page.locator('#modeSelector')).toHaveCount(0);
    await expect(page.locator('#examFlow')).toHaveCount(0);
    await expect(page.locator('#writingFlow')).toHaveCount(0);

    expect(pageErrors).toEqual([]);
    expect(failedRequests).toEqual([]);

    await page.locator('a[href="/speaking"]').click();
    await expect(page).toHaveURL(/\/speaking/);

    await page.goto('/');
    await page.locator('a[href="/writing"]').click();
    await expect(page).toHaveURL(/\/writing/);
});
