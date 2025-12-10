# Fortress Director - Hızlı Referans Rehberi

## 🗂️ Dosya Hiyerarşisi & İçerik Özeti

### **Konfigürasyon & Giriş Noktaları**

| Dosya | Amaç | Kritik mi? |
|-------|------|-----------|
| `settings.py` | Global ayarlar (LLM, portlar, dizinler) | 🔴 KRITIK |
| `cli.py` | Komut satırı arayüzü (`run_turn` komutu) | 🟡 ÖNEMLİ |
| `api.py` | FastAPI sunucusu (HTTP uç noktaları) | 🟡 ÖNEMLİ |
| `__init__.py` | Paket başlatıcısı | 🟢 Normal |

---

### **Ajanlar Katmanı** (`agents/`)

| Dosya | Sorumluluk | Giriş | Çıkış |
|-------|-----------|------|-------|
| `director_agent.py` | Ajan niyeti belirle | Durum, oyuncu seçimi | `{"focus": "...", "summary": "..."}` |
| `planner_agent.py` | Güvenli fonksiyon çağrıları planla | Durum, niyeti | `{"gas": 2, "calls": [...]}` |
| `world_renderer_agent.py` | Atmosfer & duysal detaylar | Durum, eylemler | `{"atmosphere": "..."}` |
| `__init__.py` | Dış aktarımlar | - | - |

**Key Functions:**
- `DirectorAgent.generate_intent()` — Niyeti al
- `PlannerAgent.plan()` — Plan al
- `PlannerAgent.validate_plan()` — Planı doğrula
- `WorldRendererAgent.describe()` — Atmosferi al

---

### **Core Katmanı** (`core/`)

#### **State Management**
| Dosya | Amaç |
|-------|------|
| `state_store.py` 🔴 | Ana durum yönetimi (sıcak/soğuk katman) |
| `state_store_layers.py` | Katman soyutlaması |
| `domain.py` | NPC, Structure, EventMarker sınıfları |

#### **Business Logic**
| Dosya | Amaç |
|-------|------|
| `rules_engine.py` 🔴 | Deterministik kurallar motor |
| `function_registry.py` 🔴 | 60+ güvenli fonksiyon kataloğu |
| `threat_model.py` | Tehdit izleme ve hesaplaması |
| `combat_engine.py` | Muharebe sistemi |
| `metrics_manager.py` | Metrik paneli yönetimi |

#### **Player Actions**
| Dosya | Amaç |
|-------|------|
| `player_action_catalog.py` | Oyuncu seçenekleri |
| `player_action_router.py` | Seçim yönlendirmesi |
| `player_action_validator.py` | Seçim doğrulama |
| `player_actions.yaml` | YAML konfigürasyon |

#### **Safe Functions**
| Dosya | Amaç |
|-------|------|
| `functions/function_schema.py` | Fonksiyon şeması |
| `functions/impl/` | 60+ fonksiyon uygulamaları |

---

### **Pipeline Katmanı** (`pipeline/`)

| Dosya | Amaç | Kritik mi? |
|-------|------|-----------|
| `turn_manager.py` 🔴 | Tur orkestrasyon (Ana döngü) | 🔴 KRITIK |
| `function_executor.py` | Güvenli fonksiyon çalıştırma | 🟡 ÖNEMLİ |
| `state_projection.py` | Oyuncu görünümü hazırla | 🟡 ÖNEMLİ |
| `event_curve.py` | Olay progresyon modeli | 🟡 ÖNEMLİ |
| `endgame_detector.py` | Sona ulaştı mı? | 🟡 ÖNEMLİ |
| `world_tick.py` | Otomatik dünya güncellemeleri | 🟡 ÖNEMLİ |
| `turn_trace.py` | Tur debugging & izleme | 🟢 Normal |
| `function_validator.py` | Güvenli fonksiyon doğrulama | 🟡 ÖNEMLİ |

