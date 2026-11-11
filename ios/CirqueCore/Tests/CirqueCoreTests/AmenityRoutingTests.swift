import XCTest
import Foundation
@testable import CirqueCore

final class AmenityRoutingTests: XCTestCase {

    /// Models an intermediate skier starting at `andesite_summit` (2,682m):
    /// - **Venue A (`Shedhorn Grill`)**: `quick_snack`, `grab_and_go`, open `11:00`–`15:30`, no reservation (`trail_africa`, 140s).
    /// - **Venue B (`Everett's 8800`)**: `sit_down`, `table_service`, open `11:00`–`15:00`, `requires_reservation = 1`.
    /// - **Venue C (`Black Canyon Espresso Cafe`)**: `quick_snack`, `grab_and_go`, reachable ONLY via Advanced black run `Ambush` (85s).
    /// - **Fallback Base Venue (`Vista Hall Grab & Go`)**: `quick_snack`, `grab_and_go`, open `08:00`–`17:00` via Novice `Mr. K` (280s).
    private static let bigSkyAmenitySeedSQL = """
    INSERT INTO nodes (node_id, name, lat, lon, elevation_m, node_type, poi_category) VALUES
        ('andesite_summit', 'Andesite Mountain Summit', 45.2730, -111.4120, 2682.0, 'summit', NULL),
        ('everetts_lodge', 'Everett''s 8800 Lodge', 45.2728, -111.4118, 2676.0, 'poi', 'restaurant_sitdown'),
        ('shedhorn_hub', 'Shedhorn Grill Junction', 45.2630, -111.4390, 2520.0, 'poi', 'cafeteria'),
        ('black_canyon_base', 'Black Canyon Base', 45.2805, -111.4070, 2390.0, 'poi', 'cafeteria'),
        ('village_mountain_village', 'Mountain Village Base', 45.2840, -111.4010, 2286.0, 'village', 'cafeteria');

    INSERT INTO edges (
        edge_id, source_node, target_node, type, name,
        difficulty, grooming, length_m, vertical_diff_m, average_pitch_pct, base_cost_seconds
    ) VALUES
        ('trail_everetts_glide', 'andesite_summit', 'everetts_lodge', 'piste', 'Everett''s Access Glide', 'novice', 'groomed', 90.0, -6.0, 6.7, 25.0),
        ('trail_africa', 'andesite_summit', 'shedhorn_hub', 'piste', 'Africa', 'intermediate', 'groomed', 1850.0, -162.0, 18.5, 140.0),
        ('trail_ambush', 'andesite_summit', 'black_canyon_base', 'piste', 'Ambush', 'advanced', 'mogul', 1180.0, -292.0, 34.0, 85.0),
        ('trail_mr_k', 'andesite_summit', 'village_mountain_village', 'piste', 'Mr. K', 'novice', 'groomed', 2650.0, -396.0, 14.9, 280.0);

    INSERT INTO mountain_services (
        service_id, node_id, name, category, service_speed,
        open_time_local, close_time_local, requires_reservation,
        price_tier, is_ski_in_only, daily_status
    ) VALUES
        ('srv_shedhorn_grill', 'shedhorn_hub', 'Shedhorn Grill', 'quick_snack', 'grab_and_go', '11:00', '15:30', 0, '$$', 1, 'open'),
        ('srv_everetts_8800', 'everetts_lodge', 'Everett''s 8800', 'sit_down', 'table_service', '11:00', '15:00', 1, '$$$', 1, 'open'),
        ('srv_everetts_tasting_bar', 'everetts_lodge', 'Everett''s Summit Tasting Counter', 'quick_snack', 'grab_and_go', '11:00', '15:00', 1, '$$$', 1, 'open'),
        ('srv_black_canyon_cafe', 'black_canyon_base', 'Black Canyon Espresso Cafe', 'quick_snack', 'grab_and_go', '08:00', '17:00', 0, '$$', 1, 'open'),
        ('srv_vista_hall_grab_go', 'village_mountain_village', 'Vista Hall Grab & Go', 'quick_snack', 'grab_and_go', '08:00', '17:00', 0, '$$', 0, 'open');
    """

    private var db: CirqueDatabase!
    private var overlayManager: DynamicOverlayManager!
    private var router: AmenityRouter!

    override func setUpWithError() throws {
        try super.setUpWithError()
        db = try CirqueDatabase(path: ":memory:", mode: .readWriteCreate)
        try db.executeRaw(TestGraphSchema.relationalGraphDDL)
        try db.executeRaw(Self.bigSkyAmenitySeedSQL)
        try db.enableQueryOnlyMode()

        overlayManager = DynamicOverlayManager()
        router = AmenityRouter(database: db, overlayManager: overlayManager)
    }

