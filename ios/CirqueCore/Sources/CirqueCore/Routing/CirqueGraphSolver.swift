import Foundation

// MARK: - Supporting Domain Types (TECH_SPEC Section 4 & Section 2.4)

/// Classification of directed topological edges in the resort graph.
public enum EdgeType: String, Codable, Sendable, CaseIterable {
    case piste = "piste"
    case lift = "lift"
}

/// Ordered ski terrain difficulty scale (`novice` < `intermediate` < `advanced` < `expert` < `freeride`).
/// Aerial lift edges carry `.lift` (rank 0, neutral difficulty) so they are never blocked by skill ceilings.
public enum SkiDifficulty: String, Codable, Sendable, Comparable, CaseIterable {
    case lift = "lift"
    case novice = "novice"
    case intermediate = "intermediate"
    case advanced = "advanced"
    case expert = "expert"
    case freeride = "freeride"

    public var rank: Int {
        switch self {
        case .lift: return 0
        case .novice: return 1
        case .intermediate: return 2
        case .advanced: return 3
        case .expert: return 4
        case .freeride: return 5
        }
    }

    public var spokenLabel: String {
        switch self {
        case .lift: return "aerial lift"
        case .novice: return "novice green"
        case .intermediate: return "intermediate blue"
        case .advanced: return "advanced black diamond"
        case .expert: return "expert double black"
        case .freeride: return "extreme freeride chute"
        }
    }

    public static func < (lhs: SkiDifficulty, rhs: SkiDifficulty) -> Bool {
        lhs.rank < rhs.rank
    }
}

/// Surface grooming classification for piste edges.
public enum GroomingType: String, Codable, Sendable, CaseIterable {
    case groomed = "groomed"
    case backcountry = "backcountry"
    case mogul = "mogul"
    case ungroomed = "ungroomed"
    case powder = "powder"
    case moguls = "moguls"

    public var isMogul: Bool {
        self == .mogul || self == .moguls
    }

    public var isUngroomedBackcountry: Bool {
        switch self {
        case .backcountry, .ungroomed, .powder:
            return true
        case .groomed, .mogul, .moguls:
            return false
        }
    }
}

/// Multi-criteria routing request bridging Gemma SLM structured intent (`SkiIntent`) with local graph state.
public struct RouteQuery: Equatable, Hashable, Codable, Sendable {
    public let startNodeId: String
    public let targetNodeId: String?
    public let targetPoiCategory: String?
    public let targetPoiName: String?
    public let preferredServiceSpeed: String?
    public let currentTimeLocal: String?
    public let requireOpenNow: Bool
    public let maxDifficulty: SkiDifficulty
    public let preferGroomed: Bool
    public let avoidMoguls: Bool
    public let excludeReservations: Bool

    public init(
        startNodeId: String,
        targetNodeId: String? = nil,
        targetPoiCategory: String? = nil,
        targetPoiName: String? = nil,
        preferredServiceSpeed: String? = nil,
        currentTimeLocal: String? = nil,
        requireOpenNow: Bool = true,
        maxDifficulty: SkiDifficulty = .advanced,
        preferGroomed: Bool = false,
        avoidMoguls: Bool = false,
        excludeReservations: Bool = false
    ) {
        self.startNodeId = startNodeId
        self.targetNodeId = targetNodeId
        self.targetPoiCategory = targetPoiCategory
        self.targetPoiName = targetPoiName
        self.preferredServiceSpeed = preferredServiceSpeed
        self.currentTimeLocal = currentTimeLocal
        self.requireOpenNow = requireOpenNow
        self.maxDifficulty = maxDifficulty
        self.preferGroomed = preferGroomed
        self.avoidMoguls = avoidMoguls
        self.excludeReservations = excludeReservations
    }
}

/// Optimal destination and reconstructed path returned by a single-pass 1-to-N multi-target Dijkstra search.
public struct ResolvedTargetRoute: Equatable, Hashable, Codable, Sendable {
    public let destinationNodeId: String
    public let totalCostSeconds: Double
    public let steps: [RouteStep]

    public init(
        destinationNodeId: String,
        totalCostSeconds: Double,
        steps: [RouteStep]
    ) {
        self.destinationNodeId = destinationNodeId
        self.totalCostSeconds = totalCostSeconds
        self.steps = steps
    }
}

/// A single directed traversal step in a resolved route, including synthesized natural-language audio guidance.
public struct RouteStep: Equatable, Hashable, Codable, Sendable {
    public let edgeId: String
    public let name: String
    public let type: EdgeType
    public let difficulty: SkiDifficulty
    public let lengthMeters: Double
    public let verticalDiffMeters: Double
    public let instructionAudio: String