**Key Functions:**
- `run_turn(state, player_choice)` — Tam tur çalıştır
- `TurnManager.run_turn()` — Orkestrasyon
- `execute_safe_function(call, state)` — Fonksiyon çalıştır

---

### **LLM Katmanı** (`llm/`)

| Dosya | Amaç |
|-------|------|
| `model_registry.py` 🔴 | Ajan→Model eşlemeleri |
| `ollama_client.py` 🔴 | Ollama HTTP istemcisi |
| `runtime_mode.py` 🟡 | Live/Offline modu seç |
| `cache.py` 🟡 | LLM çıktı önbelleği |
| `profiler.py` 🟡 | Latency & token izleme |
| `metrics_logger.py` | Telemetri günlüğü |
| `offline_client.py` | Fallback yanıtları |

**Key Functions:**
- `OllamaClient.generate()` — LLM sorgusu
- `ModelRegistry.get()` — Model config al
- `set_llm_enabled()` — Mode seç
- `profile_llm_call()` — Decorator profil eder

---

### **Narrative Katmanı** (`narrative/`)

| Dosya | Amaç |
|-------|------|
| `event_graph.py` | Etkinlik ağı (düğüm + kenar) |
| `final_engine.py` | Son faz kararı |
| `final_paths.py` | Finali yolları |
| `demo_graph.py` | Demo etkinlik grafiği |
| `theme_graph_loader.py` | Tema grafiği yükleyici |

**Key Functions:**
- `EventGraph.get_node()` — Sahne düğümü al
- `EventGraph.transition()` — Sahne geçişi
- `FinalEngine.evaluate_ending()` — Sonlandırıyı değerlendir

---

### **Ending Katmanı** (`ending/`)

| Dosya | Amaç |
|-------|------|
| `evaluator.py` | Sonlandırma değerlendirmesi |
| `__init__.py` | Placeholder |

---

### **Demo & UI Katmanı** (`demo/`)

| Dosya | Amaç |
|-------|------|
| `spec_loader.py` | Demo özellikleri yükleyici |
| `config/` | Demo yapılandırmaları |
| `web/` | Web UI kaynakları |

---

### **Tema Sistemi** (`themes/`)

| Dosya | Amaç |
|-------|------|
| `loader.py` 🔴 | Tema yükleme |
| `schema.py` 🔴 | Tema JSON şeması |
| `siege_default.json` | Varsayılan tema |
| `_archive/` | Eski temalar |

---

### **Promptlar** (`prompts/`)

| Dosya | Amaç |
|-------|------|
| `director_prompt.txt` 🔴 | DirectorAgent istemleri |
| `planner_prompt.txt` 🔴 | PlannerAgent istemleri |
| `world_renderer_prompt.txt` 🔴 | WorldRenderer istemleri |
| `utils.py` | Prompt yardımcı fonksiyonları |

**Key Functions:**
- `load_prompt_template()` — Prompt dosyasını oku
- `render_prompt()` — Şablonu render et

---

### **Testler** (`tests/`)

| Dizin | Kapsam |
|-------|--------|
| `agents/` | DirectorAgent, PlannerAgent, WorldRenderer testleri |
| `core/` | State, rules, functions testleri |
| `pipeline/` | Tur orkestrasyon, executor testleri |
| `llm/` | Model registry, Ollama client testleri |

**Çalıştırma:**
```bash
pytest tests/                          # Hepsi
pytest tests/agents/ -v                # Ajan testleri
pytest tests/ -m integration           # Entegrasyon testleri
pytest tests/ --cov=fortress_director  # Coverage raporu
```

---

### **Utilites** (`utils/`)

| Dosya | Amaç |
|-------|------|
| `state_diff.py` | State fark hesapla |
| `sqlite_sync.py` | SQLite senkronizasyonu |
| `json_utils.py` | JSON yardımcıları |

---

### **Runtime & Config**