    override func tearDownWithError() throws {
        router = nil
        overlayManager = nil
        db?.close()
        db = nil
        try super.tearDownWithError()
    }

    // MARK: - 1. Intermediate Mid-Day Quick Snack Routing (13:15 -> Shedhorn Grill via Africa)

    func testIntermediateSnackRouting() throws {
        let query = RouteQuery(
            startNodeId: "andesite_summit",
            targetPoiCategory: "quick_snack",
            preferredServiceSpeed: "grab_and_go",
            currentTimeLocal: "13:15",
            requireOpenNow: true,
            maxDifficulty: .intermediate,
            preferGroomed: true,
            avoidMoguls: false
        )

        // Verify candidate resolution includes open, reservation-free grab-and-go snack venues
        let candidates = router.resolveCandidateVenues(for: query)
        let candidateIds = Set(candidates.map(\.serviceId))
        XCTAssertTrue(candidateIds.contains("srv_shedhorn_grill"))
        XCTAssertTrue(candidateIds.contains("srv_black_canyon_cafe"))
        XCTAssertTrue(candidateIds.contains("srv_vista_hall_grab_go"))
        XCTAssertFalse(candidateIds.contains("srv_everetts_8800"), "Sit-down reservation restaurant must not appear in quick_snack candidates.")

        // Solve multi-target pathfinding across all candidate venues
        let result = try XCTUnwrap(
            router.findOptimalAmenityRoute(for: query),
            "AmenityRouter must find an optimal safe route for an intermediate skier at 13:15."
        )

        // Assert Shedhorn Grill is selected (140s * 0.8 = 112s via Africa < 280s * 0.8 = 224s via Mr. K,
        // while 85s Black Canyon Espresso Cafe via Ambush is rejected due to .advanced > .intermediate!)
        XCTAssertEqual(result.selectedVenue.serviceId, "srv_shedhorn_grill")
        XCTAssertEqual(result.selectedVenue.name, "Shedhorn Grill")
        XCTAssertEqual(result.route.map(\.edgeId), ["trail_africa"])

        // Assert 100% of route steps are Novice or Intermediate trails (0 Black / Expert runs)
        XCTAssertFalse(result.route.isEmpty)
        for step in result.route where step.type == .piste {
            XCTAssertTrue(
                step.difficulty == .novice || step.difficulty == .intermediate,
                "Expected exclusively novice or intermediate pistes, encountered \(step.difficulty.rawValue) on \(step.name)."
            )
        }
        let blackOrHigherCount = result.route.filter { $0.difficulty >= .advanced }.count
        XCTAssertEqual(blackOrHigherCount, 0, "0 Black or Expert runs may appear in an intermediate snack route.")
    }

    // MARK: - 2. Time-Gated Closed Venue Exclusion (16:00 -> Excludes Shedhorn, Routes to Base Venue)

    func testTimeGatedClosedVenueExcluded() throws {
        let lateAfternoonQuery = RouteQuery(
            startNodeId: "andesite_summit",
            targetPoiCategory: "quick_snack",
            preferredServiceSpeed: "grab_and_go",
            currentTimeLocal: "16:00",
            requireOpenNow: true,
            maxDifficulty: .intermediate,
            preferGroomed: true,
            avoidMoguls: false
        )

        // At 16:00, Shedhorn Grill (11:00-15:30) is closed and must be excluded from candidates
        let openCandidatesAt1600 = router.resolveCandidateVenues(for: lateAfternoonQuery)
        let candidateIds = Set(openCandidatesAt1600.map(\.serviceId))
        XCTAssertFalse(
            candidateIds.contains("srv_shedhorn_grill"),
            "Shedhorn Grill closes at 15:30 and must be excluded when currentTimeLocal is 16:00."
        )
        XCTAssertTrue(candidateIds.contains("srv_vista_hall_grab_go"))

        // Multi-target solver must ignore Black Canyon Espresso Cafe (behind Black run Ambush)
        // and route safely down Novice Mr. K to Vista Hall Grab & Go at Mountain Village Base
        let lateRouteResult = try XCTUnwrap(
            router.findOptimalAmenityRoute(for: lateAfternoonQuery),
            "AmenityRouter must fall back to the open Mountain Village base venue at 16:00."
        )

        XCTAssertEqual(lateRouteResult.selectedVenue.serviceId, "srv_vista_hall_grab_go")
        XCTAssertEqual(lateRouteResult.selectedVenue.name, "Vista Hall Grab & Go")
        XCTAssertEqual(lateRouteResult.route.map(\.edgeId), ["trail_mr_k"])
        XCTAssertEqual(lateRouteResult.route.first?.difficulty, .novice)
    }

    // MARK: - 3. Reservation Exclusion (Excludes Closer Everett's 8800 & Reservation Counters)

