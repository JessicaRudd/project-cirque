import Foundation

// MARK: - Dynamic Overlay Domain Types (TECH_SPEC Section 2.3 & Section 4)

/// Operational status of a directed lift or piste edge in the dynamic overlay table.
public enum EdgeStatus: String, Codable, Sendable, CaseIterable, Hashable {
    case open = "open"
    case closedPatrol = "closedPatrol"
    case windHold = "windHold"
    case mechanicalHold = "mechanicalHold"

    /// Whether the edge can be traversed by skiers during pathfinding.
    /// `.closedPatrol`, `.windHold`, and `.mechanicalHold` trigger immediate hard exclusion (`nil` cost).
    public var isTraversable: Bool {
        self == .open
    }

    /// Canonical snake_case representation matching `TECH_SPEC.md` Section 2.3 `dynamic_status_overlay` DDL.
    public var ddlValue: String {
        switch self {
        case .open:
            return "open"
        case .closedPatrol:
            return "closed_patrol"
        case .windHold:
            return "wind_hold"
        case .mechanicalHold:
            return "mechanical_hold"
        }
    }

    /// Parses camelCase, snake_case (`TECH_SPEC.md` Section 2.3), or raw Liftie telemetry status tokens.
    public init?(wireValue: String) {
        let trimmed = wireValue.trimmingCharacters(in: .whitespacesAndNewlines)
        if let exact = Self(rawValue: trimmed) {
            self = exact
            return
        }

        switch trimmed.lowercased() {
        case "open":
            self = .open
        case "closedpatrol", "closed_patrol", "closed", "scheduled", "patrol_closed":
            self = .closedPatrol
        case "windhold", "wind_hold", "hold", "weather_hold":
            self = .windHold
        case "mechanicalhold", "mechanical_hold", "mechanical", "maintenance":
            self = .mechanicalHold
        default:
            return nil
        }
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        let rawString = try container.decode(String.self)
        guard let parsed = Self(wireValue: rawString) else {
            throw DecodingError.dataCorruptedError(
                in: container,
                debugDescription: "Invalid EdgeStatus value '\(rawString)'."
            )
        }
        self = parsed
    }

    public func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        try container.encode(rawValue)
    }
}

/// Real-time surface condition override applied atop immutable base `EdgeRecord.grooming` metadata.
public enum GroomingOverride: String, Codable, Sendable, CaseIterable, Hashable {
    case groomed = "groomed"
    case ungroomed = "ungroomed"
    case powder = "powder"
    case moguls = "moguls"

    /// Maps the dynamic grooming override into `GroomingType` for `CirqueGraphSolver` soft multiplier evaluation.
    public var groomingType: GroomingType {
        switch self {
        case .groomed:
            return .groomed
        case .ungroomed:
            return .ungroomed
        case .powder:
            return .powder
        case .moguls:
            return .moguls
        }
    }

    /// Parses canonical or alias surface grooming strings from telemetry feeds.
    public init?(wireValue: String) {
        let trimmed = wireValue.trimmingCharacters(in: .whitespacesAndNewlines)
        if let exact = Self(rawValue: trimmed) {
            self = exact
            return
        }

        switch trimmed.lowercased() {
        case "groomed", "corduroy", "machine_groomed":
            self = .groomed
        case "ungroomed", "backcountry", "variable":
            self = .ungroomed
        case "powder", "packed_powder", "fresh_snow":
            self = .powder
        case "moguls", "mogul", "bumps":
            self = .moguls
        default:
            return nil
        }
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        let rawString = try container.decode(String.self)
        guard let parsed = Self(wireValue: rawString) else {
            throw DecodingError.dataCorruptedError(
                in: container,
                debugDescription: "Invalid GroomingOverride value '\(rawString)'."
            )
        }
        self = parsed
    }

    public func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        try container.encode(rawValue)
    }
}

/// Ephemeral in-memory status record corresponding to `TECH_SPEC.md` Section 2.3 `dynamic_status_overlay`.
public struct DynamicStatusOverlay: Equatable, Hashable, Codable, Sendable {
    public let edgeId: String
    public let status: EdgeStatus
    public let effectiveGrooming: GroomingOverride?
    public let lastUpdatedEpoch: Int64

