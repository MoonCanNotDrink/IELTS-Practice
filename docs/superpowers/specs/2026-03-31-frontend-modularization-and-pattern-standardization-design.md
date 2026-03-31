# Frontend Refactor Design Spec for Issues #9 and #10

## Scope and goals

This spec covers two linked high-risk refactors in one plan:

- **Issue #9**: split `frontend/app.js` (currently 1208 lines) into feature modules.
- **Issue #10**: standardize shared frontend patterns across pages.

Hard constraints this design must satisfy:

1. No bundler.
2. No ES modules (`type="module"`).
3. Plain `<script>` loading only.
4. Existing `window.*` behavior and inline `onclick="..."` handlers must continue to work.
5. Refactor only (no intentional behavior changes).

## Project context discovered during exploration

### Actual frontend files and pages

JavaScript files:

- `frontend/app.js`
- `frontend/shared.js`
- `frontend/free-practice.js`
- `frontend/writing.js`
- `frontend/history.js`
- `frontend/reset-password.js`

HTML files:

- `frontend/index.html`
- `frontend/speaking.html`
- `frontend/writing.html`
- `frontend/history.html`
- `frontend/reset-password.html`

Note: there is no `login.html` and no `free-practice.html` in current HEAD; free-practice is embedded in `speaking.html`.

### Current script loading order (critical)

- `index.html`: `shared.js` -> `app.js`
- `speaking.html`: `shared.js` -> `app.js` -> `free-practice.js`
- `writing.html`: `shared.js` -> `app.js` -> `writing.js` (plus CDN Chart.js)
- `history.html`: `shared.js` -> `history.js` (plus CDN Chart.js)
- `reset-password.html`: `shared.js` -> `reset-password.js`

### Coupling map relevant to refactor risk

- `app.js` provides shared runtime globals consumed by other files:
  - `window.state`
  - `window.api`
  - `window.UI_TEXT`
  - `window.DEFAULT_PART2_SPEAKING_SECONDS`
  - plus many implicit globals via top-level function declarations (`setPhase`, `formatSpeakingDuration`, etc.)
- `free-practice.js` depends on:
  - `window.state`, `window.api`, `window.UI_TEXT`
  - `window.DEFAULT_PART2_SPEAKING_SECONDS`
  - `window.formatSpeakingDuration`
  - `window.setPhase`
- `writing.js` depends on `window.state`, `window.api`, and shared escaping helpers.
- All pages rely on shared auth/theme globals from `shared.js` (`showAuth`, `logout`, `initThemeMode`, `escapeHtml`, etc.).
- Inline handlers in HTML call many global function names directly; this is the most fragile surface in a script-only architecture.

## Natural boundaries in `app.js`

`app.js` already has section boundaries that can become module boundaries with minimal semantic change:

1. Config/constants and lightweight formatters
2. State container
3. API/auth transport with refresh
4. Navigation/home/session reset
5. Phase/visibility orchestration
6. Topic drawing and rendering
7. Part 1 flow
8. Part 2 flow
9. Part 3 flow
10. Shared recording/transcription/audio conversion
11. Shared timer
12. Examiner TTS
13. Scoring/result rendering
14. Home-page history preview
15. Initialization wiring

These boundaries align with current comments and keep behavior-preserving extraction feasible.

## Approaches considered

### Approach A (recommended): Script-layered global namespace with compatibility facade

Create multiple non-module JS files loaded in strict order. Each file writes to explicit namespaces (for example `window.IELTSApp.*`) and then a small compatibility file re-exports legacy global function names needed by inline handlers and existing scripts.

**Pros**

- Safest migration path under no-bundler/no-ESM constraints.
- Keeps old global function names alive during transition.
- Enables incremental extraction from `app.js` without a big-bang rewrite.
- Makes cross-module dependencies explicit by namespace.

**Cons**

- Global surface still exists (just organized).
- Requires careful script order management.
- Temporary duplication during compatibility phase.

### Approach B: Single-file IIFE module registry in one physical file

Keep one `app.js` file but internally split into named IIFE "modules" attached to a registry object.

**Pros**

- Lowest deployment risk (single asset, no script-order changes).
- No HTML script churn.

**Cons**

- Does not materially solve issue #9 objective (still one large file).
- Harder to own and review by feature.
- Less durable for future growth.

### Approach C: Event bus driven loose coupling between page scripts

Introduce a custom event bus (`document.dispatchEvent` + listeners) and move direct calls to event contracts.

**Pros**

- Strong decoupling and testability.
- Clearer async interaction model.

**Cons**

- Highest regression risk for this codebase now.
- Larger conceptual shift than required for refactor-only scope.
- Inline handlers still need global adapters, so complexity increases.

## Recommended approach

Choose **Approach A**.

Reason: it is the only option that meaningfully splits `app.js` while minimizing functional risk in a pure script-tag architecture with heavy inline-global usage.

## Detailed design

### 1) Target file/module layout

Create a new speaking runtime folder and move speaking-specific logic there:

