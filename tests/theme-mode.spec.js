const { test, expect } = require('@playwright/test');

test.describe('theme mode switch', () => {
    test('supports system, light, and dark modes with persistence', async ({ page }) => {
        await page.addInitScript(() => {
            localStorage.setItem('ielts_token', 'playwright-token');
            localStorage.removeItem('ielts_theme_mode');
            window.alert = () => {};
        });

        await page.route('**/api/dashboard/history?limit=5', (route) =>
            route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }),
        );

        await page.emulateMedia({ colorScheme: 'light' });
        await page.goto('/');

        const html = page.locator('html');
        await expect(html).toHaveAttribute('data-theme-mode', 'system');
        await expect(html).toHaveAttribute('data-theme', 'light');
        await expect(page.locator('#currentThemeLabel')).toHaveText('System');

        await page.getByRole('button', { name: /system/i }).click();
        await page.getByRole('menuitemradio', { name: 'Dark Mode' }).click();
        await expect(html).toHaveAttribute('data-theme-mode', 'dark');
        await expect(html).toHaveAttribute('data-theme', 'dark');
        await expect(page.locator('#currentThemeLabel')).toHaveText('Dark');
        await expect.poll(() => page.evaluate(() => localStorage.getItem('ielts_theme_mode'))).toBe('dark');

        await page.getByRole('button', { name: /dark/i }).click();
        await page.getByRole('menuitemradio', { name: 'Light Mode' }).click();
        await expect(html).toHaveAttribute('data-theme-mode', 'light');
        await expect(html).toHaveAttribute('data-theme', 'light');
        await expect(page.locator('#currentThemeLabel')).toHaveText('Light');
        await expect.poll(() => page.evaluate(() => localStorage.getItem('ielts_theme_mode'))).toBe('light');

        await page.getByRole('button', { name: /light/i }).click();
        await page.getByRole('menuitemradio', { name: 'Follow System' }).click();
        await expect(html).toHaveAttribute('data-theme-mode', 'system');
        await expect(html).toHaveAttribute('data-theme', 'light');
        await expect(page.locator('#currentThemeLabel')).toHaveText('System');

        await page.emulateMedia({ colorScheme: 'dark' });
        await expect(html).toHaveAttribute('data-theme', 'dark');
    });
});
