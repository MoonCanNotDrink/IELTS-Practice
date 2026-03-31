const { test, expect } = require('@playwright/test');

test('logged-in user can open account settings and bind email', async ({ page }) => {
    await page.addInitScript(() => {
        localStorage.setItem('ielts_token', 'playwright-token');
        localStorage.setItem('ielts_refresh_token', 'playwright-refresh-token');
        window.alert = () => {};
    });

    await page.goto('/');

    const accountButton = page.locator('#btnAccount');
    await expect(accountButton).toBeVisible();
    await expect(accountButton).toHaveText('Bind Email');

    await accountButton.click();
    await expect(page.locator('#authTitle')).toHaveText('Account Settings');
    await expect(page.locator('#emailGroup')).toBeVisible();
    await expect(page.locator('#usernameGroup')).toBeHidden();

    await page.locator('#authEmail').fill('bound@example.com');
    await page.locator('#btnSubmitAuth').click();

    await expect(page.locator('#authStatus')).toContainText('Recovery email saved.');
    await expect(accountButton).toHaveText('Account');
});

test('reset password page validates token and submits new password', async ({ page }) => {
    await page.goto('/reset-password?token=valid-token');

    await expect(page.locator('#resetPasswordForm')).toBeVisible();
    await page.locator('#resetPasswordInput').fill('NewSecret123');
    await page.locator('#resetPasswordConfirmInput').fill('NewSecret123');
    await page.locator('#resetPasswordForm').getByRole('button', { name: 'Reset Password' }).click();

    await expect(page.locator('#resetPasswordStatus')).toContainText('Password has been reset successfully.');
    await expect(page.locator('#resetPasswordForm')).toBeHidden();
});

test('reset password page shows invalid token error', async ({ page }) => {
    await page.route('**/api/auth/password-reset/validate', async (route) => {
        await route.fulfill({
            status: 400,
            contentType: 'application/json',
            body: JSON.stringify({ detail: 'Invalid or expired reset token.' }),
        });
    });

    await page.goto('/reset-password?token=bad-token');

    await expect(page.locator('#resetPasswordForm')).toBeHidden();
    await expect(page.locator('#resetPasswordError')).toContainText('Invalid or expired reset token.');
});
