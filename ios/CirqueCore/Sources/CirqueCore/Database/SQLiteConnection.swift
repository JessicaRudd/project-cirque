import Foundation
#if canImport(SQLite3)
import SQLite3
#else
import CSQLite
#endif

/// SQLITE_TRANSIENT tells SQLite to copy bound text buffers immediately before the Swift String pointer expires.
private let SQLITE_TRANSIENT = unsafeBitCast(-1, to: sqlite3_destructor_type.self)

/// Represents a discrete topological vertex in `nodes` (trail junction, lift terminal, summit, village, or snapped POI).
public struct NodeRecord: Equatable, Hashable, Codable, Sendable {
    public let nodeId: String
    public let name: String?
    public let lat: Double
    public let lon: Double
    public let elevationM: Double
    public let nodeType: String
    public let poiCategory: String?

    public init(
        nodeId: String,
        name: String?,
        lat: Double,
        lon: Double,
        elevationM: Double,
        nodeType: String,
        poiCategory: String?
    ) {
        self.nodeId = nodeId
        self.name = name
        self.lat = lat
        self.lon = lon
        self.elevationM = elevationM
        self.nodeType = nodeType
        self.poiCategory = poiCategory
    }
}

/// Represents a directed edge in `edges` (downhill ski piste, uphill aerial lift, or virtual transfer edge).
public struct EdgeRecord: Equatable, Hashable, Codable, Sendable {
    public let edgeId: String
    public let sourceNode: String
    public let targetNode: String
    public let type: String
    public let name: String
    public let difficulty: String?
    public let grooming: String?
    public let lengthM: Double
    public let verticalDiffM: Double
    public let averagePitchPct: Double
    public let baseCostSeconds: Double

    public var edgeType: EdgeType {
        EdgeType(rawValue: type) ?? .piste
    }

    public var skiDifficulty: SkiDifficulty {
        guard let difficulty else { return .novice }
        return SkiDifficulty(rawValue: difficulty) ?? .novice
    }

    public var groomingType: GroomingType? {
        guard let grooming else { return nil }
        return GroomingType(rawValue: grooming)
    }

    public init(
        edgeId: String,
        sourceNode: String,
        targetNode: String,
        type: String,
        name: String,
        difficulty: String?,
        grooming: String?,
        lengthM: Double,
        verticalDiffM: Double,
        averagePitchPct: Double,
        baseCostSeconds: Double
    ) {
        self.edgeId = edgeId
        self.sourceNode = sourceNode
        self.targetNode = targetNode
        self.type = type
        self.name = name
        self.difficulty = difficulty
        self.grooming = grooming
        self.lengthM = lengthM
        self.verticalDiffM = verticalDiffM
        self.averagePitchPct = averagePitchPct
        self.baseCostSeconds = baseCostSeconds
    }
}

/// Represents an on-mountain amenity or safety facility in `mountain_services`.
public struct MountainServiceRecord: Equatable, Hashable, Codable, Sendable {
    public let serviceId: String
    public let nodeId: String
    public let name: String
    public let category: String
    public let serviceSpeed: String?
    public let openTimeLocal: String
    public let closeTimeLocal: String
    public let requiresReservation: Bool
    public let priceTier: String?
    public let isSkiInOnly: Bool
    public let dailyStatus: String

    public init(
        serviceId: String,
        nodeId: String,
        name: String,
        category: String,
        serviceSpeed: String?,
        openTimeLocal: String,
        closeTimeLocal: String,
        requiresReservation: Bool,
        priceTier: String?,
        isSkiInOnly: Bool,
        dailyStatus: String
    ) {
        self.serviceId = serviceId
        self.nodeId = nodeId
        self.name = name
        self.category = category
        self.serviceSpeed = serviceSpeed
        self.openTimeLocal = openTimeLocal
        self.closeTimeLocal = closeTimeLocal
        self.requiresReservation = requiresReservation
        self.priceTier = priceTier
        self.isSkiInOnly = isSkiInOnly
        self.dailyStatus = dailyStatus
    }
}

// MARK: - Errors

public enum CirqueDatabaseError: Error, LocalizedError, Sendable {
    case openFailed(path: String, code: Int32, message: String)
    case prepareFailed(sql: String, code: Int32, message: String)
    case executionFailed(sql: String, code: Int32, message: String)
    case connectionClosed

