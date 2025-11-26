# Live Model Perf Pilot

Amaç: Offline (stub) modeller ile gerçek Ollama modelleri arasındaki tur süresi, agent gecikmesi ve safe-function IO farkını düzenli olarak ölçmek.

## Önkoşullar
1. Ollama servisleri çalışır durumda olmalı (`OLLAMA_HOST`, `OLLAMA_PORT` vs.).
2. `FORTRESS_USE_OLLAMA=1` veya ortamınızda gerçek modelleri zorunlu tutan ayarlar açık olmalı.
3. Çalışmayı ayrı bir run klasöründe saklayın (`runs/perf_reports/live_*`).

### LLM profil ayarları
- Düşük gecikme hedefi için `FORTRESS_LLM_PROFILE=latency` kullanın. Bu profil Event/World/Judge ajanlarını sırayla `q4_k_mistral`, `phi3_adapter_v1`, `qwen_guard_v2` varyantlarına geçirir ve başlatırken ilgili quantized/adaptor dosyalarını önbelleğe okur.
- Belirli ajanlar için manuel seçim gerekiyorsa `FORTRESS_MODEL_VARIANTS=event=q4_k_mistral,judge=default` biçiminde virgülle ayrılmış map verin. Bu değer ortam profiliyle birleşir.
- Yerel disk IO’su kısıtlıysa önbellek ısıtmayı kapatmak için `FORTRESS_SKIP_MODEL_PREFETCH=1` ayarlayın veya okuma baytını `FORTRESS_MODEL_PREFETCH_BYTES` ile düşürün (varsayılan 65536).
- Telemetri çıktısındaki `llm_profile`, `llm_variants` ve `llm_cache_prefetch` alanları hangi varyantların kullanıldığını ve cache ısıtma durumunu raporlar; 3 sn tur hedefini izlerken bu alanları kaydedin.
- Go/No-Go kriterleri UI’daki “Pilot KPI Monitor” kartına yansıtılır. Hard limit: `turn_duration_ms <= 3000` (aşılırsa NO-GO). Yumuşak izleme limitleri: `map_fn_latency_ms <= 400` ve mikro aksiyon çakışmaları `<= 2`. Bu limitler üstüne çıktığında durum WATCH moduna düşer.

## Komut Akışı
```bash
python tools/perf_watchdog.py \
  --turns 3 \
  --live-models \
  --random-choice \
  --reset-state \
  --tag live_pilot \
  --report-dir runs/perf_reports
```

Bu komut:
- Offline profille aynı metrikleri toplar (`map_fn_latency_ms`, `snapshot_batch_ms`, agent ortalamaları).
- Markdown + JSON raporlarını `runs/perf_reports/perf_report_<timestamp>.*` olarak üretir.

Karşılaştırma için aynı komutu `--live-models` olmadan çalıştırıp iki raporu diffleyin.

## Beklenen Çıktılar
- Markdown raporda ek “Meta Progression” ve “Map safe function” bölümleri canlı verilerle dolmalı.
- JSON özetindeki `avg_turn_duration_s` canlı koşuda 3s hedefini aşarsa backlog’a not alın.
- `meta_share_card_rate` gibi telemetri alanlarını da kontrol edin; canlı koşu share-card üretimini engellememeli.

## Sonuçları Paylaşma
- Markdown raporunu Confluence / Notion vb. ortama yapıştırın.
- JSON özetini `tools/kpi_digest.py` ile birleştirip haftalık KPI pipeline’ına ekleyin.
- Roadmap notlarına “Live Pilot” alt maddesi olarak tarih & rapor yolunu yazın.