| Dosya | Amaç |
|-------|------|
| `runtime/` | Runtime modu yapılandırması |
| `config/` | YAML konfigürasyon dosyaları |
| `cache/` | LLM önbelleği (otomatik) |
| `logs/` | Günlük dosyaları (otomatik) |

---

## 🔍 Dosya İçeriğinde Hızlı Bulma

### **DirectorAgent Ne Yapar?**
**Dosya:** `agents/director_agent.py`

```
┌─────────────────────┐
│ DirectorAgent       │
├─────────────────────┤
│ • Prompt yükle      │
│ • Few-shots ekle    │
│ • LLM sor           │
│ • JSON parse        │
│ • DirectorIntent    │
└─────────────────────┘
```

- **Giriş:** `projected_state`, `player_choice`, `threat_snapshot`
- **Çıkış:** `{"focus": "stabilize|explore|escalate", "summary": "...", ...}`
- **Model:** Mistral 7B
- **Prompts:** `prompts/director_prompt.txt`

---

### **PlannerAgent Ne Yapar?**
**Dosya:** `agents/planner_agent.py`

```
┌──────────────────────────┐
│ PlannerAgent             │
├──────────────────────────┤
│ • Fonksiyonları listele  │
│ • Prompt oluştur         │
│ • Few-shots ekle         │
│ • LLM sor                │
│ • Plan validate          │
│ • Fallback kontrol       │
└──────────────────────────┘
```

- **Giriş:** `projected_state`, `scene_intent`
- **Çıkış:** `{"gas": 2, "calls": [...]}`
- **Model:** Phi-3 Mini
- **Şema:** `PLANNER_PLAN_SCHEMA`
- **Kısıtlamalar:** MAX_PLAN_CALLS=3, MAX_PLAN_GAS=3

---

### **Güvenli Fonksiyonlar Nerede?**
**Dosya:** `core/function_registry.py`

```
┌──────────────────────────────┐
│ FUNCTION_REGISTRY            │
├──────────────────────────────┤
│ "reinforce_wall"             │
│ "rally_morale"               │
│ "allocate_food"              │
│ ... (60+ total)              │
└──────────────────────────────┘
       ↓
   implementation
       ↓
core/functions/impl/*.py
```

- **Kayıt:** `_CATEGORY_DEFINITIONS` → `load_defaults()`
- **İşleyiciler:** `core/functions/impl/`
- **Doğrulama:** `pipeline/function_validator.py`
- **Çalıştırma:** `pipeline/function_executor.py`

---

### **Durum Nerede Saklanır?**
**Dosya:** `core/state_store.py`

```
RAM (Hot Layer)
    ↓ data/world_state.json
    ↓ data/history/turn_N.json (diff)
    ↓ (via sqlite_sync.py)
SQLite (Cold Layer)
    ↓ db/game_state.sqlite
```