    public var errorDescription: String? {
        switch self {
        case let .openFailed(path, code, message):
            return "Failed to open SQLite database at '\(path)' (code \(code)): \(message)"
        case let .prepareFailed(sql, code, message):
            return "Failed to prepare SQL statement '\(sql)' (code \(code)): \(message)"
        case let .executionFailed(sql, code, message):
            return "Failed to execute SQL '\(sql)' (code \(code)): \(message)"
        case .connectionClosed:
            return "Database connection is already closed."
        }
    }
}

// MARK: - Zero-Overhead C-SQLite3 Connection Wrapper

/// Thread-confined, zero-overhead C-SQLite3 wrapper with prepared statement caching.
/// Designed for sub-millisecond graph queries on iOS in Airplane Mode.
public final class CirqueDatabase {
    public enum OpenMode: Sendable {
        /// Production immutable mode: `SQLITE_OPEN_READONLY | SQLITE_OPEN_NOMUTEX` with `PRAGMA query_only = ON`.
        case readOnly
        /// Read-write mode used for seeding `:memory:` or temporary test fixtures before locking down with `query_only`.
        case readWriteCreate
    }

    private var db: OpaquePointer?
    private var preparedStatements: [String: OpaquePointer] = [:]
    public let databasePath: String
    public private(set) var isClosed: Bool = false

    // MARK: - SQL Query Constants

    private static let sqlGetNodeById = """
        SELECT node_id, name, lat, lon, elevation_m, node_type, poi_category
        FROM nodes
        WHERE node_id = ?1
        LIMIT 1;
        """

    private static let sqlGetAllNodes = """
        SELECT node_id, name, lat, lon, elevation_m, node_type, poi_category
        FROM nodes
        ORDER BY node_id ASC;
        """

    private static let sqlGetOutgoingEdges = """
        SELECT edge_id, source_node, target_node, type, name, difficulty, grooming,
               length_m, vertical_diff_m, average_pitch_pct, base_cost_seconds
        FROM edges
        WHERE source_node = ?1
        ORDER BY base_cost_seconds ASC, edge_id ASC;
        """

    private static let sqlGetAllEdges = """
        SELECT edge_id, source_node, target_node, type, name, difficulty, grooming,
               length_m, vertical_diff_m, average_pitch_pct, base_cost_seconds
        FROM edges
        ORDER BY edge_id ASC;
        """

    private static let sqlGetServicesFiltered = """
        SELECT service_id, node_id, name, category, service_speed,
               open_time_local, close_time_local, requires_reservation,
               price_tier, is_ski_in_only, daily_status
        FROM mountain_services
        WHERE daily_status = 'open'
          AND (?1 IS NULL OR category = ?1)
          AND (?2 IS NULL OR service_speed = ?2)
          AND (?3 IS NULL OR (?3 >= open_time_local AND ?3 <= close_time_local))
        ORDER BY service_id ASC;
        """

    // MARK: - Initialization & Lifecycle

    /// Opens a SQLite database connection.
    /// - Parameters:
    ///   - path: File path to `topology.sqlite` or `:memory:`.
    ///   - mode: `.readOnly` (default, uses `SQLITE_OPEN_READONLY | SQLITE_OPEN_NOMUTEX`) or `.readWriteCreate`.
    public init(path: String, mode: OpenMode = .readOnly) throws {
        self.databasePath = path
        var handle: OpaquePointer?

        let flags: Int32
        switch mode {
        case .readOnly:
            flags = SQLITE_OPEN_READONLY | SQLITE_OPEN_NOMUTEX
        case .readWriteCreate:
            flags = SQLITE_OPEN_READWRITE | SQLITE_OPEN_CREATE | SQLITE_OPEN_NOMUTEX
        }

        let rc = sqlite3_open_v2(path, &handle, flags, nil)
        guard rc == SQLITE_OK, let validHandle = handle else {
            let msg = handle.flatMap { String(cString: sqlite3_errmsg($0)) } ?? "Unknown error"
            if let handle {
                sqlite3_close_v2(handle)
            }
            throw CirqueDatabaseError.openFailed(path: path, code: rc, message: msg)
        }

        self.db = validHandle

        // Configure pragmas for high-speed offline edge runtime
        if mode == .readWriteCreate {
            try executeRaw("PRAGMA foreign_keys = ON;")
            try executeRaw("PRAGMA journal_mode = WAL;")
        } else {
            // Best-effort WAL pragma on read-only connection, plus strict query_only enforcement
            _ = try? executeRaw("PRAGMA journal_mode = WAL;")
            try executeRaw("PRAGMA query_only = ON;")
        }
    }

    deinit {
        close()
    }

