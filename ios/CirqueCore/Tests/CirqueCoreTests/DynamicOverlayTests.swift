import XCTest
import Foundation
@testable import CirqueCore

final class DynamicOverlayTests: XCTestCase {

    // MARK: - Section 2.3 Relational Graph DDL Fixture

    private static let relationalGraphDDL = """
    PRAGMA foreign_keys = ON;

    CREATE TABLE nodes (
        node_id TEXT PRIMARY KEY,
        name TEXT,
        lat REAL NOT NULL,
        lon REAL NOT NULL,
        elevation_m REAL NOT NULL,
        node_type TEXT CHECK(node_type IN ('trail_junction', 'lift_base', 'lift_top', 'poi', 'summit', 'village')),
        poi_category TEXT CHECK(poi_category IN ('restaurant_sitdown', 'cafeteria', 'warming_hut', 'patrol', 'restroom', NULL))
    );

    CREATE TABLE edges (
        edge_id TEXT PRIMARY KEY,
        source_node TEXT NOT NULL REFERENCES nodes(node_id),
        target_node TEXT NOT NULL REFERENCES nodes(node_id),
        type TEXT NOT NULL CHECK(type IN ('piste', 'lift')),
        name TEXT NOT NULL,
        difficulty TEXT CHECK(difficulty IN ('novice', 'intermediate', 'advanced', 'expert', 'freeride', 'lift')),
        grooming TEXT CHECK(grooming IN ('groomed', 'backcountry', 'mogul', NULL)),
        length_m REAL NOT NULL,
        vertical_diff_m REAL NOT NULL,
        average_pitch_pct REAL NOT NULL,
        base_cost_seconds REAL NOT NULL,
        FOREIGN KEY(source_node) REFERENCES nodes(node_id),
        FOREIGN KEY(target_node) REFERENCES nodes(node_id)
    );

    CREATE INDEX idx_edges_source ON edges(source_node);
    CREATE INDEX idx_edges_target ON edges(target_node);
    CREATE INDEX idx_edges_type_diff ON edges(type, difficulty);
    CREATE INDEX idx_nodes_coords ON nodes(lat, lon);
    CREATE INDEX idx_nodes_poi ON nodes(poi_category);

    CREATE TABLE dynamic_status_overlay (
        edge_id TEXT PRIMARY KEY REFERENCES edges(edge_id),
        status TEXT NOT NULL CHECK(status IN ('open', 'closed_patrol', 'wind_hold', 'mechanical_hold')),
        effective_grooming TEXT CHECK(effective_grooming IN ('groomed', 'ungroomed', 'powder', 'moguls')),
        last_updated_epoch INTEGER NOT NULL
    );

    CREATE TABLE mountain_services (
        service_id TEXT PRIMARY KEY,
        node_id TEXT NOT NULL REFERENCES nodes(node_id),
        name TEXT NOT NULL,
        category TEXT NOT NULL CHECK(category IN ('quick_snack', 'cafeteria', 'sit_down', 'bar', 'warming_hut', 'patrol', 'restroom')),
        service_speed TEXT CHECK(service_speed IN ('grab_and_go', 'counter_service', 'table_service', NULL)),
        open_time_local TEXT NOT NULL,
        close_time_local TEXT NOT NULL,
        requires_reservation INTEGER NOT NULL DEFAULT 0,
        price_tier TEXT CHECK(price_tier IN ('$', '$$', '$$$', '$$$$', NULL)),
        is_ski_in_only INTEGER NOT NULL DEFAULT 1,
        daily_status TEXT NOT NULL DEFAULT 'open' CHECK(daily_status IN ('open', 'closed_weather', 'closed_seasonal'))
    );

    CREATE INDEX idx_services_lookup ON mountain_services(category, service_speed, daily_status);
    CREATE INDEX idx_services_node ON mountain_services(node_id);
    """

    // MARK: - Big Sky Resort Sub-Graph Fixture (Mountain Village -> Andesite Summit)