    public init(
        edgeId: String,
        status: EdgeStatus,
        effectiveGrooming: GroomingOverride? = nil,
        lastUpdatedEpoch: Int64 = Int64(Date().timeIntervalSince1970)
    ) {
        self.edgeId = edgeId
        self.status = status
        self.effectiveGrooming = effectiveGrooming
        self.lastUpdatedEpoch = lastUpdatedEpoch
    }

    private enum CodingKeys: String, CodingKey {
        case edgeId
        case edgeIdSnake = "edge_id"
        case status
        case effectiveGrooming
        case effectiveGroomingSnake = "effective_grooming"
        case grooming
        case lastUpdatedEpoch
        case lastUpdatedEpochSnake = "last_updated_epoch"
        case timestamp
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)

        if let camelId = try container.decodeIfPresent(String.self, forKey: .edgeId) {
            self.edgeId = camelId
        } else if let snakeId = try container.decodeIfPresent(String.self, forKey: .edgeIdSnake) {
            self.edgeId = snakeId
        } else {
            throw DecodingError.keyNotFound(
                CodingKeys.edgeId,
                DecodingError.Context(
                    codingPath: container.codingPath,
                    debugDescription: "Missing 'edgeId' or 'edge_id' in DynamicStatusOverlay."
                )
            )
        }

        self.status = try container.decode(EdgeStatus.self, forKey: .status)

        if let camelGrooming = try container.decodeIfPresent(GroomingOverride.self, forKey: .effectiveGrooming) {
            self.effectiveGrooming = camelGrooming
        } else if let snakeGrooming = try container.decodeIfPresent(GroomingOverride.self, forKey: .effectiveGroomingSnake) {
            self.effectiveGrooming = snakeGrooming
        } else if let shortGrooming = try container.decodeIfPresent(GroomingOverride.self, forKey: .grooming) {
            self.effectiveGrooming = shortGrooming
        } else {
            self.effectiveGrooming = nil
        }

        if let camelEpoch = try container.decodeIfPresent(Int64.self, forKey: .lastUpdatedEpoch) {
            self.lastUpdatedEpoch = Self.normalizeEpochSeconds(camelEpoch)
        } else if let snakeEpoch = try container.decodeIfPresent(Int64.self, forKey: .lastUpdatedEpochSnake) {
            self.lastUpdatedEpoch = Self.normalizeEpochSeconds(snakeEpoch)
        } else if let fallbackTs = try container.decodeIfPresent(Int64.self, forKey: .timestamp) {
            self.lastUpdatedEpoch = Self.normalizeEpochSeconds(fallbackTs)
        } else {
            self.lastUpdatedEpoch = Int64(Date().timeIntervalSince1970)
        }
    }

    public func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(edgeId, forKey: .edgeId)
        try container.encode(status, forKey: .status)
        try container.encodeIfPresent(effectiveGrooming, forKey: .effectiveGrooming)
        try container.encode(lastUpdatedEpoch, forKey: .lastUpdatedEpoch)
    }

    fileprivate static func normalizeEpochSeconds(_ rawTimestamp: Int64) -> Int64 {
        // Convert millisecond timestamps (e.g. Liftie JS Date.now() > 10^11) into Unix epoch seconds.
        if rawTimestamp > 100_000_000_000 {
            return rawTimestamp / 1_000
        }
        return rawTimestamp
    }
}

// MARK: - Overlay Ingestion Errors

public enum DynamicOverlayError: Error, LocalizedError, Sendable, Equatable {
    case emptyPayload
    case invalidJSON(String)
    case unsupportedPayloadFormat
    case emptyEdgeIdentifier
    case invalidEdgeStatus(edgeId: String, rawValue: String)
    case invalidGroomingOverride(edgeId: String, rawValue: String)

    public var errorDescription: String? {
        switch self {
        case .emptyPayload:
            return "Dynamic overlay JSON payload cannot be empty."
        case let .invalidJSON(reason):
            return "Failed to parse dynamic overlay JSON payload: \(reason)"
        case .unsupportedPayloadFormat:
            return "Unsupported telemetry JSON structure; expected overlay array, delta envelope, or Liftie status object."
        case .emptyEdgeIdentifier:
            return "Overlay record contains an empty edge identifier."
        case let .invalidEdgeStatus(edgeId, rawValue):
            return "Invalid edge status '\(rawValue)' for edge '\(edgeId)'."
        case let .invalidGroomingOverride(edgeId, rawValue):
            return "Invalid grooming override '\(rawValue)' for edge '\(edgeId)'."
        }
    }
}

