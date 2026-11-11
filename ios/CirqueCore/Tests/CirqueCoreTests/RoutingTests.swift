import XCTest
import Foundation
@testable import CirqueCore

final class RoutingTests: XCTestCase {

    // MARK: - Section 2.3 Relational Graph DDL

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

    // MARK: - Representative Big Sky Resort Sub-Graph Fixture

    private static let bigSkySubgraphSeedSQL = """
    INSERT INTO nodes (node_id, name, lat, lon, elevation_m, node_type, poi_category) VALUES
        ('village_base', 'Mountain Village', 45.2840, -111.4010, 2286.0, 'village', 'cafeteria'),
        ('swift_current_top', 'Swift Current 6 Summit', 45.2795, -111.4265, 2810.5, 'lift_top', 'patrol'),
        ('andesite_base', 'Ramcharger 8 Base', 45.2815, -111.4060, 2390.0, 'lift_base', NULL),
        ('everetts_8800', 'Everett''s 8800 (Andesite Mountain Summit)', 45.2730, -111.4120, 2682.0, 'poi', 'restaurant_sitdown'),
        ('lone_peak_summit', 'Lone Peak Summit', 45.2785, -111.4510, 3403.0, 'summit', 'patrol');

    INSERT INTO edges (
        edge_id, source_node, target_node, type, name,
        difficulty, grooming, length_m, vertical_diff_m, average_pitch_pct, base_cost_seconds
    ) VALUES
        -- Aerial Lifts (neutral difficulty = 'lift')
        ('lift_swift_current', 'village_base', 'swift_current_top', 'lift', 'Swift Current 6', 'lift', NULL, 2350.0, 524.5, 22.3, 420.0),
        ('lift_ramcharger', 'andesite_base', 'everetts_8800', 'lift', 'Ramcharger 8', 'lift', NULL, 1890.0, 292.0, 15.4, 340.0),
        ('lift_lone_peak_tram', 'swift_current_top', 'lone_peak_summit', 'lift', 'Lone Peak Tram', 'lift', NULL, 1420.0, 592.5, 41.7, 240.0),

        -- Downhill Ski Trails (pistes)
        ('trail_mr_k', 'everetts_8800', 'village_base', 'piste', 'Mr. K', 'novice', 'groomed', 2450.0, -396.0, 16.2, 240.0),
        ('trail_africa', 'swift_current_top', 'andesite_base', 'piste', 'Africa', 'intermediate', 'groomed', 1850.0, -420.5, 22.7, 150.0),
        ('trail_gullies', 'swift_current_top', 'andesite_base', 'piste', 'The Gullies', 'advanced', 'mogul', 1120.0, -420.5, 37.5, 95.0),
        ('trail_big_couloir', 'lone_peak_summit', 'swift_current_top', 'piste', 'Big Couloir', 'expert', 'backcountry', 1050.0, -592.5, 50.0, 160.0);

    INSERT INTO mountain_services (
        service_id, node_id, name, category, service_speed,
        open_time_local, close_time_local, requires_reservation,
        price_tier, is_ski_in_only, daily_status
    ) VALUES
        ('srv_everetts_8800', 'everetts_8800', 'Everett''s 8800', 'sit_down', 'table_service', '11:00', '15:00', 1, '$$$', 1, 'open');
    """

    private var db: CirqueDatabase!
    private var solver: CirqueGraphSolver!

    override func setUpWithError() throws {
        try super.setUpWithError()
        db = try CirqueDatabase(path: ":memory:", mode: .readWriteCreate)
        try db.executeRaw(Self.relationalGraphDDL)
        try db.executeRaw(Self.bigSkySubgraphSeedSQL)
        try db.enableQueryOnlyMode()
        solver = CirqueGraphSolver(database: db)
    }

    override func tearDownWithError() throws {
        solver = nil
        db?.close()
        db = nil
        try super.tearDownWithError()
    }

    // MARK: - 1. Swift Current to Everett's 8800 (Novice/Intermediate Only)