- `frontend/speaking/core.js`
  - Owns root namespace init (`window.IELTSApp`), config constants, and primitive utils.
  - Defines canonical app object references used by all speaking modules.
- `frontend/speaking/state.js`
  - Creates and exports the single shared `state` object.
  - Re-exports `window.state` for backward compatibility.
- `frontend/speaking/api.js`
  - Owns `refreshAccessToken`, `api`.
  - Exports `window.api` for backward compatibility.
- `frontend/speaking/session.js`
  - `startMode`, `interruptPractice`, `backToHome`, `stopActiveCapture`.
- `frontend/speaking/phase-ui.js`
  - `setPhase`, `show`, phase-step rendering and section visibility.
- `frontend/speaking/topic.js`
  - `drawTopic`, `renderTopicCard`.
- `frontend/speaking/part1.js`
  - `loadPart1`, `renderPart1Question`, `toggleP1Recording`, `uploadAndNext`, `advanceQuestion` (part1 branch).
- `frontend/speaking/part2.js`
  - `startPrep`, `skipPrep`, `toggleP2Recording`, `uploadPart2`.
- `frontend/speaking/part3.js`
  - `loadPart3`, `renderPart3Question`, `toggleP3Recording`, `advanceQuestion` (part3 branch if shared helper remains).
- `frontend/speaking/recording.js`
  - `audioBlob2Wav`, `startRecording`, `stopRecording`, client transcription helpers.
- `frontend/speaking/timer.js`
  - `startTimer`, `clearTimer`, timer rendering helper.
- `frontend/speaking/tts.js`
  - `playExaminerAudio`, `stopExaminerAudio`, fallback speech.
- `frontend/speaking/scoring.js`
  - scoring triggers and score/transcript/feedback rendering.
- `frontend/speaking/history-preview.js`
  - homepage mini-history (`loadHistory`, `viewHistoryDetail`).
- `frontend/speaking/init.js`
  - consolidates DOMContentLoaded setup into one initializer.
- `frontend/speaking/compat.js`
  - explicit backward-compat export map of legacy globals required by HTML handlers and other scripts.

Compatibility staging note:

- Keep `frontend/app.js` as a thin compatibility loader/bridge during migration window, then optionally deprecate it later.
- During issue #9 completion, `app.js` may remain but should no longer contain the full implementation.

### 2) Canonical global namespace contract

Use a single root object:

- `window.IELTSApp = { speaking: { ... }, sharedRefs: { state, api, UI_TEXT, DEFAULT_PART2_SPEAKING_SECONDS } }`

Rules:

1. Cross-file calls in new speaking modules go through `window.IELTSApp.speaking.*`, not implicit globals.
2. `compat.js` is the only place that maps names to legacy `window.fnName` surface.
3. Legacy exports retained for compatibility:
   - Data/service: `window.state`, `window.api`, `window.UI_TEXT`, `window.DEFAULT_PART2_SPEAKING_SECONDS`
   - Handler functions referenced by HTML (`startMode`, `drawTopic`, `toggleP1Recording`, `startPrep`, etc.)
   - Utility functions used by other scripts (`formatSpeakingDuration`, `setPhase`)

This preserves behavior while reducing accidental global leakage.

### 3) Script loading order design

#### speaking.html (new order)

1. `shared.js`
2. `speaking/core.js`
3. `speaking/state.js`
4. `speaking/api.js`
5. `speaking/timer.js`
6. `speaking/recording.js`
7. `speaking/tts.js`
8. `speaking/phase-ui.js`
9. `speaking/topic.js`
10. `speaking/part1.js`
11. `speaking/part2.js`
12. `speaking/part3.js`
13. `speaking/scoring.js`
14. `speaking/history-preview.js`
15. `speaking/session.js`
16. `speaking/init.js`
17. `speaking/compat.js`
18. `free-practice.js`

Rationale:

- `free-practice.js` remains last because it consumes `state/api/UI_TEXT/setPhase/formatSpeakingDuration`.
- `compat.js` must run before any script that still expects legacy names.

#### writing.html

1. Chart.js CDN
2. `shared.js`
3. speaking shared-runtime subset (`core/state/api/session+minimal nav compatibility`) OR a dedicated lightweight `frontend/runtime/shared-runtime.js`
4. `writing.js`

This preserves writing’s current dependency on `window.state`, `window.api`, and `backToHome/interruptPractice` semantics.

#### index.html

1. `shared.js`
2. speaking shared-runtime subset (only what index needs: auth buttons initialization, optional mini-history support)

#### history.html

No required coupling to speaking runtime. Keep:

1. Chart.js CDN
2. `shared.js`
3. `history.js`

#### reset-password.html

No required coupling to speaking runtime. Keep:

1. `shared.js`
2. `reset-password.js`

### 4) State ownership design

The existing `state` object remains a single mutable object to avoid behavior changes.

Standardization rules:

1. `state.js` is the only module allowed to instantiate the object.
2. Other modules read/mutate it via imported namespace reference (`window.IELTSApp.sharedRefs.state`), not by recreating aliases arbitrarily.
3. Add sectioned shape comments in `state.js` (speaking core, recording, writing, free-practice) to make ownership explicit.
4. For issue #10, introduce helper reset functions grouped by concern:
   - `resetSpeakingTransientState()`
   - `resetRecordingState()`
   - `resetWritingTransientState()`

These helpers standardize reset patterns currently scattered in multiple files.

### 5) Cross-module dependency design

Dependency style for new speaking modules:

- **Allowed**: call through `window.IELTSApp.speaking.<module>.<fn>` or shared refs object.
- **Disallowed**: direct implicit reliance on declaration order side-effects from unrelated files.

Cycle prevention conventions:

1. Lower-level modules (timer, recording, api) do not call higher-level flow modules.
2. Flow modules (part1/2/3, scoring, topic) can call lower-level services.
3. `init.js` wires startup only, no business logic.
4. `compat.js` only exports names; no logic.

### 6) Shared pattern standardization plan (Issue #10)

Standardize these patterns across `shared.js`, speaking modules, `free-practice.js`, `writing.js`, and `history.js`:

1. **Page init pattern**
   - Replace scattered repeated DOMContentLoaded blocks with one canonical `runWhenDomReady(initFn)` helper in shared runtime.
   - Existing immediate/DOMContentLoaded dual checks become standardized wrapper usage.

2. **DOM helper pattern**
   - Canonical helpers: `byId`, `setHidden`, `setHtml`, `setText`.
   - Avoid ad-hoc null checks and repeated `document.getElementById` boilerplate.

3. **Async action button pattern**
   - Standard helper for `setLoading(button, text)` / `restoreButton(button, text, disabled)`.
   - Removes repeated manual `disabled + innerHTML` sequences.

4. **Error/status surface pattern**
   - Standard inline-message API for pages with local feedback boxes.
   - Reduce mixed usage of `alert`, inline div mutation, and silent catches.
   - Keep current user-visible wording unless bugfix required.

5. **Auth/API handling pattern**
   - One canonical authenticated request path (existing `api`) for speaking and writing scripts.
   - History/reset keep explicit fetch only where truly page-specific.

6. **Global export pattern**
   - Every file exports globals in one bottom `exports` block only.
   - No mixed mid-file `window.*` assignments.

7. **Naming conventions**
   - Verb-first handler names (`startX`, `toggleX`, `loadX`, `renderX`).
   - Consistent ids for section toggles and recording indicators.

8. **Safe HTML rendering pattern**
   - Keep `escapeHtml`/`escapeText` as canonical sanitizer and require explicit use before interpolation.

### 7) Backward compatibility matrix

Must remain unchanged for #9/#10 completion:

- All existing inline `onclick` names in HTML continue to resolve.
- `free-practice.js` and `writing.js` still find `window.state` and `window.api`.
- `window.formatSpeakingDuration` and `window.setPhase` remain callable.
- Existing page routes and static script URLs keep serving successfully.
- No UI flow or scoring behavior change by design intent.

### 8) Risk analysis and mitigations

Primary risks and controls:

1. **Script-order breakage**
   - Mitigation: explicit dependency order table in implementation plan and HTML updates performed with one source of truth.

2. **Missing legacy global export**
   - Mitigation: maintain compatibility checklist mapped from current inline handlers and cross-file usages.

3. **Subtle flow regressions from extraction**
   - Mitigation: move code section-by-section without logic edits; extract first, then rename only if needed.

4. **State reset regressions**
   - Mitigation: central reset helpers and compare pre/post behavior with high-value scenario tests.

### 9) Testing and verification strategy for implementation phase

Implementation should validate at three levels:

1. **Static contract checks**
   - Every expected global function still exists on `window`.
   - Script load order matches dependency plan.

2. **Behavior regression checks**
   - Speaking full mock flow, part2-only flow, free-practice flow.
   - Writing task flow and writing free-practice flow.
   - History page rendering and detail modal.
   - Reset-password page validation/submit flow.

3. **Build/test/lint checks**
   - Existing frontend unit/e2e suite and lint run cleanly.

No new features should be accepted during this refactor unless needed for compatibility.

## Incremental rollout recommendation

To reduce blast radius, implement in phases:

1. Extract low-risk shared services first (core/state/api/timer/recording/tts) while preserving current global names.
2. Extract flow modules (topic/part1/part2/part3/scoring/session/init).
3. Add and lock compatibility facade.
4. Standardize shared patterns (#10) with no behavior change.
5. Remove dead paths only after parity checks pass.

This sequencing keeps the app functional throughout refactor execution.

## Decision summary

- Use plain script files with explicit order.
- Introduce `window.IELTSApp` namespace as internal structure.
- Keep legacy `window.*` exports through `compat.js` to preserve inline handlers and existing dependent scripts.
- Standardize initialization, DOM access, async button state, export style, and state reset patterns across pages.
- Do not introduce bundlers, frameworks, or ES module loading.
