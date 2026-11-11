// .cirque/devlog/M3_MOBILE_ROUTING_CORE/amenity_routing_sample.swift
// Extracted from ios/CirqueCore/Sources/CirqueCore/Routing/AmenityRouter.swift

import Foundation

public extension AmenityRouter {
    /// Resolves open time-gated venues and executes a single 1-to-N Dijkstra pass
    /// to select the lowest-cost venue reachable within `query.maxDifficulty`.
    func solveVoiceSnackIntentSample(query: RouteQuery) -> (MountainServiceRecord, [RouteStep])? {
        let candidates = resolveCandidateVenues(for: query)
        guard !candidates.isEmpty else { return nil }

        let venuesByNode = Dictionary(grouping: candidates, by: \.nodeId)
        let targetNodeIds = Set(venuesByNode.keys)

        guard let resolved = solver.solveShortestPath(
            toCandidateNodes: targetNodeIds,
            query: query
        ),
        let selectedVenue = venuesByNode[resolved.destinationNodeId]?.first else {
            return nil
        }

        return (selectedVenue, resolved.steps)
    }
}