    /// Models Mountain Village (`village_mountain_village`, 2286m) to Everett's 8800 (`everetts_8800`, 2682m):
    /// - Primary Path A: `lift_ramcharger` (Ramcharger 8, direct 4-minute chairlift = 240s).
    /// - Detour Path B: `lift_swift_current` (Swift Current 6 = 420s) to `lone_mountain_bowl` (2810.5m),
    ///   followed by `trail_andesite_connector` (intermediate groomed cruiser = 150s) down to `everetts_8800` (2682m).
    /// - Downhill return runs from `everetts_8800` to `village_mountain_village` (`trail_silver_knife` and `trail_mr_k`)
    ///   for testing dynamic grooming overrides and patrol closures.
    private static let bigSkyOverlaySeedSQL = """
    INSERT INTO nodes (node_id, name, lat, lon, elevation_m, node_type, poi_category) VALUES
        ('village_mountain_village', 'Mountain Village', 45.2840, -111.4010, 2286.0, 'village', 'cafeteria'),
        ('lone_mountain_bowl', 'Swift Current 6 Summit (Lone Mountain Bowl)', 45.2795, -111.4265, 2810.5, 'lift_top', 'patrol'),
        ('everetts_8800', 'Everett''s 8800 (Andesite Mountain Summit)', 45.2730, -111.4120, 2682.0, 'summit', 'restaurant_sitdown');

    INSERT INTO edges (
        edge_id, source_node, target_node, type, name,
        difficulty, grooming, length_m, vertical_diff_m, average_pitch_pct, base_cost_seconds
    ) VALUES
        -- Primary Path A: Fast direct 4-minute chairlift (240s) from Mountain Village to Andesite Summit
        ('lift_ramcharger', 'village_mountain_village', 'everetts_8800', 'lift', 'Ramcharger 8', 'lift', NULL, 1890.0, 396.0, 20.9, 240.0),

        -- Detour Path B: Swift Current 6 (420s) to Lone Mountain Bowl + intermediate connector trail (150s) to Andesite Summit
        ('lift_swift_current', 'village_mountain_village', 'lone_mountain_bowl', 'lift', 'Swift Current 6', 'lift', NULL, 2350.0, 524.5, 22.3, 420.0),
        ('trail_andesite_connector', 'lone_mountain_bowl', 'everetts_8800', 'piste', 'Pacifier / Andesite Connector', 'intermediate', 'groomed', 1420.0, -128.5, 9.0, 150.0),

        -- Downhill return pistes from Andesite Summit back to Mountain Village
        ('trail_silver_knife', 'everetts_8800', 'village_mountain_village', 'piste', 'Silver Knife', 'intermediate', 'groomed', 2100.0, -396.0, 18.9, 180.0),
        ('trail_mr_k', 'everetts_8800', 'village_mountain_village', 'piste', 'Mr. K', 'novice', 'groomed', 2450.0, -396.0, 16.2, 240.0);

    INSERT INTO mountain_services (
        service_id, node_id, name, category, service_speed,
        open_time_local, close_time_local, requires_reservation,
        price_tier, is_ski_in_only, daily_status
    ) VALUES
        ('srv_everetts_8800', 'everetts_8800', 'Everett''s 8800', 'sit_down', 'table_service', '11:00', '15:00', 1, '$$$', 1, 'open');
    """

    private var db: CirqueDatabase!
    private var overlayManager: DynamicOverlayManager!
    private var solver: CirqueGraphSolver!

    override func setUpWithError() throws {
        try super.setUpWithError()
        db = try CirqueDatabase(path: ":memory:", mode: .readWriteCreate)
        try db.executeRaw(Self.relationalGraphDDL)
        try db.executeRaw(Self.bigSkyOverlaySeedSQL)
        // Lock down SQLite database to strictly enforce immutable bundle invariant (PRAGMA query_only = ON)
        try db.enableQueryOnlyMode()

        overlayManager = DynamicOverlayManager(
            edgeAliases: [
                "Ramcharger 8": "lift_ramcharger",
                "Swift Current 6": "lift_swift_current",
                "Silver Knife": "trail_silver_knife",
                "Mr. K": "trail_mr_k",
                "Pacifier / Andesite Connector": "trail_andesite_connector"
            ]
        )
        solver = CirqueGraphSolver(database: db, overlayManager: overlayManager)
    }

    override func tearDownWithError() throws {
        solver = nil
        overlayManager = nil
        db?.close()
        db = nil
        try super.tearDownWithError()
    }

    // MARK: - 1. Baseline Direct Route via Ramcharger 8

