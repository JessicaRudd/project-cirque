import XCTest
import Foundation
@testable import CirqueCore

final class SQLiteConnectionTests: XCTestCase {

    private var tempDatabaseURL: URL!

    override func setUpWithError() throws {
        try super.setUpWithError()
        let tempDir = FileManager.default.temporaryDirectory
        tempDatabaseURL = tempDir.appendingPathComponent("cirque_test_\(UUID().uuidString).sqlite")
    }

    override func tearDownWithError() throws {
        if let url = tempDatabaseURL {
            try? FileManager.default.removeItem(at: url)
            try? FileManager.default.removeItem(atPath: url.path + "-wal")
            try? FileManager.default.removeItem(atPath: url.path + "-shm")
        }
        try super.tearDownWithError()
    }

    private func createSeededDatabaseFile(seedSQL: String) throws -> String {
        let path = tempDatabaseURL.path
        let writer = try CirqueDatabase(path: path, mode: .readWriteCreate)
        try writer.executeRaw("PRAGMA journal_mode = WAL;")
        try writer.executeRaw(TestGraphSchema.relationalGraphDDL)
        if !seedSQL.isEmpty {
            try writer.executeRaw(seedSQL)
        }
        writer.close()
        return path
    }

    func testDatabaseInitialization() throws {
        let seedSQL = """
        INSERT INTO nodes (node_id, name, lat, lon, elevation_m, node_type, poi_category) VALUES
            ('node_village_base', 'Mountain Village Base', 45.2840, -111.4010, 2286.0, 'village', 'cafeteria'),
            ('node_swift_top', 'Swift Current 6 Summit', 45.2795, -111.4265, 2810.5, 'lift_top', NULL);
        """
        let path = try createSeededDatabaseFile(seedSQL: seedSQL)

        let db = try CirqueDatabase(path: path, mode: .readOnly)
        defer { db.close() }

        XCTAssertFalse(db.isClosed, "Database should be open after initialization.")
        XCTAssertEqual(db.currentJournalMode(), "wal", "Database must operate in WAL journal mode.")
        XCTAssertTrue(db.isQueryOnlyEnabled(), "Read-only connection must enforce PRAGMA query_only = ON.")

        let baseNode = db.getNode(byId: "node_village_base")
        XCTAssertNotNil(baseNode)
        XCTAssertEqual(baseNode?.name, "Mountain Village Base")
        XCTAssertEqual(baseNode?.elevationM, 2286.0, accuracy: 0.01)
        XCTAssertEqual(baseNode?.nodeType, "village")
        XCTAssertEqual(baseNode?.poiCategory, "cafeteria")

        XCTAssertThrowsError(
            try db.executeRaw("DELETE FROM nodes;"),
            "Write operations must be rejected when opened with SQLITE_OPEN_READONLY and PRAGMA query_only = ON."
        )
    }

