import Foundation

// MARK: - Time-Gated Multi-Target Amenity Router (TECH_SPEC Section 2.3, 3.2 & 4)

/// Full resolution result pairing a selected `MountainServiceRecord` with its optimal path and weighted travel time.
public struct AmenityRouteMatch: Equatable, Hashable, Sendable {
    public let selectedVenue: MountainServiceRecord
    public let route: [RouteStep]
    public let totalCostSeconds: Double

    public init(
        selectedVenue: MountainServiceRecord,
        route: [RouteStep],
        totalCostSeconds: Double
    ) {
        self.selectedVenue = selectedVenue
        self.route = route
        self.totalCostSeconds = totalCostSeconds
    }
}

/// Coordinates temporal amenity filtering over `mountain_services` with single-pass 1-to-N multi-target Dijkstra routing.
///
/// Design Highlights:
/// 1. **Temporal & Service-Style Pre-Filtering**: Eliminates closed, seasonal, reservation-gated, or mismatched-speed
///    venues before invoking graph traversal.
/// 2. **Single-Pass 1-to-N Dijkstra**: Rather than running `N` separate 1-to-1 shortest-path searches, passes the
///    unified `Set<String>` of candidate venue `nodeId`s into `CirqueGraphSolver` and halts on the first target popped
///    from the binary min-heap — guaranteeing the globally lowest-cost safe route in `O((V + E) log V)` time.
public final class AmenityRouter {

    public let database: CirqueDatabase
    public let overlayManager: DynamicOverlayManager?
    public let solver: CirqueGraphSolver

    public init(
        database: CirqueDatabase,
        overlayManager: DynamicOverlayManager? = nil
    ) {
        self.database = database
        self.overlayManager = overlayManager
        self.solver = CirqueGraphSolver(database: database, overlayManager: overlayManager)
    }

    // MARK: - 1. Temporal & Service-Tier Candidate Venue Resolution

    /// Resolves all open on-mountain venues matching the category, service speed, reservation rules, and local operating window in `query`.
    public func resolveCandidateVenues(for query: RouteQuery) -> [MountainServiceRecord] {
        let categoryFilter = Self.normalizeCategory(query.targetPoiCategory)
        let speedFilter = Self.normalizeNonEmpty(query.preferredServiceSpeed)

        let currentMinutes: Int?
        if query.requireOpenNow, let rawTime = Self.normalizeNonEmpty(query.currentTimeLocal) {
            guard let parsed = Self.parseMinutesSinceMidnight(rawTime) else {
                return []
            }
            currentMinutes = parsed
        } else {
            currentMinutes = nil
        }

        // Query composite index (category, service_speed, daily_status='open'); evaluate time windows via
        // isVenueOpen below so midnight-spanning apres-ski hours (e.g. 16:00-01:00) are not dropped by SQL BETWEEN.
        let dbServices = database.getServices(
            category: categoryFilter,
            speed: speedFilter,
            timeLocal: nil
        )

        let normalizedPoiName = Self.normalizeNonEmpty(query.targetPoiName)?.lowercased()
        let disallowReservations = query.excludeReservations
            || categoryFilter == "quick_snack"
            || speedFilter == "grab_and_go"

        return dbServices.filter { venue in
            if let currentMinutes, !Self.isVenueOpen(venue, atMinutesSinceMidnight: currentMinutes) {
                return false
            }
            if disallowReservations && venue.requiresReservation {
                return false
            }
            if let normalizedPoiName, !venue.name.lowercased().contains(normalizedPoiName) {
                return false
            }
            return true
        }
    }

    // MARK: - 2. Multi-Destination Optimal Pathfinding

    /// Solves for the globally lowest-cost reachable venue satisfying `query` (downhill pistes + aerial lifts)
    /// while strictly enforcing `query.maxDifficulty` and live `DynamicOverlayManager` exclusions.
    ///
    /// - Parameter query: Structured `RouteQuery` containing `startNodeId`, temporal/amenity filters, and terrain constraints.
    /// - Returns: `(selectedVenue, route)` tuple for the optimal reachable venue, or `nil` if no qualifying venue is safely reachable.
    public func findOptimalAmenityRoute(
        for query: RouteQuery
    ) -> (selectedVenue: MountainServiceRecord, route: [RouteStep])? {
        guard let match = findOptimalAmenityMatch(for: query) else {
            return nil
        }
        return (selectedVenue: match.selectedVenue, route: match.route)
    }

