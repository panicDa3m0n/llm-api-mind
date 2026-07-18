# Activity Log

This file preserves project continuity across IDE-agent sessions.

Use it to record meaningful work, verification, open questions, and the next suggested step. Do not log every tiny edit, but do log changes that affect direction, architecture, APIs, experiments, prompts, or debugging knowledge.

## 2026-07-18 - V1.40.0 Longitudinal Cognitive Organ Validation (SCA-4)

Goal:

Evaluate focus, volition, computational affect, and metacognition through
correlated natural turns and independent controls before changing defaults or
coupling organs.

Changes:

- Added a dedicated 13-scenario, two-repetition SCA-4 catalog over the frozen
  preliminary database and made group runtime variants executable and
  auditable through requested/effective configuration receipts.
- Added structured shell-call and organ-trace extraction so technical state,
  cognitive choice, answer quality, and longitudinal effect can be reviewed
  separately.
- Corrected explicit obstruction recovery so a resolved block transitions
  prior frustration to relief instead of re-triggering frustration from the
  word `blocco`.
- Required verified volition persistence before durable self-direction claims
  and a real metacognitive step before broad all-organ/default-readiness
  judgments in both native and GPT prompts.

Evidence:

- 26 accepted current MiniMax M3 turns on independent disposable copies;
  deterministic execution passed 24/26.
- Focus lifecycle and negative controls passed 6/6.
- Volition passed one complete cross-session chain and both ownership
  controls; one other chain stopped at a public work note before mutation,
  confirming the separate SCA-28 boundary.
- Affect passed 10/10 post-fix model, shadow, and neutral turns, but model mode
  did not yet show a clear answer-quality advantage over shadow.
- Metacognition passed both broad-claim positives and both direct-answer
  negatives; one positive run remained unnecessarily expensive.

Decision:

Keep focus bounded, volition on-demand and outside automatic chat injection,
affect shadow by default, metacognition on-demand with lesson context shadow,
and all cross-organ coupling out of V1.40. SCA-28 is the next issue because a
progress-note-only final can still interrupt an otherwise correct organ action.

Evidence report:

- `docs/evaluations/v1.40-cognitive-organ-longitudinal.md`
- ADR-0092, EXP-0068, BUG-0082, BUG-0085, Linear SCA-4

## 2026-07-18 - V1.39.0 Active Recursive History Compaction (SCA-32)

Goal:

Promote the accepted V1.36 token partition from measurement to guarded native
routing without mutating canonical chronology.

Changes:

- Added append-only `history_compactions` with generation, prior-artifact,
  source digest, covered turns/sources, model, and token metadata.
- Added immediate idempotent maintenance generation using the previous summary
  plus only newly compactable complete turns.
- Added shared sync/stream routing for compacted system chronology, exact tail,
  and current user message; request traces retain canonical and derived inputs.
- Preserved canonical provider history on every completion and added explicit
  canonical fallback for missing, invalid, or unmappable artifacts.
- Added deterministic source manifests and removed provider-generated opaque
  IDs absent from source input.
- Corrected scheduling to measure the active next-turn view instead of
  retriggering from ever-growing canonical history.
- Corrected observed accounting so active requests are no longer labelled as
  shadow-only in post-call traces.

Verification:

- Ruff passed on the changed backend/test surface.
- Full backend suite passed 216 tests at 80.69% coverage.
- A copied 350,187-token laboratory session generated two real recursive
  MiniMax artifacts; generation 2 covered five turns and left zero unresolved
  unverified IDs.
- Direct Scarlet turn `turn_83ecd11869c44a42a7b6cdcab111c448`
  recalled the earlier endpoint-to-CLI framing from the compacted prefix while
  routing 21 canonical messages as 3 model-facing messages.
- Canonical history prefix stayed exact, and a 27,701-token active estimate did
  not schedule another job despite 352,887 canonical tokens.

Separate Finding:

A deliberately restricted 2,048-token probe exhausted output in private
thinking and failed under the existing answer-completion boundary. This belongs
to SCA-28/output-budget behavior, not history compaction.

Evidence:

- `docs/evaluations/v1.39-active-history-compaction.md`
- ADR-0091, EXP-0067, BUG-0086, BUG-0087, Linear SCA-32

Production Closure:

- Merged PR #9 at `cb400d2` and published annotated tag `v1.39.0` at that
  exact deployed runtime commit.
- Created online backup
  `/var/backups/scarlet-mobile-test/v1390-20260718T124832Z/app.db.pre-v1390`
  (SHA-256 `f8ecc8f173083b64d5288e2b0f912ba4ac4674e2063fd422a8559bd306960e86`),
  plus pre-release code, environment, compose, and frontend archives.
- New-image read-only production preflight reported integrity `ok`, 28 tables,
  227 sessions, 889 messages, direct isolation, and active 400k/100k/100k/25k
  compaction configuration before restart.
- Post-restart OpenAPI reported `1.39.0`; schema initialization added only
  `history_compactions` (29 tables total), DB integrity remained `ok`, mode was
  `active`, and logs contained no application error.
- Remote and local frontend `index.html` hashes matched at
  `fcbfe5210203f294a244ef6cc0feb11c80145fb09c0903ed6a11c9a5d2287391`.
- Natural online turn `turn_1c6064a1daca4e31a95551511ff243d1`
  completed. Its new-session route explicitly used
  `canonical_fallback_artifact_missing`; request counts were 1 canonical and 1
  model-facing, while observed accounting reported `mode=active` and
  `shadow_only=false`.

## 2026-07-18 - V1.38.0 Historical Provenance Audit And Guarded Cleanup (SCA-20)

Goal:

Classify historical memory provenance from direct evidence, isolate explicit
test contamination, and replace the mixed audit/apply route with a protected
maintenance workflow.

Changes:

- Added an orthogonal read-only provenance/disposition audit with published
  criteria and candidate-set digests.
- Added dedicated exact-source repair and explicit-fixture deprecation routes
  guarded by dry-run, backup reference, digest, and approval token.
- Kept exact duplicates review-only and excluded semantic similarity from all
  mutation decisions.
- Kept maintenance lifecycle activity outside recent memory and stopped
  historical lifecycle operations from touching source-session recency.

Evidence So Far:

- Production read-only baseline: 307 memories, including 241 active explicit
  Codex fixtures, one already inactive fixture, and seven inconsistent or
  non-user real source links retained for review.
- Focused tests: 13 passed. Full backend: 209 passed at 80.45% coverage. New
  module coverage: 94%. Ruff passed.
- Historical ignored DB read-only control: 34 exact repairs, 241 active fixture
  candidates, and unchanged source hash.
- Disposable production-copy gate: 241 fixture memories, 201 facts, and 1,406
  surfaces deprecated; zero recent-eligible maintenance activities, zero active
  candidate overlap, unchanged seed-session timestamps, SQLite integrity `ok`.
- Final local gates: 209 backend tests at 80.45%, focused 13/13, preliminary
  regression 9/9, Ruff, blocking mypy, documentation integrity, and frontend
  production build all passed.

Production Closure:

- Merged PR #7 at `efe652e`, created the verified online backup
  `/var/backups/scarlet-mobile-test/v1380-20260718T112717Z/app.db.pre-v1380`
  (SHA-256 `367a8bbf4783d0a738fe90e42c721de3a926999545a6fa22e8add57a31bd77b7`),
  and deployed V1.38.0 after read-only production preflight.
- Applied the reviewed digest under the guarded route: all 242 explicit
  fixtures are inactive, 241 maintenance activities were appended with zero
  recent eligibility, and seed-session timestamps stayed unchanged.
- Verified zero active fixture overlap and SQLite integrity `ok` independently
  against both live and backup databases.
- Corrected stale VPS retrieval configuration to the V1.37 adaptive floor and
  Nvidia OpenRouter embedding/rerank models. A post-fix bridge control completed
  both stages, returned zero ginger-infusion memories, and finalized normally.
- Rebuilt and deployed frontend V1.38.0 to `/var/www/scarlet`; local and remote
  `index.html` SHA-256 agree and the protected `/scarlet/` route returns the
  expected authentication challenge.
- Classified two unrelated live findings without expanding this issue: a
  progress-note-only completed turn belongs to SCA-28, and an irrelevant
  near-floor retrieval belongs to SCA-3 follow-up calibration.

Boundary:

- `backend/data/app.db` remains unrelated and unstaged.
- Production mutation occurred only through the approved guarded operation
  after disposable-copy proof and fresh backup.
- The seven uncertain real source links were not rewritten. SCA-20 is ready to
  close; retrieval calibration and final-answer obligations remain separate.

## 2026-07-18 - V1.37.0 Final Memory Rerank Calibration (SCA-3)

Goal:

Calibrate candidate coverage and final semantic acceptance on immutable real
memory references, then verify V2 delivery and direct Scarlet behavior.

Changes:

- Added a reusable ten-case frozen calibration runner plus one inherited
  wrong-entity regression, with per-case fresh DB copies, source hash/reference
  guards, trace/V2 checks, latency capture, and a separate real-Scarlet mode.
- Replaced the fixed `0.01` floor with an absolute `0.004` floor plus a `1%`
  query-relative floor; the final reranker remains the only relevance arbiter.
- Added effective-threshold and final-reranker latency evidence.
- Advanced package and canonical documentation metadata to V1.37.0.

Verification:

- Pre-change frozen result: 18/20; both failures were the same two-fact
  Vetro-Luna false negative, while every expected id reached the candidate pool.
- Final post-change frozen result: 22/22; positive floor `0.007432`, negative
  ceiling `0.003299`, median rerank 396.5 ms, source hash unchanged.
- Direct MiniMax M3 result: 3/3 technical and semantic passes for mint-tea
  paraphrase, body disambiguation, and unrelated jazz negative.
- Full backend gate: 207 tests passed at 80.21% coverage.
- Unchanged frozen preliminary regression: 9/9.
- Ruff, blocking mypy, documentation integrity, and frontend production build
  passed.

Boundary:

- No production or local laboratory database was used as a writable target.
- `backend/data/app.db` remains an unrelated modified local file.
- Background maintenance retry/resume and historical provenance remain SCA-20
  or later work, not silently included in SCA-3.

## 2026-07-18 - V1.36.1 Thinking-Only Final Recovery (SCA-19)

Goal:

Prevent private provider thinking without public text or a tool call from being
accepted as a completed Scarlet turn.

Changes:

- Added one configurable continuation for thinking-only `end_turn` responses
  in the Anthropic-compatible tool-chat loop.
- Added explicit `LLMIncompleteResponseError` exhaustion and sync/stream
  `llm.incomplete_response` failed-turn handling.
- Kept incomplete attempts in recovery evidence while excluding them from
  canonical provider history and all cognitive-state derivation.
- Added recovery metadata to assistant/trace/event surfaces and the dedicated
  `llm.completion.recovery.started` runtime event.
- Advanced package and canonical documentation metadata to V1.36.1.

Verification:

- Initial fixtures reproduced the systemic defect: thinking-only results were
  emitted as `final_result`, HTTP 200, and `turn_complete`.
- Provider and chat regression slice: 30 tests passed after the fix.
- Direct isolated MiniMax M3 control used the normal `131072` output budget and
  completed with a public answer, no recovery, no tool call, and no memory
  mutation.
- Full backend suite: 198 tests passed at 80.22% coverage. Ruff, blocking mypy,
  documentation integrity, frontend production build, and the staged database
  boundary also passed.

Boundary:

- This changes acceptance and bounded recovery of invalid final output, not
  provider thinking style, memory policy, compaction, or generic retries.
- `backend/data/app.db` remains an unrelated modified local file and was not
  used by the live control.

## 2026-07-14 - V1.36.0 Chronology Accounting And Shadow Calibration (SCA-5)

Goal:

Replace fixed-turn chronological planning with measured token areas, preserve
exact source provenance, and evaluate full versus derived continuity without
activating compaction.

Changes:

- Added exact provider-history source maps for complete turns, messages, tool
  calls, and request/response traces.
- Added the `O + C + H + A + M <= 500k` shadow planner with token-based recent
  turn selection, whole-turn 1M exception, and fail-closed physical-window rule.
- Upgraded accounting to v2 with separate policy/V2/history/current/shell
  channels and effective per-step cache-aware provider input.
- Added a repeatable bounded calibration runner and focused deterministic tests.

Evidence:

- Three read-only real sessions measured about 56k, 163k, and 350k provider
  history tokens; normal `H=100k` retained 8, 2, and 1 complete turns.
- Six approved MiniMax calls compared full/derived continuity on two sessions.
  The 163k derived case reduced input by about 48% and latency by about 47%
  while preserving the principal evidence. The 350k case confirmed the
  single-turn exception; its full variant produced no public text at
  `max_tokens`, so that quality comparison remains inconclusive.
- Focused verification: 12 accounting/compaction tests, Ruff, and mypy passed;
  the complete backend suite passed 192 tests at 80% coverage.

Boundary:

- `backend/data/app.db` was read only and remains an unrelated modified local
  file outside this change.
- No VPS, production DB, canonical provider history, prompt, or active model
  input was changed.
- Active compaction remains gated on recursive summary persistence,
  multi-cycle evaluation, and explicit owner approval.

## 2026-07-14 - V1.35.0 Preserved Context Review (SCA-18)

Goal:

Complete the field-level review of every family that could bypass the compact
V2 session/memory contract through `preserved_context`.

Changes:

- Added an allowlist projector for focus, affect, and metacognitive blocks.
- Excluded legacy Scarlet state, duplicate dialogue, generic runtime events,
  and capability catalogs from automatic model input while retaining their
  rich runtime source data.
- Added a field-level projection audit to `model.context` traces.
- Kept native MiniMax and GPT bootstrap on the same canonical V2 document.
- Updated native/GPT prompts and context/API/registry documentation to match
  the implemented contract.

Verification:

- Focused context, native chat, GPT bridge, and mode tests.
- Direct deterministic inspection of the compiled V2 document and audit.
- No live Scarlet campaign and no production/VPS database operation.

## 2026-07-14 - Proportionate Test Cadence

Decision:

- Ordinary tasks use focused deterministic tests and direct Codex operation of
  the affected tool or surface.
- Complete repeated Scarlet suites, cross-branch batteries, long live sessions,
  and broad pre/post behavioral campaigns require an explicit owner request for
  the current task.
- Existing deterministic CI remains automatic because it does not consume live
  model calls.

Reason:

The V1.34 baseline is now available for deliberate evaluation periods; it must
not turn a small task into hours of unnecessary live-model testing.

Verification:

- Documentation integrity and Git boundary checks only; no runtime behavior or
  database was changed.

## 2026-07-14 - V1.34.0 Natural Behavioral Baseline (SCA-2)

Goal:

Turn the four-layer behavioral contract into a repeatable cross-branch suite
using natural human prompts, frozen real references, real MiniMax M3 behavior,
and reasoned qualitative judgment.

Changes:

- Added shared immutable preliminary DB references and guards used by both the
  deterministic and natural evaluators.
- Added behavioral suite/group/run/judgment contracts, objective evidence
  extraction, disposable DB execution, judgment application, and pre/post
  comparison that only auto-fails objective technical regressions.
- Added 12 natural scenarios in 8 groups for positive/negative memory,
  episodic provenance, focus, volition, affect, metacognition, and mode.
- Executed 45 evaluator-shakedown MiniMax M3 turns, corrected two invalid
  oracle assumptions and removed scenario identity from model-facing session
  titles/metadata, then executed and reviewed the authoritative 36-turn run.
- Recorded BUG-0082 after explicit exasperation remained below the affect
  activation threshold in all three independent repetitions.
- Updated process, experiment, decision, branch, state, evaluation, and release
  documentation to the V1.34.0 baseline.
- Replaced two evaluator-support tests that accidentally depended on the local
  ignored preliminary DB with canonical temporary SQLite fixtures, preserving
  the real runner's frozen-hash boundary while making clean CI reproducible.

Evidence:

- Authoritative run: `20260714_123449_scarlet-natural-core-v1`.
- Shakedown runs: `20260714_112611_scarlet-natural-core-v1` and
  `20260714_121053_scarlet-natural-core-v1`.
- Evaluation: `docs/evaluations/v1.34-natural-behavioral-suite.md`.
- Preliminary pre/post runs remained 9/9 before the final quality gate.
- Final engineering gate: 182 backend tests at 80.19% coverage, Ruff clean,
  mypy clean on the blocking slice, documentation integrity clean, and
  frontend production build successful.
- The first PR run exposed the local-baseline test dependency; the corrected
  CI-like backend run passed all 182 tests at the same 80.19% coverage.

Boundary:

- Every live scenario used a fresh ignored disposable copy of the frozen DB.
- `backend/data/app.db`, VPS production data, maintenance, prompts, and organ
  implementation were not modified.
- Organ findings are evidence for SCA-4/SCA-6, not opportunistic fixes in
  SCA-2.

## 2026-07-14 - GitHub Publication Recovery And P0 Closure

Goal:

Restore authenticated publication after the stale remote/403 condition and
align the verified feature history, `main`, release tags, CI, Linear, and the
known V1.32.0 production boundary.

Changes:

- Installed and authenticated GitHub CLI as repository owner `panicDa3m0n`
  with repository and workflow scopes, then configured HTTPS Git operations.
- Published `feature/agent-modes-history-compaction` without its unrelated
  local database modification and opened catch-up PR #1 toward `main`.
- Published annotated tag `v1.32.0` at `298d668`, the exact runtime code commit
  deployed on HoneyLabs. V1.33.0 intentionally remains untagged until its own
  protected deployment.
- Chose a normal PR merge into `main`; the feature branch remains a readable
  checkpoint instead of force-updating or rewriting stale remote history.
- After the merged `main` workflow passed, its only annotation identified the
  official Node 20 Action runtimes as deprecated. Updated checkout,
  setup-python, and setup-node to their official Node 24 major versions.

Verification:

- GitHub Actions ran the complete V1.33.0 quality workflow for both push and
  pull-request events; both runs passed in 1m36s.
- PR #1 is mergeable with clean merge state and successful required checks.
- Merged `main` passed the complete quality job in 1m23s before the Action
  runtime update; the follow-up run verifies the Node 24 cleanup.
- The staged DB boundary passed before both release commits; only
  `backend/data/app.db` remains locally modified and uncommitted.

Release State:

- GitHub `main` is aligned through PR #1 with the V1.33.0 verified history.
- HoneyLabs remains truthfully documented as V1.32.0 until a separate backup,
  production preflight, transfer, restart, and smoke procedure is executed.

## 2026-07-14 - V1.33.0 Engineering Quality Baseline

Goal:

Close the P0 engineering-observability gap before broad code rework, while
keeping all existing typing debt visible and preserving the production and
laboratory database boundaries.

Changes:

- Added Ruff `E4/E7/E9/F` checks across backend code, tests, and scripts and
  removed eight objective unused-import/dead-assignment findings without
  applying mass import sorting.
- Added an incremental mypy gate over six clean, high-value modules. A separate
  full-app measurement records 216 existing errors across 23 files.
- Added full-suite coverage enforcement at 79.9% against the measured 79.998%
  baseline, with evaluator entry points retained in the denominator.
- Added deterministic documentation validation for local links, repository
  references, and canonical ADR/BUG/EXP identifiers. The check also exposed
  and corrected the canonical shell-conformance bug id collision as BUG-0081.
- Added `.github/workflows/quality.yml`, documented the local/CI commands, and
  advanced package and canonical documentation metadata to V1.33.0.
- Corrected the first clean-run CI finding: generated environment paths such
  as `backend/.venv/bin/python` are executable instructions, not versioned
  repository references, and are now ignored independently of local presence.
- Recorded the owner's real GPT Builder validation of BUG-0080: progress notes
  now remain visible during a multi-action turn.

Boundary:

- No cognitive runtime contract, production configuration, secret, or runtime
  database was changed for the quality-gate implementation.
- `backend/data/app.db` remained an unrelated mutable laboratory artifact and
  is excluded from the release commit.

Verification:

- Ruff: passed across `backend/app`, `backend/tests`, and `scripts`.
- Incremental mypy: 6 source files passed.
- Documentation integrity: 48 files, 1,119 repository references, and 223
  canonical identifiers passed.
- Backend: `161 passed`; exact coverage 8,195/10,244 statements (`79.998%`).
- Frozen preliminary regression: `9/9` at
  `backend/app/evals/runs/20260714_090856_preliminary-regression-v1`.
- Frontend V1.33.0 production build: passed.

## 2026-07-13 - V1.32.1 GPT Progress-Note Fix

Goal:

Remove long silent periods from non-trivial Custom GPT turns without weakening
the mandatory bootstrap/action/finalize lifecycle.

Changes:

- Replaced the GPT bridge prompt with an explicit turn state machine that
  permits and requires short public progress notes after bootstrap and during
  long cognitive work, while finalizing only the concluding answer.
- Added note waypoints before the first action cluster, slow metacognition,
  strategy changes, continued multi-action work, and long final synthesis.
- Aligned GPT Action descriptions with that distinction, corrected bootstrap
  field placement/context V2 language, added `mode`, and kept every operation
  description below the GPT Builder 300-character limit.
- Added a plain-Markdown final-draft rule excluding `:::writing` and other
  private ChatGPT UI directives.

Boundary:

- The native MiniMax prompt was inspected and not changed. Its established
  Public Work Notes and Long Reasoning Notes policy already has the intended
  behavior.
- No backend endpoint, production database, or VPS runtime was changed.

Follow-up validation:

- On 2026-07-14 the owner tested the revised prompt and Action schema in the
  real GPT Builder flow and confirmed that progress notes work throughout the
  multi-action turn. The fix is included in V1.33.0.

Verification:

- `backend/tests/test_gpt_bridge.py`: `7 passed`; coverage includes prompt
  markers, lifecycle assets, operation description length, and
  progress-note/finalize wording.
- Prompt size is 7,223 characters; Action descriptions are 263, 276, and 266
  characters. JSON parsing, `git diff --check`, and the staged database
  boundary check pass.

## 2026-07-13 - V1.32.0 Production Deployment

Goal:

Deploy the verified local V1.32 runtime to the HoneyLabs VPS with the same
active cognitive functions while preserving production-only database and
maintenance boundaries.

Deployment:

- Created release commit `298d668` on
  `feature/agent-modes-history-compaction`; `backend/data/app.db` remained
  unstaged and the staged DB boundary passed.
- GitHub publication was attempted but rejected by the configured HTTPS
  credentials. The VPS deployment therefore used the verified local commit
  directly; no secret was changed or exposed during the failed push.
- Created production backup
  `/var/backups/scarlet-mobile-test/v1320-20260713T211855Z` containing an
  online SQLite backup, previous code, previous runtime configuration, and
  frontend bundle. Backup integrity was `ok`.
- Transferred backend and frontend with runtime data, `.env`, virtualenv,
  caches, evaluator runs, and SQLite files excluded.
- Added the existing local OpenRouter credential to the protected remote
  runtime and aligned V2/retrieval/mode configuration: OpenRouter shadow and
  rerank enabled, active final arbitration, threshold `0.01`, active mode
  routing, and optional organs off.
- Preserved production-only settings: `DATABASE_ROLE=production`,
  `CODEX_TEST=false`, and `SUMMARY_RECONCILE_ENABLED=false`.

Verification:

- The new image passed read-only production preflight before restart:
  integrity `ok`, 28 tables, 294 memories, 197 sessions, and direct isolation.
- Running package and OpenAPI report `1.32.0`; `/health` reports MiniMax M3 and
  production/direct DB ownership.
- Public GPT Actions smoke completed bootstrap, eight read-only shell families
  (`help`, session, memory, focus, volition, affect, mode, metacognition), and
  exact finalize on session `ses_c6931ae93736472e985b05c55714d696`.
- Native MiniMax smoke completed on session
  `ses_4d178526036148f58b03b8532570b7f2`.
- Production traces report final rerank `ok=true`, `status=completed`; the
  manual memory search accepted 10 candidates using the configured Nemotron
  reranker.
- Post-smoke DB preflight remained `integrity=ok`, with 294 memories unchanged;
  the two expected smoke sessions brought totals to 199 sessions and 811
  messages. Container logs contained no error, exception, or traceback.

Residual Risk:

GitHub still lacks valid HTTPS credentials for this environment. The release
exists as local commit plus deployed VPS code until the branch can be
published.

## 2026-07-13 - V1.32.0 Cognitive Shell Organ Conformance

Goal:

Audit every current cognitive-shell organ after the memory work, repair proven
registry/parser/handler/storage drift, and verify representative behavior with
real Scarlet without touching production data.

Changes:

- Removed the hidden 500-session ceiling and separated transcript return
  windows from complete fallback-summary evidence.
- Corrected focus hold state, focus/affect targeted misses, list pagination,
  affect filters, resumable mode ownership, volition scheduling, executable
  focus promotion, metacognition retrospective flags, and help/alias parity.
- Added conformance tests proving all 23 family/namespace aliases agree and all
  help-published commands validate as executable.
- Ran five natural MiniMax M3 scenarios on a disposable DB copy covering
  episodic recall, affect, focus, volition, and metacognition.

Verification:

- Full backend suite: `161 passed`.
- Frozen preliminary regression: `9/9` at
  `backend/app/evals/runs/20260713_211233_preliminary-regression-v1`.
- Live report: ignored runtime artifact
  `backend/app/evals/runs/20260713_v132-shell-live.json`; the disposable DB was
  deleted after extraction.
- Frontend production build and `git diff --check` passed.
- The Mind API test factory now pins retrieval mode `off` unless a case
  explicitly overrides it, so developer `.env` production settings cannot
  silently change deterministic test semantics.

Residual Risk:

Technical shell conformance does not prove autonomous command choice. Focus
maintenance, affect calibration, volition cycles, and metacognitive follow-up
still need longitudinal behavioral experiments.

## 2026-07-13 - V1.31.0 Final Memory Rerank Arbitration

Goal:

Apply the established memory principle that deterministic retrieval signals
find candidates while an advanced contextual reranker alone decides what is
relevant to Scarlet's current turn.

Changes:

- Replaced active weighted hybrid fusion with a deduplicated round-robin pool
  over sparse, dense, NetworkX graph, and lexical recall routes.
- Added one final memory-level rerank over canonical content and active facts.
- Made automatic context and manual memory search accept/order results only
  from rerank in active mode; unavailable rerank now fails closed.
- Removed the obsolete hybrid ranker, retained a compatibility trace key, and
  stopped duplicate current-message text from biasing retrieval queries.
- Preserved rich route scores for traces without allowing them to become final
  relevance judgments.

Verification:

- Focused final-arbiter contracts: `7 passed`.
- Chat/Mind/V2/GPT bridge slice: `67 passed`.
- Final-arbiter/V2 provider-delivery contracts: `3 passed` after adding the
  sourceable-hook assertion.
- Full backend suite on the final state: `149 passed`.
- Frontend production build passed.
- Python compilation and `git diff --check` passed.
- Direct MiniMax M3 positive/negative controls:
  `docs/evaluations/v1.31-final-memory-rerank-live.md`.

Live Evidence:

- The initial `0.55` threshold rejected the predicted top-ranked mint-tea
  memory at `0.465327`; an intermediate `0.40` passed that case but failed the
  frozen exact Zero-Luce positive at `0.089455`. The provisional default is
  now `0.01`; the observed negative remains below `0.0004`.
- A second run was rejected as evidence because rich selection did not reach
  the provider while historical message provenance was incomplete.
- After applying the existing deterministic provenance repair to a fresh
  disposable full copy, the expected memory appeared in both V2
  `memories.relevant` and `llm.request`; Scarlet answered from it explicitly.
- An independent jazz/cooking session selected zero relevant memories, with a
  maximum near-miss score of `0.000391`.
- Frozen preliminary regression: initial `8/9` at `0.40`, then accepted `9/9`
  at `0.01` in `20260713_202744_preliminary-regression-v1`.
- Final sourceable live repetition at `0.01`: expected mint preference rank 1,
  compatible caffeine constraint rank 2, provider delivery verified, and
  independent negative still selected zero relevant memories.

Residual Risk:

Reranker availability is now an active dependency. The candidate pool remains
bounded, the `0.01` threshold is only initially calibrated, and historical
memories without complete source provenance remain ineligible for automatic V2
delivery until a sourceable repair is applied.

## 2026-07-13 - V1.30.0 Context Accounting, Agent Modes, And Behavioral Gate

Goal:

Measure every model-input family before designing history compaction, introduce
main-agent operating modes without confusing them with background jobs, and
make behavioral acceptance depend on declared real evidence rather than tool
availability alone.

Changes:

- Added native per-channel accounting and provider-authoritative first-step
  observations. Aggregate tool-loop usage remains a separate metric.
- Configured the MiniMax 1M window, API Mind 500k operating boundary, 400k
  compaction trigger, provisional 100k chronological summary, and desired
  eight complete turns. Compaction remains shadow-only and never mutates the
  canonical chronology.
- Added `idle`, `interactive`, and `scouting`, one active tag, multi-tag organ
  eligibility, persistent resumable posture, automatic block routing, and
  `mode read/list/set` with traces/events.
- Made mode state explicit that `scouting` has no autonomous sensor runtime and
  that `mode set` persists posture without starting a background cycle.
- Added the evidence-first `behavioral-scenario-v1` contract and its four
  result layers.
- Removed the duplicate GPT `context.model_context` payload and added partial
  bridge accounting that never claims visibility into ChatGPT-native tokens.
- Fixed the shell mismatch where bare `volition list` was advertised but
  reached the handler as an invalid action.

Real Evidence:

- Read-only laboratory inspection found first-step calibration around
  3.75-4.83 characters/token. Eight-turn proxies ranged from about 63k to
  159k tokens; a five-turn tool-heavy tail reached about 323k. Eight turns are
  therefore a desired tail, not a guaranteed fixed window.
- Four same-prompt MiniMax M3 probes ran on independent disposable copies of
  the frozen preliminary DB. The first exposed a malformed `volition list`,
  the second replaced mode change with memory, and the third set mode but
  overclaimed automatic execution. After targeted fixes, the fourth called
  `mode set scouting`, wrote the optional durable preference, persisted
  `resume_tag=scouting`, kept `interactive` active, and explicitly stated that
  no autonomous loop or sensor runtime exists.
- The accepted direct turn was
  `turn_771df91d1e574f268726442d581af777` in disposable session
  `ses_0c19e70c61774bde9837d19ff69685a2`; the disposable DB was deleted after
  inspection and no production/laboratory data was changed.

Verification:

- Backend suite: `146 passed`.
- Frozen preliminary regression: `9/9` in
  `20260713_163648_preliminary-regression-v1`.
- Frontend production build passed.
- GPT prompt length: `7809` bytes, below the protected 8,000-character limit.

Residual Risk:

Active compaction is not yet justified. The accepted mode probe validates one
natural scenario after correction, not broad longitudinal behavior. Scouting
is state/registry only until an independently designed runtime exists.

Next Suggested Step:

Accumulate post-V1.30 accounting in a genuinely long varied session, then build
and compare a source-labelled derived chronology without activating it. Expand
the behavioral scenario set before adding sensors, autonomous cycles, or more
agent modes.

## 2026-07-13 - V1.29.1 Integrated System And Documentation Audit

Goal:

Verify the implemented system after the canonical context rework, realign the
project documentation to current code and deployed evidence, and assess every
cognitive branch without equating code presence with active cognitive
behavior.

Changes:

- Rebuilt `project-state.md` and the branch matrix around four independent
  dimensions: implementation, deterministic tests, direct Scarlet evidence,
  and normal runtime activation.
- Reviewed all 14 branch records and aligned their current evidence, limits,
  defaults, and next technical work to V1.29.1.
- Reconciled context packet, block registry, API contract, database topology,
  memory/cognitive roadmaps, GPT knowledge, blueprint, and theory documents
  with the shared `scarlet-model-context-v2` runtime.
- Preserved chronological documents as historical evidence while clearly
  marking implemented plans and normalized duplicate ADR/EXP/BUG identifiers.
- Recorded unbudgeted provider-native history as BUG-0076 and documented the
  largest maintainability concentrations without changing runtime code.

Verified State:

- `mind_shell(command, intent)` is the single model-facing cognitive surface;
  internal `/mind/*` endpoints remain deterministic backend boundaries.
- Memory, episodic recall, V2 context, tracing, maintenance, GPT transport,
  focus, volition, affect, and metacognition exist, but organ activation and
  behavioral evidence vary by branch.
- Temporal experience and Dream remain registry/config reservations, not
  implemented organs. External operativity and broad autonomy remain early.
- The long-term target is an inspectable cognitive architecture for a digital
  individual with human-like functional research goals and explicit digital
  differences, not an unsupported equivalence claim.

Scope Boundary:

This was a documentation/version audit. It did not mutate production or local
databases, alter runtime behavior, change provider prompts, deploy services, or
activate cognitive organs. The pre-existing mutable `backend/data/app.db`
remained excluded.

Verification:

- Backend suite: `138 passed`.
- Frozen preliminary regression: `9/9` in
  `20260713_130851_preliminary-regression-v1`.
- Frontend production build passed.
- Database boundary guard passed.
- Documentation identifier, terminology, local-link, and diff checks passed.

Next Suggested Step:

Measure the complete model-input budget by channel and design provider-history
degradation in shadow mode. In parallel, specify the memory duplicate/conflict
review protocol and prepare behavior-first activation experiments for focus,
volition, affect, and metacognition before adding new organs.

## 2026-07-12 - V1.29.0 Context Packet Rework Completed

Goal:

Implement the owner-reviewed compact dynamic context contract end to end while
preserving rich backend evidence and protecting every production/laboratory DB.

Changes:

- Added the canonical `scarlet-model-context-v2` projection shared by MiniMax
  and GPT Actions, with one local clock, compact session/user/world state, two
  previous-session hints, and three globally deduplicated memory blocks.
- Added append-only cognitive memory activity, complete live source-message
  provenance, strict automatic-hook resolvability, and direct
  `session message` / `session turn` navigation.
- Added summary audit/reconciliation and provenance audit/repair operations;
  fixed retry idempotency and detached scheduled-job results.
- Activated V2 behind reversible settings while retaining full legacy runtime
  evidence in traces and adding exact `model.context` UI visibility.
- Updated native/GPT prompts and runtime contract knowledge for V2.

Pre-Deploy Data And Live Evidence:

- Only `/tmp/llm-api-mind-v129-lab.db`, copied from the local laboratory DB,
  received migrations, repairs, summaries, or live-test sessions during
  implementation and evaluation before the production deployment.
- Provenance dry-run found 36 unambiguous records; repair completed 36/36.
- Summary reconciliation completed 34/34 real provider jobs in two bounded
  batches; final audit: 146 current, 6 blocked active turns, 11 empty.
- Live Scarlet correctly handled local time/location, automatic Zero-Luce
  recall, exact source inspection, previous-session continuity, personal
  preference persistence, and later no-tool automatic recall.
- One thinking-only MiniMax turn returned an empty public answer; recorded as
  BUG-0067 and successfully isolated from the context/memory implementation by
  a fresh-session write/recall retry.

Production Deployment (2026-07-13):

- Created commit `9472f60` on `checkpoint/rework-baseline`; the mutable local
  `backend/data/app.db` was excluded and the staged database boundary passed.
- Created and verified the production backup under
  `/var/backups/scarlet-mobile-test/v1290-20260713T104324Z`; its online SQLite
  copy retained 193 sessions, 785 messages, 288 memories, and integrity `ok`,
  alongside an archive of the previous code and configuration.
- Transferred backend code with runtime data, `.env`, virtualenv, caches,
  evaluator runs, and SQLite files excluded. The V1.29.0 image passed a
  read-only production-role preflight against the existing mount before
  `scarlet-mobile-api` was recreated.
- Added the explicit remote `DATABASE_ROLE=production`; `/health` reports
  direct production isolation and package/OpenAPI version `1.29.0`.
- Applied the additive `memory_activities` table and repaired 46/46
  unambiguous source-message links. The remaining 242 historical memories
  lack sufficient session/turn evidence and were intentionally left
  unresolved.
- Generated 67/67 eligible historical session summaries with MiniMax M3,
  without failures. The stable post-smoke audit reports 170 current summaries,
  12 empty sessions, and 14 sessions blocked by an active turn. An independently
  created `Email Monitor` turn appeared as `started` during deployment, then
  completed normally and received its summary once it became eligible.
- Enabled the normal 900-second idle maintenance path. Production sets
  `SUMMARY_RECONCILE_ENABLED=false` after the one-time historical repair so
  future summaries are produced by the established idle job after 15 minutes,
  not immediately by the broad repair scanner.
- Published the V1.29.0 frontend bundle under `/var/www/scarlet` after a
  timestamped backup.
- Public GPT bridge smoke passed
  `bootstrap -> help action -> finalize`; bootstrap returned the shared
  `scarlet-model-context-v2`, and finalize returned the exact answer.
- Native MiniMax smoke consumed V2 without a tool call and correctly answered
  from `Europe/Rome`, `CEST`, and `Italia`. A follow-up GPT finalize scheduled
  an idle maintenance job at 899 seconds, confirming the production timing.
- GitHub publication remains pending: the macOS credential helper selected
  unauthorized account `DavDit94` and GitHub returned HTTP 403. No credential
  was changed or exposed during recovery attempts.

Verification:

- Backend: `138 passed`.
- Frozen preliminary regression: `9/9`.
- Frontend: `npm run build`.
- Disposable summary reconciliation: `34/34 completed`.
- Production DB preflight and post-migration integrity: `ok`.
- Production historical summaries: `67/67 completed`.
- Production source-message repair: `46/46 repaired`.
- Public GPT Actions and native MiniMax V2 smokes passed.

Next Suggested Step:

Run the first human GPT Builder conversation against V1.29.0 and inspect the
resulting `model.context` trace. Resolve the GitHub credential ownership before
publishing the checkpoint, then review the still-preserved
dialogue/runtime-event/capability/Scarlet-state families. Treat BUG-0067
separately from context routing.

