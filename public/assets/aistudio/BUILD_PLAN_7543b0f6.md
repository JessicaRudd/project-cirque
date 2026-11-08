Project Cirque: Antigravity Incremental Build Plan & Evaluation Harness Architecture
Document Version: 1.4.0
Target Environment: Antigravity CLI (agy) Execution & Xcode 27+ / iOS 18+
Target Testbed: Big Sky Resort, Montana (Bounding Box: 45.23, -111.47, 45.32, -111.34)
Parent Specification: TECH_SPEC.md (Version 1.3.0)


________________


1. Executive Summary & Orchestration Strategy
Project Cirque is an asymmetric, offline-first spatial intelligence ski concierge designed to operate entirely in airplane mode on-mountain while relying on a cloud compilation plane (Google Cloud Run + AlloyDB + Cloud CDN) for packaging immutable resort data bundles.


To execute this build reliably within Antigravity without overflowing LLM context windows or introducing regressions, the project is structured into 6 isolated milestones comprising 18 atomic, self-contained micro-tasks.
Context Isolation Contract
Every micro-task executes in a clean, sandboxed Antigravity CLI session (agy --sandbox). A task receives only its explicitly declared input artifacts and an isolated priming prompt. A task is considered complete only when its dedicated verification harness passes.
Continuous Content & Telemetry Harvesting
Each task automatically logs test runs, benchmarks, code snippets, visual graph plots, and troubleshooting notes into .cirque/devlog/{MILESTONE_ID}/. This systematically prepares technical deep-dives for Substack, LinkedIn carousels, and an end-to-end conference tech talk and demo.


________________


2. Testing & Evaluation Harness Taxonomy
To guarantee safety, zero regressions, and complete air-gapped autonomy, testing and evaluation harnesses are first-class architectural components in this build plan:


1. Spatial Data Integrity Harness (scripts/verify_graph_integrity.sql, tests/pipeline/test_graph_integrity.py):


   * Asserts 0 orphan vertices, 0 isolated components, 0 dead-end transfer edges.
   * Strictly enforces slope vector polarity (ensuring downhill ski runs never have inverted negative-elevation cycles).
   * Validates that all mountain base lodges maintain 100% reachability from summit peaks.


2. SLM Golden Intent & Accuracy Harness (tests/slm/test_golden_intent_suite.py):


   * Benchmarks quantized Gemma (2B/4B) across an exhaustive test fixture of realistic ski voice queries (regular navigation, snack routing, wind hold detours, emergency ski patrol dispatch).
   * Enforces 100% schema extraction accuracy on required JSON keys (destination_type, max_difficulty, amenity_filter, urgency).
   * Measures token throughput, memory footprint, and cold-start inference latency.


3. Terrain & Safety Dijkstra Routing Harness (Tests/CirqueCoreTests/RoutingTests.swift):


   * Direct headless testing of Swift C-SQLite Dijkstra solver.
   * Asserts terrain difficulty constraints (e.g. intermediate skier queries cannot contain black or double-black edges).
   * Injects synthetic wind-hold and lift closure dynamic overlays to assert in-memory rerouting without mutating underlying immutable SQLite bundles.


4. Air-Gapped Socket Leak Harness (tests/ios/test_app_intent_offline.swift):


   * Intercepts SiriKit AppIntent execution and monitors system socket descriptors.
   * Enforces an invariant: 0 network calls, 0 background telemetry pings, and 0 external DNS lookups during the entire voice-query-to-audio-guidance loop.


5. Cloud CDN Edge & Checksum Contract Harness (tests/cloud/test_api_endpoints.py):


   * Validates HTTP response headers: immutable 1-year caching for .sqlite packages and max 180s TTL for ephemeral dynamic overlays.
   * Validates SHA-256 manifest integrity against Google Cloud Storage buckets.


6. Air-Gapped Golden Path E2E Benchmark Harness (tests/e2e/test_offline_golden_path.py):


   * End-to-end integration test executing the complete pipeline in synthetic airplane mode.
   * Enforces an end-to-end timing budget: total latency from voice query to first synthesized audio frame must be under 1.5 seconds.


________________


3. Dedicated Content Series: "Engineering the Alpine AI Harness"
A dedicated Substack article and LinkedIn carousel will focus exclusively on how these evaluation harnesses were engineered:


* Title: "Testing AI at 11,000 Feet: Why Air-Gapped Evaluation Harnesses Are Non-Negotiable"
* Key Themes:
   1. The Ski Graph Invariant: Why standard Dijkstra fails when lifts only go up and skiers only go down, and how SQL assertions prevent fatal routing bugs.
   2. Testing Without Sockets: How we built an automated test harness to prove zero network requests occur during Siri voice execution.
   3. Benchmarking Edge SLMs: Building a Golden Intent Suite to ensure Gemma 2B extracts structured JSON under 400ms on Apple Silicon.


________________


