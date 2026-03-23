const { test, expect } = require('@playwright/test');

test.describe('theme mode switch', () => {
    test('supports system, light, and dark modes with persistence', async ({ page }) => {
        await page.addInitScript(() => {
            localStorage.setItem('ielts_token', 'playwright-token');
            localStorage.removeItem('ielts_theme_mode');
            window.alert = () => {};
        });

        await page.route('**/api/scoring/history?limit=5', (route) =>
            route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }),
        );

        await page.emulateMedia({ colorScheme: 'light' });
        await page.goto('/');

        const html = page.locator('html');
        await expect(html).toHaveAttribute('data-theme-mode', 'system');
        await expect(html).toHaveAttribute('data-theme', 'light');
        await expect(page.locator('#currentThemeLabel')).toHaveText('System');

        await page.locator('#btnThemeToggle').click();
        await page.locator('#themeMenu .theme-option[data-theme-mode="dark"]').click();
        await expect(html).toHaveAttribute('data-theme-mode', 'dark');
        await expect(html).toHaveAttribute('data-theme', 'dark');
        await expect(page.locator('#currentThemeLabel')).toHaveText('Dark');
        await expect.poll(() => page.evaluate(() => localStorage.getItem('ielts_theme_mode'))).toBe('dark');

        await page.locator('#btnThemeToggle').click();
        await page.locator('#themeMenu .theme-option[data-theme-mode="light"]').click();
        await expect(html).toHaveAttribute('data-theme-mode', 'light');
        await expect(html).toHaveAttribute('data-theme', 'light');
        await expect(page.locator('#currentThemeLabel')).toHaveText('Light');
        await expect.poll(() => page.evaluate(() => localStorage.getItem('ielts_theme_mode'))).toBe('light');

        await page.locator('#btnThemeToggle').click();
        await page.locator('#themeMenu .theme-option[data-theme-mode="system"]').click();
        await expect(html).toHaveAttribute('data-theme-mode', 'system');
        await expect(html).toHaveAttribute('data-theme', 'light');
        await expect(page.locator('#currentThemeLabel')).toHaveText('System');

        await page.emulateMedia({ colorScheme: 'dark' });
        await expect(html).toHaveAttribute('data-theme', 'dark');
    });
});