    func testSwiftCurrentToEveretts() throws {
        let query = RouteQuery(
            startNodeId: "village_base",
            targetNodeId: "everetts_8800",
            maxDifficulty: .intermediate,
            preferGroomed: true,
            avoidMoguls: false
        )

        let steps = try XCTUnwrap(
            solver.solveShortestPath(query: query),
            "Solver must resolve a valid route from village_base to everetts_8800 for an intermediate skier."
        )

        XCTAssertEqual(steps.count, 3, "Expected 3 steps: Swift Current 6 -> Africa -> Ramcharger 8.")
        XCTAssertEqual(steps.map(\.edgeId), ["lift_swift_current", "trail_africa", "lift_ramcharger"])

        // Assert: Route resolves 100% through Novice and Intermediate trails (plus neutral lifts)
        let pisteSteps = steps.filter { $0.type == .piste }
        XCTAssertFalse(pisteSteps.isEmpty, "Route must include at least one downhill piste segment.")
        for step in pisteSteps {
            XCTAssertTrue(
                step.difficulty == .novice || step.difficulty == .intermediate,
                "Expected only novice or intermediate pistes, but encountered \(step.difficulty.rawValue) on \(step.name)."
            )
        }

        // Assert: 0 Black (advanced) or Expert/Freeride runs are included in output steps
        let blackOrExpertSteps = steps.filter {
            $0.difficulty == .advanced || $0.difficulty == .expert || $0.difficulty == .freeride
        }
        XCTAssertEqual(
            blackOrExpertSteps.count,
            0,
            "0 Black or Expert runs may be included when maxDifficulty is .intermediate."
        )

        // Verify natural audio instructions are generated for every step
        for step in steps {
            XCTAssertFalse(step.instructionAudio.isEmpty, "Every RouteStep must include a natural audio instruction.")
        }
        XCTAssertTrue(steps[0].instructionAudio.contains("Swift Current 6"))
        XCTAssertTrue(steps[1].instructionAudio.contains("Africa"))
        XCTAssertTrue(steps[2].instructionAudio.contains("Ramcharger 8"))
    }

    // MARK: - 2. Hard Difficulty Ceiling Constraint (Lone Peak Summit Trap Prevention)

    func testDifficultyCeilingHardConstraint() throws {
        // Skier is at the top of Lone Peak wanting to descend to Mountain Village Base,
        // but their skill ceiling is set to .intermediate.
        // Only Big Couloir (.expert, 50-degree pitch) descends from lone_peak_summit.
        let unsafeQuery = RouteQuery(
            startNodeId: "lone_peak_summit",
            targetNodeId: "village_base",
            maxDifficulty: .intermediate,
            preferGroomed: true,
            avoidMoguls: true
        )

        let route = solver.solveShortestPath(query: unsafeQuery)
        XCTAssertNil(
            route,
            "Solver MUST return nil rather than routing an intermediate skier onto expert terrain (trail_big_couloir)."
        )

        // Verify calculateCost directly returns nil for trail_big_couloir under intermediate ceiling
        let summitEdges = db.getOutgoingEdges(fromNodeId: "lone_peak_summit")
        let bigCouloir = try XCTUnwrap(summitEdges.first { $0.edgeId == "trail_big_couloir" })
        XCTAssertNil(
            solver.calculateCost(edge: bigCouloir, query: unsafeQuery),
            "calculateCost must return nil when edge difficulty (.expert) exceeds query.maxDifficulty (.intermediate)."
        )

        // Positive control: An expert skier from lone_peak_summit CAN descend via Big Couloir
        let expertQuery = RouteQuery(
            startNodeId: "lone_peak_summit",
            targetNodeId: "village_base",
            maxDifficulty: .expert,
            preferGroomed: false,
            avoidMoguls: false
        )
        let expertRoute = try XCTUnwrap(
            solver.solveShortestPath(query: expertQuery),
            "An expert skier must be able to descend from lone_peak_summit to village_base."
        )
        XCTAssertEqual(expertRoute.first?.edgeId, "trail_big_couloir")
        XCTAssertEqual(expertRoute.last?.edgeId, "trail_mr_k")
    }

    // MARK: - 3. Soft Preference Multipliers: Mogul Avoidance Reroute

