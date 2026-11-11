/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import {
  Mountain,
  CheckCircle2,
  FileCode,
  Layers,
  Share2,
  ShieldCheck,
  Database,
  FileText,
  Copy,
  Check,
  GitBranch,
  Utensils,
  Clock,
  Filter,
} from 'lucide-react';

interface FeatureItem {
  id: string;
  name: string;
  type: 'piste' | 'lift' | 'amenity';
  difficulty?: string;
  aerialway?: string;
  category?: string;
  service_speed?: string | null;
  open_time_local?: string;
  close_time_local?: string;
  price_tier?: string | null;
  is_ski_in_only?: number;
  snapping_distance_m?: number;
  assigned_node_id?: string;
  grooming?: string;
  startElevM?: number;
  endElevM?: number;
  coords: number[][] | number[];
}

const BIG_SKY_FEATURES: FeatureItem[] = [
  { id: 'piste_1001', name: 'Mr. K', type: 'piste', difficulty: 'novice', grooming: 'groomed', startElevM: 2682, endElevM: 2286, coords: [[-111.4120, 45.2730], [-111.4085, 45.2775], [-111.4045, 45.2810], [-111.4010, 45.2840]] },
  { id: 'piste_1002', name: 'Meadow Run', type: 'piste', difficulty: 'novice', grooming: 'groomed', startElevM: 2380, endElevM: 2286, coords: [[-111.4045, 45.2810], [-111.4025, 45.2825], [-111.4010, 45.2840]] },
  { id: 'piste_1003', name: 'Deepfoot', type: 'piste', difficulty: 'novice', grooming: 'groomed', startElevM: 2420, endElevM: 2286, coords: [[-111.4080, 45.2860], [-111.4045, 45.2850], [-111.4010, 45.2840]] },
  { id: 'piste_1010', name: 'Africa', type: 'piste', difficulty: 'intermediate', grooming: 'groomed', startElevM: 2810, endElevM: 2286, coords: [[-111.4265, 45.2795], [-111.4200, 45.2815], [-111.4120, 45.2840], [-111.4010, 45.2840]] },
  { id: 'piste_1011', name: 'Calamity Jane', type: 'piste', difficulty: 'intermediate', grooming: 'groomed', startElevM: 2810, endElevM: 2420, coords: [[-111.4265, 45.2795], [-111.4180, 45.2825], [-111.4080, 45.2860]] },
  { id: 'piste_1012', name: 'Swift Current Run', type: 'piste', difficulty: 'intermediate', grooming: 'groomed', startElevM: 2810, endElevM: 2286, coords: [[-111.4265, 45.2795], [-111.4190, 45.2830], [-111.4080, 45.2860], [-111.4010, 45.2840]] },
  { id: 'piste_1013', name: 'Silver Knife', type: 'piste', difficulty: 'intermediate', grooming: 'groomed', startElevM: 2810, endElevM: 2682, coords: [[-111.4265, 45.2795], [-111.4190, 45.2760], [-111.4120, 45.2730]] },
  { id: 'piste_1014', name: 'Shedhorn Trail', type: 'piste', difficulty: 'intermediate', grooming: 'groomed', startElevM: 2850, endElevM: 2550, coords: [[-111.4400, 45.2650], [-111.4390, 45.2630], [-111.4420, 45.2600]] },
  { id: 'piste_1015', name: 'Elk Park Ridge', type: 'piste', difficulty: 'intermediate', grooming: 'groomed', startElevM: 2920, endElevM: 2810, coords: [[-111.4360, 45.2740], [-111.4310, 45.2765], [-111.4265, 45.2795]] },
  { id: 'piste_1016', name: 'Lobo Runout', type: 'piste', difficulty: 'novice', grooming: 'groomed', startElevM: 2550, endElevM: 2286, coords: [[-111.4420, 45.2600], [-111.4250, 45.2700], [-111.4010, 45.2840]] },
  { id: 'piste_1020', name: 'Lone Peak Bowl', type: 'piste', difficulty: 'advanced', grooming: 'backcountry', startElevM: 3150, endElevM: 2920, coords: [[-111.4480, 45.2760], [-111.4420, 45.2750], [-111.4360, 45.2740]] },
  { id: 'piste_1021', name: 'Liberty Bowl', type: 'piste', difficulty: 'advanced', grooming: 'backcountry', startElevM: 3403, endElevM: 2850, coords: [[-111.4510, 45.2785], [-111.4450, 45.2715], [-111.4400, 45.2650]] },
  { id: 'piste_1022', name: 'Snake Pit', type: 'piste', difficulty: 'advanced', grooming: 'mogul', startElevM: 2920, endElevM: 2810, coords: [[-111.4360, 45.2740], [-111.4310, 45.2770], [-111.4265, 45.2795]] },
  { id: 'piste_1030', name: 'Big Couloir', type: 'piste', difficulty: 'freeride', grooming: 'backcountry', startElevM: 3403, endElevM: 3150, coords: [[-111.4510, 45.2785], [-111.4495, 45.2772], [-111.4480, 45.2760]] },
  { id: 'piste_1031', name: 'The Gullies', type: 'piste', difficulty: 'expert', grooming: 'backcountry', startElevM: 3403, endElevM: 2920, coords: [[-111.4510, 45.2785], [-111.4440, 45.2765], [-111.4360, 45.2740]] },
  { id: 'piste_1032', name: 'Challenger Chute', type: 'piste', difficulty: 'expert', grooming: 'mogul', startElevM: 2980, endElevM: 2810, coords: [[-111.4380, 45.2820], [-111.4320, 45.2810], [-111.4265, 45.2795]] },
  { id: 'lift_2001', name: 'Lone Peak Tram', type: 'lift', aerialway: 'cable_car', startElevM: 2920, endElevM: 3403.5, coords: [[-111.4360, 45.2740], [-111.4510, 45.2785]] },
  { id: 'lift_2002', name: 'Swift Current 6', type: 'lift', aerialway: 'chair_lift', startElevM: 2286, endElevM: 2810.5, coords: [[-111.4010, 45.2840], [-111.4265, 45.2795]] },
  { id: 'lift_2003', name: 'Ramcharger 8', type: 'lift', aerialway: 'chair_lift', startElevM: 2286, endElevM: 2682.5, coords: [[-111.4010, 45.2840], [-111.4120, 45.2730]] },
  { id: 'lift_2004', name: 'Powder Seeker 6', type: 'lift', aerialway: 'chair_lift', startElevM: 2920, endElevM: 3150.5, coords: [[-111.4360, 45.2740], [-111.4480, 45.2760]] },
  { id: 'lift_2005', name: 'Challenger 3', type: 'lift', aerialway: 'chair_lift', startElevM: 2810, endElevM: 2980.5, coords: [[-111.4265, 45.2795], [-111.4380, 45.2820]] },
  { id: 'lift_2006', name: 'Shedhorn 4', type: 'lift', aerialway: 'chair_lift', startElevM: 2550, endElevM: 2850.5, coords: [[-111.4420, 45.2600], [-111.4400, 45.2650]] },
  { id: 'lift_2007', name: 'Explorer 2', type: 'lift', aerialway: 'chair_lift', startElevM: 2286, endElevM: 2420.5, coords: [[-111.4010, 45.2840], [-111.4080, 45.2860]] },
  { id: 'srv_shedhorn_grill', name: 'Shedhorn Grill', type: 'amenity', category: 'quick_snack', service_speed: 'grab_and_go', open_time_local: '11:00', close_time_local: '15:30', price_tier: '$$', is_ski_in_only: 1, snapping_distance_m: 0.0, assigned_node_id: 'node_jct_0011', coords: [-111.4390, 45.2630] },
  { id: 'srv_headwaters_grille', name: 'Headwaters Grille', type: 'amenity', category: 'quick_snack', service_speed: 'counter_service', open_time_local: '08:00', close_time_local: '17:00', price_tier: '$$', is_ski_in_only: 0, snapping_distance_m: 20.12, assigned_node_id: 'node_poi_srv_headwaters_grille', coords: [-111.40112, 45.28416] },
  { id: 'srv_uncle_dans_cookies', name: "Uncle Dan's Cookie Hut", type: 'amenity', category: 'quick_snack', service_speed: 'grab_and_go', open_time_local: '09:30', close_time_local: '15:30', price_tier: '$', is_ski_in_only: 1, snapping_distance_m: 12.99, assigned_node_id: 'node_village_mountain_village', coords: [-111.40115, 45.28395] },
  { id: 'srv_everetts_8800', name: "Everett's 8800", type: 'amenity', category: 'sit_down', service_speed: 'table_service', open_time_local: '11:00', close_time_local: '15:00', price_tier: '$$$', is_ski_in_only: 1, snapping_distance_m: 0.0, assigned_node_id: 'node_jct_001', coords: [-111.4120, 45.2730] },
  { id: 'srv_vista_hall', name: 'Vista Hall', type: 'amenity', category: 'cafeteria', service_speed: 'counter_service', open_time_local: '08:00', close_time_local: '17:00', price_tier: '$$', is_ski_in_only: 0, snapping_distance_m: 0.0, assigned_node_id: 'node_village_mountain_village', coords: [-111.4010, 45.2840] },
  { id: 'srv_montana_jack', name: 'Montana Jack', type: 'amenity', category: 'bar', service_speed: 'table_service', open_time_local: '11:00', close_time_local: '22:00', price_tier: '$$', is_ski_in_only: 0, snapping_distance_m: 6.8, assigned_node_id: 'node_village_mountain_village', coords: [-111.40105, 45.28405] },
  { id: 'srv_patrol_summit', name: 'Lone Peak Summit Patrol Shack', type: 'amenity', category: 'patrol', service_speed: null, open_time_local: '08:30', close_time_local: '16:30', price_tier: null, is_ski_in_only: 1, snapping_distance_m: 0.0, assigned_node_id: 'node_summit_lone_peak', coords: [-111.4510, 45.2785] },
  { id: 'srv_patrol_swift_current', name: 'Swift Current Patrol Shack', type: 'amenity', category: 'patrol', service_speed: null, open_time_local: '08:30', close_time_local: '16:30', price_tier: null, is_ski_in_only: 1, snapping_distance_m: 0.0, assigned_node_id: 'node_jct_0006', coords: [-111.4265, 45.2795] },
  { id: 'srv_patrol_andesite', name: 'Andesite Summit Patrol Station', type: 'amenity', category: 'patrol', service_speed: null, open_time_local: '08:30', close_time_local: '16:30', price_tier: null, is_ski_in_only: 1, snapping_distance_m: 0.0, assigned_node_id: 'node_jct_001', coords: [-111.4120, 45.2730] },
  { id: 'srv_patrol_shedhorn', name: 'Shedhorn Patrol Shack', type: 'amenity', category: 'patrol', service_speed: null, open_time_local: '08:30', close_time_local: '16:30', price_tier: null, is_ski_in_only: 1, snapping_distance_m: 0.0, assigned_node_id: 'node_jct_0011', coords: [-111.4390, 45.2630] },
  { id: 'srv_patrol_village_base', name: 'Mountain Village Ski Patrol Base', type: 'amenity', category: 'patrol', service_speed: null, open_time_local: '08:30', close_time_local: '16:30', price_tier: null, is_ski_in_only: 0, snapping_distance_m: 0.0, assigned_node_id: 'node_village_mountain_village', coords: [-111.4010, 45.2840] },
  { id: 'srv_warming_hut_andesite', name: 'Andesite Summit Warming Hut', type: 'amenity', category: 'warming_hut', service_speed: null, open_time_local: '09:00', close_time_local: '16:00', price_tier: null, is_ski_in_only: 1, snapping_distance_m: 0.0, assigned_node_id: 'node_jct_001', coords: [-111.4120, 45.2730] },
  { id: 'srv_warming_hut_village', name: 'Mountain Village Warming Center', type: 'amenity', category: 'warming_hut', service_speed: null, open_time_local: '08:00', close_time_local: '18:00', price_tier: null, is_ski_in_only: 0, snapping_distance_m: 0.0, assigned_node_id: 'node_village_mountain_village', coords: [-111.4010, 45.2840] },
  { id: 'srv_restroom_village', name: 'Mountain Village Public Restrooms', type: 'amenity', category: 'restroom', service_speed: null, open_time_local: '07:00', close_time_local: '22:00', price_tier: null, is_ski_in_only: 0, snapping_distance_m: 0.0, assigned_node_id: 'node_village_mountain_village', coords: [-111.4010, 45.2840] },
  { id: 'srv_restroom_andesite', name: 'Andesite Top Restrooms', type: 'amenity', category: 'restroom', service_speed: null, open_time_local: '09:00', close_time_local: '16:00', price_tier: null, is_ski_in_only: 1, snapping_distance_m: 0.0, assigned_node_id: 'node_jct_001', coords: [-111.4120, 45.2730] },
];