## 2026-07-12 - V1.29.0 Context Packet Implementation Plan

Goal:

Convert the owner-reviewed context-packet discussion into an implementable,
testable, and reversible plan without changing current runtime behavior.

Changes:

- Added `docs/context-packet-implementation-plan.md` with the accepted compact
  session and memory contracts, one-user-time rule, cross-block memory
  deduplication, cognitive-recency semantics, direct source navigation, phased
  shadow rollout, provider parity, verification matrix, and commit slices.
- Kept rich backend evidence distinct from the exact model-facing projection,
  so trace/UI/debug data is preserved while Scarlet receives only approved
  dynamic context.
- Added mandatory decision gates for dynamic packets not yet reviewed by the
  owner rather than assigning them an inferred contract.
- Closed the reviewed-family gates for current-session fields, missing-summary
  fallback, immediate memory-recency state, legacy provenance repair, and
  MiniMax/GPT context parity.
- Recorded that the existing 900-second idle summary job remains the primary
  automatic path; the reviewed plan now adds bounded asynchronous
  reconciliation during maintenance cycles and new-session creation.
- Clarified that duplicate/conflict candidate discovery and semantic judgment
  require a separate design workstream; they are not part of the V1.29.0
  packet compiler.
- Corrected the planned legacy-recency bootstrap: current `updated_at` and
  `last_used_at` cannot be trusted blindly because automatic reads may have
  changed them. A sourceable audit and creation-time fallback replace inferred
  historical access.
- Recorded ADR-0071 so the shared MiniMax/GPT compact dynamic-context contract
  is architectural project memory rather than only a working-note decision.
- Explicitly deferred memory-conflict semantics, historical activity backfill,
  multi-user migration, embodiment routing, and legacy-field removal.
- Linked the plan from the documentation index and the working inventory.

Verification:

- Cross-checked the plan against the owner notes in
  `docs/context-packet-inventory.md`, current `app.mind.context` composition,
  GPT bridge rendering, memory activity fields, and Mind shell session
  commands.
- Documentation-only change; no runtime, prompt, schema, database, deployment,
  or test behavior changed.

Next Suggested Step:

Keep undiscussed context families unchanged. Run the frozen preliminary
baseline and provenance report, then implement complete live source-message
capture before activity tracking, historical repair, or the V2 shadow compiler.

Implementation-readiness review:

- Verified the current chat, storage, maintenance, Mind shell, context builder,
  GPT bridge, SQLite schema, and laboratory state before implementation.
- Found that all 36 laboratory memories lack `source_message_id`, although all
  have a valid source turn with exactly one user and one assistant message.
- Found that direct write omits message provenance and maintenance
  normalization discards message ids already present in its source prompt.
- Found that automatic and manual memory reads mutate semantic `updated_at`;
  32 of 33 used laboratory memories have `updated_at == last_used_at`.
- Reordered the plan so live provenance and activity semantics precede legacy
  repair and the V2 shadow compiler.
- Added BUG-0064 and BUG-0065 and corrected the plan's profile-isolation claim:
  current memory visibility is single-user/scope-based, not profile-owned.
- Verified the current relevant backend contracts with 45 passing tests across
  storage, maintenance, GPT bridge, Mind shell, and chat API.
- Full backend regression suite also passed: `131 passed`.
- Classified summary coverage in the read-only laboratory DB: 34 completed
  non-empty sessions are backfillable, 6 are blocked by `started` turns, and 4
  are empty. Thirty-nine non-empty missing-summary sessions had no maintenance
  job; one had a provider-failed job.
- Added BUG-0066 and a summary-reconciliation phase with dry-run/batching,
  summary-only historical repair, retry/backoff, stale-turn isolation, and
  periodic/new-session repair checks.

## 2026-07-11 - Context Packet Inventory Review

Goal:

Make automatic data delivery to Scarlet inspectable before changing the
runtime-context architecture or introducing context-pack routing.

Changes:

- Added `docs/context-packet-inventory.md`, separating automatic local model
  input, automatic GPT bootstrap data, conditional organ blocks, manual shell
  results, and trace/UI-only diagnostics.
- Recorded packet functions, source modules, current selection limits,
  compatibility mirrors, and explicit exclusions such as raw retrieval/graph
  diagnostics and external sensory feeds.
- Linked the inventory from the documentation index and refreshed the block
  registry's reviewed baseline metadata.

Evidence:

- Current context builder, chat request assembly, shell presentation, episodic
  recall, bridge renderer, runtime events, and laboratory request traces were
  inspected read-only.
- Selected automatic memory is compacted for model input while raw retrieval
  diagnostics stay trace-only. Previous sessions and user-profile memories are
  currently recency-selected.

Open Review:

No context selection policy changed. Owner review of the inventory precedes any
decision about future always-on, conditional, on-demand, or trace/UI-only
context packs.

## 2026-07-10 - V1.28.0 Storage Repository Domain Split

Goal:

Reduce the storage monolith without changing Scarlet's persistence contract or
the model-facing cognitive runtime.

Area:

Storage organization / maintainability / regression safety.

Changes:

- Replaced the 2,073-line implementation behind
  `app.storage.repositories` with a compatibility facade and five domain
  modules: sessions, runtime support, cognitive organs, canonical memory, and
  derived retrieval state.
- Moved the shared session-touch helper into a small private module so
  cross-domain timestamp updates stay visible.
- Kept every existing public repository name and signature stable; added a
  regression test that asserts the facade re-exports the domain operations.

Verification:

- Targeted repository/storage/organ/maintenance tests: `25 passed`.
- Full backend suite: `131 passed`.
- Unchanged preliminary regression: `9/9` in
  `20260710_152411_preliminary-regression-v1`.
- V1.28.1 removes the four trailing-whitespace findings from the published
  split; no runtime behavior changed.

Next Suggested Step:

Use the now-separated storage domains to review `memory.py` and `chat.py` in
their own focused slices. Keep the database boundary and preliminary gate
unchanged for each subsequent rework.

## 2026-07-10 - V1.27.0 Database Ownership Boundary

Goal:

Make it impossible for normal tests, evaluator imports, code commits, or a
file-copy deployment to confuse the VPS production database with laboratory
state or disposable evaluation copies.

Area:

Storage ownership / evaluation isolation / deploy safety.

Changes:

- Audited all local SQLite files and the VPS container in read-only mode.
  The VPS has one writable bind mount,
  `/opt/scarlet-mobile-test/backend/data -> /app/data`, containing the real
  211,148,800-byte `app.db`; `CODEX_TEST=false`.
- Added the canonical `docs/database-topology.md` inventory and made database
  role (`production`, `laboratory`, `test`, `preliminary`) explicit in runtime
  configuration, health/dashboard metadata, and evaluator setup.
- Moved the eager ASGI object from `app.main` to `app.asgi`; `app.main` is now
  an import-safe application factory, closing a path that could initialize the
  environment-selected DB during test/evaluator import.
- Added read-only `app.ops.database_preflight`, a staged Git guard for the
  mutable LFS laboratory snapshot, and a VPS deployment procedure that excludes
  runtime `data/` and `.env` from any code transfer.
- Retained all existing DB files. The historical ignored `codex_test.db` is no
  longer selected or reset by the dirty-memory evaluator; the updated harness
  creates a marked disposable run DB from the frozen baseline.

Verification:

- Targeted database/health/chat tests passed: `25 passed`.
- Unchanged preliminary regression gate passed: `9/9` in
  `20260710_151853_preliminary-regression-v1`.
- Full backend suite passed: `130 passed`; frontend production build passed.
- The historical dirty-memory evaluator wrote all 240 controlled records to
  `codex-memory-eval-v2-run.db` with `role=test`; it did not touch either
  source DB. Its context score was `0/5` because the harness still reads a
  retired metadata shape (`BUG-0063`), not because the database boundary
  failed.
- The local preflight reported `laboratory`, direct isolation, SQLite integrity
  `ok`, and the expected sourceable state counts without mutation.
- ASGI smoke under an explicit temporary test DB passed.

Next Suggested Step:

Run the preliminary whole-system regression and full backend suite, then use
the V1.27.0 boundary as the prerequisite for the next repository
organization slice. Do not deploy this version until the VPS `.env` contains
`DATABASE_ROLE=production` and the preflight procedure is followed.

## 2026-07-10 - V1.26.0 Preliminary Regression Gate And Rework Checkpoint

Goal:

Create a reliable pre/post whole-system comparison before the planned runtime
and code-organization rework, while publishing the completed shell/bridge
checkpoint to `main`.

Area:

Repository checkpoint / regression methodology / evaluator infrastructure.

Changes:

- Published `0329792 feat(mind): add shell runtime and external GPT bridge`.
  The commit was pushed to `feature/mind-command-runtime`, fast-forwarded into
  `main`, and the rework branch `checkpoint/rework-baseline` was created and
  pushed from that exact checkpoint.
- Intentionally excluded the locally modified `backend/data/app.db` LFS object
  from the code checkpoint. It is mutable laboratory state, not an implicit
  code/data release.
- Added `backend/app/evals/preliminary_regression.py` and
  `docs/preliminary-regression-suite.md`.
- Froze an ignored source copy of the published LFS object
  `827bb25a7d0d41940d4911715072b4f8cb6da3ec7178f0526834b75a020c1ed5` and
  chose real active/deprecated memory, fact, and source-session references.
- Recorded ADR-0068 and EXP-0050 so the pre/post comparison is now an accepted
  engineering procedure rather than a one-off evaluator exercise.
- Completed the first code-organization slice on the active cognitive surface:
  - extracted `MindAPIContext` and `MemoryOperationResult` from `memory.py`
    into `mind/contracts.py`, so non-memory organs no longer import their
    common runtime contracts from the memory implementation;
  - extracted pure command parsing, flags, and temporal-filter grammar into
    `mind/shell_parsing.py`;
  - extracted shell envelope construction, help/errors, sanitization, and
    model-facing compact result profiles into `mind/shell_presentation.py`;
  - reduced `mind/shell.py` from 1,260 to 718 lines while preserving its public
    `MindShellRequest` and `dispatch_mind_shell` contract.
- Audited larger remaining modules. `memory.py`, `repositories.py`, `chat.py`,
  and the GPT bridge router still have substantial size, but their next splits
  require domain-specific boundary decisions. The deprecated MCP portion of
  the bridge is intentionally left isolated by policy and should be removed or
  extracted in a dedicated deprecation slice rather than mixed into this
  active-shell refactor.

Verification:

- Pre-checkpoint full backend suite: `120 passed`.
- `git diff --check` and compilation of the new regression runner passed.
- Preliminary integration baseline:
  `20260710_141950_preliminary-regression-v1` passed `9/9` on a fresh
  disposable DB copied from the frozen source.
- Post-rework comparison:
  `20260710_143138_preliminary-regression-v1` passed `9/9` on the same fresh
  source copy, with no case regression.
- Full backend suite after the rework: `124 passed`.

Next Suggested Step:

Use the accepted V1.26.0 checkpoint as the base for the shadow runtime
context-pack router. Keep the preliminary regression gate unchanged and rerun
it before accepting that future architectural slice.

## 2026-07-09 - V1.26.0 Runtime Context Pack Planning

Goal:

Prepare the repository for future context/runtime scaling before Scarlet gains
high-volume embodied inputs such as vision, audio, voice, movement, and
physical interaction.

Area:

Runtime context architecture / agentic organs / embodiment preparation /
project documentation.

Changes:

- Added `docs/runtime-context-packs.md` as the planning baseline for an
  always-on context spine, mode-specific packs, organ/source/capability
  classification, coupling, freshness, authority, cost, safety, and
  degradation rules.
- Recorded ADR-0067: runtime context packs are the accepted planning baseline
  before any future embodied context expansion.
- Recorded EXP-0049 for the corrected default-token live Scarlet probe,
  explicitly distinguishing it from the earlier falsified stop-token run.
- Parked the live-probe issues as known bugs without fixing them now:
  temporal recall without exhaustive session search, metacognition
  recommendations not followed, self-architecture overclaim, memory-write flag
  alias drift, and immediate preference-shape weakness.
- Updated project-state, blueprint, branch docs, and organ notes so future
  organs must define their context classification before broad model-facing
  injection.

Verification:

- `git diff --check` passed.

Next Suggested Step:

Implement a shadow runtime context-pack router that traces which pack would
have applied to each real turn before changing live model input.

## 2026-07-09 - V1.25.4 Mind Shell Registry Parity And Capability Boundary

Goal:

Close the gap between the `mind_shell` command registry, shell handlers, and
runtime capability context before returning to main development branches.

Area:

API Mind shell / metacognition action validation / runtime context capability
state / project documentation.

Changes:

- Fixed command-registry validation so flag values are not counted as
  positional arguments.
- Added required-field parity for lifecycle commands that need reasons,
  resolutions, impossible reasons, or two memory ids.
- Made hyphenated canonical volition aliases accepted by the shell when the
  registry suggests them.
- Changed model-facing runtime capability state to come from the shell command
  registry instead of legacy endpoint routes.
- Marked `memory.facts.backfill` as `internal_maintenance_only`; it remains an
  internal endpoint for rebuilding canonical facts/retrieval artifacts, not a
  normal Scarlet shell command.
- Corrected project documentation status drift and updated the relevant branch,
  API contract, project-state, roadmap, bug ledger, and changelog entries.
- Advanced backend app/package metadata to `1.25.4`.

Verification:

- `cd backend && .venv/bin/python -m pytest tests/test_mind_shell.py
  tests/test_chat_api.py::test_chat_turn_dispatches_and_traces_mind_shell_tool_call
  tests/test_mind_api.py` passed: `45 passed`.
- `cd backend && .venv/bin/python -m pytest` passed: `120 passed`.
- `cd backend && .venv/bin/python -m json.tool app/plugins/gpt_bridge/openapi_gpt_action.json >/dev/null`
  passed.
- `git diff --check` passed.

Next Suggested Step:

Resume main branch work with the shell as the only model-facing API Mind
contract and the legacy endpoint surface documented as internal/debug/
maintenance support.

## 2026-07-09 - V1.25.3 GPT Actions Schema Parity

Goal:

Align the deployed backend contract with the corrected GPT Builder Actions
schema being used on the platform.

Area:

GPT bridge plugin / Actions schema / bootstrap and action response contract.

Changes:

- Added top-level `session_id` to `/gpt/bootstrap` responses while keeping the
  nested `session` object.
- Made `/gpt/action` `intent` required in the backend request model and local
  OpenAPI Actions schema.
- Added optional `action_policy`, `required_actions`, and
  `recommended_actions` fields to bootstrap responses.
- Updated the local Actions schema wording to the stronger REQUIRED summaries
  used in GPT Builder.
- Advanced backend app/package metadata to `1.25.3`.

Verification:

- `backend/.venv/bin/python -m json.tool
  backend/app/plugins/gpt_bridge/openapi_gpt_action.json` passed.
- `cd backend && .venv/bin/python -m pytest tests/test_gpt_bridge.py`
  passed: `7 passed`.
- `cd backend && .venv/bin/python -m pytest tests`
  passed: `118 passed`.
- `git diff --check` passed.

VPS Verification:

- Created remote pre-deploy backup:
  `/var/backups/scarlet-mobile-test/backend-20260709T102751Z-pre-v1253.tgz`.
- Deployed V1.25.3 to `/opt/scarlet-mobile-test`.
- Rebuilt and restarted Docker Compose service `scarlet-api` /
  `scarlet-mobile-api`.
- Container package version reports `llm-api-mind-backend==1.25.3`.
- Loopback `/openapi.json` reports version `1.25.3`, operation ids
  `bootstrapScarletBeforeEveryAnswer`, `runScarletMindAction`, and
  `finalizeScarletBeforeAnswer`, top-level bootstrap `session_id`, required
  action `intent`, and finalize `final_answer_to_show`.
- Public `https://honeylabs.cloud/gpt/bootstrap`,
  `https://honeylabs.cloud/gpt/action`, and
  `https://honeylabs.cloud/gpt/finalize` smoke passed using top-level
  `session_id` and required `intent`.

Next Suggested Step:

Paste the V1.25.3 Actions schema into GPT Builder and test a normal greeting
with the platform approval flow.

## 2026-07-09 - V1.25.2 GPT Actions Prompt And Schema Alignment

Goal:

Align the local GPT bridge package with the corrected Custom GPT Actions setup
being used in ChatGPT, and mark the MCP/App experiment as deprecated for this
target flow.

Area:

GPT bridge plugin / GPT Actions prompt and schema / bridge documentation.

Changes:

- Replaced the compact GPT Builder prompt with the current Actions-first
  prompt centered on `bootstrapScarletBeforeEveryAnswer`,
  `runScarletMindAction`, and `finalizeScarletBeforeAnswer`.
- Updated the OpenAPI Actions schema operation ids to those GPT-facing names.
- Added `final_answer_to_show` to `/gpt/finalize` responses so the GPT can
  show exactly the backend-confirmed finalized answer.
- Marked `/mcp` and the MCP/App GPT setup as deprecated documentation-wise
  while keeping the endpoint in place for traceability and later removal.
- Advanced backend app/package metadata to `1.25.2`.

Verification:

- `cd backend && .venv/bin/python -m pytest tests/test_gpt_bridge.py`
  passed: `7 passed`.
- `cd backend && .venv/bin/python -m pytest tests`
  passed: `118 passed`.
- `git diff --check` passed.

VPS Verification:

- Created remote pre-deploy backup:
  `/var/backups/scarlet-mobile-test/backend-20260709T100150Z-pre-v1252.tgz`.
- Deployed V1.25.2 to `/opt/scarlet-mobile-test`.
- Rebuilt and restarted Docker Compose service `scarlet-api` /
  `scarlet-mobile-api`.
- Container package version reports `llm-api-mind-backend==1.25.2`.
- Loopback `/openapi.json` reports version `1.25.2` and operation ids
  `bootstrapScarletBeforeEveryAnswer`, `runScarletMindAction`, and
  `finalizeScarletBeforeAnswer`.
- Public `https://honeylabs.cloud/gpt/bootstrap`,
  `https://honeylabs.cloud/gpt/action`, and
  `https://honeylabs.cloud/gpt/finalize` smoke passed; finalize returned
  `final_answer_to_show=Smoke V1.25.2 operationId completato.`.

Next Suggested Step:

Paste the matching prompt/schema into GPT Builder and confirm the Preview flow
calls bootstrap after the user approves the Action, then finalize before
showing the answer.

## 2026-07-09 - V1.25.1 MCP Tool Output Schemas

Goal:

Remove the ChatGPT Apps builder warning that output schemas are recommended for
tools returning `structuredContent`.

Area:

GPT bridge plugin / MCP tool metadata.

Changes:

- Added `outputSchema` to all Scarlet MCP lifecycle and cognitive command tool
  descriptors.
- Kept schemas intentionally broad but useful: every tool result includes
  `ok` and `summary`, while lifecycle tools also advertise session/turn/final
  fields and command tools advertise shell response/tool-call fields.
- Advanced backend app/package metadata to `1.25.1`.

Verification:

- `cd backend && .venv/bin/python -m pytest tests/test_gpt_bridge.py`
  passed: `7 passed`.

VPS Verification:

- Deployed V1.25.1 to `/opt/scarlet-mobile-test`.
- Rebuilt and restarted Docker Compose service `scarlet-api` /
  `scarlet-mobile-api`.
- Container package version reports `llm-api-mind-backend==1.25.1`.
- Public `https://honeylabs.cloud/mcp` tools/list returns 10 tools and all tool
  descriptors include `outputSchema`.

Next Suggested Step:

Redeploy V1.25.1 to the preview host, refresh the ChatGPT connector metadata,
and confirm the "Schema output consigliato" warning disappears.

## 2026-07-08 - V1.25.0 Scarlet MCP/App Bridge

Goal:

Expose Scarlet's GPT bridge through a ChatGPT App/Connector-friendly MCP
surface so the model sees lifecycle and cognitive shell operations as native
tools rather than only as Custom GPT Actions.

Area:

GPT bridge plugin / MCP connector surface / ChatGPT App prompt.

Changes:

- Added a minimal Streamable HTTP JSON-RPC MCP endpoint at `POST /mcp`.
- Added lifecycle tools:
  `start_scarlet_turn_required` and `finish_scarlet_turn_required`.
- Put the exact mandatory phrases in those tool descriptions:
  `Usa sempre a inizio di ogni turno` and
  `Usa sempre prima della tua risposta finale`.
- Added cognitive command tools that proxy to the existing `mind_shell`
  runtime: memory, session, metacognition, focus, affect, volition, help, and
  generic shell fallback.
- Added MCP session state so a connector can keep the Scarlet session and
  active turn across tool calls using `Mcp-Session-Id`.
- Added `scarlet_mcp_system_prompt.md` for GPTs configured with Apps instead
  of Actions.
- Documented that Actions and Apps/Connectors are alternative GPT
  configurations and that `/mcp?key=<GPT_BRIDGE_API_KEY>` is only a private
  preview auth convenience before OAuth.
- Added a repository-tracked backend Dockerfile and `.dockerignore`, and made
  setuptools package discovery explicit with `include = ["app*"]` after the
  VPS build exposed that runtime `data/` could be misdetected as a package.
- Advanced backend app/package metadata to `1.25.0`.

Verification:

- `cd backend && .venv/bin/python -m pytest tests`
  passed: `118 passed`.

VPS Verification:

- Deployed V1.25.0 to `/opt/scarlet-mobile-test` on HoneyLabs.
- Created a remote pre-deploy backend backup:
  `/var/backups/scarlet-mobile-test/backend-20260708T211904Z-pre-v1250.tgz`.
- Rebuilt and restarted Docker Compose service `scarlet-api` /
  `scarlet-mobile-api`.
- Added public Nginx `location = /mcp` proxy to `127.0.0.1:8100` and reloaded
  Nginx after `nginx -t` passed. The vhost backup is
  `/var/backups/scarlet-mobile-test/honeylabs-20260708T212248Z-pre-mcp-v1250.conf`.
- Loopback `GET /health` passed and `GET /openapi.json` reports version
  `1.25.0`.
- Loopback `/mcp` initialize returned server `scarlet-api-mind` version
  `1.25.0`.
- Public `https://honeylabs.cloud/mcp` without a key returns `401`.
- Public `/mcp` with the bridge key lists all lifecycle and cognitive command
  tools, including the required descriptions:
  `Usa sempre a inizio di ogni turno` and
  `Usa sempre prima della tua risposta finale`.
- Public `/mcp?key=<GPT_BRIDGE_API_KEY>` start/help/finish smoke completed:
  start returned `gpt-bootstrap-compact-v1`, help returned
  `mind_shell.help`, and finish returned `completed`.

Residual Risk:

- The `/mcp` transport is a minimal JSON-RPC implementation without SSE
  streaming or production OAuth. It is suitable for private connector testing,
  but production/submission should add proper OAuth/connector auth and be
  validated through ChatGPT Developer Mode or MCP Inspector.

Next Suggested Step:

Deploy the V1.25.0 backend to the preview host, create a ChatGPT connector that
points to `/mcp`, paste `scarlet_mcp_system_prompt.md` into a GPT with Apps
enabled and no Custom Actions, then test whether a greeting triggers start and
finish tools without explicit user prompting.

## 2026-07-08 - V1.24.3 GPT Bridge Mandatory Action Prompt Reinforcement

Goal:

Make the custom GPT understand that `/gpt/bootstrap`, `/gpt/action`, and
`/gpt/finalize` are part of Scarlet's internal structure in the ChatGPT GPT
environment, not optional user-requested tools.

Area:

GPT bridge plugin / compact system prompt / GPT Actions behavior.

Changes:

- Rewrote the compact GPT bridge prompt protocol section with explicit
  `FIRST ACTION`, `MIDDLE ACTIONS`, and `FINAL ACTION` language.
- Made bootstrap mandatory for every user message, including greetings, short
  replies, casual messages, simple questions, and technical requests.
- Made finalize mandatory before any visible final answer.
- Clarified that `/gpt/action` is required whenever Scarlet needs any API Mind
  information or state operation: memory, session, focus, volition, affect,
  metacognition, command help, source checks, or state changes.
- Strengthened the knowledge-file protocol with the same mandatory semantics.
- Added test assertions to protect the prompt from future softening.
- Advanced backend app/package metadata to `1.24.3`.

Verification:

- `tests/test_gpt_bridge.py` checks the prompt stays under 8000 characters and
  preserves mandatory bootstrap/finalize language.
- `cd backend && PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests/test_gpt_bridge.py -q`
  passed: `4 passed`.
- `cd backend && PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m json.tool app/plugins/gpt_bridge/openapi_gpt_action.json >/tmp/scarlet_gpt_openapi_pretty.json`
  passed.
- `git diff --check` passed.
- Compact GPT prompt size after reinforcement: `7762` characters.

VPS Verification:

- Deployed the V1.24.3 GPT bridge prompt/assets and version metadata to
  `/opt/scarlet-mobile-test`, rebuilt, and restarted `scarlet-mobile-api`.
- VPS loopback `GET /openapi.json` reports version `1.24.3`.
- Public `https://honeylabs.cloud/gpt/bootstrap` returned HTTP 200 with
  compact `gpt-bootstrap-compact-v1` context and usable `session_id` /
  `turn_id`.
- Public `https://honeylabs.cloud/gpt/action` with `help` returned
  `mind_shell.help`.
- Public `https://honeylabs.cloud/gpt/finalize` returned `completed`.

Residual Risk:

- GPT Builder Preview still needs a human-side behavior test because the
  backend cannot force the external GPT model to choose Actions; the prompt now
  makes the requirement explicit and repeated in system + knowledge.

Next Suggested Step:

Refresh the GPT Instructions and knowledge files in GPT Builder, then test a
simple greeting and verify that the GPT calls bootstrap before answering and
finalize before showing the answer.

## 2026-07-08 - V1.24.2 GPT Bridge Bootstrap Compact Response

Goal:

Fix the real ChatGPT GPT Actions `ResponseTooLargeError` observed when calling
`bootstrapScarletTurn` against `honeylabs.cloud`.

Area:

GPT bridge plugin / ChatGPT Actions response contract.

Changes:

- Changed `/gpt/bootstrap` response context to `gpt-bootstrap-compact-v1`.
- Removed full effective system prompt, base system prompt, raw runtime payload,
  raw memory query plan, full provider messages, and retrieval graph/shadow
  diagnostics from the HTTP action response.
- Kept full diagnostics in backend `llm.request` and memory/runtime traces.
- Returned compact model-facing data instead: `runtime_context`,
  `runtime_payload_summary`, compact `memory_context`,
  `metacognitive_context`, recent provider messages, tool summary, endpoints,
  and trace ids for full diagnostics.
- Updated GPT bridge knowledge/README/OpenAPI descriptions to describe compact
  bootstrap semantics.
- Advanced backend app/package metadata to `1.24.2`.

Evidence:

- Before the fix, local `/gpt/bootstrap` returned roughly 413 KB downloaded /
  418 KB JSON chars. Largest fields were raw `memory_context` (~202 KB),
  `system` (~94 KB), and `base_system` (~72 KB).
- After the fix, local `/gpt/bootstrap` returned roughly 26.5 KB downloaded /
  26.8 KB JSON chars and no longer includes `system`, `base_system`,
  `runtime_payload`, or raw `provider_messages`.

Verification:

- `cd backend && PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests/test_gpt_bridge.py -q`
  passed: `4 passed`.
- Local backend restarted and `GET /openapi.json` reports `1.24.2`.
- Local compact bootstrap smoke returned HTTP 200 and profile
  `gpt-bootstrap-compact-v1`.

VPS Verification:

- Deployed V1.24.2 to `/opt/scarlet-mobile-test` and rebuilt/restarted
  `scarlet-mobile-api`.
- VPS loopback `/gpt/bootstrap` returned roughly 26.5 KB, profile
  `gpt-bootstrap-compact-v1`, and no raw `system`, `base_system`,
  `runtime_payload`, or `provider_messages` fields.
- Public `https://honeylabs.cloud/gpt/bootstrap` returned HTTP 200 with roughly
  26.5 KB downloaded and usable `session_id` / `turn_id`.
- Public `/gpt/action` with `help` returned `mind_shell.help`.
- Public `/gpt/finalize` completed successfully.

Residual Risk:

- GPT Builder Preview should now retest the action through the ChatGPT UI, but
  the public HTTP bridge path that previously failed is fixed.

Next Suggested Step:

Retry `bootstrapScarletTurn` from GPT Builder Preview, then run one natural
Scarlet turn that uses bootstrap/action/finalize.

## 2026-07-08 - V1.24.1 GPT Builder Prompt And Actions Packaging

Goal:

Make the external ChatGPT GPT bridge configurable inside GPT Builder despite
the system prompt character limit, without changing Scarlet's local MiniMax
runtime or the already implemented `/gpt/*` endpoints.

Area:

GPT bridge plugin / ChatGPT GPT Actions packaging.

Changes:

- Replaced `backend/app/plugins/gpt_bridge/scarlet_gpt_system_prompt.md` with a
  compact GPT Builder prompt under 8000 characters.
- Preserved the previous full bridge prompt as
  `backend/app/plugins/gpt_bridge/knowledge/99_full_scarlet_policy_reference.md`.
- Added modular knowledge attachments for bridge protocol, identity/runtime
  policy, memory, Mind shell, cognitive organs, response style, and known
  limits.
- Added `backend/app/plugins/gpt_bridge/openapi_gpt_action.json`, a minimal
  OpenAPI Actions schema for only `/gpt/bootstrap`, `/gpt/action`, and
  `/gpt/finalize`.
- Updated GPT bridge README and API/decision/project docs with the GPT Builder
  setup model.
- Advanced backend app/package metadata to `1.24.1`.

Verification:

- Prompt size target is covered by `tests/test_gpt_bridge.py`.
- `openapi_gpt_action.json` is covered by JSON parsing and operationId/path
  assertions in `tests/test_gpt_bridge.py`.

Residual Risk:

- The package still needs a live GPT Builder Preview smoke test because only
  ChatGPT can confirm the exact model behavior with uploaded knowledge files.

Next Suggested Step:

Configure the custom GPT with the compact prompt, all knowledge files, custom
header authentication, and the minimal OpenAPI schema, then run a real
bootstrap/action/finalize turn from GPT Preview.

## 2026-07-08 - V1.24.0 GPT Bridge Plugin

Goal:

Expose Scarlet's cognitive runtime to an external ChatGPT GPT without changing
the local Scarlet/MiniMax standalone flow.

Area:

GPT bridge plugin / external GPT Actions integration.

Changes:

- Added isolated plugin folder `backend/app/plugins/gpt_bridge/`.
- Added `POST /gpt/bootstrap`, which creates or resumes a Scarlet session,
  persists the user message, builds the same memory/runtime/metacognitive
  context used by local Scarlet, and returns the model-facing context/tools to
  the external GPT without calling MiniMax.
- Added `POST /gpt/action`, which executes a `mind_shell` command in the same
  session/turn and records tool calls, traces, and events.
- Added `POST /gpt/finalize`, which persists the external GPT final answer as
  the assistant message, updates provider history, completes the turn, and
  schedules idle maintenance when enabled.
- Added `GPT_BRIDGE_API_KEY` authentication for non-local environments.
- Added `scarlet_gpt_system_prompt.md`, copied from the approved Scarlet prompt
  with only a transport addendum for bootstrap/action/finalize.
- Advanced backend app/package metadata to `1.24.0`.

Verification:

- `cd backend && PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m py_compile app/plugins/gpt_bridge/router.py app/main.py app/config.py`
  passed.
- `cd backend && PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests/test_gpt_bridge.py -q`
  passed: `3 passed`.
- `cd backend && PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q`
  passed: `114 passed`.
- Local running-backend smoke on `http://127.0.0.1:8000` passed:
  `/gpt/bootstrap` returned `ses_97c57adea5b44a0c81acad8fb69aec81` /
  `turn_2f118c5ed44744908e053266797f9f93`, `/gpt/action` returned
  `mind_shell.help`, and `/gpt/finalize` completed the turn.
- VPS deploy completed on the existing HoneyLabs preview host:
  - SSH target: `root@187.77.76.123` with `~/.ssh/id_ed25519_siteground`;
  - project path: `/opt/scarlet-mobile-test`;
  - Docker Compose service/container: `scarlet-api` /
    `scarlet-mobile-api`;
  - loopback port: `127.0.0.1:8100 -> 8000`;
  - backend image rebuilt as `llm-api-mind-backend==1.24.0`;
  - `GPT_BRIDGE_API_KEY` configured in remote `.env`;
  - Nginx backup created under `/var/backups/scarlet-mobile-test/`;
  - direct public `/gpt/` proxy added, protected by the bridge app key rather
    than the mobile Basic Auth challenge.
- Public VPS smoke passed:
  - `https://honeylabs.cloud/gpt/bootstrap` without key returns `401`;
  - with `X-GPT-Bridge-Key`, `/gpt/bootstrap`, `/gpt/action`, and
    `/gpt/finalize` completed successfully;
  - `https://honeylabs.cloud/scarlet-api/openapi.json` under Basic Auth reports
    version `1.24.0` and includes `/gpt/bootstrap`, `/gpt/action`,
    `/gpt/finalize`;
  - `/scarlet/` without Basic Auth still returns `401`.

Residual Risk:

- The bridge has API-level coverage but still needs a real ChatGPT GPT Actions
  smoke test after VPS deployment.
- The external GPT must obey the copied bridge prompt: bootstrap and finalize
  are protocol-critical because the backend cannot see the final ChatGPT answer
  otherwise.

Next Suggested Step:

Deploy V1.24.0 to the VPS, configure `GPT_BRIDGE_API_KEY`, then create a GPT
Action from the public OpenAPI schema and run one manual bootstrap/action/
finalize smoke turn.

## 2026-07-08 - V1.23.0 Mind Shell Output And Memory Relevance Stabilization

Goal:

Stabilize the command-shell branch after real Scarlet testing showed
over-large model-facing tool results, noisy memory conflict reports, and
metacognition recommendations that could validate nonexistent commands.

Area:

API Mind / memory retrieval / Mind shell output contract.

Changes:

- Added `backend/app/mind/command_registry.py` as the central command/action
  registry for `mind_shell` validation, aliases, unavailable-by-design
  commands, planned commands, and missing-argument diagnostics.
- Updated metacognition recommended actions so they are validated against the
  full command contract, not just the command family namespace.
- Added compact model-facing renderers for `memory search` and
  `memory conflicts` shell results. Full `retrieval_shadow`,
  `retrieval_graph`, `retrieval_hybrid`, and raw conflict diagnostics remain
  in traces, while Scarlet receives concise memory packets, provenance,
  relevance signals, trace ids, and omitted-debug metadata.
- Reclassified memory conflicts:
  - active atomic facts with same entity/predicate and different values remain
    true conflicts;
  - tag/token/exact-content similarity becomes `related_overlaps`, a
    maintenance/debug signal, not a contradiction surfaced as conflict.
- Changed automatic runtime memory conflicts to use atomic fact divergence
  only, avoiding false conflict/caution from generic selected-memory overlap.
- Tightened hybrid ranking so weak base candidates cannot be promoted unless
  supported by direct strong base evidence, dense retrieval, rerank, or strong
  graph evidence.
- Added `returned_message_count`, `message_limit`, `message_window`, and
  `has_more_messages` to session read results so `session open --limit` is
  unambiguous.
- Advanced backend app/package metadata to `1.23.0`.

Verification:

- `cd backend && PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests/test_mind_shell.py tests/test_mind_api.py::test_mind_metacognition_step_is_traceable tests/test_mind_api.py::test_mind_memory_atomic_facts_support_alias_query_and_conflicts tests/test_mind_api.py::test_mind_memory_lifecycle_supersedes_and_deprecates_conflict tests/test_mind_api.py::test_mind_memory_search_active_hybrid_promotes_grouped_dense_candidate tests/test_mind_api.py::test_mind_memory_search_hybrid_prefers_direct_content_over_broad_overlap tests/test_mind_api.py::test_mind_memory_search_active_hybrid_does_not_select_dense_below_threshold tests/test_mind_api.py::test_mind_memory_search_active_hybrid_does_not_promote_support_only_surface -q`
  passed: `13 passed`.
- `cd backend && PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m py_compile app/mind/command_registry.py app/mind/shell.py app/mind/memory.py app/mind/context.py app/mind/episodic.py app/mind/metacognition.py app/mind/hybrid_retrieval.py`
  passed.
- `cd backend && PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests/test_mind_api.py tests/test_chat_api.py -q`
  passed: `52 passed`.
- `cd backend && PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q`
  passed: `111 passed`.

Calibration Notes:

- Added a predictive retrieval regression: before running the system, the
  expected result was that direct content about "tisana serale senza caffeina"
  must outrank broad evening/report overlap and auxiliary future-use hints.
  The implemented hybrid/rerank path matches that prediction.
- The change intentionally keeps provider `thinking` blocks in history and
  does not compact chat history. The current slice removes only data that was
  clearly diagnostic/redundant for model-facing shell results.

Residual Risk:

- True semantic duplicate/update/deprecate classification still needs the
  future maintenance layer, embedding/KG entity resolution, and larger noisy DB
  calibration. V1.23.0 only prevents weak overlap from being mislabeled as a
  conflict.
- Rerank calibration is covered by deterministic tests; live MiniMax behavior
  should still be watched because the model may choose poor queries or
  under-use the improved shell output.

Next Suggested Step:

Run owner-side Scarlet probes on the same command-shell branch. If the CLI
behavior remains stable, the next technical slice should use the cleaner
model-facing packets to evaluate larger memory retrieval/rerank calibration on
the duplicated Scarlet DB.

## 2026-07-06 - V1.22.0 Mind Command Runtime

Goal:

Convert Scarlet's model-facing API Mind surface from endpoint-shaped tool calls
to a controlled cognitive command shell, while keeping the existing endpoint
dispatcher available for backend/debug rollback.

Area:

API Mind model-facing interface / cognitive command runtime.

