import XCTest
import Foundation

enum TestGraphSchema {
    static let relationalGraphDDL = """
    PRAGMA foreign_keys = ON;

    CREATE TABLE nodes (
        node_id TEXT PRIMARY KEY,
        name TEXT,
        lat REAL NOT NULL,
        lon REAL NOT NULL,
        elevation_m REAL NOT NULL,
        node_type TEXT CHECK(node_type IN ('trail_junction', 'lift_base', 'lift_top', 'poi', 'summit', 'village')),
        poi_category TEXT CHECK(poi_category IS NULL OR poi_category IN ('restaurant_sitdown', 'cafeteria', 'warming_hut', 'patrol', 'restroom'))
    );

    CREATE TABLE edges (
        edge_id TEXT PRIMARY KEY,
        source_node TEXT NOT NULL REFERENCES nodes(node_id),
        target_node TEXT NOT NULL REFERENCES nodes(node_id),
        type TEXT NOT NULL CHECK(type IN ('piste', 'lift')),
        name TEXT NOT NULL,
        difficulty TEXT CHECK(difficulty IN ('novice', 'intermediate', 'advanced', 'expert', 'freeride', 'lift')),
        grooming TEXT CHECK(grooming IS NULL OR grooming IN ('groomed', 'backcountry', 'mogul')),
        length_m REAL NOT NULL,
        vertical_diff_m REAL NOT NULL,
        average_pitch_pct REAL NOT NULL,
        base_cost_seconds REAL NOT NULL
    );

    CREATE INDEX idx_edges_source ON edges(source_node);
    CREATE INDEX idx_edges_target ON edges(target_node);
    CREATE INDEX idx_edges_type_diff ON edges(type, difficulty);
    CREATE INDEX idx_nodes_coords ON nodes(lat, lon);
    CREATE INDEX idx_nodes_poi ON nodes(poi_category);

    CREATE TABLE dynamic_status_overlay (
        edge_id TEXT PRIMARY KEY REFERENCES edges(edge_id),
        status TEXT NOT NULL CHECK(status IN ('open', 'closed_patrol', 'wind_hold', 'mechanical_hold')),
        effective_grooming TEXT CHECK(effective_grooming IS NULL OR effective_grooming IN ('groomed', 'ungroomed', 'powder', 'moguls')),
        last_updated_epoch INTEGER NOT NULL
    );

    CREATE TABLE mountain_services (
        service_id TEXT PRIMARY KEY,
        node_id TEXT NOT NULL REFERENCES nodes(node_id),
        name TEXT NOT NULL,
        category TEXT NOT NULL CHECK(category IN ('quick_snack', 'cafeteria', 'sit_down', 'bar', 'warming_hut', 'patrol', 'restroom')),
        service_speed TEXT CHECK(service_speed IS NULL OR service_speed IN ('grab_and_go', 'counter_service', 'table_service')),
        open_time_local TEXT NOT NULL,
        close_time_local TEXT NOT NULL,
        requires_reservation INTEGER NOT NULL DEFAULT 0,
        price_tier TEXT CHECK(price_tier IS NULL OR price_tier IN ('$', '$$', '$$$', '$$$$')),
        is_ski_in_only INTEGER NOT NULL DEFAULT 1,
        daily_status TEXT NOT NULL DEFAULT 'open' CHECK(daily_status IN ('open', 'closed_weather', 'closed_seasonal'))
    );

    CREATE INDEX idx_services_lookup ON mountain_services(category, service_speed, daily_status);
    CREATE INDEX idx_services_node ON mountain_services(node_id);
    """
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
            XCTFail(
                "XCTAssertEqual failed: (\(String(describing: lhs))) is not equal to (\(String(describing: rhs))) - \(message())",
                file: file,
                line: line
            )
        }
    } catch {
        XCTFail("XCTAssertEqual threw unexpected error: \(error) - \(message())", file: file, line: line)
    }
}
#endif