    public init(
        edgeId: String,
        name: String,
        type: EdgeType,
        difficulty: SkiDifficulty,
        lengthMeters: Double,
        verticalDiffMeters: Double,
        instructionAudio: String
    ) {
        self.edgeId = edgeId
        self.name = name
        self.type = type
        self.difficulty = difficulty
        self.lengthMeters = lengthMeters
        self.verticalDiffMeters = verticalDiffMeters
        self.instructionAudio = instructionAudio
    }
}

// MARK: - Pure Swift Binary Min-Heap Priority Queue

/// Zero-dependency array-backed binary min-heap for O(log V) Dijkstra frontier extraction.
public struct MinHeap<Element: Comparable & Sendable>: Sendable {
    private var storage: [Element] = []

    public init() {}

    public init(minimumCapacity: Int) {
        storage.reserveCapacity(minimumCapacity)
    }

    public var isEmpty: Bool {
        storage.isEmpty
    }

    public var count: Int {
        storage.count
    }

    public var peek: Element? {
        storage.first
    }

    public mutating func insert(_ element: Element) {
        storage.append(element)
        siftUp(from: storage.count - 1)
    }

    @discardableResult
    public mutating func extractMin() -> Element? {
        guard !storage.isEmpty else { return nil }
        if storage.count == 1 {
            return storage.removeLast()
        }
        let minValue = storage[0]
        storage[0] = storage.removeLast()
        siftDown(from: 0)
        return minValue
    }

    private mutating func siftUp(from index: Int) {
        var childIndex = index
        let child = storage[childIndex]
        while childIndex > 0 {
            let parentIndex = (childIndex - 1) >> 1
            let parent = storage[parentIndex]
            if child < parent {
                storage[childIndex] = parent
                childIndex = parentIndex
            } else {
                break
            }
        }
        storage[childIndex] = child
    }

    private mutating func siftDown(from index: Int) {
        let count = storage.count
        var parentIndex = index
        let element = storage[parentIndex]

        while true {
            let leftChildIndex = (parentIndex << 1) + 1
            if leftChildIndex >= count {
                break
            }
            var candidateIndex = leftChildIndex
            let rightChildIndex = leftChildIndex + 1
            if rightChildIndex < count && storage[rightChildIndex] < storage[leftChildIndex] {
                candidateIndex = rightChildIndex
            }
            if storage[candidateIndex] < element {
                storage[parentIndex] = storage[candidateIndex]
                parentIndex = candidateIndex
            } else {
                break
            }
        }
        storage[parentIndex] = element
    }
}

// MARK: - Multi-Criteria Dijkstra Graph Solver (TECH_SPEC Section 4)

/// Deterministic, offline multi-criteria Dijkstra pathfinding engine backed by `CirqueDatabase`.
/// Enforces hard terrain skill ceilings and soft surface preference multipliers in sub-10ms latency.
public final class CirqueGraphSolver {

    // MARK: - Cost Multiplier Constants

    public static let groomedBonusMultiplier: Double = 0.8
    public static let ungroomedPenaltyMultiplier: Double = 2.5
    public static let mogulAvoidancePenaltyMultiplier: Double = 5.0

    // MARK: - Internal Frontier & Backtracking Types

    private struct FrontierEntry: Comparable, Sendable {
        let nodeId: String
        let cumulativeCost: Double

        static func < (lhs: FrontierEntry, rhs: FrontierEntry) -> Bool {
            if lhs.cumulativeCost != rhs.cumulativeCost {
                return lhs.cumulativeCost < rhs.cumulativeCost
            }
            return lhs.nodeId < rhs.nodeId
        }
    }

    private struct PredecessorStep {
        let previousNodeId: String
        let edge: EdgeRecord
    }

    // MARK: - Properties

    public let database: CirqueDatabase
    public let overlayManager: DynamicOverlayManager?

    /// Initializes the Dijkstra graph solver with an active `CirqueDatabase` connection
    /// and an optional thread-safe `DynamicOverlayManager` for live lift/trail overrides.
    public init(
        database: CirqueDatabase,
        overlayManager: DynamicOverlayManager? = nil
    ) {
        self.database = database
        self.overlayManager = overlayManager
    }

    // MARK: - Multi-Criteria Edge Cost Evaluation

    /// Evaluates the effective traversal cost (in weighted seconds) of a directed edge under `query`,
    /// automatically consulting `overlayManager` for active real-time status or grooming overrides.
    /// - Returns: Weighted cost in seconds, or `nil` if the edge is closed/on-hold or violates `query.maxDifficulty`.
    public func calculateCost(edge: EdgeRecord, query: RouteQuery) -> Double? {
        let activeOverlay = overlayManager?.getOverlay(forEdgeId: edge.edgeId)
        return calculateCost(edge: edge, overlay: activeOverlay, query: query)
    }