// MARK: - Thread-Safe In-Memory Dynamic Status Overlay Manager

/// Manages ephemeral live lift/trail status and grooming overrides strictly in RAM.
///
/// Architectural Invariants:
/// - **Zero SQLite Mutation**: Never opens, writes to, or mutates immutable `topology.sqlite` bundles.
/// - **Thread-Safe O(1) Reads/Writes**: Synchronizes access to `[String: DynamicStatusOverlay]` with `NSLock`
///   so background telemetry refresh workers and interactive SiriKit Dijkstra queries never contend or race.
public final class DynamicOverlayManager: @unchecked Sendable {

    private let lock = NSLock()
    private var overlays: [String: DynamicStatusOverlay] = [:]

    /// Optional display-name-to-edgeId lookup table for resolving human-readable Liftie lift/trail names
    /// (e.g., `"Ramcharger 8" -> "lift_ramcharger"`).
    private var aliasToEdgeId: [String: String] = [:]

    public init(
        initialOverlays: [DynamicStatusOverlay] = [],
        edgeAliases: [String: String] = [:]
    ) {
        for (alias, edgeId) in edgeAliases {
            aliasToEdgeId[Self.normalizeAliasKey(alias)] = edgeId
        }
        for overlay in initialOverlays {
            overlays[overlay.edgeId] = overlay
        }
    }

    // MARK: - Core Ingestion & Query APIs

    /// Parses a JSON delta payload from Cirque telemetry workers or Liftie feeds and atomically updates the in-memory overlay cache.
    ///
    /// Supported JSON schemas:
    /// 1. Cirque Cloud API delta envelope: `{"resort_id": "...", "timestamp": 1731182400, "overlays": [...]}` (also `"deltas"` or `"edges"`).
    /// 2. Direct array of `DynamicStatusOverlay` objects: `[{"edge_id": "lift_ramcharger", "status": "wind_hold", ...}]`.
    /// 3. Liftie telemetry feed: `{"id": "big-sky", "timestamp": {"lifts": ...}, "lifts": {"status": {...}}, "trails": {"status": {...}}}`.
    ///
    /// - Parameter jsonPayload: UTF-8 encoded JSON `Data`.
    /// - Returns: Count of `DynamicStatusOverlay` records applied to the in-memory cache.
    @discardableResult
    public func applyOverlayDelta(jsonPayload: Data) throws -> Int {
        guard !jsonPayload.isEmpty else {
            throw DynamicOverlayError.emptyPayload
        }

        let jsonObject: Any
        do {
            jsonObject = try JSONSerialization.jsonObject(with: jsonPayload, options: [])
        } catch {
            throw DynamicOverlayError.invalidJSON(error.localizedDescription)
        }

        let currentAliases: [String: String] = lock.withLock { aliasToEdgeId }
        let fallbackEpoch = Int64(Date().timeIntervalSince1970)
        let parsedRecords = try Self.parsePayloadObject(
            jsonObject,
            aliases: currentAliases,
            defaultEpoch: fallbackEpoch
        )

        lock.withLock {
            for record in parsedRecords {
                overlays[record.edgeId] = record
            }
        }

        return parsedRecords.count
    }

    /// Programmatically sets or updates the live status and optional grooming override for a single edge.
    public func setStatus(
        edgeId: String,
        status: EdgeStatus,
        grooming: GroomingOverride? = nil
    ) {
        let record = DynamicStatusOverlay(
            edgeId: edgeId,
            status: status,
            effectiveGrooming: grooming,
            lastUpdatedEpoch: Int64(Date().timeIntervalSince1970)
        )
        lock.withLock {
            overlays[edgeId] = record
        }
    }

    /// Instant O(1) thread-safe dictionary lookup for a directed graph edge.
    public func getOverlay(forEdgeId edgeId: String) -> DynamicStatusOverlay? {
        lock.withLock {
            overlays[edgeId]
        }
    }

