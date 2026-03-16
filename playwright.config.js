const fs = require('fs');
const path = require('path');
const { defineConfig } = require('@playwright/test');

function findInstalledChromium() {
    const root = path.join(process.env.USERPROFILE || '', 'AppData', 'Local', 'ms-playwright');
    if (!root || !fs.existsSync(root)) return undefined;

    const chromiumDirs = fs
        .readdirSync(root, { withFileTypes: true })
        .filter((entry) => entry.isDirectory() && entry.name.startsWith('chromium-'))
        .map((entry) => entry.name)
        .sort()
        .reverse();

    for (const dir of chromiumDirs) {
        const executablePath = path.join(root, dir, 'chrome-win64', 'chrome.exe');
        if (fs.existsSync(executablePath)) {
            return executablePath;
        }
    }

    return undefined;
}

const executablePath = findInstalledChromium();

module.exports = defineConfig({
    testDir: './tests',
    use: {
        baseURL: 'http://127.0.0.1:4173',
        browserName: 'chromium',
        headless: true,
        ...(executablePath
            ? {
                  launchOptions: {
                      executablePath,
                  },
              }
            : {}),
    },
    webServer: {
        // Use a shell-safe, cross-platform forward-slash path so Playwright's
        // webServer.command works on both Unix and Windows shells.
        command: 'node tests/fixtures/static-frontend-server.cjs',
        port: 4173,
        reuseExistingServer: true,
    },
});
