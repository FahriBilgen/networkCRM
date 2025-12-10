# Fortress Director - Teknoloji Stack & Mimari Diyagramları

## 🏛️ Sistem Mimarisi

```
┌─────────────────────────────────────────────────────────────────┐
│                        UI / Frontend                             │
│  (React + Vite / Web UI @ demo_build/ui_dist)                   │
└──────────────────────┬──────────────────────────────────────────┘
                       │ HTTP/JSON (CORS)
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI (fortress_director/api.py)            │
│  - GET /turn                 - state, options, narrative         │
│  - POST /choose              - player_choice + state update      │
│  - GET /state, /metrics, etc - game state query endpoints       │
└────────┬────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  pipeline/turn_manager.py (TurnManager - Orchestrator)           │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ 1. Snapshot State (threat_model, event_graph)             │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ 2. DirectorAgent → Scene Intent                           │ │
│  │    (Query LLM: Mistral 7B)                                │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ 3. WorldRendererAgent → Atmosphere                        │ │
│  │    (Query LLM: Phi-3 Mini)                                │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ 4. PlannerAgent → Safe Function Plan                      │ │
│  │    (Query LLM: Phi-3 Mini)                                │ │
│  │    ┌──────────────────────────────────────────────────┐   │ │
│  │    │ {                                                │   │ │
│  │    │   "gas": 2,                                      │   │ │
│  │    │   "calls": [                                     │   │ │
│  │    │     {"name": "reinforce_wall", ...},             │   │ │
│  │    │     {"name": "rally_morale", ...}                │   │ │
│  │    │   ]                                              │   │ │
│  │    │ }                                                │   │ │
│  │    └──────────────────────────────────────────────────┘   │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ 5. FunctionExecutor → Execute Plan                        │ │
│  │    (pipeline/function_executor.py)                         │ │
│  │    For each call:                                          │ │
│  │      - Validate parameters                                │ │
│  │      - Call handler from core/functions/impl/             │ │
│  │      - Apply state mutation                               │ │
│  │      - Log result                                         │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ 6. Auto-Tick (Threat Model, Event Curve)                  │ │
│  │    - Resources decay                                       │ │
│  │    - Threat rises/falls                                    │ │
│  │    - Events queue updates                                 │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ 7. Persist & Finalize                                      │ │
│  │    - Compute state_diff                                    │ │
│  │    - Write data/history/turn_N.json (diff)                │ │
│  │    - Write data/world_state.json (full)                   │ │
│  │    - Sync to SQLite (db/game_state.sqlite)                │ │
│  │    - Return TurnResult                                     │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
     [TurnResult]
      - narrative
      - ui_events
      - executed_actions
      - threat_snapshot
      - is_final
         │
         ├─────► UI güncellemesi
         ├─────► Metrics paneli
         ├─────► NPC/Structs görüntüleme
         └─────► Sonraki tur seçenekleri
```

---

## 🧩 Agent Detay Mimarisi