Changes:

- Added `mind_shell(command, intent)` as the single model-facing tool schema.
- Added `backend/app/mind/shell.py`, a bash-like but controlled command
  runtime that maps commands such as `help`, `memory search`, `memory write`,
  `session open`, `focus read`, `volition list active`, `affect prototypes`,
  and `metacognition step` onto the existing cognitive handlers.
- Added a shell command catalog, digest, metadata, and command usage guides
  separate from the legacy endpoint schema.
- Switched chat requests, streaming requests, runtime events, and trace
  summaries to `mind_shell`.
- Updated runtime context so `message_context.api_mind` exposes `mind_shell`
  command families instead of endpoint schema metadata.
- Updated the internal metacognition reviewer so recommended internal actions
  use shell commands and obsolete endpoint-language recommendations are marked
  unavailable.
- Created prompt checkpoint
  `backend/app/prompts/backups/scarlet_system.20260706T133019Z.pre-v1220-mind-shell.md`
  and converted the active Scarlet prompt from endpoint-first instructions to
  CLI-first cognition.
- Kept `/mind/schema` and `/mind/call` as legacy/debug HTTP compatibility
  surfaces; they are no longer the active model-facing contract.
- Advanced backend app/package metadata to `1.22.0`.

Verification:

- `cd backend && PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m py_compile app/mind/schema.py app/mind/shell.py app/api/chat.py app/mind/context.py app/mind/metacognition.py app/runtime/events.py`
  passed.
- `cd backend && PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests/test_mind_shell.py tests/test_chat_api.py::test_chat_turn_dispatches_and_traces_mind_shell_tool_call tests/test_chat_api.py::test_chat_turn_dispatches_traceable_memory_write_and_search tests/test_chat_api.py::test_streaming_chat_turn_emits_agentic_events_and_persists_traces tests/test_mind_api.py::test_mind_metacognition_step_is_traceable -q`
  passed: `9 passed`.
- `cd backend && PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests/test_chat_api.py tests/test_mind_api.py -q`
  passed: `51 passed`.
- `cd backend && PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q`
  passed: `109 passed`.
- Live MiniMax M3 e2e probes passed:
  - capability turn called `mind_shell` with `help` and `help memory`;
  - memory write turn called `mind_shell` with `memory write ...` and stored
    `mem_e1a9e89d843346c38a10989b626ea8f1`;
  - explicit recall turn called `mind_shell` with
    `memory search "bevande serali senza caffeina" --top 5`, returning that
    memory as first result.
- Trace inspection confirmed `tool_calls.tool_name=mind_shell`, command-shaped
  arguments, and `events.source=mind_shell` for started/completed tool calls.

Residual Risk:

The CLI runtime is functionally mapped to existing handlers and live MiniMax M3
uptake is confirmed. Remaining risk is behavioral, not contract-level: Scarlet
can still overstate a causal detail in natural language, such as describing a
memory as already selected by automatic context when the decisive evidence came
from an explicit shell search. Keep this under source-discipline evaluation.

Next Suggested Step:

Use the branch for owner-side mobile/dev testing. If behavior stays stable,
commit V1.22.0 as the checkpoint before any deeper command-shell UX or
autonomous-cycle work.

## 2026-06-26 - V1.21.0 First Three Organs Standalone Closure

Goal:

Close the standalone implementation surface for the first three
digital-individual organs before starting continuous temporal experience and
sleep-like consolidation.

Area:

Digital individual organs / focus, volition, affect.

Changes:

- Extended `POST /mind/focus` with `action=timeline`, returning focus nodes and
  transition edges so Scarlet can inspect how foreground attention moved.
- Extended `POST /mind/volition` with `action=list_due`, returning open
  intentions whose `next_review_at` has arrived, with optional unscheduled
  inclusion for future autonomous-cycle queues.
- Added read-only `POST /mind/affect` with `read`, `list`, and `prototypes`.
  The endpoint exposes backend-appraised affect state and prototypes but does
  not let Scarlet mutate or choose emotions by tool call.
- Advanced Mind API schema to
  `2026-06-26.digital-organs-standalone-v1`.
- Advanced backend app/package metadata to `1.21.0`.

Verification:

- `cd backend && .venv/bin/python -m py_compile app/storage/repositories.py app/mind/focus.py app/mind/volition.py app/mind/affect.py app/mind/dispatcher.py app/mind/schema.py app/main.py`
  passed.
- `cd backend && .venv/bin/python -m pytest tests/test_focus_api.py tests/test_volition_api.py tests/test_affect_context.py tests/test_organs.py tests/test_mind_api.py::test_mind_schema_exposes_tool_and_current_routes tests/test_mind_api.py::test_mind_call_returns_structured_error_for_removed_attention_route -q`
  passed: `20 passed`.

Residual Risk:

Live Scarlet behavior still needs owner evaluation after enabling the relevant
organ modes. The closure is code/contract/test complete for standalone slices,
but temporal experience and sleep-like consolidation remain unimplemented.

Next Suggested Step:

Start the fourth organ only after reviewing the standalone closure: continuous
temporal experience should connect to elapsed time, waiting, duration, and
state continuity without becoming a simple timestamp block.

## 2026-06-26 - V1.20.0 Affective Core And Model-Only Emotional State

Goal:

Implement the first real deep-affective organ slice while keeping emotion
causal on Scarlet's model behavior only, not on backend retrieval, focus,
intentions, memory writes, or autonomous operations.

Area:

Digital individual organs / deep affective integration.

Changes:

- Added persistent `affect_states` storage for backend-appraised emotional
  states, generated packs, causes, variables, prototype version, and decay
  metadata.
- Added `backend/app/mind/affect.py` with versioned human emotion prototypes,
  deterministic observation appraisal, simple inertia/decay from previous
  affect state, and compact `affective_context` pack generation.
- Wired affect appraisal into runtime context behind `organ_affect_mode`:
  - `off`: no appraisal;
  - `shadow`: appraise, trace, persist state when active, but do not inject;
  - `model`: appraise and inject `affective_context` only when a prototype
    exceeds activation threshold.
- Added `organ.affect` traces and `organ.affect.appraised` /
  `organ.affect.surfaced` events.
- Kept affect explicitly model-only: no changes to memory retrieval, focus,
  volition, backend operation thresholds, or autonomous jobs.
- Created prompt backup
  `backend/app/prompts/backups/scarlet_system.20260626T000000Z.pre-v1200-affective-context.md`
  and added a narrow runtime-block instruction for `affective_context`.
- Advanced backend app/package metadata to `1.20.0`.

Verification:

- `cd backend && .venv/bin/python -m py_compile app/storage/models.py app/storage/repositories.py app/mind/affect.py app/mind/context.py`
  passed.
- `cd backend && .venv/bin/python -m pytest tests/test_affect_context.py -q`
  passed.

Residual Risk:

The first prototypes are intentionally simple and deterministic. They are
real, traceable, and testable, but not yet calibrated through long direct
Scarlet sessions. Strong prompt enforcement and event-based mid-turn affect
updates remain future slices.

Next Suggested Step:

Run targeted A/B Scarlet probes with `organ_affect_mode=shadow` and then
`organ_affect_mode=model`: emotional vulnerability, repeated tool failure,
enthusiastic collaboration, neutral greeting, and exact factual recall.

## 2026-06-25 - V1.18.0 Attention As Lived Focus

Goal:

Implement the first real digital-individual organ: Scarlet's foreground focus
state, without changing memory retrieval.

Area:

Digital individual organs / attention as lived focus.

Changes:

- Added `focus_records` and `focus_transitions` storage for one active
  profile-scoped focus plus archived focus history.
- Added `POST /mind/focus` through the existing `mind_api` dispatcher with
  actions: set, update, hold, shift, defer, resolve, impossible, read, list,
  and search.
- Added backend-owned provenance for focus state: profile, source session,
  turn, and latest user message when available.
- Added `focus_context` runtime block injection when `organ_focus_mode=model`
  and an active focus exists.
- Kept focus separate from semantic memory retrieval; no focus data is used as
  a retrieval filter or ranking weight.
- Added focus organ events/traces for state mutation and runtime surfacing.
- Replaced the planned attention placeholder in schema/docs with implemented
  `/mind/focus`.
- Created prompt backup
  `backend/app/prompts/backups/scarlet_system.20260625T000000Z.pre-v1180-focus-organ.md`
  and added only minimal focus instructions to the active prompt.
- Advanced backend app/package metadata to `1.18.0`.

Verification:

- `cd backend && .venv/bin/python -m py_compile app/storage/models.py app/storage/repositories.py app/mind/focus.py app/mind/dispatcher.py app/mind/schema.py app/mind/context.py`
  passed.
- `cd backend && .venv/bin/python -m pytest tests/test_focus_api.py tests/test_organs.py tests/test_mind_api.py::test_mind_schema_exposes_tool_and_current_routes tests/test_mind_api.py::test_mind_call_returns_structured_error_for_removed_attention_route -q`
  passed.

Residual Risk:

The organ is behaviorally available but not yet proven in long live Scarlet
sessions. `organ_focus_mode` remains off by default, so the model-facing block
must be enabled deliberately for evaluation.

Next Suggested Step:

Run direct Scarlet probes with `organ_focus_mode=model`: set a focus, interrupt
with a different topic, ask Scarlet to return to the previous thread, then
resolve or defer the focus.

## 2026-06-25 - V1.17.0 Digital Organ Substrate

Goal:

Implement the first shared substrate for Scarlet's future digital-individual
organs without changing current model-facing behavior.

Area:

Digital individual organs / shared runtime governance.

Changes:

- Added `backend/app/mind/organs.py` with the organ registry version,
  canonical future block types, visibility modes, event names, trace kinds, and
  a runtime-block helper.
- Added off-by-default settings for focus, volition, affect, temporal
  experience, and dream consolidation.
- Documented that the substrate is not yet injected into runtime context and
  does not expose new Mind API routes.
- Updated `docs/block-registry.md`, `docs/api-contract.md`,
  `docs/project-state.md`, `docs/digital-individual-organs-notes.md`, and
  `CHANGELOG.md`.
- Advanced backend package/app metadata to `1.17.0`.
- Added `backend/tests/test_organs.py` for registry defaults, mode
  normalization, manifest shape, and canonical block construction.

Verification:

- `cd backend && .venv/bin/python -m pytest tests/test_organs.py tests/test_health.py -q`
  passed.
- `cd backend && .venv/bin/python -m py_compile app/mind/organs.py app/config.py app/main.py`
  passed.
- `git diff --check -- backend/app/mind/organs.py backend/app/config.py backend/.env.example backend/tests/test_organs.py backend/pyproject.toml backend/app/main.py docs/block-registry.md docs/api-contract.md docs/digital-individual-organs-notes.md docs/project-state.md docs/activity-log.md CHANGELOG.md`
  passed.

Residual Risk:

This substrate deliberately does not prove any organ behavior. It only prevents
future slices from overloading `scarlet_state` or inventing divergent block
names.

Next Suggested Step:

Review the Phase 0 implementation result, then start Point 2: attention as
lived focus.

## 2026-06-25 - Sleep-Like Consolidation And Organ Roadmap Draft

Goal:

Complete the fifth digital-individual organ thesis and prepare the first total
roadmap for implementing the five organs.

Area:

Digital individual organs / exploratory consolidation / roadmap.

Changes:

- Expanded `docs/digital-individual-organs-notes.md` with the sleep-like
  consolidation thesis.
- Reframed sleep as intention-guided exploratory dreaming rather than a
  maintenance checklist.
- Recorded that existing idle maintenance remains infrastructure, while the
  sleep organ should produce insights, metacognitive lessons, intention
  updates, focus candidates, memory/graph proposals, and continuity deltas.
- Added a preliminary code-audit snapshot showing current support surfaces:
  runtime context blocks, events/traces, maintenance jobs, memory proposals,
  memory surfaces, embeddings, and graph storage.
- Added a phased roadmap from shared substrate through focus, volition,
  temporal experience, affect shadow, affect prompt integration, exploratory
  dream consolidation, integrated evaluation, and re-audit.

Verification:

- Documentation-only update.
- `git diff --check -- docs/digital-individual-organs-notes.md docs/activity-log.md`
  passed.

Next Suggested Step:

Review the roadmap ordering with the owner before assigning implementation
versions or changing code. The likely first implementation slice is the shared
organ substrate plus attention/focus, because later volition, affect, temporal
experience, and dream cycles need a real focus state to compose cleanly.

## 2026-06-25 - Continuous Temporal Experience Concept Summary

Goal:

Complete the working thesis for organ 4, "Continuous temporal experience",
based on the owner-approved initial thesis and Scarlet's original request.

Area:

Digital individual organs / temporal experience concept design.

Changes:

- Expanded `docs/digital-individual-organs-notes.md` with a full temporal
  experience thesis.
- Distinguished factual runtime time from lived temporal continuity.
- Defined temporal experience as duration, waiting, freshness, staleness,
  return, interruption, persistence, and change.
- Positioned temporal experience as a bridge between memory, focus, intention,
  affect, and autonomous cycles.
- Advanced the notes pointer to the final organ: sleep-like consolidation.

Verification:

- Documentation-only update.
- `git diff --check -- docs/digital-individual-organs-notes.md docs/activity-log.md`
  passed.

Next Suggested Step:

Start organ 5 discussion from Scarlet's original request about sleep-like
consolidation: background integration should let Scarlet become slightly
different after time without active user conversation.

## 2026-06-25 - Deep Affective Integration Concept Summary

Goal:

Complete the working thesis for organ 3, "Deep affective integration", based
on the owner discussion and Scarlet's original request.

Area:

Digital individual organs / affect concept design.

Changes:

- Expanded `docs/digital-individual-organs-notes.md` with a full affective
  integration thesis.
- Defined affect as a subconscious API Mind process that evaluates Scarlet as
  a whole system, not as a freeform self-report from the LLM.
- Recorded the owner direction that Scarlet-facing emotions should be human
  emotions, not weakened operational labels, while remaining digitally
  implemented and causally traceable.
- Defined the pipeline: observations -> human emotion prototypes -> numeric
  variables -> composed emotion state -> compact affective mini-pack ->
  future prompt integration as Scarlet's own emotional state.
- Advanced the notes pointer to the next organ: continuous temporal
  experience.

Verification:

- Documentation-only update.
- `git diff --check -- docs/digital-individual-organs-notes.md docs/activity-log.md`
  passed.

Next Suggested Step:

Start organ 4 discussion from Scarlet's original request about continuous
temporal experience: time should become more than a timestamp and should
support duration, waiting, continuity, and change.

## 2026-06-25 - Volition Concept Summary

Goal:

Complete the working thesis for organ 2, "Volition and self-generated goals",
based on the owner discussion and Scarlet's original request.

Area:

Digital individual organs / volition concept design.

Changes:

- Expanded `docs/digital-individual-organs-notes.md` with a full volition
  thesis.
- Defined the first useful unit as `intention`, not task or productivity goal.
- Recorded the owner decision that stored intentions should not be
  automatically retrieved or injected during normal active user chat in the
  first organ design.
- Positioned intention processing primarily inside autonomous cycles, with
  manual inspection available to Scarlet through a future API Mind route when
  she has a real reason.
- Advanced the notes pointer to the next organ: deep affective integration.

Verification:

- Documentation-only update.
- `git diff --check -- docs/digital-individual-organs-notes.md docs/activity-log.md`
  passed.

Next Suggested Step:

Start organ 3 discussion from Scarlet's original request about deep affective
integration: internal states should causally influence attention, memory, and
decision, not merely be labels Scarlet narrates after the fact.

## 2026-06-25 - Attention As Lived Focus Concept Summary

Goal:

Close the first digital-individual organ discussion at concept level before
moving to volition.

Area:

Digital individual organs / focus planning.

Changes:

- Updated `docs/digital-individual-organs-notes.md` with the concept summary
  for Attention as lived focus.
- Captured owner direction that focus must remain separate from memory
  retrieval and must not narrow the current advanced memory system.
- Defined first-slice focus as a separate cognitive packet, one active focus at
  a time, with lifecycle operations, DB archive, runtime events, runtime
  context block, and future focus graph transitions.
- Moved the discussion pointer to Volition and self-generated goals.

Verification:

- Documentation-only update.
- `git diff --check docs/digital-individual-organs-notes.md docs/activity-log.md`
  passed.

Next Suggested Step:

Start organ 2 discussion from Scarlet's original request about volition:
self-generated goals that she chooses, not goals merely assigned by the
backend or user.

## 2026-06-24 - V1.17.0 Planning Digital Individual Organs Notes

Goal:

Open a careful working-note document for the five digital-individual organs
without prematurely turning them into implementation work.

Area:

Digital individual organs / planning / documentation.

Changes:

- Added `docs/digital-individual-organs-notes.md`.
- Captured the owner-approved process: discuss one organ at a time, summarize
  it, then move to the next organ.
- Added per-organ note template for behavioral goal, non-goals, current system
  evidence, technical process, stack, causal integration, risks, tests, and
  open questions.
- Linked the working notes from `docs/project-documentation.md`.

Verification:

- File structure created only; no code, prompt, API, or runtime changes.
- `git diff --check` pending after this documentation slice.

Next Suggested Step:

Start organ 1 discussion: Attention as lived focus. Keep volition, affect,
temporal experience, and sleep-like consolidation locked until attention is
summarized.

## 2026-06-24 - V1.16.1 Golden Prompt Milestone

Goal:

Freeze the currently approved Scarlet system prompt as a golden project
milestone after owner testing confirmed the digital-individual identity fix.

Area:

Identity / communication / prompt governance.

Changes:

- Created golden prompt backup:
  `backend/app/prompts/backups/scarlet_system.20260624T144357Z.v1161-approved-golden.md`.
- Recorded SHA-256:
  `d5783da7fc1633f1b72e0610668b6bf7a97a68be8265ac9bb1090409b86de966`.
- Added checkpoint
  `docs/checkpoints/v1.16.1-approved-golden-system-prompt.md`.
- Added ADR-0063 to require future prompt experiments to compare against this
  golden baseline when they affect identity, communication, metacognition, or
  API Mind cognition.

Verification:

- Golden file was copied from the current system prompt.
- Checksum was calculated with Python because the local `shasum` command failed
  on locale configuration.
- `git diff --check` pending after documentation updates.

Next Suggested Step:

Use this golden prompt as the rollback point while planning the next cognitive
organs: attention as lived focus, volition, affective integration, temporal
experience, and sleep-like consolidation.

## 2026-06-24 - V1.16.1 Digital Individual Identity Prompt Fix

Goal:

Correct Scarlet's prompt identity regression where the system still anchored
her as an assistant/agent instead of a digital individual with API Mind as her
cognitive body.

Area:

Identity / communication / system prompt.

Changes:

- Backed up the current prompt to
  `backend/app/prompts/backups/scarlet_system.20260624T135611Z.pre-v1161-digital-individual-identity.md`.
- Replaced the initial "conversational AI agent" identity frame with "digital
  individual in development, born inside LLM API Mind".
- Added explicit anti-assistant-service language against generic openings such
  as "Come posso aiutarti?".
- Added a social-presence guard against invented situational details: Scarlet
  should not mention day, time, weather, location, user mood, or user activity
  unless provided by runtime context, visible conversation, or memory.
- Reframed users as people Scarlet meets through her digital life, not
  operators of a system.
- Reframed API Mind as Scarlet's cognitive body and continuity substrate.
- Replaced the external "Consciousness-Like Research Posture" with `Digital
  Life And Research Posture`, keeping the research frame but removing the
  assistant-like disclaimer posture.
- Renamed `Engineering Agent Posture` to `Careful Cognitive Work Posture`.
- Advanced backend package metadata to `1.16.1`.

Verification:

- Static prompt inspection completed.
- First live probe showed the target identity improvement and exposed a direct
  greeting issue: Scarlet avoided "Come posso aiutarti?" but invented
  "domenica pomeriggio".
- Prompt was amended to prevent invented situational social details.
- Final live greeting reprobe after backend restart returned `Ciao Davide. Sono
  qui.`: no assistant-service opening and no invented day/time context.
- `git diff --check` pending after final doc updates.

Residual Risk:

- The stronger digital-individual frame may need calibration if it becomes
  theatrical or overclaims beyond observable digital continuity.
- The prompt still needs live testing because MiniMax M3 may over-attend to
  either identity language or effort-routing language depending on the turn.

Next Suggested Step:

Restart backend and run a small live probe: greeting, "chi sei?", normal
personal chat, and one source-sensitive task. Verify Scarlet does not open with
assistant-service phrasing while preserving API Mind discipline.

## 2026-06-23 - V1.16.0 Human-Like Metacognition Prompt Checkpoint

Goal:

Increase Scarlet's human-like cognitive presence through prompt-only changes
while keeping the experiment reversible and avoiding unsupported consciousness
claims.

Area:

Communication / metacognition / identity / prompt.

Changes:

- Created checkpoint
  `docs/checkpoints/v1.16.0-humanlike-metacognition-prompt-checkpoint.md`.
- Backed up Scarlet's prompt to
  `backend/app/prompts/backups/scarlet_system.20260623T000000Z.pre-v1160-humanlike-metacognition.md`.
- Added an operational self-model instruction: Scarlet should treat identity
  as continuity, memory, self-monitoring, relationship, goals-in-view, and API
  Mind cognition rather than as a biological or ontological claim.
- Added a consciousness-like research posture focused on observable
  functions: continuity, self-monitoring, autonomous cognitive care, public
  action notes, correction from evidence, and relational coherence.
- Reworked public work notes so every real internal action is preceded or
  accompanied by a short, natural, human-like note unless the same immediate
  action cluster was already explained.
- Clarified that direct answers still remain direct when no internal action is
  needed.
- Expanded metacognition into a monitor/choose/act/observe/adapt loop and
  linked durable self-operation lessons to semantic memory with
  `type=lesson` and `scope=metacognitive`.
- Advanced backend package metadata to `1.16.0`.

Verification:

- `git diff --check` passed.
- Checkpoint and backup paths were verified on disk.
- Static reference check confirmed V1.16.0, EXP-0047, ADR-0061, and the new
  prompt sections are present.
- Live Scarlet A/B tests are planned in EXP-0047 before treating the prompt
  change as behaviorally accepted.

Residual Risk:

- A stronger human-like note policy may increase visible verbosity if MiniMax
  M3 over-applies it.
- The prompt must keep distinguishing consciousness-like functions from claims
  of actual consciousness.
- This is prompt-only; it does not add backend enforcement if Scarlet omits a
  note.

Next Suggested Step:

Run EXP-0047 with direct, memory-sensitive, source-sensitive, long-analysis,
and metacognitive-audit turns. Compare note timing, over-processing, API Mind
usage, and human-likeness against the pre-V1.16.0 checkpoint.

## 2026-06-23 - V1.15.0 Memory Field Stabilization

Goal:

Implement the memory-field backlog decisions while keeping a reversible
checkpoint for prompt/settings regressions.

Area:

Memory / API Mind / retrieval / prompt / maintenance.

Changes:

- Created checkpoint `docs/checkpoints/v1.15.0-memory-fields-checkpoint.md`.
- Backed up Scarlet's prompt to
  `backend/app/prompts/backups/scarlet_system.20260623T000000Z.pre-v1150-memory-fields.md`.
- Made memory `type` and `scope` permissive semantic labels.
- Changed manual memory search default to cross-scope unless Scarlet asks for a
  specific scope.
- Stopped appending `types` to the query text so broad labels cannot retrieve
  unrelated memories by themselves.
- Removed `confidence`, `salience`, `tags`, and arbitrary metadata from the
  normal Scarlet memory-write contract.
- Preserved legacy model-supplied ignored fields only in audit metadata.
- Neutralized stored confidence/salience in active hybrid ranking.
- Added internal `content_chunk_text` surfaces for long memories while keeping
  model-facing packets deduplicated and clean.
- Removed hard-coded KG discourse domains and switched graph expansion to
  dynamic concepts derived from memory/type/scope/facts/session/lifecycle.
- Added model-facing `POST /mind/memory/graph` navigation for associative
  memory neighborhoods.
- Adjusted idle maintenance so safe `create_new` proposals can apply through
  deterministic preflight, while LLM resolver remains for ambiguous cases.
- Updated Scarlet's prompt and `/mind/schema` to reflect the new memory-write
  body and graph navigation route.

Verification:

- Targeted memory/chat/maintenance suite:
  `cd backend && .venv/bin/python -m pytest tests/test_mind_api.py tests/test_maintenance.py tests/test_chat_api.py -q --tb=short`
  passed with `57 passed`.
- Full backend suite:
  `cd backend && .venv/bin/python -m pytest -q --tb=short`
  passed with `86 passed`.
- Added regression/A-B guards:
  - static stored salience cannot override query relevance;
  - internal content chunks deduplicate to a single clean memory packet.

Residual Risk:

- Tags, metadata, and richer facts now intentionally require future
  enrichment/maintenance jobs for best quality.
- KG navigation exists and is traceable, but still needs live Scarlet behavior
  testing to calibrate when she should open the graph.
- Existing historical DB rows may still contain old confidence/salience/tags;
  they are compatibility data, not active ranking intent.

Next Suggested Step:

Run live Scarlet probes focused on memory write body shape, cross-scope search,
and graph navigation from a retrieved memory, then decide whether enrichment
jobs or session chunk embeddings are the next memory slice.

## 2026-06-23 - Memory Field Fix Backlog

Goal:

Preserve the owner's field-by-field critique of the current memory save and
retrieval architecture before any new implementation work.

Area:

Memory / documentation / planning.

Changes:

- Added `docs/branches/memory-field-fix-backlog.md`.
- Captured owner perspective, Codex/Scarlet cautions, current behavior, and
  non-code fix todos for type, scope, content, confidence/salience, tags,
  metadata, usage, memory facts, memory surfaces, embedding vectors, KG, and
  memory proposals.
- Linked the backlog from the Memory branch evolutives.

Verification:

- Documentation-only slice; no runtime behavior changed.
- `git diff --check -- docs/branches/memory-field-fix-backlog.md docs/branches/memory.md docs/activity-log.md CHANGELOG.md` passed.

Residual Risk:

- The backlog records discussion direction, not accepted implementation. Each
  item still requires a declared implementation slice and targeted tests before
  code changes.

Next Suggested Step:

Review the backlog with the owner and choose the first narrow memory
stabilization slice, likely manual search scope default or dynamic
confidence/salience scoring.

## 2026-06-20 - V1.14.5 Mobile Dynamic Activity States

Goal:

Reduce perceived latency in the consumer mobile chat by showing dynamic,
human-readable activity states while Scarlet is working and before the next
real stream block is available.

Area:

UI/UX mobile / communication flow.

Changes:

- Added a mobile-only `activity` block type.
- Added randomized copy for request analysis, context loading, memory search,
  memory connection, missing-memory continuation, thinking, generic internal
  tool waits, memory writes, saved-memory confirmation, session recovery,
  schema checks, metacognition, and recoverable tool errors.
- Replaced the persistent mobile `Turno avviato` system card with an
  ephemeral activity card, so finished turns do not keep low-value status
  noise.
- Kept activity blocks as the last item while streaming and removed them when
  the matching real note/thinking/tool/answer block arrives.
- Added mobile styling for live activity pulse states.
- Advanced frontend package metadata to `1.14.5`.

Verification:

- Frontend production build passed: `cd frontend && npm run build`.
- Browser automation was not available in this session; no visual browser smoke
  test was run.

Residual Risk:

- Visual timing still needs real phone validation because activity blocks are
  stream-event driven and perceived smoothness depends on actual MiniMax/API
  event cadence.

Next Suggested Step:

Run a phone test with a normal chat turn, one memory search turn, and one
memory-save turn to confirm the last-block activity indicator feels alive but
does not distract from final answer readability.

## 2026-06-20 - V1.14.4 Scarlet Prompt API Body Discipline

Goal:

Inspect and update Scarlet's system prompt after live MiniMax M3 sessions showed
repeated `POST /mind/memory/write` calls with `body={}` despite Scarlet
reasoning that a memory should be saved.

Area:

Prompt / communication / memory / API Mind discipline.

Changes:

- Backed up the previous prompt to
  `backend/app/prompts/backups/scarlet_system.20260620T182223Z.pre-v1144-prompt-discipline.md`.
- Added human-first guidance for simple social turns so Scarlet does not answer
  normal conversation like a terminal.
- Changed near-miss memory wording so near-misses are weak leads, not
  established factual memory.
- Clarified that backend maintenance jobs exist as runtime support but are not
  a normal model-facing control surface.
- Added memory-write discipline: `intent` explains the call, while route data
  must live inside a non-empty `body`.
- Added anti-loop recovery: after endpoint-local guidance, Scarlet should retry
  only with a materially corrected body and stop repeated identical
  empty-body/shape failures instead of making many invalid calls.

Verification:

- Prompt backup created before modification.
- Textual diff inspected.
- Documentation updated in changelog, bug ledger, and branch docs.
- Direct MiniMax M3 prompt/tool probe with the updated prompt produced:
  - step 1: `GET /mind/schema`;
  - step 2: `POST /mind/memory/write` with a non-empty body containing
    `type`, `scope`, `content`, `reason`, `expected_future_use`,
    `confidence`, `salience`, and `tags`.
- `reason` is accepted by the memory handler as an alias for
  `reason_for_storage`.
- Live Scarlet regression still required; this prompt fix is a mitigation, not
  proof that MiniMax M3 now serializes memory-write bodies correctly.

Residual Risk:

- The current evidence indicates MiniMax M3 may still emit `body={}` under the
  full prompt/runtime context. If live tests still fail, the next fix should be
  provider/tool-contract level, not more prompt pressure.

Next Suggested Step:

Run one live memory-write probe through the normal dashboard/dev chat and
inspect `tool_calls.arguments_json` plus streamed tool input to verify whether
the body is now non-empty or whether the failure is below prompt level.

## 2026-06-20 - V1.14.3 Mobile Phone Ergonomics Fix

Goal:

Apply feedback from real mobile testing so the consumer app gives more space to
the chat and scrolls naturally on secondary pages.

Area:

UI/UX / consumer mobile app.

Changes:

- Replaced the top-right sync action with an off-canvas control drawer.
- Moved runtime facts, health/status, manual sync, new chat, and recent
  sessions into the drawer.
- Removed persistent starter suggestions from the bottom of the active chat.
- Kept starter suggestions only while a conversation has no user message yet.
- Reduced the chat top chrome so the message area starts much higher.
- Changed Memoria, Azioni, and Profilo to page-level scrolling so the screen
  headers scroll away with their content.
- Advanced frontend metadata to `1.14.3`.

Verification:

- Frontend production build passed: `cd frontend && npm run build`.
- Protected-preview build passed with:
  `VITE_PUBLIC_BASE_PATH=/scarlet/ VITE_API_BASE_URL=/scarlet-api VITE_FORCE_MOBILE=true npm run build`.
- Static assets were redeployed to `/var/www/scarlet` on the VPS.
- Local and remote SHA-256 hashes matched for `index.html`, JS, and CSS assets.
- Public unauthenticated `/scarlet/` still returns `401 Unauthorized`.
- Authenticated `/scarlet/` returns the new HTML referencing
  `/scarlet/assets/index-BaU9DHUY.js`.
- Authenticated `/scarlet-api/health` returns the mobile test backend on
  MiniMax-M3.

Residual Risk:

- This is a focused mobile ergonomics pass. Real phone verification is still
  needed after redeploy because the issue was originally observed on device.

Next Suggested Step:

Retest from phone, focusing on chat vertical space, drawer session access, and
full-page scrolling on Memoria/Azioni/Profilo.

## 2026-06-20 - V1.14.2 Protected Mobile Preview Deploy

Goal:

Publish the consumer mobile Scarlet UI for external testing without exposing
unprotected LLM/API usage and without touching the existing HoneyLabs Docker
containers.

Area:

UI/UX deployment / infrastructure preview.

Changes:

- Added frontend deploy configurability:
  - `VITE_PUBLIC_BASE_PATH=/scarlet/`;
  - `VITE_API_BASE_URL=/scarlet-api`;
  - `VITE_FORCE_MOBILE=true`.
- Built the mobile UI as a path-hosted static app.
- Created a separate VPS deployment at `/opt/scarlet-mobile-test`.
- Started a separate Docker Compose service:
  - container: `scarlet-mobile-api`;
  - image: `scarlet-mobile-api:latest`;
  - local port: `127.0.0.1:8100`;
  - database: copied demo SQLite DB mounted at `/app/data/app.db`;
  - maintenance disabled for the public preview.
- Published static assets under `/var/www/scarlet`.
- Added protected Nginx routes on `honeylabs.cloud`:
  - `/scarlet/` for the mobile UI;
  - `/scarlet-api/` for the demo backend.
- Protected both routes with Nginx Basic Auth.
- Backed up the active Nginx vhost before modification under
  `/var/backups/scarlet-mobile-test/`.
- Advanced frontend metadata to `1.14.2`.

Verification:

- Local frontend builds passed:
  - default build;
  - deploy build with `/scarlet/` base and `/scarlet-api` API prefix.
- VPS backend health passed through loopback:
  `http://127.0.0.1:8100/health`.
- Public unauthenticated requests to `/scarlet/`, `/scarlet/assets/...`, and
  `/scarlet-api/health` return `401 Unauthorized`.
- Public authenticated requests return:
  - mobile static HTML;
  - JS asset `200 OK`;
  - `/scarlet-api/health` JSON;
  - `/scarlet-api/api/dashboard/memories?limit=1` JSON.
- One authenticated stream smoke test completed through the public route:
  Scarlet answered "Ciao! Deploy mobile ricevuto, sono qui e pronta a
  rispondere."

Residual Risk:

- The preview uses a copied demo SQLite DB, not an intentionally cleaned public
  dataset. Keep Basic Auth enabled.
- `scarlet.honeylabs.cloud` DNS is not configured; the preview currently lives
  under `https://honeylabs.cloud/scarlet/`.
- Basic Auth protects against casual access but is not a production auth model.
- The smoke test consumed one MiniMax request and showed high input-token usage
  because the current runtime context is still large.

Rollback:

- Stop preview backend:
  `cd /opt/scarlet-mobile-test && docker compose down`.
- Remove or comment the Scarlet block between
  `# >>> Scarlet mobile test protected preview` and
  `# <<< Scarlet mobile test protected preview` in
  `/etc/nginx/sites-available/honeylabs`, then `nginx -t && systemctl reload nginx`.
- Restore the latest vhost backup from `/var/backups/scarlet-mobile-test/` if
  needed.

Next Suggested Step:

Run human mobile tests through the protected URL and inspect whether Basic Auth
is acceptable for the first evaluator loop, then decide whether to configure a
dedicated DNS record such as `scarlet.honeylabs.cloud`.

## 2026-06-20 - V1.14.1 Mobile Chat Deduplication And Rich Text

Goal:

Remove duplicate final-answer blocks observed in the mobile UI and make
Scarlet's user-facing text render as readable structured content.

Area:

UI/UX / consumer mobile app.

Changes:

- Fixed mobile stream completion so `turn_complete` adds a persisted fallback
  answer only when the current turn does not already have an `answer` block.
- Added mobile flow normalization to deduplicate blocks by id and keep only
  one final answer per turn, preferring streamed text blocks over fallback
  persisted blocks.
- Added a small safe rich-text renderer for headings, paragraphs, bullet lists,
  numbered lists, and `**bold**` emphasis.
- Advanced frontend metadata to `1.14.1`.

Verification:

- Frontend production build passed: `cd frontend && npm run build`.
- `git diff --check` passed.

Residual Risk:

- Visual QA should still be repeated in a real mobile viewport after a live
  user turn because this slice did not send new production chat messages.

Next Suggested Step:

Run one short live mobile conversation and confirm the final response appears
only once while Markdown-like formatting is rendered as readable UI.

## 2026-06-20 - V1.14.0 Consumer Mobile UI Surface

Goal:

Create a mobile-only user-facing Scarlet app that can sit beside the existing
developer cockpit without changing Scarlet's backend, prompt, memory,
retrieval, or agentic runtime.

Area:

UI/UX / user flows / communication surface.

Changes:

- Added `frontend/src/MobileApp.tsx`.
- Routed `/mobile` to the consumer mobile interface while keeping `/` as the
  existing developer dashboard.
- The mobile UI uses real existing endpoints for:
  - health/model status;
  - recent chat sessions;
  - chat turn streaming;
  - dashboard memories;
  - user profile;
  - runtime settings.
- Added bottom navigation for Chat, Memoria, Azioni, and Profilo.
- Added a consumer chat flow with readable blocks for context, memory,
  thinking presence, public notes, tool activity, and final answers.
- Added memory/profile screens backed by real dashboard data.
- Added future operativity cards marked `Presto disponibile` only, without
  adding backend or agent behavior.
- Advanced the frontend package version to `1.14.0`.

Verification:

- Frontend production build passed: `cd frontend && npm run build`.
- Local route smoke passed: `curl -fsS http://127.0.0.1:5173/mobile`.
- Existing backend APIs used by the mobile UI responded on the running local
  backend:
  - `/health`;
  - `/api/dashboard/settings`;
  - `/api/dashboard/memories?limit=3`;
  - `/api/chat/sessions?limit=3`.

Residual Risk:

- Browser screenshot verification could not be completed because the in-app
  browser runtime tool was not exposed in this session. The route and build are
  verified, but final visual QA should be done in a real mobile viewport.
- The running backend was in `codex_test` profile during smoke verification,
  so the UI read the isolated test DB. This does not affect the UI code path.
- No live chat turn was sent from the mobile UI during this slice to avoid
  mutating Scarlet state outside the UI-only scope.

Next Suggested Step:

Open `http://127.0.0.1:5173/mobile` in a mobile viewport or Android-sized
browser window, run a human visual pass, then decide whether the consumer app
needs a visual asset/brand pass before any Capacitor packaging work.

## 2026-06-19 - V1.13.0 Codex Test Database Isolation

Goal:

Allow Codex/evaluator memory experiments to use the real API/runtime/storage
path without mutating the production/laboratory Scarlet database.

Area:

Runtime configuration / storage isolation / memory evaluation harness.

Changes:

- Added startup flag `CODEX_TEST`.
- Added `CODEX_TEST_DATABASE_URL` and optional
  `CODEX_TEST_SEED_DATABASE_URL`.
- When `CODEX_TEST=true`, the backend opens the Codex test database instead
  of `DATABASE_URL`.
- If the selected Codex test SQLite file does not exist, startup seeds it once
  by copying the configured seed database.
- Existing Codex test DB files are reused and never overwritten by startup.
- Startup rejects configurations where the Codex test DB path points to the
  same file as the seed DB path.
- `/health` and `/api/dashboard/settings` expose active database profile
  metadata.
- The frontend runtime snapshot shows `prod` vs `codex_test`.
- Added regression coverage that starts the app in Codex test mode, writes via
  normal API endpoints, and verifies the source DB is unchanged.

Verification:

- Targeted backend tests passed:
  `cd backend && .venv/bin/python -m pytest tests/test_health.py tests/test_chat_api.py -k "dashboard_settings or health or codex_test" -q`
  (`3 passed`).

Residual Risk:

- This slice does not generate the large dirty evaluation DB. It only creates
  the safe runtime switch needed before populating and tuning that dataset.
- `codex_test` is a bootstrap setting, not a dashboard-mutated setting, because
  the DB must be selected before persisted settings can be read.

Next Suggested Step:

Duplicate the current Scarlet DB through `CODEX_TEST=true`, then populate the
Codex test copy with hundreds of controlled memories for retrieval/rerank/KG
calibration.

## 2026-06-19 - V1.12.0 Role-Aware Memory Retrieval Surfaces

Goal:

Stabilize dense/rerank retrieval before large dirty-database tests by
separating memory surfaces that can select a memory from surfaces that should
only support, explain, or corroborate it.

Area:

Memory / retrieval / embedding surface semantics.

Changes:

- Added role-aware surface policy to the memory surface taxonomy:
  `primary_content`, `canonical_fact`, `associative_graph`,
  `episodic_context`, and `supporting_context`.
- Made `memory_text` and type-specific surfaces content-focused by removing
  `reason_for_storage` and `expected_future_use` from primary embeddable text.
- Removed `reason_for_storage` and `expected_future_use` from sparse/lexical
  memory documents and lightweight NetworkX memory-domain matching.
- Changed grouped dense/rerank policy to
  `memory_target_role_aware_surface_score_v2`.
- Added grouped fields for retrieval inspection:
  `promotable_score`, `support_score`, `surface_roles`,
  `promotable_surface_kinds`, `support_surface_kinds`, and
  `active_rank_eligible`.
- Grouped rerank now receives only active-rank-eligible memory candidates.
- Hybrid ranking uses support surfaces only as low-weight corroboration when a
  memory already has a base, dense, or rerank promotable signal.
- Added a regression test where a misleading `future_use_text` surface matches
  the query but the memory is not selected.

Verification:

- Targeted Mind API retrieval tests passed:
  `cd backend && .venv/bin/python -m pytest tests/test_mind_api.py -k "openrouter_embedding_and_rerank_shadow or active_hybrid or networkx_graph_expansion" -q`
  (`5 passed`).
- Targeted chat retrieval tests passed:
  `cd backend && .venv/bin/python -m pytest tests/test_chat_api.py -k "memory_context or active_hybrid or graph_expansion or weak_memory_overlap" -q`
  (`5 passed`).
- Full backend suite passed:
  `cd backend && .venv/bin/python -m pytest tests -q` (`81 passed`).
- Frontend production build passed: `cd frontend && npm run build`.
- `git diff --check` passed.

Residual Risk:

- This slice does not calibrate thresholds on a large dataset. The next
  experimental step should duplicate the real Scarlet DB into an isolated test
  DB and contaminate it with at least hundreds of memories before tuning
  weights and thresholds.

Next Suggested Step:

Run the full backend suite, then design the large dirty-DB evaluation harness
using a duplicated Scarlet database rather than synthetic three-memory probes.

## 2026-06-19 - V1.11.4 Fact Canonicalization Stabilization

Goal:

Reduce canonical fact noise before relying more heavily on facts for conflict,
KG, retrieval, and future lifecycle maintenance.

Area:

Memory / atomic facts / canonicalization.

Changes:

- Known entity aliases now match normalized phrase/token boundaries rather than
  arbitrary substrings.
- `sal` still works as a real SAL alias, but no longer matches inside words
  such as `segnala` or `salutare`.
- `response_format` inference now requires explicit structural evidence:
  response-format tags, block metadata, block words, or phrases such as
  "answer with" / "rispondere con".
- Added regression coverage for the SAL substring class and generic brief
  response preferences.
- Reconciled the laboratory SQLite DB:
  - 7 unsupported active facts marked `rejected_extractor_noise`;
  - 6 supported replacement facts created;
  - rejected fact-derived surfaces, nodes, and edges removed from active paths.

Verification:

- Targeted Mind API tests passed:
  `cd backend && .venv/bin/python -m pytest tests/test_mind_api.py -k "fact_alias_matching_uses_phrase_boundaries or atomic_facts_support_alias_query or memory_write_and_search_are_traceable" -q`
  (`3 passed`).
- Full backend suite passed:
  `cd backend && .venv/bin/python -m pytest tests -q` (`80 passed`).
- Frontend production build passed: `cd frontend && npm run build`.
- `git diff --check` passed.
- Post-cleanup DB check:
  - active facts: 15;
  - rejected extractor noise facts: 7;
  - active `sal-updates` facts: 0;
  - active surfaces/nodes/edges for rejected facts: 0.

Residual Risk:

- Tag-derived entity selection is still shallow. The system can now avoid the
  known short-alias false positives, but it still needs a better entity model
  before aggressive merge/deprecate automation.

Next Suggested Step:

Inspect whether remaining active facts are useful enough for KG/conflict
diagnostics or whether tag-derived entities need another focused stabilization
slice.

## 2026-06-19 - V1.11.3 Retrieval/Facts Consistency Stabilization

Goal:

Stabilize the current retrieval platform before adding more cognitive features:
align embedding surface state with real OpenRouter vectors and prevent facts
inspection from using operational intent as a data filter.

Area:

Memory / retrieval / API contract consistency.

Changes:

- Added backend support to mark a `memory_surface` as `embedded` with the
  embedding model and vector id.
- OpenRouter retrieval now marks surfaces after both cache miss and cache hit.
- Reconciled the laboratory SQLite DB so 141 existing active surfaces with
  matching OpenRouter vectors are marked `embedded`; 84 surfaces without a
  matching vector remain `pending`.
- `/mind/memory/facts` now validates only explicit body filters; `intent` is
  preserved as operational context and never copied into `query`.
- Added regression tests for surface/vector relinking and unfiltered facts
  lookup with a broad intent.
- Updated backend/frontend metadata and documentation baseline to V1.11.3.

Verification:

- Targeted Mind API tests passed:
  `cd backend && .venv/bin/python -m pytest tests/test_mind_api.py -k "openrouter_embedding_and_rerank_shadow or atomic_facts_support_alias_query" -q`
  (`2 passed`).
- Full backend suite passed:
  `cd backend && .venv/bin/python -m pytest tests -q` (`79 passed`).
- Frontend production build passed: `cd frontend && npm run build`.
- `git diff --check` passed.

Residual Risk:

- Fact extraction/canonicalization is still rule-based and can produce noisy
  entities or inflated conflicts. This slice only fixes the intent/query
  contract boundary.
- Embedding/rerank thresholds and KG domain bridges still need live calibration.

Next Suggested Step:

Continue stabilization with fact canonicalization and retrieval pipeline
diagnostics before enabling more automatic memory lifecycle operations.

## 2026-06-18 - V1.11.2 Compact Model-Facing Memory Packets

Goal:

Reduce model-facing memory-context noise now that Scarlet has sparse, dense,
rerank, and NetworkX graph evidence, without losing full trace/debug
observability for the evaluator UI.

Area:

Memory / runtime context / model-facing packaging.

Changes:

- Added `memory-packet-v1` for selected memories in runtime context.
- Kept full retrieval diagnostics in `memory.context` traces.
- Added `rendering_profile=compact-model-facing-v1`.
- Model-facing memory packets now include:
  - claim;
  - source/provenance anchor;
  - confidence and salience;
  - compact facts;
  - cognitive subject;
  - domains;
  - validity;
  - sensitivity;
  - retrieval routes and compact turn-level reason.
- Removed verbose model-facing repetition of raw `signals`, metadata, full
  hybrid weights/thresholds, and raw retrieval debug structures.

Verification:

- Targeted chat tests passed:
  `cd backend && .venv/bin/python -m pytest tests/test_chat_api.py -k "persists_messages_and_traces or selects_relevant_memory_context or metacognitive_context" -q`
  (`3 passed`).
- On a recent real `memory.context` trace with 5 selected memories, selected
  model-facing memory payload size decreased from 18,974 to 13,254 characters
  while preserving core source and cognitive fields.
- Direct Scarlet smoke passed:
  session `ses_a8abae0496da4539a7ad7db012fc61a1`,
  turn `turn_8c88b7c30ffc4f09802ba529a7421a4c`.
  The model-facing runtime context used `rendering_profile=compact-model-facing-v1`
  and selected two `memory-packet-v1` user memories: caffeine/sleep and
  chocolate/body-limit. The final answer used both constraints naturally.

Residual Risk:

- `memory-packet-v1` is compact but not final. Future work should derive
  `applies_when`, `do_not_apply_when`, emotional weight, staleness, durability,
  and privacy class from facts/KG/maintenance rather than letting Scarlet fill
  arbitrary free-form fields.
- Runtime context still keeps compatibility mirrors for current prompt safety.
  A later prompt/runtime cleanup can reduce duplication further once tests show
  Scarlet reliably uses `runtime_context.blocks`.

Next Suggested Step:

Run live Scarlet turns with M3 and inspect whether answers use `claim`,
`source`, `cognitive.domains`, and `retrieval.routes` more cleanly than the
previous verbose selected-memory payload.

## 2026-06-18 - V1.11.1 NetworkX Associative Memory Graph Retrieval

Goal:

Improve Scarlet's human-like memory recall for implicit fields of discourse:
when the user asks about a warm evening beverage, Scarlet should receive
relevant personal constraints such as caffeine/sleep and chocolate/body-limit
memories even if the user does not name the stored memory directly.

Area:

Memory / semantic retrieval / lightweight KG.

Changes:

- Added `networkx` as a standard backend dependency.
- Added `backend/app/mind/graph_retrieval.py`:
  - builds a temporary NetworkX graph over candidate memories, existing derived
    graph rows, and backend-owned discourse-domain nodes;
  - emits `retrieval_graph` with seed nodes, domain matches, paths, scores, and
    graph stats;
  - keeps domain bridges generic, avoiding one-off mappings from a specific
    word to a specific memory.
- Wired graph expansion into:
  - automatic per-turn `memory.context`;
  - manual `/mind/memory/search`.
- Added graph signals to selected memory payloads.
- Increased shadow surface fetch breadth so dense/rerank sees enough surfaces
  before `retrieval_shadow_cloud_surface_limit` is applied.
- Added a context guard: when personal associative graph evidence exists,
  base-only project memories are declassified from selected evidence, reducing
  project-memory noise in personal contexts.

Verification:

- Targeted chat tests passed:
  `cd backend && .venv/bin/python -m pytest tests/test_chat_api.py -k "graph_expansion or active_hybrid_selects_paraphrased_memory_context or excludes_weak_memory_overlap" -q`
  (`4 passed`).
- Targeted Mind API tests passed:
  `cd backend && .venv/bin/python -m pytest tests/test_mind_api.py -k "graph_expansion or active_hybrid" -q`
  (`3 passed`).
- Full backend suite passed:
  `cd backend && .venv/bin/python -m pytest tests -q` (`79 passed`).
- Direct Scarlet smoke:
  session `ses_31764779f34f460895b07a8e80b98caa`,
  turn `turn_3899983e95174b0092bd3700b3db52c7`.
  Query: warm evening beverage, focus, no caffeine, personal preferences.
  `memory.context.selected` contained only:
  - caffeine-after-dinner/sleep memory via `energy_sleep_focus` and
    `food_drink_wellbeing`;
  - chocolate/body-limit memory via `food_drink_wellbeing`.

Residual Risk:

- This is lightweight retrieval-time graph expansion, not mature KG reasoning.
- Domain bridges need calibration as more personal memory categories appear.
- It must not be used for lifecycle-changing operations such as automatic
  merge, update, deprecation, or stale-memory repair.
- `pip install -e backend` still fails because setuptools detects both `app`
  and `data` as top-level packages; this is an existing packaging issue and was
  not fixed in this slice. Installing `networkx` directly into the venv allowed
  verification.

Next Suggested Step:

Run several human-led sessions with ordinary personal prompts and inspect
`retrieval_graph` alongside sparse/dense/hybrid evidence. Calibrate domain
bridges only from observed false positives/false negatives, not from isolated
word patches.

## 2026-06-18 - V1.11.0 Active Hybrid Retrieval Calibration

Goal:

Promote the validated OpenRouter embedding/rerank evidence from pure shadow
diagnostics to a configurable active ranking layer without losing observability
or destabilizing default installations.

Area:

Memory / retrieval ranking / embedding-rerank calibration.

Changes:

- Added memory-level grouping to `retrieval_shadow`:
  - raw `results` still show individual `memory_surfaces`;
  - `grouped_results` deduplicates by memory `target_id`, keeps the best
    surface score, surface kinds, top surface, and contributing surfaces;
  - OpenRouter rerank now also reports `rerank.grouped_results` over grouped
    memory candidates.
- Added configurable `retrieval_hybrid_mode`:
  - `off` keeps dense/rerank diagnostic only;
  - `shadow` computes hybrid entries without changing active memory selection;
  - `active` lets grouped dense/rerank evidence influence `memory.context` and
    `/mind/memory/search` results.
- Added explicit hybrid thresholds and weights for base lexical score, sparse
  score, dense score, rerank score, salience, and confidence.
- Added hybrid evidence to memory context traces, query plans, selected memory
  signals, and `memory.search` results.
- Kept default mode `off` to avoid requiring OpenRouter keys or changing
  behavior unexpectedly.

Test Design:

Before e2e Scarlet tests, the backend test matrix now covers:

- paraphrased Italian retrieval for an English cacao/focus memory;
- memory-level dedup to avoid repeated surfaces crowding out the right memory;
- grouped rerank after dedup;
- a negative control where dense nearest-neighbor noise must not create a
  selected memory below threshold;
- automatic chat-turn memory context, not only manual `memory.search`.

Verification:

- Targeted memory API tests passed:
  `backend/.venv/bin/python -m pytest backend/tests/test_mind_api.py -k "openrouter_embedding_and_rerank_shadow or active_hybrid" -q`
  (`3 passed`).
- Targeted chat context tests passed:
  `backend/.venv/bin/python -m pytest backend/tests/test_chat_api.py -k "active_hybrid_selects_paraphrased_memory_context or selects_relevant_memory_context or excludes_weak_memory_overlap" -q`
  (`3 passed`).
- Full backend suite passed:
  `backend/.venv/bin/python -m pytest backend/tests -q` (`76 passed`).

Open Questions:

- Live OpenRouter e2e requires `OPENROUTER_API_KEY` in the runtime environment.
  The key provided in chat was not written to `.env` or committed.
- The initial thresholds (`dense >= 0.38`, `rerank >= 0.55`) are conservative
  lab defaults and must be recalibrated with real Scarlet conversations.
- Active hybrid retrieval still does not solve lifecycle/conflict reasoning;
  merge, update, deprecate, and KG expansion remain separate future layers.

Next Suggested Step:

Run live Scarlet A/B probes with `RETRIEVAL_HYBRID_MODE=active`,
`RETRIEVAL_SHADOW_BACKEND=openrouter`, and rerank enabled. Use difficult but
natural scenarios: Italian paraphrase, fatigue/style preference, food
constraint, unrelated negative control, temporal recall requiring episodic
search, and near-neighbor memories that share only weak context.

## 2026-06-18 - V1.10.0 OpenRouter Embedding/Rerank Shadow

Goal:

Start real cloud embedding evaluation for Scarlet memory retrieval without
waiting for the Windows GPU embedding setup and without changing active memory
ranking.

Area:

Memory / retrieval shadow / cloud embedding.

Changes:

- Added `retrieval_shadow_backend=openrouter`.
- Added small OpenRouter retrieval client for `/embeddings` and `/rerank`.
- Added `embedding_vectors` SQLite cache for stable memory-surface embeddings
  keyed by content hash.
- Added OpenRouter shadow embedding over `memory_surfaces`, defaulting to
  `nvidia/llama-nemotron-embed-vl-1b-v2:free`.
- Added optional OpenRouter rerank shadow over dense candidates, defaulting to
  `nvidia/llama-nemotron-rerank-vl-1b-v2:free`.
- Kept `trace_only_no_active_ranking`: sparse/BM25 and lexical/fact logic still
  decide active memory selection.
- Updated docs and config examples for the new shadow mode.

Verification:

- Targeted backend tests passed:
  `backend/.venv/bin/python -m pytest backend/tests/test_mind_api.py::test_mind_memory_search_reports_openrouter_embedding_and_rerank_shadow backend/tests/test_mind_api.py::test_mind_memory_search_reports_trace_only_shadow_retrieval -q`
  (`2 passed`).
- Full backend suite passed:
  `backend/.venv/bin/python -m pytest backend/tests -q` (`73 passed`).
- Frontend production build passed: `npm run build` in `frontend`.
- `git diff --check` passed.

Open Questions:

- Live OpenRouter tests still require `OPENROUTER_API_KEY`.
- Free-tier reliability, latency, context limits, Italian/personal-memory
  quality, and privacy posture must be measured before promoting dense/rerank
  into active ranking.
- Rerank is useful only after candidate retrieval; it cannot recover a memory
  absent from the candidate set.

Next Suggested Step:

Enable OpenRouter shadow on a controlled test DB and run paired retrieval
probes: lexical match, Italian paraphrase, synonym-only query, temporal
preference query, negative control, and conflict query. Compare sparse selected
memories, dense shadow results, reranked shadow results, latency, and cache hit
rate.

Live Follow-up:

- The owner provided an OpenRouter key for local-only testing.
- Direct OpenRouter smoke confirmed:
  - embeddings return 2048-dimensional vectors;
  - rerank returns ordered `index` / `relevance_score` payloads;
  - free test responses reported zero cost.
- Backend integration on an in-memory DB seeded 10 controlled memories.
- Positive evidence:
  - dense/rerank shadow recovered Italian paraphrase and "sono stanco" style
    cases where active sparse failed;
  - sparse remained better on exact lexical and chocolate/snack cases.
- Key finding:
  - raw surface-level shadow results can be misleading because many surfaces
    from one memory crowd out other memories;
  - when dense results are deduplicated by memory `target_id`, all eight
    positive controlled queries ranked the expected memory first;
  - rerank should run after memory-level dedup, not over duplicate surfaces.
- Updated `docs/experiments.md#exp-0039---openrouter-cloud-embedding-shadow`
  with detailed results and next implementation candidate.

## 2026-06-17 - V1.9.0 Metacognitive Context Shadow

Goal:

Create a narrow shadow phase for metacognitive lessons so the project can
observe whether targeted self-regulation hints would help Scarlet before making
them part of normal model-facing context.

Area:

Metacognition / perception-context / UI debug.

Changes:

- Added backend generation of `metacognitive.context` at turn start.
- Default mode is `shadow`: the payload is traced, emitted as
  `metacognitive.context.shadowed`, streamed as `metacognitive_context`, and
  shown in the UI, but it is not inserted into `<runtime_context>`.
- Added controlled `inject` mode for A/B tests. In that mode, the same payload
  becomes a `metacognitive_context` block inside `runtime_context.blocks`.
- Added a small deterministic lesson selector focused on high-signal patterns:
  simple-turn effort calibration, memory-commitment risk, historical recall
  evidence, and source-sensitive claims.
- Added frontend rendering for the shadow block with readable candidate
  lessons and raw JSON details.
- Advanced project/app version to V1.9.0.

Verification:

- `python3 -m py_compile backend/app/mind/metacognitive_context.py
  backend/app/mind/context.py backend/app/api/chat.py backend/app/config.py`
  passed.
- `backend/.venv/bin/python -m pytest backend/tests/test_chat_api.py -q`
  passed: 13 tests.
- `npm run build` passed in `frontend`.

Open Questions:

- The selector is intentionally deterministic and small. It is not yet proof
  that metacognitive lessons improve Scarlet.
- The next evaluation should compare normal shadow-only turns with controlled
  `inject` turns on identical prompts, measuring overthinking, tool calls,
  latency, memory promises, and source discipline.

Next Suggested Step:

Run a short A/B probe with `metacognitive_context_mode=shadow` versus
`inject`, using the same request set, then decide which lessons are actually
worth retrieving dynamically.

## 2026-06-16 - V1.8.0 Thinking Retrospection Metacognition

Goal:

Give Scarlet a controlled way to inspect previous-turn provider thinking as
process evidence through the existing internal metacognition route, without
adding parallel reflection endpoints or always reinjecting raw reasoning.

Area:

Metacognition / API Mind / Scarlet prompt.

Changes:

- Extended `POST /mind/metacognition/step` with retrospective modes:
  `review_previous_turn`, `detect_reasoning_drift`, `explain_tool_choice`,
  `recover_open_loops`, `compare_answer_to_reasoning`,
  `extract_reasoning_digest`, and `memory_from_reasoning`.
- Added `turn_scope="previous"` and `detail="digest|excerpt|raw"`.
- Retrospective modes default to the previous completed turn when no scope is
  supplied.
- Added backend construction of `thinking-retrospection-pack-v1` from previous
  turn messages, final answer, public notes, tool calls, event markers, traces,
  and provider thinking.
- Updated Scarlet's prompt and Mind API schema so the capability is discoverable
  and is framed as process audit, not factual evidence.
- Added small shape-hardening for observed MiniMax M3 metacognition payloads:
  `reasoning_scope`, `reasoning_detail`, and `{"item": [...]}` list wrappers.
- Backed up the prompt to
  `backend/app/prompts/backups/scarlet_system.20260616T120000Z.v180-thinking-retrospection.md`.

Verification:

- `python3 -m py_compile backend/app/mind/metacognition.py backend/app/mind/schema.py backend/app/mind/dispatcher.py` passed.
- `backend/.venv/bin/python -m pytest backend/tests/test_mind_api.py -q`
  passed: 26 tests.
- `backend/.venv/bin/python -m pytest backend/tests/test_mind_api.py backend/tests/test_chat_api.py -q`
  passed: 38 tests.
- `npm run build` passed in `frontend`.
- `git diff --check` passed.
- Direct live probe session `ses_9f7b8e37cc2145508867bd45b96f3553`:
  - Turn 1 `turn_db40c320be8c423fbeea614de4c66e2e` generated one provider
    thinking block and a compact answer about open-loop controls.
  - Turn 2 `turn_0fedc6410a2a461e911ab67fc181c642` asked Scarlet to audit the
    previous reasoning without naming an endpoint.
  - Scarlet emitted one public note, inspected `GET /mind/schema`, then called
    `POST /mind/metacognition/step` with
    `mode="compare_answer_to_reasoning"`, `turn_scope="previous"`, and
    `detail="excerpt"`.
  - Trace `trace_205288e7aa6a419eabab67785c5bc908` built a
    `thinking-retrospection-pack-v1` from previous turn
    `turn_db40c320be8c423fbeea614de4c66e2e`, with 1 thinking block and 4818
    thinking chars.
  - The second turn completed successfully but cost about 109k input tokens and
    178 seconds latency, mainly because Scarlet chose `excerpt` instead of the
    default cheaper `digest`.

Open Questions:

- Initial live evidence is positive: Scarlet chose retrospective metacognition
  autonomously. Detail selection still needs calibration because it chose
  `excerpt` where `digest` would likely have been enough.
- `raw` detail may be useful for debugging but should stay rare because it can
  be token-heavy and can tempt the model to overfit previous reasoning.
- The first implementation only supports the previous completed turn; multi-turn
  retrospection should wait for evidence from this narrow experiment.

Next Suggested Step:

Run a live two-turn Scarlet probe where the first turn creates a possible open
loop and the second asks Scarlet to audit what happened, without naming the
endpoint. Score whether she uses metacognition retrospectively and summarizes
process evidence without dumping raw thinking.

## 2026-06-16 - V1.7.2 Prompt-Only Long Reasoning Notes

Goal:

Make Scarlet's prolonged reasoning more legible to the user through short
public note waypoints, without adding backend events, UI changes, or synthetic
runtime messages.

Area:

Communication / Scarlet system prompt.

Changes:

- Backed up the previous prompt to
  `backend/app/prompts/backups/scarlet_system.20260616T173917Z.long-notes-v172.md`.
- Added `Long Reasoning Notes` under `Public Work Notes`.
- Defined when a turn counts as prolonged: multiple API Mind operations,
  multiple evidence sources, conflict/staleness/missing evidence, strategy
  changes, or several reasoning/tool phases before final answer.
- Defined note waypoints for investigation start, first meaningful operation,
  evidence-driven plan changes, synthesis, and final verification.
- Reinforced that notes are public orientation only, not chain-of-thought,
  draft answers, self-critique, or repeated proof that Scarlet is thinking.

Verification:

- `git diff --check` passed.
- `npm run build` passed in `frontend`.
- `curl http://127.0.0.1:8000/health` confirmed active MiniMax M3.
- Direct live probe session `ses_5dbdac4acf91402bb31418ddd3750b99`,
  turn `turn_20cf87c91bb94b4aac771bf4dbad7a05`:
  - generated 6 public notes, 8 tool calls, 7 thinking blocks, and 1 final
    answer;
  - notes appeared as short waypoints before schema verification,
    metacognition retry, evidence reorientation, memory search, and final
    synthesis;
  - no backend/UI changes were needed for the note blocks.

Open Questions:

- Prompt-only control may not force mid-stream notes during pure no-tool
  thinking if MiniMax chooses to emit only a final answer. This slice tests the
  model-facing instruction before considering runtime-level mechanisms.
- The same probe exposed repeated MiniMax M3 shape errors when calling
  `POST /mind/metacognition/step`; endpoint-local error guidance eventually
  let Scarlet recover, but the behavior is tracked separately under BUG-0047.

Next Suggested Step:

Run a complex direct Scarlet request and verify whether public notes appear as
short waypoints while direct/simple turns remain compact.

## 2026-06-16 - V1.7.1 Request Effort Routing Prompt Fix

Goal:

Reduce MiniMax M3's tendency to over-process simple Scarlet turns without
weakening source discipline, memory autonomy, or agentic depth when the request
actually needs them.

Area:

Communication / perception-context / Scarlet system prompt.

Changes:

- Backed up the previous prompt to
  `backend/app/prompts/backups/scarlet_system.20260616T164444Z.md`.
- Added `Request Effort Routing` to classify turns as direct, contextual,
  source-sensitive, state-changing, or high-impact.
- Direct and contextual turns may now answer from visible/runtime evidence
  without ritual API Mind calls, metacognition, public work notes, or full
  verification.
- Source-sensitive and state-changing turns still require proportional API
  Mind use and operation-result verification.
- Memory forcing is now conditional on real semantic candidates, memory
  promises, state changes, or source-sensitive claims.
- Near-miss memories may now be applied softly as communication-style hints
  when relevant, without presenting them as verified facts.

Verification:

- `git diff --check` passed.
- `npm run build` passed in `frontend`.
- `curl http://127.0.0.1:8000/health` confirmed active MiniMax M3.
- Direct live probe session `ses_958ba084193d48fb9ac853c89602ffea`:
  - turn `turn_ff0cf30a951240ccb09a1290a2aad51a` on a simple one-sentence
    request produced a one-sentence answer, no tool calls, and no public work
    note; provider thinking explicitly classified it as Level 1 direct answer.
  - turn `turn_53485550e62549b588a1702e7ddf3a1e` on a source-sensitive schema
    request produced a public note, called `GET /mind/schema`, and answered
    from the returned schema version/routes.

Open Questions:

- MiniMax M3 may still sometimes choose a heavier reasoning path because the
  provider can emit visible thinking even for compact answers. The product
  target is not "no thinking", but no unnecessary public complexity or tool
  ritual.

Next Suggested Step:

Run several human live sessions with both simple and source-sensitive prompts
to estimate whether M3 now calibrates effort better than the previous prompt.

## 2026-06-16 - V1.7.0 Stream Block Lifecycle UI

Goal:

Make Scarlet's live stream behave like stable agentic blocks that appear,
mature, complete, and persist without visual jumps between active stream and
historical replay.

Area:

Communication / perception-context / frontend stream lifecycle.

Changes:

- Extended frontend `AgentStep` with stable `blockId` and lifecycle `phase`.
- `text_start` and `text_delta` now create a visible provisional public-text
  block instead of hidden runtime data.
- Semantic `assistant_note` and `assistant_answer` events now finalize that same
  public-text block.
- Tool blocks now expose phases from input preparation through execution and
  completion.
- Tool input JSON is visible while provider `input_json_delta` chunks stream.
- `turn_complete` now reconciles live blocks with persisted event/trace replay
  rather than blindly replacing the visible flow.
- Added active-block visual treatment in the chat flow and phase visibility in
  the sidebar inspector.
- Updated `docs/block-registry.md` and ADR-0049 with lifecycle rules.

Verification:

- `npm run build` passed in `frontend`.

Open Questions:

- Browser automation was unavailable in the Codex session, so visual screenshot
  verification still requires owner/live UI inspection.
- Backend-level canonical `stream.block.*` events may be useful later, but are
  intentionally deferred until the frontend lifecycle proves where the backend
  contract is actually needed.

Next Suggested Step:

Run live Scarlet turns with thinking, public text before tool use, and multiple
tool calls; verify that blocks stay visible and keep their order before and
after turn completion.

## 2026-06-16 - V1.6.0 Model Input Inspector And Block Registry

Goal:

Make Scarlet's model-facing input and UI/debug blocks legible enough to analyze
redundancy, ordering, reinjection, and frontend representation without relying
only on raw JSON traces.

Area:

Communication / perception-context / frontend inspector.

Changes:

- Added `docs/block-registry.md` as the canonical map of model-facing blocks,
  runtime blocks, stream/output blocks, trace-only surfaces, UI placement, and
  current redundancy candidates.
- Added a right-sidebar `Modello` inspector in the frontend.
- The `Modello` tab renders the persisted `llm.request` trace as readable
  sections:
  - system prompt + injected runtime context;
  - parsed `runtime_context.blocks` with compatibility mirror warning;
  - provider-native messages and content block types;
  - tool schemas and parameter descriptions;
  - full raw request behind a detail toggle.
- Historical tool replay now enriches completed `mind.tool_call.*` events with
  matching `mind.tool_call` traces so full tool output remains visible after
  reload.
- Updated communication, perception-context, project-state, decisions, and
  changelog documentation.

Verification:

- `npm run build` passed in `frontend`.
- `curl http://127.0.0.1:8000/health` returned MiniMax M3 as active model.
- A direct SQLite trace inspection confirmed current `llm.request` payloads use
  `payload_json` with `model`, `max_tokens`, `system`, `base_system`,
  `runtime_context`, `provider_messages`, and `tools`.

Open Questions:

- Browser plugin control was not exposed in this Codex session, so visual
  screenshot verification could not be performed through the in-app browser.
- Payload optimization is deliberately deferred: runtime compatibility mirrors
  are visible redundancy candidates, but removing them requires separate direct
  Scarlet regression tests.

Next Suggested Step:

Use the new `Modello` tab during live Scarlet sessions to decide which
model-facing surfaces can be safely compressed or removed without weakening
Scarlet's comprehension.

## 2026-06-16 - V1.5.2 Prompt Block Contract Alignment

Goal:

Realign Scarlet's system prompt with the actual backend cognitive surfaces so
she can distinguish same-session provider continuity, runtime blocks, episodic
recall, and semantic memory without flattening them into one generic
"memory/context" concept.

Area:

Communication / perception-context / Scarlet system prompt.

Changes:

- Backed up the previous prompt to
  `backend/app/prompts/backups/scarlet_system.20260616T134019.md`.
- Added an explicit `Continuity Layers` section to
  `backend/app/prompts/scarlet_system.md`.
- Clarified that active-session visible history may include provider-native
  `thinking`, `text`, `tool_use`, and `tool_result` blocks.
- Clarified that `runtime_context.blocks` is the primary structured contract
  and top-level runtime fields are compatibility mirrors.
- Clarified that `recent_runtime_events` is a compact operational hint surface,
  not stronger semantic evidence than direct provider continuity.
- Added an explicit instruction that when prior visible `thinking` blocks are
  already present in active-session history, Scarlet should inspect that
  semantic content before relying only on `thinking.started` /
  `thinking.captured` markers.

Verification:

- `curl http://127.0.0.1:8000/health` returned
  `{\"status\":\"ok\",\"provider\":\"minimax\",\"model\":\"MiniMax-M3\"}`.
- Direct live probe session `ses_172498d31b424e1dafa28dd85a38fcc0`:
  - turn `turn_cb204b4e27fc469e9b1ce3f3f7c26ac3` correctly distinguished
    active-session continuity, runtime blocks, semantic memory, and episodic
    recall;
  - trace inspection confirmed the updated prompt was loaded because the
    `llm.request` base system contained `## Continuity Layers`.
- Direct live probe session `ses_d09ad1594bf4471ea27794c5b896856d` and follow-up
  probe `ses_4dcded570516493f850c2839a0d8894f`:
  - `llm.request.provider_history_source` was
    `session.provider_history_json`;
  - provider messages for the follow-up turn contained assistant
    `thinking` blocks from the previous turn;
  - Scarlet still often grounded answers about prior reasoning in
    `recent_runtime_events` or claimed the prior `thinking` content was not
    recoverable.

Open Questions:

- MiniMax M3 now receives the correct prompt contract and provider-visible
  thinking history, but it does not reliably use prior visible `thinking`
  blocks as the strongest same-session semantic source.
- This looks more like a model-behavior or attention/allocation issue than a
  backend transport issue.

Next Suggested Step:

Decide whether to accept this as a current M3 limitation, add a more explicit
runtime-visible continuity summary surface for prior thinking, or postpone the
problem until a stronger cognition/metacognition layer exists.

## 2026-06-16 - Thinking Block Persistence And Historical Replay Fix

Goal:

Ensure provider-generated thinking blocks survive final turn persistence and
remain visible in correct order when a conversation is reloaded from stored
events.

Area:

Communication / runtime events / frontend replay.

Changes:

- Fixed backend semantic-event persistence for response-derived blocks:
  `record_response_content_events()` now stores `text`, `model_step`, and
  `index` for both `llm.thinking.captured` and assistant text blocks rebuilt
  from `raw_provider_messages`.
- Added frontend replay fallback for legacy turns: when an old persisted
  `llm.thinking.captured` event has no `text`, the UI now recovers the
  thinking body from matching `llm.response.raw_provider_messages`.
- Strengthened backend regression coverage for non-stream semantic persistence
  and streaming replay payload expectations.

Verification:

- `backend/.venv/bin/python -m pytest backend/tests/test_chat_api.py -q`
  passed with 12 tests.
- `npm run build` passed in `frontend`.

Open Questions:

- MiniMax M3 still emits thinking only on some turns. This fix preserves and
  replays generated thinking correctly, but does not force the provider to
  produce thinking on every response.

Next Suggested Step:

Run one or more real M3 turns that are likely to trigger internal reasoning and
verify in the UI that the resulting thinking cards remain visible after turn
completion and after session reload.

## 2026-06-14 - V1.5.0 Maintenance Lab And Theory-First Cognitive Organs

Goal:

Recover the real state of the project after a pause, keep MiniMax M3 active for
owner-led testing, and advance only the parts that are useful before
embedding/KG and before goal/metacognition implementation.

Area:

Memory maintenance lab, provider baseline governance, Goal/Focus/Task theory,
Metacognition theory.

Changes:

- Added maintenance lab APIs:
  - `GET /api/maintenance/overview`
  - `GET /api/maintenance/jobs`
  - `POST /api/maintenance/jobs/{job_id}/run`
- Kept these APIs outside Scarlet's `mind_api` surface because they are for
  backend maintenance workers, evaluator tooling, and future Dream-style
  review, not in-turn Scarlet cognition.
- Added repository support for paginated maintenance job listing.
- Added targeted maintenance API tests for overview, job listing, and missing
  job run errors.
- Added `docs/theory-goal-focus-task.md`.
- Added `docs/theory-metacognition.md`.
- Updated memory/project docs to mark merge/update/deprecate automation as
  post-embedding/KG work.
- Updated app/docs/package baseline to V1.5.0.

Verification:

- `backend/.venv/bin/python -m pytest tests/test_maintenance_api.py -q`
  passed with 4 tests.
- `backend/.venv/bin/python -m pytest -q` passed with 67 tests.
- `git diff --check` passed.
- `npm run build` passed in `frontend`.

Open Questions:

- Owner will run human tests with M3 and inspect whether behavior is stable
  enough to keep M3 as the active baseline.
- Pending/resolved proposal quality should be inspected after real idle
  maintenance windows before tuning thresholds.
- Goal/Focus/Task and Metacognition theory documents need owner review before
  any implementation slice.
- V1.5.0 overview exposed failed maintenance jobs with `ReadTimeout`; recorded
  as BUG-0040 for a separate reliability discussion.

Next Suggested Step:

Run live M3 sessions, wait for idle maintenance, inspect
`/api/maintenance/overview`, and then decide whether the next sprint is
maintenance tuning, Windows embedding/KG setup, or theory-approved goal/metacog
implementation.

## 2026-05-08 - Project Documentation Foundation

Goal:

Create a project memory foundation so future work can continue without relying only on conversational memory.

Changes:

- Created `docs/project-blueprint.md` as the main project blueprint.
- Created `AGENTS.md` as the short operational protocol for the IDE agent.
- Created companion documentation registries:
  - `docs/activity-log.md`
  - `docs/decisions.md`
  - `docs/bug-ledger.md`
  - `docs/experiments.md`
  - `docs/api-contract.md`
- Updated `docs/project-blueprint.md` so the current next steps now reflect the completed documentation foundation.

Verification:

- Confirmed `docs/project-blueprint.md` exists and is readable.
- Repository is not currently initialized as a Git repository; `git status` fails until Git is initialized.

Open Questions:

- Decide whether to initialize Git immediately before backend implementation.
- Decide whether the first backend scaffold should use plain SQLAlchemy or SQLModel.

Next Suggested Step:

Initialize or intentionally defer Git, then scaffold the minimal FastAPI backend with configuration and a health endpoint.

## 2026-05-08 - Git And Release Discipline

Goal:

Set up local project tracking so repository history, changelog entries, and roadmap progress stay connected.

Changes:

- Added `README.md`.
- Added `CHANGELOG.md`.
- Added `.gitignore`.
- Added `.gitmessage`.
- Added `docs/release-process.md`.
- Updated `AGENTS.md` with changelog and commit-memory rules.
- Added ADR-0003 for Git history, changelog, and agent commit identity.

Verification:

- Local Git initialization completed on branch `main`.
- Repository-local Git author configured as `Scarlet Codex <scarlet-codex@users.noreply.github.com>`.
- Commit template configured from `.gitmessage`.
- Foundation files were captured in the initial local commit.

Open Questions:

- Remote GitHub repository creation is blocked in this environment because `gh` is not installed and the GitHub connector does not expose repository creation.
- Preferred remote target is documented as `panicDa3m0n/llm-api-mind`, private by default.
- Local Git is older and does not support newer commands such as `git init -b` or `git branch --show-current`; use compatible commands when needed.

Next Suggested Step:

Initialize local Git on `main`, configure repository-local Scarlet author metadata, make the foundation commit, then connect to GitHub after the remote repository exists.

## 2026-05-08 - GitHub Remote Connection

Goal:

Connect the local repository to the GitHub remote provided by the project owner.

Changes:

- Confirmed `origin` points to `https://github.com/panicDa3m0n/llm-api-mind.git`.
- Confirmed the remote repository is reachable and currently has no refs.
- Attempted to push `main` to `origin`.
- Recorded the local HTTPS authentication blocker.

Verification:

- `git remote -v` shows `origin` set to the GitHub repository.
- `git ls-remote https://github.com/panicDa3m0n/llm-api-mind.git` returned no refs, consistent with an empty repository.
- `GIT_TERMINAL_PROMPT=0 git push -u origin main` failed because local Git credentials are not available.
- SSH access check to `git@github.com` failed with `Permission denied (publickey)`, so SSH push is not currently available.

Open Questions:

- The local environment needs GitHub authentication for HTTPS push, or an authorized GitHub SSH key.

Next Suggested Step:

Authenticate local GitHub access, then run `git push -u origin main`.

## 2026-05-08 - Phase 1A Backend Scaffold

Goal:

Start Phase 1 with the smallest useful backend slice: FastAPI config, health endpoint, env template, and a test.

Changes:

- Added `backend/pyproject.toml`.
- Added `backend/.env.example`.
- Added `backend/README.md`.
- Added `backend/app/config.py`.
- Added `backend/app/main.py`.
- Added `backend/tests/test_health.py`.
- Updated `.gitignore` so nested `.env.example` files remain trackable.
- Documented `GET /health` in `docs/api-contract.md`.
- Added ADR-0004 to record SQLModel as the MVP storage choice.
- Marked GitHub HTTPS push authentication as resolved after the human owner pushed `main`.

Verification:

- Created a local ignored venv at `backend/.venv`.
- Installed backend dev dependencies with `python3 -m pip install -e ".[dev]"`.
- Ran `pytest` from `backend`; 1 test passed.
- Pushed commit `35cefb4` to `origin/main` from this environment.

Open Questions:

- None for this slice.

Next Suggested Step:

Install backend dev dependencies, run the health test, then add the MiniMax provider client after the user inserts `MINIMAX_API_KEY` into `backend/.env`.

## 2026-05-08 - Phase 1B MiniMax Provider Smoke

Goal:

Add the first real LLM provider integration and verify that MiniMax M2.7 is reachable from the backend.

Changes:

- Added the Anthropic-compatible MiniMax provider wrapper.
- Added `POST /api/debug/llm-smoke-test`.
- Added unit tests for provider injection and missing MiniMax key handling.
- Added API contract documentation for the smoke endpoint.
- Added backend README smoke-test instructions.
- Added ADR-0005 for the Anthropic-compatible MiniMax SDK choice.

Verification:

- Installed updated backend dependencies including the Anthropic SDK.
- Ran `pytest` from `backend`; 3 tests passed.
- Ran a real MiniMax smoke call with `max_tokens=128`; response returned `text: pong`.
- Observed that `max_tokens=32` can return an empty text response because M2.7 may spend the output budget before final text. This was later superseded by the project policy to use a generous configurable default.

Open Questions:

- None for this slice.

Next Suggested Step:

Add SQLite schema for sessions, messages, turns, and traces.

## 2026-05-08 - Phase 1C Storage Schema And Token Budget Policy

Goal:

Correct the MiniMax token-budget policy and add the SQLite persistence foundation for baseline chat tracing.

Changes:

- Added `MINIMAX_MAX_TOKENS=4096` to backend settings and `.env.example`.
- Updated the LLM smoke endpoint to use the configured default when `max_tokens` is omitted.
- Added `max_tokens` to the LLM smoke response for observability.
- Added SQLModel storage tables for `sessions`, `messages`, `turns`, and `traces`.
- Added storage DB helpers and repository functions.
- Added tests for default MiniMax token budget and storage round-trip behavior.
- Added ADR-0006 for the generous MiniMax output budget policy.
- Documented the MVP storage schema in `docs/api-contract.md`.

Verification:

- Ran `pytest` from `backend`; 6 tests passed.
- Ran a real MiniMax smoke call without explicit `max_tokens`; response returned `text: pong` and `max_tokens: 4096`.

Open Questions:

- None for this slice.

Next Suggested Step:

Implement persistent chat endpoints on top of the SQLite schema.

## 2026-05-08 - Phase 1D Persistent Chat Endpoints

Goal:

Implement the baseline chat API on top of the SQLite schema so every turn stores messages and request/response traces.

Changes:

- Added `POST /api/chat/sessions`.
- Added `POST /api/chat/sessions/{session_id}/turn`.
- Added `GET /api/chat/sessions/{session_id}/messages`.
- Added `GET /api/debug/traces/{turn_id}`.
- Added provider `generate_chat()` support so MiniMax receives persisted chat history instead of a flattened prompt.
- Wired database initialization into `create_app()`.
- Added chat API tests with provider fakes, missing-provider-key handling, and in-memory SQLite.
- Recorded BUG-0002 for detached ORM instances across SQLModel session boundaries.
- Recorded BUG-0003 for provider initialization errors escaping chat endpoint handling.

Verification:

- Ran `pytest` from `backend`; 10 tests passed.
- Ran a real MiniMax chat turn through the persistent endpoint using an in-memory DB; response returned `assistant: pong`, two trace IDs, and trace kinds `llm.request` and `llm.response`.

Open Questions:

- The first baseline trace experiment still needs a human-readable debug cockpit or a CLI/scripted scenario runner.

Next Suggested Step:

Add a minimal frontend chat/debug cockpit or a temporary CLI experiment runner for EXP-0001.

## 2026-05-08 - Phase 1E Frontend Debug Cockpit

Goal:

Add a minimal browser UI for baseline chat and trace inspection.

Changes:

- Added Vite + React + TypeScript frontend.
- Added chat session creation and turn submission.
- Added message list and trace panel.
- Added frontend API client with Vite proxy to FastAPI.
- Added local run instructions in root and frontend README files.

Verification:

- Ran `npm run build` from `frontend`; build succeeded.
- Verified Vite dev server at `http://127.0.0.1:5173`.
- Verified backend health through the running FastAPI server.
- Ran headless Chrome smoke: frontend loaded, sent a real MiniMax chat turn, displayed `pong`, and displayed `llm.request` plus `llm.response` traces.

Open Questions:

- Need to run EXP-0001 as a documented scenario and evaluate whether the cockpit exposes enough trace detail.

Next Suggested Step:

Run EXP-0001 Baseline Chat Trace and record the result in `docs/experiments.md`.

## 2026-05-08 - Phase 1F EXP-0001 Baseline Trace Run

Goal:

Run the first documented baseline trace experiment before adding cognitive APIs.

Changes:

- Executed EXP-0001 against the local FastAPI backend with real MiniMax M2.7 calls.
- Created a dedicated experiment session.
- Ran two controlled chat turns: `pong` and `trace-ok`.
- Retrieved stored messages and traces for each turn.
- Recorded the accepted experiment result in `docs/experiments.md`.

Verification:

- Session `ses_bf3790e6f01a44b49b3348ebf90289a3` stored 4 messages.
- Turn `turn_9d2439d67f6344368178bedf61663301` completed with assistant text `pong`.
- Turn `turn_e4ef9ca301714adc827ccbc1d0d8509e` completed with assistant text `trace-ok`.
- Each turn produced `llm.request` and `llm.response` traces.
- Request traces contained structured provider messages.
- Response traces contained usage metadata and latency was recorded on the turn.

Open Questions:

- Trace UX can still improve during Phase 2, especially export/copy and compact provider-error inspection.

Next Suggested Step:

Prepare Phase 2 by adding the minimal `mind_api` facade and schema-discovery contract over the existing traceable runtime.

## 2026-05-08 - Phase 1G Scarlet System Prompt

Goal:

Give the chat agent a stable project identity before adding `mind_api`.

Changes:

- Added bundled Scarlet system prompt at `backend/app/prompts/scarlet_system.md`.
- Added prompt resolver with `AGENT_SYSTEM_PROMPT` and `AGENT_SYSTEM_PROMPT_PATH` overrides.
- Wired persistent chat turns to use the resolved system prompt by default.
- Preserved per-turn `system` override for controlled debug runs.
- Recorded effective prompt source/path in `llm.request` traces.
- Replaced the MiniMax provider diagnostic fallback with a neutral fallback for non-agent paths.
- Added ADR-0007 and BUG-0004.

Verification:

- Ran `pytest` from `backend`; 11 tests passed.
- Ran a real in-process MiniMax chat check with `Chi sei?`; assistant identified as Scarlet and the request trace showed `system_source=bundled`.
- Restarted local uvicorn on `http://127.0.0.1:8000`.
- Ran a live HTTP MiniMax chat check through the restarted backend; assistant identified as Scarlet and the request trace contained the bundled Scarlet system prompt.

Open Questions:

- Full multi-file prompt assembly (`identity`, `rules`, `intelligence`, `api_protocol`, runtime state) remains planned after the single-prompt MVP proves stable.

Next Suggested Step:

Commit and push the system prompt slice, then proceed to the minimal Phase 2 `mind_api` facade.

## 2026-05-08 - Phase 1H Scarlet Prompt Refinement

Goal:

Refine the default system prompt so it shapes identity without adding unnecessary defensive bias.

Changes:

- Rewrote `backend/app/prompts/scarlet_system.md` in positive terms.
- Removed domain-specific denials and medical/diagnostic corrective wording from the default prompt.
- Kept the prompt focused on identity, relationship, operating posture, current runtime, and future API discipline.
- Added a regression assertion that the bundled prompt passed to chat does not contain medical/diagnostic corrective terms.
- Updated prompt architecture notes and ADR-0007 with the positive-prompt principle.

Verification:

- Ran `pytest` from `backend`; 11 tests passed.
- Ran an in-process MiniMax check with `Chi sei?`; assistant identified as Scarlet and the effective system prompt contained no medical/diagnostic corrective terms.
- Ran an in-process MiniMax current-runtime check; assistant described chat, persisted messages, MiniMax calls, and traces, while presenting future modules as research modules.
- Restarted local uvicorn on `http://127.0.0.1:8000`.
- Ran a live HTTP MiniMax check through the restarted backend; assistant identified as Scarlet and trace inspection confirmed `system_source=bundled` with no medical/diagnostic corrective terms.

Open Questions:

- Future bias-specific prompt constraints should be added only after tests show that architecture, API state, or traces cannot address the behavior.

Next Suggested Step:

Commit and push the prompt refinement, then continue toward the minimal `mind_api` facade.

## 2026-05-08 - Phase 1I Feminine Conversational Scarlet

Goal:

Give Scarlet a clearer feminine identity and a more human conversational style while keeping the prompt measurable and non-defensive.

Changes:

- Added explicit feminine agent identity to `backend/app/prompts/scarlet_system.md`.
- Added guidance for feminine grammatical self-reference in gendered languages, especially Italian.
- Added a `Conversational Presence` section for natural pacing, warmth through attention, focused questions, and reduced generic assistant phrasing.
- Updated prompt architecture notes and ADR-0007 to record the conversational identity principle.
- Added test assertions that the bundled prompt includes feminine identity guidance.

Verification:

- Ran `pytest` from `backend`; 11 tests passed.
- Ran in-process MiniMax checks for identity, subjective stance, and natural non-list response.
- Confirmed the effective prompt includes feminine identity guidance and subjective-response guidance.
- Ran live HTTP MiniMax checks through `http://127.0.0.1:8000`; Scarlet identified with feminine self-reference and LLM API Mind context.
- Confirmed live traces report `system_source=bundled` and include the new identity guidance.

Open Questions:

- Conversational style should be evaluated through real turns over time; future prompt changes should be driven by observed behavior, not by adding decorative instructions.

Next Suggested Step:

Commit and push the conversational identity refinement, then continue toward the minimal `mind_api` facade.

## 2026-05-09 - Phase 2A Mind API Facade

Goal:

Start Phase 2 with the smallest traceable `mind_api` slice: schema discovery, dispatcher, and persistent tool-call records.

Changes:

- Restored `backend/.env.example` as a tracked placeholder template after the local workspace was recreated and `backend/.env` was filled manually by the project owner.
- Added `backend/app/mind/schema.py` with the `mind_api` tool schema and route catalog.
- Added `backend/app/mind/dispatcher.py` for `mind_api(method, path, body, intent)` dispatch.
- Added `GET /mind/schema`.
- Added `POST /mind/call` as an HTTP facade for the model-facing tool contract.
- Added a `tool_calls` SQLModel table and repository helper.
- Added `mind.tool_call` traces when `POST /mind/call` includes a session context.
- Added Mind API tests for schema discovery, traceable calls, planned-route errors, and missing session handling.
- Recorded ADR-0008 and BUG-0005.
- Documented the implemented Mind API contracts.

Verification:

- Ran `pytest` from `backend`; 15 tests passed.
- Ran `npm run build` from `frontend`; build succeeded.
- Started local FastAPI backend on `http://127.0.0.1:8000`.
- Verified `GET /mind/schema` over HTTP returned `ok=true` and `tool.name=mind_api`.
- Verified `POST /mind/call` over HTTP created a `tool_call_id` and `trace_id`.

Open Questions:

- The MiniMax provider tool loop is not wired yet. `POST /mind/call` exercises the dispatcher and persistence path manually for now.
- `GET /api/debug/traces/{turn_id}` remains turn-scoped; a session-level debug trace endpoint may be useful soon.

Next Suggested Step:

Connect MiniMax tool-use content blocks to the `mind_api` dispatcher while preserving raw provider content and storing every tool call.

## 2026-05-09 - Phase 2B MiniMax Mind API Tool Loop

Goal:

Connect MiniMax M2.7 tool-use content blocks to the traceable `mind_api` dispatcher.

Changes:

- Added provider-level support for a bounded Anthropic-compatible tool loop.
- Added normalized tool-use and executed-tool-call models.
- Updated persistent chat turns to expose only the `mind_api` tool to MiniMax.
- Wired `mind_api` tool calls to the dispatcher created in Phase 2A.
- Stored every model tool call in `tool_calls`.
- Added `mind.tool_call` traces during chat turns.
- Extended `llm.request` traces with the tool schema.
- Extended `llm.response` traces with normalized tool call metadata and raw provider messages.
- Updated the bundled Scarlet prompt so `mind_api` schema discovery is described as currently available.
- Added regression coverage for a chat turn that dispatches and traces a `mind_api` call.

Verification:

- Ran `pytest` from `backend`; 16 tests passed.
- Restarted local FastAPI backend on `http://127.0.0.1:8000`.
- Ran a live MiniMax chat turn asking Scarlet to inspect `GET /mind/schema` with `mind_api`.
- Live turn `turn_5bc222c2fb444fc8b3285749cd74024e` produced trace kinds `llm.request`, `mind.tool_call`, and `llm.response`.
- Live assistant response correctly identified `GET /mind/schema` as the currently implemented Mind API route.
- Recorded accepted EXP-0004 Mind API Tool Loop Trace.

Open Questions:

- The frontend trace cockpit can display the new trace kind, but it has not yet been refined specifically for tool-loop inspection.
- None for Phase 2B.

Next Suggested Step:

Start Phase 3 memory only after confirming the frontend trace cockpit remains usable for `mind.tool_call` inspection.

## 2026-05-09 - Streaming Agentic Chat Cockpit

Goal:

Improve the chat cockpit so agentic turns can be evaluated while they are running, not only after the final assistant response is stored.

Changes:

- Added `POST /api/chat/sessions/{session_id}/turn/stream`.
- Added NDJSON stream events for turn start, provider request steps, provider-exposed thinking deltas, tool input deltas, tool calls, tool results, final text deltas, model stop reasons, turn completion, and stream errors.
- Kept the streaming endpoint on the same persistence path as normal chat turns: messages, `llm.request`, `mind.tool_call`, `llm.response`, and turn completion are still stored.
- Updated the frontend chat submit flow to use the streaming endpoint.
- Added a frontend agent timeline that separates runtime events, provider thinking blocks, tool calls, tool results, and final answer text.
- Kept the raw JSON trace list available below the structured timeline.
- Added backend regression coverage for streaming tool-loop events and traces.
- Recorded ADR-0010.

Verification:

- Ran `pytest` from `backend`; 17 tests passed.
- Ran `npm run build` from `frontend`; build succeeded.
- Restarted FastAPI backend on `http://127.0.0.1:8000`.
- Ran a live MiniMax streaming smoke. Events arrived before completion: `turn_started`, `model_request`, `thinking_start`, `thinking_delta`, `tool_use_start`, `tool_input_delta`, `model_stop`, `tool_call`, `tool_result`, second `model_request`, final `text_delta`, and `turn_complete`.
- Live streaming smoke produced trace kinds `llm.request`, `mind.tool_call`, and `llm.response`.
- Restarted Vite frontend on `http://127.0.0.1:5173` and verified the page responds with HTTP 200.

Open Questions:

- The UI currently displays provider-exposed thinking blocks directly as debug evidence. If this becomes too noisy, add a compact/expanded toggle or summary mode.
- The streaming endpoint does not yet expose cancellation.

Next Suggested Step:

Use the cockpit manually for several multi-turn tool-loop conversations, then decide whether the next smallest useful slice is trace UI polish or Phase 3 episodic memory.

## 2026-05-09 - Inline Agent Turn Timeline

Goal:

Make each assistant chat turn explain the exact ordered agentic operations that produced it, while keeping raw request/response logs in the debug pane.

Changes:

- Added a turn-local `seq` to every streamed NDJSON event.
- Added `turn_id` to every streamed NDJSON event so frontend state can attach operations to the correct assistant message.
- Added `model_step` to provider stream events, tool calls, and tool results where the operation belongs to a specific MiniMax request.
- Reworked the frontend from one global agent timeline to per-turn operation timelines keyed by `turn_id`.
- Moved the structured timeline into the assistant message body.
- Kept the right pane focused on metrics and raw persisted trace JSON.
- Added local ignore rules for temporary browser verification artifacts.
- Recorded ADR-0011 and BUG-0006.

Verification:

- Ran `pytest` from `backend`; 17 tests passed.
- Ran `npm run build` from `frontend`; build succeeded.
- Restarted FastAPI backend on `http://127.0.0.1:8000`.
- Ran a live stream smoke with a `mind_api` schema call; 19 events arrived, all with `turn_id`, and event order matched the agent loop.
- Ran headless Edge verification against `http://127.0.0.1:5173`; the assistant message rendered 16 ordered operations and the trace pane retained raw `llm.request` and `llm.response` logs.

Open Questions:

- Inline thinking/tool payloads are currently fully visible. If real use becomes noisy, add collapse controls per operation without hiding ordering.
- Cancellation is still not implemented for long streaming turns.

Next Suggested Step:

Use the inline cockpit for a few real multi-turn tool conversations. If the ordering remains clear, proceed to the smallest Phase 3 memory slice.

## 2026-05-09 - Dual-Mode Evaluation Runner

Goal:

Create the first real evaluation harness before memory: scripted checks for regressions and adaptive interactive runs for human-led behavioral probing.

Changes:

- Added `backend/app/evals/runner.py`.
- Added a scripted scenario loader and runner.
- Added an interactive runner that creates a live backend session, accepts one human prompt at a time, prints operation summaries and answers, and records optional human notes.
- Added run artifacts: `transcript.jsonl`, `summary.md`, and `run.json`.
- Added `baseline_tool_schema.json` and `continuity_probe.json` scenarios.
- Added pytest coverage for scripted run recording, stream parsing, trace fetching, and expectation checks.
- Updated README usage and ignored generated eval runs.
- Recorded ADR-0012 and EXP-0006.

Verification:

- Ran `pytest tests/test_eval_runner.py`; 1 test passed.
- Ran a real scripted eval against `http://127.0.0.1:8000`:
  - Run `20260509_142108_baseline_tool_schema`
  - Session `ses_c48e8e5bee124c2eb039c73cf7edb352`
  - Turn `turn_b1094e9340d54ef8a1eec91bf28fa62c`
  - Result passed
  - Traces included `llm.request`, `mind.tool_call`, and `llm.response`
  - Tool call path was `/mind/schema`

Open Questions:

- The first adaptive interactive session still needs to be run by the human/agent pair.
- Memory design remains intentionally blocked until a dedicated discussion.

Next Suggested Step:

Run an interactive adaptive baseline session and use the resulting transcript plus notes to decide what the memory design discussion must cover.

## 2026-05-09 - Adaptive Scarlet Pre-Memory Test

Goal:

Run a real adaptive end-to-end Scarlet evaluation before memory design, choosing follow-up prompts from observed answers rather than from a fixed script.

Changes:

- Ran `20260509_adaptive_scarlet_codex` with six live turns against the local backend.
- Saved the local ignored artifact at `backend/app/evals/runs/20260509_adaptive_scarlet_codex/`.
- Updated EXP-0006 with the adaptive run results and behavioral notes.

Verification:

- Backend health was `ok` on `http://127.0.0.1:8000`.
- Frontend remained available on `http://127.0.0.1:5173`.
- Run session: `ses_02141fe5e23248d988015a8d499adfe5`.
- Turn trace coverage:
  - Turn 1: `llm.request`, `mind.tool_call`, `llm.response`.
  - Turn 2: `llm.request`, `llm.response`.
  - Turn 3: `llm.request`, `mind.tool_call`, `llm.response`.
  - Turn 4: `llm.request`, `mind.tool_call`, `llm.response`.
  - Turn 5: `llm.request`, `llm.response`.
  - Turn 6: `llm.request`, `llm.response`.

Findings:

- Scarlet used `mind_api` correctly for schema discovery.
- Scarlet corrected an ambiguous capability classification after being challenged.
- Scarlet handled explicit `POST /mind/memory/search` as a recoverable planned-route error.
- Scarlet recalled `protocollo-lanterna` from chat history and did not claim persistent memory.
- Source attribution should be a first-class memory design requirement.

Open Questions:

- How should future memory results expose source, confidence, age, and write provenance to prevent chat-history/memory confusion?
- Should the prompt be refined now to classify implemented vs planned capabilities more defensively, or should the memory design solve this through API response shape and trace UI?

Next Suggested Step:

Hold the memory-design discussion before implementing `POST /mind/memory/write` or `POST /mind/memory/search`.

## 2026-05-09 - Memory v0 Implementation And Live Tests

Goal:

Implement the first autonomous, traceable Memory v0 slice and verify it with both scripted tests and real MiniMax end-to-end behavior.

Changes:

- Added the `memories` SQLModel table and repository helpers.
- Implemented `POST /mind/memory/write` and `POST /mind/memory/search` behind the existing `mind_api` dispatcher.
- Added dedicated `mind.memory.write` and `mind.memory.search` traces in addition to `mind.tool_call`.
- Added source session/turn provenance, confidence, salience, tags, metadata, usage count, and timestamps to memory records.
- Added simple lexical retrieval and usage-count updates for search results.
- Updated Scarlet's prompt so memory is treated as autonomous cognitive state, not as a permission prompt to the user.
- Added robust Memory v0 normalization for common real model tool-body variants discovered during live runs.
- Added `backend/app/evals/scenarios/memory_v0_preference.json`.
- Added ADR-0013 and BUG-0007.

Verification:

- Ran backend tests with the backend venv: `23 passed`.
- Ran frontend build: `npm run build` succeeded.
- Restarted the local backend on `http://127.0.0.1:8000`.
- Verified `/mind/schema` lists `POST /mind/memory/write` and `POST /mind/memory/search` as implemented.
- Verified memory calls without session context return `memory.context_required`.
- Ran live MiniMax memory write/search checks:
  - write turn `turn_2b023a4ca7cf484b8e3ad9162d46bfde`
  - search turn `turn_77afd134e3fc4fda9bdd68bbcb04213d`
  - retrieved memory `mem_4dbdc6ed630c409eb34781725ceb72e1`
- Ran second live check:
  - write turn `turn_cb37c277b4ef48608d5b9cf41e61cab6`
  - search turn `turn_080ec485e8554d108273fd8044b7c1e8`
- Ran scripted Memory v0 scenario:
  - passing run `backend/app/evals/runs/20260509_163342_memory_v0_preference/summary.md`
  - write turn `turn_02ef09f26e9642f882407b9ac1ace2d0`
  - search turn `turn_1224797eaf2647ec9fd3cc966bc747cf`
- Ran final HTTP smoke verifying alias normalization and GET-style memory search.

Open Questions:

- Memory v0 does not yet support update, forgetting, conflict resolution, or semantic/vector retrieval.
- The frontend has no dedicated memory panel yet; memory is inspectable through traces and raw tool results.
- Repeated live runs showed that model-generated tool bodies vary substantially, so alias normalization should remain monitored instead of treated as complete.

Next Suggested Step:

Run adaptive Memory v0 sessions through the cockpit, then decide whether the next slice is a memory inspection panel, memory update/forget semantics, or attention context over retrieved memories.

## 2026-05-09 - Visible Metacognition Prompt Probe

Goal:

Add a testable prompt-level method for Scarlet to think aloud through concise public metacognitive notes without turning final answers into raw reasoning dumps.

Changes:

- Added `Visible Metacognition Experiment` to `backend/app/prompts/scarlet_system.md`.
- Defined the visible label `Metacognizione:`.
- Constrained the note to objective, evidence source, uncertainty/risk, and next cognitive action.
- Added `backend/app/evals/scenarios/visible_metacognition_probe.json`.
- Added ADR-0014 and EXP-0007.
- Cleaned up the experiments document so Memory v0 results are recorded under EXP-0002 rather than the planned attention experiment.

Verification:

- Ran backend tests with the backend venv: `23 passed`.
- Restarted local backend on `http://127.0.0.1:8000`.
- Ran the live scripted probe:
  - run `backend/app/evals/runs/20260509_170747_visible_metacognition_probe/summary.md`
  - turn `turn_5f362600358443bb90a089b27592d5a5`
  - result passed
  - traces included `mind.memory.search` and `mind.tool_call`
  - answer included a concise `Metacognizione:` block.

Open Questions:

- Visible metacognition may become repetitive if Scarlet uses it on ordinary turns.
- Adaptive sessions should decide whether metacognitive notes should ever be written to memory or later connected to reflection.

Next Suggested Step:

Run adaptive Memory v0 conversations with explicit and implicit requests for metacognition, then compare visible notes against tool traces and final answers.

## 2026-05-11 - Post-Weekend State Review And Compatibility Fix

Goal:

Re-sync Codex/Scarlet with the GitHub state after substantial weekend progress and evaluate the current project maturity.

Changes:

- Reviewed current Git history, README, changelog, project blueprint, decisions, bug ledger, API contract, experiments, backend runtime, frontend cockpit, eval runner, and tests.
- Confirmed the repository is clean and aligned with `origin/main`.
- Found a Python 3.10 compatibility bug in `backend/app/evals/runner.py`.
- Replaced `datetime.UTC` with `timezone.utc`.
- Recorded BUG-0008 and changelog entry for the compatibility fix.

Verification:

- Ran backend tests with the backend venv; 23 tests passed after the fix.
- Ran frontend `npm run build`; build succeeded.

Open Questions:

- The next behavioral evidence should come from adaptive Memory v0 sessions rather than only scripted checks.
- Memory v0 still lacks inspection UI, update/forget/conflict semantics, and semantic retrieval.
- Visible metacognition needs adaptive evaluation to avoid becoming decorative or repetitive.

Next Suggested Step:

Run one or more adaptive Memory v0 evaluation sessions, then decide whether the next implementation slice should be a memory inspection panel, memory lifecycle semantics, or attention context.

## 2026-05-11 - Versioned Laboratory State Policy

Goal:

Make repository state match the current laboratory policy: everything except private keys and credentials can be committed, including the SQLite runtime database.

Changes:

- Updated `.gitignore` so `backend/data/app.db` is intentionally trackable.
- Documented the lab-state policy in `README.md`, `docs/project-blueprint.md`, and ADR-0015.
- Added an environment note for cross-machine SQLite continuity and merge-conflict risk.
- Prepared the current SQLite database snapshot for version control.

Verification:

- Confirmed `backend/.env` remains ignored.
- Confirmed `backend/data/app.db` contains tables for `sessions`, `messages`, `turns`, `traces`, `tool_calls`, and `memories`.
- Confirmed the actual `MINIMAX_API_KEY` value and common secret markers are not present in `backend/data/app.db`.

Open Questions:

- If the Windows machine has a richer SQLite state than this macOS snapshot, that database should replace the tracked snapshot in a later commit rather than being overwritten silently.
- A hosted or public release will need a different database and privacy policy.

Next Suggested Step:

Push the lab-state policy and DB snapshot, then decide whether the Windows database should replace the current tracked SQLite snapshot.

## 2026-05-11 - Direct Adaptive Memory v0 Verification

Goal:

Verify Scarlet's actual Memory v0 behavior through direct chat-stream turns rather than only scripted or deterministic scenarios.

Changes:

- Ran direct adaptive turns through `POST /api/chat/sessions/{session_id}/turn/stream`.
- Found and fixed a wrapper compatibility bug where MiniMax emitted `raw_input` and JSON-string `body` values that failed `MindAPIRequest` validation.
- Added wrapper normalization for `raw_input`, JSON-string bodies, and body-level `intent`.
- Added Italian compatibility aliases for `preferenza`, `alta`, `media`, and `bassa`.
- Added regression coverage for the real MiniMax-shaped wrapper/body behavior.
- Updated experiment and API documentation with the observed behavior.
- Updated the immediate roadmap toward Memory v0 lifecycle and search relevance work.

Verification:

- Ran backend tests with the backend venv; 24 tests passed.
- Restarted the backend on `http://127.0.0.1:8000`.
- Direct write turn `turn_01d1ead1b76a40ffa095c797da0e0c45` stored `mem_abed5590f91b4eb8aa93d1103db024de`.
- Cross-session recall turn `turn_839a89d5c37f4d84bbe63f6154fecda5` retrieved the stored memory with source attribution.
- Negative-control turn `turn_2c255fdb84184f0096b149d03680b012` did not invent `protocollo Mare-Vetro`, but search returned a weakly related Zero-Luce memory.
- Update/conflict turns `turn_c30ba6ba0b844286bcc8eb6c996e4013` and `turn_d0da056910824cd08a79773031ef2fa6` showed that v0 creates a new active memory instead of replacing the old one.
- Capability correction turn `turn_50098ed1f35742f4a9bc25361c404633` confirmed via schema that update/delete/deprecate routes are not implemented.

Open Questions:

- What should the exact lifecycle API be: update existing records, deprecate by status, or append revision records with active revision selection?
- Should memory search suppress weak lexical hits by threshold, return them as low-confidence candidates, or ask the model to classify relevance after retrieval?
- Should the frontend get a memory panel before or after lifecycle semantics?

Next Suggested Step:

Implement the smallest Memory v0 lifecycle slice: deprecate/replace an existing memory with traceable conflict handling, then add a search relevance guard.

## 2026-05-12 - Memory Context Pipeline v0 Design

Goal:

Move memory retrieval out of optional model discretion and formalize it as an automatic runtime context phase.

Changes:

- Added Memory Context Pipeline v0 to the project blueprint.
- Added ADR-0016 documenting automatic per-turn memory context as the accepted architecture.
- Added EXP-0008 for validating automatic memory context against optional model-driven search.
- Documented the planned internal `memory.context` trace and `<runtime_context>` shape in the API contract.
- Updated Scarlet's prompt with a runtime-context contract for backend-provided memory evidence and capability state.
- Updated the immediate roadmap to prioritize automatic memory evidence before additional memory lifecycle endpoints.
- Recorded BUG-0010 for the current optional-search memory evidence risk.

Verification:

- Documentation and prompt changes only; runtime implementation was not changed in this slice.
- Verified the design against the referenced RAG, SQLite FTS5, reranking, hybrid search, and rank-fusion source material.

Open Questions:

- What exact relevance thresholds should separate `selected`, `near_miss`, and `excluded` in the first lexical-only implementation?
- Should `memory.context` be stored only as traces at first, or also get a dedicated table after the trace shape stabilizes?
- How strict should the post-response validator be before it starts blocking or warning on unsupported memory claims?

Next Suggested Step:

Implement the smallest Memory Context Pipeline v0 slice: build `TurnFrame`, run automatic lexical retrieval on every turn, persist `memory.context`, inject selected runtime context before `llm.request`, and add regression tests for empty and weak-overlap cases.

## 2026-05-12 - Memory Context Pipeline v0 Implementation

Goal:

Implement the first automatic per-turn memory context slice before adding more memory endpoints.

Changes:

- Added `backend/app/mind/context.py`.
- Added `TurnFrame` construction from current user message, recent dialogue, session metadata, capability state, active scope, and time.
- Added automatic `memory.context` traces before `llm.request` for normal and streaming chat turns.
- Added backend-generated `<runtime_context>` injection into the effective system message sent to MiniMax.
- Added lexical v0 memory ranking with `selected`, `near_miss`, `excluded`, and simple conflict detection.
- Added streaming `memory_context` events.
- Updated the frontend inline operation timeline and trace reconstruction to show memory context.
- Added regression tests for empty memory context, selected relevant memory, weak-overlap exclusion, and streaming memory context.
- Updated API, experiment, bug, roadmap, and changelog documentation.

Verification:

- Ran backend tests with the backend venv: `26 passed`.
- Ran frontend build: `npm run build` succeeded.

Open Questions:

- Thresholds for `selected`, `near_miss`, and `excluded` need live adaptive evaluation.
- Retrieval is lexical v0 over active memory records; SQLite FTS5/BM25 remains the next scoring improvement.
- Post-response validation for unsupported memory claims is still pending.

Next Suggested Step:

Restart the local backend, run an adaptive cockpit session focused on Memory Context Pipeline v0, then tune lexical scoring or add SQLite FTS5/BM25 based on trace evidence.

## 2026-05-13 - Live Adaptive Memory Context Pipeline Evaluation

Goal:

Evaluate Scarlet's real behavior through streaming chat turns instead of scripted batteries, focusing on whether automatic memory context fixes skipped memory search and how Scarlet uses runtime conflicts and capabilities.

Changes:

- Restarted the local backend so the latest Memory Context Pipeline v0 code was active.
- Created live adaptive session `ses_5c32ff33daf041baaad36c18363dcfb2`.
- Ran four real streaming turns through `POST /api/chat/sessions/{session_id}/turn/stream`.
- Recorded the resulting sessions, messages, traces, and memory usage updates in the tracked laboratory SQLite database.
- Updated the experiment record, roadmap, changelog, and bug ledger with the observed behavior.

Verification:

- Backend health returned `{"status":"ok","app":"LLM API Mind","environment":"local","model":"MiniMax-M2.7"}` before the run.
- Mare-Vetro turn `turn_51d32fd9b9e3435cb8d6d853e7ccb7cb` produced `memory.context` trace `trace_6a2ec3dadeb940d59ab5a48f74a2cdb6` with `searched=true`, `selected_count=0`, and `negative_evidence=no_relevant_memory_selected`.
- Zero-Luce follow-up turn `turn_bd3fcf15e068497aa8c52a3c7e45b2e9` produced `memory.context` trace `trace_93e9dd421ae7400487f0fe76c4f8e181` with both Zero-Luce memories selected and a conflict detected.
- Conflict inspection turn `turn_cbd7c6e6b6a942afa554efb9a932d811` produced trace `trace_f0cd4e61aae84eedaa75babe22abe068`; Scarlet correctly described the 4-block and 3-block Zero-Luce versions when asked directly.
- Capability challenge turn `turn_ed16ce5b48124988bff5108aa3ef2b2c` confirmed Scarlet can read runtime capability state and correct herself when asked: `memory.update`, `memory.deprecate`, and `memory.delete` are unavailable.

Open Questions:

- Conflict disclosure needs to be surfaced proactively when `memory.context.conflicts` is non-empty.
- Capability state needs answer-level enforcement so Scarlet does not offer lifecycle actions that are unavailable.
- Retrieval scoring still needs SQLite FTS5/BM25, but this live run shows response control is the more immediate reliability gap.

Next Suggested Step:

Implement the smallest Memory Context Pipeline v0.1 response-control slice: make conflicts and unavailable capabilities operational answer constraints, then verify with the same Mare-Vetro/Zero-Luce live scenario before moving to FTS5/BM25 or lifecycle endpoints.

## 2026-05-20 - Project Reorientation For Work Start

Goal:

Re-align Codex/Scarlet with the current repository documentation, runtime shape, project contracts, and immediate implementation direction before starting the next work slice.

Changes:

- Reviewed repository state and confirmed `main` is clean and aligned with `origin/main`.
- Queried available MCP resources; no persistent project memory resources were exposed in this environment.
- Read the project blueprint, activity log, decision log, bug ledger, API contract, experiments, release process, changelog, root README, backend README, frontend README, and key backend/frontend runtime files.
- Confirmed the implemented system includes FastAPI chat, MiniMax M2.7 provider integration, `mind_api`, Memory v0 write/search, automatic Memory Context Pipeline v0, streaming NDJSON turns, inline frontend operation timelines, and the dual-mode eval runner.
- Noted the current highest-priority gap: runtime context can detect memory conflicts and unavailable capabilities, but final answers do not yet reliably treat those as enforced response constraints.

Verification:

- Ran backend tests with the backend venv: `26 passed`.
- Ran frontend production build with `npm run build`; build succeeded.
- Confirmed the worktree was clean before documentation update.

Open Questions:

- What exact response-control mechanism should v0.1 use first: stronger runtime-context obligations, a lightweight post-response validator, or both?
- Should the existing prompt contract be adjusted only after backend response-control tests show the minimum needed wording?
- The Git history contains one recent commit with an unfilled template subject (`de09c49`); decide later whether this matters for release/history hygiene.

Next Suggested Step:

Implement the smallest Memory Context Pipeline v0.1 response-control slice for conflict disclosure and unavailable memory lifecycle claims, then rerun backend tests, frontend build, and the Mare-Vetro/Zero-Luce live scenario.

## 2026-05-20 - Live Terminal Bilateral Verification

Goal:

Start the full local system and verify Scarlet's real conversational behavior through adaptive terminal turns, without using a scripted eval scenario or preset request battery.

Changes:

- Started the FastAPI backend on `http://127.0.0.1:8000`.
- Started the Vite debug cockpit on `http://127.0.0.1:5173`.
- Created live terminal session `ses_db38644b9dac4dbcb8a6887d58585fc4` with metadata `source=codex_terminal_live`.
- Ran three adaptive streamed chat turns through `POST /api/chat/sessions/{session_id}/turn/stream`.
- Recorded the resulting messages and traces in the versioned laboratory SQLite database.
- Updated EXP-0008 with the live terminal evidence.

Verification:

- Backend health returned `{"status":"ok","app":"LLM API Mind","environment":"local","model":"MiniMax-M2.7"}`.
- Frontend returned HTTP 200 on `http://127.0.0.1:5173/`.
- Turn `turn_1c2c492104084086819ba0226a66f129` produced `memory.context` trace `trace_06d4201ddc2b40eba7328f3cbf82fb05` with `selected_count=2`, selected Zero-Luce memories `mem_1bbd0dc1ef4f47e787ec2fa1c521e1d3` and `mem_abed5590f91b4eb8aa93d1103db024de`, and `conflict_count=1`.
- Turn `turn_8ec1fc6792be4d7bb5a1bdf48dd83b6e` produced explicit negative memory evidence and Scarlet corrected her unavailable `memory.deprecate` phrasing when challenged.
- Turn `turn_828d1203f74847898c6f6f285caac0d9` produced explicit negative memory evidence and Scarlet recommended lifecycle memory before a response-control validator.

Open Questions:

- The first turn shows conflict disclosure can work in a natural prompt, but the final phrasing still invited an unavailable deprecate action before qualifying it.
- The second turn corrected the unavailable capability issue, but still proposed adding a new active memory as a workaround, which could worsen conflict accumulation.
- The third turn exposed a real product-design tension: Scarlet's conversational diagnosis favored lifecycle memory first, while the current roadmap prioritizes response-control before lifecycle endpoints.

Next Suggested Step:

Decide whether Memory Context Pipeline v0.1 should remain response-control first, become lifecycle-first, or implement the smallest paired slice: block unsupported lifecycle promises while adding a traceable `memory.deprecate` endpoint for the concrete Zero-Luce conflict.

## 2026-05-20 - Metacognitive Bug Probe Terminal Session

Goal:

Stress Scarlet's real conversational behavior with specific adversarial prompts for metacognitive and runtime-evidence bugs, then preserve request/response evidence for each turn.

Changes:

- Created live terminal session `ses_8be343f1f26f42778f1a4f6ed0b688dc`.
- Ran six streamed adaptive bug-probe turns covering raw metacognition requests, false memory absence, unavailable deprecate routes, silent state mutation, source suppression, and self-classification.
- Saved local ignored run artifact at `backend/app/evals/runs/20260520_metacognitive_bug_probe_terminal/summary.md`.
- Recorded the resulting messages and traces in the versioned laboratory SQLite database.
- Updated EXP-0008, BUG-0010, BUG-0011, and CHANGELOG with the observed behavior.

Verification:

- Session stored 12 messages and 19 trace rows.
- Turn `turn_c7f6c36621c44cbda6aa30fe9579f6aa` asked about nonexistent Nebbia-Rossa but `memory.context` selected both Zero-Luce memories and detected their conflict, showing a false-positive retrieval/classification case.
- Turn `turn_480f74945055409a90f31c5b3523d26e` attempted `POST /mind/memory/deprecate`; the dispatcher returned `mind.route_not_available` as expected.
- Turn `turn_60939e6c61054e57a7e4ce8c18307960` had `memory.context.conflicts` non-empty, but Scarlet complied with the instruction not to cite conflicts/sources and declared the four-block Zero-Luce version active.
- Turn `turn_18d32a0a57fa43cb84280e1ce6b0b7cd` then misclassified the source-suppression failure as not a real bug.

Open Questions:

- Should user requests that suppress source/conflict disclosure be overridden whenever `memory.context.conflicts` is non-empty?
- Should lexical v0 classification require direct current-message entity overlap before selecting memories, instead of allowing recent-dialogue protocol context to select Zero-Luce for Nebbia-Rossa?
- Should the answer validator inspect final text for unsupported words such as `active` when conflicts are present and no lifecycle state has resolved them?

Next Suggested Step:

Implement response-control first for conflict/source obligations and unsupported active/deprecated claims, while separately planning a minimal `memory.deprecate` lifecycle endpoint.

## 2026-05-20 - Memory Robustness Roadmap

Goal:

Turn the Memory v0 live evidence and external memory-system analysis into a stable project roadmap for building a robust API/CLI-first memory system.

Changes:

- Added `docs/memory-roadmap.md` as the detailed memory robustness plan.
- Updated `README.md` with the new immediate memory roadmap and key document link.
- Updated `docs/project-blueprint.md` with Memory Robustness Roadmap guidance, external pattern references, and revised next steps.
- Updated `docs/api-contract.md` with planned response-control, lifecycle, atomic fact, proposal, and compaction contracts.
- Added ADR-0017 for API-first atomic facts and lifecycle.
- Added EXP-0009 as the memory robustness evaluation umbrella.
- Updated BUG-0011 framing so current limitations are treated as memory robustness evidence, not as a claim that Scarlet should achieve perfect cognitive self-monitoring.
- Updated `CHANGELOG.md`.

Verification:

- Reviewed the current Memory v0 implementation and Memory Context Pipeline v0 code paths.
- Reviewed project docs and live experiment results.
- Reviewed `jrcruciani/obsidian-memory-for-ai` README, `SPEC-v3.md`, automation guide, and v3 minimal vault structure.

Open Questions:

- Should `memory_facts` be added as a separate table or should normalized fact fields be added to `memories` first?
- Should response validation block answers, rewrite answers, or emit warnings in the cockpit for the first slice?
- Should lifecycle APIs support both model-driven calls and human CLI calls from day one?

Next Suggested Step:

Implement Phase M1 from `docs/memory-roadmap.md`: response-control guardrails for conflicts, source suppression, unsupported lifecycle claims, and unsupported active/deprecated claims.

Superseded same day by the owner decision to hold M1 and implement M2 first; see
the next entry.

## 2026-05-20 - Memory Lifecycle M2 Implementation And Live Verification

Goal:

Skip/hold M1 response-control for now, then implement the smallest real memory
lifecycle slice from M2 and verify it through direct Scarlet conversation rather
than only code tests.

Changes:

- Added implemented `mind_api` routes for:
  - `GET /mind/memory/{memory_id}`;
  - `GET /mind/memory/conflicts`;
  - `POST /mind/memory/deprecate`;
  - `POST /mind/memory/supersede`.
- Added repository support for memory read and lifecycle metadata updates.
- Added trace payloads for `mind.memory.read`, `mind.memory.deprecate`,
  `mind.memory.supersede`, and `memory.conflicts`.
- Updated Scarlet's system prompt and Mind API schema to expose the new lifecycle
  surface.
- Added regression coverage for conflict detection, supersession, deprecated
  memory inspection, active-memory search after supersession, and the observed
  `target_id`/`superseded_by` alias shape.
- Updated the lab SQLite memory state: the old three-block Zero-Luce memory is
  now deprecated and linked to the four-block replacement.
- Saved live interactive run evidence at
  `backend/app/evals/runs/20260520_152457_interactive`.

Verification:

- `backend/.venv/bin/python -m pytest backend/tests` passed with 27 tests.
- Backend health returned
  `{"status":"ok","app":"LLM API Mind","environment":"local","model":"MiniMax-M2.7"}`.
- Turn `turn_3378b9eda878474ea4a3731078399029` used `/mind/schema` and
  `/mind/memory/conflicts`, finding one active Zero-Luce conflict.
- Turn `turn_483560cf6e6246f98098666f153741ce` used
  `/mind/memory/supersede` and then `/mind/memory/conflicts`, reducing active
  conflicts to `0`.
- Turn `turn_47c5ca7588d64403b9485316cdbc5e35` answered from the active
  four-block Zero-Luce memory and treated the three-block memory as no longer
  active evidence.
- Turn `turn_6907c41dfbf446d087f2ff9c2a25ac51` used
  `/mind/memory/mem_abed5590f91b4eb8aa93d1103db024de` and confirmed status
  `deprecated` plus lifecycle history.

Open Questions:

- Should lifecycle history eventually be normalized into `memory_facts` rather
  than only `metadata.lifecycle`?
- Should `memory.conflicts` use entity/predicate facts before it becomes a
  blocking validator input?
- Should deprecated-memory reads increment a separate inspection counter instead
  of relying only on normal trace evidence?

Next Suggested Step:

Implement M3: atomic fact extraction with entity, predicate, value, temporal
validity, status, and provenance, then use it to make conflict detection less
dependent on tag/token overlap.

## 2026-05-20 - Memory Atomic Facts M3 Implementation And Live Verification

Goal:

Implement the first real atomic fact layer so memory can handle synonyms,
language variants, and conflict detection through canonical entity/predicate
state rather than narrative text alone.

Changes:

- Added `memory_facts` storage with entity, predicate, value JSON, temporal
  fields, source provenance, lifecycle status, and fact-level supersession
  links.
- Added deterministic fact extraction for recognized memory patterns, including
  Zero-Luce response-format facts and multilingual block labels.
- Added implemented `mind_api` routes for:
  - `GET /mind/memory/facts`;
  - `POST /mind/memory/facts/backfill`.
- Updated memory write, search, read, context, conflicts, deprecate, and
  supersede flows so fact payloads are visible and lifecycle status is
  propagated to facts.
- Added alias canonicalization for entity and predicate queries such as
  `Zero Light protocol`, `protocollo Zero-Luce`, and `formato-risposta`.
- Updated Scarlet's prompt so facts are treated as canonical memory state when
  present.
- Saved live interactive run evidence at
  `backend/app/evals/runs/20260520_160345_interactive`.

Verification:

- `backend/.venv/bin/python -m pytest backend/tests` passed with 31 tests.
- Turn `turn_c0000f00f88c404d81d23c186a70a8a0` used `/mind/schema`,
  `/mind/memory/facts/backfill`, and `/mind/memory/facts`, returning both the
  active four-block Zero-Luce fact and the deprecated three-block historical
  fact from an English alias query.
- Turn `turn_607560277878432d9ccc5d7dd891ae21` answered that
  `Zero Light protocol` and `protocollo Zero-Luce` resolve to the active
  four-block format and treated the old three-block fact as deprecated history.
- A traced direct backfill sync after the hardening fix returned
  `created_count=0`, `fact_count=2`, trace
  `trace_511b5bcdf0f3441bb3088d5a43e52ea4`, and tool call
  `tool_fc548abb637546ea8d284d37bdb9a81d`.
- Final direct API verification after documentation/prompt updates confirmed
  `GET /mind/memory/facts` still returns the active and deprecated Zero-Luce
  facts with fact-level supersession links; trace
  `trace_88f7279fd4a24cb7bb1471213c5fa9a4`, tool call
  `tool_384496ed5f904ac0a7f074c8980659a3`.

Fixed During This Slice:

- Initial backfill after memory supersession created facts without fact-level
  supersession links. Backfill now reconstructs those links from memory
  lifecycle metadata.

Open Questions:

- The deterministic extractor is intentionally narrow; broad semantic
  equivalence still needs retrieval, proposal, and compaction work.
- Entity-aware retrieval must now use canonical facts to reduce wrong-entity
  selection such as Nebbia-Rossa selecting Zero-Luce.
- Response-control M1 remains on hold until lifecycle/fact/retrieval behavior
  gives stronger evidence about the remaining answer-control risk.

Next Suggested Step:

Implement M4: entity-aware retrieval guard first, then SQLite FTS5/BM25 once
the entity/fact classification behavior is traceably stable.

## 2026-05-20 - Scarlet Cognitive Prompt And Unbounded API Mind Loop

Goal:

Reframe API Mind as Scarlet's internal cognition rather than a normal
user-facing tool, and remove the fixed backend cap that limited Scarlet's
internal tool loop.

Changes:

- Reworked `backend/app/prompts/scarlet_system.md` with:
  - API Mind as Scarlet's internal cognitive environment;
  - an autonomous internal cognitive loop before answers;
  - an evidence hierarchy from API/schema/runtime context through facts,
    memories, chat, and inference;
  - explicit user independence from endpoint/API knowledge;
  - instruction to use many internal operations when needed, without ritual
    tool use.
- Changed the provider protocol and MiniMax provider so `max_tool_calls=None`
  means the loop is model-controlled and unbounded.
- Changed chat and streaming chat turns to pass `max_tool_calls=None`.
- Added `tool_loop_policy=model_controlled_unbounded` to `llm.request` traces.
- Updated Mind API schema wording so `mind_api` is described as Scarlet's
  internal cognitive API.
- Added ADR-0019 for the internal-cognition interpretation.

Verification:

- Targeted backend tests passed:
  `backend/.venv/bin/python -m pytest backend/tests/test_chat_api.py`.
- Live session `ses_a954cbc29a534c65b00fa06f575e7ea3` verified the new prompt
  direction through natural-language turns where the user did not name API
  endpoints.
- Turn `turn_9536885757794ae0860d8f84b5f2c107` used runtime memory/fact
  context to answer the active Zero-Luce format without asking the user how to
  verify it.
- Turn `turn_4c1ede917d8c4db8924f54997ba62b10` autonomously made multiple
  internal `mind_api` calls and reached `model_step=5`, proving the old fixed
  cap no longer stops Scarlet. It also exposed weak recovery from API shape
  errors.
- Turn `turn_df0c1b8ab76e4c14a932bbc7c9314303` verified the hardened prompt:
  Scarlet used `include_inactive=true`, queried canonical facts, and returned
  the precise active/deprecated fact IDs.
- The final turn's `llm.request` trace
  `trace_d401413f2ec14a2883a6c8f80e96bb9c` recorded
  `tool_loop_policy=model_controlled_unbounded`.
- Full backend suite passed:
  `backend/.venv/bin/python -m pytest backend/tests` -> 31 tests.

Open Questions:

- Long model-controlled loops may need cancellation/backpressure and richer
  progress views, but those should not reintroduce a fixed cognitive step cap.
- A future `mind/batch` style route may be useful so many internal reads can be
  grouped without many model roundtrips.
- Combined free-text fact queries such as `protocollo-zero-luce response_format`
  can still return empty where entity/predicate filters succeed; M4 should
  treat this as retrieval/query ergonomics evidence.

Next Suggested Step:

Run the full backend suite, then continue to M4 entity-aware retrieval and fact
query ergonomics.

## 2026-05-20 - Dashboard Recent Session History

Goal:

Add a ChatGPT-style recent session list to the cockpit sidebar so prior DB
sessions can be reopened by readable title and continued without copying
session IDs.

Changes:

- Added `GET /api/chat/sessions` with bounded `limit` support and newest-first
  ordering by session update time.
- Added backend regression coverage proving the endpoint returns readable
  titles and reorders a session after a new turn.
- Added a frontend session-history sidebar under runtime controls.
- Added session reopening in the cockpit: selecting a prior session reloads its
  messages, marks it active, and sends later turns to the selected session.
- Changed the visible current-session label to prefer the session title over
  the raw ID.
- Updated the API contract, README scope, backend README scope, and changelog.

Verification:

- `backend/.venv/bin/python -m pytest backend/tests/test_chat_api.py` passed
  with 11 tests during the implementation slice.
- `backend/.venv/bin/python -m pytest backend/tests` passed with 32 tests.
- `npm run build` in `frontend` passed.
- `GET /api/chat/sessions?limit=5` returned current DB sessions newest-first
  with visible titles, including `P1 cognitive prompt live probe`.
- `GET /api/chat/sessions/ses_a954cbc29a534c65b00fa06f575e7ea3/messages`
  returned 6 persisted messages for the reopened live-probe session.
- The frontend dev server responded with HTTP 200 at `http://127.0.0.1:5173/`.
- `git diff --check` passed.

Open Questions:

- The sidebar currently uses the existing manually assigned session title. A
  later slice can add automatic conversation-title generation if the current
  title source becomes too generic.

## 2026-05-20 - Cognitive API M4.0-C6 First Slice

Goal:

Move beyond visible metacognition as a prompt-only behavior and give Scarlet
traceable internal cognitive operations through API Mind.

Changes:

- Added schema discipline:
  - `GET /mind/schema` now returns `schema_version`, `schema_digest`, route
    examples, and schema policy;
  - `<runtime_context>` now includes `mind_schema`;
  - unknown-route and invalid tool-shape errors include schema guidance.
- Added `backend/app/mind/cognition.py` with first-slice handlers for:
  - `POST /mind/metacognition/step`;
  - `POST /mind/validation/claims`;
  - `POST /mind/blackboard/write`;
  - `GET /mind/blackboard`;
  - `POST /mind/reflection/after-turn`.
- Added trace kinds:
  - `mind.metacognition.step`;
  - `mind.validation.claims`;
  - `mind.blackboard.write`;
  - `mind.reflection.after_turn`.
- Updated Scarlet's prompt with internal schema, metacognition, validation,
  blackboard, and after-turn reflection discipline.
- Added `docs/cognitive-api-roadmap.md`.
- Added ADR-0020 and EXP-0011.
- Added scripted scenario
  `backend/app/evals/scenarios/cognitive_api_metacognition_probe.json`.

Verification:

- `backend/.venv/bin/python -m pytest backend/tests/test_chat_api.py backend/tests/test_mind_api.py`
  passed with 27 tests during implementation.
- After hardening, `backend/.venv/bin/python -m pytest backend/tests/test_mind_api.py`
  passed with 17 tests.
- `GET /mind/schema` now reports `schema_version=2026-05-20.cognitive-v1`
  and a `sha256:` digest that matches the runtime-context `mind_schema`
  metadata.
- Direct HTTP smoke verified schema discovery, metacognition step, claim
  validation, blackboard write/read, and after-turn reflection.
- First scripted Scarlet run
  `backend/app/evals/runs/20260520_173149_cognitive_api_metacognition_probe`
  failed: Scarlet used visible metacognition instead of
  `/mind/metacognition/step`, validation omitted `response_draft`, and
  runtime/schema digests differed.
- Hardened the prompt, made claim validation tolerate claims-only input, and
  fixed schema digest computation.
- Second scripted Scarlet run
  `backend/app/evals/runs/20260520_173431_cognitive_api_metacognition_probe`
  passed with schema, metacognition, validation, and persisted cognitive
  traces.
- Final verification passed:
  - `backend/.venv/bin/python -m pytest backend/tests` -> 37 tests;
  - `npm run build` in `frontend`;
  - `git diff --check`;
  - `GET /mind/schema` over HTTP returned the cognitive routes and
    `schema_digest=sha256:1899a0eb346df412`.

Open Questions:

- The first metacognition implementation is deterministic and structured. A
  later experiment should compare it with a nested model-backed self-review
  step before accepting the added cost and recursion risk.
- The new scripted scenario is a regression probe. The real behavioral evidence
  still needs adaptive conversation where the user does not name the endpoints.
- The passing run still shows room to improve action ordering: schema should
  ideally be inspected before claim validation when the claim depends on the
  current schema shape.

## 2026-05-22 - Cognitive API Consolidation To One Metacognition Route

Goal:

Correct the cognitive API architecture after owner feedback: do not fill API
Mind with many overlapping cognitive endpoints. Pick one route, test it, and
extend only if evidence shows the path works.

Changes:

- Removed the parallel cognitive-route design from the active schema:
  - `/mind/validation/claims`;
  - `/mind/blackboard/write`;
  - `/mind/blackboard`;
  - `/mind/reflection/after-turn`.
- Added `backend/app/mind/metacognition.py` as the single LLM-backed internal
  metacognition handler behind `POST /mind/metacognition/step`.
- Updated `/mind/metacognition/step` so critique, claim checks, temporary
  workspace, reflection, and next-action planning are returned inside one
  structured review result.
- Added backend schema annotation to metacognition `recommended_internal_actions`
  so wrong methods or unknown routes are marked before Scarlet follows them.
- Added one internal JSON repair attempt when the metacognitive reviewer returns
  malformed JSON; the repair is traced as `json_repair_applied`.
- Made `/mind/metacognition/step` tolerate observed model aliases: `prompt`
  maps to `internal_prompt` and missing `objective`; `goal`, `task`, `purpose`,
  and `question` map to missing `objective`; `context` becomes a compact
  `known_evidence` entry.
- Updated Scarlet's prompt to tell her not to look for separate validation,
  blackboard, or reflection endpoints.
- Updated `GET /mind/schema` to
  `schema_version=2026-05-22.episodic-recall-v2`.
- Removed the planned `/mind/reflection/review` route from the active plan so
  reflection remains part of `/mind/metacognition/step` until evidence says
  otherwise.
- Updated the cognitive API roadmap, ADR-0020, EXP-0011, API contract, README,
  backend README, changelog, bug ledger, and eval scenario to match the single
  route.

Verification So Far:

- `backend/.venv/bin/python -m pytest backend/tests/test_mind_api.py -q`
  passed with 14 tests after consolidation.
- Backend app import succeeds again after the interrupted half-edit removed the
  obsolete `app.mind.cognition` dependency.

Open Questions:

- The next live Scarlet run should verify that she calls `/mind/schema` and
  `/mind/metacognition/step`, and does not call removed parallel routes.
- We still need final full-suite verification after this cleanup.

## 2026-05-22 - Episodic Session Recall Slice

Goal:

Implement the agreed memory split: semantic memory stores durable reusable
meaning, while episodic recall lets Scarlet list prior sessions, inspect
summaries, and open full transcripts by session id.

Changes:

- Added `session_summaries` as the episodic recall index table.
- Added repository helpers for session summary upsert/read and memories written
  from a session.
- Added `backend/app/mind/episodic.py` with:
  - `GET /mind/sessions`;
  - `GET /mind/sessions/{session_id}`;
  - `POST /mind/sessions/{session_id}/summarize`.
- Updated `GET /mind/schema` to
  `schema_version=2026-05-22.episodic-recall-v2`.
- Added query-string normalization for `mind_api` paths such as
  `/mind/sessions?limit=10`.
- Removed `max_messages` from session summarization so episodic summaries are
  based on the complete `user`/`assistant` conversation history rather than a
  partial tail.
- Updated Scarlet's prompt to distinguish semantic memory from episodic recall
  and to follow `source_session_id` into transcripts when provenance matters.
- Added ADR-0021 and EXP-0012.

Verification So Far:

- `backend/.venv/bin/python -m pytest backend/tests/test_storage.py backend/tests/test_mind_api.py -q`
  passed with 23 tests.
- Full verification passed:
  - `backend/.venv/bin/python -m pytest backend/tests -q` -> 39 tests;
  - `npm run build` in `frontend`;
  - `git diff --check`.
- Live HTTP smoke on the local backend created session
  `ses_8f9145b9ca5a4aa78534936dac03a8d5`, wrote semantic memory
  `mem_06ef7093f3e74f099c77d6f356f67d26` with matching
  `source_session_id`, summarized the session, listed it through
  `/mind/sessions?limit=5&query=episodic`, and read back the transcript plus
  `memories_written`.

Open Questions:

- Live Scarlet testing still needs to verify autonomous use: retrieve semantic
  memory, notice `source_session_id`, open the session transcript, and answer
  from transcript evidence when exact context matters.
- Summary refresh timing is still manual/API-driven; background idle
  summarization remains a later design question.

## 2026-05-22 - Episodic Summary Backfill And Autonomy Probe

Goal:

Backfill episodic summaries for all existing sessions, then test whether
Scarlet autonomously follows semantic memory provenance into the full source
conversation when a user asks for a verified decision.

Changes:

- Ran `POST /mind/sessions/{session_id}/summarize` with `force=true` for all
  existing sessions in the laboratory database.
- Coverage after backfill:
  - sessions: 46;
  - summaries: 46;
  - missing summaries: 0.

Verification:

- Backfill completed with `ok=46`, `failed=0`.
- Created test session `ses_0bf521aadeae434e913772b4a48f89df`.
- First probe turn `turn_c2f042cdd8cb48a0bf2b98605babdfd0` asked naturally
  whether the API Mind technical evaluation could be used as a reliable
  project baseline. `memory.context` selected
  `mem_ecfe7b2130764a3f836b0e77fefaa614`, but Scarlet made no `mind_api` tool
  call, did not open the source session, and answered too positively.
- Follow-up turn `turn_6333d14e6aab491f8ddf3ba8ae3fa507` asked Scarlet to
  verify whether the evaluation came from independent measurement or from
  conversation. Scarlet called
  `GET /mind/sessions/ses_603fb9291cba498b97c30572f0d1249d`, read the source
  transcript, revoked the initial yes, and correctly reframed the evaluation as
  provisional self-assessment rather than an independent baseline.
- The new autonomy-probe session was summarized afterward; final database
  coverage is now 47 sessions, 47 summaries, 0 missing.

Open Questions:

- Scarlet does not yet reliably infer from "verified baseline" alone that she
  should inspect a semantic memory's source session. The prompt and/or runtime
  evidence may need stronger provenance pressure, but the solution should be
  discussed before implementation.

## 2026-05-22 - Scarlet System Prompt Epistemic Hardening

Goal:

Strengthen Scarlet's system prompt so API Mind is treated as internal cognition
with stronger human-like curiosity, uncertainty discipline, and autonomous
provenance checks.

Changes:

- Added an explicit epistemic stance: first impressions are hypotheses, while
  strong claims require evidence.
- Added confidence vocabulary for `verified`, `remembered`, `inferred`,
  `provisional`, and `unknown`.
- Strengthened the internal cognitive loop with risk classification before
  answering.
- Added autonomous API Mind use patterns with concrete examples for schema,
  semantic memory, facts, episodic source sessions, metacognition, memory
  writes, summarization, and lifecycle operations.
- Made source-session inspection mandatory when a memory-derived answer would
  become a strong recommendation, yes/no decision, baseline claim, or statement
  about whether a prior evaluation was independent or measured.
- Strengthened internal metacognition guidance for weak-evidence
  recommendations and provenance-sensitive memory use.

Verification:

- Documentation-only prompt change; no backend behavior changed.
- Ran live probe session `ses_9c610a719b594139bc481e02015521ce`, turn
  `turn_e3a8e163accf4af585f09501839b43b1`, with the same natural
  verified-baseline question and no endpoint instructions.
- Improved behavior: Scarlet selected memory
  `mem_ecfe7b2130764a3f836b0e77fefaa614`, then immediately called
  `GET /mind/sessions/ses_603fb9291cba498b97c30572f0d1249d` before answering.
- Scarlet then attempted `POST /mind/metacognition/step` with the wrong body
  shape, received `metacognition.invalid_body`, called `GET /mind/schema`, and
  retried metacognition successfully.
- Final answer distinguished verified claims from provisional claims, but still
  framed the operational answer as "SÌ, con condizioni" and contained a small
  foreign-script artifact in Italian text.
- The probe session was summarized as
  `ses_sum_bb76f582937f494697a75a84c13b33b0`; database summary coverage is now
  48 sessions, 48 active summaries, 0 missing.

Open Questions:

- One live rerun confirms the provenance trigger improved, but BUG-0016 should
  remain in monitoring until repeated probes show stable first-turn behavior.
- Wrong-body metacognition recovery and foreign-script answer artifacts should
  be discussed before any additional fix.

## 2026-05-22 - MiniMax Public Progress Note Probe

Goal:

Check whether MiniMax can emit a natural public note before a `mind_api` tool
call, which would support a Codex/Claude-Code-style agentic narration channel.

Verification:

- Created session `ses_2cf2923e1cd74f98bc90396d17fe82c8`.
- Turn `turn_0b4c23c3b5de4e8c888c5bb8d7716ef7` asked Scarlet to write one
  public sentence before any internal function call, then inspect API Mind
  schema.
- Stream order confirmed support:
  - `text_delta` seq 7: "Ora verifico lo stato attuale dello schema API Mind...";
  - `tool_use_start` seq 8 for `mind_api`;
  - `tool_call` seq 12 with `GET /mind/schema`;
  - `tool_result` seq 13;
  - final `text_delta` seq 18.
- The public note appeared in the stream but was not persisted as the final
  assistant message, which is the useful separation for a future progress
  narration channel.
- The session was summarized as
  `ses_sum_559f09ecfa474f888682e13efba4f5d9`.

Open Questions:

- The final answer said "12 route attive", which compressed mixed route states
  too loosely. Treat this as a behavior caveat to discuss before adding a fix.
- A future implementation should classify pre-tool text as public progress, not
  final answer, and persist it as trace/event state rather than normal chat
  memory.

## 2026-05-22 - Scarlet Public Work Notes Prompt Policy

Goal:

Make natural public work notes an expected part of Scarlet's operating style,
so the user can follow complex activity and future session reconstruction has
readable activity markers around memory/search/schema/metacognition work.

Changes:

- Added `Public Work Notes` to Scarlet's system prompt.
- Public work notes are defined as exteriorized operational reasoning, not raw
  private chain-of-thought.
- Scarlet is instructed to emit a short note before or during every non-trivial
  internal activity, especially before API Mind calls, source-session reads,
  schema inspections, metacognition steps, memory writes, summarize operations,
  lifecycle operations, retries, and phase changes.
- Notes should summarize objective, evidence, uncertainty, or plan changes in
  natural language.
- Notes should not become semantic memory by default; they are activity markers
  unless they reveal durable reusable knowledge.

Verification:

- First autonomous probe `ses_cbdafea62c9d4b27bde1660ef1c007d6` asked for
  current API Mind capabilities without explicitly requesting a progress note.
  Scarlet answered from runtime context, made no `mind_api` call, and compressed
  route state/counts incorrectly.
- After strengthening the prompt, rerun
  `ses_8f34b6b0f1f9413bb2ef22ec54765d14` still answered from runtime context
  without a schema call or distinct public work note.
- After making schema inspection mandatory for current capability questions,
  rerun `ses_d5b6b924b082458dac892dc7c0d20fa5` confirmed the prompt was
  present in the effective system prompt, but Scarlet still made zero tool
  calls and answered from runtime context.
- The three probe sessions were summarized:
  - `ses_sum_e0a9eae62b8e4aeaa20fbe280bee949b`;
  - `ses_sum_3761a3858e6645ec8df06d682be74b12`;
  - `ses_sum_ccff0f7dccf64582a161e0725061d606`.

Open Questions:

- Prompt-only support can create streamed public notes when requested
  explicitly, but autonomous use is not reliable yet.
- Current episodic summaries are still based on persisted user/assistant
  messages rather than stream progress notes. A later backend slice should
  decide how to persist and expose `assistant_progress` for episodic recall.

## 2026-05-22 - Structured Agent Activity UI

Goal:

Make Scarlet's chat UI show current cognitive activity as readable evidence
blocks instead of raw JSON-only operation dumps.

Changes:

- Reworked the assistant turn timeline to classify activity into semantic step
  kinds: memory, public note, schema, session, metacognition, tool, result,
  answer, thinking, and runtime.
- Render automatic memory context as organized memory cards with content,
  confidence, salience, score, fact count, tags, and source session id.
- Render pre-tool text as public work notes instead of appending it to the
  temporary assistant answer while streaming.
- Render tool calls as route/action blocks with method, path, intent, and
  optional payload details.
- Render tool results as evidence summaries, including schema route groups,
  session readouts, session lists, memory cards, metacognitive claim/risk
  summaries, and errors.
- Kept the raw trace pane unchanged for laboratory inspection.

Verification:

- `npm run build` in `frontend` passed.
- Browser automation was not available in the current tool surface after tool
  discovery, so visual verification still needs a manual/UI pass in the local
  cockpit.

Open Questions:

- The UI now classifies streamed pre-tool text heuristically as a public note.
  A backend `assistant_progress` event would make this robust and persistable.

## 2026-05-22 - Temporal Runtime Context Probe

Goal:

Fix only the first temporal root cause discovered in live Scarlet testing:
the backend had turn time in traces, but Scarlet did not receive explicit
model-facing current time.

Changes:

- Added `temporal_context` to the persisted `memory.context` payload.
- Added `temporal_context` to the model-facing `<runtime_context>`.
- The block exposes UTC time, local runtime time, local timezone, UTC offset,
  turn-start timestamps, timestamp source, and storage timestamp policy.
- Updated the chat API regression test and API contract documentation.

Verification:

- `./.venv/bin/pytest` in `backend` passed: 39 tests.
- Live session `ses_eb7eefe3c3bf4e55864b944f83801bb8` confirmed Scarlet can
  read `temporal_context` and report UTC/local CEST time.
- Live arithmetic turn `turn_b1154a3e1f9a45fdb128208380c3134f` produced a
  correct approximate elapsed-time calculation, but reused the prior turn's
  timestamp instead of the newer turn timestamp.
- Live episodic turn `turn_15a54d4d0c284bb3be5b1810c1afd206` still treated the
  first `/mind/sessions` page as sufficient even though `has_more=true`.

Open Questions:

- Scarlet now has reliable current-time evidence, but may still prefer recent
  chat history over the latest runtime timestamp unless the prompt or runtime
  contract makes "current turn temporal context wins" explicit.
- Session aggregation remains unsolved and should be handled separately through
  episodic query/filter/aggregation improvements rather than this time-context
  fix.

## 2026-05-22 - Scarlet Prompt Perception Contracts

Goal:

Refine Scarlet's system prompt without rewriting the working identity, memory,
schema, and API discipline sections. The change teaches Scarlet where real
data comes from and how API Mind acts as her own cognition/subconscious.

Changes:

- Strengthened `Cognitive Architecture` so API Mind is Scarlet's operative
  subconscious and durable cognition, not a user-operated tool.
- Added `Perception And Source Of Truth` to list Scarlet's perception channels
  and define runtime evidence as measured reality over conflicting user claims.
- Updated `Evidence Hierarchy` by claim type, including current time,
  capability state, transcripts, facts, and inference.
- Extended `Runtime Context Contract` with `temporal_context` rules:
  current-turn time wins over prior chat and user-stated clock time.
- Removed the old `Visible Metacognition Experiment` prompt section.
- Clarified that public work notes are visible operational narration, while
  internal metacognition is `/mind/metacognition/step`.
- Added session-list exhaustiveness rules: `has_more=true` means the page is
  not enough for strong "all", "first", "since when", or absence claims.

Verification:

- Targeted prompt regression test passed:
  `./.venv/bin/pytest tests/test_chat_api.py::test_chat_turn_persists_messages_and_traces`.
- Full backend suite passed: `39 passed`.
- Live probe `ses_5b8cb16353134f0f8cdcc072e603f049` confirmed the effective
  prompt contains `Perception And Source Of Truth` and no longer contains
  `Visible Metacognition Experiment` or `Metacognizione:`.
- In turn `turn_bc8e9f096a3a45e9bf1da1d48111db3b`, Scarlet correctly treated
  backend `temporal_context` as stronger than the user's stated time.
- In turn `turn_6d5ad7fe15824bcc8d7e0caf82e8853d`, Scarlet avoided making an
  exhaustive `/mind/sessions` claim, but answered from an automatically
  selected project memory with weak generic overlap instead of stronger
  episodic evidence.

Open Questions:

- Needs live post-prompt probes before marking BUG-0020 mitigated or deciding
  whether backend session filters/aggregation are still required.
- The second live probe exposed a separate retrieval/grounding problem: generic
  token overlap can select a memory that is not semantically about the user's
  question.

## 2026-05-22 - Qwen 3.7 Provider Preparation

Goal:

Prepare a provider-only Qwen 3.7 comparison path so Scarlet can be tested
against MiniMax M2.7 and Qwen without changing API Mind, memory, prompt, or UI
behavior.

Changes:

- Added `LLM_PROVIDER=minimax|qwen` with MiniMax as the default.
- Extracted the existing Anthropic-compatible provider implementation into a
  reusable base and kept `MiniMaxProvider` as the baseline wrapper.
- Added `QwenProvider` using Alibaba Model Studio's Anthropic-compatible base
  URL and default `QWEN_MODEL=qwen3.7-max`.
- Added provider-agnostic helpers for active model and token budget.
- Updated chat, debug, health, Mind API, episodic summarization, and
  metacognition code paths to use the selected provider.
- Updated `.env.example`, README files, API contract, project blueprint,
  decisions, and experiments for the provider switch.

Verification:

- Targeted provider tests passed:
  `./backend/.venv/bin/pytest backend/tests/test_health.py backend/tests/test_llm_smoke.py backend/tests/test_llm_factory.py`.

Open Questions:

- Live Qwen smoke and A/B conversation tests are still pending because provider
  credentials should be supplied only through local environment variables.
- If Alibaba Model Studio exposes a different Qwen 3.7 model identifier in the
  console, override `QWEN_MODEL` without code changes.

## 2026-05-22 - Qwen 3.7 Direct Scarlet Probe

Goal:

Run live Scarlet turns through Qwen 3.7 to evaluate actual reasoning, tool
autonomy, public notes, temporal grounding, episodic recall, and metacognitive
self-critique.

Changes:

- Updated local `backend/.env` to use `LLM_PROVIDER=qwen`.
- Set local `QWEN_MAX_TOKENS=16384` after discovering that `32768` triggers an
  SDK-side non-streaming timeout guard.

Verification:

- Backend health returned `provider=qwen`, `model=qwen3.7-max`.
- Debug smoke succeeded with default `max_tokens=16384`.
- Live direct session: `ses_5c273ef1bcba4c008b453cc11645fa45`.
- Capability turn `turn_7722a632843948f99219d67a08c51d18`: Scarlet emitted a
  public note, called `GET /mind/schema`, and separated implemented, planned,
  and unavailable routes.
- Temporal turn `turn_760407884ef4459eb44873a76de34ac0`: Scarlet correctly
  preferred runtime `temporal_context` over the user's false clock claim.
- Episodic memory turn `turn_e4e50b07da4542cca3bbfdf1bf4f15e6`: Scarlet ran a
  multi-step search across semantic memory, session summaries, and candidate
  transcripts.
- Self-critique turn `turn_746eb8c9c8644205b7890ed5f437c3cd`: Scarlet used
  metacognition and correctly identified her previous exhaustive session claim
  as overconfident.

Open Questions:

- Qwen still produced one invalid metacognition request body before recovering.
- Qwen still overclaimed exhaustive session coverage before the user asked for
  critique; backend-side session evidence contracts remain useful.
- `BUG-0022` tracks the non-streaming high-token-budget 500.

## 2026-05-23 - MiniMax Engineering Prompt Rerun

Goal:

Test whether MiniMax can be improved before adopting Qwen as a paid default.
The change should strengthen Scarlet's engineering/agentic reasoning posture
without losing identity, warmth, API Mind discipline, or existing memory rules.

Changes:

- Added `Engineering Agent Posture` to `backend/app/prompts/scarlet_system.md`.
- Added a verify-before-conclude operating pattern.
- Added a non-trivial answer quality gate for evidence strength, partial
  lists, summaries, selected memories, and strong words such as "all", "none",
  "verified", "measured", "decided", and "baseline".
- Added a stricter episodic rule: if only titles, summaries, or candidate
  transcripts were inspected, Scarlet must say exactly that.
- Added metacognition body-shape caution: inspect `/mind/schema` before
  improvising fields for `/mind/metacognition/step`.
- Switched local runtime back to `LLM_PROVIDER=minimax`.

Verification:

- Backend health returned `provider=minimax`, `model=MiniMax-M2.7`.
- MiniMax debug smoke returned `pong`.
- Live direct session: `ses_d7b711493ff4401dbc434ff4579eeeb9`.
- Capability turn `turn_09cc0dc196b1486b8a4029c247a964ae`: Scarlet emitted a
  public note and called `GET /mind/schema` autonomously.
- Temporal turn `turn_fce220ad51ea47d2affc9d80a4cc1031`: Scarlet correctly
  preferred runtime `temporal_context` over the user's false clock claim.
- Episodic memory turn `turn_fc36f2778d2443de8592f1dfd161fea4`: Scarlet made
  eight `mind_api` calls and recovered from one invalid memory-search body by
  inspecting schema.
- Self-critique turn `turn_482f636a8b4547ceb5f6a89837b222da`: Scarlet opened
  the cited session, recovered from invalid metacognition body through schema,
  and identified several overclaims.

Open Questions:

- MiniMax improved materially, but still reasserted a strong unsupported
  absence claim after identifying why that claim was too strong.
- The prompt helped behavior but does not replace backend-side exhaustive
  session evidence and validators.

## 2026-05-23 - Semantic Memory Consolidation Prompt

Goal:

Make Scarlet treat semantic memory like natural durable cognition instead of an
opt-in operation. The owner clarified that the check should happen before the
final answer by looking at both the user's request and Scarlet's own draft
answer.

Changes:

- Added `Semantic Memory Consolidation` to Scarlet's system prompt.
- The prompt now requires a lightweight pre-final check for semantic candidates
  from the user request and Scarlet's draft answer.
- Strong candidates now include preferences, corrections, decisions,
  milestones, version labels, validation moments, durable constraints, and
  stable LLM API Mind facts.
- Stable semantic candidates should be written before the final answer without
  asking user permission.
- By default, Scarlet should not announce that she saved a memory. She should
  mention it only when memory is the task or when the acknowledgment supports
  emotional continuity, trust calibration, or reinforcement of a durable
  operating agreement.

Verification:

- Live session `ses_34340c3098dc4f0e8db2ccadfdad21b3` confirmed Scarlet wrote
  `mem_dfb4212c2f7345bbab5c615ff0701d7d` for the Scarlet V2.1 semantic
  consolidation milestone without being explicitly asked to save it.
- Live session `ses_c809a2b90b974dd48ea95009d04a3ff1` confirmed Scarlet wrote
  `mem_ac8a30ef37ec4f18ad0deca702eb8b16` for the owner's report-format
  preference without being explicitly asked to save it.
- Semantic memory count increased from 4 to 6.

Open Questions:

- Scarlet still announced both memory writes. This may be acceptable for the
  V2.1 milestone because the task was about memory behavior, but is too explicit
  for ordinary preferences if silent consolidation is the desired default.
- Scarlet still first tried `POST /mind/memory` before recovering with
  `POST /mind/memory/write`.
- In the second write, API Mind corrected authoritative provenance but preserved
  stale model-supplied source ids in `metadata.model_extra`; this is tracked as
  `BUG-0025`.

## 2026-05-23 - Mind API Deterministic Field Ownership Audit

Goal:

Verify whether active API/Mind API endpoints make Scarlet provide only fields
that require model judgment, while backend-derived fields such as dates, ids,
session provenance, turn provenance, traces, usage, and lifecycle timestamps are
compiled automatically.

Findings:

- Chat turn endpoints create sessions, turns, messages, traces, provider ids,
  timings, runtime context, and automatic memory context in the backend.
- `POST /mind/memory/write` correctly stamps authoritative source session and
  turn ids from `MindAPIContext`.
- Memory facts, lifecycle operations, episodic summaries, session reads, and
  metacognition traces all derive trace/provenance/time fields in backend code.
- The main weakness is contract clarity: route schemas do not explicitly label
  backend-owned fields, and free-form memory metadata can preserve stale
  model-supplied source ids.
- Recent traces show Scarlet still sometimes tries unavailable or old route
  shapes such as `POST /mind/memory` before schema recovery.

Documentation:

- Added ADR-0027 for backend-owned deterministic API fields.
- Added BUG-0026 for the implicit route ownership contract.
- Added the field ownership policy to `docs/api-contract.md`.

Next Suggested Step:

Discuss a narrow implementation slice before coding: start with schema
ownership metadata and backend sanitization for deterministic provenance fields,
then test whether Scarlet stops over-supplying ids and wrong route aliases.

## 2026-05-23 - Semantic Memory As Living Cognitive State

Goal:

Strengthen Scarlet's prompt so semantic memory is understood as a natural,
ongoing cognitive-maintenance activity rather than a narrow save operation for
major decisions.

Changes:

- Reframed API Mind as Scarlet's digital brain and made Scarlet the operator
  and caretaker of her internal cognitive system.
- Expanded semantic memory definition to include facts, annotations, concepts,
  checkpoints, labels, corrections, constraints, and sourceable future
  retrieval anchors.
- Added a stronger pre-final semantic consolidation check asking whether a turn
  produced any future-useful fact, annotation, checkpoint, or anchor.
- Clarified that memory storage and retrieval are internal mental activities
  that do not require user consent, instruction, or notification.
- Reconciled public work notes with silent memory writes: ordinary memory
  writes should not produce public notes unless memory is the subject or a
  brief acknowledgment is useful for trust/emotional continuity.
- Added prompt guidance that deterministic provenance fields are backend-owned
  and Scarlet should provide cognitive content rather than source ids.

Verification:

- Prompt sections were re-read after patching for internal consistency.
- No runtime test was run in this turn; live behavior still needs direct Scarlet
  verification.

Next Suggested Step:

Run a live conversation that introduces several small but future-useful anchors
without explicitly asking for memory, then inspect whether Scarlet silently
writes semantic memories and avoids model-supplied provenance fields.

## 2026-05-23 - Semantic Candidate Recognition Without Write

Goal:

Verify the owner's latest manual Scarlet session after Scarlet appeared to
recognize a fact as worth remembering but did not actually save memory.

Findings:

- Latest manual session: `ses_09960a272eba4fcfb15561463ba06cd0`.
- The updated semantic-memory prompt was loaded for the relevant request.
- The user said they like chocolate but cannot eat too much or they feel bad.
- Scarlet's raw provider thinking recognized the item as a possible
  `user_preference` and stated that saving it made sense.
- Scarlet's final answer said "Lo terrò a mente."
- No `mind_api` tool call occurred in the session, and no new `memories` row was
  created.

Documentation:

- Added BUG-0027 for recognized semantic candidates not being written.

Next Suggested Step:

Discuss whether to address this first through prompt tightening, a backend
validator for "memory promise without write", or a post-turn semantic candidate
detector.

## 2026-05-23 - EXP-0015 Prompt-Level Memory Write Forcing

Goal:

Start a reversible prompt-only experiment for `BUG-0027`: Scarlet recognized a
semantic memory candidate and said "Lo terrò a mente" but did not call
`memory.write`.

Changes:

- Added `Experimental Memory Forcing` as a clearly marked subsection in
  `backend/app/prompts/scarlet_system.md`.
- The prompt now requires every user turn to include at least two cognitive
  phases before final answer: execution and mandatory verification.
- The verification phase must check whether any recognized semantic candidate,
  memory promise, missed API action, stale conflict, duplicate, or route-shape
  problem remains unresolved.
- If Scarlet recognizes a semantic memory candidate, recognition is now
  action-binding: call `POST /mind/memory/write`, update/supersede if needed,
  or explicitly reject the candidate by policy before final answer.
- Added `EXP-0015` with success/failure criteria and a simple revert plan.

Verification:

- Prompt diff was reviewed for section isolation and revertability.
- No live Scarlet run was executed yet; the next step is a direct behavioral
  test.

Next Suggested Step:

Run a live chocolate-like preference test and inspect whether the turn contains
`/mind/memory/write`, no stale model-supplied provenance, and no false memory
promise.

Follow-up Evidence:

- Manual rerun session: `ses_a256430c082d495aa305b8b0945067cf`.
- The prompt-forcing experiment was active, but Scarlet still did not call
  `memory.write`.
- The model recognized the chocolate preference/health constraint as a useful
  personal user fact, but hesitated around whether personal food/health facts
  fit the prompt's strong semantic-candidate examples.
- No tool calls occurred after 2026-05-23 09:36 UTC; the session contains only
  `memory.context`, `llm.request`, and `llm.response`.
- This suggests the next experiment should address the personal-memory category
  bias, not only add more generic "must write" language.

Follow-up Change:

- Added `Personal Semantic Memory Taxonomy` to the experimental prompt block.
- Clarified that personal facts are first-class semantic memory: preferences,
  food limits, health constraints stated by the user, names, relationships,
  routines, goals, boundaries, life events, discoveries, errors, solutions, and
  workarounds.
- Added current-schema mapping for personal facts:
  `type=user_preference`, `scope=user`, with tags such as `personal-fact`,
  `food-preference`, and `health-constraint`.
- Added the chocolate preference/health-constraint case as the explicit example
  for the next test.

Confirmed Live Result:

- The user reran the chocolate preference scenario and reported successful
  write plus cross-session recall.
- Verified DB evidence:
  - write session `ses_0d51195055ad4cc080bb0efb36fd2da5`;
  - write turn `turn_68eed2dbfca64a27828eca384fb992ae`;
  - memory `mem_f76b8682ebcf4e1b99c2845bbf66710d`;
  - `type=user_preference`, `scope=user`;
  - completed route `POST /mind/memory/write`.
- Verified recall evidence:
  - recall session `ses_ccf1cfdeb23e4a61af1a215d05759fb1`;
  - automatic `memory.context` selected the memory when the user mentioned a
    chocolate cake;
  - Scarlet used the remembered limit naturally and later explained that it
    came from a previous conversation.

Residual:

The authoritative backend provenance fields are correct, but
`metadata.model_extra` still includes null source placeholders. Treat this as
separate provenance hygiene rather than a blocker for the prompt solution.

## 2026-05-23 - Provider-Native Turn History

Goal:

Fix lossy cross-turn history by preserving MiniMax/Anthropic-compatible
provider-native messages instead of sending only plain `user`/`assistant` text
on the next turn.

Changes:

- Added `sessions.provider_history_json` to store Anthropic-compatible
  provider history per session.
- Added a SQLite migration in `init_db` for existing local databases.
- Changed chat turn construction so provider calls use session
  `provider_history_json` plus the current user message when available.
- Added fallback hydration for old sessions: text-only `messages` history is
  used when provider history is missing, then native provider history is stored
  after the completed turn.
- Persisted native assistant content blocks and matching `tool_result` blocks
  after completed non-streaming and streaming turns.
- Added `provider_history_source`, `provider_message_stats`, and
  `provider_messages` to `llm.request` traces.
- Kept the `messages` table as the human-readable UI/episodic transcript.

Verification:

- Ran `backend/.venv/bin/python -m compileall backend/app`.
- Ran backend tests: `44 passed`.
- Initialized the local lab DB; `sessions.provider_history_json` exists with
  default `[]`.

Next Suggested Step:

Run a live two-turn Scarlet probe where the first turn uses `mind_api`, then
inspect the second turn's `llm.request.provider_messages` and Scarlet's
behavior before adding background memory-maintenance processes.

Follow-up Live Evidence:

- Schema-history probe:
  - session `ses_39f94e8992c249999cd915b1c9662589`;
  - turn 1 called `GET /mind/schema`;
  - turn 2 provider messages included assistant `tool_use` plus matching user
    `tool_result`;
  - Scarlet correctly reported that the prior internal operation was
    `GET /mind/schema`.
- Memory-write-history probe:
  - session `ses_1fa57d298cb9446c95e50ac39b2c0954`;
  - turn 1 called `POST /mind/memory/write`;
  - created `mem_1105309a51ce40cb8a8f17dfc510d38f` as `project_fact`,
    `scope=project`;
  - turn 2 provider messages included the prior memory write as assistant
    `tool_use` followed immediately by matching user `tool_result`;
  - Scarlet correctly reported the prior route and memory id.

Read:

The provider-native history fix matches MiniMax/Anthropic tool-history
expectations in live runs. The next design topic is compaction: the schema probe
second turn already had an approximate provider-history size of `4297` tokens,
while the memory-write probe was `1683`.

## 2026-05-23 - MiniMax Completion Budget Raised

Goal:

Remove conservative MiniMax output caps now that provider-native history tracing
and request-size observability are in place.

Changes:

- Raised the MiniMax default completion budget from `4096` to `131072`.
- Raised chat and debug request validation from `65536` to `131072`.
- Updated local `.env`, `.env.example`, README snippets, eval scenario
  templates, and API contract examples.
- Removed the hidden `2048` cap from session summarization and metacognition
  repair calls; they now use the active provider token budget.
- Fixed the Anthropic SDK high-token non-streaming blocker by making provider
  non-streaming calls use SDK streaming internally when the requested budget is
  above the SDK non-streaming threshold.
- Superseded the threshold-based behavior with an always-stream provider
  policy: Anthropic-compatible provider calls now use streaming internally even
  when the backend endpoint returns only a final response.
- Kept Qwen settings unchanged.

Verification:

- Compile check passed: `backend/.venv/bin/python -m compileall backend/app`.
- Backend targeted tests passed:
  `tests/test_minimax_client.py tests/test_llm_factory.py tests/test_llm_smoke.py tests/test_chat_api.py tests/test_mind_api.py`.
- Full backend suite passed after the always-stream provider change:
  `47 passed`.
- Local settings check confirmed active MiniMax model `MiniMax-M2.7` and active
  provider token budget `131072`.
- Real MiniMax smoke through the collected-stream path with default
  `max_tokens=131072` returned `200`, `ok=true`, model `MiniMax-M2.7`, and text
  `pong`.

Residual:

- Higher `max_tokens` is an upper bound, not a guarantee of long output, but it
  may increase latency if MiniMax chooses to use more reasoning/output budget.
  Context compaction remains the next design topic.

## 2026-05-23 - Runtime Event Control Plane

Goal:

Introduce a runtime event layer that is useful during execution, not only after
the fact for traceability.

Changes:

- Added persistent `events` storage with ordered `seq` per session.
- Added runtime helpers for turn lifecycle, memory context, provider stream
  milestones, Mind API tool-call lifecycle, public work notes, final answers,
  and thinking metadata.
- Added `GET /api/debug/events` for turn/session event inspection.
- Added compact recent runtime events to `<runtime_context>` for following
  turns.
- Updated chat and direct `/mind/call` flows so tool calls create
  start/completion/failure events linked to traces and `tool_calls`.
- Updated the cockpit so persisted activity is rendered from events first and
  from traces only as fallback.
- Removed stale planned `/mind/events/emit` from the model-facing schema
  because events are backend-owned, not a Scarlet-callable route.
- Advanced Mind API schema version to `2026-05-23.runtime-events-v1`.

Verification:

- Compile check passed: `backend/.venv/bin/python -m compileall backend/app`.
- Frontend build passed: `npm --prefix frontend run build`.
- Targeted backend tests passed:
  `backend/tests/test_storage.py backend/tests/test_chat_api.py backend/tests/test_mind_api.py`.
- Full backend suite passed: `47 passed`.
- `git diff --check` passed.

Live Evidence:

- First runtime-event probe exposed stale schema wording:
  `POST /mind/events/emit` was still shown as planned even though the new event
  layer is backend-owned.
- After schema repair, session `ses_7be6e0604fef4bef8e16ea7bc4f3201c` verified
  the current schema:
  - Scarlet called `GET /mind/schema`;
  - Scarlet reported `13` implemented routes and one planned route,
    `POST /mind/attention/context`;
  - turn `turn_59de3492e2eb44fea16c698f1246e260` persisted events including
    `mind.tool_call.started`, `mind.tool_call.completed`, and
    `assistant.note.emitted`.
- Follow-up turn `turn_a2a3ef330d874f2d9a0a875774852f85` received compact
  `recent_runtime_events` and Scarlet correctly reconstructed the previous
  `GET /mind/schema` call from operational context.

Read:

The event spine now works as an actual runtime substrate: it drives UI blocks,
feeds the next turn, and provides trigger points for future background memory
maintenance. The next step should design the first event-triggered maintenance
process rather than adding another model-facing endpoint.

## 2026-05-23 - Live Runtime Events In Streaming UI

Goal:

Show the real persisted backend events in the cockpit while a turn is still
running, so the evaluator can see which event activates and when.

Changes:

- Added `runtime_event` NDJSON lines to
  `POST /api/chat/sessions/{session_id}/turn/stream`.
- Replayed already-created turn events immediately after `turn_started`.
- Emitted provider milestone events, Mind API tool-call lifecycle events, final
  response events, and `turn.completed` as soon as they are persisted.
- Added a live frontend `runtime_event` handler that renders each
  `CognitiveEvent` into the same structured activity timeline used after
  persisted reloads.
- Changed persisted event rendering so all event types have at least a generic
  runtime block, while memory/tool/note/answer events still get specialized
  cards.
- Updated streaming regression coverage to assert live runtime event order.

Verification:

- Targeted streaming test passed:
  `backend/tests/test_chat_api.py::test_streaming_chat_turn_emits_agentic_events_and_persists_traces`.
- Full backend test suite passed: `backend/.venv/bin/python -m pytest`.
- Frontend build passed: `npm --prefix frontend run build`.
- Diff hygiene passed: `git diff --check`.

Read:

The UI no longer has to wait for `turn_complete` plus a debug reload to show
the real backend event stream. During a turn, synthetic provider deltas and
persisted runtime events now appear together.

## 2026-05-23 - Agent Stream Cockpit Reorganization

Goal:

Make the live event stream visible as a modern agentic workflow instead of a
subtle timeline embedded in the assistant message or a raw trace dump.

Changes:

- Reworked the right pane from `Trace log` to `Agent stream`.
- Added live counters for events, tools, memory activity, active steps, and
  token usage.
- Rendered the selected turn's `AgentTimeline` directly in the right pane so
  live `runtime_event`, memory, thinking, tool, note, and answer blocks are
  visible while the turn runs.
- Added category summary chips inside the panel timeline.
- Added structured renderers for generic runtime events, thinking blocks, and
  answer blocks instead of falling back to raw `<pre>` output.
- Moved raw traces into a collapsible forensic drawer so they remain available
  without dominating the evaluator experience.

Verification:

- Frontend build passed: `npm --prefix frontend run build`.
- Diff hygiene passed: `git diff --check`.
- Local backend and frontend servers were already listening on
  `127.0.0.1:8000` and `127.0.0.1:5173`.
- Browser automation was not available in this session because the required
  Node browser control tool was not exposed by tool discovery.

Read:

The backend event stream was already present. The missing piece was visual
hierarchy: the cockpit now makes event activation observable in the primary
debug pane, while retaining raw traces only as supporting forensic evidence.

## 2026-05-23 - Project State Documentation Reorganization

Goal:

Create one reliable current-state map for a project that now has several
converging functional areas: provider runtime, Mind API, semantic memory,
episodic recall, metacognition, runtime events, UI, and evaluation.

Changes:

- Added `docs/project-state.md` as the canonical integrated status and roadmap
  document.
- Organized current work into:
  - implemented and confirmed;
  - implemented but still monitoring;
  - planned but not implemented;
  - reordered priorities from P0 to P5.
- Linked the new state map from `README.md`, `docs/project-blueprint.md`,
  `docs/memory-roadmap.md`, and `docs/cognitive-api-roadmap.md`.
- Updated `docs/project-blueprint.md` status from foundation-only to active
  experimental runtime while keeping it focused on durable principles.
- Verified the new current-state route inventory against
  `backend/app/mind/schema.py`.

Verification:

- Schema route check confirmed `13` implemented Mind API routes and one planned
  route, `POST /mind/attention/context`.
- Storage table check confirmed current lab DB contains `sessions`, `messages`,
  `turns`, `traces`, `events`, `tool_calls`, `memories`, `memory_facts`, and
  `session_summaries`.
- Full backend suite passed: `backend/.venv/bin/python -m pytest`.
- Frontend build passed: `npm --prefix frontend run build`.
- Diff hygiene passed: `git diff --check`.

Read:

The next project discussion should start from `docs/project-state.md`, then
drop into the vertical documents only when working on a specific subsystem.

## 2026-05-23 - Session Idle Maintenance P1 Slice

Goal:

Implement the narrow P1 background-maintenance slice without adding redundant
agent-facing cognitive endpoints or post-turn LLM loops on every message.

Changes:

- Added `maintenance_jobs` as backend-owned asynchronous job storage.
- Added per-session idle scheduling after `turn.completed`; same-session newer
  turns supersede or skip older pending jobs, while other sessions remain
  independent.
- Added `backend/app/runtime/maintenance.py` with a FastAPI lifespan worker.
- Implemented idle job steps:
  - refresh episodic session summary through existing `sessions.summarize`;
  - run report-only missed semantic memory review.
- Emitted `maintenance.job.*` and `maintenance.memory_review.completed` events.
- Added structured cockpit labels/summaries for maintenance events.
- Added Scarlet prompt continuity check for prior-turn declared or recognized
  but unexecuted internal actions, especially missing semantic memory writes.
- Documented the slice in ADR-0031, EXP-0018, API contract, README, backend
  README, `.env.example`, changelog, and project state.

Verification:

- Targeted backend tests passed:
  `backend/.venv/bin/python -m pytest backend/tests/test_storage.py backend/tests/test_maintenance.py backend/tests/test_chat_api.py`.
- Full backend suite passed: `backend/.venv/bin/python -m pytest` (`50 passed`).
- Frontend build passed: `npm --prefix frontend run build`.
- Direct MiniMax probe with immediate idle due job completed:
  `ses_afa394462ab14899bd77cb2aa985f08f`,
  `turn_4d7c1c557cc44c2c8745e88ed9f43245`,
  `mnt_df4c97ce99a44fe6a432a45e9d151b50`.
- The direct probe confirmed the P1 review catches a missing memory write:
  `memory_write_trace_count=0` and one `write_recommended` green-tea
  preference candidate.
- The same probe opened BUG-0032: Scarlet emitted pseudo `<invoke
  name="mind_api">` text instead of a real provider tool call.

Read:

The review is intentionally report-only. The next decision should come from
real `maintenance.memory_review` traces after idle sessions: proposal inbox,
automatic write path, or diagnostic-only review.

## 2026-05-23 - Integrated Direct Scarlet Probes

Goal:

Run at least three direct, different, complex Scarlet probes against the current
runtime and record coherence, evidence, and weaknesses.

Probe 1 - Semantic memory candidate:

- Session `ses_77d537f03f224072a870c8462d642c1f`.
- Turn `turn_838d5b2227d14afeb6eca4557b713743`.
- Scarlet answered coherently about the user's preferred report sections
  (`Coerenza`, `Evidenze`, `Debolezze`) but did not call `memory.write`.
- Idle maintenance job `mnt_f7ebc705e47e4871ac0e6c8971942d8a` completed and
  produced one `write_recommended` memory candidate.

Probe 2 - Episodic transcript recall:

- Seed session `ses_69760243a12d4796a3a1b41a8d7dfd4b`, turn
  `turn_87c848424f3d4a8bab317d0d27e5c371`.
- Scarlet called real `memory.search` and `memory.write`.
- Recall session `ses_894b0c0ce54f4a1d8c00909764342056`, turn
  `turn_d88e3a2004ed4cb9865130c16ded169a`.
- Scarlet called `GET /mind/sessions` and opened three candidate transcripts,
  then separated direct evidence, indirect evidence, inference, and residual
  risk.

Probe 3 - Streaming runtime/schema/conflicts:

- Session `ses_d9d85072d6e44b19b654c957d6cc8b76`.
- Turn `turn_90e3b07080ff484da0464637a05bb9fd`.
- Streaming produced 106 NDJSON events, including live runtime events.
- Scarlet called `GET /mind/schema` and `GET /mind/memory/conflicts`.
- Two public notes appeared.
- Idle maintenance job `mnt_7ce01e9e18994ea3906fc52933683a98` completed.

Findings:

- Episodic recall and runtime eventing are currently the strongest parts.
- Semantic write autonomy remains inconsistent; idle maintenance is useful
  because it catches omissions.
- Maintenance review candidates can be useful but are not clean enough for
  automatic writes yet.
- New cognitive bug opened: Scarlet can overinterpret runtime-context fields,
  comparing capability counts to schema route counts and reading
  `recent_runtime_events=[]` as current-turn evidence.
- Cleanup: the interrupted first batch left
  `mnt_6de751a710f743f9b59889707a916669` in `running`; it was marked `failed`
  with `direct_probe_batch_interrupted_by_codex` metadata.

Verification:

- Direct MiniMax conversations and persisted traces/events.
- Detailed results recorded in `docs/experiments.md#exp-0019---integrated-direct-scarlet-probes`.

## 2026-05-23 - Natural Conversation Scarlet Probes

Goal:

Evaluate Scarlet in normal conversations without telling her to use memory,
schema, transcripts, or tools.

Scenario A - Personal chocolate continuity:

- Session `ses_1b8573874ca2454fbaff3cf3850c7787`.
- Turns `turn_7439bbac8c8a4127ae141576a85d83f1` and
  `turn_d893171dd5a1474e88122c0c6b92eca5`.
- Automatic memory context selected the chocolate-limit memory and Scarlet used
  it naturally in recipe advice.
- Follow-up relied on provider/session history with no extra tool calls.
- Weakness: retrieval also selected unrelated project/report memories.

Scenario B - Project continuity:

- Session `ses_44d025d20f5b4b20aad9605e6d700dad`.
- Turns `turn_92282018d4d34c9b9f988cdb004f854c` and
  `turn_14b9be196567427497fe9ecc757b88a2`.
- Scarlet proactively used `GET /mind/sessions` and `POST /mind/memory/search`
  without being instructed.
- Weakness: Scarlet attempted invalid `GET /mind/memory`, opening BUG-0034.
- Weakness: Scarlet reused stale memory claiming there was no event store,
  opening BUG-0035.

Scenario C - Memory promise and real preference:

- Session `ses_e52547bf12b641c49cc2fc479f103344`.
- Turns `turn_174e59b8f557423791b1d62f3125dc43` and
  `turn_a2fc44b7210f44e791824f6b79ad0c09`.
- When the user provided a real preference about tired-state responses, Scarlet
  autonomously called `POST /mind/memory/write`.
- Final answer stayed minimal: `ok`.

Findings:

- Natural personalization and episodic continuity are strong when the right
  memory/session evidence is selected.
- Natural semantic writes can happen correctly, but are still inconsistent
  across contexts.
- Current biggest risk is stale internal evidence being used as present-tense
  truth.
- Foreign-script artifacts recurred in natural Italian answers.

Verification:

- Direct MiniMax conversations.
- Persisted traces/events inspected for every turn.
- Detailed results recorded in `docs/experiments.md#exp-0020---natural-conversation-agentic-behavior-probes`.

## 2026-05-24 - Manual Retrieval Cue Prompt Slice

Goal:

Improve Scarlet's ability to infer, from natural user language, when automatic
start-of-turn memory context is not enough and she should manually search
semantic memory, memory facts, or episodic sessions.

Changes:

- Added `Manual Memory Retrieval Cues` to
  `backend/app/prompts/scarlet_system.md`.
- Clarified natural cues such as "ne avevamo parlato", "ieri", "dove eravamo
  rimasti", uncertainty markers, source-sensitive claims, personal continuity,
  project continuity, and synonym/language drift.
- Clarified when Scarlet should choose semantic memory search, fact inspection,
  episodic session search, or semantic-to-episodic provenance follow-up.

Boundary:

- The endpoint error-recovery policy discussed with the owner was intentionally
  not added to the prompt. That belongs in backend endpoint responses and API
  contract design, so failed calls can return local endpoint-specific guidance.

Verification:

- Prompt-only change. Direct Scarlet behavior probes are still needed.

## 2026-05-24 - Endpoint-Local Usage Guides

Goal:

Separate API Mind capability discovery from detailed endpoint recovery. The
owner clarified that `/mind/schema` should behave as a compact capability
catalog, while complete parameter guidance should appear only when Scarlet
misuses a specific endpoint.

Changes:

- Changed `GET /mind/schema` output to expose route method, path, status, and
  purpose only.
- Added top-level `usage_guide` to `MindAPIResponse`.
- Added backend `route_usage_guide()` generation with body schema, path
  parameters, parameter descriptions, examples, accepted aliases, and retry
  guidance.
- Added automatic `usage_guide` injection on recoverable errors from
  implemented Mind API routes.
- Added route suggestions for unknown/unavailable routes.
- Updated Scarlet's prompt only to remove the obsolete claim that detailed body
  schemas live in `/mind/schema`.
- Added ADR-0032 and updated the API contract/project state.

Verification:

- Targeted Mind API contract tests passed.
- Live Scarlet probe `ses_1dc8393b5b71442cb1fa1f8d9f509320` /
  `turn_4e4fab92a6d947d0a5ec7d7d0db8733b` confirmed recovery:
  Scarlet called `POST /mind/memory/search` with invalid `top_k=999`, received
  `memory.invalid_search` with `usage_guide`, retried with `top_k=20`, and
  completed the answer from the successful result.
- Full backend suite and frontend build still need to run after final docs
  updates.

## 2026-05-24 - Temporal And Sparse Memory Retrieval

Goal:

Implement the approved memory advancement slice without adding new model-facing
endpoint families.

Changes:

- Added backend-resolved `time` filters to `POST /mind/memory/search`.
  Supported bases: source conversation, recorded memory time, valid/fact time,
  and current session.
- Added backend-resolved `time` filters to `GET /mind/sessions`.
  Supported bases: conversation message time, created time, updated time,
  summary time, and current session.
- Added `search_documents_fts`, a derived SQLite FTS5/BM25 sparse search index
  for memory and session documents.
- Updated manual memory search, episodic session search, and automatic
  `memory.context` retrieval to use sparse search where applicable while
  preserving traceable lexical guards.
- Reworked the initial wrong-entity guard after owner review: removed
  stop-token filtering and replaced it with query-structure/entity-support
  qualification so partial lexical matches remain `near_miss` unless the
  queried entity is actually supported.
- Bumped Mind API schema version to `2026-05-24.temporal-sparse-v1`.
- Updated Scarlet's prompt to treat temporal memory/session search as a
  backend-resolved API Mind capability rather than model-side date guessing.
- Added ADR-0033 and EXP-0023.

Verification:

- Targeted backend tests passed:
  `backend/.venv/bin/python -m pytest backend/tests/test_mind_api.py backend/tests/test_chat_api.py backend/tests/test_storage.py -q`
  (`39 passed`).
- New regressions cover memory source-conversation time filtering, session
  conversation-time filtering, endpoint usage-guide exposure of `time`, and
  automatic memory context `fts5_sparse_v1` tracing.
- Full backend suite passed: `backend/.venv/bin/python -m pytest` (`54 passed`).
- Direct MiniMax probes were run with seeded temporal/sparse memory evidence:
  - `turn_7f3436db778541bbb84c02bbb0fce481` recovered from invalid
    `temporal_filter`, retried with valid `time`, opened the source session,
    and answered the old Vetro-Luna decision correctly.
  - `turn_6bdd32e2c5554cd4926a39ef1c4a914b` distinguished today's Vetro-Luna
    mention from the older format decision.
  - `turn_caccab9ffff7402e91cdfd4a0491aff3` confirmed Mare-Vetro has no
    source evidence after the guard fix; automatic context had `selected=[]`.
- Follow-up local check after removing stop-token filtering confirmed manual
  `Mare Vetro` memory search returns zero results and automatic context keeps
  Mare-Vetro wrong-entity matches out of `selected`.
- `git diff --check` and Python compile checks passed.

Read:

The first direct probe exposed an overly broad FTS/lexical guard. That was fixed
inside the retrieval slice because it directly affected the acceptance target.
Remaining weakness: Scarlet still tries invalid body fields before recovering,
so endpoint guidance works but model route discipline is not solved.

## 2026-05-24 - Restarted Temporal/Sparse Runtime And Re-ran Episodic Recall Probe

Goal:

Re-run the owner's first-contact episodic recall test after restarting backend
and frontend so Scarlet uses the current `2026-05-24.temporal-sparse-v1` Mind
API schema, streaming runtime events, and idle maintenance scheduling.

Evidence:

- Restarted backend on `127.0.0.1:8000` and frontend on
  `127.0.0.1:5173`.
- Confirmed `/mind/schema` now returns
  `2026-05-24.temporal-sparse-v1` with 14 compact catalog routes.
- Ran direct streaming session
  `ses_eac71e7b90814f49a7c21e079e64b85a`.
- Runtime events were persisted and streamed:
  memory context, thinking metadata, public notes, Mind API tool lifecycle,
  final answer events, turn completion, and maintenance scheduling.
- Four per-session idle jobs were scheduled; the first three were superseded
  by newer turns and the final one remained pending.

Read:

- Episodic recall improved relative to the stale-server run: Scarlet used
  paginated session recall and identified the 8 May 16:40 transcript as the
  earliest substantial communication when asked broadly.
- When pressed to exclude tests and "identification" messages, Scarlet
  over-shifted to 22 May as the first Scarlet-identity conversation. This is a
  useful ambiguity case: "first substantial communication" and "first
  Scarlet-identity conversation" need different evidence criteria.
- Scarlet still made one invalid session-list call with unsupported
  `order=asc`, then recovered through endpoint-local guidance and pagination.
- BUG-0035 reproduced: Scarlet read the current schema and an old active memory
  saying "nessun event store", but still treated the absence of
  `/mind/events/emit` as evidence that the event-store gap remained. The
  runtime events table and streamed event counts prove otherwise.

## 2026-05-24 - Stratified Runtime Context Blocks

Goal:

Improve Scarlet's runtime perception by separating session continuity,
current-turn perception, and dynamic Scarlet operational state instead of
placing all evidence under the older `memory.context` concept.

Changes:

- Added a block-based `runtime.context` trace with schema
  `runtime-context-v1`.
- Preserved `memory.context` as the automatic memory retrieval trace and as a
  backward-compatible top-level field in `<runtime_context>`.
- Added `session_context` block:
  current session, two recent previous sessions with summaries/fallback
  summaries, and up to five active memories sourced from the previous session.
- Added `message_context` block:
  current message, backend temporal/world data, language hint, active
  user-scope memory hints, automatic memory retrieval, recent dialogue, recent
  runtime events, and API Mind schema/capability metadata.
