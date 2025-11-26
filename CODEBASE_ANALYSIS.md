# Fortress Director - Detaylı Kod Tabanı Analizi

## 📋 Proje Özeti

**Fortress Director** — deterministik, yerel-ilk bir multi-agent AI oyun motoru. Bir kale kuşatma senaryosunda (Seige of Lornhaven) oyuncuya dinamik hikayeler sunan, LLM tabanlı ajanlarla ve güvenli fonksiyon yürütme mekanizmaları ile entegre olmuş bir sistem.

- **Dil:** Python 3.9+
- **Esas Framework:** FastAPI (API), Pydantic (veri doğrulama)
- **LLM Altyapısı:** Ollama + Mistral/Phi-3/Gemma/Qwen modelleri
- **Veri Saklama:** SQLite (soğuk) + JSON (sıcak katman)
- **Tema Sistemi:** JSON/YAML tabanlı tema paketleri

---

## 🏗️ Mimari Yapı

```
fortress_director/
├── agents/               # LLM-tabanlı karar vericiler
│   ├── director_agent.py           # Ajan amacını belirle
│   ├── planner_agent.py            # Güvenli fonksiyon planla
│   └── world_renderer_agent.py      # Dünya atmosferini oluştur
│
├── core/                 # İş mantığı ve durum yönetimi
│   ├── state_store.py              # Oyun durumu (JSON/SQLite)
│   ├── function_registry.py        # 60+ güvenli fonksiyon kataloğu
│   ├── rules_engine.py             # Deterministik kurallar
│   ├── domain.py                   # NPC, Structure, EventMarker sınıfları
│   ├── threat_model.py             # Tehdit/kaynakları takibi
│   └── functions/                  # Fonksiyon uygulamaları
│
├── pipeline/             # Tur orkestrasyon
│   ├── turn_manager.py             # Ana tur döngüsü
│   ├── function_executor.py        # Güvenli fonk. çalıştır
│   ├── state_projection.py         # Oyuncu görünümü hazırla
│   └── endgame_detector.py         # Son faz algılaması
│
├── llm/                  # LLM entegrasyonu
│   ├── model_registry.py           # Ajan→Model eşlemeleri
│   ├── ollama_client.py            # Ollama HTTP istemcisi
│   ├── cache.py                    # LLM çıktı önbellekleme
│   ├── profiler.py                 # Latency/token izleme
│   └── runtime_mode.py             # Live/Offline geçişi
│
├── narrative/            # Hikaye grafiği ve finali
│   ├── event_graph.py              # Sahne/etkinlik ağı
│   ├── final_engine.py             # Son faz kararı
│   └── theme_graph_loader.py       # Tema etkinlik yükleyici
│
├── ending/               # Finale spesifik mantık
│   └── evaluator.py                # Sonu değerlendir
│
├── demo/                 # UI ve CLI yüzeyleri
│   ├── config/                     # Demo ayarları
│   └── web/                        # (İsteğe bağlı) Web UI
│
├── themes/               # Tema paketleri
│   └── siege_default.json          # Varsayılan tema (Lornhaven)
│
├── tests/                # pytest paketleri
│   ├── agents/
│   ├── core/
│   ├── pipeline/
│   └── llm/
│
├── prompts/              # Ajan istemini şablonları
│   ├── director_prompt.txt
│   ├── planner_prompt.txt
│   ├── world_renderer_prompt.txt
│   └── utils.py
│
├── api.py                # FastAPI uygulaması
├── settings.py           # Global yapılandırma
├── cli.py                # Komut satırı arayüzü
└── __init__.py
```

---

## 🧠 Temel Bileşenler

### 1. **Ajanlar (Agents)**

Üç ana ajan, her biri JSON çıktısı döndürür:

#### **DirectorAgent** (`agents/director_agent.py`)
- **Görev:** Mevcut oyun durumuna ve oyuncu seçimine dayalı ajan "niyetini" (intent) belirle
- **Girdi:** Oyun durumu, oyuncu seçimi, tehdit snapshot'ı
- **Çıktı:** JSON
  ```json
  {
    "focus": "stabilize|explore|escalate",
    "summary": "İkinci duvar onarımı...",
    "risk_budget": 1-3,
    "scene_intent": {...}
  }
  ```
