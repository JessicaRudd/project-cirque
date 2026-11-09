"""
Project Cirque: Code Snippet from STEP_1_2
Module: pipeline/build_topology.py
Highlight: DAG Gravity Polarity Enforcement & 25m Virtual Transfer Edge Injection
"""

from typing import Dict, List
from pipeline.build_topology import GraphEdge, GraphNode, haversine_distance_m


def inject_virtual_transfer_edges(
    lift_top_nodes: List[GraphNode],
    nodes_by_id: Dict[str, GraphNode],
) -> List[GraphEdge]:
    """
    For every lift_top terminal, find all trail start / junction nodes within a
    25-meter Euclidean/Haversine radius and inject a virtual walk/skate edge
    (type='piste', difficulty='novice', length_m <= 25.0, base_cost_seconds=30.0).
    """
    transfer_edges: List[GraphEdge] = []
    for ltop in lift_top_nodes:
        for candidate in nodes_by_id.values():
            if candidate.node_type in {"lift_top", "lift_base"}:
                continue
            dist_m = haversine_distance_m(ltop.lon, ltop.lat, candidate.lon, candidate.lat)
            if dist_m <= 25.0:
                xfer_len = round(max(1.0, min(25.0, dist_m)), 2)
                v_diff = round(candidate.elevation_m - ltop.elevation_m, 2)  # <= 0.0
                pitch = round((abs(v_diff) / xfer_len) * 100.0, 2)

                transfer_edges.append(
                    GraphEdge(
                        edge_id=f"edge_xfer_{ltop.node_id}_to_{candidate.node_id}",
                        source_node=ltop.node_id,
                        target_node=candidate.node_id,
                        type="piste",
                        name=f"Unload Transfer: {ltop.name} to {candidate.name}",
                        difficulty="novice",
                        grooming="groomed",
                        length_m=xfer_len,
                        vertical_diff_m=v_diff,
                        average_pitch_pct=pitch,
                        base_cost_seconds=30.0,
                    )
                )
    return transfer_edges
