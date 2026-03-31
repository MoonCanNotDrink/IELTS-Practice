import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';

function loadScript(relativePath, exportNames = []) {
  const code = readFileSync(resolve(relativePath), 'utf-8');
  const exportBlock = exportNames.length
    ? `\nreturn { ${exportNames.map((name) => `${name}: typeof ${name} !== 'undefined' ? ${name} : undefined`).join(', ')} };`
    : '';
  const fn = new Function(`${code}${exportBlock}`);
  return fn.call(globalThis) || {};
}

beforeAll(() => {
  loadScript('frontend/shared.js');

  const appExports = loadScript('frontend/app.js', [
    'formatTimerValue',
    'formatDurationBadge',
    'formatSpeakingDuration',
    'renderTopicCard',
  ]);
  Object.assign(globalThis, appExports);
  Object.assign(window, appExports);

  const freePracticeExports = loadScript('frontend/free-practice.js', ['buildFreePracticeTopic']);
  Object.assign(globalThis, freePracticeExports);
  Object.assign(window, freePracticeExports);
});

beforeEach(() => {
  localStorage.clear();
  vi.restoreAllMocks();
  document.body.innerHTML = '<div class="header-controls"><button id="btnLogin"></button><button id="btnLogout"></button></div>';
  loadScript('frontend/shared.js');
});

describe('escapeText / escapeHtml (shared.js)', () => {
  it('escapes all five HTML entities', () => {
    expect(window.escapeHtml(`&<>"'`)).toBe('&amp;&lt;&gt;&quot;&#39;');
  });

  it('returns empty string for empty, null, and undefined', () => {
    expect(window.escapeHtml('')).toBe('');
    expect(window.escapeHtml(null)).toBe('');
    expect(window.escapeHtml(undefined)).toBe('');
  });

  it('handles numbers and strings without special characters', () => {
    expect(window.escapeHtml(12345)).toBe('12345');
    expect(window.escapeHtml('IELTS practice')).toBe('IELTS practice');
  });

  it('escapes mixed content and XSS-like input', () => {
    expect(window.escapeHtml('Tom & Jerry <Cartoon>')).toBe('Tom &amp; Jerry &lt;Cartoon&gt;');
    expect(window.escapeHtml('<script>alert(1)</script>')).toBe('&lt;script&gt;alert(1)&lt;/script&gt;');
  });
});

describe('getStoredThemeMode (shared.js)', () => {
  it('returns valid stored modes', () => {
    localStorage.setItem('ielts_theme_mode', 'light');
    expect(window.getStoredThemeMode()).toBe('light');

    localStorage.setItem('ielts_theme_mode', 'dark');
    expect(window.getStoredThemeMode()).toBe('dark');

    localStorage.setItem('ielts_theme_mode', 'system');
    expect(window.getStoredThemeMode()).toBe('system');
  });

  it('falls back to system for invalid or missing values', () => {
    localStorage.setItem('ielts_theme_mode', 'invalid');
    expect(window.getStoredThemeMode()).toBe('system');

    localStorage.setItem('ielts_theme_mode', '');
    expect(window.getStoredThemeMode()).toBe('system');

    localStorage.removeItem('ielts_theme_mode');
    expect(window.getStoredThemeMode()).toBe('system');
  });
});

describe('auth modal modes (shared.js)', () => {
  it('shows email and confirm password in register mode, forgot password in login mode', () => {
    window.setAuthMode('register');
    expect(document.getElementById('emailGroup').classList.contains('hidden')).toBe(false);
    expect(document.getElementById('confirmPasswordGroup').classList.contains('hidden')).toBe(false);
    expect(document.getElementById('forgotPasswordGroup').classList.contains('hidden')).toBe(true);

    window.setAuthMode('login');
    expect(document.getElementById('emailGroup').classList.contains('hidden')).toBe(true);
    expect(document.getElementById('confirmPasswordGroup').classList.contains('hidden')).toBe(true);
    expect(document.getElementById('forgotPasswordGroup').classList.contains('hidden')).toBe(false);
  });

  it('updates account button label based on whether profile has email', async () => {
    localStorage.setItem('ielts_token', 'token');
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ username: 'tester', email: null, email_verified: false }),
    });

    await window.loadAuthProfile();
    expect(document.getElementById('btnAccount').textContent).toBe('Bind Email');

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ username: 'tester', email: 'tester@example.com', email_verified: false }),
    });

    await window.loadAuthProfile();
    expect(document.getElementById('btnAccount').textContent).toBe('Account');
  });

  it('switches to password reset mode from the forgot password entry point', () => {
    window.showPasswordResetRequest();
    expect(document.getElementById('authTitle').textContent).toBe('Reset Password');
    expect(document.getElementById('emailGroup').classList.contains('hidden')).toBe(false);
    expect(document.getElementById('usernameGroup').classList.contains('hidden')).toBe(true);
    expect(document.getElementById('authModal').classList.contains('show')).toBe(true);
  });
});

describe('formatTimerValue (app.js)', () => {
  it('formats normal durations', () => {
    expect(window.formatTimerValue(0)).toBe('00:00');
    expect(window.formatTimerValue(59)).toBe('00:59');
    expect(window.formatTimerValue(60)).toBe('01:00');
    expect(window.formatTimerValue(125)).toBe('02:05');
    expect(window.formatTimerValue(3600)).toBe('60:00');
  });

  it('handles edge and invalid values', () => {
    expect(window.formatTimerValue(-5)).toBe('00:00');
    expect(window.formatTimerValue(NaN)).toBe('00:00');
    expect(window.formatTimerValue(null)).toBe('00:00');
    expect(window.formatTimerValue(undefined)).toBe('00:00');
    expect(window.formatTimerValue(30.7)).toBe('00:31');
  });
});