    /// Clears all active dynamic overrides, immediately restoring immutable base `topology.sqlite` defaults.
    public func resetAllOverlays() {
        lock.withLock {
            overlays.removeAll()
        }
    }

    // MARK: - Introspection & Alias Registration Helpers

    /// Number of edges currently carrying an active dynamic status overlay.
    public var activeOverlayCount: Int {
        lock.withLock {
            overlays.count
        }
    }

    /// Returns a point-in-time snapshot copy of the entire active overlay table.
    public func snapshotOverlays() -> [String: DynamicStatusOverlay] {
        lock.withLock {
            overlays
        }
    }

    /// Registers human-readable lift/trail names (such as from `CirqueDatabase.getAllEdges()`) to canonical `edgeId`s
    /// so raw Liftie status maps keyed by lift display name resolve directly to graph edge IDs.
    public func registerEdgeAliases(_ aliases: [String: String]) {
        lock.withLock {
            for (alias, edgeId) in aliases {
                aliasToEdgeId[Self.normalizeAliasKey(alias)] = edgeId
            }
        }
    }

    // MARK: - Flexible Telemetry Payload Parser

    private static func parsePayloadObject(
        _ root: Any,
        aliases: [String: String],
        defaultEpoch: Int64
    ) throws -> [DynamicStatusOverlay] {
        // Format 1: Top-level JSON array of overlay entries
        if let array = root as? [[String: Any]] {
            return try array.map { entry in
                try parseOverlayDictionary(entry, aliases: aliases, fallbackEpoch: defaultEpoch)
            }
        }

        guard let dict = root as? [String: Any] else {
            throw DynamicOverlayError.unsupportedPayloadFormat
        }

        let envelopeEpoch = extractTimestamp(from: dict) ?? defaultEpoch

        // Format 2: Cirque Cloud Run delta envelope ("overlays", "deltas", or "edges")
        for arrayKey in ["overlays", "deltas", "edges"] {
            if let rawEntries = dict[arrayKey] {
                guard let entries = rawEntries as? [[String: Any]] else {
                    throw DynamicOverlayError.unsupportedPayloadFormat
                }
                return try entries.map { entry in
                    try parseOverlayDictionary(entry, aliases: aliases, fallbackEpoch: envelopeEpoch)
                }
            }
        }

        // Format 3: Liftie live telemetry structure ("lifts": {"status": {...}}, optional "trails"/"runs" & "grooming")
        var liftieOverlays: [DynamicStatusOverlay] = []
        var matchedLiftieStructure = false

        let groomingMap = extractGroomingMap(from: dict, aliases: aliases)

        if let liftsContainer = dict["lifts"] as? [String: Any] {
            let statusMap = (liftsContainer["status"] as? [String: Any]) ?? liftsContainer
            if dict["lifts"] != nil, liftsContainer["status"] is [String: Any] {
                matchedLiftieStructure = true
                for (rawKey, rawStatusVal) in statusMap {
                    guard let statusStr = rawStatusVal as? String else {
                        throw DynamicOverlayError.invalidEdgeStatus(edgeId: rawKey, rawValue: "\(rawStatusVal)")
                    }
                    let resolvedId = resolveEdgeId(rawKey, defaultPrefix: "lift_", aliases: aliases)
                    guard !resolvedId.isEmpty else {
                        throw DynamicOverlayError.emptyEdgeIdentifier
                    }
                    guard let status = EdgeStatus(wireValue: statusStr) else {
                        throw DynamicOverlayError.invalidEdgeStatus(edgeId: resolvedId, rawValue: statusStr)
                    }
                    liftieOverlays.append(
                        DynamicStatusOverlay(
                            edgeId: resolvedId,
                            status: status,
                            effectiveGrooming: groomingMap[resolvedId],
                            lastUpdatedEpoch: envelopeEpoch
                        )
                    )
                }
            }
        }

        for trailsKey in ["trails", "runs", "pistes"] {
            if let trailsContainer = dict[trailsKey] as? [String: Any] {
                matchedLiftieStructure = true
                let statusMap = (trailsContainer["status"] as? [String: Any]) ?? trailsContainer
                for (rawKey, rawVal) in statusMap {
                    let resolvedId = resolveEdgeId(rawKey, defaultPrefix: "trail_", aliases: aliases)
                    guard !resolvedId.isEmpty else {
                        throw DynamicOverlayError.emptyEdgeIdentifier
                    }

                    if let statusStr = rawVal as? String {
                        guard let status = EdgeStatus(wireValue: statusStr) else {
                            throw DynamicOverlayError.invalidEdgeStatus(edgeId: resolvedId, rawValue: statusStr)
                        }
                        liftieOverlays.append(
                            DynamicStatusOverlay(
                                edgeId: resolvedId,
                                status: status,
                                effectiveGrooming: groomingMap[resolvedId],
                                lastUpdatedEpoch: envelopeEpoch
                            )
                        )
                    } else if let detailDict = rawVal as? [String: Any] {
                        var mutableDetail = detailDict
                        if mutableDetail["edge_id"] == nil && mutableDetail["edgeId"] == nil {
                            mutableDetail["edge_id"] = resolvedId
                        }
                        liftieOverlays.append(
                            try parseOverlayDictionary(
                                mutableDetail,
                                aliases: aliases,
                                fallbackEpoch: envelopeEpoch
                            )
                        )
                    } else {
                        throw DynamicOverlayError.invalidEdgeStatus(edgeId: resolvedId, rawValue: "\(rawVal)")
                    }
                }
            }
        }

        if matchedLiftieStructure {
            // Merge standalone grooming overrides for open pistes not already listed in trails.status
            let existingIds = Set(liftieOverlays.map(\.edgeId))
            for (edgeId, groomingOverride) in groomingMap where !existingIds.contains(edgeId) {
                liftieOverlays.append(
                    DynamicStatusOverlay(
                        edgeId: edgeId,
                        status: .open,
                        effectiveGrooming: groomingOverride,
                        lastUpdatedEpoch: envelopeEpoch
                    )
                )
            }
            return liftieOverlays.sorted { $0.edgeId < $1.edgeId }
        }

        // Format 4: Single DynamicStatusOverlay JSON object
        if dict["edge_id"] != nil || dict["edgeId"] != nil {
            return [try parseOverlayDictionary(dict, aliases: aliases, fallbackEpoch: envelopeEpoch)]
        }

        throw DynamicOverlayError.unsupportedPayloadFormat
    }