4. Machine-Readable Antigravity Build Plan (build_plan.json)
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "project": "Project Cirque",
  "version": "1.4.0",
  "target_environment": {
    "orchestrator": "Antigravity CLI (agy)",
    "mobile_runtime": "Xcode 27+ / iOS 18+ / Swift 6",
    "cloud_runtime": "Google Cloud Run / AlloyDB / GCS",
    "testbed": "Big Sky Resort, Montana (45.23, -111.47, 45.32, -111.34)"
  },
  "devlog_root": ".cirque/devlog",
  "milestones": [
    {
      "milestone_id": "M1_DATA_PLANE",
      "title": "Ingestion & Topological Graph Pipeline",
      "content_theme": "Spatial Data Engineering: From OpenStreetMap Vectors to Offline Directed Graphs",
      "harness_focus": "Topological Data Quality & Graph Integrity Harnesses",
      "steps": [
        {
          "step_id": "STEP_1_1",
          "title": "Raw Data Harvester & Bounding Box Extractor",
          "isolated_context_prompt": "Task: Implement pipeline/fetch_ski_data.py to ingest Big Sky vector geometries from OpenSkiData and Overpass API (OSM) for bounding box [45.23, -111.47, 45.32, -111.34], cross-referencing Skimap.org boundaries. Save output as data/raw/big_sky_raw.geojson. Add unit tests in tests/pipeline/test_fetch.py verifying coordinate envelope and essential attributes (aerialway, piste:type, piste:difficulty). Log output summary to .cirque/devlog/M1_DATA_PLANE/step_1_1.json.",
          "input_artifacts": ["TECH_SPEC.md (Section 2.1)"],
          "deliverables": [
            "pipeline/fetch_ski_data.py",
            "data/raw/big_sky_raw.geojson",
            "tests/pipeline/test_fetch.py"
          ],
          "harness": {
            "name": "OSM Ingestion & Envelope Contract Harness",
            "command": "pytest tests/pipeline/test_fetch.py -v",
            "pass_criteria": "100% valid polygon/linestring geometries within Big Sky bounding box; 0 empty difficulty tags."
          },
          "content_harvesting": {
            "sublines": "Substack / LinkedIn Data Bite",
            "artifacts_to_save": [
              ".cirque/devlog/M1_DATA_PLANE/step_1_1_snippet.py",
              ".cirque/devlog/M1_DATA_PLANE/big_sky_bbox_map.png"
            ],
            "talking_points": [
              "Cleaning real-world OSM aerialway & piste tags",
              "Handling malformed coordinates and boundary edge cases"
            ]
          }
        },
        {
          "step_id": "STEP_1_2",
          "title": "Topological Network Compiler & Elevation Sampler",
          "isolated_context_prompt": "Task: Implement pipeline/build_topology.py using Shapely and GeoPandas. Intersect trail lines and lift segments into discrete junction nodes. Compute slope gradient, vertical drop, and distance using USGS 3DEP elevation data. Insert virtual walk/skate transfer edges. Output compiled topology.sqlite conforming to DDL Section 2.3. Write tests/pipeline/test_topology.py verifying graph connectivity and elevation consistency. Log output summary to .cirque/devlog/M1_DATA_PLANE/step_1_2.json.",
          "input_artifacts": [
            "data/raw/big_sky_raw.geojson",
            "TECH_SPEC.md (Section 2.2 & 2.3)"
          ],
          "deliverables": [
            "pipeline/build_topology.py",
            "data/compiled/topology.sqlite",
            "tests/pipeline/test_topology.py"
          ],
          "harness": {
            "name": "Topological Network & Elevation Verification Harness",
            "command": "pytest tests/pipeline/test_topology.py -v",
            "pass_criteria": "All junctions properly snapped; DEM elevations correctly interpolated; transfer edges created between lift summits and trails."
          },
          "content_harvesting": {
            "sublines": "Technical deep dive: Directed Graph Compilation",
            "artifacts_to_save": [
              ".cirque/devlog/M1_DATA_PLANE/graph_junction_logic.py",
              ".cirque/devlog/M1_DATA_PLANE/elevation_profile_chart.png"
            ],
            "talking_points": [
              "Splitting shared trails into true routing edges",
              "Adding virtual transfer links between lift top-stations and trailheads"
            ]
          }
        },
        {
          "step_id": "STEP_1_3",
          "title": "On-Mountain Amenities & Services Ingestion",
          "isolated_context_prompt": "Task: Implement pipeline/ingest_mountain_services.py to scrape and ingest Big Sky dining venues (e.g. Shedhorn Grill, Vista Hall, Everett's 8800), warming huts, and ski patrol shacks. Populate table 'mountain_services' in topology.sqlite with service_type, service_tier, and operational_hours. Write tests/pipeline/test_services.py validating service node coordinates snap to valid graph junctions. Log summary to .cirque/devlog/M1_DATA_PLANE/step_1_3.json.",
          "input_artifacts": [
            "data/compiled/topology.sqlite",
            "TECH_SPEC.md (Section 1 & 2.3)"
          ],
          "deliverables": [
            "pipeline/ingest_mountain_services.py",
            "tests/pipeline/test_services.py"
          ],
          "harness": {
            "name": "Amenity Junction Snapping & Operating Hours Harness",
            "command": "pytest tests/pipeline/test_services.py -v",
            "pass_criteria": "All dining and patrol points of interest snap to existing graph vertices within a 25-meter radius."
          },
          "content_harvesting": {
            "sublines": "Data modeling for spatial services",
            "artifacts_to_save": [
              ".cirque/devlog/M1_DATA_PLANE/services_schema.sql",
              ".cirque/devlog/M1_DATA_PLANE/amenities_distribution.png"
            ],
            "talking_points": [
              "Snapping real-world POIs to nearest navigable network vertices",
              "Structuring time-gated amenities for lunch and safety routing"
            ]
          }
        },
        {
          "step_id": "STEP_1_4",
          "title": "Graph Integrity Verification Suite",
          "isolated_context_prompt": "Task: Create scripts/verify_graph_integrity.sql and python test runner tests/pipeline/test_graph_integrity.py. Validate: (1) 0 orphan edges, (2) 0 negative slope elevation cycles on ski runs, (3) reachability of all base lodges from mountain peaks. Export graph validation metrics. Save output to .cirque/devlog/M1_DATA_PLANE/step_1_4_integrity_report.json.",
          "input_artifacts": [
            "data/compiled/topology.sqlite",
            "TECH_SPEC.md (Section 6 & Stage 1.4)"
          ],
          "deliverables": [
            "scripts/verify_graph_integrity.sql",
            "tests/pipeline/test_graph_integrity.py",
            ".cirque/devlog/M1_DATA_PLANE/step_1_4_integrity_report.json"
          ],
          "harness": {
            "name": "Comprehensive Graph Topology & Reachability Gatekeeper",
            "command": "pytest tests/pipeline/test_graph_integrity.py -v",
            "pass_criteria": "Zero orphan edges, zero negative slope gravity violations on runs, 100% reachability to mountain base."
          },
          "content_harvesting": {
            "sublines": "Data Quality as a First-Class Citizen in Spatial AI",
            "artifacts_to_save": [
              ".cirque/devlog/M1_DATA_PLANE/integrity_queries.sql",
              ".cirque/devlog/M1_DATA_PLANE/subgraph_reachability_diagram.png"
            ],
            "talking_points": [
              "Why standard graph algorithms break when ski lifts travel uphill and skiers travel downhill",
              "Automated data quality gates before packaging mobile SQLite bundles"
            ]
          }
        }
      ]
    },
    {
      "milestone_id": "M2_LOCAL_SLM",
      "title": "On-Device Gemma Intent Engine",
      "content_theme": "Edge AI: Structured JSON Intent Extraction with Quantized Gemma Models",
      "harness_focus": "SLM Schema Extraction & Golden Benchmark Evaluation Harnesses",
      "steps": [
        {
          "step_id": "STEP_2_1",
          "title": "SLM Intent Parser Harness & Prompt Contracts",
          "isolated_context_prompt": "Task: Implement slm/gemma_intent_parser.py providing a clean interface for quantized Gemma (2B/4B) via llama.cpp or Core ML. Define strict prompt templates and JSON output schema enforcing fields: destination_type, max_difficulty, preference_tags, amenity_filter, and urgency. Add mock mode for CI testing. Write tests/slm/test_prompt_schema.py. Log results to .cirque/devlog/M2_LOCAL_SLM/step_2_1.json.",
          "input_artifacts": ["TECH_SPEC.md (Section 3.1 & Stage 2)"],
          "deliverables": [
            "slm/gemma_intent_parser.py",
            "slm/schemas/intent_schema.json",
            "tests/slm/test_prompt_schema.py"
          ],
          "harness": {
            "name": "JSON Schema Conformance & Grammar Harness",
            "command": "pytest tests/slm/test_prompt_schema.py -v",
            "pass_criteria": "All model completions strictly parse into typed Intent dataclass with zero missing keys."
          },
          "content_harvesting": {
            "sublines": "Constraining SLMs to Strict JSON Schemas",
            "artifacts_to_save": [
              ".cirque/devlog/M2_LOCAL_SLM/gemma_system_prompt.txt",
              ".cirque/devlog/M2_LOCAL_SLM/sample_raw_vs_parsed_intent.json"
            ],
            "talking_points": [
              "Prompt engineering for tiny models without hallucinations",
              "Enforcing JSON grammar constraints at inference time"
            ]
          }
        },
        {
          "step_id": "STEP_2_2",
          "title": "Golden Intent Test Suite & Benchmark Evaluation",
          "isolated_context_prompt": "Task: Implement tests/slm/test_golden_intent_suite.py containing all benchmark prompts from Section 3.2 (e.g., 'Find me a scenic blue groomer to Mountain Village', 'I need a fast burger near Shedhorn without double blacks', 'Emergency: knee injury on Swift Current'). Assert 100% extraction accuracy and benchmark token latency. Save benchmark report to .cirque/devlog/M2_LOCAL_SLM/step_2_2_benchmark.json.",
          "input_artifacts": [
            "slm/gemma_intent_parser.py",
            "TECH_SPEC.md (Section 3.2)"
          ],
          "deliverables": [
            "tests/slm/test_golden_intent_suite.py",
            ".cirque/devlog/M2_LOCAL_SLM/step_2_2_benchmark.json"
          ],
          "harness": {
            "name": "Golden Intent Evaluation & Latency Benchmark Suite",
            "command": "pytest tests/slm/test_golden_intent_suite.py -v -s",
            "pass_criteria": "100% field accuracy on golden prompt suite; inference latency < 450ms on M-series / Apple Silicon."
          },
          "content_harvesting": {
            "sublines": "Benchmarking Small Language Models on Edge Hardware",
            "artifacts_to_save": [
              ".cirque/devlog/M2_LOCAL_SLM/accuracy_confusion_matrix.png",
              ".cirque/devlog/M2_LOCAL_SLM/inference_speed_chart.png"
            ],
            "talking_points": [
              "Achieving 100% field accuracy on domain-specific ski queries",
              "Inference latency vs. parameter size trade-offs (2B vs 4B)"
            ]
          }
        }
      ]
    },
    {
      "milestone_id": "M3_MOBILE_ROUTING_CORE",
      "title": "Embedded Graph Solver & Dynamic Status Overlay",
      "content_theme": "High-Performance Mobile C++/Swift Graph Algorithms: Weighted Dijkstra with Real-Time Constraints",
      "harness_focus": "Headless Swift Routing & Dynamic Terrain Simulation Harnesses",
      "steps": [
        {
          "step_id": "STEP_3_1",
          "title": "CirqueCore Swift Package & SQLite Connection Wrapper",
          "isolated_context_prompt": "Task: Initialize Swift Package at ios/CirqueCore. Implement Database/SQLiteConnection.swift providing direct, low-overhead C-SQLite bindings in WAL mode. Load topology.sqlite and implement query helpers for vertices, edges, and mountain_services. Write Tests/CirqueCoreTests/SQLiteConnectionTests.swift. Log test run to .cirque/devlog/M3_MOBILE_ROUTING_CORE/step_3_1.json.",
          "input_artifacts": [
            "data/compiled/topology.sqlite",
            "TECH_SPEC.md (Section 2.3 & Stage 3.1)"
          ],
          "deliverables": [
            "ios/CirqueCore/Package.swift",
            "ios/CirqueCore/Sources/CirqueCore/Database/SQLiteConnection.swift",
            "ios/CirqueCore/Tests/CirqueCoreTests/SQLiteConnectionTests.swift"
          ],
          "harness": {
            "name": "C-SQLite Zero-Overhead Memory & Query Harness",
            "command": "swift test --package-path ios/CirqueCore --filter SQLiteConnectionTests",
            "pass_criteria": "Database opens in WAL mode; edge/vertex queries execute in under 2ms; zero memory leaks."
          },
          "content_harvesting": {
            "sublines": "Zero-Overhead Offline SQLite in Swift",
            "artifacts_to_save": [
              ".cirque/devlog/M3_MOBILE_ROUTING_CORE/sqlite_binding_snippet.swift",
              ".cirque/devlog/M3_MOBILE_ROUTING_CORE/db_read_benchmarks.txt"
            ],
            "talking_points": [
              "Why direct C-SQLite bindings beat heavy ORMs for real-time mobile pathfinding",
              "Memory footprint and query execution times under 2ms"
            ]
          }
        },
        {
          "step_id": "STEP_3_2",
          "title": "Multi-Criteria Dijkstra Graph Solver",
          "isolated_context_prompt": "Task: Implement Routing/CirqueGraphSolver.swift inside ios/CirqueCore. Implement weighted Dijkstra/A* routing supporting: (1) difficulty ceiling penalties, (2) dynamic edge exclusion (closed runs/lifts), and (3) grooming priority weighting. Write Tests/CirqueCoreTests/RoutingTests.swift with TestSwiftCurrentToEveretts() asserting novice/intermediate exclusivity. Log benchmark to .cirque/devlog/M3_MOBILE_ROUTING_CORE/step_3_2.json.",
          "input_artifacts": [
            "ios/CirqueCore/Sources/CirqueCore/Database/SQLiteConnection.swift",
            "TECH_SPEC.md (Section 3.1 & Stage 3.2)"
          ],
          "deliverables": [
            "ios/CirqueCore/Sources/CirqueCore/Routing/CirqueGraphSolver.swift",
            "ios/CirqueCore/Tests/CirqueCoreTests/RoutingTests.swift"
          ],
          "harness": {
            "name": "Difficulty Exclusivity & Cost Function Routing Harness",
            "command": "swift test --package-path ios/CirqueCore --filter RoutingTests",
            "pass_criteria": "TestSwiftCurrentToEveretts() resolves 100% through Novice/Intermediate trails; 0 black runs included."
          },
          "content_harvesting": {
            "sublines": "Building a Terrain-Aware Routing Engine",
            "artifacts_to_save": [
              ".cirque/devlog/M3_MOBILE_ROUTING_CORE/dijkstra_cost_function.swift",
              ".cirque/devlog/M3_MOBILE_ROUTING_CORE/computed_ski_path.png"
            ],
            "talking_points": [
              "Formulating edge weights for ski terrain: vertical drop vs distance vs skier ability",
              "Preventing accidental routing into double black chutes"
            ]
          }
        },
        {
          "step_id": "STEP_3_3",
          "title": "Dynamic Delta Status Overlay Engine",
          "isolated_context_prompt": "Task: Implement Routing/DynamicOverlayManager.swift inside ios/CirqueCore. Handle live status overlays (open/hold/closed) applied directly to in-memory graph edge weights without mutating the underlying SQLite bundle. Write unit test TestWindHoldDetour() verifying that when Ramcharger 8 is on wind hold, the solver detours via Swift Current 6. Log results to .cirque/devlog/M3_MOBILE_ROUTING_CORE/step_3_3.json.",
          "input_artifacts": [
            "ios/CirqueCore/Sources/CirqueCore/Routing/CirqueGraphSolver.swift",
            "TECH_SPEC.md (Stage 3.2)"
          ],
          "deliverables": [
            "ios/CirqueCore/Sources/CirqueCore/Routing/DynamicOverlayManager.swift",
            "ios/CirqueCore/Tests/CirqueCoreTests/DynamicOverlayTests.swift"
          ],
          "harness": {
            "name": "Dynamic Lift Closure & Weather Reroute Harness",
            "command": "swift test --package-path ios/CirqueCore --filter DynamicOverlayTests",
            "pass_criteria": "TestWindHoldDetour() cleanly redirects route around Ramcharger 8 within 5ms of overlay application."
          },
          "content_harvesting": {
            "sublines": "Dynamic Graph Edge Masking in Memory",
            "artifacts_to_save": [
              ".cirque/devlog/M3_MOBILE_ROUTING_CORE/wind_hold_reroute_diff.txt",
              ".cirque/devlog/M3_MOBILE_ROUTING_CORE/reroute_comparison_map.png"
            ],
            "talking_points": [
              "Handling alpine weather disruptions without invalidating immutable base maps",
              "Instant sub-second rerouting on the mountain"
            ]
          }
        },
        {
          "step_id": "STEP_3_4",
          "title": "Time-Gated Amenity & Multi-Target Routing",
          "isolated_context_prompt": "Task: Implement Routing/AmenityRouter.swift inside ios/CirqueCore. Filter open venues by operating hours, select the optimal venue based on parsed intent tags (e.g., 'lunch', 'warming hut'), and solve for the optimal path adhering to skier ability. Write TestIntermediateSnackRouting() asserting grab-and-go snack routing avoids black terrain. Log summary to .cirque/devlog/M3_MOBILE_ROUTING_CORE/step_3_4.json.",
          "input_artifacts": [
            "ios/CirqueCore/Sources/CirqueCore/Routing/CirqueGraphSolver.swift",
            "TECH_SPEC.md (Stage 3.3)"
          ],
          "deliverables": [
            "ios/CirqueCore/Sources/CirqueCore/Routing/AmenityRouter.swift",
            "ios/CirqueCore/Tests/CirqueCoreTests/AmenityRoutingTests.swift"
          ],
          "harness": {
            "name": "Temporal Venue Filter & Multi-Destination Routing Harness",
            "command": "swift test --package-path ios/CirqueCore --filter AmenityRoutingTests",
            "pass_criteria": "TestIntermediateSnackRouting() selects open grab-and-go venue and creates route adhering to skier ability limits."
          },
          "content_harvesting": {
            "sublines": "Multi-Target Pathfinding with Temporal Constraints",
            "artifacts_to_save": [
              ".cirque/devlog/M3_MOBILE_ROUTING_CORE/amenity_routing_sample.swift",
              ".cirque/devlog/M3_MOBILE_ROUTING_CORE/shedhorn_vs_everetts_decision.png"
            ],
            "talking_points": [
              "Solving Dijkstra across multiple candidate targets simultaneously",
              "Evaluating trail difficulty vs operating hours in real-time"
            ]
          }
        }
      ]
    },
    {
      "milestone_id": "M4_VOICE_AUDIO_RUNTIME",
      "title": "On-Device SiriKit & Audio Navigation",
      "content_theme": "Audio UX: Hands-Free Ski Concierge with SiriKit App Intents and Bluetooth Audio",
      "harness_focus": "Speech Synthesis Contracts & Network Air-Gap Leak Harnesses",
      "steps": [
        {
          "step_id": "STEP_4_1",
          "title": "Audio Guidance Coordinator",
          "isolated_context_prompt": "Task: Implement Audio/AudioGuidanceCoordinator.swift inside ios/CirqueCore wrapping AVSpeechSynthesizer. Generate concise, natural ski navigation callouts (e.g. 'Bear right onto Mr. K, stay left past the beginner bypass, Ramcharger chair is 300 yards ahead'). Add unit tests in Tests/CirqueCoreTests/AudioGuidanceTests.swift with audio phrase formatting assertions. Log summary to .cirque/devlog/M4_VOICE_AUDIO_RUNTIME/step_4_1.json.",
          "input_artifacts": [
            "ios/CirqueCore/Sources/CirqueCore/Routing/CirqueGraphSolver.swift",
            "TECH_SPEC.md (Section 1 & Stage 3.1)"
          ],
          "deliverables": [
            "ios/CirqueCore/Sources/CirqueCore/Audio/AudioGuidanceCoordinator.swift",
            "ios/CirqueCore/Tests/CirqueCoreTests/AudioGuidanceTests.swift"
          ],
          "harness": {
            "name": "Audio Guidance Callout & Formatter Harness",
            "command": "swift test --package-path ios/CirqueCore --filter AudioGuidanceTests",
            "pass_criteria": "Phrasing generator produces valid turn-by-turn prompts matching trail names and distances under 15 words."
          },
          "content_harvesting": {
            "sublines": "Designing Audio UX for High-Speed Cold Weather Sports",
            "artifacts_to_save": [
              ".cirque/devlog/M4_VOICE_AUDIO_RUNTIME/turn_by_turn_sample_phrases.txt",
              ".cirque/devlog/M4_VOICE_AUDIO_RUNTIME/audio_coordinator_snippet.swift"
            ],
            "talking_points": [
              "Why screens are useless at -10°F with ski gloves on",
              "Synthesizing turn-by-turn guidance with minimal cognitive load"
            ]
          }
        },
        {
          "step_id": "STEP_4_2",
          "title": "SiriKit AppIntent Pipeline Integration",
          "isolated_context_prompt": "Task: Create ios/CirqueApp and implement Intents/GetSkiRouteIntent.swift conforming to AppIntent. Wire the user voice prompt into local Gemma parsing, trigger CirqueGraphSolver, and pipe audio instructions into AudioGuidanceCoordinator. Implement offline mock harness tests/ios/test_app_intent_offline.swift asserting 0 network sockets open during execution. Log report to .cirque/devlog/M4_VOICE_AUDIO_RUNTIME/step_4_2.json.",
          "input_artifacts": [
            "ios/CirqueCore/Sources/CirqueCore",
            "slm/gemma_intent_parser.py",
            "TECH_SPEC.md (Stage 4.1 & 4.2)"
          ],
          "deliverables": [
            "ios/CirqueApp/Intents/GetSkiRouteIntent.swift",
            "ios/CirqueApp/Intents/CirqueShortcutsProvider.swift",
            "tests/ios/test_app_intent_offline.swift"
          ],
          "harness": {
            "name": "Air-Gapped Socket Leak & AppIntent Execution Harness",
            "command": "swift test --package-path ios/CirqueApp --filter OfflineIntentTests",
            "pass_criteria": "Zero network socket activity detected; full invocation executes offline end-to-end."
          },
          "content_harvesting": {
            "sublines": "Building Air-Gapped Siri Shortcuts with On-Device AI",
            "artifacts_to_save": [
              ".cirque/devlog/M4_VOICE_AUDIO_RUNTIME/app_intent_snippet.swift",
              ".cirque/devlog/M4_VOICE_AUDIO_RUNTIME/siri_activation_flowchart.png"
            ],
            "talking_points": [
              "Integrating SiriKit AppIntents without relying on Apple cloud servers",
              "Passing voice prompts directly into local Core ML execution"
            ]
          }
        }
      ]
    },
    {
      "milestone_id": "M5_CLOUD_SERVICES",
      "title": "Cloud Run Services, Compiler & Live Telemetry",
      "content_theme": "Cloud Architecture: Zero-Idle Cloud Run & Global Edge CDN Distribution",
      "harness_focus": "HTTP API Schema Contracts & Cache Invalidation Harnesses",
      "steps": [
        {
          "step_id": "STEP_5_1",
          "title": "Cloud Run API Service (FastAPI / Go)",
          "isolated_context_prompt": "Task: Implement cloud/cirque-api providing: GET /v1/resorts, GET /v1/resorts/{id}/manifest, and GET /v1/resorts/{id}/overlay. Include Dockerfile and local docker-compose setup. Implement tests/cloud/test_api_endpoints.py asserting response schemas, cache headers (immutable for manifests, 180s for overlays), and SHA-256 checksum validation. Log output to .cirque/devlog/M5_CLOUD_SERVICES/step_5_1.json.",
          "input_artifacts": ["TECH_SPEC.md (Section 7.1 & 7.2)"],
          "deliverables": [
            "cloud/cirque-api/main.py",
            "cloud/cirque-api/Dockerfile",
            "tests/cloud/test_api_endpoints.py"
          ],
          "harness": {
            "name": "Cloud Run API Contract & Cache Header Verification Harness",
            "command": "pytest tests/cloud/test_api_endpoints.py -v",
            "pass_criteria": "Manifest endpoints return HTTP 200 with SHA-256 checksums and immutable Cache-Control; overlay returns 180s TTL."
          },
          "content_harvesting": {
            "sublines": "Serving Immutable Offline Packs from Cloud Run",
            "artifacts_to_save": [
              ".cirque/devlog/M5_CLOUD_SERVICES/fastapi_manifest_routes.py",
              ".cirque/devlog/M5_CLOUD_SERVICES/cache_header_headers.txt"
            ],
            "talking_points": [
              "Designing immutable client package manifests with SHA-256 integrity",
              "Leveraging Cloud CDN edge caching to minimize origin load"
            ]
          }
        },
        {
          "step_id": "STEP_5_2",
          "title": "Batch Compiler Job & Telemetry Sync Worker",
          "isolated_context_prompt": "Task: Implement cloud/cirque-compiler/job.py and cloud/telemetry-sync/worker.py. The compiler runs spatial validation, packages .sqlite + manifest, and uploads to gs://cirque-mountain-packs/. The telemetry worker scrapes Liftie on a 5-minute cron and pushes JSON status deltas. Write tests/cloud/test_sync_worker.py with mock Liftie responses. Log metrics to .cirque/devlog/M5_CLOUD_SERVICES/step_5_2.json.",
          "input_artifacts": [
            "pipeline/build_topology.py",
            "TECH_SPEC.md (Section 7.1 & 7.3)"
          ],
          "deliverables": [
            "cloud/cirque-compiler/job.py",
            "cloud/telemetry-sync/worker.py",
            "tests/cloud/test_sync_worker.py"
          ],
          "harness": {
            "name": "Telemetry Ingestion & Delta Calculation Harness",
            "command": "pytest tests/cloud/test_sync_worker.py -v",
            "pass_criteria": "Scraper correctly computes JSON status diff from raw Liftie HTML fixtures; zero unhandled network retries."
          },
          "content_harvesting": {
            "sublines": "Automating Heavy Spatial Compiles with Cloud Run Jobs",
            "artifacts_to_save": [
              ".cirque/devlog/M5_CLOUD_SERVICES/liftie_scraper_snippet.py",
              ".cirque/devlog/M5_CLOUD_SERVICES/compiler_job_spec.yaml"
            ],
            "talking_points": [
              "Batch processing spatial networks in serverless containers",
              "Diffing lift status events to broadcast minimal payloads"
            ]
          }
        },
        {
          "step_id": "STEP_5_3",
          "title": "Terraform Infrastructure as Code",
          "isolated_context_prompt": "Task: Implement cloud/terraform modules defining: (1) Cloud Run Service cirque-api, (2) Cloud Run Jobs for compiler and telemetry, (3) Cloud Storage bucket gs://cirque-mountain-packs/ with Cloud CDN backend, and (4) Cloud Scheduler cron triggers. Add terraform validate and tflint test script. Log execution report to .cirque/devlog/M5_CLOUD_SERVICES/step_5_3.json.",
          "input_artifacts": ["TECH_SPEC.md (Section 7.1, 7.2 & Stage 5.1)"],
          "deliverables": [
            "cloud/terraform/main.tf",
            "cloud/terraform/variables.tf",
            "cloud/terraform/cloud_run.tf",
            "cloud/terraform/storage_cdn.tf",
            "scripts/verify_terraform.sh"
          ],
          "harness": {
            "name": "Terraform Linting & Infrastructure Validation Harness",
            "command": "bash scripts/verify_terraform.sh",
            "pass_criteria": "terraform validate returns 0; tflint passes with 0 warnings; all GCP resource schemas match production specs."
          },
          "content_harvesting": {
            "sublines": "Zero-Idle Infrastructure with Terraform & Google Cloud",
            "artifacts_to_save": [
              ".cirque/devlog/M5_CLOUD_SERVICES/terraform_cloud_run.tf",
              ".cirque/devlog/M5_CLOUD_SERVICES/cloud_architecture_diagram.png"
            ],
            "talking_points": [
              "Deploying serverless geospatial pipelines with zero baseline idle cost",
              "Automating CDN cache invalidations for resort updates"
            ]
          }
        }
      ]
    },
    {
      "milestone_id": "M6_END_TO_END_AND_CONTENT",
      "title": "End-to-End Offline Demo, Benchmarks & Tech Talk Assembly",
      "content_theme": "Full-Stack AI Project Showcase: From Mountain Slopes to the Conference Stage",
      "harness_focus": "System-Wide Air-Gapped Latency & Slide Validation Harnesses",
      "steps": [
        {
          "step_id": "STEP_6_1",
          "title": "Air-Gapped Golden Path Integration Test",
          "isolated_context_prompt": "Task: Create test harness tests/e2e/test_offline_golden_path.py simulating full system flow in airplane mode: raw voice prompt -> Gemma JSON intent -> SQLite Dijkstra solver with wind-hold dynamic overlay -> synthesized audio guidance. Validate that total latency from voice input to audio start is <1.5 seconds. Save complete execution trace to .cirque/devlog/M6_END_TO_END_AND_CONTENT/golden_path_trace.json.",
          "input_artifacts": [
            "data/compiled/topology.sqlite",
            "slm/gemma_intent_parser.py",
            "ios/CirqueCore"
          ],
          "deliverables": [
            "tests/e2e/test_offline_golden_path.py",
            ".cirque/devlog/M6_END_TO_END_AND_CONTENT/golden_path_trace.json"
          ],
          "harness": {
            "name": "Full-System Offline Golden Path Timing & Execution Harness",
            "command": "python tests/e2e/test_offline_golden_path.py",
            "pass_criteria": "Voice prompt to audio playback completes in < 1.5 seconds under 100% simulated airplane mode."
          },
          "content_harvesting": {
            "sublines": "The Ultimate Test: Sub-Second Offline Voice Routing",
            "artifacts_to_save": [
              ".cirque/devlog/M6_END_TO_END_AND_CONTENT/golden_path_benchmark.png",
              ".cirque/devlog/M6_END_TO_END_AND_CONTENT/terminal_demo_replay.cast"
            ],
            "talking_points": [
              "End-to-end timing budget: speech parsing, graph query, audio playback",
              "Proving true air-gapped autonomy on consumer devices"
            ]
          }
        },
        {
          "step_id": "STEP_6_2",
          "title": "Content Generator: Substack & LinkedIn Draft Assembler",
          "isolated_context_prompt": "Task: Implement scripts/assemble_content_drafts.py to crawl .cirque/devlog/ across all milestones and automatically generate: (1) drafts/substack_series_overview.md, (2) drafts/substack_harness_architecture.md, (3) drafts/linkedin_carousel_posts.md, and (4) drafts/troubleshooting_and_war_stories.md featuring recorded code snippets, architecture diagrams, and benchmark charts. Verify file generation and markdown syntax. Log report to .cirque/devlog/M6_END_TO_END_AND_CONTENT/content_manifest.json.",
          "input_artifacts": [".cirque/devlog/**"],
          "deliverables": [
            "scripts/assemble_content_drafts.py",
            "drafts/substack_series_overview.md",
            "drafts/substack_harness_architecture.md",
            "drafts/linkedin_carousel_posts.md",
            "drafts/troubleshooting_and_war_stories.md"
          ],
          "harness": {
            "name": "Automated Content Markdown & Asset Integrity Harness",
            "command": "python scripts/assemble_content_drafts.py",
            "pass_criteria": "All four target markdown files generated; all linked snippets and image paths verified to exist in .cirque/devlog/."
          },
          "content_harvesting": {
            "sublines": "Automated Developer Content Pipeline",
            "artifacts_to_save": [
              ".cirque/devlog/M6_END_TO_END_AND_CONTENT/assembled_content_preview.png"
            ],
            "talking_points": [
              "How to turn every Git commit and test log into high-impact developer advocacy content",
              "Building in public without slowing down execution"
            ]
          }
        },
        {
          "step_id": "STEP_6_3",
          "title": "Tech Talk Slide Deck & Interactive Live Demo Script",
          "isolated_context_prompt": "Task: Create docs/presentation/tech_talk_deck.md (Marp-compatible markdown slide deck) and docs/presentation/live_demo_script.md. Include full architecture slides, harness deep-dives, live CLI/iOS simulation commands, audio playback cues, and backup fallback strategies for poor stage connectivity. Validate slides with scripts/verify_slides.sh.",
          "input_artifacts": [
            "TECH_SPEC.md",
            "drafts/substack_series_overview.md",
            "drafts/substack_harness_architecture.md",
            ".cirque/devlog/M6_END_TO_END_AND_CONTENT/golden_path_trace.json"
          ],
          "deliverables": [
            "docs/presentation/tech_talk_deck.md",
            "docs/presentation/live_demo_script.md",
            "scripts/verify_slides.sh"
          ],
          "harness": {
            "name": "Marp Slide Deck Syntax & Asset Rendering Harness",
            "command": "bash scripts/verify_slides.sh",
            "pass_criteria": "Marp compiles slides without syntax errors; all benchmark diagrams render correctly; demo script timings match talk duration."
          },
          "content_harvesting": {
            "sublines": "Conference-Ready Delivery: Stage Presentation & Bulletproof Demos",
            "artifacts_to_save": [
              ".cirque/devlog/M6_END_TO_END_AND_CONTENT/slide_deck_export.pdf",
              ".cirque/devlog/M6_END_TO_END_AND_CONTENT/stage_checklist.md"
            ],
            "talking_points": [
              "Structuring a 30-minute conference talk: The Problem, The Edge Architecture, The Live Demo",
              "Zero-failure stage demos using local offline agents"
            ]
          }
        }
      ]
    }
  ]
}