    func testDirectRouteUnderNormalConditions() throws {
        let query = RouteQuery(
            startNodeId: "village_mountain_village",
            targetNodeId: "everetts_8800",
            maxDifficulty: .intermediate,
            preferGroomed: true,
            avoidMoguls: true
        )

        XCTAssertEqual(overlayManager.activeOverlayCount, 0, "No overlays should be active under baseline conditions.")

        let route = try XCTUnwrap(
            solver.solveShortestPath(query: query),
            "Solver must resolve a baseline route from village_mountain_village to everetts_8800."
        )

        XCTAssertEqual(route.count, 1, "Without overlays, solver must choose single-hop Path A via Ramcharger 8.")
        XCTAssertEqual(route.map(\.edgeId), ["lift_ramcharger"])
        XCTAssertEqual(route.first?.name, "Ramcharger 8")
        XCTAssertEqual(route.first?.type, .lift)
        XCTAssertTrue(route.first?.instructionAudio.contains("Ramcharger 8") == true)
    }

    // MARK: - 2. Wind-Hold Detour via Swift Current 6 (< 5.0 ms Latency Budget)

    func testWindHoldDetour() throws {
        let query = RouteQuery(
            startNodeId: "village_mountain_village",
            targetNodeId: "everetts_8800",
            maxDifficulty: .intermediate,
            preferGroomed: true,
            avoidMoguls: false
        )

        // Warm up SQLite prepared statement cache prior to timing the live wind-hold reroute
        let baselineRoute = try XCTUnwrap(solver.solveShortestPath(query: query))
        XCTAssertEqual(baselineRoute.map(\.edgeId), ["lift_ramcharger"])

        // Apply dynamic wind-hold overlay onto Ramcharger 8 and measure end-to-end reroute latency
        let startNanos = DispatchTime.now().uptimeNanoseconds
        overlayManager.setStatus(edgeId: "lift_ramcharger", status: .windHold, grooming: nil)
        let detourRoute = try XCTUnwrap(
            solver.solveShortestPath(query: query),
            "Solver must cleanly find Detour Path B when lift_ramcharger is on windHold."
        )
        let elapsedMs = Double(DispatchTime.now().uptimeNanoseconds - startNanos) / 1_000_000.0

        // Assert detour path uses Swift Current 6 -> Lone Mountain Bowl -> Andesite Connector -> Everett's 8800
        XCTAssertEqual(
            detourRoute.map(\.edgeId),
            ["lift_swift_current", "trail_andesite_connector"],
            "When Ramcharger 8 is on windHold, solver must detour via Swift Current 6 and the intermediate connector trail."
        )
        XCTAssertEqual(detourRoute[0].name, "Swift Current 6")
        XCTAssertEqual(detourRoute[0].type, .lift)
        XCTAssertEqual(detourRoute[1].name, "Pacifier / Andesite Connector")
        XCTAssertEqual(detourRoute[1].type, .piste)
        XCTAssertEqual(detourRoute[1].difficulty, .intermediate)

        // Assert hard exclusion on Ramcharger 8 directly via calculateCost
        let villageOutgoing = db.getOutgoingEdges(fromNodeId: "village_mountain_village")
        let ramchargerEdge = try XCTUnwrap(villageOutgoing.first { $0.edgeId == "lift_ramcharger" })
        XCTAssertNil(
            solver.calculateCost(edge: ramchargerEdge, query: query),
            "calculateCost must return nil immediately when edge status is .windHold."
        )

        // Assert single-shot wind-hold reroute latency is strictly under 5.0 milliseconds
        XCTAssertLessThan(
            elapsedMs,
            5.0,
            "Dynamic wind-hold reroute must complete in under 5.0ms (measured \(String(format: "%.4f", elapsedMs))ms)."
        )

        // Verify sustained multi-iteration re-evaluation also stays well below 5.0ms
        let iterations = 100
        let loopStartNanos = DispatchTime.now().uptimeNanoseconds
        for _ in 0..<iterations {
            let repeated = solver.solveShortestPath(query: query)
            XCTAssertEqual(repeated?.count, 2)
        }
        let averageMs = (Double(DispatchTime.now().uptimeNanoseconds - loopStartNanos) / Double(iterations)) / 1_000_000.0
        XCTAssertLessThan(
            averageMs,
            5.0,
            "Average dynamic detour solve latency must be under 5.0ms (measured \(String(format: "%.4f", averageMs))ms)."
        )

        // Architectural Invariant Check: Underlying SQLite database remains strictly read-only and unmutated
        XCTAssertTrue(db.isQueryOnlyEnabled(), "SQLite database must remain in strict query_only mode.")
        let activeOverlay = try XCTUnwrap(overlayManager.getOverlay(forEdgeId: "lift_ramcharger"))
        XCTAssertEqual(activeOverlay.status, .windHold)
        XCTAssertNil(activeOverlay.effectiveGrooming)
    }

