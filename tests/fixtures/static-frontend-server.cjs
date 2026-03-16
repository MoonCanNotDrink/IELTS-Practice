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

    if (pathname === '/static/index.css') {
        return sendFile(response, path.join(FRONTEND_DIR, 'index.css'), 'text/css');
    }

    if (pathname === '/static/app.js') {
        return sendFile(response, path.join(FRONTEND_DIR, 'app.js'), 'application/javascript');
    }

    if (pathname === '/api/scoring/history') {
        response.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
        response.end('[]');
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
