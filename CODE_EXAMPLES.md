# Fortress Director - Kod Örnekleri & Pratik Rehber

## 📚 Pratik Kod Örnekleri

### 1. Temel Tur Çalıştırması

```python
# fortress_director/cli.py'de kullanılan temel örnek

from fortress_director.core.state_store import GameState
from fortress_director.pipeline.turn_manager import run_turn

# Durumu yükle
game_state = GameState()
game_state.load()  # data/world_state.json'dan oku

# Oyuncu seçimini al
player_choice = "option_2"

# Turu çalıştır
result = run_turn(
    state=game_state,
    player_choice=player_choice
)

# Sonuç
print(f"Narrative: {result.narrative}")
print(f"Player Options: {result.player_options}")
print(f"Executed Actions: {result.executed_actions}")
print(f"Turn: {result.turn_number}")

# Durumu kaydet
game_state.persist()
```

---

### 2. DirectorAgent Kullanımı

```python
# agents/director_agent.py - Niyeti Belirle

from fortress_director.agents import DirectorAgent
from fortress_director.core.threat_model import ThreatModel

# Ajan oluştur
director = DirectorAgent(use_llm=True)

# Tehdit snapshot'ı
threat_model = ThreatModel({})
threat_snapshot = threat_model.snapshot(game_state)

# Niyeti oluştur
intent = director.generate_intent(
    projected_state=game_state.to_dict(),
    player_choice="option_1",
    threat_snapshot=threat_snapshot,
    event_seed="turn_5_critical",
    endgame_directive=None,
    event_node=None
)

# Sonuç
print(intent)
# {
#   "focus": "stabilize",
#   "summary": "Strengthen defenses before the evening assault",
#   "risk_budget": 1,
#   "player_options": [
#       {"id": "opt_1", "label": "Deploy masons", ...},
#       ...
#   ],
#   "notes": "Wall integrity declining."
# }
```

---

### 3. PlannerAgent Kullanımı

```python
# agents/planner_agent.py - Fonksiyon Planlaması

from fortress_director.agents import PlannerAgent

# Ajan oluştur
planner = PlannerAgent(use_llm=True)

# Prompt oluştur
prompt = planner.build_prompt(
    projected_state=game_state.to_dict(),
    scene_intent=director_intent,
    max_functions=3,
    call_limit=2
)

# LLM'den plan iste
plan = planner.plan(
    projected_state=game_state.to_dict(),
    scene_intent=director_intent
)

# Sonuç
print(plan)
# {
#   "gas": 2,
#   "calls": [
#       {
#           "name": "reinforce_wall",
#           "kwargs": {"structure_id": "western_wall", "amount": 2}
#       },
#       {
#           "name": "rally_morale",
#           "kwargs": {"boost": 5}
#       }
#   ]
# }

# Plan validation
if planner.validate_plan(plan):
    print("Plan is valid!")
else:
    print("Plan validation failed, using fallback")
```

---

### 4. Güvenli Fonksiyon Kayıt & Çalıştırma

```python
# core/function_registry.py - Fonksiyon Sistemi

from fortress_director.core.function_registry import (
    FUNCTION_REGISTRY,
    register_safe_function,
    bind_handler,
    load_defaults
)
from fortress_director.core.functions.function_schema import SafeFunctionMeta, FunctionParam

# 1. Tüm fonksiyonları yükle (bootstrap)
load_defaults()

# 2. Kayıtlı fonksiyonları kontrol et
print(f"Total functions: {len(FUNCTION_REGISTRY)}")
for name, meta in FUNCTION_REGISTRY.items():
    print(f"  - {name}: {meta.description} (gas: {meta.gas_cost})")

# 3. Belirli bir fonksiyonu al
func_meta = FUNCTION_REGISTRY["reinforce_wall"]
print(f"Function: {func_meta.name}")
print(f"Params: {[(p.name, p.type) for p in func_meta.params]}")

# 4. Yeni fonksiyon kaydet
new_func = SafeFunctionMeta(
    name="custom_signal",
    category="intel",
    description="Send signal to allies",
    params=[
        FunctionParam(name="message", type="str", required=True),
        FunctionParam(name="range_km", type="int", required=False)
    ],
    gas_cost=1,
    planner_weight=1.2
)
register_safe_function(new_func)

# 5. İşleyici bağla
def handler_custom_signal(message: str, range_km: int = 5, **kwargs):
    return {
        "success": True,
        "signal_sent": True,
        "recipients": ["allied_garrison", "nearby_scout"],
        "message": message
    }

bind_handler("custom_signal", handler_custom_signal)

# 6. Fonksiyonu çalıştır
result = func_meta.handler(message="Breach imminent!", range_km=10)
print(result)
```