    // MARK: - 3. Reopened Lift Restores Primary Direct Path

    func testReopenedLiftRestoresPrimaryPath() throws {
        let query = RouteQuery(
            startNodeId: "village_mountain_village",
            targetNodeId: "everetts_8800",
            maxDifficulty: .intermediate,
            preferGroomed: true,
            avoidMoguls: false
        )

        // 1. Place Ramcharger 8 on wind hold -> forces detour
        overlayManager.setStatus(edgeId: "lift_ramcharger", status: .windHold, grooming: nil)
        let detourSteps = try XCTUnwrap(solver.solveShortestPath(query: query))
        XCTAssertEqual(detourSteps.map(\.edgeId), ["lift_swift_current", "trail_andesite_connector"])

        // 2. Patrol clears wind hold and updates Ramcharger 8 status back to .open
        overlayManager.setStatus(edgeId: "lift_ramcharger", status: .open, grooming: nil)
        XCTAssertEqual(overlayManager.getOverlay(forEdgeId: "lift_ramcharger")?.status, .open)

        let restoredSteps = try XCTUnwrap(
            solver.solveShortestPath(query: query),
            "Solver must immediately restore direct Path A once lift_ramcharger returns to .open."
        )
        XCTAssertEqual(
            restoredSteps.map(\.edgeId),
            ["lift_ramcharger"],
            "Reopening Ramcharger 8 must immediately revert route from Swift Current 6 detour back to direct Ramcharger 8."
        )

        // 3. Verify mechanicalHold + resetAllOverlays() also cleanly restores primary route
        overlayManager.setStatus(edgeId: "lift_ramcharger", status: .mechanicalHold, grooming: nil)
        let mechHoldDetour = try XCTUnwrap(solver.solveShortestPath(query: query))
        XCTAssertEqual(mechHoldDetour.map(\.edgeId), ["lift_swift_current", "trail_andesite_connector"])

        overlayManager.resetAllOverlays()
        XCTAssertEqual(overlayManager.activeOverlayCount, 0)
        XCTAssertNil(overlayManager.getOverlay(forEdgeId: "lift_ramcharger"))

        let postResetSteps = try XCTUnwrap(solver.solveShortestPath(query: query))
        XCTAssertEqual(postResetSteps.map(\.edgeId), ["lift_ramcharger"])
    }

    // MARK: - 4. Liftie & Cloud Telemetry Delta JSON Payload Parsing