    /// Evaluates the effective traversal cost (in weighted seconds) of a directed edge given an explicit `DynamicStatusOverlay`.
    /// - Returns: Weighted cost in seconds, or `nil` if `overlay.status` is non-open (`.closedPatrol`, `.windHold`, `.mechanicalHold`)
    ///   or if the edge violates the skier's hard `maxDifficulty` ceiling.
    public func calculateCost(
        edge: EdgeRecord,
        overlay: DynamicStatusOverlay?,
        query: RouteQuery
    ) -> Double? {
        // 1. Dynamic Status Hard Exclusion: Never route across patrol-closed, wind-held, or mechanically held edges.
        if let status = overlay?.status {
            switch status {
            case .closedPatrol, .windHold, .mechanicalHold:
                return nil
            case .open:
                break
            }
        }

        let type = edge.edgeType
        let difficulty = type == .lift ? .lift : edge.skiDifficulty

        // 2. Hard Difficulty Cutoff: Never route a skier onto a piste exceeding their declared skill ceiling.
        if type == .piste && difficulty > query.maxDifficulty {
            return nil
        }

        // Guard against invalid negative base costs in malformed fixtures.
        let baseCost = max(0.0, edge.baseCostSeconds)
        var multiplier: Double = 1.0

        // 3. Soft Preference Multipliers (applied to downhill ski pistes, respecting dynamic grooming overrides)
        if type == .piste {
            let effectiveGrooming: GroomingType? = overlay?.effectiveGrooming?.groomingType ?? edge.groomingType

            if query.preferGroomed {
                if effectiveGrooming == .groomed {
                    multiplier *= Self.groomedBonusMultiplier
                } else if let grooming = effectiveGrooming, grooming.isUngroomedBackcountry {
                    multiplier *= Self.ungroomedPenaltyMultiplier
                }
            }

            if query.avoidMoguls, let grooming = effectiveGrooming, grooming.isMogul {
                multiplier *= Self.mogulAvoidancePenaltyMultiplier
            }
        }

        return baseCost * multiplier
    }

    // MARK: - Priority-Queue Dijkstra Pathfinding

    /// Solves the optimal shortest path satisfying `query` using a binary min-heap Dijkstra search.
    /// - Parameter query: Multi-criteria `RouteQuery` specifying origin, destination/POI filters, and terrain constraints.
    /// - Returns: Chronological array of `RouteStep` instructions from `startNodeId` to destination, or `nil` if no safe route exists.
    public func solveShortestPath(query: RouteQuery) -> [RouteStep]? {
        let candidateTargets = resolveTargetNodeIds(for: query)
        return solveShortestPath(toCandidateNodes: candidateTargets, query: query)?.steps
    }

    /// Executes a single-pass 1-to-N priority-queue Dijkstra search from `query.startNodeId` across `candidateTargets`.
    /// Because vertices are extracted from the min-heap in monotonically non-decreasing order of `cumulativeCost`,
    /// the first target popped from `frontier` is guaranteed to be the globally optimal reachable destination.
    public func solveShortestPath(
        toCandidateNodes candidateTargets: Set<String>,
        query: RouteQuery
    ) -> ResolvedTargetRoute? {
        guard !candidateTargets.isEmpty else {
            return nil
        }

        if candidateTargets.contains(query.startNodeId) {
            return ResolvedTargetRoute(
                destinationNodeId: query.startNodeId,
                totalCostSeconds: 0.0,
                steps: []
            )
        }

        var frontier = MinHeap<FrontierEntry>(minimumCapacity: 64)
        var minCosts: [String: Double] = [query.startNodeId: 0.0]
        var predecessors: [String: PredecessorStep] = [:]
        var settledNodes = Set<String>()

        frontier.insert(FrontierEntry(nodeId: query.startNodeId, cumulativeCost: 0.0))

        var resolvedDestinationNodeId: String?
        var resolvedTotalCost: Double = 0.0

        while let current = frontier.extractMin() {
            // Lazy deletion: skip heap entries superseded by a lower-cost relaxation.
            if settledNodes.contains(current.nodeId) {
                continue
            }
            settledNodes.insert(current.nodeId)

            // Min-heap monotonicity guarantees the first popped candidate is globally optimal across all N targets.
            if candidateTargets.contains(current.nodeId) {
                resolvedDestinationNodeId = current.nodeId
                resolvedTotalCost = current.cumulativeCost
                break
            }

            let outgoingEdges = database.getOutgoingEdges(fromNodeId: current.nodeId)
            for edge in outgoingEdges {
                let neighborId = edge.targetNode
                if settledNodes.contains(neighborId) {
                    continue
                }

                guard let edgeCost = calculateCost(edge: edge, query: query) else {
                    continue
                }

                let newCumulativeCost = current.cumulativeCost + edgeCost
                let existingCost = minCosts[neighborId] ?? .infinity

                if newCumulativeCost < existingCost {
                    minCosts[neighborId] = newCumulativeCost
                    predecessors[neighborId] = PredecessorStep(
                        previousNodeId: current.nodeId,
                        edge: edge
                    )
                    frontier.insert(
                        FrontierEntry(
                            nodeId: neighborId,
                            cumulativeCost: newCumulativeCost
                        )
                    )
                }
            }
        }

        guard let destinationNodeId = resolvedDestinationNodeId,
              let steps = reconstructRoute(
                  from: query.startNodeId,
                  to: destinationNodeId,
                  predecessors: predecessors
              ) else {
            return nil
        }

        return ResolvedTargetRoute(
            destinationNodeId: destinationNodeId,
            totalCostSeconds: resolvedTotalCost,
            steps: steps
        )
    }