    func testMogulAvoidanceReroute() throws {
        // 1. Without mogul avoidance, an advanced skier descending from swift_current_top to andesite_base
        // takes the shorter mogul gully (trail_gullies: 95s base cost) over trail_africa (150s base cost).
        let directMogulQuery = RouteQuery(
            startNodeId: "swift_current_top",
            targetNodeId: "andesite_base",
            maxDifficulty: .advanced,
            preferGroomed: false,
            avoidMoguls: false
        )
        let directSteps = try XCTUnwrap(solver.solveShortestPath(query: directMogulQuery))
        XCTAssertEqual(directSteps.map(\.edgeId), ["trail_gullies"])

        // 2. With avoidMoguls = true, trail_gullies incurs a 5.0x penalty (95s * 5.0 = 475s),
        // causing the solver to reroute onto the longer groomed cruiser trail_africa (150s).
        let avoidMogulsQuery = RouteQuery(
            startNodeId: "swift_current_top",
            targetNodeId: "andesite_base",
            maxDifficulty: .advanced,
            preferGroomed: false,
            avoidMoguls: true
        )
        let reroutedSteps = try XCTUnwrap(solver.solveShortestPath(query: avoidMogulsQuery))
        XCTAssertEqual(
            reroutedSteps.map(\.edgeId),
            ["trail_africa"],
            "When avoidMoguls = true, solver must choose groomed cruiser trail_africa over shorter mogul gully trail_gullies."
        )

        // Verify exact multiplier math on both edges
        let outgoing = db.getOutgoingEdges(fromNodeId: "swift_current_top")
        let africaEdge = try XCTUnwrap(outgoing.first { $0.edgeId == "trail_africa" })
        let gulliesEdge = try XCTUnwrap(outgoing.first { $0.edgeId == "trail_gullies" })

        let groomedAndMogulAvoidQuery = RouteQuery(
            startNodeId: "swift_current_top",
            targetNodeId: "andesite_base",
            maxDifficulty: .advanced,
            preferGroomed: true,
            avoidMoguls: true
        )
        let africaWeightedCost = try XCTUnwrap(solver.calculateCost(edge: africaEdge, query: groomedAndMogulAvoidQuery))
        let gulliesWeightedCost = try XCTUnwrap(solver.calculateCost(edge: gulliesEdge, query: groomedAndMogulAvoidQuery))

        XCTAssertEqual(africaWeightedCost, 150.0 * 0.8, accuracy: 0.001, "Groomed piste must receive 0.8x bonus.")
        XCTAssertEqual(gulliesWeightedCost, 95.0 * 5.0, accuracy: 0.001, "Mogul piste must receive 5.0x penalty.")
    }

    // MARK: - 4. Solver Execution Performance (< 10.0 ms Budget)

    func testSolverExecutionPerformance() throws {
        // Augment the in-memory graph with an additional 300 nodes & 600 edges to simulate full-mountain fan-out
        let perfDb = try CirqueDatabase(path: ":memory:", mode: .readWriteCreate)
        defer { perfDb.close() }

        try perfDb.executeRaw(Self.relationalGraphDDL)
        try perfDb.executeRaw(Self.bigSkySubgraphSeedSQL)

        var bulkSQL = "BEGIN TRANSACTION;\n"
        for i in 0..<300 {
            let nodeId = String(format: "jct_perf_%03d", i)
            let prevNodeId = (i == 0) ? "swift_current_top" : String(format: "jct_perf_%03d", i - 1)
            let groomEdgeId = String(format: "edge_groom_%03d", i)
            let mogulEdgeId = String(format: "edge_mogul_%03d", i)

            bulkSQL += """
            INSERT INTO nodes (node_id, name, lat, lon, elevation_m, node_type, poi_category)
            VALUES ('\(nodeId)', 'Performance Junction \(i)', 45.2750, -111.4150, 2600.0, 'trail_junction', NULL);
            INSERT INTO edges (edge_id, source_node, target_node, type, name, difficulty, grooming, length_m, vertical_diff_m, average_pitch_pct, base_cost_seconds)
            VALUES ('\(groomEdgeId)', '\(prevNodeId)', '\(nodeId)', 'piste', 'Cruiser \(i)', 'intermediate', 'groomed', 320.0, -45.0, 14.0, 42.0);
            INSERT INTO edges (edge_id, source_node, target_node, type, name, difficulty, grooming, length_m, vertical_diff_m, average_pitch_pct, base_cost_seconds)
            VALUES ('\(mogulEdgeId)', '\(prevNodeId)', '\(nodeId)', 'piste', 'Bumps \(i)', 'advanced', 'mogul', 260.0, -45.0, 28.0, 35.0);
            """
        }
        bulkSQL += "COMMIT;"
        try perfDb.executeRaw(bulkSQL)
        try perfDb.enableQueryOnlyMode()

        let perfSolver = CirqueGraphSolver(database: perfDb)
        let query = RouteQuery(
            startNodeId: "village_base",
            targetNodeId: "everetts_8800",
            maxDifficulty: .intermediate,
            preferGroomed: true,
            avoidMoguls: true
        )

        // Warm up statement cache
        let warmupRoute = perfSolver.solveShortestPath(query: query)
        XCTAssertNotNil(warmupRoute)
        XCTAssertEqual(warmupRoute?.count, 3)

        let iterations = 100
        let startNanos = DispatchTime.now().uptimeNanoseconds
        for _ in 0..<iterations {
            let result = perfSolver.solveShortestPath(query: query)
            XCTAssertNotNil(result)
        }
        let elapsedNanos = DispatchTime.now().uptimeNanoseconds - startNanos
        let averageMs = (Double(elapsedNanos) / Double(iterations)) / 1_000_000.0

        XCTAssertLessThan(
            averageMs,
            10.0,
            "Multi-criteria Dijkstra solver must execute in under 10.0ms (measured \(String(format: "%.4f", averageMs))ms)."
        )
    }
}
