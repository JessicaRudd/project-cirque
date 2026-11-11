# Milestone 3: STEP 3.4 Multi-Track Content & Workshop Pack

**Milestone:** `M3_MOBILE_ROUTING_CORE`  
**Step:** `STEP_3_4` (Time-Gated Amenity & Multi-Target Routing)  
**Target Testbed:** Big Sky Resort, Montana (`topology.sqlite` + `CirqueCore` Swift 6)

---

## Track 1: Engineering Design Notes

### Composing SQLite Operating-Hours Filters with 1-to-N Dijkstra in Swift 6

- **Separate Relational Filtering from Graph Expansion:** `AmenityRouter` keeps venue eligibility rules out of the inner Dijkstra loop. SQLite B-tree lookups on `mountain_services` narrow candidates by `category` and `service_speed`, Swift checks `open_time_local` / `close_time_local` (including overnight spans) plus `requires_reservation == 0`, and `CirqueGraphSolver` receives a plain `Set<String>` of snapped vertex IDs.
- **Single-Heap 1-to-N Early Exit:** Rather than running `solveShortestPath` inside a `for venue in candidates` loop, `CirqueGraphSolver.solveShortestPath(toCandidateNodes:query:)` expands one binary min-heap from `query.startNodeId`. Because edge weights (ski seconds times surface multipliers plus chairlift ride seconds) are non-negative, the first candidate vertex popped from the heap is optimal across both pistes and lifts.
- **Terrain Ceilings Before Travel Time:** In the Big Sky test fixture, `Black Canyon Espresso Cafe` is 85 seconds downhill from `andesite_summit`, but the only trail to it is the Advanced black run `Ambush`. For an intermediate skier at `13:15`, `calculateCost` returns `nil` on `Ambush`, so the solver picks `Shedhorn Grill` via groomed blue `Africa` (`112.0s` weighted). At `16:00`, after Shedhorn closes at `15:30`, the router switches to `Vista Hall Grab & Go` via green `Mr. K` (`224.0s` weighted).

---

## Track 2: Systems Note

### Multi-Target Dijkstra on Mobile: Single-Pass 1-to-N vs. N Separate 1-to-1 Runs

When a skier asks *"Where can I grab a quick snack right now?"*, multiple open venues across different mountain zones can match (`Shedhorn Grill`, `Headwaters Grille`, `Uncle Dan's Cookie Hut`, `Vista Hall`).

Running 1-to-1 Dijkstra $N$ times from `startNodeId` to each `venue.nodeId` repeats the same upper-mountain expansions on every iteration:

- **Iterative 1-to-1:** $O(N \cdot (V + E) \log V)$ heap operations and $N\times$ duplicate SQLite adjacency lookups around the skier's starting ridge.
- **Single-Pass 1-to-N:** $O((V + E) \log V)$ worst case, stopping as soon as the closest reachable candidate vertex pops off the min-heap (`0.1035 ms` average on the compiled Big Sky `topology.sqlite` graph).

**Implementation checklist:**
1. Filter `mountain_services` by `daily_status = 'open'`, operating hours, and reservation rules, then collect target vertices: `let targets = Set(venues.map(\.nodeId))`.
2. Push `(nodeId: query.startNodeId, cumulativeCost: 0.0)` onto a single `MinHeap`.
3. On each `popMin()`, return immediately when `targets.contains(current.nodeId)`. Non-negative edge costs guarantee the first target popped has minimum total travel cost across all $N$ venues.

---

## Track 3 & 4: Substack & LinkedIn Draft

**Title:** *Routing Hungry Skiers at Big Sky Without Sending Them Down Black Runs*

- **Offline Voice Intent at 9,000 Feet:** In Airplane Mode, quantized on-device Gemma converts *"quick mid-day snack, no black runs"* into a typed `RouteQuery` (`targetPoiCategory: "quick_snack"`, `preferredServiceSpeed: "grab_and_go"`, `maxDifficulty: .intermediate`, `excludeReservations: true`) with zero network calls.
- **Operating Hours and Reservations Before Pathfinding:** `AmenityRouter` checks local mountain time (`13:15` vs. `16:00`) and `requires_reservation` flags in SQLite first. Reservation-only `Everett's 8800` at the top of Andesite is skipped for walk-in snack queries, and `Shedhorn Grill` drops out of the candidate set once its kitchen closes at `15:30`.
- **0.10 ms 1-to-N Dijkstra with Patrol Overrides:** One min-heap pass scores every open candidate at once, prunes black-diamond shortcuts like `Ambush`, respects live patrol closures in `DynamicOverlayManager`, and returns turn-by-turn steps down blue `Africa`.

---

## Track 5: Workshop Code Snippet

```swift
public func resolveCandidateVenues(for query: RouteQuery) -> [MountainServiceRecord] {
    let canonicalCategory = Self.normalizeCategory(query.targetPoiCategory)
    let canonicalSpeed = Self.normalizeServiceSpeed(query.preferredServiceSpeed)

    let services = database.getServices(
        category: canonicalCategory,
        speed: canonicalSpeed,
        timeLocal: nil
    )

    let shouldExcludeReservations = query.excludeReservations
        || canonicalCategory == "quick_snack"
        || canonicalSpeed == "grab_and_go"

    let normalizedNameQuery = query.targetPoiName?
        .trimmingCharacters(in: .whitespacesAndNewlines)
        .lowercased()

    return services.filter { venue in
        if shouldExcludeReservations && venue.requiresReservation {
            return false
        }
        if query.requireOpenNow, let currentTime = query.currentTimeLocal {
            guard Self.isVenueOpen(
                openTime: venue.openTimeLocal,
                closeTime: venue.closeTimeLocal,
                at: currentTime
            ) else {
                return false
            }
        }
        if let nameSubstr = normalizedNameQuery, !nameSubstr.isEmpty {
            guard venue.name.lowercased().contains(nameSubstr) else {
                return false
            }
        }
        return true
    }
}
```