    func testOutgoingEdgesQueryPerformance() throws {
        let db = try CirqueDatabase(path: ":memory:", mode: .readWriteCreate)
        defer { db.close() }

        try db.executeRaw(TestGraphSchema.relationalGraphDDL)

        // Insert hub node and 500 target nodes + 500 directed edges
        var sqlBuilder = "BEGIN TRANSACTION;\n"
        sqlBuilder += """
        INSERT INTO nodes (node_id, name, lat, lon, elevation_m, node_type, poi_category)
        VALUES ('node_hub', 'Lone Peak Hub', 45.2795, -111.4265, 2810.0, 'trail_junction', NULL);
        """

        for i in 0..<500 {
            let targetId = String(format: "node_target_%04d", i)
            let edgeId = String(format: "edge_piste_%04d", i)
            let cost = Double(35 + (i % 120))
            let sourceId = (i < 50) ? "node_hub" : String(format: "node_target_%04d", i - 50)

            sqlBuilder += """
            INSERT INTO nodes (node_id, name, lat, lon, elevation_m, node_type, poi_category)
            VALUES ('\(targetId)', 'Junction \(i)', 45.2750, -111.4150, 2600.0, 'trail_junction', NULL);
            INSERT INTO edges (edge_id, source_node, target_node, type, name, difficulty, grooming, length_m, vertical_diff_m, average_pitch_pct, base_cost_seconds)
            VALUES ('\(edgeId)', '\(sourceId)', '\(targetId)', 'piste', 'Cruiser \(i)', 'intermediate', 'groomed', 450.0, -95.0, 21.1, \(cost));
            """
        }
        sqlBuilder += "COMMIT;"

        try db.executeRaw(sqlBuilder)
        try db.enableQueryOnlyMode()

        // Warm up the prepared statement cache
        let warmupEdges = db.getOutgoingEdges(fromNodeId: "node_hub")
        XCTAssertEqual(warmupEdges.count, 50, "Hub node should have 50 outgoing edges.")

        // Measure cached prepared statement execution time across 100 iterations
        let iterations = 100
        let startNanos = DispatchTime.now().uptimeNanoseconds
        for _ in 0..<iterations {
            let edges = db.getOutgoingEdges(fromNodeId: "node_hub")
            XCTAssertEqual(edges.count, 50)
        }
        let elapsedNanos = DispatchTime.now().uptimeNanoseconds - startNanos
        let averageMilliseconds = (Double(elapsedNanos) / Double(iterations)) / 1_000_000.0

        XCTAssertLessThan(
            averageMilliseconds,
            2.0,
            "getOutgoingEdges must execute in under 2.0ms (measured \(String(format: "%.4f", averageMilliseconds))ms)."
        )

        // Verify all 500 edges can also be fetched via getAllEdges
        let allEdges = db.getAllEdges()
        XCTAssertEqual(allEdges.count, 500)
    }

    // MARK: - 3. Mountain Services Temporal & Category Filtering