```
┌───────────────────────────────────────────────────────────────────┐
│                         agents/                                   │
├───────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ DirectorAgent (director_agent.py)                        │   │
│  │ ─────────────────────────────────────────────────────────│   │
│  │ • Load prompt: prompts/director_prompt.txt               │   │
│  │ • Add few-shot examples (DIRECTOR_FEW_SHOTS)            │   │
│  │ • Invoke LLM (Mistral 7B)                               │   │
│  │ • Parse JSON → {focus, summary, risk_budget, ...}       │   │
│  │ • Return DirectorIntent                                  │   │
│  │                                                           │   │
│  │ Input: (state, player_choice, threat_snapshot)          │   │
│  │ Output: {"focus": "stabilize", "summary": "...", ...}   │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ PlannerAgent (planner_agent.py)                          │   │
│  │ ─────────────────────────────────────────────────────────│   │
│  │ • Load safe functions from FUNCTION_REGISTRY            │   │
│  │ • Build prompt with available functions                 │   │
│  │ • Add few-shot examples (FEW_SHOT_EXAMPLES)            │   │
│  │ • Invoke LLM (Phi-3 Mini)                              │   │
│  │ • Validate JSON with PLANNER_PLAN_SCHEMA               │   │
│  │ • Check gas budget (MAX_PLAN_GAS = 3)                  │   │
│  │ • Check call count (MAX_PLAN_CALLS = 3)                │   │
│  │ • Handle errors: log + fallback to deterministic plan   │   │
│  │                                                           │   │
│  │ Input: (projected_state, scene_intent)                 │   │
│  │ Output: {"gas": 2, "calls": [{...}, {...}]}            │   │
│  │                                                           │   │
│  │ Error Handling:                                         │   │
│  │ • $schema found → ValueError (reject)                  │   │
│  │ • Invalid JSON → normalize + warn                      │   │
│  │ • Missing gas → infer + log                            │   │
│  │ • Exceed max_calls → truncate warnings                 │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ WorldRendererAgent (world_renderer_agent.py)            │   │
│  │ ─────────────────────────────────────────────────────────│   │
│  │ • Load prompt: prompts/world_renderer_prompt.txt        │   │
│  │ • Add state context (location, weather, NPC status)    │   │
│  │ • Invoke LLM (Phi-3 Mini)                              │   │
│  │ • Parse JSON → {atmosphere, sensory_details, ...}      │   │
│  │ • GUARANTEE: if atmosphere empty → fallback            │   │
│  │ • Return atmosphere dict                                │   │
│  │                                                           │   │
│  │ Input: (state, executed_actions, director_intent)     │   │
│  │ Output: {"atmosphere": "...", "sensory_details": ...}  │   │
│  │                                                           │   │
│  │ Fallback (if empty):                                    │   │
│  │ • build_default_atmosphere(state)                      │   │
│  │ • theme-appropriate mood                                │   │
│  │ • minimal sensory details                               │   │
│  └──────────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Durum Döngüsü

```
┌─────────────────────────────────────────────────────────────┐
│         GameState (core/state_store.py)                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [Sıcak Katman - RAM]                 [Soğuk Katman]       │
│  ─────────────────────                 ─────────────       │
│  • turn                                 • SQLite log        │
│  • metrics (order, morale)              • history/ dir      │
│  • player_position                      • archived turns   │
│  • npc_locations                        • full backups     │
│  • structures                                               │
│  • flags, recent_events                                     │
│                                                             │
│  data/world_state.json (full snapshot)                     │
│  data/history/turn_{N}.json (diff only)                   │
│  db/game_state.sqlite (schema + log)                      │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ Lifecycle:                                          │  │
│  │                                                     │  │
│  │ 1. load() → JSON from disk into RAM               │  │
│  │ 2. apply_safe_function() → mutate fields          │  │
│  │ 3. apply_threat_tick() → auto-update              │  │
│  │ 4. persist() → compute_diff, write both layers    │  │
│  │ 5. sqlite_sync() → replicate to cold storage      │  │
│  │ 6. [ready for next turn]                          │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                             │
│  Metrics Schema:                                            │
│  {                                                         │
│    "order": 60,              # Command cohesion (0-100)   │
│    "morale": 64,             # Troop morale (0-100)       │
│    "resources": 82,          # Food/supplies (0-100)      │
│    "knowledge": 48,          # Intel gathered (0-100)     │
│    "glitch": 42,             # AI error rate (0-100)      │
│    "combat": {                                            │
│      "total_skirmishes": 5,                              │
│      "total_casualties_friendly": 12,                    │
│      "total_casualties_enemy": 18                        │
│    }                                                     │
│  }                                                       │
│                                                             │
│  Flags (persistent):                                        │
│  {                                                         │
│    "wall_compromised": false,                             │
│    "morale_crisis": false,                                │
│    "supply_low": false,                                   │
│    "enemy_breach": false,                                 │
│    "major_event_triggered": false                         │
│  }                                                       │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 Güvenli Fonksiyon Sistemi

