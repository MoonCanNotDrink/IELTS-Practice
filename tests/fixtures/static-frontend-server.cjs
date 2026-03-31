const fs = require('fs');
const http = require('http');
const path = require('path');

const ROOT = path.resolve(__dirname, '..', '..');
const FRONTEND_DIR = path.join(ROOT, 'frontend');
const PORT = Number(process.env.PLAYWRIGHT_FRONTEND_PORT || 4173);

function sendFile(response, filePath, contentType) {
    response.writeHead(200, { 'Content-Type': `${contentType}; charset=utf-8` });
    response.end(fs.readFileSync(filePath, 'utf8'));
}

const server = http.createServer((request, response) => {
    const url = new URL(request.url, `http://127.0.0.1:${PORT}`);
    const pathname = url.pathname;

    if (pathname === '/') {
        return sendFile(response, path.join(FRONTEND_DIR, 'index.html'), 'text/html');
    }

    if (pathname === '/history') {
        return sendFile(response, path.join(FRONTEND_DIR, 'history.html'), 'text/html');
    }

    if (pathname === '/speaking') {
        return sendFile(response, path.join(FRONTEND_DIR, 'speaking.html'), 'text/html');
    }

    if (pathname === '/writing') {
        return sendFile(response, path.join(FRONTEND_DIR, 'writing.html'), 'text/html');
    }

    if (pathname === '/reset-password') {
        return sendFile(response, path.join(FRONTEND_DIR, 'reset-password.html'), 'text/html');
    }

    if (pathname.startsWith('/static/')) {
        const relativeAssetPath = pathname.slice('/static/'.length);
        const assetPath = path.join(FRONTEND_DIR, relativeAssetPath);

        if (!assetPath.startsWith(FRONTEND_DIR)) {
            response.writeHead(403, { 'Content-Type': 'application/json; charset=utf-8' });
            response.end(JSON.stringify({ detail: 'Forbidden' }));
            return;
        }

        if (fs.existsSync(assetPath)) {
            const ext = path.extname(assetPath);
            const contentType = ext === '.css'
                ? 'text/css'
                : ext === '.js'
                    ? 'application/javascript'
                    : null;

            if (contentType) {
                return sendFile(response, assetPath, contentType);
            }
        }
    }

    if (pathname === '/api/auth/me') {
        response.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
        response.end(JSON.stringify({ username: 'playwright', email: null, email_verified: false }));
        return;
    }

    if (pathname === '/api/auth/email' && request.method === 'PUT') {
        response.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
        response.end(JSON.stringify({ username: 'playwright', email: 'bound@example.com', email_verified: false }));
        return;
    }

    if (pathname === '/api/auth/password-reset/request' && request.method === 'POST') {
        response.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
        response.end(JSON.stringify({ message: 'If the email exists, a reset link has been sent.' }));
        return;
    }

    if (pathname === '/api/auth/password-reset/validate' && request.method === 'POST') {
        response.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
        response.end(JSON.stringify({ valid: true }));
        return;
    }

    if (pathname === '/api/auth/password-reset/confirm' && request.method === 'POST') {
        response.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
        response.end(JSON.stringify({ message: 'Password has been reset successfully.' }));
        return;
    }

    if (pathname === '/api/dashboard/history') {
        response.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
        response.end('[]');
        return;
    }

    if (pathname === '/api/writing/prompts' && request.method === 'GET') {
        response.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
        response.end(JSON.stringify([
            { id: 1, slug: 'task1-bar-chart', task_type: 'task1', title: 'Bar Chart Description', prompt_text: 'The bar chart below shows...', prompt_details: null },
            { id: 2, slug: 'task1-pie-chart', task_type: 'task1', title: 'Pie Chart Description', prompt_text: 'The pie chart illustrates...', prompt_details: null },
            { id: 3, slug: 'task2-environment', task_type: 'task2', title: 'Environmental Protection', prompt_text: 'Some people believe that environmental problems should be solved on a global scale...', prompt_details: null },
            { id: 4, slug: 'task2-technology', task_type: 'task2', title: 'Technology in Education', prompt_text: 'Many people think that technology has made our lives easier...', prompt_details: null },
            { id: 5, slug: 'task2-remote-work', task_type: 'task2', title: 'Remote Work', prompt_text: 'Working from home has become increasingly common...', prompt_details: null }
        ]));
        return;
    }

    if (pathname.startsWith('/api/')) {
        response.writeHead(401, { 'Content-Type': 'application/json; charset=utf-8' });
        response.end(JSON.stringify({ detail: 'Unauthorized' }));
        return;
    }

    response.writeHead(404, { 'Content-Type': 'application/json; charset=utf-8' });
    response.end(JSON.stringify({ detail: 'Not found' }));
});

server.listen(PORT, '127.0.0.1', () => {
    console.log(`Static frontend server listening on http://127.0.0.1:${PORT}`);
});