    func testDeltaJSONPayloadParsing() throws {
        // Part A: Mock Liftie live telemetry JSON payload (lifts.status + trails.status + grooming overrides)
        let mockLiftieJSON = """
        {
          "id": "big-sky",
          "name": "Big Sky Resort",
          "timestamp": {
            "lifts": 1731330000000
          },
          "lifts": {
            "status": {
              "Ramcharger 8": "hold",
              "Swift Current 6": "open"
            }
          },
          "trails": {
            "status": {
              "trail_silver_knife": {
                "status": "open",
                "effective_grooming": "moguls"
              },
              "trail_mr_k": {
                "status": "open",
                "effective_grooming": "groomed"
              }
            }
          }
        }
        """.data(using: .utf8)!

        let appliedLiftieCount = try overlayManager.applyOverlayDelta(jsonPayload: mockLiftieJSON)
        XCTAssertEqual(appliedLiftieCount, 4, "Expected 4 overlay records ingested from Liftie JSON payload.")
        XCTAssertEqual(overlayManager.activeOverlayCount, 4)

        let ramchargerOverlay = try XCTUnwrap(overlayManager.getOverlay(forEdgeId: "lift_ramcharger"))
        XCTAssertEqual(ramchargerOverlay.status, .windHold)
        XCTAssertNil(ramchargerOverlay.effectiveGrooming)
        XCTAssertEqual(ramchargerOverlay.lastUpdatedEpoch, 1_731_330_000, "Millisecond Liftie timestamp must normalize to Unix seconds.")

        let swiftCurrentOverlay = try XCTUnwrap(overlayManager.getOverlay(forEdgeId: "lift_swift_current"))
        XCTAssertEqual(swiftCurrentOverlay.status, .open)

        let silverKnifeOverlay = try XCTUnwrap(overlayManager.getOverlay(forEdgeId: "trail_silver_knife"))
        XCTAssertEqual(silverKnifeOverlay.status, .open)
        XCTAssertEqual(silverKnifeOverlay.effectiveGrooming, .moguls)

        // Verify ingested Liftie JSON drives live Wind-Hold detour in CirqueGraphSolver
        let uphillQuery = RouteQuery(
            startNodeId: "village_mountain_village",
            targetNodeId: "everetts_8800",
            maxDifficulty: .intermediate,
            preferGroomed: true,
            avoidMoguls: true
        )
        let detourRoute = try XCTUnwrap(solver.solveShortestPath(query: uphillQuery))
        XCTAssertEqual(detourRoute.map(\.edgeId), ["lift_swift_current", "trail_andesite_connector"])

        // Verify ingested grooming override ("moguls" on Silver Knife) reroutes mogul-avoiding downhill skier onto Mr. K
        let downhillQuery = RouteQuery(
            startNodeId: "everetts_8800",
            targetNodeId: "village_mountain_village",
            maxDifficulty: .intermediate,
            preferGroomed: true,
            avoidMoguls: true
        )
        let downhillRoute = try XCTUnwrap(solver.solveShortestPath(query: downhillQuery))
        XCTAssertEqual(
            downhillRoute.map(\.edgeId),
            ["trail_mr_k"],
            "Mogul override on Silver Knife (180s * 5.0 = 900s) must redirect skier onto groomed Mr. K (240s * 0.8 = 192s)."
        )

        // Part B: Cirque Cloud Run GET /v1/resorts/{id}/overlay delta envelope restoring Ramcharger 8 & closing Mr. K for patrol
        let cloudDeltaEnvelopeJSON = """
        {
          "resort_id": "us_mt_big_sky",
          "overlays": [
            {
              "edge_id": "lift_ramcharger",
              "status": "open",
              "effective_grooming": null,
              "last_updated_epoch": 1731330300
            },
            {
              "edge_id": "trail_mr_k",
              "status": "closed_patrol",
              "effective_grooming": "powder",
              "last_updated_epoch": 1731330300
            }
          ]
        }
        """.data(using: .utf8)!

        let appliedDeltaCount = try overlayManager.applyOverlayDelta(jsonPayload: cloudDeltaEnvelopeJSON)
        XCTAssertEqual(appliedDeltaCount, 2)
        XCTAssertEqual(overlayManager.getOverlay(forEdgeId: "lift_ramcharger")?.status, .open)
        XCTAssertEqual(overlayManager.getOverlay(forEdgeId: "lift_ramcharger")?.lastUpdatedEpoch, 1_731_330_300)
        XCTAssertEqual(overlayManager.getOverlay(forEdgeId: "trail_mr_k")?.status, .closedPatrol)
        XCTAssertEqual(overlayManager.getOverlay(forEdgeId: "trail_mr_k")?.effectiveGrooming, .powder)

        // Uphill route now immediately uses reopened Ramcharger 8
        let restoredUphill = try XCTUnwrap(solver.solveShortestPath(query: uphillQuery))
        XCTAssertEqual(restoredUphill.map(\.edgeId), ["lift_ramcharger"])

        // Downhill route now excludes closedPatrol Mr. K and falls back to open Silver Knife
        let patrolReroutedDownhill = try XCTUnwrap(solver.solveShortestPath(query: downhillQuery))
        XCTAssertEqual(patrolReroutedDownhill.map(\.edgeId), ["trail_silver_knife"])
    }

    // MARK: - 5. Hard Exclusions & Soft Grooming Multiplier Precision

