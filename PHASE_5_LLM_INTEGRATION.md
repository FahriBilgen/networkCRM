# FAZ 5 – GERÇEK LLM ENTEGRASYONU

**Amaç:** Stub agent'ları gerçek Ollama LLM çağrılarıyla değiştirmek, oyunu tam dinamik hale getirmek.

**Süre Tahmini:** 4-6 saat  
**Önkoşul:** Ollama kurulu ve çalışır durumda (`ollama serve`)

---

## Task 5.1 – Director Agent LLM Entegrasyonu

**Goal:** DirectorAgent'ın scene intent ve player options üretmesini LLM'e yaptırmak.

**Adımlar:**

1. **Prompt Template Oluştur:**
   - `fortress_director/prompts/director_prompt.txt` dosyasını düzenle/oluştur
   - Projected state, metrics, recent events kullan
   - Few-shot examples ekle (2-3 örnek scene intent)
   - Output format: JSON (scene_intent + player_options)

2. **OllamaClient Entegre Et:**
   ```python
   # fortress_director/agents/director_agent.py
   from fortress_director.llm.ollama_client import OllamaClient
   
   class DirectorAgent:
       def __init__(self, llm_client=None, model="mistral"):
           self._llm_client = llm_client or OllamaClient()
           self._model = model
   
       def generate_intent(self, projected_state, player_choice):
           prompt = self._build_prompt(projected_state, player_choice)
           response = self._llm_client.generate(
               model=self._model,
               prompt=prompt,
               response_format="json"
           )
           return self._parse_output(response)
   ```

3. **Output Parser Yaz:**
   - JSON parse ve validation
   - Schema: `{"scene_intent": {...}, "player_options": [...]}`
   - Fallback: Parse başarısız olursa stub output dön

**Tamamlanma Kriteri:**
- `tests/agents/test_director_llm.py` yaz
- Mock Ollama response ile test et
- Gerçek Ollama ile manuel test: `pytest tests/agents/test_director_llm.py -v`

---

## Task 5.2 – Planner Agent LLM Entegrasyonu

**Goal:** PlannerAgent'ın safe function çağrılarını LLM'den alması.

**Adımlar:**

1. **Mevcut Prompt'u Güncelle:**
   - `planner_agent.py` içindeki `build_prompt()` zaten hazır
   - Cluster manager ile relevant functions filtreleniyor ✅
   - Few-shot examples mevcut ✅

2. **LLM Çağrısını Ekle:**
   ```python
   def plan_actions(self, projected_state, scene_intent):
       prompt = self.build_prompt(projected_state, scene_intent)
       
       # LLM'e gönder
       response = self._llm_client.generate(
           model=self._model,  # "mistral" veya "qwen"
           prompt=prompt,
           response_format="json",
           options={"temperature": 0.7, "top_p": 0.9}
       )
       
       # Parse ve validate
       try:
           validated = self.validate_llm_output(response["response"])
           actions = [{"function": c["name"], "args": c["kwargs"]} 
                      for c in validated["calls"]]
       except Exception:
           # Fallback to deterministic plan
           validated = self._build_fallback_plan(projected_state, scene_intent)
           actions = ...
       
       return {"prompt": prompt, "raw_plan": validated, "planned_actions": actions}
   ```

3. **Error Handling Ekle:**
   - LLM timeout → fallback plan
   - Invalid JSON → fallback plan
   - Schema validation fail → fallback plan
   - Log all failures for debugging

**Tamamlanma Kriteri:**
- `tests/agents/test_planner_llm.py` yaz
- Mock LLM output ile valid/invalid case'leri test et
- Gerçek Ollama ile 5 turn test: her turn'de LLM'den plan gelmeli

---

## Task 5.3 – WorldRenderer Agent LLM Entegrasyonu

**Goal:** Narrative text ve NPC dialoglarını LLM'den üretmek.

**Adımlar:**

1. **Prompt Template Oluştur:**
   - `fortress_director/prompts/world_renderer_prompt.txt` oluştur
   - Input: executed_actions, state_delta, atmosphere cues
   - Output: JSON `{"narrative_block": str, "npc_dialogues": [...], "atmosphere": {...}}`
   - Theme-specific flavor (siege_default için)

2. **WorldRendererAgent'ı Güncelle:**
   ```python
   # fortress_director/agents/world_renderer_agent.py
   class WorldRendererAgent:
       def __init__(self, llm_client=None, model="phi-3"):
           self._llm_client = llm_client or OllamaClient()
           self._model = model
   
       def render(self, world_state, executed_actions):
           prompt = self._build_prompt(world_state, executed_actions)
           response = self._llm_client.generate(
               model=self._model,
               prompt=prompt,
               response_format="json"
           )
           return self._parse_output(response)
   ```

3. **Fallback Template Sistemi:**
   - LLM başarısız olursa şu anki template-based output kullan
   - Deterministic + LLM hybrid yaklaşım

**Tamamlanma Kriteri:**
- `tests/agents/test_world_renderer_llm.py` yaz
- Mock output ile test
- Gerçek Ollama ile narrative kalitesini kontrol et

---

## Task 5.4 – LLM Configuration & Model Management

**Goal:** Farklı modelleri kolayca değiştirebilmek.

**Adımlar:**

1. **Config Dosyasını Güncelle:**
   ```yaml
   # fortress_director/config/settings.yaml
   llm:
     ollama:
       base_url: "http://localhost:11434/"
       timeout: 240.0
     models:
       director: "mistral:7b"
       planner: "qwen:1.5b"
       world_renderer: "phi-3:mini"
     options:
       temperature: 0.7
       top_p: 0.9
       top_k: 40
   ```

