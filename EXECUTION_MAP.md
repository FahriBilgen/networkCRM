# 🗺️ EXECUTION MAP - Detaylı Harita ve Koordinatlar

**Tarih:** 26 Kasım 2025  
**Amaç:** Bulguları uygulamaya dönüştürme

---

## EXECUTION STRUCTURE (Ağaç Yapısı)

```
🎯 GOAL: Production Ready (80-90%)
│
├─ TIER 1 - CRITICAL (Hafta 1, Pazartesi-Cuma)
│  │
│  ├─ [TASK 1.1] Database Schema & Migrations ⏱️ 4 hours
│  │  ├─ Dosya: fortress_director/db/schema.sql (create, 0 bytes → 200 lines)
│  │  ├─ Dosya: fortress_director/db/migrations/001_init.sql (create)
│  │  ├─ Dosya: fortress_director/utils/db_manager.py (create)
│  │  ├─ Dosya: tests/unit/test_db_schema.py (create)
│  │  ├─ SQL Tablolar:
│  │  │  ├─ sessions (5 fields: id, player_name, theme_id, created_at, status)
│  │  │  ├─ game_turns (6 fields: session_id, turn_number, state_snapshot, player_choice, execution_time_ms, created_at)
│  │  │  ├─ checkpoints (5 fields: session_id, turn_number, state, reason, created_at)
│  │  │  └─ safe_function_calls (7 fields: session_id, turn_number, function_name, parameters, result, success, execution_time_ms)
│  │  └─ Test: Verify CREATE TABLE statements execute, verify schema.sql > 0 bytes
│  │
│  ├─ [TASK 1.2] API Security Layer ⏱️ 6 hours
│  │  ├─ JWT Authentication:
│  │  │  ├─ Dosya: fortress_director/auth/__init__.py (create)
│  │  │  ├─ Dosya: fortress_director/auth/jwt_handler.py (create, ~80 lines)
│  │  │  │  └─ Functions: create_access_token(), verify_token(), decode_token()
│  │  │  └─ Test: test_jwt_token_creation, test_jwt_token_verification
│  │  │
│  │  ├─ Rate Limiting:
│  │  │  ├─ Package: fastapi-slowapi (pip install)
│  │  │  ├─ Dosya: fortress_director/config/rate_limiter.py (create, ~50 lines)
│  │  │  │  └─ Config: 100 req/min per user, 10 req/sec per endpoint
│  │  │  └─ Test: test_rate_limit_enforcement
│  │  │
│  │  ├─ CORS Configuration:
│  │  │  ├─ Dosya: fortress_director/api.py (modify, ~20 lines added)
│  │  │  │  └─ Add: app.add_middleware(CORSMiddleware, ...)
│  │  │  │  └─ Allow origins: ["http://localhost:3000", "https://yourdomain.com"]
│  │  │  └─ Test: test_cors_headers
│  │  │
│  │  ├─ Input Validation:
│  │  │  ├─ Dosya: fortress_director/core/models.py (modify, pydantic models)
│  │  │  │  └─ Add: Field validators, max_length constraints
│  │  │  └─ Test: test_invalid_input_rejection
│  │  │
│  │  └─ Error Handling:
│  │     ├─ Dosya: fortress_director/api.py (modify, exception handlers, ~30 lines)
│  │     │  └─ Add: @app.exception_handler(Exception)
│  │     │  └─ Return: {"error": "Internal Server Error"} (not traceback)
│  │     └─ Test: test_no_traceback_in_error_response
│  │
│  ├─ [TASK 1.3] Session Isolation ⏱️ 5 hours
│  │  ├─ Refactor State Store:
│  │  │  ├─ Dosya: fortress_director/core/state_store.py (modify, add session_id parameter)
│  │  │  │  └─ Change: __init__(self) → __init__(self, session_id: str)
│  │  │  │  └─ Update: load/save methods to use session_id in path
│  │  │  │  └─ New path: data/sessions/{session_id}/world_state.json
│  │  │  └─ Test: test_session_isolation_single_user, test_session_data_separate
│  │  │
│  │  ├─ File Locking:
│  │  │  ├─ Dosya: fortress_director/utils/file_lock.py (create, ~40 lines)
│  │  │  │  └─ Class: FileLock (context manager)
│  │  │  └─ Test: test_concurrent_file_access
│  │  │
│  │  ├─ API Updates:
│  │  │  ├─ Dosya: fortress_director/api.py (modify, ~10 lines)
│  │  │  │  └─ Add: session_id lookup/creation in /reset and /turn endpoints
│  │  │  └─ Test: test_api_session_isolation
│  │  │
│  │  └─ Directory Structure:
│  │     └─ Create: data/sessions/{session_id}/
│  │        ├─ world_state.json
│  │        ├─ turn_history/
│  │        ├─ checkpoints/
│  │        └─ .locks/
│  │
│  ├─ [TASK 1.4] LLM Fallback Mechanism ⏱️ 4 hours
│  │  ├─ Fallback Templates:
│  │  │  ├─ Dosya: fortress_director/llm/fallback_templates.py (create, ~150 lines)
│  │  │  │  ├─ FALLBACK_EVENTS: dict (3-5 default events)
│  │  │  │  ├─ FALLBACK_WORLD_DESCRIPTIONS: dict (atmosphere templates)
│  │  │  │  └─ FALLBACK_NPC_REACTIONS: dict (per NPC)
│  │  │  └─ Test: test_fallback_templates_valid_json
│  │  │
│  │  ├─ Agent Modifications:
│  │  │  ├─ Dosya: fortress_director/agents/event_agent.py (modify, try/except)
│  │  │  │  └─ Wrap: return self._call_ollama() with try/except TimeoutError
│  │  │  │  └─ Return: fallback on timeout
│  │  │  ├─ Dosya: fortress_director/agents/world_agent.py (same pattern)
│  │  │  ├─ Dosya: fortress_director/agents/character_agent.py (same pattern)
│  │  │  └─ Test: test_agent_fallback_on_timeout, test_deterministic_fallback
│  │  │
│  │  ├─ Mock Mode:
│  │  │  ├─ Environment: FORTRESS_LLM_MODE=stub (use fallback always)
│  │  │  ├─ Dosya: fortress_director/llm/runtime_mode.py (update)
│  │  │  └─ Test: test_mock_mode_all_turns
│  │  │
│  │  └─ Logging:
│  │     ├─ Dosya: fortress_director/utils/logging_config.py (update, add fallback logs)
│  │     └─ Test: test_fallback_logged_to_file
│  │
│  └─ [TESTING TIER 1] ⏱️ 3 hours
│     ├─ Run: pytest tests/unit/test_db_schema.py -v
│     ├─ Run: pytest tests/integration/test_api_security.py -v
│     ├─ Run: pytest tests/integration/test_session_isolation.py -v
│     ├─ Run: pytest tests/unit/test_llm_fallback.py -v
│     └─ Verify: All tests passing, no regressions in existing 74 tests
│
├─ TIER 2 - HIGH (Hafta 1 Perşembe-Cuma + Hafta 2 Pazartesi-Salı)
│  │
│  ├─ [TASK 2.1] Safe Functions Completion - Phase 1 (Core) ⏱️ 8 hours
│  │  ├─ Implementation (12 functions):
│  │  │  ├─ move_npc (fortress_director/orchestrator/orchestrator.py, line ~2400)
│  │  │  │  ├─ Validation: NPC exists, target within bounds
│  │  │  │  ├─ State update: npc["position"] = {x, y}
│  │  │  │  ├─ UI events: [{type: "npc_move", from: old_pos, to: new_pos}]
│  │  │  │  └─ Test: test_move_npc_success, test_move_npc_invalid_target
│  │  │  ├─ resolve_combat (line ~2500)
│  │  │  │  ├─ Calculation: attacker_strength vs defender_strength
│  │  │  │  ├─ Outcome: attacker_win | defender_win | stalemate
│  │  │  │  ├─ State: update morale/order metrics
│  │  │  │  └─ Test: test_combat_attacker_win, test_combat_deterministic
│  │  │  ├─ repair_breach (line ~2600)
│  │  │  ├─ reinforce_structure (line ~2650)
│  │  │  ├─ spawn_patrol (line ~2700)
│  │  │  ├─ set_watcher_route (line ~2750)
│  │  │  ├─ adjust_metric (line ~2800)
│  │  │  ├─ set_flag (line ~2850)
│  │  │  ├─ change_weather (line ~2900)
│  │  │  ├─ trigger_environment_hazard (line ~2950)
│  │  │  ├─ queue_major_event (line ~3000)
│  │  │  └─ advance_story_act (line ~3050)
│  │  │
│  │  ├─ Testing:
│  │  │  ├─ Unit: tests/unit/test_safe_functions_phase1.py (create, ~200 lines)
│  │  │  │  ├─ 2 tests per function (success, edge case)
│  │  │  │  └─ Verify: state_delta correct, rollback works
│  │  │  ├─ Integration: tests/integration/test_safe_function_chain.py
│  │  │  │  └─ Chain: move_npc → resolve_combat → adjust_metric
│  │  │  └─ Run: pytest tests/unit/test_safe_functions_phase1.py -v
│  │  │
│  │  └─ Validation:
│  │     ├─ Dosya: fortress_director/codeaware/function_validator.py (update)
│  │     │  └─ Add: validators for each function (parameter types, ranges)
│  │     └─ Test: test_validator_rejects_invalid_params
│  │
│  ├─ [TASK 2.2] Safe Functions Completion - Phase 2 (Resources) ⏱️ 6 hours
│  │  ├─ Functions:
│  │  │  ├─ adjust_stockpile
│  │  │  ├─ open_trade_route
│  │  │  ├─ close_trade_route
│  │  │  └─ transfer_item
│  │  └─ Testing: same pattern as Phase 1
│  │
│  ├─ [TASK 2.3] Safe Functions Completion - Phase 3 (Story/World) ⏱️ 6 hours
│  │  ├─ Functions:
│  │  │  ├─ queue_major_event
│  │  │  ├─ advance_story_act
│  │  │  ├─ change_weather
│  │  │  └─ trigger_environment_hazard
│  │  └─ Testing: same pattern as Phase 1
│  │
│  ├─ [TASK 2.4] Environment Configuration ⏱️ 2 hours
│  │  ├─ Create: .env.local (development)
│  │  │  └─ FORTRESS_LLM_MODE=llm
│  │  │  └─ FORTRESS_API_PORT=8000
│  │  │  └─ FORTRESS_JWT_SECRET=dev-secret-key
│  │  │  └─ ... (other vars)
│  │  ├─ Update: fortress_director/settings.py (modify, ~20 lines)
│  │  │  ├─ Load from .env using python-dotenv
│  │  │  ├─ Validate required vars on startup
│  │  │  └─ Log config (no secrets)
│  │  ├─ Dosya: fortress_director/config/env_loader.py (create)
│  │  │  └─ Function: load_env() → Dict[str, Any]
│  │  └─ Test: test_env_loading, test_env_validation
│  │
│  ├─ [TASK 2.5] Integration Testing Phase 2 ⏱️ 4 hours
│  │  ├─ Test Suite: tests/integration/test_safe_function_integration.py
│  │  │  ├─ Test: full_turn_with_safe_functions (E2E)
│  │  │  ├─ Test: safe_function_state_persistence
│  │  │  ├─ Test: safe_function_ui_events
│  │  │  └─ Test: safe_function_rollback_on_error
│  │  └─ Run: pytest tests/integration/ -v (all tests)
│  │
│  └─ [TIER 2 SUCCESS CRITERIA]
│     ├─ 60+ safe functions implemented (currently ~12)
│     ├─ All Phase 1, 2, 3 tests passing
│     ├─ Environment config working with .env
│     └─ Integration tests: 100+ new test cases
│
├─ TIER 3 - MEDIUM (Hafta 2 Çarşamba-Cuma)
│  │
│  ├─ [TASK 3.1] Multi-Theme Support ⏱️ 8 hours
│  │  ├─ Theme 1: siege_default (✅ already complete)
│  │  │
│  │  ├─ Theme 2: mirror_archives (sci-fi)
│  │  │  ├─ Dosya: fortress_director/themes/mirror_archives/theme.json (create, ~300 lines)
│  │  │  │  ├─ NPCs: 4 unique (Dr. Aria, Prophet Zek, Sentinel Unit, Rogue AI)
│  │  │  │  ├─ Structures: 4 unique (Containment Core, Data Vault, Shield Generator, Repair Station)
│  │  │  │  ├─ Atmosphere: sci-fi (glowing, mechanical, digital)
│  │  │  │  ├─ Quest beats: 3 acts (Days 1-2, 3-4, 5-7)
│  │  │  │  └─ Safe function overrides: (e.g., disable "repair_breach", enable "repair_core")
│  │  │  ├─ Dosya: fortress_director/themes/mirror_archives/README.md (create)
│  │  │  └─ Test: test_mirror_archives_theme_valid
│  │  │
│  │  ├─ Theme 3: courtly_intrigue (political)
│  │  │  ├─ Dosya: fortress_director/themes/courtly_intrigue/theme.json (create, ~300 lines)
│  │  │  │  ├─ NPCs: 4 unique (Lady Cordelia, Lord Theron, Bishop Marcus, Merchant Prince)
│  │  │  │  ├─ Structures: 4 unique (Grand Hall, Treasury, Guard Tower, Chapel)
│  │  │  │  ├─ Atmosphere: courtly (elegant, tense, diplomatic)
│  │  │  │  ├─ Quest beats: 3 acts
│  │  │  │  └─ Safe function overrides: (e.g., enable "negotiate_treaty", disable "resolve_combat")
│  │  │  ├─ Dosya: fortress_director/themes/courtly_intrigue/README.md (create)
│  │  │  └─ Test: test_courtly_intrigue_theme_valid
│  │  │
│  │  ├─ API Update:
│  │  │  ├─ Dosya: fortress_director/api.py (modify, ~5 lines)
│  │  │  │  └─ Get available themes from themes/*/theme.json
│  │  │  └─ Test: test_list_all_themes_endpoint
│  │  │
│  │  ├─ UI Integration:
│  │  │  ├─ Dosya: demo/web/src/components/ThemeSelector.tsx (create/update)
│  │  │  │  └─ Dropdown: select from 3+ themes
│  │  │  └─ Test: test_theme_selector_works
│  │  │
│  │  └─ Testing:
│  │     ├─ tests/integration/test_all_themes.py (create)
│  │     │  ├─ Test each theme loads without errors
│  │     │  ├─ Test default NPCs/structures present
│  │     │  ├─ Test quest progression valid
│  │     │  └─ Run: pytest tests/integration/test_all_themes.py -v
│  │     └─ Manual: Play 1 turn in each theme
│  │
│  ├─ [TASK 3.2] Monitoring & Observability ⏱️ 6 hours
│  │  ├─ Metrics Collection:
│  │  │  ├─ Dosya: fortress_director/utils/metrics_collector.py (create, ~100 lines)
│  │  │  │  ├─ Metrics: turn_duration_ms, events_generated, safe_functions_executed
│  │  │  │  ├─ Metrics: agent_success_rate, fallback_rate, error_rate
│  │  │  │  └─ Storage: metrics.json (append-only)
│  │  │  └─ Test: test_metrics_collection
│  │  │
│  │  ├─ Health Check Endpoint:
│  │  │  ├─ Dosya: fortress_director/api.py (modify, add endpoint, ~20 lines)
│  │  │  │  └─ GET /health → {status: "healthy", uptime_ms: 12345, db_ok: true, ...}
│  │  │  └─ Test: test_health_endpoint
│  │  │
│  │  ├─ Logging Enhancements:
│  │  │  ├─ Dosya: fortress_director/utils/logging_config.py (modify)
│  │  │  │  └─ Structured logging: JSON format for parsed logs
│  │  │  │  └─ Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
│  │  │  └─ Test: test_structured_logging_output
│  │  │
│  │  ├─ Basic Dashboard (optional):
│  │  │  ├─ Dosya: tools/metrics_dashboard.py (create, ~150 lines)
│  │  │  │  └─ Simple ASCII dashboard: reads metrics.json, shows stats
│  │  │  └─ Usage: python tools/metrics_dashboard.py
│  │  │
│  │  └─ Documentation:
│  │     └─ docs/monitoring_guide.md (create, ~100 lines)
│  │        └─ How to check health, interpret metrics, troubleshoot
│  │
│  ├─ [TASK 3.3] Performance Optimization ⏱️ 4 hours
│  │  ├─ Profiling:
│  │  │  ├─ Run: tools/regression_runner.py (existing)
│  │  │  │  └─ Collect: turn times for 10 full games
│  │  │  └─ Analyze: identify slow agents/functions
│  │  │
│  │  ├─ Optimization Targets:
│  │  │  ├─ Cache: common phrases/outputs (reduce token generation)
│  │  │  ├─ Batch: multiple safe functions if possible
│  │  │  └─ Quantize: consider 4-bit models for agents (future)
│  │  │
│  │  └─ Validation:
│  │     └─ Verify: turn time ≤ 3.5s with safety margin
│  │
│  └─ [TIER 3 SUCCESS CRITERIA]
│     ├─ 3 playable themes (siege, mirror_archives, courtly_intrigue)
│     ├─ Health check endpoint live
│     ├─ Metrics collection running
│     ├─ Performance: 3.5s/turn target met or close
│     └─ Documentation complete
│
└─ VALIDATION & RELEASE (Hafta 2 Cuma)
   │
   ├─ [FULL TEST SUITE]
   │  ├─ Run: pytest tests/ -v --tb=short
   │  ├─ Expected: 150+ tests passing (74 existing + 76 new)
   │  ├─ Coverage: ≥80% code coverage
   │  └─ No regressions in original 74 tests
   │
   ├─ [INTEGRATION TEST]
   │  ├─ Test: Full game 7-turn playthrough each theme
   │  ├─ Test: Concurrent 3-player sessions
   │  ├─ Test: Ollama timeout simulation + fallback
   │  ├─ Test: Database persistence across restarts
   │  └─ Verify: All game states correctly persisted
   │
   ├─ [SECURITY AUDIT]
   │  ├─ Test: Unauthenticated /turn → 401 error
   │  ├─ Test: Rate limit enforcement
   │  ├─ Test: XSS/injection attempts rejected
   │  ├─ Test: CORS headers correct
   │  └─ Verify: No stack traces in responses
   │
   ├─ [DOCUMENTATION]
   │  ├─ Update: docs/api.md (new endpoints, examples)
   │  ├─ Create: docs/deployment_guide.md (env vars, database setup)
   │  ├─ Update: README.md (latest status)
   │  ├─ Create: docs/troubleshooting.md (common issues)
   │  └─ Create: CHANGELOG.md (all changes)
   │
   ├─ [GIT COMMITS]
   │  ├─ Commit: feat: database schema and migrations
   │  ├─ Commit: feat: JWT authentication and rate limiting
   │  ├─ Commit: feat: session isolation per user
   │  ├─ Commit: feat: LLM fallback mechanism
   │  ├─ Commit: feat: complete all 60+ safe functions
   │  ├─ Commit: feat: environment configuration from .env
   │  ├─ Commit: feat: multi-theme support (3 themes)
   │  ├─ Commit: feat: health check and metrics collection
   │  └─ Commit: docs: comprehensive deployment guide
   │
   └─ [PRODUCTION READINESS CHECKLIST]
      ├─ ✅ Database: working, migrated
      ├─ ✅ Security: JWT + rate limit + CORS
      ├─ ✅ Sessions: isolated, concurrent-safe
      ├─ ✅ Fallback: Ollama timeout → deterministic response
      ├─ ✅ Safe Functions: 60+, all implemented
      ├─ ✅ Tests: 150+, 80%+ coverage
      ├─ ✅ Performance: ≤3.5s/turn
      ├─ ✅ Documentation: complete
      ├─ ✅ Multi-theme: 3+ themes working
      └─ ✅ Monitoring: health check, metrics active

PRODUCTION READINESS: 80-90% ✅ READY FOR BETA LAUNCH
```

