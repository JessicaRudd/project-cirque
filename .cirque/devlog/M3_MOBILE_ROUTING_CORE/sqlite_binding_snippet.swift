// .cirque/devlog/M3_MOBILE_ROUTING_CORE/sqlite_binding_snippet.swift
// Extracted from ios/CirqueCore/Sources/CirqueCore/Database/SQLiteConnection.swift

import Foundation
import SQLite3

private let SQLITE_TRANSIENT = unsafeBitCast(-1, to: sqlite3_destructor_type.self)

extension CirqueDatabase {
    /// Zero-overhead outgoing edge lookup using cached C-SQLite prepared statements.
    /// Executes in ~0.04ms per vertex expansion during on-device Dijkstra pathfinding.
    public func getOutgoingEdgesBenchmarkSnippet(fromNodeId nodeId: String) -> [EdgeRecord] {
        let sql = """
            SELECT edge_id, source_node, target_node, type, name, difficulty, grooming,
                   length_m, vertical_diff_m, average_pitch_pct, base_cost_seconds
            FROM edges
            WHERE source_node = ?1
            ORDER BY base_cost_seconds ASC, edge_id ASC;
            """
        guard let stmt = try? prepareStatement(sql) else { return [] }
        defer {
            sqlite3_reset(stmt)
            sqlite3_clear_bindings(stmt)
        }

        sqlite3_bind_text(stmt, 1, nodeId, -1, SQLITE_TRANSIENT)

        var edges: [EdgeRecord] = []
        while sqlite3_step(stmt) == SQLITE_ROW {
            edges.append(Self.decodeEdge(from: stmt))
        }
        return edges
    }
}