---

### 5. Durum Saklama & Kalıcılık

```python
# core/state_store.py - Durum Yönetimi

from fortress_director.core.state_store import GameState
from fortress_director.utils.state_diff import compute_state_diff

# Durumu yükle
state = GameState()
state.load()  # data/world_state.json

print(f"Turn: {state.data['turn']}")
print(f"Morale: {state.data['metrics']['morale']}")

# Durumu değiştir
state.data["metrics"]["morale"] -= 5
state.data["npc_locations"][0]["x"] = 8  # NPC'yi taşı

# Diff hesapla
diff = compute_state_diff(
    old_state=state._last_persisted or {},
    new_state=state.data
)
print(f"Diff: {diff}")
# {
#   "metrics": {"morale": -5},
#   "npc_locations.0.x": 8
# }

# Kalıcılığa gönder
state.persist()
# → Yazar data/world_state.json (full)
# → Yazar data/history/turn_5.json (diff)
# → Senkronize db/game_state.sqlite

# SQLite'tan geri oku
archived_turn = state.load_from_history(turn_number=3)
print(f"Turn 3 state: {archived_turn}")
```

---

### 6. LLM Model Kayıt Yönetimi

```python
# llm/model_registry.py - Model Yapılandırması

from fortress_director.llm.model_registry import get_registry, ModelConfig
from fortress_director.settings import SETTINGS

# Singleton kayıt tablosunu al
registry = get_registry()

# Tüm modelleri listele
for record in registry.list():
    print(f"Agent: {record.agent}")
    print(f"  Model: {record.config.name}")
    print(f"  Temperature: {record.config.temperature}")
    print(f"  Max Tokens: {record.config.max_tokens}")

# Belirli bir ajan için model al
director_config = registry.get("director")
print(f"Director uses: {director_config.name}")

# Oluşturma seçeneklerini hazırla
options = registry.build_generation_options(
    "director",
    overrides={"temperature": 0.5}  # Ovverride
)
print(f"Generation options: {options}")
# {
#   "temperature": 0.5,
#   "top_p": 0.9,
#   "top_k": 40,
#   "num_predict": 512
# }

# Ollama istemcisi
from fortress_director.llm.ollama_client import OllamaClient

client = OllamaClient(base_url="http://localhost:11434")
response = client.generate(
    model=director_config.name,
    prompt="Describe a fortress under siege...",
    stream=False,
    options=options
)
print(f"LLM Response: {response}")
```

---

### 7. Tema Paketleri Yükleme & Kullanma