```
┌──────────────────────────────────────────────────────────┐
│  core/function_registry.py                               │
│  ──────────────────────────────────────────────────────  │
│                                                          │
│  FUNCTION_REGISTRY: Dict[str, SafeFunctionMeta]         │
│  ─────────────────────────────────────────────────────  │
│                                                          │
│  Registration (boot time):                              │
│  ┌─────────────────────────────────────────────────┐   │
│  │ _CATEGORY_DEFINITIONS = {                       │   │
│  │   "combat": [                                   │   │
│  │     {                                           │   │
│  │       "name": "reinforce_wall",                │   │
│  │       "description": "...",                     │   │
│  │       "params": [...],                          │   │
│  │       "gas_cost": 2,                            │   │
│  │       "planner_weight": 1.5,                    │   │
│  │       "enabled": true                           │   │
│  │     },                                          │   │
│  │     ...                                         │   │
│  │   ],                                            │   │
│  │   "morale": [...],                              │   │
│  │   "resources": [...],                           │   │
│  │   "intel": [...],                               │   │
│  │   "npc": [...]                                  │   │
│  │ }                                               │   │
│  │                                                 │   │
│  │ load_defaults() → register all 60+ functions   │   │
│  └─────────────────────────────────────────────────┘   │
│                                                          │
│  Handler Binding (init):                                │
│  ┌─────────────────────────────────────────────────┐   │
│  │ core/functions/impl/combat.py:                  │   │
│  │   def handler_reinforce_wall(**kwargs):        │   │
│  │       return {"success": true, ...}             │   │
│  │                                                 │   │
│  │ bind_handler("reinforce_wall", handler_func)   │   │
│  └─────────────────────────────────────────────────┘   │
│                                                          │
│  Execution (per-turn):                                  │
│  ┌─────────────────────────────────────────────────┐   │
│  │ plan = planner_agent.plan(...)                  │   │
│  │ # → {"gas": 2, "calls": [{"name": "...", ...}]}│   │
│  │                                                 │   │
│  │ for call in plan["calls"]:                      │   │
│  │   func = FUNCTION_REGISTRY[call["name"]]       │   │
│  │   result = func.handler(**call["kwargs"])      │   │
│  │   state.apply_result(result)                   │   │
│  │   log.info(f"Executed {call['name']}")         │   │
│  └─────────────────────────────────────────────────┘   │
│                                                          │
│  Validation:                                            │
│  • Parameter types checked                              │
│  • Gas budget enforced (MAX = 3)                        │
│  • Call count limited (MAX = 3)                         │
│  • State mutations are atomic                           │
│  • Errors logged & handled gracefully                   │
└──────────────────────────────────────────────────────────┘

Safe Functions (60+ total):

COMBAT (10):
  - apply_combat_pressure
  - reduce_threat
  - ranged_attack
  - melee_engagement
  - suppressive_fire
  - scout_enemy_positions
  - fortify_combat_zone
  - deploy_archers
  - set_ambush
  - breach_wall

MORALE (8):
  - rally_morale
  - reduce_panic
  - inspire_troops
  - address_doubts
  - boost_hope
  - calm_nerves
  - energize_defense
  - restore_confidence

RESOURCES (7):
  - allocate_food
  - distribute_supplies
  - repair_structure
  - gather_materials
  - store_provisions
  - optimize_use
  - stretch_resources

INTEL (8):
  - gather_intelligence
  - scout_perimeter
  - analyze_threat
  - identify_weakness
  - map_surroundings
  - track_movement
  - predict_attack
  - decode_message

NPC (12):
  - move_npc
  - recruit_volunteer
  - assign_task
  - delegate_authority
  - train_unit
  - boost_confidence
  - heal_wounds
  - set_npc_status
  - and more...

... (total 60+)
```

---

## 🌐 LLM Entegrasyon Akışı

