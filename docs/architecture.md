# Fortress Director Architecture

Bu belge, FAZ CLEANUP sonrası hedeflenen klasör düzeni ve ana bileşenlerin sorumluluklarını özetler.

```
fortress_director/
├── agents/           # Director, Event, Planner, Character, Judge, Creativity
├── core/             # StateStore, MetricManager, rules, persistence altyapısı
├── pipeline/         # Turn yürütücüsü, scheduler, safe function kuyruğu
├── llm/              # Model kayıtları, istemciler, profiler, runtime modları
├── ending/           # Finale/epilog sahneleri ve aktörleri (yeni faz)
├── demo/             # UI + CLI yüzeyleri; web istemcisi ve demo konfigleri
├── prompts/          # Ajan prompt şablonları ve yardımcı dosyalar
└── tests/            # Modül bazlı pytest paketleri (agents/core/pipeline/…)
```

## Katmanlar

### Agents
- Her ajan tek sorumluluk prensibi ile çalışır; `agents/__init__.py` yalnızca kayıt/pydantic modellerini dışa aktarır.
- Ajan çıktıları `pipeline.turn_manager` tarafından normalize edilir, `safe_function_specs` ve `prompt_runtime` yardımcılarını kullanır.

### Core
- `core/state_store.py`, `core/state_store_layers.py` sıcak/soğuk katman yönetimini üstlenir.
- `core/rules_engine.py` deterministik dünya güncellemelerini uygular; `core/metrics_manager.py` skor panosunu yönetir.
- `core/sqlite_sync.py` sıcak (JSON) ve soğuk (SQLite/history) kopyaları senkronize eder.

### Pipeline
- `pipeline/turn_manager.py` orkestrasyon giriş noktasıdır.
- Modüler aşamalar: snapshot, director stage, world/event/creativity/planner/character, judge, safe function kuyruğu, persist.
- `pipeline/function_executor.py` güvenli fonksiyon çağrılarını kaynak etiketleriyle işletir; `pipeline/state_projection.py` oyuncu görünümünü hazırlar.

### LLM
- `llm/model_registry.py` -> hangi ajan hangi modeli kullanacak bilgisini merkezi tutar.
- `llm/ollama_client.py` + `llm/runtime_mode.py` canlı model/ deterministik fallback seçimlerini sağlar.
- `llm/profiler.py` her çağrıyı `logs/llm_calls.log` dosyasına işler.

### Ending
- Finale spesifik scriptler, metrik eşikleri, epilog üreticileri burada tutulur. (Yeni oluşturulan klasör; mevcut kod buraya taşınacak.)

### Demo
- CLI (`scripts/dev_tools.py`) ve web UI (`demo/web/`) için paylaşılan varlıklar.
- `demo/config/` altında sahne/derece ayarları planlanır; UI paketleri bu klasörden servis edilir.

### Prompts
- Ajana özgü prompt dosyaları (`character_prompt.txt` vb.) ve yardımcı şablonlar (`prompts/utils.py`).
- Prompt güncellemeleri için sürüm notları `docs/` altında tutulur.

### Tests
- Yeni yapı ile her modülün testleri `fortress_director/tests/<module>/...` yoluna taşınacak.
- `pytest.ini` `testpaths = fortress_director/tests` olarak güncellenecek.

## Veri ve Log Ağaçları
- `runs/` ve `logs/` klasörleri koddan ayrıdır; cleanup script’leri (`scripts/repo_audit.py`, `scripts/cleanup_summary.py`) bu klasörler üzerinden rapor üretir.
- `fortress_director/_offline_runtime/` geliştirici kayıtlarını tutar; prod kodu tarafından direkt kullanılmaz.

## Gelecek Adımlar
1. `fortress_director/demo/` ve `fortress_director/ending/` klasörlerine mevcut UI/finishing kodları taşınacak.
2. `tests/` üst dizini, `fortress_director/tests/` içine aktarılıp import yolları güncellenecek.
3. `core/` ve `pipeline/` altındaki safe function yürütücüleri, yeni `safe_cleanup` raporlarıyla tutarlı hale getirilecek.

Bu yapı, ajan katmanları ile pipeline arasındaki sınırları keskinleştirir, dead code temizliğini kolaylaştırır ve demo/ending fazları için net bir genişleme alanı sağlar.