    /// Explicitly finalizes all cached prepared statements and closes the underlying SQLite connection.
    public func close() {
        guard !isClosed else { return }
        for (_, stmt) in preparedStatements {
            sqlite3_finalize(stmt)
        }
        preparedStatements.removeAll()

        if let handle = db {
            sqlite3_close_v2(handle)
            db = nil
        }
        isClosed = true
    }

    /// Number of currently cached prepared statements (exposed for memory lifecycle verification).
    public var cachedStatementCount: Int {
        preparedStatements.count
    }

    // MARK: - Pragma & Schema Helpers

    /// Executes arbitrary DDL/DML statements (used when initializing `:memory:` or test fixtures before enabling `query_only`).
    public func executeRaw(_ sql: String) throws {
        guard let handle = db, !isClosed else {
            throw CirqueDatabaseError.connectionClosed
        }
        var errMsg: UnsafeMutablePointer<CChar>?
        let rc = sqlite3_exec(handle, sql, nil, nil, &errMsg)
        if rc != SQLITE_OK {
            let message = errMsg.map { String(cString: $0) } ?? String(cString: sqlite3_errmsg(handle))
            if let errMsg {
                sqlite3_free(errMsg)
            }
            throw CirqueDatabaseError.executionFailed(sql: sql, code: rc, message: message)
        }
    }

    /// Enables strict `PRAGMA query_only = ON;` after test fixture seeding.
    public func enableQueryOnlyMode() throws {
        try executeRaw("PRAGMA query_only = ON;")
    }

    /// Returns the active SQLite `journal_mode` (e.g., `"wal"`, `"memory"`, `"delete"`).
    public func currentJournalMode() -> String {
        guard let stmt = try? prepareStatement("PRAGMA journal_mode;") else {
            return "unknown"
        }
        defer {
            sqlite3_reset(stmt)
        }
        if sqlite3_step(stmt) == SQLITE_ROW, let cStr = sqlite3_column_text(stmt, 0) {
            return String(cString: cStr).lowercased()
        }
        return "unknown"
    }

    /// Returns true if `PRAGMA query_only` is currently `1`.
    public func isQueryOnlyEnabled() -> Bool {
        guard let stmt = try? prepareStatement("PRAGMA query_only;") else {
            return false
        }
        defer {
            sqlite3_reset(stmt)
        }
        if sqlite3_step(stmt) == SQLITE_ROW {
            return sqlite3_column_int(stmt, 0) == 1
        }
        return false
    }

    // MARK: - Prepared Statement Cache

    private func prepareStatement(_ sql: String) throws -> OpaquePointer {
        guard let handle = db, !isClosed else {
            throw CirqueDatabaseError.connectionClosed
        }

        if let cached = preparedStatements[sql] {
            sqlite3_reset(cached)
            sqlite3_clear_bindings(cached)
            return cached
        }

        var stmt: OpaquePointer?
        let rc = sqlite3_prepare_v2(handle, sql, -1, &stmt, nil)
        guard rc == SQLITE_OK, let validStmt = stmt else {
            let message = String(cString: sqlite3_errmsg(handle))
            throw CirqueDatabaseError.prepareFailed(sql: sql, code: rc, message: message)
        }

        preparedStatements[sql] = validStmt
        return validStmt
    }

    // MARK: - Core Graph & Service Queries

    /// Fetches a single topological node by its primary key `node_id`.
    public func getNode(byId id: String) -> NodeRecord? {
        guard let stmt = try? prepareStatement(Self.sqlGetNodeById) else {
            return nil
        }
        defer {
            sqlite3_reset(stmt)
            sqlite3_clear_bindings(stmt)
        }

        sqlite3_bind_text(stmt, 1, id, -1, SQLITE_TRANSIENT)

        guard sqlite3_step(stmt) == SQLITE_ROW else {
            return nil
        }

        return Self.decodeNode(from: stmt)
    }

    /// Fetches all topological nodes ordered by `node_id`.
    public func getAllNodes() -> [NodeRecord] {
        guard let stmt = try? prepareStatement(Self.sqlGetAllNodes) else {
            return []
        }
        defer {
            sqlite3_reset(stmt)
        }

        var results: [NodeRecord] = []
        while sqlite3_step(stmt) == SQLITE_ROW {
            results.append(Self.decodeNode(from: stmt))
        }
        return results
    }