```python
# themes/loader.py - Tema Sistemi

from fortress_director.themes.loader import load_theme_from_file, BUILTIN_THEMES
from fortress_director.themes.schema import ThemeConfig

# Yerleşik tema yükle
default_theme = load_theme_from_file(BUILTIN_THEMES["siege_default"])

print(f"Theme: {default_theme.id}")
print(f"Name: {default_theme.name}")
print(f"Description: {default_theme.description}")

# NPC'leri incele
for npc in default_theme.npcs:
    print(f"  - {npc.name} ({npc.id}): {npc.role}")

# Yapıları incele
for struct in default_theme.structures:
    print(f"  - {struct.id}: {struct.kind} @ ({struct.x}, {struct.y})")

# Etkinlik grafiğini yükle
from fortress_director.narrative.theme_graph_loader import load_event_graph_for_theme
event_graph = load_event_graph_for_theme(default_theme)

print(f"Event graph nodes: {len(event_graph.nodes)}")
for node_id, node in event_graph.nodes.items():
    print(f"  - {node_id}: {node.description}")

# Özel tema oluştur & kaydet
custom_theme = ThemeConfig(
    id="my_custom_scenario",
    name="Custom Fortress",
    description="My own scenario",
    npcs=[...],
    structures=[...],
    safe_functions_enabled=["reinforce_wall", "rally_morale", ...],
    safe_functions_disabled=[],
    event_graph_config={...}
)

import json
with open("fortress_director/themes/my_custom.json", "w") as f:
    json.dump(custom_theme.to_dict(), f, indent=2)
```

---

### 8. İşletme Hattı - Tam Örnek

```python
# pipeline/turn_manager.py - Tam Tur Akışı

from fortress_director.pipeline.turn_manager import TurnManager, run_turn
from fortress_director.core.state_store import GameState
from fortress_director.agents import DirectorAgent, PlannerAgent, WorldRendererAgent

# Tür yöneticisini başlat
turn_mgr = TurnManager(
    director_agent=DirectorAgent(use_llm=True),
    planner_agent=PlannerAgent(use_llm=True),
    world_renderer_agent=WorldRendererAgent(use_llm=True),
)

# Durumu yükle
state = GameState()
state.load()

# Oyuncu seçimi simüle et
player_choice = "option_1"

# Tam tur çalıştırması
try:
    result = run_turn(
        state=state,
        player_choice=player_choice
    )
    
    print("=== TURN RESULT ===")
    print(f"Narrative: {result.narrative}")
    print(f"\nAtmosphere: {result.atmosphere}")
    print(f"\nExecuted Actions:")
    for action in result.executed_actions:
        print(f"  - {action['name']}: {action.get('description', 'N/A')}")
    
    print(f"\nThreat Level: {result.threat_snapshot.current_threat}")
    print(f"Metrics: {result.threat_snapshot.core_metrics}")
    
    if result.is_final:
        print(f"\n*** GAME ENDED ***")
        print(f"Ending: {result.ending_id}")
        print(f"Summary: {result.final_payload}")
    else:
        print(f"\nNext Turn Options:")
        for opt in result.player_options:
            print(f"  - {opt['id']}: {opt['label']}")
    
    # Durumu kaydet
    state.persist()
    
except Exception as e:
    print(f"Turn failed: {e}")
    import traceback
    traceback.print_exc()
```

---

### 9. API Örneği (FastAPI)

```python
# api.py - REST Endpoints

from fastapi import FastAPI, Query
from pydantic import BaseModel
from fortress_director.core.state_store import GameState
from fortress_director.pipeline.turn_manager import run_turn

app = FastAPI()
_GAME_STATE = GameState()

class PlayerChoiceRequest(BaseModel):
    choice: str

@app.on_event("startup")
async def startup():
    """Başlangıçta durumu yükle"""
    _GAME_STATE.load()

@app.get("/state")
def get_state():
    """Mevcut oyun durumunu döndür"""
    return _GAME_STATE.to_dict()

@app.get("/metrics")
def get_metrics():
    """Metrikleri döndür"""
    return _GAME_STATE.data.get("metrics", {})

@app.post("/choose")
def choose_action(req: PlayerChoiceRequest):
    """Oyuncu seçimi işle ve turu çalıştır"""
    try:
        result = run_turn(
            state=_GAME_STATE,
            player_choice=req.choice
        )
        _GAME_STATE.persist()
        
        return {
            "success": True,
            "turn": result.turn_number,
            "narrative": result.narrative,
            "ui_events": result.ui_events,
            "next_options": result.player_options,
            "is_final": result.is_final
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/health")
def health_check():
    """Sistem durumunu kontrol et"""
    return {
        "status": "ok",
        "turn": _GAME_STATE.data.get("turn", 0),
        "game_state": "loaded"
    }

# Çalıştır: uvicorn fortress_director.api:app --host 0.0.0.0 --port 8000
```

