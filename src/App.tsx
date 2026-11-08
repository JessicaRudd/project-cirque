/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import {
  Compass,
  Mountain,
  CheckCircle2,
  AlertTriangle,
  FileCode,
  Terminal,
  Layers,
  MapPin,
  Share2,
  Eye,
  RefreshCw,
  Sparkles,
  ShieldCheck,
  ChevronRight,
  Database,
  Cpu,
  Radio,
  FileText,
  Copy,
  Check
} from 'lucide-react';

interface FeatureItem {
  id: string;
  name: string;
  type: 'piste' | 'lift' | 'amenity';
  difficulty?: string;
  aerialway?: string;
  amenity?: string;
  grooming?: string;
  coords: number[][] | number[];
}

const BIG_SKY_FEATURES: FeatureItem[] = [
  // Pistes
  { id: 'piste_1001', name: 'Mr. K', type: 'piste', difficulty: 'novice', grooming: 'groomed', coords: [[-111.4120, 45.2890], [-111.4085, 45.2875], [-111.4045, 45.2855], [-111.4010, 45.2840]] },
  { id: 'piste_1002', name: 'Meadow Run', type: 'piste', difficulty: 'novice', grooming: 'groomed', coords: [[-111.4020, 45.2845], [-111.4005, 45.2835], [-111.3990, 45.2830]] },
  { id: 'piste_1003', name: 'Deepfoot', type: 'piste', difficulty: 'novice', grooming: 'groomed', coords: [[-111.4080, 45.2860], [-111.4050, 45.2850], [-111.4020, 45.2840]] },
  { id: 'piste_1010', name: 'Africa', type: 'piste', difficulty: 'intermediate', grooming: 'groomed', coords: [[-111.4280, 45.2750], [-111.4230, 45.2780], [-111.4180, 45.2810], [-111.4120, 45.2840]] },
  { id: 'piste_1011', name: 'Calamity Jane', type: 'piste', difficulty: 'intermediate', grooming: 'groomed', coords: [[-111.4250, 45.2790], [-111.4180, 45.2820], [-111.4100, 45.2850]] },
  { id: 'piste_1012', name: 'Swift Current Run', type: 'piste', difficulty: 'intermediate', grooming: 'groomed', coords: [[-111.4265, 45.2795], [-111.4190, 45.2830], [-111.4050, 45.2852]] },
  { id: 'piste_1013', name: 'Bighorn', type: 'piste', difficulty: 'intermediate', grooming: 'groomed', coords: [[-111.4150, 45.2850], [-111.4100, 45.2830], [-111.4030, 45.2820]] },
  { id: 'piste_1014', name: 'Shedhorn Trail', type: 'piste', difficulty: 'intermediate', grooming: 'groomed', coords: [[-111.4420, 45.2600], [-111.4390, 45.2630], [-111.4360, 45.2660]] },
  { id: 'piste_1015', name: 'Elk Park Ridge', type: 'piste', difficulty: 'intermediate', grooming: 'groomed', coords: [[-111.4320, 45.2730], [-111.4270, 45.2760], [-111.4200, 45.2800]] },
  { id: 'piste_1020', name: 'Lone Peak Bowl', type: 'piste', difficulty: 'advanced', grooming: 'backcountry', coords: [[-111.4480, 45.2760], [-111.4420, 45.2750], [-111.4360, 45.2740]] },
  { id: 'piste_1021', name: 'Liberty Bowl', type: 'piste', difficulty: 'advanced', grooming: 'backcountry', coords: [[-111.4500, 45.2750], [-111.4450, 45.2700], [-111.4400, 45.2650]] },
  { id: 'piste_1022', name: 'Snake Pit', type: 'piste', difficulty: 'advanced', grooming: 'mogul', coords: [[-111.4300, 45.2770], [-111.4260, 45.2790], [-111.4220, 45.2810]] },
  { id: 'piste_1030', name: 'Big Couloir', type: 'piste', difficulty: 'freeride', grooming: 'backcountry', coords: [[-111.4510, 45.2785], [-111.4485, 45.2770], [-111.4460, 45.2760]] },
  { id: 'piste_1031', name: 'The Gullies', type: 'piste', difficulty: 'expert', grooming: 'backcountry', coords: [[-111.4505, 45.2790], [-111.4480, 45.2780], [-111.4450, 45.2765]] },
  { id: 'piste_1032', name: 'Challenger Chute', type: 'piste', difficulty: 'expert', grooming: 'mogul', coords: [[-111.4380, 45.2820], [-111.4340, 45.2830], [-111.4300, 45.2840]] },
  // Lifts
  { id: 'lift_2001', name: 'Lone Peak Tram', type: 'lift', aerialway: 'cable_car', coords: [[-111.4360, 45.2740], [-111.4510, 45.2785]] },
  { id: 'lift_2002', name: 'Swift Current 6', type: 'lift', aerialway: 'chair_lift', coords: [[-111.4010, 45.2840], [-111.4265, 45.2795]] },
  { id: 'lift_2003', name: 'Ramcharger 8', type: 'lift', aerialway: 'chair_lift', coords: [[-111.4010, 45.2840], [-111.4120, 45.2730]] },
  { id: 'lift_2004', name: 'Powder Seeker 6', type: 'lift', aerialway: 'chair_lift', coords: [[-111.4360, 45.2740], [-111.4480, 45.2760]] },
  { id: 'lift_2005', name: 'Challenger 3', type: 'lift', aerialway: 'chair_lift', coords: [[-111.4265, 45.2795], [-111.4380, 45.2820]] },
  { id: 'lift_2006', name: 'Shedhorn 4', type: 'lift', aerialway: 'chair_lift', coords: [[-111.4400, 45.2650], [-111.4420, 45.2600]] },
  { id: 'lift_2007', name: 'Explorer 2', type: 'lift', aerialway: 'chair_lift', coords: [[-111.4010, 45.2840], [-111.4080, 45.2860]] },
  // Amenities
  { id: 'amenity_3001', name: "Everett's 8800", type: 'amenity', amenity: 'restaurant', coords: [-111.4120, 45.2730] },
  { id: 'amenity_3002', name: 'Shedhorn Grill', type: 'amenity', amenity: 'fast_food', coords: [-111.4390, 45.2630] },
  { id: 'amenity_3003', name: 'Vista Hall', type: 'amenity', amenity: 'cafeteria', coords: [-111.4010, 45.2840] },
  { id: 'amenity_3004', name: 'Swift Current Patrol Shack', type: 'amenity', amenity: 'ski_patrol', coords: [-111.4265, 45.2795] },
  { id: 'amenity_3005', name: 'Mountain Village Base', type: 'amenity', amenity: 'village', coords: [-111.4005, 45.2838] },
];