    /// Fetches all outgoing directed edges originating from `nodeId`, ordered by ascending `base_cost_seconds`.
    public func getOutgoingEdges(fromNodeId nodeId: String) -> [EdgeRecord] {
        guard let stmt = try? prepareStatement(Self.sqlGetOutgoingEdges) else {
            return []
        }
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

    /// Fetches the complete edge list from `edges` for bulk in-memory adjacency graph construction.
    public func getAllEdges() -> [EdgeRecord] {
        guard let stmt = try? prepareStatement(Self.sqlGetAllEdges) else {
            return []
        }
        defer {
            sqlite3_reset(stmt)
        }

        var edges: [EdgeRecord] = []
        while sqlite3_step(stmt) == SQLITE_ROW {
            edges.append(Self.decodeEdge(from: stmt))
        }
        return edges
    }

    /// Queries open mountain services with optional category, service speed, and local time (`HH:MM`) filtering.
    /// - Parameters:
    ///   - category: Optional category filter (e.g. `"quick_snack"`, `"sit_down"`, `"patrol"`).
    ///   - speed: Optional service speed filter (e.g. `"grab_and_go"`, `"table_service"`).
    ///   - timeLocal: Optional 24-hour local time string `"HH:MM"` (e.g. `"13:15"`).
    /// - Returns: Matching `MountainServiceRecord` rows ordered by `service_id`.
    public func getServices(
        category: String? = nil,
        speed: String? = nil,
        timeLocal: String? = nil
    ) -> [MountainServiceRecord] {
        guard let stmt = try? prepareStatement(Self.sqlGetServicesFiltered) else {
            return []
        }
        defer {
            sqlite3_reset(stmt)
            sqlite3_clear_bindings(stmt)
        }

        Self.bindOptionalText(stmt, index: 1, value: category)
        Self.bindOptionalText(stmt, index: 2, value: speed)
        Self.bindOptionalText(stmt, index: 3, value: timeLocal)

        var services: [MountainServiceRecord] = []
        while sqlite3_step(stmt) == SQLITE_ROW {
            services.append(Self.decodeService(from: stmt))
        }
        return services
    }

    private static func bindOptionalText(_ stmt: OpaquePointer, index: Int32, value: String?) {
        if let value {
            sqlite3_bind_text(stmt, index, value, -1, SQLITE_TRANSIENT)
        } else {
            sqlite3_bind_null(stmt, index)
        }
    }

    // MARK: - Zero-Copy Column Decoders

    private static func columnString(_ stmt: OpaquePointer, _ index: Int32) -> String {
        guard let cStr = sqlite3_column_text(stmt, index) else {
            return ""
        }
        return String(cString: cStr)
    }

    private static func columnOptionalString(_ stmt: OpaquePointer, _ index: Int32) -> String? {
        guard sqlite3_column_type(stmt, index) != SQLITE_NULL,
              let cStr = sqlite3_column_text(stmt, index) else {
            return nil
        }
        return String(cString: cStr)
    }

    private static func decodeNode(from stmt: OpaquePointer) -> NodeRecord {
        NodeRecord(
            nodeId: columnString(stmt, 0),
            name: columnOptionalString(stmt, 1),
            lat: sqlite3_column_double(stmt, 2),
            lon: sqlite3_column_double(stmt, 3),
            elevationM: sqlite3_column_double(stmt, 4),
            nodeType: columnString(stmt, 5),
            poiCategory: columnOptionalString(stmt, 6)
        )
    }

    private static func decodeEdge(from stmt: OpaquePointer) -> EdgeRecord {
        EdgeRecord(
            edgeId: columnString(stmt, 0),
            sourceNode: columnString(stmt, 1),
            targetNode: columnString(stmt, 2),
            type: columnString(stmt, 3),
            name: columnString(stmt, 4),
            difficulty: columnOptionalString(stmt, 5),
            grooming: columnOptionalString(stmt, 6),
            lengthM: sqlite3_column_double(stmt, 7),
            verticalDiffM: sqlite3_column_double(stmt, 8),
            averagePitchPct: sqlite3_column_double(stmt, 9),
            baseCostSeconds: sqlite3_column_double(stmt, 10)
        )
    }

    private static func decodeService(from stmt: OpaquePointer) -> MountainServiceRecord {
        MountainServiceRecord(
            serviceId: columnString(stmt, 0),
            nodeId: columnString(stmt, 1),
            name: columnString(stmt, 2),
            category: columnString(stmt, 3),
            serviceSpeed: columnOptionalString(stmt, 4),
            openTimeLocal: columnString(stmt, 5),
            closeTimeLocal: columnString(stmt, 6),
            requiresReservation: sqlite3_column_int(stmt, 7) != 0,
            priceTier: columnOptionalString(stmt, 8),
            isSkiInOnly: sqlite3_column_int(stmt, 9) != 0,
            dailyStatus: columnString(stmt, 10)
        )
    }
}
