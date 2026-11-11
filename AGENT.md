# Project Cirque: Agent Operational Guidelines & Architecture Manual

## 1. System Mission & Core Architecture
Project Cirque is an asymmetric, offline-first spatial intelligence ski concierge operating in Airplane Mode on-mountain:
- **Cloud Compilation Plane:** Google Cloud Run (`cirque-compiler`, `cirque-api`, `telemetry-sync`) + AlloyDB (PostGIS/pgRouting) + Cloud Storage + Cloud CDN.
- **Edge Execution Runtime:** iOS 18+ / Swift 6 / Core ML quantized Gemma 2B/4B / Embedded C-SQLite3 / SiriKit AppIntents.
- **Target Testbed:** Big Sky Resort, Montana (`bbox: [45.23, -111.47, 45.32, -111.34]`).

---

## 2. Non-Negotiable Architectural Invariants

1. **Immutable Mobile Cartography:**
   - `topology.sqlite` must be accessed strictly with `PRAGMA query_only = ON;` and `SQLITE_OPEN_READONLY | SQLITE_OPEN_NOMUTEX`.
   - Never write to or mutate `topology.sqlite` on mobile or client runtimes.
   - Dynamic states (wind holds, patrol closures, grooming overrides) must live 100% in volatile RAM (`DynamicOverlayManager`).
2. **Air-Gapped Socket Invariant:**
   - 0 network socket calls, 0 background telemetry pings, 0 external DNS lookups during the voice-query-to-audio-guidance loop.
3. **Hard Terrain Skill Ceilings:**
   - When `edge.difficulty > query.maxDifficulty`, `calculateCost` MUST return `nil`. Never route a skier onto terrain exceeding their declared ability.
4. **Latency Budgets:**
   - Single-pass 1-to-N Dijkstra: < 10.0 ms.
   - Dynamic overlay reroutes: < 5.0 ms.
   - Total voice-to-audio guidance loop: < 1.5 s.

---

## 3. Code Quality & Anti-Slop Protocol (Signs of AI Code to Avoid)

Act as a pragmatic Staff Engineer. Optimize for readability, locality of behavior, and maintainability over cleverness or ceremony. Adhere to the principles in `grugbrain.ai`, `jomadu/grug-brained-developer-ruleset`, `miqdadbadjuber/anti-slop`, `PatrickJS/awesome-cursorrules` (`anti-overengineering.mdc`), and `febbhav/signs-of-ai-design`.

### 3.1 Anti-Overengineering & Locality (The Grug Rule)
- **No Premature Abstraction:** Do not create interfaces, protocols, abstract base classes, factory patterns, or wrapper classes unless there are at least 3 concrete implementations already in the codebase. Prefer flat functions and simple structs.
- **Locality of Behavior:** Keep related logic together. A reader should understand what a function does without jumping across 5 files.
- **Minimal Diffs & Scope Discipline:** Only modify what was explicitly requested. Never perform "drive-by" refactoring, variable renaming, or formatting changes on untouched code.
- **Standard Library First:** Do not introduce third-party dependencies for tasks easily solved by the language's standard library.

### 3.2 Comment Hygiene (No AI Narration)
- **Zero "What" Comments:** Never write comments that restate the code (e.g., `// Loop through records`, `# Increment counter`, `// Return true`). If the code needs a "what" comment, rename the variables or extract a well-named helper function.
- **No Conversational Artifacts:** Never leave comments like `// Updated per user request`, `// Fixed bug here`, or `// TODO: add implementation later`.
- **Earned "Why" Comments Only:** Only write comments to explain *why* a non-obvious decision was made (e.g., a hardware quirk, a non-obvious mathematical formula, or a safety constraint).

### 3.3 Error Handling & Defensiveness
- **Fail Fast, Don't Swallow:** Never use bare `except:` or generic `catch` blocks that log and return `nil`/`None` unless explicitly required by a fault-tolerant pipeline boundary. Let unexpected errors raise with full context.
- **Trust Internal Types:** Validate data strictly at system boundaries (CLI args, API payloads, raw file ingestion). Inside internal functions, trust the type signatures—do not write redundant type checks or defensive assertions for guaranteed inputs.

### 3.4 Complete Implementations Only
- **No Semantic Mimicry:** Never output placeholder stubs (`pass`, `...`, `// implement here`) unless explicitly asked for scaffolding. Every function must work end-to-end.