    func testMountainServicesFiltering() throws {
        let seedSQL = """
        INSERT INTO nodes (node_id, name, lat, lon, elevation_m, node_type, poi_category) VALUES
            ('node_jct_015', 'Shedhorn Base Junction', 45.2630, -111.4390, 2550.0, 'poi', 'cafeteria'),
            ('node_jct_001', 'Andesite Summit Terminal', 45.2730, -111.4120, 2682.0, 'lift_top', 'restaurant_sitdown'),
            ('node_jct_005', 'Meadow Junction', 45.2825, -111.4025, 2380.0, 'trail_junction', NULL),
            ('node_village_mountain_village', 'Mountain Village', 45.2840, -111.4010, 2286.0, 'village', 'cafeteria');

        INSERT INTO mountain_services (
            service_id, node_id, name, category, service_speed,
            open_time_local, close_time_local, requires_reservation,
            price_tier, is_ski_in_only, daily_status
        ) VALUES
            ('srv_shedhorn_grill', 'node_jct_015', 'Shedhorn Grill', 'quick_snack', 'grab_and_go', '11:00', '15:30', 0, '$$', 1, 'open'),
            ('srv_everetts_8800', 'node_jct_001', 'Everett''s 8800', 'sit_down', 'table_service', '11:00', '15:00', 1, '$$$', 1, 'open'),
            ('srv_early_coffee_hut', 'node_jct_005', 'Early Bird Coffee Hut', 'quick_snack', 'grab_and_go', '08:00', '11:30', 0, '$', 1, 'open'),
            ('srv_closed_yurt', 'node_jct_015', 'Backcountry Yurt', 'quick_snack', 'grab_and_go', '11:00', '16:00', 0, '$$', 1, 'closed_weather'),
            ('srv_vista_hall', 'node_village_mountain_village', 'Vista Hall', 'cafeteria', 'counter_service', '08:00', '17:00', 0, '$$', 0, 'open');
        """

        let path = try createSeededDatabaseFile(seedSQL: seedSQL)
        let db = try CirqueDatabase(path: path, mode: .readOnly)
        defer { db.close() }

        // 1. Filter for open grab-and-go quick snacks at 13:15
        let snackVenuesAt1315 = db.getServices(
            category: "quick_snack",
            speed: "grab_and_go",
            timeLocal: "13:15"
        )
        XCTAssertEqual(snackVenuesAt1315.count, 1, "Only Shedhorn Grill should be open for grab_and_go quick_snack at 13:15.")
        XCTAssertEqual(snackVenuesAt1315.first?.serviceId, "srv_shedhorn_grill")
        XCTAssertEqual(snackVenuesAt1315.first?.name, "Shedhorn Grill")
        XCTAssertEqual(snackVenuesAt1315.first?.nodeId, "node_jct_015")
        XCTAssertEqual(snackVenuesAt1315.first?.isSkiInOnly, true)
        XCTAssertEqual(snackVenuesAt1315.first?.requiresReservation, false)

        // 2. Filter for sit-down dining at 13:15 (Everett's 8800)
        let sitDownAt1315 = db.getServices(
            category: "sit_down",
            speed: "table_service",
            timeLocal: "13:15"
        )
        XCTAssertEqual(sitDownAt1315.count, 1)
        XCTAssertEqual(sitDownAt1315.first?.serviceId, "srv_everetts_8800")
        XCTAssertEqual(sitDownAt1315.first?.name, "Everett's 8800")
        XCTAssertEqual(sitDownAt1315.first?.nodeId, "node_jct_001")
        XCTAssertEqual(sitDownAt1315.first?.requiresReservation, true)
        XCTAssertEqual(sitDownAt1315.first?.priceTier, "$$$")

        // 3. Query all open venues at 13:15 regardless of category
        let allOpenAt1315 = db.getServices(category: nil, speed: nil, timeLocal: "13:15")
        let openIds = Set(allOpenAt1315.map(\.serviceId))
        XCTAssertEqual(openIds, ["srv_shedhorn_grill", "srv_everetts_8800", "srv_vista_hall"])
        XCTAssertFalse(openIds.contains("srv_early_coffee_hut"), "Early Bird Coffee Hut closes at 11:30.")
        XCTAssertFalse(openIds.contains("srv_closed_yurt"), "Weather-closed venues must be excluded.")
    }

    // MARK: - 4. Memory Lifecycle & Statement Finalization

    func testMemoryLifecycle() throws {
        let seedSQL = """
        INSERT INTO nodes (node_id, name, lat, lon, elevation_m, node_type, poi_category) VALUES
            ('node_a', 'Summit A', 45.2800, -111.4300, 3000.0, 'summit', NULL),
            ('node_b', 'Base B', 45.2840, -111.4010, 2286.0, 'village', NULL);
        INSERT INTO edges (edge_id, source_node, target_node, type, name, difficulty, grooming, length_m, vertical_diff_m, average_pitch_pct, base_cost_seconds) VALUES
            ('edge_ab', 'node_a', 'node_b', 'piste', 'Liberty Run', 'intermediate', 'groomed', 1200.0, -714.0, 24.5, 110.0);
        """
        let path = try createSeededDatabaseFile(seedSQL: seedSQL)

        weak var weakDbReference: CirqueDatabase?

        for _ in 0..<50 {
            do {
                let db = try CirqueDatabase(path: path, mode: .readOnly)
                weakDbReference = db

                _ = db.getNode(byId: "node_a")
                _ = db.getOutgoingEdges(fromNodeId: "node_a")
                _ = db.getAllEdges()
                _ = db.getServices(category: "quick_snack", speed: nil, timeLocal: "13:15")

                XCTAssertEqual(db.cachedStatementCount, 4, "Four distinct prepared statements should be cached.")
                db.close()
                XCTAssertEqual(db.cachedStatementCount, 0, "All prepared statements must be finalized on close().")
                XCTAssertTrue(db.isClosed)
            }
            XCTAssertNil(weakDbReference, "CirqueDatabase instance must deallocate cleanly with 0 reference cycles.")
        }
    }
}
