const { test, expect } = require('@playwright/test');

const ROUTES = ['/', '/history'];

for (const route of ROUTES) {
    test.describe(`auth register modal ${route}`, () => {
        test('supports password toggles and confirm-password validation', async ({ page }) => {
            await page.addInitScript(() => {
                localStorage.removeItem('ielts_token');
                window.alert = () => {};
            });

            await page.goto(route);

            const authModal = page.locator('#authModal');
            if (!(await authModal.evaluate((element) => element.classList.contains('show')))) {
                await page.locator('#btnLogin').click();
            }

            await page.locator('#authToggleText a').click();

            const passwordInput = page.locator('#authPassword');
            const confirmInput = page.locator('#authConfirmPassword');
            const passwordToggle = page.locator('#authPasswordToggle');
            const confirmToggle = page.locator('#authConfirmPasswordToggle');
            const authError = page.locator('#authError');

            await expect(page.locator('#confirmPasswordGroup')).toBeVisible();
            await expect(page.locator('#inviteCodeGroup')).toBeVisible();
            await expect(passwordToggle).toBeVisible();

            await passwordInput.fill('Secret123');
            await passwordToggle.click();
            await expect(passwordToggle).toHaveText('Hide');
            await expect(passwordInput).toHaveAttribute('type', 'text');

            await confirmInput.fill('Secret321');
            await confirmToggle.click();
            await expect(confirmToggle).toHaveText('Hide');
            await expect(confirmInput).toHaveAttribute('type', 'text');

            await page.locator('#authUsername').fill('new-user');
            await page.locator('#btnSubmitAuth').click();
            await expect(authError).toContainText('Passwords do not match.');

            await confirmInput.fill('');
            await page.locator('#btnSubmitAuth').click();
            await expect(authError).toContainText('Please confirm your password.');

            await page.locator('#authToggleText a').click();
            await expect(page.locator('#confirmPasswordGroup')).toBeHidden();
            await expect(passwordToggle).toBeHidden();
            await expect(passwordInput).toHaveAttribute('type', 'password');
        });
    });
}