---

### 10. Test Örneği

```python
# tests/agents/test_director_agent.py - Birim Testi

import pytest
from fortress_director.agents import DirectorAgent
from fortress_director.core.state_store import GameState
from fortress_director.core.threat_model import ThreatModel

class TestDirectorAgent:
    
    @pytest.fixture
    def agent(self):
        """DirectorAgent fixture"""
        return DirectorAgent(use_llm=False)  # Offline mode
    
    @pytest.fixture
    def state(self):
        """GameState fixture"""
        state = GameState()
        state.load()
        return state
    
    def test_generate_intent_returns_dict(self, agent, state):
        """Intent oluşturma dict döndürür"""
        intent = agent.generate_intent(
            projected_state=state.to_dict(),
            player_choice="option_1",
            threat_snapshot=ThreatModel({}).snapshot(state),
            event_seed=None,
            endgame_directive=None,
            event_node=None
        )
        
        assert isinstance(intent, dict)
        assert "focus" in intent
        assert "summary" in intent
    
    def test_intent_focus_is_valid(self, agent, state):
        """Focus alanı geçerli bir değere sahip"""
        intent = agent.generate_intent(
            projected_state=state.to_dict(),
            player_choice="option_1",
            threat_snapshot=ThreatModel({}).snapshot(state),
            event_seed=None,
            endgame_directive=None,
            event_node=None
        )
        
        assert intent["focus"] in ["stabilize", "explore", "escalate"]
    
    def test_intent_has_player_options(self, agent, state):
        """Intent oyuncu seçeneklerini içerir"""
        intent = agent.generate_intent(
            projected_state=state.to_dict(),
            player_choice=None,
            threat_snapshot=ThreatModel({}).snapshot(state),
            event_seed=None,
            endgame_directive=None,
            event_node=None
        )
        
        assert "player_options" in intent
        assert len(intent["player_options"]) == 3
        for opt in intent["player_options"]:
            assert "id" in opt
            assert "label" in opt

# Çalıştır: pytest tests/agents/test_director_agent.py -v
```

---

### 11. Entegrasyon Testi

```python
# tests/pipeline/test_full_turn_integration.py - Entegrasyon Testi

import pytest
from fortress_director.core.state_store import GameState
from fortress_director.pipeline.turn_manager import run_turn

@pytest.mark.integration
class TestFullTurnFlow:
    
    @pytest.fixture
    def fresh_game(self):
        """Yeni oyun durumu"""
        state = GameState()
        state.load()
        return state
    
    @pytest.mark.integration
    def test_full_turn_completes(self, fresh_game):
        """Tam tur başarıyla tamamlanır"""
        result = run_turn(
            state=fresh_game,
            player_choice="option_1"
        )
        
        assert result.turn_number >= 0
        assert result.narrative
        assert len(result.player_options) > 0
        assert result.executed_actions is not None
    
    @pytest.mark.integration
    def test_state_persists_after_turn(self, fresh_game):
        """Durum turdan sonra kalıcı"""
        old_turn = fresh_game.data["turn"]
        
        result = run_turn(
            state=fresh_game,
            player_choice="option_1"
        )
        fresh_game.persist()
        
        # Yeniden yükle
        reloaded = GameState()
        reloaded.load()
        
        # Turn sayısı artmış
        assert reloaded.data["turn"] > old_turn
    
    @pytest.mark.integration
    def test_multiple_turns_flow(self, fresh_game):
        """Çoklu tur akışı işler"""
        for i in range(3):
            result = run_turn(
                state=fresh_game,
                player_choice=["option_1", "option_2", "option_3"][i % 3]
            )
            assert result.narrative
            fresh_game.persist()
        
        assert fresh_game.data["turn"] >= 3

# Çalıştır: pytest tests/pipeline/test_full_turn_integration.py -v -m integration
```