    private static func parseOverlayDictionary(
        _ dict: [String: Any],
        aliases: [String: String],
        fallbackEpoch: Int64
    ) throws -> DynamicStatusOverlay {
        let rawId = (dict["edgeId"] as? String)
            ?? (dict["edge_id"] as? String)
            ?? (dict["id"] as? String)

        guard let unwrappedId = rawId?.trimmingCharacters(in: .whitespacesAndNewlines),
              !unwrappedId.isEmpty else {
            throw DynamicOverlayError.emptyEdgeIdentifier
        }

        let resolvedEdgeId = aliases[normalizeAliasKey(unwrappedId)] ?? unwrappedId

        guard let rawStatus = dict["status"] as? String else {
            throw DynamicOverlayError.invalidEdgeStatus(
                edgeId: resolvedEdgeId,
                rawValue: String(describing: dict["status"])
            )
        }
        guard let status = EdgeStatus(wireValue: rawStatus) else {
            throw DynamicOverlayError.invalidEdgeStatus(edgeId: resolvedEdgeId, rawValue: rawStatus)
        }

        let rawGroomingValue: Any? = dict["effectiveGrooming"]
            ?? dict["effective_grooming"]
            ?? dict["grooming"]

        let effectiveGrooming: GroomingOverride?
        if rawGroomingValue == nil || rawGroomingValue is NSNull {
            effectiveGrooming = nil
        } else if let groomingStr = rawGroomingValue as? String {
            guard let parsedGrooming = GroomingOverride(wireValue: groomingStr) else {
                throw DynamicOverlayError.invalidGroomingOverride(
                    edgeId: resolvedEdgeId,
                    rawValue: groomingStr
                )
            }
            effectiveGrooming = parsedGrooming
        } else {
            throw DynamicOverlayError.invalidGroomingOverride(
                edgeId: resolvedEdgeId,
                rawValue: String(describing: rawGroomingValue)
            )
        }

        let recordEpoch = extractTimestamp(from: dict) ?? fallbackEpoch

        return DynamicStatusOverlay(
            edgeId: resolvedEdgeId,
            status: status,
            effectiveGrooming: effectiveGrooming,
            lastUpdatedEpoch: recordEpoch
        )
    }

