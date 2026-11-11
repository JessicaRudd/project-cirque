---
name: cirque-step-runner
description: Autonomous step execution engine for Project Cirque. Manages branch creation, anti-slop code generation, test harnesses, human-voice devlog summaries, and GitHub PR creation.
---
# Cirque Step Runner

Use this skill when executing any step from `BUILD_PLAN.md` (e.g. `STEP_4_1`, `STEP_4_2`, etc.).

## 1. Step Initiation & Branching
- Check current Git branch. If on `main`, pull latest: `git pull --ff-only origin main`.
- Create a dedicated feature branch: `git checkout -b feat/<step_id_slug>`.

## 2. Engineering Standards (Anti-Slop Protocol)
Follow the anti-overengineering and locality rules from `grugbrain.ai` and `PatrickJS/awesome-cursorrules`:
- **Locality over ceremony:** Write flat, cohesive functions and simple structs. Do not invent protocols or wrapper layers unless there are 3+ concrete implementations.
- **No comment narration:** Never write comments explaining *what* the code does (`// Loop through items`). Write earned *why* comments only.
- **Fail fast:** Never swallow errors with broad catch blocks.
- **Complete code:** Zero placeholder stubs (`pass`, `...`, `// implement later`). Every deliverable must run end-to-end.

## 3. Test Harness Execution
- **Swift Core (`ios/CirqueCore`):**
  ```bash
  PATH="/tmp/swift/usr/bin:$PATH" swift test --package-path ios/CirqueCore --filter <TestClass>
  ```
  *Note:* On Linux XCTest, if using `XCTAssertEqual` with optional `FloatingPoint` accuracy, include the `#if !canImport(ObjectiveC)` overload.
- **Python Pipelines / SLM:**
  ```bash
  pytest tests/<dir>/test_<module>.py -v
  ```

## 4. Human-Voice Devlog & Content Generation
When writing `.cirque/devlog/<MILESTONE_ID>/<step_id>.json` or content packs:
- **Avoid AI Writing Clichés:** Do NOT use words from Wikipedia's signs of AI writing (`tapestry`, `testament`, `crucial`, `pivotal`, `beacon`, `delve`, `seamless`, `game-changer`, `landscape`).
- **Tone:** Direct, technical, opinionated systems engineer writing for peers. Anchor all statements with concrete metrics, trail names, and latency numbers.

## 5. Commit, Push & PR Creation
- Add deliverables and devlog artifacts.
- Commit with conventional commit message: `feat(<module>): ...`.
- Push to remote: `git push -u origin feat/<step_id_slug>`.
- Open pull request:
  ```bash
  gh pr create --base main --head feat/<step_id_slug> --title "feat(<module>): ..." --body "..."
  ```