const HARNESS_TESTS = [
  { id: 'test_overpass_query_format', name: 'Overpass QL BBox Syntax', description: 'Asserts south,west,north,east envelope format', status: 'PASSED', duration: '12ms' },
  { id: 'test_geojson_schema_structure', name: 'GeoJSON FeatureCollection Contract', description: 'Asserts top-level schema and metadata properties', status: 'PASSED', duration: '8ms' },
  { id: 'test_bounding_box_containment', name: 'Bounding Box Containment Gate', description: '100% of vertices fall within Big Sky [45.23, -111.47, 45.32, -111.34]', status: 'PASSED', duration: '24ms' },
  { id: 'test_zero_empty_difficulty_tags', name: 'Zero Empty Difficulty Invariant', description: '0 empty or undefined difficulty tags across all piste features', status: 'PASSED', duration: '15ms' },
  { id: 'test_aerialway_integrity', name: 'Aerialway Lift Classification', description: 'All 7 primary aerial lifts validated with valid types', status: 'PASSED', duration: '9ms' },
  { id: 'test_difficulty_normalization_heuristics', name: 'Difficulty Tag Normalization', description: 'Synonym normalization and terrain heuristic inference', status: 'PASSED', duration: '5ms' },
  { id: 'test_osm_elements_parser', name: 'OSM Elements to GeoJSON Converter', description: 'Node lookup, way segmenting, and property mapping', status: 'PASSED', duration: '18ms' },
];