2. **Model Registry Oluştur:**
   ```python
   # fortress_director/llm/model_registry.py
   from dataclasses import dataclass
   
   @dataclass
   class ModelConfig:
       name: str
       temperature: float = 0.7
       top_p: float = 0.9
   
   DEFAULT_MODELS = {
       "director": ModelConfig("mistral:7b", temperature=0.8),
       "planner": ModelConfig("qwen:1.5b", temperature=0.6),
       "world_renderer": ModelConfig("phi-3:mini", temperature=0.9),
   }
   ```

3. **Health Check Tool:**
   ```python
   # scripts/dev_tools.py'ye ekle
   def check_llm_health():
       """Verify Ollama is running and models are available."""
       client = OllamaClient()
       for agent, model in DEFAULT_MODELS.items():
           try:
               client.generate(model=model.name, prompt="test", options={"max_tokens": 1})
               print(f"✅ {agent}: {model.name} OK")
           except Exception as e:
               print(f"❌ {agent}: {model.name} FAIL - {e}")
   ```

**Tamamlanma Kriteri:**
- `py scripts/dev_tools.py check_llm` komutu çalışıyor
- Agent'lar config'den model okuyabiliyor
- Model değiştirme settings.yaml'dan yapılabiliyor

---

## Task 5.5 – End-to-End LLM Test

**Goal:** Tüm pipeline'ı gerçek LLM ile test etmek.

**Adımlar:**

1. **Integration Test Yaz:**
   ```python
   # tests/integration/test_llm_pipeline.py
   import pytest
   from fortress_director.pipeline.turn_manager import run_turn
   
   @pytest.mark.integration
   def test_full_turn_with_llm():
       """Run one turn with real LLM calls."""
       result = run_turn(player_choice="option_1")
       assert result["narrative"]
       assert len(result["executed_actions"]) > 0
       assert result["player_options"]
   
   @pytest.mark.integration
   def test_golden_path_with_llm():
       """Run 7-turn demo scenario with LLM."""
       for turn in range(7):
           result = run_turn(player_choice=f"option_{(turn % 3) + 1}")
           assert "stability" in result.get("hud", {})
   ```

2. **Performance Benchmark:**
   ```python
   def benchmark_llm_latency():
       """Measure average turn time with LLM."""
       import time
       times = []
       for _ in range(10):
           start = time.time()
           run_turn(player_choice="option_1")
           times.append(time.time() - start)
       print(f"Avg turn time: {sum(times)/len(times):.2f}s")
   ```

3. **Quality Assurance:**
   - 10 turn çalıştır, narrative'leri oku
   - Tutarlılık kontrolü (NPC isimleri, location'lar)
   - Function çağrıları mantıklı mı?

**Tamamlanma Kriteri:**
- Integration testler geçiyor
- Ortalama turn süresi < 10 saniye
- Narrative kalitesi kabul edilebilir

---

## Task 5.6 – UI'da LLM Status Gösterimi

**Goal:** Kullanıcı LLM çalışıp çalışmadığını görebilmeli.

**Adımlar:**

1. **Backend Status Endpoint:**
   ```python
   # fortress_director/api.py
   @app.get("/api/status")
   def get_status():
       """Return system health including LLM availability."""
       llm_health = {}
       for agent, model in DEFAULT_MODELS.items():
           try:
               client.generate(model=model.name, prompt="ping", options={"max_tokens": 1})
               llm_health[agent] = "online"
           except:
               llm_health[agent] = "offline"
       return {"llm": llm_health, "version": API_VERSION}
   ```

2. **UI Status Indicator:**
   - HUD'da veya Debug Panel'de LLM status göster
   - 🟢 Online / 🔴 Offline / 🟡 Fallback Mode

3. **Fallback Mode Toggle:**
   - Settings'ten "Use Stub Agents" toggle ekle
   - Demo için LLM kapalı gösterebilme

**Tamamlanma Kriteri:**
- UI'da LLM status görünüyor
- Ollama kapatınca "offline" gösteriyor
- Fallback mode çalışıyor

---

## 📊 Faz 5 Başarı Kriterleri

✅ **Director Agent:**
- LLM'den scene intent ve player options alıyor
- Parse hatası olunca fallback çalışıyor
- Test coverage > %80

✅ **Planner Agent:**
- LLM'den safe function planı alıyor
- Cluster manager ile prompt optimize
- Validation + fallback mekanizması

✅ **WorldRenderer Agent:**
- LLM'den narrative üretiyor
- NPC dialogları dinamik
- Atmosphere cues çalışıyor

✅ **Configuration:**
- Model seçimi config'den yapılabiliyor
- LLM health check çalışıyor
- Performance kabul edilebilir (<10s/turn)

✅ **Integration:**
- 7-turn Golden Path LLM ile çalışıyor
- Smoke test 20 run geçiyor
- UI'da LLM status görünüyor

---

## 🚀 Deployment Checklist

- [ ] Ollama kurulum dokümantasyonu (`docs/llm_setup.md`)
- [ ] Model indirme scripti (`scripts/download_models.sh`)
- [ ] Environment variable setup (`.env.example`)
- [ ] LLM olmadan da çalışma modu (offline/demo mode)
- [ ] Error logging ve monitoring

---

## 📝 Notlar

**Model Önerileri:**
- **Director**: Mistral 7B (reasoning + options generation)
- **Planner**: Qwen 1.5B (hızlı, function calling için yeterli)
- **WorldRenderer**: Phi-3 Mini (creative narrative için iyi)

**Alternatif:**
- Hepsi için Llama 3.1 8B (tek model, tutarlılık)
- GPT-4 API (cloud, daha kaliteli ama maliyet)

**Performance Tips:**
- Planner için caching (aynı context → aynı plan)
- Parallel LLM calls (3 agent async olabilir)
- Prompt optimization (token sayısını azalt)