const HARNESS_TESTS = [
  { id: 'testIntermediateSnackRouting', suite: 'AmenityRoutingTests.swift', name: '1-to-N Snack Routing & Skill Ceiling', description: 'Selects Shedhorn Grill at 13:15 via blue Africa (112s) and rejects faster black-diamond shortcut Ambush', duration: '0.10ms' },
  { id: 'testTimeGatedClosedVenueExcluded', suite: 'AmenityRoutingTests.swift', name: 'Operating Hours Cutoff (16:00)', description: 'Excludes Shedhorn Grill after 15:30 close and routes down green Mr. K to open Vista Hall Grab & Go', duration: '0.09ms' },
  { id: 'testReservationExclusion', suite: 'AmenityRoutingTests.swift', name: 'Reservation Filter on Walk-In Queries', description: "Skips reservation-only Everett's 8800 (25s away) for grab-and-go snack requests", duration: '0.08ms' },
  { id: 'testWindHoldDetour', suite: 'DynamicOverlayTests.swift', name: 'Ramcharger 8 Wind-Hold Reroute (<5ms)', description: 'Masks lift_ramcharger in RAM without mutating topology.sqlite and detours via Swift Current 6 in 0.092ms', duration: '0.09ms' },
  { id: 'testConcurrentThreadSafeOverlayAccess', suite: 'DynamicOverlayTests.swift', name: 'NSLock Swift 6 StrictConcurrency Stress', description: 'Runs 200 concurrent status reads and writes across DispatchQueue.concurrentPerform with zero data races', duration: '1.40ms' },
  { id: 'testDifficultyCeilingHardConstraint', suite: 'RoutingTests.swift', name: 'Hard Nil Cutoff Above Max Difficulty', description: 'Returns nil when an intermediate skier at Lone Peak Summit has only expert descent terrain (Big Couloir)', duration: '0.06ms' },
  { id: 'testSolverExecutionPerformance', suite: 'RoutingTests.swift', name: 'Multi-Criteria Dijkstra Latency (<10ms)', description: 'Solves 100 iterations over a 305-node, 607-edge mountain fixture in 0.418ms average', duration: '0.42ms' },
  { id: 'testDatabaseInitialization', suite: 'SQLiteConnectionTests.swift', name: 'Read-Only C-SQLite3 & Query-Only Pragma', description: 'Opens topology.sqlite with SQLITE_OPEN_READONLY | SQLITE_OPEN_NOMUTEX and enforces PRAGMA query_only = ON', duration: '0.42ms' },
  { id: 'testOutgoingEdgesQueryPerformance', suite: 'SQLiteConnectionTests.swift', name: 'Prepared Statement Adjacency Cache (<2ms)', description: 'Executes cached getOutgoingEdges over 500 edges in 0.041ms with zero leaked statement pointers', duration: '0.04ms' },
  { id: 'test_golden_intent_case_accuracy', suite: 'test_golden_intent_suite.py', name: '8/8 Golden Voice Transcripts (100% Exact Match)', description: 'Verifies field-by-field parity across snack, patrol, lunch, wind-hold detour, warming hut, chute, and bar intents', duration: '0.12ms' },
  { id: 'test_parser_strips_markdown_fences', suite: 'test_prompt_schema.py', name: 'Fenced & Conversational JSON Sanitizer', description: 'Extracts inner JSON from fenced LLM completions even when surrounding prose contains braces', duration: '0.08ms' },
  { id: 'test_base_lodge_reachability', suite: 'test_graph_integrity.py', name: 'Recursive CTE Summit-to-Base Gatekeeper', description: 'Proves continuous downhill paths from Lone Peak (3,403m) and Andesite (2,682m) to Mountain Village across 3,804 edges', duration: '18ms' },
  { id: 'test_sqlite_schema', suite: 'test_topology.py', name: 'SQLite DDL & Nullable CHECK Constraints', description: 'Validates 3,458 nodes, 3,804 edges, B-tree indexes, and NULL-safe CHECK constraints against TECH_SPEC Section 2.3', duration: '14ms' },
  { id: 'test_mountain_services_table_populated', suite: 'test_services.py', name: 'Idempotent 15-Venue Spatial Snapping', description: 'Verifies all 7 POI categories (including restroom) snap within 25m (2.66m avg) with 0 FK violations', duration: '11ms' },
  { id: 'test_geojson_schema_and_complete_mountain_scale', suite: 'test_fetch.py', name: 'Big Sky GeoJSON Scale & BBox Gate', description: 'Validates 782 Big Sky features (721 pistes, 61 lifts) inside [45.205, -111.490, 45.340, -111.315] with 0 empty difficulties', duration: '19ms' },
];

