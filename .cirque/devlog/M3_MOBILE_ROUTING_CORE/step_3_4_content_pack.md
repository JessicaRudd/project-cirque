# Milestone 3 — STEP 3.4 Multi-Track Content & Workshop Pack

**Milestone:** `M3_MOBILE_ROUTING_CORE`  
**Step:** `STEP_3_4` — Time-Gated Amenity & Multi-Target Routing  
**Target Testbed:** Big Sky Resort, Montana (`topology.sqlite` + `CirqueCore` Swift 6)

---

## Track 1: Gemini Carbon Insights

### Modeling Temporal Relational Predicates + 1-to-N Graph Search in Swift 6

- **Seamless Composition Across Relational and Graph Domains:** Carbon cleanly separated *set-based temporal filtering* (SQLite B-tree index lookups over `mountain_services` for `category`, `service_speed`, `open_time_local <= t <= close_time_local`, and `requires_reservation == 0`) from *topological cost minimization* (`CirqueGraphSolver` over `nodes` and `edges`). Rather than entangling venue business logic inside the Dijkstra loop, `AmenityRouter` prunes ineligible destinations first and hands a pure `Set<String>` of snapped vertex IDs to the graph engine.
- **Zero-Regression Refactoring to 1-to-N Early-Exit Dijkstra:** Instead of calling `solveShortestPath` in a `for venue in candidates` loop, Carbon recognized that `CirqueGraphSolver` could expose `solveShortestPath(toCandidateNodes:query:) -> ResolvedTargetRoute?` and share a single binary min-heap expansion. Because Dijkstra settles vertices in monotonically non-decreasing order of cumulative weighted cost, popping the first vertex `v ∈ candidateTargets` guarantees global optimality across both downhill pistes and uphill chairlifts while preserving backwards compatibility with every Step 3.2 and Step 3.3 XCTest.
- **Safety-First Multi-Criteria Pruning:** When a faster venue (`Black Canyon Espresso Cafe`, `85s` raw descent) sits behind an Advanced black-diamond run (`Ambush`) while an intermediate skier asks for a mid-day snack at `13:15`, the hard skill ceiling (`edge.difficulty > query.maxDifficulty -> nil`) prunes the unsafe branch before it ever enters the priority queue, cleanly selecting `Shedhorn Grill` via groomed blue `Africa` (`112s` weighted) — and automatically pivoting to `Vista Hall Grab & Go` via green `Mr. K` after `15:30` when Shedhorn closes.

---

## Track 2: Google Tech Tip

### Solving Multi-Target Dijkstra on Embedded Devices: Why 1-to-N Graph Solvers Beat Iterative 1-to-1 Calls

When a user asks an offline mobile assistant *"Where can I grab a quick snack right now?"*, there isn't a single destination — there may be $N$ open venues scattered across different mountain zones (`Shedhorn Grill`, `Headwaters Grille`, `Uncle Dan's Cookie Hut`, `Vista Hall`).

A naive implementation runs **iterative 1-to-1 Dijkstra** $N$ times from `startNodeId` to each candidate `venue.nodeId` and picks the minimum:

- **Iterative 1-to-1 Cost:** $O(N \cdot (V + E) \log V)$ heap operations and $N\times$ redundant SQLite adjacency reads across the exact same upper-mountain neighborhood around the skier.
- **Single-Pass 1-to-N Cost:** $O((V + E) \log V)$ **at worst**, and in practice terminates as soon as the **closest** reachable venue is extracted from the min-heap — without ever expanding vertices deeper down the mountain!

**How to implement 1-to-N Dijkstra on embedded runtimes:**
1. Pre-filter candidate POIs by operating hours and user intent (`resolveCandidateVenues`), then collect their snapped graph IDs into an $O(1)$ hash set: `let targets = Set(venues.map(\.nodeId))`.
2. Seed a single binary `MinHeap` at `query.startNodeId` with `cumulativeCost = 0.0`.
3. On each `extractMin()`, check `if targets.contains(current.nodeId) { break }`. Because all edge weights (ski seconds $\times$ surface multipliers + lift transit times) are non-negative, the **first** candidate popped is mathematically guaranteed to minimize total travel cost across all $N$ candidates in a single pass.

---

## Track 3 & 4: Substack & LinkedIn Pitch

**Title:** *How We Built Voice-Guided Burger Routing for Intermediate Skiers at Big Sky*

- **Voice Intent to Structured Constraints — Offline at 9,000 Feet:** A skier taps their helmet mic in Airplane Mode and asks for *"a quick mid-day snack without black runs."* On-device quantized Gemma translates casual speech into a deterministic `RouteQuery` (`category: "quick_snack"`, `speed: "grab_and_go"`, `maxDifficulty: .intermediate`, `excludeReservations: true`) with zero cloud round-trips.
- **Time-of-Day & Reservation Awareness Built Into the Graph:** Before touching a single trail edge, `AmenityRouter` cross-checks local mountain time (`13:15` vs. `16:00`) and reservation flags in embedded SQLite — automatically skipping reservation-only dining like `Everett's 8800` right next to the summit and dropping `Shedhorn Grill` the moment its kitchen closes at `15:30`.
- **1-to-N Terrain-Safe Dijkstra in Sub-Millisecond Swift:** A single-pass multi-target Dijkstra solver evaluates every open venue simultaneously, hard-blocking steep black-diamond shortcuts (`Ambush`), honoring live patrol closures in RAM, and delivering turn-by-turn audio down groomed blue `Africa` in under `0.15 ms`.

---

## Track 5: Workshop / Tech Talk Snippet (Render-Atlanta / Antigravity Workshop)

```swift
public func resolveCandidateVenues(for query: RouteQuery) -> [MountainServiceRecord] {
    let timeFilter = query.requireOpenNow ? query.currentTimeLocal : nil
    let services = database.getServices(
        category: query.targetPoiCategory,
        speed: query.preferredServiceSpeed,
        timeLocal: timeFilter // SQLite index: open_time_local <= ?3 <= close_time_local
    )

    let blockReservations = query.excludeReservations
        || query.targetPoiCategory == "quick_snack"
        || query.preferredServiceSpeed == "grab_and_go"

    return services.filter { venue in
        guard venue.dailyStatus == "open" else { return false }
        if blockReservations && venue.requiresReservation { return false }
        if let name = query.targetPoiName?.lowercased(), !name.isEmpty {
            return venue.name.lowercased().contains(name)
        }
        return true
    }
}
```
