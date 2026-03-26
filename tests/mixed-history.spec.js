const { test, expect } = require('@playwright/test');

test('renders mixed speaking and writing history on history page', async ({ page }) => {
    const mockHistory = [
        {
            id: 1,
            module_type: 'writing',
            task_type: 'task1',
            title: 'Writing Task 1 - Bar Chart',
            date: '2023-10-01T10:00:00Z',
            scores: { overall: 6.5 },
            scoring_status: 'completed',
            detail_api_path: '/api/writing/attempts/1/detail'
        },
        {
            id: 2,
            module_type: 'speaking',
            task_type: 'full_exam',
            title: 'Speaking Full Exam',
            date: '2023-10-02T10:00:00Z',
            scores: { overall: 7.0 },
            scoring_status: 'completed',
            detail_api_path: '/api/exam/sessions/2/score'
        }
    ];

    await page.route('**/api/dashboard/history**', async route => {
        await route.fulfill({ json: mockHistory });
    });

    await page.addInitScript(() => {
        localStorage.setItem('ielts_token', 'fake-token');
    });

    await page.goto('/history');

    await expect(page.locator('#historyList')).toContainText('Writing Task 1 - Bar Chart');
    await expect(page.locator('#historyList')).toContainText('6.5');
    await expect(page.locator('#historyList')).toContainText('Speaking Full Exam');
    await expect(page.locator('#historyList')).toContainText('7.0');
});