---

### 12. Tema Oluşturma Örneği

```python
# themes/my_custom_scenario.json - Tema Paket Şablonu

{
  "id": "forest_refuge",
  "name": "Forest Refuge",
  "description": "Small town sheltering refugees in an ancient forest",
  "grid_size": 12,
  "npcs": [
    {
      "id": "elder_miriam",
      "name": "Elder Miriam",
      "role": "leader",
      "summary": "Wise elder guiding the refugees",
      "initial_x": 5,
      "initial_y": 6,
      "health": 80,
      "morale": 75
    },
    {
      "id": "scout_kael",
      "name": "Scout Kael",
      "role": "recon",
      "summary": "Young scout watching the perimeter",
      "initial_x": 2,
      "initial_y": 3,
      "health": 100,
      "morale": 60
    }
  ],
  "structures": [
    {
      "id": "watchtower",
      "kind": "tower",
      "x": 1,
      "y": 1,
      "integrity": 60,
      "max_integrity": 100
    },
    {
      "id": "main_shelter",
      "kind": "building",
      "x": 5,
      "y": 6,
      "integrity": 85,
      "max_integrity": 100
    }
  ],
  "initial_metrics": {
    "order": 50,
    "morale": 55,
    "resources": 70,
    "knowledge": 40,
    "glitch": 20
  },
  "safe_functions_enabled": [
    "rally_morale",
    "gather_intelligence",
    "scout_perimeter",
    "fortify_combat_zone",
    "repair_structure"
  ],
  "safe_functions_disabled": [
    "melee_engagement",
    "ranged_attack"
  ],
  "turn_limit": 25,
  "events": [
    {
      "id": "event_refugees_arrive",
      "turn": 1,
      "description": "First wave of refugees reaches the forest"
    }
  ]
}
```

---

## 🔍 Hata Ayıklama İpuçları

### **Problem: LLM çıktısı JSON değil**

```python
# logs/fortress_run.log'ı kontrol et
# TypeError: Object of type ... is not JSON serializable

# Çözüm:
# 1. Prompt'u daha sıkı yap (docs/architecture.md)
# 2. Temperature'ı düşür
# 3. Offline mode'de test et

from fortress_director.llm.runtime_mode import set_llm_enabled
set_llm_enabled(False)  # Offline testler
```

### **Problem: Durum persist edilmiyor**

```python
# Kontrol:
# 1. data/ ve db/ dizinleri mevcut mu?
# 2. Dosya izinleri doğru mu?
# 3. SQLite kilitli mi?

import os
print(os.access("data/", os.W_OK))  # Yazılabilir mi?
print(os.path.exists("db/game_state.sqlite"))  # DB var mı?
```

### **Problem: Güvenli fonksiyon başarısız**

```python
# Adım-adım debugging:
from fortress_director.core.function_registry import FUNCTION_REGISTRY

func_meta = FUNCTION_REGISTRY["my_function"]
print(f"Handler: {func_meta.handler}")
print(f"Params: {[p.name for p in func_meta.params]}")

# Test et:
try:
    result = func_meta.handler(param1="test")
    print(f"Success: {result}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
```

---

## 📖 Daha Fazla Bilgi

- **API Referansı:** `/health` endpoint'i kontrol et
- **Telemetri:** `logs/llm_calls.log` ve `logs/turn_perf.log`
- **Tema Doğrulama:** `fortress_director/themes/schema.py`
- **Prompt Şablonları:** `fortress_director/prompts/`

---

Bu rehber **pratik kod örnekleri** ile Fortress Director'ı başlatmanız için yeterli bir başlangıç sunmaktadır!