    func testReservationExclusion() throws {
        // 1. Even though Everett's Lodge is only 25 seconds from andesite_summit (closer than Shedhorn Grill at 140s),
        // a quick-snack query without reservations cleanly excludes both Everett's 8800 (sit_down, reservation=1)
        // and Everett's Summit Tasting Counter (quick_snack, grab_and_go, reservation=1).
        let noReservationSnackQuery = RouteQuery(
            startNodeId: "andesite_summit",
            targetPoiCategory: "quick_snack",
            preferredServiceSpeed: "grab_and_go",
            currentTimeLocal: "13:15",
            requireOpenNow: true,
            maxDifficulty: .intermediate,
            preferGroomed: true,
            avoidMoguls: false,
            excludeReservations: true
        )

        let snackCandidates = router.resolveCandidateVenues(for: noReservationSnackQuery)
        XCTAssertTrue(
            snackCandidates.allSatisfy { !$0.requiresReservation },
            "All resolved candidate venues must have requiresReservation == false."
        )
        XCTAssertFalse(snackCandidates.contains { $0.serviceId == "srv_everetts_8800" })
        XCTAssertFalse(snackCandidates.contains { $0.serviceId == "srv_everetts_tasting_bar" })

        let snackSelection = try XCTUnwrap(router.findOptimalAmenityRoute(for: noReservationSnackQuery))
        XCTAssertEqual(snackSelection.selectedVenue.serviceId, "srv_shedhorn_grill")

        // 2. Category-agnostic dining query with excludeReservations = true also excludes Everett's 8800
        let anyOpenWalkInQuery = RouteQuery(
            startNodeId: "andesite_summit",
            targetPoiCategory: nil,
            preferredServiceSpeed: nil,
            currentTimeLocal: "13:15",
            requireOpenNow: true,
            maxDifficulty: .intermediate,
            preferGroomed: true,
            avoidMoguls: false,
            excludeReservations: true
        )

        let walkInCandidates = router.resolveCandidateVenues(for: anyOpenWalkInQuery)
        XCTAssertFalse(
            walkInCandidates.contains { $0.serviceId == "srv_everetts_8800" },
            "Everett's 8800 requires a reservation and must be excluded even when category filter is nil."
        )
        let walkInSelection = try XCTUnwrap(router.findOptimalAmenityRoute(for: anyOpenWalkInQuery))
        XCTAssertEqual(walkInSelection.selectedVenue.serviceId, "srv_shedhorn_grill")
    }

    // MARK: - 4. Dynamic Overlay Patrol Closure Redirects Multi-Target Amenity Selection

    func testDynamicPatrolClosureRedirectsAmenitySelection() throws {
        let query = RouteQuery(
            startNodeId: "andesite_summit",
            targetPoiCategory: "quick_snack",
            preferredServiceSpeed: "grab_and_go",
            currentTimeLocal: "13:15",
            requireOpenNow: true,
            maxDifficulty: .intermediate,
            preferGroomed: true,
            avoidMoguls: false
        )

        // Patrol closes trail_africa -> Shedhorn Grill becomes unreachable; solver reroutes to Vista Hall via Mr. K
        overlayManager.setStatus(edgeId: "trail_africa", status: .closedPatrol, grooming: nil)

        let rerouted = try XCTUnwrap(router.findOptimalAmenityRoute(for: query))
        XCTAssertEqual(rerouted.selectedVenue.serviceId, "srv_vista_hall_grab_go")
        XCTAssertEqual(rerouted.route.map(\.edgeId), ["trail_mr_k"])
    }

    // MARK: - 5. Unreachable Black-Only Venue Returns Nil Safely

    func testUnreachableBlackOnlyVenueReturnsNilForIntermediateSkier() throws {
        // Query specifically for "Black Canyon Espresso Cafe" (reachable ONLY via Advanced black run Ambush)
        let blackCafeQuery = RouteQuery(
            startNodeId: "andesite_summit",
            targetPoiCategory: "quick_snack",
            targetPoiName: "Black Canyon Espresso",
            preferredServiceSpeed: "grab_and_go",
            currentTimeLocal: "13:15",
            requireOpenNow: true,
            maxDifficulty: .intermediate,
            preferGroomed: false,
            avoidMoguls: false
        )

        let candidates = router.resolveCandidateVenues(for: blackCafeQuery)
        XCTAssertEqual(candidates.map(\.serviceId), ["srv_black_canyon_cafe"])

        let unsafeResult = router.findOptimalAmenityRoute(for: blackCafeQuery)
        XCTAssertNil(
            unsafeResult,
            "AmenityRouter must return nil rather than routing an intermediate skier down Black run Ambush."
        )
    }
}