    func testHardExclusionStatusesAndSoftGroomingOverrides() throws {
        let summitOutgoing = db.getOutgoingEdges(fromNodeId: "everetts_8800")
        let silverKnife = try XCTUnwrap(summitOutgoing.first { $0.edgeId == "trail_silver_knife" })

        let query = RouteQuery(
            startNodeId: "everetts_8800",
            targetNodeId: "village_mountain_village",
            maxDifficulty: .intermediate,
            preferGroomed: true,
            avoidMoguls: true
        )

        // 1. Base groomed cost (180s * 0.8 = 144.0s)
        let baseGroomedCost = try XCTUnwrap(solver.calculateCost(edge: silverKnife, query: query))
        XCTAssertEqual(baseGroomedCost, 180.0 * 0.8, accuracy: 0.001)

        // 2. Soft override: .ungroomed -> replaces base .groomed with 2.5x penalty (180s * 2.5 = 450.0s)
        overlayManager.setStatus(edgeId: "trail_silver_knife", status: .open, grooming: .ungroomed)
        let ungroomedCost = try XCTUnwrap(solver.calculateCost(edge: silverKnife, query: query))
        XCTAssertEqual(ungroomedCost, 180.0 * 2.5, accuracy: 0.001)

        // 3. Soft override: .powder -> 2.5x ungroomed penalty when preferGroomed is true (180s * 2.5 = 450.0s)
        overlayManager.setStatus(edgeId: "trail_silver_knife", status: .open, grooming: .powder)
        let powderCost = try XCTUnwrap(solver.calculateCost(edge: silverKnife, query: query))
        XCTAssertEqual(powderCost, 180.0 * 2.5, accuracy: 0.001)

        // 4. Soft override: .moguls -> 5.0x mogul avoidance penalty when avoidMoguls is true (180s * 5.0 = 900.0s)
        overlayManager.setStatus(edgeId: "trail_silver_knife", status: .open, grooming: .moguls)
        let mogulsCost = try XCTUnwrap(solver.calculateCost(edge: silverKnife, query: query))
        XCTAssertEqual(mogulsCost, 180.0 * 5.0, accuracy: 0.001)

        // 5. Hard exclusions: .closedPatrol, .windHold, .mechanicalHold must all return nil
        for blockedStatus: EdgeStatus in [.closedPatrol, .windHold, .mechanicalHold] {
            overlayManager.setStatus(edgeId: "trail_silver_knife", status: blockedStatus, grooming: .groomed)
            XCTAssertNil(
                solver.calculateCost(edge: silverKnife, query: query),
                "Edge with status \(blockedStatus.rawValue) must return nil from calculateCost."
            )
        }
    }

    // MARK: - 6. Concurrent Multi-Threaded Overlay Reads & Writes

    func testConcurrentThreadSafeOverlayAccess() throws {
        let manager = DynamicOverlayManager()
        let statuses = EdgeStatus.allCases
        let groomings: [GroomingOverride?] = [nil, .groomed, .ungroomed, .powder, .moguls]

        DispatchQueue.concurrentPerform(iterations: 200) { index in
            let edgeId = "edge_concurrent_\(index % 10)"
            let status = statuses[index % statuses.count]
            let grooming = groomings[index % groomings.count]
            manager.setStatus(edgeId: edgeId, status: status, grooming: grooming)
            _ = manager.getOverlay(forEdgeId: edgeId)
            _ = manager.activeOverlayCount
        }

        XCTAssertEqual(manager.activeOverlayCount, 10)
        manager.resetAllOverlays()
        XCTAssertEqual(manager.activeOverlayCount, 0)
    }
}

#if !canImport(ObjectiveC)
/// Bridges Apple XCTest's optional `FloatingPoint` accuracy assertion overload on Linux `swift-corelibs-xctest`.
func XCTAssertEqual<T: FloatingPoint>(
    _ expression1: @autoclosure () throws -> T?,
    _ expression2: @autoclosure () throws -> T?,
    accuracy: T,
    _ message: @autoclosure () -> String = "",
    file: StaticString = #filePath,
    line: UInt = #line
) {
    do {
        let lhs = try expression1()
        let rhs = try expression2()
        switch (lhs, rhs) {
        case (nil, nil):
            return
        case let (l?, r?):
            XCTAssertEqual(l, r, accuracy: accuracy, message(), file: file, line: line)
        default:
            XCTFail("XCTAssertEqual failed: (\(String(describing: lhs))) is not equal to (\(String(describing: rhs))) - \(message())", file: file, line: line)
        }
    } catch {
        XCTFail("XCTAssertEqual threw unexpected error: \(error) - \(message())", file: file, line: line)
    }
}
#endif
