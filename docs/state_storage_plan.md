# Fortress State Storage Plan

## Goals
- Soguk/sicak katman ayrimi ile snapshot/persist maliyetini dusurmek
- Diff tabanli yazimla gereksiz deep copy ve IO'yu engellemek
- Rollback/telemetry uyumlulugunu korumak

## Hot vs Cold Fields
- Hot (RAM): metrics, flags, current_room, player summary, planlayici/guardrail bagli alanlar.
- Cold (Arsiv/SQLite): recent_events uzun listesi, audit/replay, NPC journal gecmisi, motif history, sf_history.
- Hybrit: npc_trust, structures -> hot cache + SQLite mirror.

## Diff Strategy
1. snapshot() hot katman icin deepcopy, cold katmani referansla temsil eden metadata (örn. history pointer).
2. persist():
   - hot state'i RAM'de guncelle ve JSON'a sadece hot alanlari yaz.
   - cold alan degisti ise state_diff ile farki hesapla, diff'i data/history/turn_X.json veya SQLite tablosuna ekle.
   - sqlite_sync diff aware mod: sadece degisen tablolari UPDATE/INSERT et.
3. Rollback icin checkpoint => hot snapshot + cold diff pointer.

## Telemetry & Tools
- telemetry.state_io_metrics zaten var.
- Yeni: diff yazim sayisi, cold yazim boyutu.
- `tools/profile_state_io.py` `--mode hot|full` ile yalnizca HOT snapshot/persist yolunu olceyebiliyor; rapor `mode` alaninda belirtiliyor.

## Implementation Steps
1. state_storage_plan.md (bu dosya).
2. StateStore refaktoru:
   - _state_hot, _state_cold diye iki sozluk.
   - snapshot() hot copy + cold metadata.
   - persist() -> apply_hot_updates + flush_diff (ilk iterasyonda cold diff `data/history/turn_X.json` dosyasina yazildi).
3. sqlite_sync'de diff aware satirlar.
4. Tests: yeni unit + integration, profile_turn/perf.
5. JSON Layout:
   - `data/world_state.json` artik yalnizca HOT alanlari ve `_cold_refs` metadata'sini (`{"latest_turn": 8, "history_dir": "history"}`) barindirir.
   - load() sirasi: hot JSON okunur, `_cold_refs` varsa `history/turn_XXXX.json` diff dosyalari uygulanip cold cache doldurulur.
   - history merge kurali: her diff dosyasi tam snapshot degil; apply ederken `DEFAULT_WORLD_STATE` + hot JSON + diff zinciri kullanilir (turn numarasi bazli).

## Risks
- Cold diff pointer'lari bozulursa rollback zor => ekstra test.
- Tools (debug_state, telemetry agregator) hot/cold ayrimini anlamali.
- IO tasarrufu beklenirken karmaşıklık artabilir; önce prototip metrigi topla.