- **Sıcak:** `GameState.data` (RAM'de)
- **Dosya:** `data/world_state.json` (full)
- **Arşiv:** `data/history/turn_*.json` (diff)
- **DB:** `db/game_state.sqlite` (log)

---

### **Tur Nasıl Çalıştırılır?**
**Dosya:** `pipeline/turn_manager.py`

```
1. Snapshot (threat_model, event_graph)
2. DirectorAgent → Intent
3. WorldRendererAgent → Atmosphere
4. PlannerAgent → Plan
5. FunctionExecutor → Execute
6. Auto-tick (threat, resources)
7. Persist & finalize
```

- **Giriş:** `run_turn(state, player_choice)`
- **Çıkış:** `TurnResult`
- **Orchestrator:** `TurnManager`

---

### **Temalar Nerede Tanımlanır?**
**Dosya:** `themes/`

```
themes/
├── siege_default.json
├── _archive/
└── schema.py
```

- **Yükleme:** `themes/loader.py`
- **Doğrulama:** `themes/schema.py`
- **Grafik:** `narrative/theme_graph_loader.py`

---

### **API Uç Noktaları Nerede?**
**Dosya:** `api.py`

```
GET    /                   → HTML UI
GET    /state              → Game state
GET    /metrics            → Metrics
POST   /turn               → Run turn
POST   /choose             → Player choice
GET    /health             → Status
```

---

## 📊 Kritik Kontrol Noktaları

| Kontrol | Dosya | Durum |
|---------|-------|-------|
| **Durum Yükleniyor mu?** | `core/state_store.py` | ✅ `load()` |
| **LLM'ye bağlı mı?** | `llm/ollama_client.py` | ✅ `generate()` |
| **Planlar geçerli mi?** | `agents/planner_agent.py` | ✅ `validate_plan()` |
| **Fonksiyonlar çalışıyor mu?** | `pipeline/function_executor.py` | ✅ `execute_safe_function()` |
| **Durum kalıcı mı?** | `core/state_store.py` | ✅ `persist()` |
| **API yanıt veriyor mu?** | `api.py` | ✅ `@app.get()` |

---

## 🚀 Başlama Rehberi (Yol Haritası)

### **1. Yapı Anlama (30 dk)**
```
settings.py          → Konfigürasyon
api.py               → Giriş noktası
pipeline/turn_manager.py → Akış
agents/              → Ajanlar
core/                → Durum
```

### **2. Kodu Çalıştırma (15 dk)**
```bash
# Turu çalıştır
python fortress_director/cli.py run_turn

# Veya API sunucusunu başlat
python -m uvicorn fortress_director.api:app
```

### **3. Testleri Çalıştırma (15 dk)**
```bash
pytest tests/agents/ -v
pytest tests/pipeline/ -v
pytest tests/ --cov
```

### **4. Kodu Değiştirme (1+ saat)**
- Prompt düzenle: `prompts/`
- Yeni fonksiyon ekle: `core/functions/impl/`
- Tema oluştur: `themes/`
- Test yaz: `tests/`

---

## 🔧 Hızlı Referans Komutları

```bash
# Tek tur çalıştır
python fortress_director/cli.py run_turn --state data/world_state.json

# API sunucusu
python -m uvicorn fortress_director.api:app --host 0.0.0.0 --port 8000

# Tüm testler
pytest tests/ -v

# Belirli test
pytest tests/agents/test_director_agent.py::test_name -v

# Coverage raporu
pytest tests/ --cov=fortress_director --cov-report=html

# Günlükleri izle
tail -f fortress_director/logs/fortress_run.log

# Tema doğrula
fortress_director/scripts/cli.py theme validate --theme siege_default

# Durum farkını göster
git diff data/world_state.json
```

---

## 📞 Ne Arıyorsanız, Nereye Bakın?

| Soru | Dosya |
|------|-------|
| **Niyeti nasıl oluşturur?** | `agents/director_agent.py` |
| **Planı nasıl doğrular?** | `agents/planner_agent.py` |
| **Durum nasıl yönetilir?** | `core/state_store.py` |
| **Fonksiyonlar nedir?** | `core/function_registry.py` |
| **Tur nasıl çalışır?** | `pipeline/turn_manager.py` |
| **LLM nasıl bağlanır?** | `llm/ollama_client.py` |
| **Tema nedir?** | `themes/schema.py` |
| **API uç noktaları?** | `api.py` |
| **Promptları nasıl düzenleme?** | `prompts/` |
| **Yeni fonksiyon eklemek?** | `core/functions/impl/` |
| **Testleri nasıl yazacağım?** | `tests/` (örnekler) |
| **Sonu nasıl çalışır?** | `narrative/final_engine.py` |

---

Bu **Hızlı Referans Rehberi**, tüm önemli dosyaları ve işlevleri merkezi bir konumda toplamaktadır. Herhangi bir sorunuz varsa, bu belgede belirtilen dosya yollarını izleyerek bulabilirsiniz!