- **Model:** Mistral 7B (varsayılan)
- **Önemli:** Prompt şablonunda "few-shot" örnekleri ile birlikte tasarımcılar tarafından yazılmış sahne niyetleri

#### **PlannerAgent** (`agents/planner_agent.py`)
- **Görev:** Direktör niyetinden güvenli fonksiyon çağrılarının bir planını oluştur
- **Girdi:** Proyeksiyonlu durum, sahne niyeti, ön bellek
- **Çıktı:** JSON plan
  ```json
  {
    "gas": 1,
    "calls": [
      {
        "name": "reinforce_wall",
        "kwargs": {"structure_id": "western_wall", "amount": 2}
      }
    ]
  }
  ```
- **Model:** Phi-3 Mini
- **Önemli:** 
  - MAX_PLAN_CALLS = 3, MAX_PLAN_GAS = 3
  - Jsonschema doğrulama ile sert şema kontrolü
  - Fallback fonksiyonları ($schema hataları, eksik gas vb.)

#### **WorldRendererAgent** (`agents/world_renderer_agent.py`)
- **Görev:** Atmosfer, duysal detaylar ve ambient tanımı oluştur
- **Çıktı:** JSON
  ```json
  {
    "atmosphere": "Sisli bulutlar aşağıda asılı...",
    "sensory_details": "Islak toprak kokusu...",
    "ambient_sounds": "Uzak davullar..."
  }
  ```
- **Model:** Phi-3 Mini
- **Garantiler:** Boş atmosphere durumlarda deterministik fallback

---

### 2. **Durum Saklama (State Store)**

`core/state_store.py` — iki katmanlı tasarım:

#### **Sıcak Katman (RAM)**
- Oyuncu konumu, NPC konumları, metrikler, bayraklar
- JSON dosyasında tutulur: `data/world_state.json`
- Performans için bellek içinde

#### **Soğuk Katman (SQLite)**
- Uzun kronoloji, tüm olay geçmişi, tur kayıtları
- SQLite: `db/game_state.sqlite`
- `fortress_director/utils/sqlite_sync.py` tarafından senkron tutulur

#### **Ana Durumlar:**
```python
{
  "turn": 5,
  "turn_limit": 30,
  "rng_seed": 12345,
  "world": {
    "stability": 58,
    "resources": 82,
    "threat_level": "volatile"
  },
  "metrics": {
    "order": 60,
    "morale": 64,
    "resources": 82,
    "knowledge": 48,
    "glitch": 42,
    "combat": {...}
  },
  "npc_locations": [
    {"id": "scout_ila", "x": 3, "y": 4, "room": "north_wall", ...}
  ],
  "structures": {
    "western_wall": {"id": "western_wall", "integrity": 70, ...}
  },
  "map_event_markers": [...]
}
```

---

### 3. **Güvenli Fonksiyon Sistemi**

`core/function_registry.py` — 60+ deterministik "oyun etkisi" fonksiyonu:

#### **Kategoriler:**
- **Combat:** `apply_combat_pressure`, `ranged_attack`, `deploy_archers`
- **Morale:** `rally_morale`, `reduce_panic`
- **Resources:** `allocate_food`, `repair_structure`
- **Intel:** `scout_enemy_positions`, `gather_intelligence`
- **NPC:** `move_npc`, `set_npc_status`, `recruit_volunteer`

#### **Sema:**
```python
@dataclass
class SafeFunctionMeta:
    name: str                          # "reinforce_wall"
    category: str                      # "combat"
    description: str                   # "Kalıntıyı güçlendir"
    params: List[FunctionParam]        # [{"name": "structure_id", "type": "str", "required": True}]
    gas_cost: int = 1                  # Planner bütçesi
    planner_weight: float = 1.0        # Ajan tercihi
    enabled: bool = True
    handler: Callable | None = None    # Çalışma zamanı yürütücü
```

#### **Çalıştırma:**
```python
# pipeline/function_executor.py
plan = planner_agent.plan(...)
for call in plan["calls"]:
    func_meta = FUNCTION_REGISTRY[call["name"]]
    result = func_meta.handler(**call["kwargs"])
    state.apply_result(result)
```

---

### 4. **Tur Orkestrasyon**

`pipeline/turn_manager.py` — serialized (sırayla) tur akışı:

```
1. Snapshot durumu (tehdit modeli, olay grafiği)
   ↓
2. DirectorAgent → Niyeti oluştur
   ↓
3. WorldRendererAgent → Atmosferi oluştur
   ↓
4. PlannerAgent → Fonk. çağrılarını planla
   ↓
5. FunctionExecutor → Planı çalıştır, durumu güncelle
   ↓
6. ThreatModel/EventCurve → Otomatik sayaçları değiştir
   ↓
7. Persist → state.json + SQLite'a yaz
   ↓
8. TurnResult döndür (UI'ye gönder)
```

#### **TurnResult:**
```python
@dataclass
class TurnResult:
    narrative: str                     # Kurgulanmış hikaye metni
    ui_events: List[Dict]              # Harita güncelleme olayları
    player_options: List[Dict]         # Sonraki tur seçenekleri
    executed_actions: List[Dict]       # Güvenli fonk. sonuçları
    threat_snapshot: ThreatSnapshot    # Kaynaklar, kaynaklar vb.
    is_final: bool = False             # Sona ulaştı mı?
```

---

### 5. **LLM Entegrasyonu**

`llm/` — Ollama iletişimi ve model yönetimi

#### **Model Kayıtı** (`model_registry.py`)
```python
{
    "director": ModelConfig(name="mistral:latest", temperature=0.7, ...),
    "planner": ModelConfig(name="phi:latest", temperature=0.4, ...),
    "world_renderer": ModelConfig(name="phi:latest", temperature=0.6, ...),
}
```

#### **Ollama İstemcisi** (`ollama_client.py`)
```python
client = OllamaClient(base_url="http://localhost:11434")
response = client.generate(
    model="mistral:latest",
    prompt="...",
    stream=False,
    options={"temperature": 0.7, "num_predict": 512}
)
```

#### **Çalışma Modu** (`runtime_mode.py`)
- **Live:** Ollama'dan gerçek LLM çıktısı
- **Offline:** Önceden tanımlanmış fallback tepkileri (test/demo için)

#### **Profil & Metrikleri** (`profiler.py`)
- Her LLM çağrısı: latency, token sayısı, model adı
- Günlük: `logs/llm_calls.log`
- Telemetri: state'e kaydedilir

---

### 6. **Tema Sistemi**

`themes/` — Senaryo paketleri (JSON/YAML)

#### **Tema Yapısı:**
```json
{
  "id": "siege_default",
  "name": "Siege of Lornhaven",
  "description": "Kale kuşatması senaryosu",
  "npcs": [
    {
      "id": "scout_ila",
      "name": "Scout Ila",
      "role": "recon",
      "initial_x": 3,
      "initial_y": 4
    }
  ],
  "structures": [
    {
      "id": "western_wall",
      "kind": "wall",
      "integrity": 70
    }
  ],
  "safe_functions_enabled": [
    "reinforce_wall",
    "rally_morale",
    "allocate_food"
  ],
  "event_graph": {...}
}
```

#### **Yükleme:**
```python
from fortress_director.themes.loader import load_theme_from_file, BUILTIN_THEMES
theme_cfg = load_theme_from_file(BUILTIN_THEMES["siege_default"])
```

---

### 7. **Hikaye Grafiği & Finale**

`narrative/` — Etkinlik yönetimi ve sonlanış

#### **EventGraph** (`event_graph.py`)
- Düğümleri (sahneler), kenarları (geçişler)
- Her sahne: senaryo niyeti, oyuncu seçenekleri, sonraki düğümler
- Tema tarafından yüklenir

#### **FinalEngine** (`final_engine.py`)
- Metrik eşikleri kontrol et
- Son sahne hakkında karar ver
- Epilog şablonu renderin

#### **Evaluator** (`ending/evaluator.py`)
- Sonlanış puanı hesapla
- Oyuncuya özet geri döndür

---

## 📊 Veri Akışları

### **Tur Başı → Tur Sonu**

```
İnsan Girdisi (Oyuncu Seçimi)
    ↓
[run_turn(game_state, player_choice)]
    ↓
TurnManager.run_turn()
    ├─ threat_snapshot = ThreatModel.snapshot()
    ├─ director_intent = DirectorAgent(state, player_choice, threat_snapshot)
    ├─ atmosphere = WorldRendererAgent(state, director_intent)
    ├─ plan = PlannerAgent(state, director_intent)
    ├─ for call in plan["calls"]:
    │   └─ FunctionExecutor.execute(call, state) → Durumu güncelle
    ├─ state.apply_threat_tick() → Otomatik kaynaklar değişir
    ├─ state.persist() → JSON + SQLite'a yaz
    └─ TurnResult() → API'ye dön
    ↓
[Oyuncu Arayüzü Güncelle]
    ↓
Sonraki Tur veya Sonu
```