```
┌──────────────────────────────────────────────────────────┐
│  llm/ Submodule                                          │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  model_registry.py:                                      │
│  ┌─────────────────────────────────────────────────┐   │
│  │ ModelRegistry                                   │   │
│  │ ─────────────────────────────────────────────── │   │
│  │ models = {                                      │   │
│  │   "director": ModelConfig(                      │   │
│  │     name="mistral:latest",                      │   │
│  │     temperature=0.7,                            │   │
│  │     top_p=0.9,                                  │   │
│  │     max_tokens=512                              │   │
│  │   ),                                            │   │
│  │   "planner": ModelConfig(                       │   │
│  │     name="phi:latest",                          │   │
│  │     temperature=0.4,                            │   │
│  │     top_p=0.5,                                  │   │
│  │     max_tokens=192                              │   │
│  │   ),                                            │   │
│  │   "world_renderer": ModelConfig(...)            │   │
│  │ }                                               │   │
│  │                                                 │   │
│  │ get("director") → ModelConfig                   │   │
│  │ list() → [ModelRecord, ModelRecord, ...]       │   │
│  └─────────────────────────────────────────────────┘   │
│                                                          │
│  ollama_client.py:                                      │
│  ┌─────────────────────────────────────────────────┐   │
│  │ OllamaClient                                    │   │
│  │ ─────────────────────────────────────────────── │   │
│  │ base_url = "http://localhost:11434"             │   │
│  │                                                 │   │
│  │ generate(model, prompt, options) →              │   │
│  │   POST /api/generate                            │   │
│  │   return response.text (raw output)             │   │
│  │                                                 │   │
│  │ Error handling:                                 │   │
│  │ • Connection refused → OllamaClientError       │   │
│  │ • Timeout → generate_with_timeout + fallback   │   │
│  │ • Invalid JSON → log + raise                   │   │
│  └─────────────────────────────────────────────────┘   │
│                                                          │
│  runtime_mode.py:                                       │
│  ┌─────────────────────────────────────────────────┐   │
│  │ RuntimeMode                                     │   │
│  │ ─────────────────────────────────────────────── │   │
│  │ • LIVE: Query real LLM (Ollama)                │   │
│  │ • OFFLINE: Use fallback responses              │   │
│  │                                                 │   │
│  │ set_llm_enabled(True) → LIVE mode             │   │
│  │ set_llm_enabled(False) → OFFLINE mode         │   │
│  │                                                 │   │
│  │ is_llm_enabled() → bool                         │   │
│  │ get_mode() → RuntimeMode enum                  │   │
│  └─────────────────────────────────────────────────┘   │
│                                                          │
│  cache.py:                                              │
│  ┌─────────────────────────────────────────────────┐   │
│  │ LLMCache (LRU + JSON disk)                      │   │
│  │ ─────────────────────────────────────────────── │   │
│  │ Key: hash(model + prompt + options)             │   │
│  │ Value: {"raw_output": "...", "timestamp": ...} │   │
│  │                                                 │   │
│  │ cache.get(key) → cached_value or None          │   │
│  │ cache.put(key, value) → store                  │   │
│  │                                                 │   │
│  │ Storage: fortress_director/cache/llm_*.json    │   │
│  │ Lifetime: ~1 hour (TTL check)                  │   │
│  └─────────────────────────────────────────────────┘   │
│                                                          │
│  profiler.py:                                           │
│  ┌─────────────────────────────────────────────────┐   │
│  │ LLMCallMetrics                                  │   │
│  │ ─────────────────────────────────────────────── │   │
│  │ @profile_llm_call(agent="director")             │   │
│  │ def generate_intent(...):                       │   │
│  │   # Measures latency, token count              │   │
│  │   # Logs to logs/llm_calls.log                 │   │
│  │                                                 │   │
│  │ Output fields:                                  │   │
│  │ • agent: "director"                             │   │
│  │ • model: "mistral:latest"                       │   │
│  │ • latency_ms: 245                               │   │
│  │ • tokens: 128                                   │   │
│  │ • cache_hit: false                              │   │
│  │ • timestamp: "2025-11-24T..."                   │   │
│  └─────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────┘

LLM Query Flow:

Agent.generate(prompt, options)
    │
    ├─ RuntimeMode = is_llm_enabled()
    │
    ├─ if LIVE:
    │   ├─ @profile_llm_call()
    │   ├─ cache.get(key) → cached_response?
    │   │   if cached: return cached
    │   │   else: continue
    │   │
    │   ├─ OllamaClient.generate(model, prompt, options)
    │   │   POST /api/generate
    │   │   ├─ Timeout? → generate_with_timeout()
    │   │   ├─ Error? → OllamaClientError → fallback
    │   │   └─ Return raw_output
    │   │
    │   ├─ Validate JSON (jsonschema)
    │   ├─ cache.put(key, response)
    │   └─ Return parsed JSON
    │
    └─ else OFFLINE:
        ├─ Load fallback response
        └─ Return deterministic result
```

---

## 📦 Teknoloji Stack

| Katman | Teknoloji | Açıklama |
|--------|-----------|----------|
| **Frontend** | React + Vite | Web UI (demo_build/ui_dist) |
| **API** | FastAPI 0.10+ | REST endpoints |
| **Validation** | Pydantic | Request/response schemas |
| **Core Logic** | Python 3.9+ | Ajanlar, fonksiyonlar |
| **State** | JSON (RAM) | Sıcak katman |
| **Database** | SQLite | Soğuk katman, arşiv |
| **LLM Runtime** | Ollama | Local model serving |
| **Models** | Mistral/Phi-3/Gemma/Qwen | Agent LLMs |
| **JSON Schema** | jsonschema | Output validation |
| **Testing** | pytest | Unit + integration |
| **Logging** | Python logging | Files + stdout |
| **Config** | YAML/JSON | Settings |

