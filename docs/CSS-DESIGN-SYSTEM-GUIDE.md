# Modern CSS Design System Guide for Vanilla HTML/CSS/JS

> Production-ready patterns for polishing your IELTS practice app UI — no frameworks required.

This guide covers modern CSS architecture, theming, typography, micro-interactions, and responsive patterns that will transform your vanilla CSS into a polished, maintainable design system.

---

## Table of Contents

1. [Modern CSS Features to Leverage](#1-modern-css-features-to-leverage)
2. [CSS Custom Property Theming & Dark Mode](#2-css-custom-property-theming--dark-mode)
3. [Color Systems with OKLCH & color-mix()](#3-color-systems-with-oklch--color-mix)
4. [Typography: Modular Scales & Fluid Type](#4-typography-modular-scales--fluid-type)
5. [Card & Dashboard UI Patterns](#5-card--dashboard-ui-patterns)
6. [Micro-Interactions & Animations](#6-micro-interactions--animations)
7. [Responsive Design Without Frameworks](#7-responsive-design-without-frameworks)

---

## 1. Modern CSS Features to Leverage

These features have >90% browser support and eliminate JavaScript solutions that used to be necessary.

### Container Queries (@container)

Container queries let components respond to their *container's* size, not the viewport. This is the single biggest shift in responsive design — components own their responsive behavior.

```css
/* First, establish containment on the parent */
.card-container {
  container-type: inline-size;
}

/* Then query the container, not the viewport */
.card {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

/* Card adapts when its container is < 400px */
@container (max-width: 400px) {
  .card {
    grid-template-columns: 1fr;
  }
}
```

**IELTS App Use Case**: Your practice question cards can adapt whether they're in the main content area or a sidebar — no media queries needed.

```css
/* Example: Practice card that responds to its container */
.practice-card {
  display: flex;
  gap: 1rem;
  padding: 1.5rem;
}

@container (max-width: 320px) {
  .practice-card {
    flex-direction: column;
    padding: 1rem;
  }
  
  .practice-card__media {
    display: none; /* Hide thumbnail in tight spaces */
  }
}
```

### The :has() Selector

`:has()` gives you parent selection — styling a container based on its children's state. No more JavaScript toggle classes.

```css
/* Style the card differently when it has an image */
.card:has(.card__image) {
  grid-template-columns: 1fr 1fr;
}

/* Style card when it has a "completed" badge */
.card:has(.badge--completed) {
  border-color: var(--color-success);
}

/* Form validation states without JS */
.form-field:has(input:invalid) {
  border-color: var(--color-danger);
}

.form-field:has(input:focus-visible) {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-alpha);
}
```

**IELTS App Use Case**: Highlight practice sessions that are complete, style answer cards differently based on whether they have feedback attached.

### color-mix() Function

Create color variations without defining every shade manually.

```css
:root {
  --primary: #4f46e5;
  
  /* Generate lighter/darker variants */
  --primary-light: color-mix(in srgb, var(--primary), white 20%);
  --primary-dark: color-mix(in srgb, var(--primary), black 20%);
  --primary-subtle: color-mix(in srgb, var(--primary), white 90%);
}

/* Interactive hover states */
.button:hover {
  background: color-mix(in srgb, var(--primary), black 10%);
}

.button:active {
  background: color-mix(in srgb, var(--primary), black 20%);
}
```

### oklch() Color Space

Perceptually uniform colors — equal lightness *looks* equal. Essential for accessible color systems.

```css
:root {
  /* oklch(lightness chroma hue) - all in degrees for hue */
  --color-primary: oklch(65% 0.15 260);
  --color-success: oklch(70% 0.15 140);
  --color-warning: oklch(75% 0.15 45);
  --color-danger: oklch(60% 0.15 20);
  
  /* Neutrals with proper perceptual steps */
  --gray-50: oklch(98% 0.005 250);
  --gray-100: oklch(95% 0.01 250);
  --gray-200: oklch(90% 0.015 250);
  --gray-300: oklch(80% 0.02 250);
  --gray-400: oklch(70% 0.025 250);
  --gray-500: oklch(55% 0.03 250);
  --gray-600: oklch(45% 0.03 250);
  --gray-700: oklch(35% 0.03 250);
  --gray-800: oklch(25% 0.03 250);
  --gray-900: oklch(15% 0.02 250);
}
```

**Key Advantage**: When you generate palettes with oklch, a 10% change in lightness produces a *visually consistent* step — unlike HSL where some hues appear dramatically brighter at the same lightness.

### View Transitions

Native page transition API with zero JavaScript for simple cases.

```css
/* Enable view transitions globally */
@view-transition {
  navigation: auto;
}

/* Customize transition behavior */
::view-transition-old(root) {
  animation: fade-out 0.3s ease-out;
}

::view-transition-new(root) {
  animation: fade-in 0.3s ease-in;
}

/* Named transitions for specific elements */
.card {
  view-transition-name: practice-card;
}

.card:nth-child(1) {
  view-transition-name: practice-card-1;
}
```

**IELTS App Use Case**: Smooth transitions when navigating between Speaking, Writing, and History pages.

### Scroll-Driven Animations

Animate based on scroll position — no Intersection Observer needed.

```css
/* Reveal elements as they enter viewport */
@keyframes reveal {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.practice-card {
  animation: reveal linear both;
  animation-timeline: view();
  animation-range: entry 10% cover 30%;
}

/* Progress indicator tied to scroll */
.progress-bar {
  width: 0;
  animation: grow linear;
  animation-timeline: scroll();
}
```

---

## 2. CSS Custom Property Theming & Dark Mode

### Three-Tier Token Architecture

Separate your custom properties into three layers for maintainability:

```css
/* ============================================
   TIER 1: Primitive Tokens (raw values)
   ============================================ */
:root {
  /* Colors */
  --blue-500: oklch(65% 0.15 250);
  --blue-600: oklch(60% 0.15 250);
  --blue-700: oklch(55% 0.15 250);
  
  --slate-50: oklch(98% 0.008 240);
  --slate-100: oklch(95% 0.015 240);
  --slate-200: oklch(90% 0.02 240);
  --slate-500: oklch(55% 0.025 240);
  --slate-700: oklch(35% 0.025 240);
  --slate-900: oklch(15% 0.015 240);
  
  /* Spacing scale (multiples of 4) */
  --space-1: 0.25rem;   /* 4px */
  --space-2: 0.5rem;    /* 8px */
  --space-3: 0.75rem;   /* 12px */
  --space-4: 1rem;      /* 16px */
  --space-5: 1.25rem;   /* 20px */
  --space-6: 1.5rem;    /* 24px */
  --space-8: 2rem;      /* 32px */
  --space-10: 2.5rem;   /* 40px */
  --space-12: 3rem;     /* 48px */
  
  /* Typography */
  --font-sans: 'Inter', system-ui, -apple-system, sans-serif;
  --font-mono: 'JetBrains Mono', ui-monospace, monospace;
}

/* ============================================
   TIER 2: Semantic Tokens (meaning-based)
   ============================================ */
:root {
  /* Backgrounds */
  --bg-base: var(--slate-50);
  --bg-surface: white;
  --bg-elevated: white;
  
  /* Text */
  --text-primary: var(--slate-900);
  --text-secondary: var(--slate-500);
  --text-tertiary: var(--slate-400);
  
  /* Brand */
  --color-primary: var(--blue-600);
  --color-primary-hover: var(--blue-700);
  
  /* Borders */
  --border-default: var(--slate-200);
  --border-subtle: var(--slate-100);
}

/* ============================================
   TIER 3: Component Tokens (specific use)
   ============================================ */
:root {
  /* Card component */
  --card-bg: var(--bg-surface);
  --card-border: var(--border-default);
  --card-radius: 0.75rem;
  --card-padding: var(--space-5);
  --card-shadow: 0 1px 3px oklch(0% 0 0 / 0.1), 0 1px 2px oklch(0% 0 0 / 0.06);
  --card-shadow-hover: 0 10px 15px oklch(0% 0 0 / 0.1), 0 4px 6px oklch(0% 0 0 / 0.05);
  
  /* Button component */
  --button-radius: 0.5rem;
  --button-padding-y: 0.625rem;
  --button-padding-x: 1.25rem;
  --button-font-weight: 500;
}
```

### Dark Mode Implementation

The robust approach combines automatic OS preference with manual toggle:

```css
/* ============================================
   BASE (Light) THEME
   ============================================ */
:root {
  --bg-base: oklch(98% 0.01 240);
  --bg-surface: oklch(100% 0 0);
  --bg-elevated: oklch(100% 0 0);
  
  --text-primary: oklch(20% 0.02 240);
  --text-secondary: oklch(45% 0.02 240);
  --text-tertiary: oklch(65% 0.015 240);
  
  --border-default: oklch(85% 0.01 240);
  --border-subtle: oklch(92% 0.008 240);
  
  --color-primary: oklch(60% 0.15 260);
  --color-success: oklch(65% 0.15 150);
  --color-warning: oklch(70% 0.15 45);
  --color-danger: oklch(58% 0.15 20);
  
  --card-shadow: 0 1px 3px oklch(0% 0 0 / 0.08), 0 1px 2px oklch(0% 0 0 / 0.04);
  --card-shadow-hover: 0 10px 15px oklch(0% 0 0 / 0.1), 0 4px 6px oklch(0% 0 0 / 0.05);
  
  --focus-ring: oklch(60% 0.15 260 / 0.3);
}

/* ============================================
   DARK THEME OVERRIDE
   ============================================ */
[data-theme="dark"],
:root.dark {
  --bg-base: oklch(15% 0.015 240);
  --bg-surface: oklch(18% 0.015 240);
  --bg-elevated: oklch(22% 0.015 240);
  
  --text-primary: oklch(92% 0.01 240);
  --text-secondary: oklch(70% 0.015 240);
  --text-tertiary: oklch(55% 0.015 240);
  
  --border-default: oklch(30% 0.015 240);
  --border-subtle: oklch(25% 0.012 240);
  
  --color-primary: oklch(70% 0.15 260);
  --color-success: oklch(75% 0.15 150);
  --color-warning: oklch(75% 0.15 45);
  --color-danger: oklch(65% 0.15 20);
  
  --card-shadow: 0 1px 3px oklch(0% 0 0 / 0.3), 0 1px 2px oklch(0% 0 0 / 0.2);
  --card-shadow-hover: 0 10px 15px oklch(0% 0 0 / 0.35), 0 4px 6px oklch(0% 0 0 / 0.2);
  
  --focus-ring: oklch(70% 0.15 260 / 0.3);
}
```

### Automatic OS Preference

```css
/* If user hasn't set manual preference, respect system */
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    /* Dark theme values */
  }
}
```

### JavaScript Toggle

```javascript
// Theme toggle implementation
function setTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem('theme', theme);
}

// Initialize on page load
const saved = localStorage.getItem('theme');
const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

if (saved) {
  setTheme(saved);
} else if (prefersDark) {
  setTheme('dark');
}
```

---

## 3. Color Systems with OKLCH & color-mix

### Building a Complete Palette

```css
:root {
  /* Primary Brand */
  --primary-50: oklch(97% 0.02 260);
  --primary-100: oklch(92% 0.04 260);
  --primary-200: oklch(85% 0.06 260);
  --primary-300: oklch(75% 0.1 260);
  --primary-400: oklch(70% 0.15 260);
  --primary-500: oklch(60% 0.18 260);  /* Main brand color */
  --primary-600: oklch(55% 0.16 260);
  --primary-700: oklch(48% 0.14 260);
  --primary-800: oklch(40% 0.12 260);
  --primary-900: oklch(30% 0.1 260);
  
  /* Semantic Colors */
  --success: oklch(65% 0.15 150);
  --warning: oklch(72% 0.15 45);
  --danger: oklch(58% 0.15 20);
  --info: oklch(65% 0.15 200);
  
  /* Alpha utilities - use color-mix for backgrounds */
  --primary-alpha-10: oklch(60% 0.18 260 / 0.1);
  --primary-alpha-20: oklch(60% 0.18 260 / 0.2);
  --surface-alpha: oklch(100% 0 0 / 0.8);
}
```

### Interactive State Colors

```css
/* Hover states - darken slightly */
.button:hover {
  background: var(--primary-600);
}

.button:focus-visible {
  outline: none;
  box-shadow: 0 0 0 3px var(--primary-alpha-20);
}

/* Active/pressed states */
.button:active {
  transform: scale(0.98);
}

/* Disabled states */
.button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
```

---

## 4. Typography: Modular Scales & Fluid Type

### Choosing a Modular Scale

| Scale | Ratio | Use Case |
|-------|-------|----------|
| Minor Third | 1.2 | Dense dashboards, lots of content |
| Major Third | 1.25 | General purpose |
| Perfect Fourth | 1.333 | Editorial, readable |
| Perfect Fifth | 1.5 | Impact, landing pages |
| Golden Ratio | 1.618 | Expressive, artistic |

For an IELTS practice app, **Major Third (1.25)** or **Perfect Fourth (1.333)** works well — readable but with clear hierarchy.

### Fluid Typography with clamp()

```css
:root {
  /* Base size */
  --font-base: 1rem;         /* 16px */
  --font-base-lg: 1.125rem;  /* 18px */
  
  /* Fluid type scale - clamp(min, preferred, max) */
  --text-xs: clamp(0.75rem, 0.7rem + 0.25vw, 0.8rem);
  --text-sm: clamp(0.875rem, 0.8rem + 0.25vw, 0.9375rem);
  --text-base: clamp(1rem, 0.9rem + 0.5vw, 1.125rem);
  --text-lg: clamp(1.125rem, 1rem + 0.5vw, 1.375rem);
  --text-xl: clamp(1.25rem, 1rem + 1vw, 1.75rem);
  --text-2xl: clamp(1.5rem, 1.2rem + 1.5vw, 2.25rem);
  --text-3xl: clamp(1.875rem, 1.5rem + 2vw, 3rem);
  --text-4xl: clamp(2.25rem, 1.8rem + 2.5vw, 3.75rem);
  
  /* Line heights */
  --leading-tight: 1.25;
  --leading-normal: 1.5;
  --leading-relaxed: 1.625;
  
  /* Letter spacing */
  --tracking-tight: -0.025em;
  --tracking-normal: 0;
  --tracking-wide: 0.025em;
}
```

### Typography System Usage

```css
/* Base typography */
body {
  font-family: var(--font-sans);
  font-size: var(--text-base);
  line-height: var(--leading-normal);
  color: var(--text-primary);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* Headings */
h1 { font-size: var(--text-4xl); font-weight: 700; line-height: var(--leading-tight); }
h2 { font-size: var(--text-3xl); font-weight: 600; line-height: var(--leading-tight); }
h3 { font-size: var(--text-2xl); font-weight: 600; line-height: var(--leading-tight); }
h4 { font-size: var(--text-xl); font-weight: 600; line-height: var(--leading-normal); }

/* Body text */
p { font-size: var(--text-base); line-height: var(--leading-relaxed); margin-bottom: var(--space-4); }

/* Small text */
small, .text-sm { font-size: var(--text-sm); }
.caption { font-size: var(--text-xs); color: var(--text-secondary); }
```

### Variable Fonts for Performance

```css
@font-face {
  font-family: 'Inter';
  src: url('/fonts/Inter-Variable.woff2') format('woff2-variations');
  font-weight: 100 900;  /* Range for variable font */
  font-display: swap;
}

body {
  font-family: 'Inter', system-ui, sans-serif;
  font-variation-settings: 'opsz' 32, 'wght' 400;
}

h1, h2, h3, h4 {
  font-variation-settings: 'wght' 600;
}
```

---

## 5. Card & Dashboard UI Patterns

### Base Card Component

```css
.card {
  background: var(--card-bg);
  border: 1px solid var(--card-border);
  border-radius: var(--card-radius);
  padding: var(--card-padding);
  box-shadow: var(--card-shadow);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

/* Hover state - lift effect */
.card:hover {
  transform: translateY(-2px);
  box-shadow: var(--card-shadow-hover);
}

/* Interactive card */
.card--interactive {
  cursor: pointer;
}

.card--interactive:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}
```

### Dashboard Stat Card

```css
.stat-card {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-5);
}

.stat-card__label {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  font-weight: 500;
}

.stat-card__value {
  font-size: var(--text-2xl);
  font-weight: 700;
  color: var(--text-primary);
}

.stat-card__trend {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--text-sm);
  font-weight: 500;
}

.stat-card__trend--up {
  color: var(--color-success);
}

.stat-card__trend--down {
  color: var(--color-danger);
}
```

### Practice Session Card

```css
.session-card {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-4);
  background: var(--card-bg);
  border: 1px solid var(--border-default);
  border-radius: var(--card-radius);
}

.session-card__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border-radius: var(--space-2);
  background: var(--primary-alpha-10);
  color: var(--color-primary);
  flex-shrink: 0;
}

.session-card__content {
  flex: 1;
  min-width: 0;
}

.session-card__title {
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: var(--space-1);
}

.session-card__meta {
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

/* Completed state */
.session-card--completed {
  border-color: var(--color-success);
}

.session-card--completed .session-card__icon {
  background: oklch(65% 0.15 150 / 0.15);
  color: var(--color-success);
}

/* Responsive - stack on small containers */
@container (max-width: 280px) {
  .session-card {
    flex-direction: column;
    text-align: center;
  }
}
```

### Grid Layout for Dashboard

```css
.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--space-4);
}

/* For stat cards - smaller */
.dashboard-grid--stats {
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
}

/* For history items - list style */
.dashboard-grid--list {
  grid-template-columns: 1fr;
}
```

---

## 6. Micro-Interactions & Animations

### Button States

```css
/* Base button */
.button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: var(--button-padding-y) var(--button-padding-x);
  font-size: var(--text-sm);
  font-weight: var(--button-font-weight);
  border-radius: var(--button-radius);
  border: 1px solid transparent;
  background: var(--color-primary);
  color: white;
  cursor: pointer;
  transition: all 0.15s ease;
}

.button:hover {
  background: var(--primary-700);
  transform: translateY(-1px);
}

.button:active {
  transform: translateY(0) scale(0.98);
}

.button:focus-visible {
  outline: none;
  box-shadow: 0 0 0 3px var(--focus-ring);
}

/* Variants */
.button--secondary {
  background: var(--bg-surface);
  color: var(--text-primary);
  border-color: var(--border-default);
}

.button--secondary:hover {
  background: var(--bg-elevated);
  border-color: var(--border-subtle);
}

.button--ghost {
  background: transparent;
  color: var(--text-secondary);
}

.button--ghost:hover {
  background: var(--border-subtle);
  color: var(--text-primary);
}
```

### Card Hover Effects

```css
/* Subtle lift */
.card:hover {
  transform: translateY(-4px);
  box-shadow: var(--card-shadow-hover);
}

/* Border highlight on hover */
.card--interactive:hover {
  border-color: var(--color-primary);
}

/* With :has() for state-based styling */
.card:has(.badge--completed) {
  background: oklch(65% 0.15 150 / 0.05);
}

.card:has(.badge--completed):hover {
  background: oklch(65% 0.15 150 / 0.1);
}
```

### Loading States

```css
/* Skeleton loader - pulsing effect */
.skeleton {
  background: linear-gradient(
    90deg,
    var(--border-subtle) 25%,
    var(--bg-surface) 50%,
    var(--border-subtle) 75%
  );
  background-size: 200% 100%;
  animation: skeleton-pulse 1.5s ease-in-out infinite;
  border-radius: var(--space-1);
}

@keyframes skeleton-pulse {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* Spinner */
.spinner {
  width: 20px;
  height: 20px;
  border: 2px solid var(--border-default);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spinner-rotate 0.8s linear infinite;
}

@keyframes spinner-rotate {
  to { transform: rotate(360deg); }
}
```

### Focus Rings for Accessibility

```css
/* Consistent focus styling */
*:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

/* Make focus more prominent for interactive elements */
a:focus-visible,
button:focus-visible,
[tabindex]:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 3px;
  box-shadow: 0 0 0 5px var(--focus-ring);
}
```

### Page Transitions

```css
/* Fade in on page load */
@keyframes fade-in {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

main {
  animation: fade-in 0.3s ease-out;
}

/* Stagger children */
main > * {
  animation: fade-in 0.3s ease-out both;
}

main > *:nth-child(1) { animation-delay: 0ms; }
main > *:nth-child(2) { animation-delay: 50ms; }
main > *:nth-child(3) { animation-delay: 100ms; }
main > *:nth-child(4) { animation-delay: 150ms; }
```

### Reduced Motion Support

```css
/* Respect user preferences */
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

## 7. Responsive Design Without Frameworks

### Container Queries as Primary Responsive Tool

```css
/* Instead of media queries, use container queries */

.page-section {
  container-type: inline-size;
}

.section-title {
  font-size: var(--text-2xl);
}

@container (max-width: 480px) {
  .section-title {
    font-size: var(--text-xl);
  }
}
```

### Fluid Spacing with min()/max()/clamp()

```css
/* Fluid padding that scales with viewport */
.container {
  padding: clamp(1rem, 5vw, 3rem);
}

/* Use container query units for component-relative sizing */
.card-media {
  height: 200px;
  width: 30cqi;  /* 30% of container's inline size */
}

/* Prevent elements from getting too wide */
.content-wrapper {
  max-width: min(65ch, 100%);
}

/* Use max() for flexible minimums */
.sidebar {
  width: max(250px, 30vw);
}
```

### Grid for Layout

```css
/* Responsive grid - auto-fill is your friend */
.grid-auto {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(300px, 100%), 1fr));
  gap: var(--space-4);
}

/* Specific column counts */
.grid-2 { grid-template-columns: repeat(2, 1fr); }
.grid-3 { grid-template-columns: repeat(3, 1fr); }
.grid-4 { grid-template-columns: repeat(4, 1fr); }

/* Mobile fallback */
@media (max-width: 640px) {
  .grid-2, .grid-3, .grid-4 {
    grid-template-columns: 1fr;
  }
}
```

### CSS Logical Properties

Use logical properties instead of physical (left/right/top/bottom) for internationalization and vertical writing modes:

```css
/* Instead of margin-left, use margin-inline-start */
.card {
  margin-block-end: var(--space-4);
  padding-inline: var(--space-4);
}

/* Instead of width/height, use inline-size/block-size */
.avatar {
  inline-size: 40px;
  block-size: 40px;
}

/* Border shorthand */
.card {
  border-block: 1px solid var(--border-default);
  border-inline: 1px solid var(--border-default);
}
```

---

## Putting It All Together

### File Organization

```
/css
  /tokens          # Design tokens (colors, spacing, typography)
    colors.css
    spacing.css
    typography.css
  /components      # Component styles
    button.css
    card.css
    input.css
    skeleton.css
  /layout          # Layout utilities
    container.css
    grid.css
  /themes          # Theme variants
    light.css
    dark.css
  /utilities       # Utilities
    focus.css
    animation.css
  styles.css       # Main entry point
```

### Main Stylesheet Structure

```css
/* styles.css */

/* 1. Reset & base */
@import './reset.css';

/* 2. Design tokens */
@import './tokens/colors.css';
@import './tokens/spacing.css';
@import './tokens/typography.css';

/* 3. Themes */
@import './themes/light.css';
@import './themes/dark.css';

/* 4. Components */
@import './components/button.css';
@import './components/card.css';
@import './components/input.css';

/* 5. Layout */
@import './layout/container.css';
@import './layout/grid.css';

/* 6. Utilities */
@import './utilities/focus.css';
@import './utilities/animation.css';
```

---

## Quick Reference: Recommended Token Values

### Spacing Scale (multiples of 4)

```css
--space-1: 0.25rem;   /* 4px */
--space-2: 0.5rem;    /* 8px */
--space-3: 0.75rem;   /* 12px */
--space-4: 1rem;      /* 16px */
--space-5: 1.25rem;   /* 20px */
--space-6: 1.5rem;    /* 24px */
--space-8: 2rem;      /* 32px */
--space-10: 2.5rem;   /* 40px */
--space-12: 3rem;     /* 48px */
--space-16: 4rem;     /* 64px */
--space-20: 5rem;     /* 80px */
```

### Border Radius Scale

```css
--radius-sm: 0.25rem;   /* 4px */
--radius-md: 0.5rem;    /* 8px */
--radius-lg: 0.75rem;   /* 12px */
--radius-xl: 1rem;      /* 16px */
--radius-2xl: 1.5rem;   /* 24px */
--radius-full: 9999px;
```

### Typography Scale (Major Third 1.25)

```css
--text-xs: 0.8rem;
--text-sm: 0.875rem;
--text-base: 1rem;
--text-lg: 1.125rem;
--text-xl: 1.25rem;
--text-2xl: 1.5625rem;
--text-3xl: 1.953125rem;
--text-4xl: 2.44140625rem;
```

---

## Browser Support Notes

All features listed have >90% global support as of 2026:

| Feature | Support | Notes |
|---------|---------|-------|
| Container Queries | 93%+ | Firefox 110+ |
| :has() Selector | 93%+ | Firefox 121+ |
| color-mix() | 92%+ | Firefox 113+ |
| oklch() | 93%+ | Firefox 113+ |
| clamp() | 96% | Universal |
| @layer | 95%+ | Universal |
| view-transition | 90%+ | Chrome/Edge, Safari 18+ |
| scroll-driven anim | 90%+ | Chrome/Edge only currently |

For older browsers, use progressive enhancement — the layout still works without these features.

---

## Resources for Further Learning

- **Typography tools**: [Utopia Type Scale](https://utopia.fyi/type/calculator/), [Fluid Type Scale](https://www.fluidtypescale.com/)
- **Color tools**: [OKLCH Color Picker](https://oklch.com/), [ColorScale](https://colorscale.calcolor.us/)
- **Layout tools**: [CSS Grid Generator](https://cssgrid-generator.netlify.app/), [Layoutit](https://grid.layoutit.com/)
- **Container queries**: [MDN Container Queries](https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_container_queries)

---

*This guide gives you production-ready patterns. Apply them incrementally — start with the token system and dark mode, then add container queries and fluid typography for your next level of polish.*