### **Veritabanı → Durum Oku/Yaz**

```
GameState.load()
    ├─ JSON sıcak katmanından oku: data/world_state.json
    └─ Metrikler, konum, bayraklar belleğe yükle

GameState.persist()
    ├─ Farkı hesapla (state_diff.py)
    ├─ data/history/turn_{N}.json'a yazma (diff)
    ├─ data/world_state.json'a yazma (tam)
    └─ SQLite senkronizasyonu (sqlite_sync.py)
```

---

## 🔍 Önemli Klasörler & Dosyalar

### **Yapılandırma**
- `settings.py` — Global ayarlar (modeller, bağlantı noktaları, log dizinleri)
- `demo_build/demo_config.yaml` — Demo runtime ayarları

### **Günlükleme & Veriler**
- `logs/` — LLM çağrıları, telemetri, tur günlükleri
- `data/world_state.json` — Geçerli oyun durumu
- `data/history/turn_*.json` — Tur farklılıkları
- `db/game_state.sqlite` — Tarihsel arşiv
- `runs/` — Senaryo çalıştırmaları ve performans raporları

### **Test Dosyaları**
- `tests/` — pytest paketleri (agents/, core/, pipeline/, llm/)
- `acceptance_tests/model_guardrail.jsonl` — LLM regresyon veri seti
- `pytest.ini` — pytest yapılandırması

### **Belgeler**
- `docs/architecture.md` — Bu yapı
- `docs/llm_setup.md` — Modelleri kurma
- `docs/safe_function_expansion_design.md` — Fonk. tasarımı
- `roadmap.md` — Faz planı
- `PROJECT_STATUS_REPORT.md` — Sorun/çözüm günlüğü

---

## 🚀 Çalıştırma

### **CLI (Tek Tur)**
```bash
python fortress_director/cli.py run_turn --state data/world_state.json
```

### **API (Sunucu)**
```bash
python -m uvicorn fortress_director.api:app --host 0.0.0.0 --port 8000
```

### **Demo (One-Command)**
```bash
# Windows PowerShell 7+
.\demo_build\run_demo.ps1

# Linux/macOS
./demo_build/run_demo.sh
```

### **Testler**
```bash
# Tüm testler
pytest tests/

# Ajan testleri
pytest tests/agents/ -v

# Entegrasyon testleri
pytest tests/pipeline/ -m integration
```

---

## ⚙️ Geliştirme İş Akışı

### **Yeni Güvenli Fonksiyon Ekleme**

1. **Fonksiyonu kaydet** (`core/function_registry.py`):
   ```python
   _CATEGORY_DEFINITIONS["my_category"] = [{
       "name": "my_function",
       "description": "...",
       "params": [...],
       "gas_cost": 2,
   }]
   ```

2. **İşleyici bağla** (`core/functions/impl/my_impl.py`):
   ```python
   def handler_my_function(param1: str, **kwargs) -> Dict[str, Any]:
       # İş mantığı
       return {"success": True, "message": "..."}
   
   bind_handler("my_function", handler_my_function)
   ```

3. **Test yaz** (`tests/core/test_my_function.py`):
   ```python
   def test_my_function():
       result = handler_my_function(param1="test")
       assert result["success"]
   ```

### **Promptu Güncellemek**

1. `fortress_director/prompts/{agent}_prompt.txt` dosyasını düzenle
2. Few-shot örneklerini veya format açıklamalarını iyileştir
3. Tüm ajan testlerini çalıştır:
   ```bash
   pytest tests/agents/ -v
   ```

### **Yeni Tema Paketi**

1. `fortress_director/themes/my_theme.json` oluştur
2. Schema doğrula: `fortress_director/themes/schema.py`
3. Temas yükleyiciyi kontrol et: `narrative/theme_graph_loader.py`

---

## 📈 Performans & İzleme

