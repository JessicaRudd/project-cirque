---
name: cirque-airgap-auditor
description: Audit iOS runtime code for strict compliance with offline air-gapped invariants (0 network sockets, PRAGMA query_only = ON, and difficulty skill ceilings).
---
# Cirque Air-Gap Auditor

Use this skill to audit deliverables and ensure zero regressions against Project Cirque's safety and air-gap invariants.

## 1. Zero Network Sockets Audit
Inspect any Swift code added to `ios/CirqueCore` or `ios/CirqueApp`:
- Ensure **zero** imports of `Network`, `WebKit`, or remote networking code in the routing and speech synthesis paths.
- No `URLSession.shared.dataTask`, `NWPathMonitor`, or background telemetry pings.
- All routing queries must execute 100% locally against cached memory or local SQLite.

## 2. Immutable SQLite Bundle Audit
- Assert that production SQLite connections enforce:
  `SQLITE_OPEN_READONLY | SQLITE_OPEN_NOMUTEX`
  and execute `PRAGMA query_only = ON;`.
- Ensure all volatile operational state (wind holds, patrol closures, grooming overrides) resides in `DynamicOverlayManager` in RAM.
- Verify that attempting a write against the connection raises a rejection error.

## 3. Hard Skill Ceiling Audit
- For any new or modified router (e.g. `CirqueGraphSolver`, `AmenityRouter`):
  Verify an intermediate skier (`maxDifficulty: .intermediate`) query cannot receive a route containing `.advanced`, `.expert`, or `.freeride` pistes.
  `calculateCost` MUST return `nil` for any edge where `edge.difficulty > query.maxDifficulty`.

## 4. Latency Budget Verification
Assert that performance tests clock well under the target budgets:
- Single-pass Dijkstra: `< 10.0 ms` (typical: `< 0.5 ms`).
- Dynamic wind-hold reroutes: `< 5.0 ms` (typical: `< 0.1 ms`).
- 1-to-N Amenity routing: `< 10.0 ms` (typical: `< 0.2 ms`).