---

## TIMELINE SUMMARY

```
📅 WEEK 1
 L Mon  | Database (4h) + API Security (6h)        = 10h
 L Tue  | Session Isolation (5h) + LLM Fallback (4h) + Testing (3h) = 12h
 L Wed  | Safe Functions Phase 1 (8h) + Testing (4h) = 12h
 L Thu  | Safe Functions Phase 2+3 (12h) + Testing (4h) = 16h
 L Fri  | Integration Testing (8h) + Bug Fixes (4h) = 12h
       └─ WEEK 1 TOTAL: 62 hours (1 full dev week)

📅 WEEK 2
 L Mon  | Environment Config (2h) + Multi-Theme (10h) + Testing (5h) = 17h
 L Tue  | Continue Multi-Theme (5h) + Monitoring (8h) = 13h
 L Wed  | Bug Fixes (8h) + Performance Tuning (4h) = 12h
 L Thu  | Full Integration Test (8h) + Docs (4h) = 12h
 L Fri  | Final Validation (8h) + Release Prep (4h) = 12h
       └─ WEEK 2 TOTAL: 66 hours (1 full dev week)

TOTAL: ~128 hours (3.2 weeks with buffer) ✅
```

---

## DEPENDENCY GRAPH (Order Matters!)

```
1. Database Schema ✅
   └─ Required by: Session Isolation, API Security, Safe Functions

2. API Security ✅
   └─ Required by: Everything (protection layer)

3. Session Isolation ✅
   ├─ Required by: Multi-user support
   └─ Uses: Database Schema + API Security

4. LLM Fallback ✅
   └─ Required by: Reliability (independent)

5. Safe Functions Completion ✅
   ├─ Requires: Database Schema (for audit log)
   ├─ Requires: Session Isolation (per-session state)
   └─ Required by: Gameplay, Multi-theme

6. Environment Configuration ✅
   └─ Required by: Deployment, Multi-theme

7. Multi-Theme Support ⏱️
   ├─ Requires: Safe Functions (all themes use them)
   └─ Requires: Environment Config (theme loading)

8. Monitoring & Observability 📊
   └─ Optional (independent)

Critical Path: DB → API Security → Session → Safe Functions → Multi-Theme
```

---

## DAILY STANDUP TEMPLATE

**Each day, report:**

```
DATE: YYYY-MM-DD
COMPLETED TODAY:
  ✅ Task X.Y: [brief summary]
     - Tests passing: N
     - Commits: [hash list]

IN PROGRESS:
  🔄 Task A.B: [what you're working on right now]

BLOCKERS:
  ❌ [if any]

TOMORROW PLAN:
  - Task C.D: [what's next]
  - Task C.E: [what's next]
```

---

END OF EXECUTION MAP