describe('formatDurationBadge (app.js)', () => {
  it('formats minute and second badges', () => {
    expect(window.formatDurationBadge(60)).toBe('1 Min');
    expect(window.formatDurationBadge(120)).toBe('2 Min');
    expect(window.formatDurationBadge(90)).toBe('90 Sec');
    expect(window.formatDurationBadge(45)).toBe('45 Sec');
  });

  it('uses default duration when input is falsy/invalid', () => {
    expect(window.formatDurationBadge(0)).toBe('2 Min');
    expect(window.formatDurationBadge(null)).toBe('2 Min');
    expect(window.formatDurationBadge(NaN)).toBe('2 Min');
  });
});

describe('formatSpeakingDuration (app.js)', () => {
  it('formats speaking durations with proper grammar', () => {
    expect(window.formatSpeakingDuration(60)).toBe('1 minute');
    expect(window.formatSpeakingDuration(120)).toBe('2 minutes');
    expect(window.formatSpeakingDuration(61)).toBe('1 minute 1 second');
    expect(window.formatSpeakingDuration(125)).toBe('2 minutes 5 seconds');
    expect(window.formatSpeakingDuration(30)).toBe('30 seconds');
    expect(window.formatSpeakingDuration(1)).toBe('1 second');
  });

  it('uses default duration when input is falsy/invalid', () => {
    expect(window.formatSpeakingDuration(0)).toBe('2 minutes');
    expect(window.formatSpeakingDuration(null)).toBe('2 minutes');
  });
});

describe('renderTopicCard (app.js)', () => {
  it('renders a full topic object', () => {
    const html = window.renderTopicCard({
      categoryLabel: 'People',
      title: 'Describe a person you admire',
      introLabel: 'You should say:',
      points: ['Who this person is', 'Why you admire them'],
    });

    expect(html).toContain('<div class="category-badge">People</div>');
    expect(html).toContain('<h3 class="topic-title">Describe a person you admire</h3>');
    expect(html).toContain('<li>Who this person is</li>');
    expect(html).toContain('<li>Why you admire them</li>');
  });

  it('handles missing fields, null topic, empty points, and missing category label', () => {
    const nullTopicHtml = window.renderTopicCard(null);
    expect(nullTopicHtml).toContain('<h3 class="topic-title"></h3>');
    expect(nullTopicHtml).toContain('You should say:');
    expect(nullTopicHtml).not.toContain('category-badge');

    const missingFieldsHtml = window.renderTopicCard({ title: 'Topic only' });
    expect(missingFieldsHtml).toContain('<h3 class="topic-title">Topic only</h3>');
    expect(missingFieldsHtml).toContain('You should say:');

    const emptyPointsHtml = window.renderTopicCard({ title: 'No points', points: [] });
    expect(emptyPointsHtml).toContain('<ul class="topic-points">');
    expect(emptyPointsHtml).not.toContain('<li>');
  });

  it('escapes XSS-like content in title and points', () => {
    const html = window.renderTopicCard({
      categoryLabel: '<img src=x onerror=alert(1)>',
      title: '<script>alert(1)</script>',
      introLabel: '<b>Intro</b>',
      points: ['<svg onload=alert(1)>', 'Safe & Sound'],
    });

    expect(html).toContain('&lt;script&gt;alert(1)&lt;/script&gt;');
    expect(html).toContain('&lt;img src=x onerror=alert(1)&gt;');
    expect(html).toContain('&lt;svg onload=alert(1)&gt;');
    expect(html).toContain('Safe &amp; Sound');
    expect(html).not.toContain('<script>');
    expect(html).not.toContain('<svg');
  });
});

describe('buildFreePracticeTopic (free-practice.js)', () => {
  it('builds the free practice topic object', () => {
    const topic = window.buildFreePracticeTopic('Talk about your hometown', 90);

    expect(topic).toEqual({
      title: 'Talk about your hometown',
      categoryLabel: 'Free Practice',
      introLabel: 'Use this prompt',
      points: [
        'Speak for 1 minute 30 seconds.',
        'Give reasons, examples, and a clear structure in your answer.',
      ],
    });
  });

  it('uses formatSpeakingDuration output in the first point', () => {
    const mock = vi.spyOn(window, 'formatSpeakingDuration').mockReturnValue('mocked duration');

    const topic = window.buildFreePracticeTopic('Prompt', 999);
    expect(mock).toHaveBeenCalledWith(999);
    expect(topic.points[0]).toBe('Speak for mocked duration.');
  });
});

describe('reset password page script', () => {
  it('shows the form when the reset token validates', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ valid: true }),
    });
    global.fetch = fetchMock;

    document.body.innerHTML = `
      <div id="resetPasswordIntro"></div>
      <div id="resetPasswordError" style="display:none"></div>
      <div id="resetPasswordStatus" style="display:none"></div>
      <form id="resetPasswordForm" class="hidden"></form>
    `;

    const originalLocation = window.location;
    delete window.location;
    window.location = new URL('http://localhost/reset-password?token=valid-token');

    loadScript('frontend/reset-password.js');
    document.dispatchEvent(new Event('DOMContentLoaded'));
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(fetchMock).toHaveBeenCalledWith('/api/auth/password-reset/validate', expect.any(Object));
    expect(document.getElementById('resetPasswordForm').classList.contains('hidden')).toBe(false);

    window.location = originalLocation;
  });
});