---

## 🔌 API Endpoints

```
GET    /                              → HTML index (UI)
GET    /state                         → Current game state
GET    /metrics                       → Metrics dashboard
POST   /turn                          → Run single turn
POST   /choose                        → Player choice + advance
GET    /history/{turn_num}            → Archived turn data
GET    /theme                         → Current theme config
POST   /theme                         → Change theme
GET    /health                        → LLM + Database status
POST   /reset                         → New game
```

---

## 🎓 Öğrenme Yolları

### **Başlangıç → Orta Düzey**
1. `settings.py` — Yapılandırma yapısını anla
2. `core/state_store.py` — Durum yönetimini öğren
3. `pipeline/turn_manager.py` — Tur akışını takip et
4. `agents/director_agent.py` — Ajan yapısını gözlemle
5. Birim testleri (`tests/agents/`) — İş mantığını doğrula

### **Orta → İleri Düzey**
1. `core/function_registry.py` — Güvenli fonksiyon sistemi
2. `core/functions/impl/` — İşleyici uygulamaları
3. `narrative/event_graph.py` — Hikaye mimarisi
4. `llm/` — LLM entegrasyonu
5. `themes/loader.py` — Tema paketleri

### **İleri → Uzman**
1. `narrative/final_engine.py` — Finali tasarımı
2. `pipeline/function_executor.py` — Yürütme motoru
3. `core/threat_model.py` — Dinamik sistemler
4. `llm/profiler.py` + `llm/cache.py` — Performans optimizasyonu
5. Entegrasyon testleri + Kabul testleri

---

## 🚦 Başlatma Checklist

```
Pre-Flight Checks:
  ☐ Python 3.9+ installed (python --version)
  ☐ Ollama running (curl http://localhost:11434/api/tags)
  ☐ Models pulled (ollama pull mistral:latest, etc.)
  
Project Setup:
  ☐ pip install -r requirements.txt
  ☐ pytest tests/ -v (all pass?)
  
Configuration:
  ☐ fortress_director/settings.py → SETTINGS verified
  ☐ LLM models accessible (ollama list)
  ☐ data/, db/, logs/ directories exist
  
Runtime:
  ☐ CLI test: python fortress_director/cli.py run_turn
  ☐ API test: python -m uvicorn fortress_director.api:app
  ☐ UI test: http://localhost:8000/
  
Demo:
  ☐ ./demo_build/run_demo.ps1 (Windows) OR run_demo.sh (Linux/Mac)
```

---

## 📊 Performans Hedefleri

| Metrik | Hedef | Durum |
|--------|-------|-------|
| **LLM Latency** | <2 sn (uncached) | ✓ Monitored |
| **State Persist** | <50 ms | ✓ Profiled |
| **Turn Cycle** | <10 sn | ✓ Logged |
| **Memory Growth** | <200 MB / 100 turns | ✓ Rotation active |
| **Cache Hit Rate** | >70% | ✓ Tracked |
| **Error Rate** | <1% | ✓ Telemetry |

---

## 🔐 Güvenlik & Doğrulama

✅ **Tüm ajan çıktıları** JSON schemalarla doğrulanır  
✅ **Güvenli fonksiyon parametreleri** tip-check edilir  
✅ **Durum mutasyonları** atomiktir (transaction-like)  
✅ **Hata yönetimi** sessiz başarısızlıkları engeller  
✅ **Logging** tam audit trail sağlar  
✅ **Tema paketleri** bağımlılık resolver ile yüklenir  

---

## 📞 Yardım & Hata Ayıklama

```bash
# Günlükleri canlı görüntüle
tail -f fortress_director/logs/fortress_run.log

# LLM çağrılarını profil et
python tools/profile_turn.py --turns 5

# Tema doğrulama
fortress_director/scripts/cli.py theme validate --theme siege_default

# State diff'ini göster
git diff data/world_state.json

# Test Coverage
pytest tests/ --cov=fortress_director --cov-report=html

# Regression Testi
python tools/regression_runner.py --baseline main --head HEAD
```

---

Kapsayıcı bir referans belgesinde **Fortress Director** başarıyla belgelenmiştir. Herhangi bir sorunuz veya detay istemeniz durumunda, lütfen belirtiniz!