### **Telemetri Araçları**
- `tools/perf_watchdog.py` — Haftalık KPI raporu
- `tools/profile_turn.py` — Tur profili (latency, bellek)
- `tools/regression_runner.py` — Prompt/tema regresyonu testi

### **Kritik Yollar**
1. **LLM Gecikmesi** — DirectorAgent → PlannerAgent (>5 sn uyarı)
2. **Durum Persist** — JSON yazma + SQLite sync (<50 ms hedef)
3. **Bellek Büyümesi** — recent_events, npc_locations rotation

---

## 🧪 Test Stratejisi

### **Katman 1: Birim Testleri**
- Güvenli fonksiyon doğrulama/yürütme
- Domain model işlemleri (NPC move, Structure reinforce)
- Ajan prompt yapılandırması

### **Katman 2: Entegrasyon Testleri**
- Multi-tur sahneler (mocked LLM)
- Durum kalıcılığı & diff dosyaları
- Tehdit modeli + Event grafiği akışları

### **Katman 3: Kabul Testleri**
- LLM regresyonu: `acceptance_tests/model_guardrail.jsonl`
- Judge veto oranları izleme
- Safe function başarı/başarısızlık sayaçları

---

## 🎯 Kod Kuralları & Kural Kitabı

### **Kodu Yazarken**

1. **Öznitelikler:**
   - Serialized (paralel yok)
   - Atomik durum güncellemeleri
   - Sıkı JSON schemalar

2. **Ajan Çıktıları:**
   - Markdown yok, HTML yok → **Yalnız JSON**
   - Hiçbir kod bloğu kuşaklama değil
   - Eksik alanlar tahmin edilirse log kaydı düş

3. **Hata İşleme:**
   - Her `except` bloğunda loglama
   - Sessizce yutulan hatalar yasak
   - Fallback'ler deterministic ve sorumlu

4. **Modülü Test Etme:**
   - Birim testleri <500 ms
   - Entegrasyon testleri mocked LLM'ler ile çalışır
   - Senaryo dosyaları (JSON) offline testlere eklenebilir

---

## 📝 Dosya Referansları

| Dosya | Amaç |
|-------|------|
| `settings.py` | Global yapılandırma |
| `api.py` | FastAPI uygulaması |
| `cli.py` | Komut satırı arayüzü |
| `pipeline/turn_manager.py` | Tur orkestrasyon |
| `core/state_store.py` | Durum yönetimi |
| `core/function_registry.py` | Güvenli fonksiyon kataloğu |
| `agents/director_agent.py` | Niyeti belirle |
| `agents/planner_agent.py` | Fonksiyonları planla |
| `agents/world_renderer_agent.py` | Atmosferi oluştur |
| `llm/model_registry.py` | Model eşlemeleri |
| `llm/ollama_client.py` | Ollama HTTP istemcisi |
| `narrative/event_graph.py` | Etkinlik ağı |
| `ending/evaluator.py` | Sonlanış değerlendirmesi |
| `themes/loader.py` | Tema yükleme |
| `prompts/` | Ajan istemleri |
| `demo/` | Web UI ve CLI |

---

## 🔗 Bağlantılar & Kaynaklar

- **Architecture:** `docs/architecture.md`
- **LLM Kurulumu:** `docs/llm_setup.md`
- **Tema Paketleri:** `docs/theme_packages.md` + `docs/story_packs.md`
- **Safe Function Tasarımı:** `docs/safe_functions/safe_function_expansion_design.md`
- **Sorun Takibi:** `PROJECT_STATUS_REPORT.md`
- **Yol Haritası:** `roadmap.md`

---

## 📌 Özet

**Fortress Director**, aşağıdakilerle merkezi bir yapı sunan tutarlı bir oyun motorudur:

✅ **Deterministic:** Ajan kararları kurallar tarafından doğrulanır  
✅ **Modüler:** Ajanlar bağımsızdır, testleri izole edilir  
✅ **JSON-Native:** Tüm ajan çıktıları yapılandırılmış şemalar  
✅ **İzlenebilir:** Her LLM çağrısı, işlem ve durum değişikliği günlüğü  
✅ **Ölçeklenebilir:** Yeni temalar, fonksiyonlar, ajanlar modüler olarak eklenir  

**Sonuç:** Kale kuşatma senaryosunda, türler boyunca tutarlı hikaye anlatımını sağlayan production-ready bir AI oyun altyapısı.