    private func resolveTargetNodeIds(for query: RouteQuery) -> Set<String> {
        var targets = Set<String>()

        if let explicitTarget = query.targetNodeId, !explicitTarget.isEmpty {
            targets.insert(explicitTarget)
            return targets
        }

        let timeFilter = query.requireOpenNow ? query.currentTimeLocal : nil
        let matchingServices = database.getServices(
            category: query.targetPoiCategory,
            speed: query.preferredServiceSpeed,
            timeLocal: timeFilter
        )

        if let poiName = query.targetPoiName?.trimmingCharacters(in: .whitespacesAndNewlines),
           !poiName.isEmpty {
            let normalizedQueryName = poiName.lowercased()
            for service in matchingServices where service.name.lowercased().contains(normalizedQueryName) {
                targets.insert(service.nodeId)
            }

            if targets.isEmpty {
                for node in database.getAllNodes() {
                    if let nodeName = node.name?.lowercased(), nodeName.contains(normalizedQueryName) {
                        targets.insert(node.nodeId)
                    }
                }
            }
        } else {
            for service in matchingServices {
                targets.insert(service.nodeId)
            }

            if targets.isEmpty, let category = query.targetPoiCategory {
                for node in database.getAllNodes() where node.poiCategory == category {
                    targets.insert(node.nodeId)
                }
            }
        }

        return targets
    }

    // MARK: - Path Backtracking & Natural Audio Instruction Synthesis

    private func reconstructRoute(
        from startNodeId: String,
        to destinationNodeId: String,
        predecessors: [String: PredecessorStep]
    ) -> [RouteStep]? {
        var reversedEdges: [EdgeRecord] = []
        var cursorNodeId = destinationNodeId

        while cursorNodeId != startNodeId {
            guard let step = predecessors[cursorNodeId] else {
                return nil
            }
            reversedEdges.append(step.edge)
            cursorNodeId = step.previousNodeId
        }

        let chronologicalEdges = Array(reversedEdges.reversed())
        var routeSteps: [RouteStep] = []
        routeSteps.reserveCapacity(chronologicalEdges.count)

        for (index, edge) in chronologicalEdges.enumerated() {
            let type = edge.edgeType
            let difficulty: SkiDifficulty = (type == .lift) ? .lift : edge.skiDifficulty
            let isFinalStep = (index == chronologicalEdges.count - 1)
            let audioInstruction = buildAudioInstruction(
                for: edge,
                type: type,
                difficulty: difficulty,
                isFirstStep: index == 0,
                isFinalStep: isFinalStep
            )

            routeSteps.append(
                RouteStep(
                    edgeId: edge.edgeId,
                    name: edge.name,
                    type: type,
                    difficulty: difficulty,
                    lengthMeters: edge.lengthM,
                    verticalDiffMeters: edge.verticalDiffM,
                    instructionAudio: audioInstruction
                )
            )
        }

        return routeSteps
    }

    private func buildAudioInstruction(
        for edge: EdgeRecord,
        type: EdgeType,
        difficulty: SkiDifficulty,
        isFirstStep: Bool,
        isFinalStep: Bool
    ) -> String {
        let targetNode = database.getNode(byId: edge.targetNode)
        let targetName = targetNode?.name ?? "the next junction"

        switch type {
        case .lift:
            if isFinalStep {
                return "Take \(edge.name) to \(targetName) to arrive at your destination."
            }
            return "Take \(edge.name) to \(targetName)."

        case .piste:
            let verticalDropMeters = Int(abs(edge.verticalDiffM).rounded())
            let actionPrefix = isFirstStep ? "Start down" : "Turn onto"
            if isFinalStep {
                return "\(actionPrefix) \(edge.name) (\(difficulty.spokenLabel)) and descend \(verticalDropMeters) meters to \(targetName)."
            }
            return "\(actionPrefix) \(edge.name) (\(difficulty.spokenLabel)) toward \(targetName)."
        }
    }
}