const BUILD_MILESTONES = [
  { step: 'M1 • STEP 1.1–1.4', title: 'Data Plane & Topology Compiler', detail: '782 GeoJSON features compiled into 3,458 nodes, 3,804 directed edges, and 15 snapped venues with recursive CTE verification.' },
  { step: 'M2 • STEP 2.1–2.2', title: 'On-Device Gemma Intent Schema', detail: '8-field SkiIntent contract, fence-safe JSON parser, and 8/8 golden voice transcripts passing at 100% field accuracy.' },
  { step: 'M3 • STEP 3.1–3.2', title: 'CirqueCore C-SQLite & Dijkstra', detail: 'Read-only C-SQLite3 statement cache (0.041ms lookups) and binary min-heap Dijkstra with hard ability ceilings.' },
  { step: 'M3 • STEP 3.3–3.4', title: 'RAM Overlays & 1-to-N Amenity Router', detail: 'NSLock wind-hold edge masking (0.092ms reroute) and operating-hours 1-to-N multi-target dining search (0.104ms).' },
];

const INITIAL_FEATURE =
  BIG_SKY_FEATURES.find((f) => f.id === 'srv_shedhorn_grill') ?? BIG_SKY_FEATURES[0];

export default function App() {
  const [selectedFeature, setSelectedFeature] = useState<FeatureItem>(INITIAL_FEATURE);
  const [activeTab, setActiveTab] = useState<'map' | 'services' | 'harness' | 'devlog' | 'spec'>('map');
  const [simulatedTime, setSimulatedTime] = useState('13:15');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [copied, setCopied] = useState(false);

  const minLon = -111.460;
  const maxLon = -111.392;
  const minLat = 45.256;
  const maxLat = 45.292;

  const toSvgX = (lon: number) => 60 + ((lon - minLon) / (maxLon - minLon)) * 680;
  const toSvgY = (lat: number) => 440 - ((lat - minLat) / (maxLat - minLat)) * 380;

  const getDifficultyColor = (diff?: string) => {
    switch (diff) {
      case 'novice':
        return '#16a34a';
      case 'intermediate':
        return '#2563eb';
      case 'advanced':
        return '#e2e8f0';
      case 'expert':
      case 'freeride':
        return '#dc2626';
      default:
        return '#94a3b8';
    }
  };

  const copySnippet = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const filteredServices = BIG_SKY_FEATURES.filter((f) => {
    if (f.type !== 'amenity') return false;
    if (categoryFilter !== 'all' && f.category !== categoryFilter) return false;
    return true;
  });

  const isVenueOpen = (item: FeatureItem, timeStr: string) => {
    if (!item.open_time_local || !item.close_time_local) return false;
    return item.open_time_local <= timeStr && timeStr <= item.close_time_local;
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      <header className="border-b border-slate-800 bg-slate-900 sticky top-0 z-50 px-6 py-3.5">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center">
              <Mountain className="h-5 w-5 text-sky-400" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="font-bold text-base text-white tracking-tight">Project Cirque</h1>
                <span className="text-xs px-2 py-0.5 rounded font-mono bg-slate-800 text-slate-300 border border-slate-700">
                  v1.4.0
                </span>
                <span className="text-xs px-2 py-0.5 rounded font-medium bg-emerald-950 text-emerald-300 border border-emerald-800 flex items-center gap-1">
                  <CheckCircle2 className="h-3 w-3" /> Milestones 1–3 Verified
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Big Sky Resort Topology • Swift 6 C-SQLite3 &amp; 1-to-N Dijkstra • Offline Air-Gapped Runtime
              </p>
            </div>
          </div>

          <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-lg border border-slate-800">
            <button
              onClick={() => setActiveTab('map')}
              className={`px-3 py-1.5 rounded text-xs font-medium transition flex items-center gap-1.5 ${
                activeTab === 'map' ? 'bg-sky-700 text-white' : 'text-slate-300 hover:text-white'
              }`}
            >
              <GitBranch className="h-3.5 w-3.5" /> Trail Graph
            </button>
            <button
              onClick={() => setActiveTab('services')}
              className={`px-3 py-1.5 rounded text-xs font-medium transition flex items-center gap-1.5 ${
                activeTab === 'services' ? 'bg-sky-700 text-white' : 'text-slate-300 hover:text-white'
              }`}
            >
              <Utensils className="h-3.5 w-3.5" /> Amenities (15)
            </button>
            <button
              onClick={() => setActiveTab('harness')}
              className={`px-3 py-1.5 rounded text-xs font-medium transition flex items-center gap-1.5 ${
                activeTab === 'harness' ? 'bg-sky-700 text-white' : 'text-slate-300 hover:text-white'
              }`}
            >
              <ShieldCheck className="h-3.5 w-3.5" /> Tests (52/52)
            </button>
            <button
              onClick={() => setActiveTab('devlog')}
              className={`px-3 py-1.5 rounded text-xs font-medium transition flex items-center gap-1.5 ${
                activeTab === 'devlog' ? 'bg-sky-700 text-white' : 'text-slate-300 hover:text-white'
              }`}
            >
              <FileCode className="h-3.5 w-3.5" /> Devlog (Step 3.4)
            </button>
            <button
              onClick={() => setActiveTab('spec')}
              className={`px-3 py-1.5 rounded text-xs font-medium transition flex items-center gap-1.5 ${
                activeTab === 'spec' ? 'bg-sky-700 text-white' : 'text-slate-300 hover:text-white'
              }`}
            >
              <FileText className="h-3.5 w-3.5" /> Build Status
            </button>
          </div>
        </div>
      </header>

      <div className="bg-slate-950 border-b border-slate-800 px-6 py-2">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between text-xs text-slate-300 gap-3">
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1.5 text-slate-400">
              <span className="h-2 w-2 rounded-full bg-emerald-400"></span>
              Completed: <strong className="text-white">STEP_1_1 → STEP_3_4</strong>
            </span>
            <span className="text-slate-700">|</span>
            <span className="text-slate-400">
              Compiled Graph: <strong className="text-slate-200">3,458 nodes • 3,804 edges • 15 services</strong>
            </span>
          </div>

          <div className="flex items-center gap-2 font-mono text-[11px]">
            <span className="bg-slate-900 px-2 py-0.5 rounded border border-slate-800 text-sky-300">
              PRAGMA query_only = ON • 0.104ms 1-to-N Dijkstra
            </span>
            <span className="bg-slate-900 px-2 py-0.5 rounded border border-slate-800 text-emerald-300">
              19/19 Swift XCTests • 33/33 Pytest
            </span>
          </div>
        </div>
      </div>

      <main className="max-w-7xl mx-auto w-full p-6 flex-1 flex flex-col gap-6">
        {activeTab === 'map' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col">
              <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
                <div className="flex items-center gap-2">
                  <Database className="h-4 w-4 text-sky-400" />
                  <h2 className="font-semibold text-sm text-slate-100">
                    Big Sky Corridor Schematic &amp; Snapped Amenities
                  </h2>
                </div>
                <div className="flex flex-wrap items-center gap-3 text-xs text-slate-300">
                  <span className="flex items-center gap-1.5">
                    <span className="h-2.5 w-2.5 rounded-full bg-green-600"></span> Novice
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="h-2.5 w-2.5 rounded-full bg-blue-600"></span> Intermediate
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="h-2.5 w-2.5 bg-slate-200 rotate-45"></span> Advanced
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="h-2.5 w-2.5 bg-red-600 rotate-45"></span> Expert
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="h-0.5 w-3.5 bg-amber-500"></span> Lift
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="h-2.5 w-2.5 rounded-full bg-orange-500"></span> Venue
                  </span>
                </div>
              </div>

              <div className="relative w-full aspect-[16/10] bg-slate-950 rounded-lg border border-slate-800 overflow-hidden flex items-center justify-center">
                <svg viewBox="0 0 800 480" className="w-full h-full select-none">
                  {[120, 200, 280, 360].map((y) => (
                    <line key={y} x1={40} y1={y} x2={760} y2={y} stroke="#1e293b" strokeWidth="1" strokeDasharray="4 4" />
                  ))}

                  {BIG_SKY_FEATURES.filter((f) => f.type === 'piste').map((piste) => {
                    const coords = piste.coords as number[][];
                    const pathD = coords
                      .map((pt, i) => `${i === 0 ? 'M' : 'L'} ${toSvgX(pt[0])} ${toSvgY(pt[1])}`)
                      .join(' ');
                    const isSelected = selectedFeature.id === piste.id;

                    return (
                      <g key={piste.id} className="cursor-pointer" onClick={() => setSelectedFeature(piste)}>
                        {isSelected && (
                          <path
                            d={pathD}
                            fill="none"
                            stroke="#38bdf8"
                            strokeWidth={6.5}
                            strokeOpacity={0.45}
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          />
                        )}
                        <path
                          d={pathD}
                          fill="none"
                          stroke={getDifficultyColor(piste.difficulty)}
                          strokeWidth={isSelected ? 3.5 : 2.2}
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      </g>
                    );
                  })}

                  {BIG_SKY_FEATURES.filter((f) => f.type === 'lift').map((lift) => {
                    const coords = lift.coords as number[][];
                    const pathD = coords
                      .map((pt, i) => `${i === 0 ? 'M' : 'L'} ${toSvgX(pt[0])} ${toSvgY(pt[1])}`)
                      .join(' ');
                    const isSelected = selectedFeature.id === lift.id;

                    return (
                      <g key={lift.id} className="cursor-pointer" onClick={() => setSelectedFeature(lift)}>
                        <path
                          d={pathD}
                          fill="none"
                          stroke="#d97706"
                          strokeWidth={isSelected ? 4.5 : 2.4}
                          strokeDasharray="6 3"
                          strokeLinecap="round"
                        />
                      </g>
                    );
                  })}

                  {BIG_SKY_FEATURES.filter((f) => f.type === 'amenity').map((amenity) => {
                    const pt = amenity.coords as number[];
                    const cx = toSvgX(pt[0]);
                    const cy = toSvgY(pt[1]);
                    const isSelected = selectedFeature.id === amenity.id;

                    return (
                      <g key={amenity.id} className="cursor-pointer" onClick={() => setSelectedFeature(amenity)}>
                        <circle
                          cx={cx}
                          cy={cy}
                          r={isSelected ? 7.5 : 5}
                          fill={isSelected ? '#38bdf8' : '#ea580c'}
                          stroke="#0f172a"
                          strokeWidth="1.5"
                        />
                        {isSelected && (
                          <text x={cx + 10} y={cy + 4} fill="#f8fafc" fontSize="10" fontWeight="600">
                            {amenity.name}
                          </text>
                        )}
                      </g>
                    );
                  })}
                </svg>

                <div className="absolute bottom-3 left-3 bg-slate-900 px-3 py-1.5 rounded border border-slate-800 text-[11px] text-slate-300 flex items-center gap-3">
                  <span>Full Bundle: 721 Pistes • 61 Lifts</span>
                  <span className="text-emerald-400 font-medium">15/15 POIs Snapped (&le; 25m)</span>
                </div>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4">
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                  <div className="text-[11px] text-slate-400">Compiled Graph</div>
                  <div className="text-lg font-bold text-white mt-0.5 font-mono">3,458 / 3,804</div>
                  <div className="text-[10px] text-slate-400 mt-1">Nodes / Directed Edges</div>
                </div>
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                  <div className="text-[11px] text-slate-400">Avg Snap Distance</div>
                  <div className="text-lg font-bold text-sky-400 mt-0.5 font-mono">2.66m</div>
                  <div className="text-[10px] text-slate-400 mt-1">Max 20.12m (15 Venues)</div>
                </div>
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                  <div className="text-[11px] text-slate-400">Wind-Hold Reroute</div>
                  <div className="text-lg font-bold text-amber-400 mt-0.5 font-mono">0.092ms</div>
                  <div className="text-[10px] text-slate-400 mt-1">NSLock RAM Overlay</div>
                </div>
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                  <div className="text-[11px] text-slate-400">1-to-N Snack Search</div>
                  <div className="text-lg font-bold text-emerald-400 mt-0.5 font-mono">0.104ms</div>
                  <div className="text-[10px] text-slate-400 mt-1">Single Min-Heap Pass</div>
                </div>
              </div>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <Layers className="h-4 w-4 text-sky-400" />
                  <h3 className="font-semibold text-sm text-slate-100">Feature Inspector</h3>
                </div>
                <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-200 border border-slate-700">
                  {selectedFeature.category || selectedFeature.difficulty || selectedFeature.aerialway || selectedFeature.type}
                </span>
              </div>

              <div className="bg-slate-950 rounded-lg p-4 border border-slate-800 mb-4">
                <div className="text-base font-bold text-white">{selectedFeature.name}</div>
                <div className="text-xs text-slate-400 font-mono mt-0.5">{selectedFeature.id}</div>

                <div className="mt-4 space-y-2 text-xs">
                  <div className="flex justify-between py-1 border-b border-slate-900">
                    <span className="text-slate-400">Feature Type</span>
                    <span className="font-mono text-slate-200 uppercase">{selectedFeature.type}</span>
                  </div>

                  {selectedFeature.difficulty && (
                    <div className="flex justify-between py-1 border-b border-slate-900">
                      <span className="text-slate-400">Difficulty Rating</span>
                      <span className="font-semibold text-white capitalize">{selectedFeature.difficulty}</span>
                    </div>
                  )}

                  {selectedFeature.grooming && (
                    <div className="flex justify-between py-1 border-b border-slate-900">
                      <span className="text-slate-400">Surface / Grooming</span>
                      <span className="font-mono text-sky-300">{selectedFeature.grooming}</span>
                    </div>
                  )}

                  {selectedFeature.aerialway && (
                    <div className="flex justify-between py-1 border-b border-slate-900">
                      <span className="text-slate-400">Aerialway Class</span>
                      <span className="font-mono text-amber-300">{selectedFeature.aerialway}</span>
                    </div>
                  )}

                  {selectedFeature.startElevM !== undefined && selectedFeature.endElevM !== undefined && (
                    <div className="flex justify-between py-1 border-b border-slate-900">
                      <span className="text-slate-400">Elevation Profile</span>
                      <span className="font-mono text-slate-200">
                        {selectedFeature.startElevM}m → {selectedFeature.endElevM}m ({(selectedFeature.endElevM - selectedFeature.startElevM).toFixed(0)}m)
                      </span>
                    </div>
                  )}

                  {selectedFeature.category && (
                    <div className="flex justify-between py-1 border-b border-slate-900">
                      <span className="text-slate-400">Amenity Category</span>
                      <span className="font-mono text-orange-300">{selectedFeature.category}</span>
                    </div>
                  )}

                  {selectedFeature.service_speed && (
                    <div className="flex justify-between py-1 border-b border-slate-900">
                      <span className="text-slate-400">Service Speed</span>
                      <span className="font-mono text-sky-300">{selectedFeature.service_speed}</span>
                    </div>
                  )}

                  {selectedFeature.open_time_local && (
                    <div className="flex justify-between py-1 border-b border-slate-900">
                      <span className="text-slate-400">Operating Hours</span>
                      <span className="font-mono text-emerald-400">
                        {selectedFeature.open_time_local} – {selectedFeature.close_time_local}
                      </span>
                    </div>
                  )}

                  {selectedFeature.price_tier && (
                    <div className="flex justify-between py-1 border-b border-slate-900">
                      <span className="text-slate-400">Price Tier</span>
                      <span className="font-mono text-amber-400">{selectedFeature.price_tier}</span>
                    </div>
                  )}

                  {selectedFeature.snapping_distance_m !== undefined && (
                    <div className="flex justify-between py-1 border-b border-slate-900">
                      <span className="text-slate-400">Junction Snap Distance</span>
                      <span className="font-mono text-slate-300">{selectedFeature.snapping_distance_m.toFixed(2)}m</span>
                    </div>
                  )}

                  {selectedFeature.assigned_node_id && (
                    <div className="flex justify-between py-1 border-b border-slate-900">
                      <span className="text-slate-400">Snapped Graph Node</span>
                      <span className="font-mono text-sky-400">{selectedFeature.assigned_node_id}</span>
                    </div>
                  )}
                </div>
              </div>

              <div className="flex-1 flex flex-col">
                <div className="text-xs font-semibold text-slate-300 mb-2 flex items-center justify-between">
                  <span>Step 3.4 Multi-Target Query</span>
                  <span className="text-[10px] font-mono text-emerald-400">13:15 MST • .intermediate</span>
                </div>
                <div className="bg-slate-950 p-3.5 rounded-lg border border-slate-800 text-[11px] font-mono text-slate-300 space-y-2 flex-1">
                  <div className="text-sky-400 font-semibold">
                    AmenityRouter.findOptimalAmenityRoute(from: &quot;andesite_summit&quot;)
                  </div>
                  <div className="pl-2 border-l border-slate-800 space-y-1 text-slate-400">
                    <div className="text-emerald-400">✓ Shedhorn Grill (11:00–15:30) • node_jct_0011 • 112.0s</div>
                    <div className="text-emerald-400">✓ Uncle Dan&apos;s Cookie Hut (09:30–15:30) • node_village...</div>
                    <div className="text-slate-500">✕ Everett&apos;s 8800 (requires_reservation = 1)</div>
                  </div>
                  <div className="text-slate-500 text-[10px] mt-2">
                    Click any piste, lift, or venue on the schematic to inspect its compiled record.
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'services' && (
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <div className="flex flex-wrap items-center justify-between gap-4 mb-6 pb-4 border-b border-slate-800">
              <div>
                <h2 className="text-base font-bold text-white flex items-center gap-2">
                  <Utensils className="h-5 w-5 text-orange-400" />
                  Mountain Services Directory (15 Snapped Venues)
                </h2>
                <p className="text-xs text-slate-400 mt-1">
                  Rows from <code className="font-mono text-slate-300">mountain_services</code> with local operating windows and snapped graph vertices.
                </p>
              </div>

              <div className="flex items-center gap-3">
                <div className="flex items-center gap-1.5 bg-slate-950 px-3 py-1.5 rounded border border-slate-800 text-xs">
                  <Clock className="h-3.5 w-3.5 text-sky-400" />
                  <span className="text-slate-400">Local Time:</span>
                  <input
                    type="time"
                    value={simulatedTime}
                    onChange={(e) => setSimulatedTime(e.target.value)}
                    className="bg-transparent text-white font-mono text-xs focus:outline-none cursor-pointer"
                  />
                </div>

                <div className="flex items-center gap-1.5 bg-slate-950 px-3 py-1.5 rounded border border-slate-800 text-xs">
                  <Filter className="h-3.5 w-3.5 text-slate-400" />
                  <select
                    value={categoryFilter}
                    onChange={(e) => setCategoryFilter(e.target.value)}
                    className="bg-slate-950 text-white text-xs focus:outline-none cursor-pointer"
                  >
                    <option value="all">All Categories (15)</option>
                    <option value="quick_snack">Quick Snack</option>
                    <option value="sit_down">Sit Down</option>
                    <option value="cafeteria">Cafeteria</option>
                    <option value="bar">Bar</option>
                    <option value="patrol">Patrol</option>
                    <option value="warming_hut">Warming Hut</option>
                    <option value="restroom">Restroom</option>
                  </select>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredServices.map((service) => {
                const open = isVenueOpen(service, simulatedTime);
                return (
                  <div
                    key={service.id}
                    onClick={() => {
                      setSelectedFeature(service);
                      setActiveTab('map');
                    }}
                    className="bg-slate-950 p-4 rounded-lg border border-slate-800 hover:border-sky-600 cursor-pointer transition flex flex-col justify-between"
                  >
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-bold text-white">{service.name}</span>
                        <span
                          className={`text-[10px] font-bold px-2 py-0.5 rounded font-mono ${
                            open
                              ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                              : 'bg-rose-950 text-rose-400 border border-rose-800'
                          }`}
                        >
                          {open ? 'OPEN' : 'CLOSED'}
                        </span>
                      </div>

                      <div className="space-y-1.5 text-xs text-slate-400">
                        <div className="flex justify-between">
                          <span>Category:</span>
                          <span className="font-mono text-slate-200">{service.category}</span>
                        </div>
                        {service.service_speed && (
                          <div className="flex justify-between">
                            <span>Service Speed:</span>
                            <span className="font-mono text-sky-300">{service.service_speed}</span>
                          </div>
                        )}
                        <div className="flex justify-between">
                          <span>Hours:</span>
                          <span className="font-mono text-slate-300">
                            {service.open_time_local} – {service.close_time_local}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span>Access:</span>
                          <span className="text-slate-300">{service.is_ski_in_only ? 'Ski-In Only' : 'Base Area'}</span>
                        </div>
                      </div>
                    </div>

                    <div className="mt-4 pt-3 border-t border-slate-900 flex items-center justify-between text-[11px]">
                      <span className="font-mono text-slate-400">{service.assigned_node_id}</span>
                      <span className="font-mono text-orange-300">Snap: {service.snapping_distance_m?.toFixed(2)}m</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {activeTab === 'harness' && (
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <div className="flex flex-wrap items-center justify-between gap-4 mb-6 pb-4 border-b border-slate-800">
              <div>
                <div className="flex items-center gap-2">
                  <ShieldCheck className="h-5 w-5 text-emerald-400" />
                  <h2 className="text-base font-bold text-white">Automated Verification Suites (Milestones 1–3)</h2>
                </div>
                <p className="text-xs text-slate-400 mt-1">
                  Commands: <code className="font-mono text-sky-300">swift test --package-path ios/CirqueCore</code> &bull;{' '}
                  <code className="font-mono text-sky-300">uv run --with-requirements requirements.txt pytest -v</code>
                </p>
              </div>
              <span className="text-xs px-3 py-1 rounded bg-emerald-950 text-emerald-300 border border-emerald-800 font-mono font-semibold flex items-center gap-1.5">
                <CheckCircle2 className="h-4 w-4" /> 52 Passed, 0 Failed (19 XCTest + 33 Pytest)
              </span>
            </div>

            <div className="space-y-2.5">
              {HARNESS_TESTS.map((t) => (
                <div
                  key={t.id}
                  className="bg-slate-950 p-3.5 rounded-lg border border-slate-800 flex items-center justify-between gap-4"
                >
                  <div className="flex items-start gap-3">
                    <CheckCircle2 className="h-4 w-4 text-emerald-400 mt-0.5 shrink-0" />
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
                          {t.suite}
                        </span>
                        <span className="text-xs font-mono font-bold text-sky-300">{t.id}</span>
                        <span className="text-xs text-slate-200 font-medium">{t.name}</span>
                      </div>
                      <p className="text-xs text-slate-400 mt-0.5">{t.description}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 shrink-0">
                    <span className="text-xs font-mono text-slate-400">{t.duration}</span>
                    <span className="text-xs px-2 py-0.5 rounded font-mono font-bold bg-emerald-950 text-emerald-400 border border-emerald-800">
                      PASSED
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'devlog' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <FileCode className="h-4 w-4 text-sky-400" />
                  <h3 className="font-semibold text-sm text-slate-100">
                    .cirque/devlog/M3_MOBILE_ROUTING_CORE/step_3_4.json
                  </h3>
                </div>
                <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950 px-2 py-0.5 rounded border border-emerald-800">
                  STEP_3_4 PASSED
                </span>
              </div>
              <pre className="bg-slate-950 p-4 rounded-lg border border-slate-800 text-xs font-mono text-slate-300 overflow-y-auto max-h-[500px]">
                {`{
  "step_id": "STEP_3_4",
  "milestone_id": "M3_MOBILE_ROUTING_CORE",
  "title": "Time-Gated Amenity & Multi-Target Routing",
  "status": "PASSED",
  "algorithm": "SQLite Index Filter + Single-Pass 1-to-N Min-Heap Dijkstra",
  "verification_metrics": {
    "intermediate_snack_routing_1315": {
      "origin": "andesite_summit",
      "selected_venue_id": "srv_shedhorn_grill",
      "resolved_edges": ["trail_africa"],
      "weighted_cost_seconds": 112.0,
      "black_or_expert_runs_included": 0
    },
    "time_gated_late_afternoon_1600": {
      "excluded_closed_venue": "srv_shedhorn_grill (closes 15:30)",
      "selected_venue_id": "srv_vista_hall_grab_go",
      "resolved_edges": ["trail_mr_k"],
      "weighted_cost_seconds": 224.0
    },
    "benchmarks_ms": {
      "resolve_candidate_venues_avg_ms": 0.0301,
      "multi_target_dijkstra_avg_ms": 0.1035,
      "latency_budget_ms": 10.0
    }
  }
}`}
              </pre>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Share2 className="h-4 w-4 text-sky-400" />
                  <h3 className="font-semibold text-sm text-slate-100">
                    Engineering Notes (Steps 3.1–3.4)
                  </h3>
                </div>
                <button
                  onClick={() =>
                    copySnippet(
                      `1-to-N Multi-Target Dijkstra with Operating-Hours Filters at Big Sky\n\n1. Read-Only C-SQLite3 Cache: CirqueDatabase opens topology.sqlite with SQLITE_OPEN_READONLY | SQLITE_OPEN_NOMUTEX and PRAGMA query_only = ON, reusing compiled OpaquePointer statements for 0.041 ms adjacency lookups.\n2. NSLock RAM Overlays: 5-minute wind holds and patrol closures stay in DynamicOverlayManager in RAM, rerouting around a wind-held Ramcharger 8 via Swift Current 6 in 0.092 ms without touching SQLite.\n3. Single-Pass 1-to-N Amenity Search: AmenityRouter filters mountain_services by local operating hours and reservation flags first, then pops the lowest-cost reachable venue from one binary min-heap pass in 0.104 ms while enforcing maxDifficulty.`
                    )
                  }
                  className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-xs text-slate-200 flex items-center gap-1 transition"
                >
                  {copied ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
                  {copied ? 'Copied' : 'Copy Notes'}
                </button>
              </div>

              <div className="bg-slate-950 p-5 rounded-lg border border-slate-800 text-xs text-slate-300 space-y-3 leading-relaxed flex-1">
                <div className="font-bold text-sm text-white">
                  1-to-N Multi-Target Dijkstra with Operating-Hours Filters at Big Sky
                </div>
                <p className="text-slate-400">
                  <strong className="text-sky-400">1. Read-Only C-SQLite3 Cache:</strong> `CirqueDatabase` opens
                  `topology.sqlite` with `SQLITE_OPEN_READONLY | SQLITE_OPEN_NOMUTEX` and `PRAGMA query_only = ON`,
                  resetting cached `OpaquePointer` statements for 0.041 ms adjacency reads.
                </p>
                <p className="text-slate-400">
                  <strong className="text-sky-400">2. In-Memory Wind-Hold Masking:</strong> `DynamicOverlayManager`
                  keeps patrol closures and lift holds in an `NSLock`-guarded dictionary in RAM, rerouting around a
                  wind-held Ramcharger 8 via Swift Current 6 in 0.092 ms.
                </p>
                <p className="text-slate-400">
                  <strong className="text-sky-400">3. Single-Heap 1-to-N Dining Search:</strong> `AmenityRouter`
                  filters `mountain_services` by local mountain hours (`13:15` vs. `16:00`) and reservation rules
                  before expanding one binary min-heap in 0.104 ms, rejecting black-diamond shortcuts when
                  `maxDifficulty = .intermediate`.
                </p>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'spec' && (
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <h2 className="text-base font-bold text-white mb-1">Project Cirque Build Plan Status</h2>
            <p className="text-xs text-slate-400">
              Milestones 1 through 3 are verified on Linux/macOS toolchains; Milestone 4 (Voice &amp; Audio Turn-by-Turn Synthesis) is next.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mt-4">
              {BUILD_MILESTONES.map((item) => (
                <div key={item.step} className="p-4 rounded-lg border border-emerald-800/80 bg-slate-950">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-mono font-bold text-emerald-400">{item.step}</span>
                    <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800">
                      COMPLETED
                    </span>
                  </div>
                  <h4 className="font-semibold text-xs text-white">{item.title}</h4>
                  <p className="text-[11px] text-slate-400 mt-1.5 leading-relaxed">{item.detail}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