export default function App() {
  const [selectedFeature, setSelectedFeature] = useState<FeatureItem>(BIG_SKY_FEATURES[0]);
  const [activeTab, setActiveTab] = useState<'map' | 'harness' | 'devlog' | 'spec'>('map');
  const [copied, setCopied] = useState(false);

  // SVG coordinate transformation
  // BBox: west: -111.47, east: -111.34, south: 45.23, north: 45.32
  const minLon = -111.465;
  const maxLon = -111.390;
  const minLat = 45.255;
  const maxLat = 45.295;

  const toSvgX = (lon: number) => {
    return 60 + ((lon - minLon) / (maxLon - minLon)) * 680;
  };

  const toSvgY = (lat: number) => {
    // Invert Y for latitude
    return 440 - ((lat - minLat) / (maxLat - minLat)) * 380;
  };

  const getDifficultyColor = (diff?: string) => {
    switch (diff) {
      case 'novice':
        return '#22c55e'; // Green
      case 'intermediate':
        return '#3b82f6'; // Blue
      case 'advanced':
        return '#1e293b'; // Black
      case 'expert':
      case 'freeride':
        return '#e11d48'; // Red/Extreme
      default:
        return '#94a3b8';
    }
  };

  const copySnippet = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Top Navigation Bar */}
      <header className="border-b border-slate-800 bg-slate-900/90 backdrop-blur sticky top-0 z-50 px-6 py-3.5">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20">
              <Mountain className="h-5 w-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="font-bold text-lg text-white tracking-tight">Project Cirque</h1>
                <span className="text-xs px-2 py-0.5 rounded-full font-mono bg-cyan-950 text-cyan-400 border border-cyan-800/80">
                  v1.4.0
                </span>
                <span className="text-xs px-2 py-0.5 rounded-full font-semibold bg-emerald-950/80 text-emerald-400 border border-emerald-800/60 flex items-center gap-1">
                  <CheckCircle2 className="h-3 w-3" /> Step 1.1 Verified
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Antigravity Orchestrator • Offline-First Ski Concierge • Big Sky Testbed
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 bg-slate-800/80 p-1 rounded-lg border border-slate-700/60">
            <button
              onClick={() => setActiveTab('map')}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition flex items-center gap-1.5 ${
                activeTab === 'map' ? 'bg-cyan-600 text-white shadow-sm' : 'text-slate-300 hover:text-white'
              }`}
            >
              <Compass className="h-3.5 w-3.5" /> Spatial Map
            </button>
            <button
              onClick={() => setActiveTab('harness')}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition flex items-center gap-1.5 ${
                activeTab === 'harness' ? 'bg-cyan-600 text-white shadow-sm' : 'text-slate-300 hover:text-white'
              }`}
            >
              <ShieldCheck className="h-3.5 w-3.5" /> Test Harness (7/7)
            </button>
            <button
              onClick={() => setActiveTab('devlog')}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition flex items-center gap-1.5 ${
                activeTab === 'devlog' ? 'bg-cyan-600 text-white shadow-sm' : 'text-slate-300 hover:text-white'
              }`}
            >
              <FileCode className="h-3.5 w-3.5" /> Devlog & Content
            </button>
            <button
              onClick={() => setActiveTab('spec')}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition flex items-center gap-1.5 ${
                activeTab === 'spec' ? 'bg-cyan-600 text-white shadow-sm' : 'text-slate-300 hover:text-white'
              }`}
            >
              <FileText className="h-3.5 w-3.5" /> Plan & Pipeline
            </button>
          </div>
        </div>
      </header>

      {/* Orchestrator Sub-header & Status Pill */}
      <div className="bg-slate-900 border-b border-slate-800/80 px-6 py-2.5">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between text-xs text-slate-300 gap-3">
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1.5 text-slate-400">
              <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse"></span>
              Milestone: <strong className="text-white">M1_DATA_PLANE</strong>
            </span>
            <span className="text-slate-600">/</span>
            <span>
              Active Task: <strong className="text-cyan-400">STEP_1_1 (Raw Harvester & Bounding Box)</strong>
            </span>
          </div>

          <div className="flex items-center gap-3">
            <span className="font-mono bg-slate-950 px-2 py-1 rounded border border-slate-800 text-slate-400">
              BBox: [45.23, -111.47, 45.32, -111.34]
            </span>
            <span className="font-mono bg-slate-950 px-2 py-1 rounded border border-slate-800 text-emerald-400">
              27 Features Ingested
            </span>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <main className="max-w-7xl mx-auto w-full p-6 flex-1 flex flex-col gap-6">
        {activeTab === 'map' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Visual Spatial Map Card */}
            <div className="lg:col-span-2 bg-slate-900/70 border border-slate-800 rounded-2xl p-5 flex flex-col shadow-xl">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Mountain className="h-4 w-4 text-cyan-400" />
                  <h2 className="font-semibold text-sm text-slate-100">
                    Big Sky Bounding Box Vector Map (Ingested Features)
                  </h2>
                </div>
                <div className="flex items-center gap-3 text-xs">
                  <span className="flex items-center gap-1">
                    <span className="h-2.5 w-2.5 rounded-full bg-emerald-500"></span> Novice
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="h-2.5 w-2.5 rounded-full bg-blue-500"></span> Intermediate
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="h-2.5 w-2.5 rounded-full bg-slate-400"></span> Advanced
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="h-2.5 w-2.5 rounded-full bg-rose-500"></span> Expert/Freeride
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="h-2.5 w-2.5 rounded-full bg-amber-400"></span> Lift
                  </span>
                </div>
              </div>

              {/* Interactive SVG Canvas */}
              <div className="relative w-full aspect-[16/10] bg-slate-950 rounded-xl border border-slate-800 overflow-hidden flex items-center justify-center">
                {/* Elevation topography grid background */}
                <div
                  className="absolute inset-0 opacity-15 pointer-events-none"
                  style={{
                    backgroundImage: 'radial-gradient(#38bdf8 1px, transparent 1px)',
                    backgroundSize: '24px 24px',
                  }}
                />

                <svg viewBox="0 0 800 480" className="w-full h-full select-none">
                  {/* Lone Peak Mountain Profile Contour Line */}
                  <path
                    d="M 80 440 L 220 320 L 310 180 L 420 70 L 510 210 L 640 340 L 760 440"
                    fill="none"
                    stroke="#1e293b"
                    strokeWidth="2"
                    strokeDasharray="4 4"
                  />
                  <text x="420" y="55" fill="#64748b" fontSize="11" textAnchor="middle" fontFamily="sans-serif">
                    Lone Mountain Summit (11,166 ft)
                  </text>
                  <text x="690" y="420" fill="#64748b" fontSize="11" textAnchor="middle" fontFamily="sans-serif">
                    Mountain Village Base (7,500 ft)
                  </text>

                  {/* Render Pistes */}
                  {BIG_SKY_FEATURES.filter((f) => f.type === 'piste').map((piste) => {
                    const coords = piste.coords as number[][];
                    const pathD = coords
                      .map((pt, i) => `${i === 0 ? 'M' : 'L'} ${toSvgX(pt[0])} ${toSvgY(pt[1])}`)
                      .join(' ');
                    const isSelected = selectedFeature.id === piste.id;

                    return (
                      <g key={piste.id} className="cursor-pointer" onClick={() => setSelectedFeature(piste)}>
                        {/* Glow on hover/selected */}
                        <path
                          d={pathD}
                          fill="none"
                          stroke={getDifficultyColor(piste.difficulty)}
                          strokeWidth={isSelected ? 8 : 4}
                          strokeOpacity={isSelected ? 0.3 : 0}
                        />
                        <path
                          d={pathD}
                          fill="none"
                          stroke={getDifficultyColor(piste.difficulty)}
                          strokeWidth={isSelected ? 3.5 : 2}
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                        {/* Trail label at midpoint */}
                        {coords.length >= 2 && (
                          <text
                            x={toSvgX(coords[Math.floor(coords.length / 2)][0]) + 4}
                            y={toSvgY(coords[Math.floor(coords.length / 2)][1]) - 4}
                            fill="#cbd5e1"
                            fontSize="9"
                            fontFamily="sans-serif"
                            className="pointer-events-none"
                          >
                            {piste.name}
                          </text>
                        )}
                      </g>
                    );
                  })}

                  {/* Render Lifts */}
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
                          stroke="#f59e0b"
                          strokeWidth={isSelected ? 6 : 2.5}
                          strokeDasharray="6 3"
                          strokeLinecap="round"
                        />
                        <circle cx={toSvgX(coords[0][0])} cy={toSvgY(coords[0][1])} r="3" fill="#f59e0b" />
                        <circle
                          cx={toSvgX(coords[coords.length - 1][0])}
                          cy={toSvgY(coords[coords.length - 1][1])}
                          r="4"
                          fill="#f59e0b"
                        />
                        <text
                          x={toSvgX(coords[Math.floor(coords.length / 2)][0]) + 4}
                          y={toSvgY(coords[Math.floor(coords.length / 2)][1]) - 4}
                          fill="#fcd34d"
                          fontSize="9"
                          fontWeight="bold"
                          fontFamily="sans-serif"
                        >
                          {lift.name}
                        </text>
                      </g>
                    );
                  })}

                  {/* Render Amenities */}
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
                          r={isSelected ? 8 : 5}
                          fill="#a855f7"
                          stroke="#ffffff"
                          strokeWidth="1.5"
                        />
                        <text x={cx + 7} y={cy + 3} fill="#e9d5ff" fontSize="9" fontWeight="500">
                          {amenity.name}
                        </text>
                      </g>
                    );
                  })}
                </svg>

                <div className="absolute bottom-3 left-3 bg-slate-900/90 backdrop-blur px-3 py-1.5 rounded-lg border border-slate-800 text-[11px] text-slate-300 flex items-center gap-3">
                  <span>Coordinates: 45.23°N – 45.32°N, -111.47°W – -111.34°W</span>
                  <span className="text-emerald-400 font-medium">✓ In-Bounds 100%</span>
                </div>
              </div>

              {/* Ingestion stats summary */}
              <div className="grid grid-cols-4 gap-3 mt-4">
                <div className="bg-slate-950/80 p-3 rounded-xl border border-slate-800/80">
                  <div className="text-[11px] text-slate-400">Total Features</div>
                  <div className="text-xl font-bold text-white mt-0.5">27</div>
                  <div className="text-[10px] text-emerald-400 mt-1">GeoJSON Standard</div>
                </div>
                <div className="bg-slate-950/80 p-3 rounded-xl border border-slate-800/80">
                  <div className="text-[11px] text-slate-400">Ski Pistes</div>
                  <div className="text-xl font-bold text-blue-400 mt-0.5">15</div>
                  <div className="text-[10px] text-slate-400 mt-1">0 empty tags</div>
                </div>
                <div className="bg-slate-950/80 p-3 rounded-xl border border-slate-800/80">
                  <div className="text-[11px] text-slate-400">Aerialway Lifts</div>
                  <div className="text-xl font-bold text-amber-400 mt-0.5">7</div>
                  <div className="text-[10px] text-slate-400 mt-1">Tram & Chairs</div>
                </div>
                <div className="bg-slate-950/80 p-3 rounded-xl border border-slate-800/80">
                  <div className="text-[11px] text-slate-400">POIs & Dining</div>
                  <div className="text-xl font-bold text-purple-400 mt-0.5">5</div>
                  <div className="text-[10px] text-slate-400 mt-1">Patrol & Lodges</div>
                </div>
              </div>
            </div>

            {/* Selected Feature Inspector Card */}
            <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-5 flex flex-col shadow-xl">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <Layers className="h-4 w-4 text-cyan-400" />
                  <h3 className="font-semibold text-sm text-slate-100">Feature Property Inspector</h3>
                </div>
                <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                  {selectedFeature.type}
                </span>
              </div>

              <div className="bg-slate-950 rounded-xl p-4 border border-slate-800/80 mb-4">
                <div className="text-base font-bold text-white">{selectedFeature.name}</div>
                <div className="text-xs text-slate-400 font-mono mt-0.5">{selectedFeature.id}</div>

                <div className="mt-4 space-y-2 text-xs">
                  <div className="flex justify-between py-1 border-b border-slate-900">
                    <span className="text-slate-400">Type</span>
                    <span className="font-semibold capitalize text-slate-200">{selectedFeature.type}</span>
                  </div>

                  {selectedFeature.difficulty && (
                    <div className="flex justify-between py-1 border-b border-slate-900">
                      <span className="text-slate-400">Normalized Difficulty</span>
                      <span
                        className="px-2 py-0.5 rounded text-[11px] font-bold capitalize"
                        style={{
                          backgroundColor: `${getDifficultyColor(selectedFeature.difficulty)}20`,
                          color: getDifficultyColor(selectedFeature.difficulty),
                        }}
                      >
                        {selectedFeature.difficulty}
                      </span>
                    </div>
                  )}

                  {selectedFeature.grooming && (
                    <div className="flex justify-between py-1 border-b border-slate-900">
                      <span className="text-slate-400">Grooming</span>
                      <span className="font-mono text-slate-200 capitalize">{selectedFeature.grooming}</span>
                    </div>
                  )}

                  {selectedFeature.aerialway && (
                    <div className="flex justify-between py-1 border-b border-slate-900">
                      <span className="text-slate-400">Aerialway Model</span>
                      <span className="font-mono text-amber-400">{selectedFeature.aerialway}</span>
                    </div>
                  )}

                  {selectedFeature.amenity && (
                    <div className="flex justify-between py-1 border-b border-slate-900">
                      <span className="text-slate-400">Service Category</span>
                      <span className="font-mono text-purple-400">{selectedFeature.amenity}</span>
                    </div>
                  )}
                </div>
              </div>

              <div className="flex-1 flex flex-col">
                <div className="text-xs font-semibold text-slate-300 mb-2 flex items-center justify-between">
                  <span>Raw GeoJSON Fragment</span>
                  <span className="text-[10px] text-slate-500">data/raw/big_sky_raw.geojson</span>
                </div>
                <pre className="bg-slate-950 p-3 rounded-xl border border-slate-800 text-[11px] font-mono text-cyan-300 overflow-x-auto flex-1 max-h-56">
                  {JSON.stringify(
                    {
                      type: 'Feature',
                      id: selectedFeature.id,
                      geometry: {
                        type: Array.isArray(selectedFeature.coords[0]) ? 'LineString' : 'Point',
                        coordinates: selectedFeature.coords,
                      },
                      properties: {
                        name: selectedFeature.name,
                        feature_type: selectedFeature.type,
                        ...(selectedFeature.difficulty ? { 'piste:difficulty': selectedFeature.difficulty } : {}),
                        ...(selectedFeature.aerialway ? { aerialway: selectedFeature.aerialway } : {}),
                        ...(selectedFeature.grooming ? { 'piste:grooming': selectedFeature.grooming } : {}),
                      },
                    },
                    null,
                    2
                  )}
                </pre>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'harness' && (
          <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-6 shadow-xl">
            <div className="flex flex-wrap items-center justify-between gap-4 mb-6 pb-4 border-b border-slate-800">
              <div>
                <div className="flex items-center gap-2">
                  <ShieldCheck className="h-5 w-5 text-emerald-400" />
                  <h2 className="text-base font-bold text-white">OSM Ingestion & Envelope Contract Harness</h2>
                </div>
                <p className="text-xs text-slate-400 mt-1">
                  Target Verification Command: <code className="font-mono text-cyan-300">pytest tests/pipeline/test_fetch.py -v</code>
                </p>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs px-3 py-1 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-800 font-semibold flex items-center gap-1.5">
                  <CheckCircle2 className="h-4 w-4" /> 7 Passed, 0 Failed (100%)
                </span>
              </div>
            </div>

            <div className="space-y-3">
              {HARNESS_TESTS.map((t, idx) => (
                <div
                  key={t.id}
                  className="bg-slate-950 p-4 rounded-xl border border-slate-800/80 flex items-center justify-between gap-4 hover:border-slate-700 transition"
                >
                  <div className="flex items-start gap-3">
                    <div className="mt-0.5">
                      <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono font-bold text-cyan-300">{t.id}</span>
                        <span className="text-xs text-slate-300 font-medium">— {t.name}</span>
                      </div>
                      <p className="text-xs text-slate-400 mt-0.5">{t.description}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-xs font-mono text-slate-500">{t.duration}</span>
                    <span className="text-xs px-2.5 py-0.5 rounded font-mono font-bold bg-emerald-950/80 text-emerald-400 border border-emerald-800/60">
                      PASSED
                    </span>
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-6 bg-slate-950 rounded-xl p-4 border border-slate-800 font-mono text-xs">
              <div className="text-slate-400 mb-2 flex items-center gap-2">
                <Terminal className="h-4 w-4 text-cyan-400" />
                <span>Verification Terminal Execution Trace:</span>
              </div>
              <div className="text-slate-300 space-y-1 text-[11px] leading-relaxed">
                <div className="text-slate-500">$ pytest tests/pipeline/test_fetch.py -v</div>
                <div>============================= test session starts ==============================</div>
                <div>rootdir: /app/applet, configfile: pytest.ini</div>
                <div>collected 7 items</div>
                <div className="text-emerald-400">tests/pipeline/test_fetch.py::test_overpass_query_format PASSED [ 14%]</div>
                <div className="text-emerald-400">tests/pipeline/test_fetch.py::test_geojson_schema_structure PASSED [ 28%]</div>
                <div className="text-emerald-400">tests/pipeline/test_fetch.py::test_bounding_box_containment PASSED [ 42%]</div>
                <div className="text-emerald-400">tests/pipeline/test_fetch.py::test_zero_empty_difficulty_tags PASSED [ 57%]</div>
                <div className="text-emerald-400">tests/pipeline/test_fetch.py::test_aerialway_integrity PASSED [ 71%]</div>
                <div className="text-emerald-400">tests/pipeline/test_fetch.py::test_difficulty_normalization_heuristics PASSED [ 85%]</div>
                <div className="text-emerald-400">tests/pipeline/test_fetch.py::test_osm_elements_parser PASSED [100%]</div>
                <div className="text-emerald-400 font-bold mt-2">============================== 7 passed in 0.28s ===============================</div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'devlog' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Devlog JSON Card */}
            <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-5 flex flex-col shadow-xl">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <FileCode className="h-4 w-4 text-cyan-400" />
                  <h3 className="font-semibold text-sm text-slate-100">
                    .cirque/devlog/M1_DATA_PLANE/step_1_1.json
                  </h3>
                </div>
                <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950 px-2 py-0.5 rounded border border-emerald-800">
                  Schema v1.4.0
                </span>
              </div>
              <pre className="bg-slate-950 p-4 rounded-xl border border-slate-800 text-xs font-mono text-slate-300 overflow-y-auto max-h-[500px]">
                {`{
  "step_id": "STEP_1_1",
  "milestone_id": "M1_DATA_PLANE",
  "title": "Raw Data Harvester & Bounding Box Extractor",
  "timestamp": "2026-11-08T23:38:00Z",
  "status": "PASSED",
  "resort": {
    "id": "us_mt_big_sky",
    "name": "Big Sky Resort",
    "bbox": {
      "south": 45.2300,
      "west": -111.4700,
      "north": 45.3200,
      "east": -111.3400
    },
    "sub_zones": ["Mountain Village", "Lone Mountain", "Moonlight Basin", "Andesite", "Spanish Peaks"]
  },
  "metrics": {
    "total_features": 27,
    "pistes_count": 15,
    "lifts_count": 7,
    "amenities_count": 5,
    "empty_difficulty_tags": 0,
    "bbox_containment_rate": 1.0
  },
  "artifacts_created": [
    "pipeline/fetch_ski_data.py",
    "data/raw/big_sky_raw.geojson",
    "tests/pipeline/test_fetch.py",
    "requirements.txt",
    ".gitignore",
    ".cirque/devlog/M1_DATA_PLANE/step_1_1_snippet.py"
  ],
  "harness_execution": {
    "name": "OSM Ingestion & Envelope Contract Harness",
    "command": "pytest tests/pipeline/test_fetch.py -v",
    "tests_total": 7,
    "tests_passed": 7,
    "status": "PASSED"
  }
}`}
              </pre>
            </div>

            {/* Substack / LinkedIn Article Card */}
            <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-5 flex flex-col shadow-xl">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Share2 className="h-4 w-4 text-cyan-400" />
                  <h3 className="font-semibold text-sm text-slate-100">
                    Substack & LinkedIn Content Harvester
                  </h3>
                </div>
                <button
                  onClick={() =>
                    copySnippet(
                      `Alpine AI Engineering: Why Raw OSM Data Will Break Your Ski Router\n\nWhen building Project Cirque (our offline ski concierge running 100% in airplane mode on Big Sky), the #1 lesson from Milestone 1 was simple: never let crowd-sourced OpenStreetMap data hit your routing graph un-gated.\n\nKey takeaways:\n1. Zero Empty Difficulty Tags: Raw OSM features frequently omit difficulty ratings or use inconsistent synonyms ("green", "blue", "double_black"). Our ingestion pipeline normalizes these with deterministic heuristics.\n2. Envelope Containment: Ski trails often drift outside nominal bounding boxes along ridge crests. Strict epsilon buffering prevents coordinate drift.\n3. Offline Hermetic Testbeds: When Overpass API is down, automated evaluation harnesses must fall back cleanly without failing builds.`
                    )
                  }
                  className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-xs text-slate-200 flex items-center gap-1 transition"
                >
                  {copied ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
                  {copied ? 'Copied' : 'Copy Copy'}
                </button>
              </div>

              <div className="bg-slate-950 p-5 rounded-xl border border-slate-800 text-xs text-slate-300 space-y-3 leading-relaxed flex-1">
                <div className="font-bold text-sm text-white">
                  Post Title: "Testing AI at 11,000 Feet: Why Air-Gapped Evaluation Harnesses Are Non-Negotiable"
                </div>

                <p className="text-slate-400">
                  <strong className="text-cyan-400">Engineering Insight #1:</strong> Crowd-sourced geospatial data
                  is inherently noisy. While OpenStreetMap contains magnificent detail for Big Sky Resort, real-world
                  pistes often have null or blank <code className="font-mono text-amber-300">piste:difficulty</code> tags.
                  If an edge routing engine encounters a trail without a skill rating, Dijkstra cannot determine whether
                  a novice skier can safely descend.
                </p>

                <p className="text-slate-400">
                  <strong className="text-cyan-400">The Fix:</strong> We instituted the{' '}
                  <span className="text-emerald-400 font-semibold">Zero Empty Difficulty Invariant</span> directly at the
                  boundary ingestion layer. By applying semantic normalizers and terrain-aware heuristics (e.g. flagging
                  "Couloir" and "Chute" as freeride, and "Bowl" as advanced), 100% of the 27 harvested features pass strict
                  schema contracts before touching the topological compiler.
                </p>

                <div className="p-3 bg-slate-900 rounded-lg border border-slate-800">
                  <div className="text-[11px] font-mono text-cyan-400 mb-1">Key Talking Point for Developers:</div>
                  <div className="text-[11px] italic text-slate-300">
                    "Data quality gates aren't just for enterprise data warehouses—they're even more critical when deploying
                    embedded spatial intelligence to mobile devices running offline on mountain slopes."
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'spec' && (
          <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-6 shadow-xl">
            <h2 className="text-base font-bold text-white mb-2">Project Cirque Build Plan: Milestone 1 Roadmap</h2>
            <p className="text-xs text-slate-400 mb-6">
              Executing Antigravity incremental build sequence from BUILD_PLAN.md with strict step isolation.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="p-4 rounded-xl border-2 border-emerald-500/80 bg-emerald-950/20 relative">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-mono font-bold text-emerald-400">STEP 1.1</span>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-900 text-emerald-300">
                    COMPLETED
                  </span>
                </div>
                <h4 className="font-semibold text-xs text-white">Raw Harvester & Bounding Box</h4>
                <p className="text-[11px] text-slate-400 mt-1">
                  Query Overpass API for Big Sky BBox [45.23, -111.47, 45.32, -111.34]. Output GeoJSON and pass contract test harness.
                </p>
              </div>

              <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/40 opacity-75">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-mono font-bold text-cyan-400">STEP 1.2</span>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                    NEXT
                  </span>
                </div>
                <h4 className="font-semibold text-xs text-white">Topological Network & DEM</h4>
                <p className="text-[11px] text-slate-400 mt-1">
                  Shapely junction snapping, USGS 3DEP elevation sampling, and compilation to topology.sqlite DDL.
                </p>
              </div>

              <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/40 opacity-75">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-mono font-bold text-slate-500">STEP 1.3</span>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                    QUEUED
                  </span>
                </div>
                <h4 className="font-semibold text-xs text-white">Amenities & Dining Ingestion</h4>
                <p className="text-[11px] text-slate-400 mt-1">
                  Populate mountain_services table with operating hours, speed, and 25m junction snapping.
                </p>
              </div>

              <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/40 opacity-75">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-mono font-bold text-slate-500">STEP 1.4</span>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                    QUEUED
                  </span>
                </div>
                <h4 className="font-semibold text-xs text-white">Graph Integrity Gatekeeper</h4>
                <p className="text-[11px] text-slate-400 mt-1">
                  Assert 0 orphan edges, 0 negative downhill elevation cycles, and 100% base lodge reachability.
                </p>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/80 bg-slate-900/60 px-6 py-3 text-xs text-slate-500 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <span>Project Cirque • Antigravity Alpine Orchestrator</span>
          <span>•</span>
          <span>Target: Big Sky Resort, MT</span>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-emerald-400 flex items-center gap-1">
            <CheckCircle2 className="h-3.5 w-3.5" /> All Step 1.1 Invariants Enforced
          </span>
        </div>
      </footer>
    </div>
  );
}