    private static func extractGroomingMap(
        from root: [String: Any],
        aliases: [String: String]
    ) -> [String: GroomingOverride] {
        guard let rawMap = root["grooming"] as? [String: Any] else {
            return [:]
        }
        var result: [String: GroomingOverride] = [:]
        for (rawKey, rawVal) in rawMap {
            guard let groomingStr = rawVal as? String,
                  let override = GroomingOverride(wireValue: groomingStr) else {
                continue
            }
            let edgeId = resolveEdgeId(rawKey, defaultPrefix: "trail_", aliases: aliases)
            if !edgeId.isEmpty {
                result[edgeId] = override
            }
        }
        return result
    }

    private static func extractTimestamp(from dict: [String: Any]) -> Int64? {
        for key in ["lastUpdatedEpoch", "last_updated_epoch", "updated_at", "updatedAt", "timestamp"] {
            if let int64Val = dict[key] as? Int64 {
                return DynamicStatusOverlay.normalizeEpochSeconds(int64Val)
            }
            if let intVal = dict[key] as? Int {
                return DynamicStatusOverlay.normalizeEpochSeconds(Int64(intVal))
            }
            if let doubleVal = dict[key] as? Double {
                return DynamicStatusOverlay.normalizeEpochSeconds(Int64(doubleVal))
            }
            if let nestedTs = dict[key] as? [String: Any] {
                if let liftsTs = nestedTs["lifts"] as? Int64 {
                    return DynamicStatusOverlay.normalizeEpochSeconds(liftsTs)
                }
                if let liftsTsInt = nestedTs["lifts"] as? Int {
                    return DynamicStatusOverlay.normalizeEpochSeconds(Int64(liftsTsInt))
                }
                if let liftsTsDouble = nestedTs["lifts"] as? Double {
                    return DynamicStatusOverlay.normalizeEpochSeconds(Int64(liftsTsDouble))
                }
            }
        }
        return nil
    }

    private static func resolveEdgeId(
        _ rawKey: String,
        defaultPrefix: String,
        aliases: [String: String]
    ) -> String {
        let trimmed = rawKey.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return "" }

        let normalizedAlias = normalizeAliasKey(trimmed)
        if let mapped = aliases[normalizedAlias] {
            return mapped
        }

        // Preserve canonical edge identifiers directly (e.g. "lift_ramcharger", "edge_lift_188386457", "trail_mr_k").
        if trimmed.hasPrefix("lift_") || trimmed.hasPrefix("trail_") || trimmed.hasPrefix("edge_") {
            return trimmed
        }

        // Fallback slugification for human-readable Liftie display names (e.g. "Ramcharger 8" -> "lift_ramcharger" / slug).
        var slug = trimmed.lowercased()
        var cleanedScalars: [Character] = []
        var previousWasUnderscore = false
        for ch in slug {
            if ch.isLetter || ch.isNumber {
                cleanedScalars.append(ch)
                previousWasUnderscore = false
            } else if !previousWasUnderscore {
                cleanedScalars.append("_")
                previousWasUnderscore = true
            }
        }
        slug = String(cleanedScalars).trimmingCharacters(in: CharacterSet(charactersIn: "_"))

        // Strip trailing chair capacity suffixes on standard lift names when slugifying (e.g. "ramcharger_8" -> "ramcharger")
        // unless an explicit alias was provided, while keeping multi-word lift names like "swift_current_6" -> "swift_current".
        if defaultPrefix == "lift_" {
            let parts = slug.split(separator: "_")
            if parts.count >= 2, let last = parts.last, Int(last) != nil {
                slug = parts.dropLast().joined(separator: "_")
            }
        }

        return "\(defaultPrefix)\(slug)"
    }

    private static func normalizeAliasKey(_ key: String) -> String {
        key.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
    }
}