    /// Convenience overload allowing an explicit `startNodeId` override atop an existing `RouteQuery`.
    public func findOptimalAmenityRoute(
        startNodeId: String,
        query: RouteQuery
    ) -> (selectedVenue: MountainServiceRecord, route: [RouteStep])? {
        let overriddenQuery = RouteQuery(
            startNodeId: startNodeId,
            targetNodeId: query.targetNodeId,
            targetPoiCategory: query.targetPoiCategory,
            targetPoiName: query.targetPoiName,
            preferredServiceSpeed: query.preferredServiceSpeed,
            currentTimeLocal: query.currentTimeLocal,
            requireOpenNow: query.requireOpenNow,
            maxDifficulty: query.maxDifficulty,
            preferGroomed: query.preferGroomed,
            avoidMoguls: query.avoidMoguls,
            excludeReservations: query.excludeReservations
        )
        return findOptimalAmenityRoute(for: overriddenQuery)
    }

    /// Rich variant of `findOptimalAmenityRoute(for:)` exposing `totalCostSeconds` for telemetry and benchmarking.
    public func findOptimalAmenityMatch(for query: RouteQuery) -> AmenityRouteMatch? {
        let candidateVenues = resolveCandidateVenues(for: query)
        guard !candidateVenues.isEmpty else {
            return nil
        }

        // Group qualifying venues by snapped topological nodeId
        var venuesByNodeId: [String: [MountainServiceRecord]] = [:]
        for venue in candidateVenues {
            venuesByNodeId[venue.nodeId, default: []].append(venue)
        }

        let candidateNodeIds = Set(venuesByNodeId.keys)

        // Execute single-pass 1-to-N Dijkstra across all candidate target vertices simultaneously
        guard let resolvedRoute = solver.solveShortestPath(
            toCandidateNodes: candidateNodeIds,
            query: query
        ),
        let matchingNodeVenues = venuesByNodeId[resolvedRoute.destinationNodeId],
        let selectedVenue = Self.selectBestVenueAtNode(matchingNodeVenues, for: query) else {
            return nil
        }

        return AmenityRouteMatch(
            selectedVenue: selectedVenue,
            route: resolvedRoute.steps,
            totalCostSeconds: resolvedRoute.totalCostSeconds
        )
    }

    // MARK: - Private Normalization & Temporal Helpers

    private static func selectBestVenueAtNode(
        _ venues: [MountainServiceRecord],
        for query: RouteQuery
    ) -> MountainServiceRecord? {
        let preferredSpeed = normalizeNonEmpty(query.preferredServiceSpeed)
        return venues.sorted { lhs, rhs in
            // Prefer non-reservation venues first when tied at the exact same junction node
            if lhs.requiresReservation != rhs.requiresReservation {
                return !lhs.requiresReservation
            }
            // Prefer exact service_speed match when query did not hard-filter speed
            if let preferredSpeed {
                let lhsMatches = (lhs.serviceSpeed == preferredSpeed)
                let rhsMatches = (rhs.serviceSpeed == preferredSpeed)
                if lhsMatches != rhsMatches {
                    return lhsMatches
                }
            }
            return lhs.serviceId < rhs.serviceId
        }.first
    }

    private static func normalizeCategory(_ rawCategory: String?) -> String? {
        guard let trimmed = normalizeNonEmpty(rawCategory) else {
            return nil
        }
        switch trimmed.lowercased() {
        case "restaurant_sitdown", "sitdown":
            return "sit_down"
        default:
            return trimmed.lowercased()
        }
    }

    private static func normalizeNonEmpty(_ value: String?) -> String? {
        guard let trimmed = value?.trimmingCharacters(in: .whitespacesAndNewlines),
              !trimmed.isEmpty else {
            return nil
        }
        return trimmed
    }

    private static func isVenueOpen(
        _ venue: MountainServiceRecord,
        atMinutesSinceMidnight currentMinutes: Int
    ) -> Bool {
        guard let openMinutes = parseMinutesSinceMidnight(venue.openTimeLocal),
              let closeMinutes = parseMinutesSinceMidnight(venue.closeTimeLocal) else {
            return false
        }
        if openMinutes <= closeMinutes {
            return currentMinutes >= openMinutes && currentMinutes <= closeMinutes
        } else {
            // Supports late-night apres venues crossing midnight (e.g. 16:00 -> 01:00)
            return currentMinutes >= openMinutes || currentMinutes <= closeMinutes
        }
    }

    private static func parseMinutesSinceMidnight(_ timeString: String) -> Int? {
        let parts = timeString.trimmingCharacters(in: .whitespacesAndNewlines).split(separator: ":")
        guard parts.count == 2,
              let hours = Int(parts[0]),
              let minutes = Int(parts[1]),
              (0...23).contains(hours),
              (0...59).contains(minutes) else {
            return nil
        }
        return (hours * 60) + minutes
    }
}