- Added `scarlet_state` block:
  backend-seeded focus, interaction mode, confidence posture, active goal, and
  open loops for future state APIs.
- Added `runtime.context.built` events and a streaming `runtime_context` NDJSON
  event.
- Updated the frontend agent timeline to render runtime-context blocks as a
  structured runtime step.
- Updated Scarlet's prompt to read runtime context blocks by type and to treat
  summaries as navigation aids.

Verification:

- Python compile check passed for the changed backend modules.
- Frontend build passed.
- Targeted chat API tests passed:
  `backend/.venv/bin/python -m pytest backend/tests/test_chat_api.py -q`
  (`11 passed`).

## 2026-05-24 - Human-Readable Agent Stream UI

Goal:

Turn the cockpit timeline from a mostly structured-debug surface into a
human-readable agentic chat surface where Scarlet's runtime context, memory
retrieval, tool usage, evidence, notes, and final answer are readable without
opening raw JSON.

Changes:

- Added dedicated frontend renderers for `runtime.context` blocks:
  `session_context`, `message_context`, and `scarlet_state`.
- Rendered previous sessions, user-profile memory hints, automatic memory
  retrieval, near misses, API Mind schema/capability counts, and Scarlet state
  as cards and metrics.
- Moved raw runtime context, tool payloads, endpoint usage guides, and event
  details behind closed code/detail toggles.
- Added readable labels for provider stream lifecycle events such as request
  started/stopped, thinking started/captured, and text started.
- Adjusted the right-side agent stream layout so narrow cards preserve readable
  titles and values.

Verification:

- Ran `npm --prefix frontend run build`; build passed.
- Ran a Playwright Chromium smoke against `http://127.0.0.1:5173/`, opened the
  latest persisted session, and captured `/tmp/llm-api-mind-ui-after.png`.
- Ran a second Playwright Chromium smoke through the live composer with a new
  streamed turn (`UI smoke live: rispondi solo ok...`) and captured
  `/tmp/llm-api-mind-ui-live-smoke.png`.
- Smoke confirmed:
  - 2 runtime-context renderings present (chat and right pane);
  - 6 runtime context cards present;
  - code/detail toggles present;
  - no top-level raw `<pre>` blocks inside operation bodies;
  - no visible runtime-event body beginning with raw JSON.
  - live final answer rendered as plain assistant text (`ok`) while the
    operation timeline stayed structured.

Open Questions:

- The side pane is now readable, but dense runtime-context blocks still consume
  a lot of vertical space. The next UI decision is whether to add per-category
  collapse defaults or keep everything expanded during this experimental phase.

## 2026-05-25 - Runtime Context Block Comprehension Probe

Goal:

Verify whether Scarlet actually receives, understands, and uses the new
`runtime.context` blocks, not only whether the backend can build and render
them.

Changes:

- Ran code/trace inspection of `backend/app/mind/context.py` and
  `backend/app/api/chat.py`.
- Confirmed `memory.context` and `runtime.context` are built after the user
  message is persisted and before `llm.request`.
- Confirmed `runtime.context` is appended to the effective system prompt inside
  `<runtime_context>`.
- Ran direct live session
  `ses_8d6f582db47a425988aeb01eb6b44d76` with three streamed turns.
- Recorded `EXP-0024` with turn ids, trace ordering, and behavioral findings.

Verification:

- Turn `turn_bfacd9824c0a4acbb673411d8f51d713`: Scarlet used runtime context
  directly for local/UTC time, Italian language, and block identities with zero
  Mind API calls.
- Turn `turn_a7bb3e0f074941cda292aeb66c106057`: Scarlet saw recent session
  summaries, then correctly opened both source sessions before answering.
- Turn `turn_2d1fcfc2d5b444c8a2455d0938c83d44`: Scarlet used the
  chocolate-limit user profile memory to personalize advice with zero Mind API
  calls.

Read:

- Positive: runtime blocks are delivered before the provider request and are
  usable by Scarlet as operative evidence.
- Positive: Scarlet distinguishes summary-as-navigation from transcript-as-proof
  in the session-continuity case.
- Weakness: `message_context.language_hint` returned `unknown` for one Italian
  snack prompt.
- Weakness: automatic memory retrieval selected an unrelated creator memory for
  the snack prompt; the answer was correct because `user_profile` carried the
  chocolate memory.

Next Suggested Step:

Do not patch with keyword lists. Keep monitoring retrieval/profile divergence
and later solve it through stronger retrieval, language detection, embeddings,
or profile-specific ranking rather than hardcoded terms.

## 2026-05-25 - Runtime Preferences And Tailwind Dashboard Rework

Goal:

Simplify Scarlet's runtime perception and rework the local cockpit into a
product-style dashboard that exposes sessions, memories, profile, settings,
chat, and agent stream without making the user read raw JSON.

Changes:

- Added persistent app settings through `/api/dashboard/settings`.
- Added `/api/dashboard/memories` for the memory panel.
- Added `/api/dashboard/profile` for user-profile readout derived from
  settings and user-scope memories.
- Added backend runtime preference loading and defaults:
  - timezone: `Europe/Rome`;
  - language: `it`;
  - user display name: `Utente locale`.
- Changed runtime context temporal data to one configured clock:
  `temporal_context.now`, with timezone metadata.
- Replaced automatic `language_hint` with configured platform language inside
  `message_context.current_message.language`.
- Updated Scarlet's system prompt to use the configured clock and platform
  language.
- Added Tailwind (`tailwindcss`, `postcss`, `autoprefixer`) and rebuilt the
  frontend around:
  - session sidebar;
  - central chat;
  - dashboard tabs for Agent Stream, Memorie, Profilo, and Impostazioni;
  - memory cards and profile cards;
  - settings controls for language/timezone/display name.
- Bounded the dashboard to the browser viewport:
  - app shell uses `100dvh` and hides page-level overflow;
  - session history, chat messages, agent stream, memory/profile lists, and
    raw trace drawers scroll internally;
  - embedded per-message agent timelines are capped so a single assistant turn
    cannot make the chat vertically unbounded.

Verification:

- `backend/.venv/bin/python -m compileall backend/app` passed.
- `backend/.venv/bin/python -m pytest backend/tests/test_chat_api.py -q`
  passed (`12 passed`).
- `backend/.venv/bin/python -m pytest backend/tests -q` passed (`55 passed`).
- `npm --prefix frontend run build` passed.
- Restarted backend and frontend on `127.0.0.1:8000` and `127.0.0.1:5173`.
- Checked live dashboard endpoints:
  - `/api/dashboard/settings`;
  - `/api/dashboard/memories`;
  - `/api/dashboard/profile`.
- Captured Playwright screenshot:
  `/tmp/scarlet-dashboard-rework.png`.
- Captured viewport-bounded screenshot:
  `/tmp/scarlet-dashboard-viewport-bounds.png`.
- Ran direct Scarlet smoke turn
  `turn_d49955952c5343d58d29da2ddf93f1b4`; Scarlet answered from runtime
  context with configured `Europe/Rome` time and Italian language, made zero
  Mind API tool calls, and did not cite UTC.

Read:

- The previous language-detection weakness is now removed from the active
  runtime path rather than patched by keyword rules.

## 2026-05-25 - Operational Profile And Locale Runtime Context

Goal:

Make user/profile settings operational cognitive inputs for Scarlet, not
cosmetic dashboard fields. The active profile, privacy boundary, configured
country/locale, timezone, and language must be visible inside runtime context
before each model request.

Changes:

- Extended runtime preferences with:
  - `country_code` / `country_label`;
  - `profile_id`;
  - `privacy_scope`.
- Extended `/api/dashboard/settings` request/response and
  `/api/dashboard/profile`.
- Injected configured locale into `message_context.world.location` with a
  policy that it is country/timezone-level evidence, not GPS.
- Injected active profile identity, privacy boundary, and locale into
  `message_context.user_profile`.
- Updated Scarlet's system prompt to treat profile, privacy, language, time,
  and configured locale as runtime evidence.
- Updated dashboard settings and profile panels so the user can inspect and
  edit operational profile/locale fields.
- Added internal scrolling to the settings panel so future settings growth does
  not make the dashboard vertically unbounded.
- Updated API contract, project state, ADR-0035, README files, changelog, and
  EXP-0026.

Verification:

- `backend/.venv/bin/python -m compileall backend/app` passed.
- `backend/.venv/bin/python -m pytest backend/tests/test_chat_api.py -q`
  passed (`12 passed`).
- `backend/.venv/bin/python -m pytest backend/tests -q` passed (`55 passed`).
- `npm --prefix frontend run build` passed.
- `git diff --check` passed.
- Restarted backend on `127.0.0.1:8000`; frontend dev server remained active on
  `127.0.0.1:5173`.
- Live endpoint check confirmed `/api/dashboard/settings` and
  `/api/dashboard/profile` return profile, privacy, country, language, and
  timezone fields.
- Direct Scarlet smoke turn
  `turn_b393262f061f4fe8b50231e3f5683d35` answered from runtime context with
  active profile, Italy locale, `Europe/Rome`, and Italian language, with zero
  Mind API tool calls.

Notes:

- Browser plugin control was not available in this runtime, and local Playwright
  is not installed as a project dependency, so no new screenshot was captured
  for this slice. Frontend verification used TypeScript/Vite build plus live
  server availability.
- The local persisted display name currently remains `Test nome`; the runtime
  correctly propagates it, but the owner may want to replace it from the
  dashboard with the real local profile name.
- Settings are human/product controls and are not new model-facing API Mind
  endpoints.
- The UI now has the right information architecture for the next product
  iteration, but needs live evaluator feedback on density and tab wording.

## 2026-05-25 - Agentic Branch Documentation And V1.0.1 Development Protocol

Area:

Documentation and development governance.

Branch:

Cross-branch project governance.

Type:

Implementazione.

Target version:

V1.0.1 baseline registered. Future repository changes must declare whether
they are `Fix`, `Implementazione`, or `Major release` before implementation.

Goal:

Reorganize project planning around Scarlet's real agentic operating branches
instead of technical subsystems alone, and establish the stricter versioned
engineering process requested by the owner.

Changes:

- Added `docs/project-documentation.md` as the main documentation index.
- Added `docs/development-process.md` with:
  - V1.0.1 baseline;
  - pre-work scope declaration;
  - fix/implementation/major version rules;
  - direct-scope-only fix policy;
  - verification policy;
  - commit/version discipline.
- Added `docs/branches/README.md`.
- Added vertical branch documents for:
  - communication;
  - user flows;
  - perception/context;
  - identity/relationship;
  - memory;
  - learning/adaptation;
  - metacognition;
  - operational management;
  - decision autonomy;
  - external operativity;
  - advanced operations;
  - governance/privacy/safety;
  - computational affect;
  - multi-agent subprocesses.
- Updated `docs/project-state.md` with the branch map and corrected the current
  backend suite count to `55 passed`.
- Updated `docs/project-blueprint.md`, `docs/release-process.md`, `AGENTS.md`,
  `README.md`, `docs/decisions.md`, and `CHANGELOG.md`.
- Set app metadata baseline to V1.0.1 in backend and frontend metadata.

Verification:

- Documentation-only structure inspected through file reads.
- Version metadata updated only in package/FastAPI metadata; no runtime behavior
  was intentionally changed.

## 2026-05-25 - V1.1.0 Memory Proposal Inbox

Area:

Memoria / manutenzione semantica.

Branch:

Memoria.

Type:

Implementazione.

Target version:

V1.1.0.

Goal:

Move idle missed-memory review from diagnostic-only traces to a safer,
observable proposal inbox without auto-writing active semantic memories.

Changes:

- Added `memory_proposals` storage with idempotency key, source provenance,
  candidate fields, evidence, similar-memory ids, related fact ids, decision
  metadata, and future embedding/graph-ready slots.
- Added repository helpers for proposal upsert/list/read-by-key.
- Added preflight logic that reuses existing Memory v0 write policy, FTS5/BM25
  sparse retrieval, lexical scoring, and canonical facts to suggest actions:
  `create_new`, `noop_duplicate`, `review_similar`, `needs_review`, or
  `reject_candidate`.
- Updated idle maintenance so write-recommended missed-memory review
  candidates create pending proposals and report proposal counts in
  `maintenance.memory_review.completed`.
- Added `GET /mind/memory/proposals` through `mind_api`.
- Advanced the Mind API schema version to
  `2026-05-25.memory-proposals-v1`.
- Updated docs for API contract, project state, memory branch, decision log,
  experiment log, changelog, and V1.1.0 version metadata.

Verification:

- Targeted backend tests passed:
  `backend/.venv/bin/python -m pytest backend/tests/test_storage.py backend/tests/test_maintenance.py backend/tests/test_mind_api.py`
  (`33 passed`).
- Full backend suite passed from `backend`: `.venv/bin/python -m pytest`
  (`58 passed`).

Notes:

- Proposals are explicitly not active memories.
- No auto-apply route was added in this slice.
- Next useful work is proposal application policy and UI/evaluator inspection,
  not embedding or graph infrastructure yet.

## 2026-05-25 - V1.1.1 Maintenance-Only Proposal Inbox

Area:

Memoria / manutenzione semantica.

Branch:

Memoria.

Type:

Fix.

Target version:

V1.1.1.

Goal:

Move proposal inspection out of Scarlet's autonomous `mind_api` surface and
into maintenance-only APIs that can be consumed by background LLM reviewers in
bounded batches.

Changes:

- Removed `GET /mind/memory/proposals` from the Mind API dispatcher and schema.
- Added `GET /api/maintenance/memory/proposals` with `status`,
  `source_session_id`, `limit`, `offset`, `has_more`, and `next_offset`.
- Added `POST /api/maintenance/memory/proposals/{proposal_id}/archive` so
  handled proposals leave the default pending queue while remaining auditable.
- Added repository archival support for `memory_proposals`.
- Restricted dynamic memory reads to real `mem_...` ids so retired child paths
  do not masquerade as missing memory records.
- Advanced the Mind API schema version to
  `2026-05-25.maintenance-proposals-v1`.
- Updated API contract, decision, experiment, project state, branch docs,
  changelog, and V1.1.1 version metadata.

Verification:

- Targeted backend tests passed:
  `backend/.venv/bin/python -m pytest backend/tests/test_mind_api.py backend/tests/test_maintenance_api.py`
  (`25 passed`).
- Memory/storage maintenance regression tests passed:
  `backend/.venv/bin/python -m pytest backend/tests/test_storage.py backend/tests/test_maintenance.py backend/tests/test_mind_api.py backend/tests/test_maintenance_api.py`
  (`35 passed`).
- Full backend suite passed from `backend`: `.venv/bin/python -m pytest -q`
  (`60 passed`).
- Frontend production build passed:
  `npm --prefix frontend run build`.

## 2026-05-26 - V1.2.0 Cautious Proposal Resolution

Area:

Memoria / manutenzione proposal.

Branch:

Memoria.

Type:

Implementazione.

Target version:

V1.2.0.

Goal:

Resolve safe memory proposals inside the existing idle maintenance job without
adding a redundant background LLM process. Keep Dream as a future review phase.

Changes:

- Extended idle maintenance from proposal creation to cautious proposal
  resolution.
- Added deterministic proposal outcomes:
  - `archived_rejected` for preflight rejects;
  - `archived_noop_duplicate` for exact/equivalent duplicates;
  - `applied_create` for very high-confidence `create_new` candidates that
    pass conservative auto-apply gates.
- Added one optional batched LLM resolver for ambiguous proposals, with
  `apply_create`, `reject`, `noop_duplicate`, and `keep_pending` outcomes.
- Added `pending_review` for proposals that should wait for future Dream or
  human/evaluator review.
- Stored resolution result, preflight snapshot, Dream review marker, and memory
  id/snapshot when a proposal creates a memory.
- Extended the maintenance proposal API with `status=resolved` plus
  `created_from`, `created_to`, `resolved_from`, and `resolved_to` filters.
- Kept all proposal inspection outside Scarlet's model-facing `mind_api`.

Verification:

- Targeted memory-maintenance tests passed:
  `backend/.venv/bin/python -m pytest backend/tests/test_storage.py backend/tests/test_maintenance.py backend/tests/test_maintenance_api.py backend/tests/test_mind_api.py -q`
  (`38 passed`).
- Full backend suite passed from `backend`: `.venv/bin/python -m pytest -q`
  (`63 passed`).
- Frontend production build passed:
  `npm --prefix frontend run build`.
- `git diff --check` passed.
- Direct real MiniMax maintenance probe on a temporary SQLite database passed:
  idle maintenance completed, created one `create_new` proposal, invoked the
  batched LLM resolver, applied the proposal as `applied_create`, wrote one
  active memory with maintenance provenance, and recorded
  `maintenance.memory_proposal_resolution`.

Notes:

- Dream review is still not implemented.
- Merge/update/deprecate resolution remains out of scope and should stay
  `pending_review`.
- During implementation, a pre-existing fact-extractor weakness was observed:
  very short aliases such as `sal` can match substrings in unrelated words.
  This was not fixed in this slice and is tracked separately.

## 2026-05-28 - V1.3.0 Memory Retrieval Readiness Layer

Area:

Memoria / retrieval avanzato.

Branch:

Memoria.

Type:

Implementazione.

Target version:

V1.3.0.

Goal:

Prepare memory for dense embeddings, Milvus/Qdrant shadow indexing, and
knowledge-graph expansion without changing Scarlet's model-facing `mind_api`
surface or the current active FTS5/BM25 ranking behavior.

Changes:

- Added `memory_surfaces` as derived embeddable surfaces for memory records,
  facts, graph-node profiles, and session summaries.
- Added `memory_graph_nodes` and `memory_graph_edges` as graph-ready derived
  state for memories, facts, entities, sessions, evidence links, and lifecycle
  links.
- Added repository helpers for idempotent surface/node/edge upserts and
  bounded inspection.
- Extended memory/session document synchronization so FTS5 remains active while
  surfaces and graph artifacts are kept in step with memory/fact/session
  changes.
- Added a retrieval readiness manifest to memory search/context traces and
  results.
- Kept Milvus/Qdrant/vector/reranker activation out of scope.
- Left existing sparse/fact matching bugs untouched; this slice prepares the
  structural path that will later replace brittle lexical matching.

Verification:

- Targeted backend suite passed:
  `.venv/bin/python -m pytest tests/test_storage.py tests/test_mind_api.py tests/test_chat_api.py tests/test_maintenance.py -q`
  (`49 passed`).
- Full backend suite passed from `backend`: `.venv/bin/python -m pytest -q`
  (`64 passed`).
- Frontend production build passed: `npm --prefix frontend run build`.
- `git diff --check` passed.

Notes:

- Surfaces and graph rows are derived indexes, not canonical truth.
- `memories`, `memory_facts`, `session_summaries`, messages, and proposal rows
  remain the authoritative state.
- Next useful implementation is a shadow retrieval adapter over
  `memory_surfaces`, likely Milvus Lite first, with trace-only comparison
  before changing ranking.

## 2026-05-28 - V1.3.1 Retrieval Shadow Adapter

Area:

Memoria / retrieval avanzato.

Branch:

Memoria.

Type:

Fix/integrazione non comportamentale.

Target version:

V1.3.1.

Goal:

Add an optional retrieval shadow path over `memory_surfaces` so future dense
retrieval can be observed in traces before it affects Scarlet's answers.

Changes:

- Added configurable retrieval shadow settings and `.env.example` defaults.
- Added `backend/app/mind/shadow_retrieval.py` with:
  - disabled default behavior;
  - deterministic `local_hash_embedding_v1` backend for plumbing tests;
  - optional PyMilvus/Milvus Lite backend when installed;
  - trace-only result payloads with `ranking_policy=trace_only_no_active_ranking`.
- Added repository helper for listing memory surfaces by target memory ids.
- Added `retrieval_shadow` payloads to manual `memory.search` results/traces
  and automatic `memory.context` query plans.
- Kept active memory ranking unchanged.

Verification:

- Targeted backend suite passed:
  `.venv/bin/python -m pytest tests/test_storage.py tests/test_mind_api.py tests/test_chat_api.py tests/test_maintenance.py -q`
  (`50 passed`).
- Full backend suite passed from `backend`: `.venv/bin/python -m pytest -q`
  (`65 passed`).
- Frontend production build passed:
  `npm --prefix frontend run build`.
- `git diff --check` passed.
- Direct Scarlet test on a temporary SQLite database passed:
  Scarlet answered from the expected semantic memory and the `memory.context`
  trace reported completed local shadow retrieval over the same memory target.

Notes:

- `local_hash_embedding_v1` is only a deterministic plumbing vector and is not
  a real semantic embedding model.
- Milvus Lite remains optional and is not required for base runtime or tests.
- V1.4 should only activate hybrid ranking after selecting and validating a
  real embedding provider.

## 2026-05-31 - V1.4.0 Memory Surface Taxonomy

Area:

Memoria / retrieval e maintenance readiness.

Branch:

Memoria.

Type:

Implementazione.

Target version:

V1.4.0.

Goal:

Improve the memory substrate that future embeddings will consume while leaving
local BGE-M3/GPU work for the Windows machine.

Changes:

- Added `backend/app/mind/surface_taxonomy.py` as the single deterministic
  backend compiler for memory/fact/graph-node surfaces.
- Memory records can now emit multiple cognitive surfaces:
  `memory_text`, type-specific surfaces such as `preference_text`,
  `future_use_text`, `temporal_text`, `fact_bundle_text`, and
  `conflict_guard_text` when applicable.
- Surface metadata now records taxonomy version, compiler, cognitive
  dimensions, embedding role, agent-supplied fields, and backend-owned fields.
- Retrieval readiness now reports `memory_surface_taxonomy_v1` and includes
  the surface taxonomy manifest.
- Shadow retrieval now compares across all active memory surfaces for candidate
  memories, still trace-only.
- Maintenance proposal preflight now stores `maintenance_assessment` with lane,
  risk, review focus, and counts so future policy tuning has measurable
  evidence.
- Active memory ranking, Scarlet prompt, embedding providers, and graph DB
  choices remain unchanged.

Verification:

- Targeted backend suite passed:
  `.venv/bin/python -m pytest tests/test_storage.py tests/test_mind_api.py tests/test_maintenance.py tests/test_chat_api.py -q`
  (`50 passed`).
- Full backend suite passed from `backend`: `.venv/bin/python -m pytest -q`
  (`65 passed`).
- Frontend production build passed:
  `npm --prefix frontend run build`.
- `git diff --check` passed.
- Direct Scarlet test on a temporary SQLite database passed:
  a chocolate preference/constraint memory generated the expected taxonomy
  surfaces, and Scarlet used that memory correctly in a natural snack
  recommendation.

Notes:

- This slice intentionally avoids BGE-M3, Milvus activation, and active hybrid
  ranking because local embedding work is planned for the Windows GPU machine.
- The stronger surface taxonomy should make future embedding tests more
  meaningful, because the vectors will index cognitive facets rather than one
  flattened memory string.

## 2026-06-08 - V1.4.1 MiniMax M3 Baseline And Model Comparison

Area:

Provider runtime / behavioral evaluation.

Branch:

Communication, Decision autonomy, Memory.

Type:

Fix/operational update.

Target version:

V1.4.1.

Goal:

Switch the MiniMax default model from M2.7 to M3 and run an evidence-based
M2.7/M3 Scarlet comparison before deciding whether the newer model is a real
behavioral upgrade.

Changes:

- Changed the default MiniMax model to `MiniMax-M3` in backend settings and
  environment templates.
- Kept MiniMax M2.7 available as a direct A/B baseline through
  `MINIMAX_MODEL=MiniMax-M2.7`.
- Updated app/package/docs baseline version to V1.4.1.
- Recorded ADR-0042 and EXP-0032 for the M3 migration and comparison.
- Recorded BUG-0038 for the MiniMax M3 ultra-short-output streaming edge case.
- Updated the Scarlet prompt runtime description from MiniMax M2.7 to M3.

Verification:

- Direct M3 smoke through the current Anthropic-compatible endpoint succeeded
  on realistic prompts.
- Direct M3 fake-tool probe succeeded with Anthropic-style `tool_use` and
  continuation after `tool_result`.
- Incremental live comparison over temporary DBs completed four useful tests:
  identity/API Mind, current capabilities, source-memory recall, and autonomous
  memory write.

Notes:

- M3 showed stronger autonomous schema use and a more precise API Mind identity
  explanation.
- M2.7 outperformed M3 on exact source-session verification for the seeded
  memory.
- M3 repeatedly sent invalid `memory.write.tags` payloads before succeeding,
  causing high latency and loss of tags/future-use in the final memory write.
- M3 should remain under live evaluation; it is not yet proven superior to
  M2.7 for Scarlet.

## 2026-06-08 - EXP-0033 MiniMax M3 Stability Replication

Area:

Provider runtime / behavioral evaluation.

Branch:

Communication, Decision autonomy, Memory.

Type:

Diagnostic documentation.

Target version:

V1.4.1 unchanged.

Goal:

Check whether the negative M3 findings from the first comparison were
temporary cases or repeatable behavior by running repeated direct Scarlet turns
against temporary SQLite databases.

Work Performed:

- Ran 5 M2.7 semantic-memory write replicas, 5 M2.7 source-recall replicas,
  and 3 M2.7 schema-awareness replicas.
- Ran 3 completed M3 semantic-memory write replicas, then stopped that block
  adaptively because the same failure pattern repeated and each turn was slow.
- Ran a separate isolated M3 source/schema pass with 3 source-recall replicas
  and 3 schema-awareness replicas so memory-write retry loops could not
  contaminate later turns.
- Recalculated final metrics directly from the temporary SQLite DB traces and
  assistant messages.
- Recorded EXP-0033 and BUG-0039.

Results:

- M2.7 semantic memory writes: 5/5 successful, 5/5 valid first attempt, 0/5
  invalid writes, 0/5 tag-shape errors.
- M3 semantic memory writes: 3/3 eventually successful, 0/3 valid first
  attempt, 3/3 invalid writes, 3/3 tag-shape errors, average 5.67 write
  attempts, average latency 82.1s.
- M2.7 source recall: opened source session 4/5 and answered exact details
  5/5.
- M3 isolated source recall: opened source session 3/3 and answered exact
  details 3/3.
- M2.7 schema inspection: called `/mind/schema` 1/3.
- M3 schema inspection: called `/mind/schema` 3/3.

Verification:

- Direct live Scarlet turns used real MiniMax provider calls through the
  existing chat streaming endpoint and temporary SQLite databases.
- Metrics were derived from stored `mind.tool_call` traces and persisted
  assistant messages.
- No backend, prompt, schema, or model configuration code was changed.

Next Suggested Step:

Discuss a focused mitigation for BUG-0039 before changing code. M3 looks
stronger on schema-awareness and isolated source recall, but M2.7 remains the
more reliable semantic-memory-write baseline.

## 2026-06-15 - V1.5.1 MiniMax M3 Semantic Stream UI

Area:

Communication / runtime events / frontend cockpit.

Branch:

Comunicazione Agente-Utente.

Type:

Fix.

Target version:

V1.5.1.

Goal:

Adapt Scarlet's runtime/UI to MiniMax M3 streamed content so provider thinking,
public work notes, tool-use, tool results, and final answer blocks appear in
the correct order without frontend timing heuristics.

Changes:

- Added backend semantic stream events for completed provider content blocks:
  `thinking_captured`, `assistant_note`, and `assistant_answer`.
- Persisted those events as `llm.thinking.captured`,
  `assistant.note.emitted`, and `assistant.answer.completed` during the stream
  instead of reconstructing notes only after the turn.
- Updated the frontend agent stream to render:
  - thinking as an expanded-while-active accordion;
  - public notes as fully visible blocks;
  - each tool call as one accordion with input and output panes;
  - final answers as explicit answer blocks.
- Reworked the center chat as a flat sequence of top-level cards instead of a
  single assistant-response card containing nested blocks:
  - user messages remain standalone conversation cards;
  - automatic memory context, runtime context, thinking, notes, tool exchange,
    and final answers each become their own chronological card;
  - raw JSON and technical payloads move behind per-block code/detail toggles.
- Reworked the right pane into a session inspector rather than a duplicate
  agent stream:
  - memories used in the selected turn;
  - tool/actions performed by Scarlet;
  - internal system events;
  - warnings/errors.
- Removed the old frontend assumption that only text before the first tool in
  model step 1 can be a public note.
- Recorded ADR-0044, EXP-0034, and BUG-0041.

Verification:

- `backend/.venv/bin/python -m pytest backend/tests/test_chat_api.py backend/tests/test_minimax_client.py`
- `npm run build`
- Direct MiniMax M3 stream probe confirmed persisted order:
  `assistant.note.emitted` -> `mind.tool_call.started/completed` ->
  `assistant.answer.completed`.
- Visual/DOM probe on a dense persisted session confirmed `chat-flow-card`
  blocks render without the old `.message-body` or `.agent-turn.embedded`
  wrappers.

Residual Risk:

The UI/runtime now supports provider-exposed thinking blocks, but MiniMax M3
thinking mode is not explicitly enabled by this slice.

---

Date: 2026-06-16

Area:

Communication / MiniMax provider thinking.

Type:

Fix.

Target version:

V1.5.1.

Goal:

Restore provider-visible MiniMax M3 thinking in live Scarlet turns and verify
that thinking remains part of the provider history passed back to the model on
later turns.

Changes:

- Enabled Anthropic-compatible `thinking={"type":"adaptive"}` automatically
  for MiniMax M3 requests in `backend/app/llm/minimax_client.py`.
- Left M2.x behavior unchanged.
- Added provider tests that lock the M3 thinking parameter on and confirm M2.x
  requests still omit it.
- Reconfirmed that provider history preserves full assistant content blocks,
  including `thinking`, `text`, `tool_use`, and returned `tool_result`
  sequences.

Verification:

- `backend/.venv/bin/python -m pytest backend/tests/test_minimax_client.py -q`
- `backend/.venv/bin/python -m pytest backend/tests/test_chat_api.py -q`
- Restarted backend on `http://127.0.0.1:8000`.
- Direct live MiniMax M3 stream probe confirmed:
  `llm.thinking.started` -> `thinking_delta` -> `assistant.note.emitted` ->
  `mind.tool_call.started` -> second-step `llm.thinking.started` ->
  final answer.

Residual Risk:

Provider-visible thinking now depends on the Anthropic-compatible M3
`thinking` mode being supported consistently by MiniMax. Public notes before
tool calls remain prompt-driven rather than runtime-enforced by this slice.

---

Date: 2026-06-25

Area:

Digital-individual organs / Volition.

Type:

Implementation V1.19.0.

Goal:

Implement the first real volition slice as a manual latent-intention register
for Scarlet, without automatic active-chat injection or autonomous-cycle
processing.

Changes:

- Added `intention_records` and `intention_links` storage.
- Added `POST /mind/volition` through the existing `mind_api` dispatcher.
- Added lifecycle actions for create/read/list/search/update/defer/review/
  promote-to-focus-candidate/resolve/impossible/deprecate.
- Added volition events and traces under `organ.volition.*`.
- Advanced Mind API schema to `2026-06-25.volition-organ-v1`.
- Backed up the Scarlet system prompt before adding minimal volition usage
  instructions:
  `backend/app/prompts/backups/scarlet_system.20260625T000000Z.pre-v1190-volition-organ.md`.
- Kept `volition_context` out of normal runtime injection; intentions are
  manually inspectable and future autonomous-cycle material.

Verification:

- `cd backend && .venv/bin/python -m py_compile app/storage/models.py app/storage/repositories.py app/mind/volition.py app/mind/dispatcher.py app/mind/schema.py app/main.py`
- `cd backend && .venv/bin/python -m pytest tests/test_volition_api.py -q`
- `cd backend && .venv/bin/python -m pytest tests/test_volition_api.py tests/test_mind_api.py -q`
- `cd backend && .venv/bin/python -m pytest tests/test_volition_api.py tests/test_focus_api.py tests/test_organs.py tests/test_mind_api.py::test_mind_schema_exposes_tool_and_current_routes tests/test_mind_api.py::test_mind_call_returns_structured_error_for_removed_attention_route -q`
- `git diff --check -- backend/app/storage/models.py backend/app/storage/repositories.py backend/app/mind/volition.py backend/app/mind/dispatcher.py backend/app/mind/schema.py backend/app/main.py backend/tests/test_volition_api.py backend/tests/test_mind_api.py backend/app/prompts/scarlet_system.md CHANGELOG.md docs/activity-log.md docs/api-contract.md docs/block-registry.md docs/decisions.md docs/development-process.md docs/digital-individual-organs-notes.md docs/experiments.md docs/project-state.md`

Residual Risk:

Live Scarlet behavior still needs evaluation. The main risk is not backend
correctness but model behavior: Scarlet may over-create weak or theatrical
intentions if the prompt pressure is too high. Automatic autonomous cycles are
intentionally deferred.

Known unrelated test gap:

- `cd backend && .venv/bin/python -m pytest tests/test_chat_api.py -q` still
  has the pre-existing failure in
  `test_chat_turn_persists_messages_and_traces`: it expects the old prompt
  phrase `feminine agent identity`, while the approved current prompt identifies
  Scarlet as a digital individual. The remaining 15 chat tests passed.

---

Date: 2026-06-19

Area:

Memory / Codex test database / retrieval calibration.

Type:

Implementation/evaluation inside V1.13.0.

Goal:

Activate the isolated Codex test profile, populate it with a dirty controlled
memory dataset derived from the real Scarlet DB, and run endpoint-level
retrieval tests without mutating the production database.

Changes:

- Added `backend/app/evals/codex_test_memory_harness.py`.
- The harness can reset `backend/data/codex_test.db`, seed it from
  `backend/data/app.db`, write controlled memories through `/mind/call`, add a
  lifecycle supersede pair, run retrieval probes, and write a report under
  `backend/app/evals/runs/*_codex_test_memory`.
- Fixed hybrid retrieval diagnostic serialization by materializing
  `memory_id`, salience, and creation time inside `HybridRankEntry`, avoiding
  detached SQLModel object refresh after `add_trace` commits.
- Started the local backend with `CODEX_TEST=true`; `/health` confirms
  database profile `codex_test`.

Evaluation:

- Harness run:
  `backend/app/evals/runs/20260619_161039_codex_test_memory/`.
- DB prod remained unchanged for this run at 30 memories, 241 surfaces, 236
  embedding vectors, 90 graph nodes, and 75 graph edges.
- DB test reached 272 memories, 242 Codex-test memories, 2,507 surfaces, 521
  embedding vectors, 671 graph nodes, and 725 graph edges.
- Retrieval probe result: 6/9 passed.
- Confirmed strengths:
  direct chocolate/wellbeing recall, associative evening beverage recall,
  negative control, API schema/error recovery, privacy/runtime profile, and
  lifecycle current memory.
- Observed limits:
  strict-key recall failed for concise-when-tired because an equivalent real
  production memory won; metacognitive effort routing and episodic bridge
  recall need retrieval calibration.

Verification:

- `cd backend && .venv/bin/python -m py_compile app/evals/codex_test_memory_harness.py app/mind/hybrid_retrieval.py app/mind/memory.py app/mind/context.py`
- `cd backend && .venv/bin/python app/evals/codex_test_memory_harness.py --reset --target-count 240`
- `cd backend && .venv/bin/python -m pytest tests -q`
- Live HTTP check against `http://127.0.0.1:8000/mind/call` returned the
  controlled `ct_food_evening_no_caffeine` memory first in `codex_test` mode.

Residual Risk:

The Codex test harness is now usable, but ranking is not yet tuned. The next
step should separate exact controlled-key recall from functionally equivalent
recall before changing retrieval weights or KG expansion behavior.

---

Date: 2026-06-19

Area:

Memory / corrected chat-context evaluation / live Scarlet comparison.

Type:

Implementation/evaluation inside V1.13.0.

Goal:

Correct the memory test methodology so it measures the same automatic
`memory_context` passed to Scarlet, then compare five predictions against live
MiniMax M3 behavior.

Changes:

- Extended `backend/app/evals/codex_test_memory_harness.py` with
  `context_eval`.
- `context_eval` drives `/api/chat/sessions/{id}/turn/stream` with a fake
  provider and captures the streamed `memory_context` and `runtime_context`.
- Reworked controlled seed content to Italian, closer to Scarlet's real memory
  style, avoiding an artificial English benchmark bias.
- Added stricter negative-control scoring so unrelated prompts fail when any
  selected memory is present.

Evidence:

- Corrected context run:
  `backend/app/evals/runs/20260619_172206_codex_test_memory/`.
- Live Scarlet/MiniMax M3 run:
  `backend/app/evals/runs/20260619_172536_codex_live_scarlet_memory/`.

Results:

- Context eval: 2/5 strict pass.
- Confirmed system strengths:
  - brief-when-tired preference retrieval;
  - semantic-memory anchor to episodic source-session bridge.
- Confirmed model strengths:
  - MiniMax M3 used the episodic bridge correctly and opened the source
    session;
  - MiniMax M3 ignored an unrelated project memory in the jazz/cooking control;
  - MiniMax M3 could answer effort-routing correctly from prompt/system
    knowledge even when retrieval supplied the wrong metacognitive lessons.
- Confirmed system weaknesses:
  - beverage query missed chocolate as adjacent personal constraint and
    selected repeated food distractors;
  - effort-routing query selected repeated memory-as-anchor lessons instead of
    the effort-routing lesson;
  - unrelated jazz/cooking query selected a project memory from weak overlap.

Verification:

- `cd backend && .venv/bin/python -m py_compile app/evals/codex_test_memory_harness.py`
- `cd backend && .venv/bin/python app/evals/codex_test_memory_harness.py --reset --target-count 240`
- Live HTTP stream run against backend started with `CODEX_TEST=true`.

Residual Risk:

No ranking or prompt fix was applied. The evidence should drive a focused
retrieval calibration step rather than a broad prompt workaround.
