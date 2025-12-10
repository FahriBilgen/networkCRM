# Legacy Design Reference

Bu dosya, FAZ CLEANUP sırasında kaldırılan eski plan ve tasarım dokümanlarının işe yarar özetlerini tutar. Orijinal belgeler repo karmaşasını artırdığı için silindi; önemli içgörüler aşağıda korunmuştur.

## Agent Prompt Overhaul Blueprint (2025-11-07)
- Her ajan çıktısının güvenilir `safe_functions` ve uzun vadeli pacing bilgisi içermesi hedefleniyordu.
- DirectorAgent için yeni girdiler/çıktılar (risk budget, forced safe functions, finale hints) tanımlandı; Event/Planner/Character/Judge ajanlarının nasıl bağlanacağı belirtildi.
- Prompt dosyaları için örnek JSON şablonları ve guardrail hatırlatıcıları listelendi; otomatik regresyon testleri önerildi.

## Dynamic Overhaul Plan (2025-11-02)
- Safe function genişletmesi (world, NPC, resources, story) için domain bazlı API taslakları ve validasyon kuralları derlendi.
- Dünya durumu/persistans katmanı için JSON + SQLite versiyonlama ve diff tabanlı senaryolar açıklandı.
- Orchestrator güncellemeleri, test/perf hedefleri ve finale tasarım sırasıyla planlandı; açık riskler/bağımlılıklar listelendi.

## Orchestrator Flow Overhaul (2025-11-05)
- Yeni tur sırası: Director sahnesi → World/Event/Creativity/Planner/Character → Judge dedup → RulesEngine → Safe Function kuyruğu.
- Safe function kota politikası ve kaynak bazlı `source` etiketleri tanımlandı; doğrulama/rollback adımları detaylandırıldı.
- Judge cache mekanizması, glitch eğrisi iyileştirmeleri ve hata yönetimi (invalid JSON retry, telemetry sayaçları) tarif edildi.

## State Storage Plan (2025-11-04)
- Hot (RAM) vs Cold (history/SQLite) alan ayrımı, diff tabanlı snapshot/persist stratejisi ve rollback modeli dökümante edildi.
- `StateStore` için `_state_hot/_state_cold` ayrımı, `sqlite_sync` diff yazımı ve JSON `_cold_refs` formatı anlatıldı.
- Telemetry metrikleri ve riskler (diff pointer bozulması, tooling karmaşıklığı) vurgulandı.

## Current Scenario Baseline (2025-11-02)
- Safe Function Registry’nin güncel tablosu, validator notları ve yan etkileri listelendi.
- `DEFAULT_WORLD_STATE` yapısı ve sıcak/soğuk türetilmiş alanlar açıklandı; mevcut test kapsamı tablosu eklendi.
- Baseline gözlemleri: ajans promptları az safe function üretiyor, schema migration ihtiyacı, MetricManager uyumluluğu.

## Finale Design Outline (2025-11-03)
- Turn bazlı finale akışı (Build-Up → Escalation → Crisis → Resolution) ve tetikleyici metrikler detaylandırıldı.
- Glitch davranışı, NPC rolleri ve yapı dayanıklılığı için safe function kullanım örnekleri verildi.
- Epilog yolları (Victory / Pyrrhic / Defeat) ve RulesEngine genişletmeleri anlatıldı.

## Player View Summary Enhancements (2025-11-07)
- `player_view` alanına eklenen yeni öznitelikler (metrics_panel, active_flags, npc_trust_overview, guardrail_notes, map_state, safe_function_history vb.) tanımlandı.
- Entegrasyon notları: opsiyonel alanlar, SSE/telemetry eşleşmesi, profil/test çıktılarının nasıl doğrulandığı.