### 3.5 UI & Design Discipline (When Building Web or Preview Artifacts)
- Follow `febbhav/signs-of-ai-design` (`design-rules.md`): Avoid the generic "AI dashboard" look—no gratuitous purple/cyan neon gradients, no floating glassmorphism cards with arbitrary box-shadows, and no generic marketing filler.
- Use purposeful typography, crisp high-contrast charts, authentic terrain data, and dense information hierarchies that respect the skier's situational context.

---

## 4. Human Voice Protocol (Anti-AI Writing Standards)

When drafting documentation, devlog summaries, LinkedIn carousels, Substack essays, or technical slide decks, strictly avoid the well-documented **signs of AI writing** (cataloged in Wikipedia's *Signs of AI writing* essay):

### 4.1 Banned AI Clichés & Buzzwords
Never use the following filler words, phrases, or rhetorical crutches:
- **Banned Words:** `tapestry`, `testament`, `crucial`, `pivotal`, `beacon`, `delve`, `foster`, `harnessing`, `revolutionize`, `seamless`, `game-changer`, `synergy`, `landscape` (metaphorical), `vibrant`.
- **Banned Intros & Outros:** `In today's fast-paced world...`, `It's important to remember...`, `In conclusion...`, `Furthermore...`, `Moreover...`, `Navigating the complexities of...`.
- **Banned Rhetorical Traps:** Rhetorical questions (`Have you ever wondered...?`), formulaic rule-of-three adjectives (`efficient, scalable, and robust`), and synthetic false balance (`While some might argue X, it is equally important to consider Y`).

### 4.2 Voice & Style Mandate
- **Tone:** Pragmatic, direct, opinionated systems engineer writing for peers.
- **Sentence Structure:** Vary sentence lengths. Use punchy one-sentence observations mixed with concrete explanations.
- **Specifics Over Fluff:** Anchor every statement in concrete numbers, specific mountain names, exact latency benchmarks, and code symbols (e.g., `0.092ms`, `Ramcharger 8`, `Ambush`, `PRAGMA query_only`).
- **Show the Scars:** Talk about real trade-offs, edge cases that broke, and non-obvious engineering decisions (e.g., why Dijkstra heap extraction beats iterative queries, why GPS fails in deep gullies).

---

## 5. Toolchain Shortcuts & Environment Cheat Sheet

To save tokens and execution time:
- **Swift 6 Toolchain:** Installed at `/tmp/swift/usr/bin/swift`.
  - Compile & test command:
    ```bash
    PATH="/tmp/swift/usr/bin:$PATH" swift test --package-path ios/CirqueCore --filter <TestClass>
    ```
  - Linux `CSQLite` module map is configured at `/tmp/swift/usr/lib/swift/linux/module.modulemap`.
  - In Linux XCTest, `XCTAssertEqual` with optional floating points requires the `#if !canImport(ObjectiveC)` overload.
- **Python Toolchain:** Python 3.11 with pre-installed `shapely`, `geopandas`, `pytest`.
  - Run pipeline tests: `pytest tests/pipeline/test_<module>.py -v`
  - Run SLM tests: `pytest tests/slm/test_<module>.py -v`
- **Database CLI:**
  - Direct read queries: `sqlite3 data/compiled/topology.sqlite "SELECT ... LIMIT 10;"`

---

## 6. Token Conservation Guardrails

> [!CAUTION]
> **Token Traps to Avoid:**
> 1. **Massive Files:** NEVER view or dump `data/raw/big_sky_raw.geojson` (71,825 lines). Use `jq` with bounds:
>    `jq '.features[] | select(.properties.name == "Ramcharger 8")' data/raw/big_sky_raw.geojson | head -n 30`
> 2. **Unbounded Database Scans:** NEVER run `SELECT * FROM edges` without `LIMIT`.
> 3. **Broad File Reads:** Use targeted `view_file` ranges (50–100 lines) instead of loading 500+ line files.
> 4. **No Polling Loops:** Antigravity automatically wakes on task completion. Do not run `while` loops on task status.

---

## 7. Step Execution & Delivery Protocol

For each step from `BUILD_PLAN.md`:
1. **Branch:** `git checkout -b feat/<step_id_slug>`
2. **Implement:** Write clean, complete code complying with Section 3 (Anti-Slop).
3. **Verify:** Run the dedicated test harness with timing benchmarks.
4. **Log Devlog:** Write `.cirque/devlog/<MILESTONE_ID>/<step_id>.json` and any required content pack in human voice (Section 4).
5. **Commit & PR:**
   ```bash
   git add <deliverables>
   git commit -m "feat(<module>): implement <feature_description>"
   git push -u origin feat/<step_id_slug>
   gh pr create --base main --head feat/<step_id_slug> --title "..." --body "..."
   ```
