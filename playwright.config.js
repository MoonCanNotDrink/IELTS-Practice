const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
    testDir: './tests',
    testMatch: '**/*.spec.js',
    outputDir: '.tmp/playwright-test-results',
    use: {
        baseURL: 'http://127.0.0.1:4173',
        browserName: 'chromium',
        headless: true,
    },
    webServer: {
        // Use a shell-safe, cross-platform forward-slash path so Playwright's
        // webServer.command works on both Unix and Windows shells.
        command: 'node tests/fixtures/static-frontend-server.cjs',
        port: 4173,
        reuseExistingServer: true,
    },
});
