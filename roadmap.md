Yol Haritasi (Guncel)

Faz 0 - Durum Analizi

LLM cagri sureleri, state boyutu (JSON/SQLite), log hacmi ve bellek kullanimini olc; tools/profile_turn.py gibi basit profil araclari yaz.
Integration loglarini incele, Judge veto orani ve safe function basarisizlik sebebi topla.
Gereksiz LLM ve validator loglarini seviyeye gore kis; olcumlere engel olmasin.

Faz 1 - Cekirdek Akisi Stabilize Et

- [x] Character/Creativity/Judge promptlarini sadakat, motif tekrari, hava durumu gibi kurallarla guclendir; tekrar eden vetolari azalt.
- [x] Fallback tepkilerini ucu alternatife cikart (savunma, moral, taktik); veto sonrasinda kisa aciklama uret.
- [x] Safe function cagrilari icin ajan promptlarina ornekler ekle; planner_guardrail'de rapor kalemleri takip et.
- [x] Prompt sadelestirme + kucuk LRU cache ile LLM token ve cagri suresini dusur.
- [x] Offline ve integration testlerinde veto oranini olc; pytest -m integration --maxfail=1 + log raporu.

Faz 2 - Hikaye Surekliligi ve Yeniden Oynanabilirlik

- [x] Turn basi ozet: metrik mini paneli, aktif bayraklar, NPC guven ozetleri uret.
- [x] recent_motifs ve timeline yonetimi: motif tekrarini kontrol et, yeni hikayeye uydur.
- [x] NPC journal: tur tur kisa cumleler kaydet; limit ve rotasyon uygula.
- [x] Judge veto mesajini oyuncu metnine ekle; fallback diyaloglar tematik olsun.
- [x] Ressourcen limitleri (recent_events vb.) belirle, state'in sismesini onle.

Faz 3 - Final ve Dramaturji

- [x] final_summary motoru: metrik esikleri ve flag kombinasyonlari ile farkli ending kartlari.
- [x] Dramaturji plani: 3/6/9. turda ozel sinyaller, major event tetikleyici parametreler (major_event_last_turn vb.).
- [x] Post-game recap: secilen secenekler, safe function etkileri, vetolar. Telemetriye ekle.

Faz 4 - Tema ve Konsept Esnekligi

- [x] Prompt/state/safe function yapilarini tema paketleri (JSON/YAML) olarak duzenle; themes/siege, themes/scifi vb.
- [x] Tema secim belgesi ve gereken adimlari yaz; yeni konsept icin rehber olustur.

Faz 5 - State ve Veri Yonetimi

- [x] StateStore icin sicak/soguk katman ayrimi yap; metrikler, flags ve current_room gibi kritik alanlari RAM'de tutarken uzun log ve recent_events'leri SQLite/history/turn_X.json arsivine tasi.
- [x] snapshot()/persist() akisina diff tabanli writer ekle; gereksiz deep copy maliyetini azalt ve sqlite_sync.py uzerinden batch transaction + PRAGMA ayarlarini profil et. (state_storage_plan.md hazirlandi, ilk cold diff dosyalari data/history/turn_X.json altina yaziliyor). Hedef <50 ms IO icin tools/profile_state_io.py scripti yaz.
- [x] runs ve logs dizinleri icin otomatik rotasyon + gzip arsivleri kur; audit/replay ihtiyacinda yalnizca ilgili turn diff'lerini cek.

Faz 6 - UI Hazirligi ve Safe Function Etkilesimi

- [x] API sozlesmesini versionla; player_view/options/safe_function_results JSON semasini yayinlayip FastAPI uzerinden valide et.
- [x] npc_locations, map_state ve guardrail anlatimini standartla; safe function sonuclarini bu canonical formatlara yaz ki UI ayni veriyi kullansin.
- [x] fortress_director/demo altinda metrik barlari, NPC kartlari, guardrail feed ve safe function gecmisi gosteren basit prototip calistir.
- [x] Planlayici ve safe function telemetrisini SSE/polling endpoint olarak sun; veto/fallback anlatimini oyuncuya gorunur kil.

Faz 7 - Teknik Mimari Refaktor

- [x] fortress_director/orchestrator/orchestrator.py dosyasini turn_runner, state_services, safe_function_executor ve telemetry_builder modullerine bol; her modul <500 satir ve bagimsiz test edilebilir olsun.
- [x] RulesEngine ve FunctionRegistry paketlerini repo icindeki baska projelerin de kullanabilecegi bagimsiz birer modul olarak ayir.
- [x] CI akisina iki katman ekle: offline/unit testler zorunlu, integration/perf (profil turn, acceptance) istege bagli ama raporlama zorunlu.

Faz 8 - Gozlemlenebilirlik ve Operasyon

- [x] Her ajan icin latency/token/gas metrigini topla; glitch ve Judge veto verisini ayni telemetri kanalinda birlestir ve state'e yaz.
- [x] runs/telemetry.csv ve SQLite ciktilariyla Grafana/Metabase uyumlu dataset uret; >90 sn turn veya >10 safe function icin otomatik uyari esikleri tanimla.
- [x] tools/telemetry_report.py ile son N turnun KPI ozetini al; regresyon goruldugunde roadmap guncellemelerini tetikle.

Faz 9 - Tema ve Tasarimci Araclari

- [x] fortress_director/scripts/cli.py'ya 'theme validate' ve 'theme simulate' komutlarini ekle; themes/theme_schema.json uzerinden veri dogrulamasi yap ve diff cikart.
- [x] Tema/prompt sandbox'i kur: tasarimcilar JSON + prompt duzenleyip 2-3 tur simulasyonu kod yazmadan calistirsin.
- [x] Yeni story pack'ler icin depo ve dokumantasyon olustur; hangi safe function setlerinin acik oldugunu ve gerekli asset'leri listele.

Surekli Yapilacaklar

- [x] Performans kritik yollari haftalik profil et; KPI (LLM bekleme, persist suresi, bellek) icin otomatik rapor uret ve paylas. (tools/perf_watchdog.py)
- [x] Prompt/tema degisikliklerinde mini regression (offline + integration) kos; sonuc ozetini runs/regressions altina kaydet. (tools/regression_runner.py)
- [x] Gereksiz bagimlilik ve log seviyelerini dusur; requirements*.txt dosyalarini aylik gozden gecir. (tools/dependency_log_audit.py)
- [x] Telemetri ve roadmap senkronizasyonu icin aylik retro yap; yeni metrik ihtiyaci cikarsa Faz 8 backlog'una ekle. (tools/telemetry_retro.py + perf_watchdog raporlari)
- [x] docs/ klasorunun (current_state_baseline, theme_packages, player_view) planla uyumunu her sprint sonunda dogrula. (tools/docs_consistency_check.py)

Sonraki Adimlar

- [x] Perf/telemetri raporlarini otomatik tetiklemek icin `.github/workflows/weekly-kpi.yml` eklendi; bu aksiyon tools/perf_watchdog.py + tools/kpi_digest.py ciktilarini haftalik olarak olusturup GitHub step summary uzerinden paylasiyor.
- [x] Tema/prompt backlog'u `docs/theme_prompt_backlog.md` dosyasinda guncellendi; perf_report_20251107_182136 ve runs/regressions/* verilerine dayali onceliklendirme sirasi eklendi.
- [x] Release checklist'i `docs/release_checklist.md` altinda toplandi; dependency_log_audit.py ve docs_consistency_check.py ciktilari her sprint sonunda manuel olarak gozden gecirilecek.

Yeni Yol Haritasi - Dinamik Oyun Hedefi

Faz A - Oyuncu Deneyimi Temeli

- [x] Turn HUD'una kazanma/kaybetme kosullari, kalan tur sayisi ve kaynak barlarini ekle; risk gostergeleri ve Judge vetolari icin aksiyon onerileri uret. (HUD karti + risk panosu fortress_director/demo/web/index.html altinda yayinda)
- [x] Ilk 3 turu kapsayan tutorial senaryosu yaz; Character/Judge ajan promptlarina onboarding ornekleri ekle. (tutorial_overlay + prompt brief'leri aktif)
- [x] UI prototipini oyuncu testiyle dogrula, erisilebilirlik (kontrast, font, renk) hedeflerini belirle. (docs/ui_accessibility_targets.md + history/ui_playtests.md ilk dry run)

Faz B - Dinamik Dunya Katmani

- [x] FunctionRegistry'ye map ve NPC odakli yeni safe function'lar (`update_map_layer`, `adjust_npc_role`, `spawn_event_marker`) ekle; JSON schema + limitleri tanimla. (validators + `safe-functions/schema` endpoint tamam)
- [x] Safe function ciktilarini isleyip SSE/WebSocket ile UI'ya aktaran map diff adapter'i yaz; client tarafinda animasyonlu guncelleme uygula. (map_diff_adapter + ui/index.html map activity/pulse kartlari)
- [x] NPC davranis sablonlarini tanimla; LLM yalnizca hedef/niyet cikarirken pathfinding ve tepki suresi deterministik motor tarafindan yonetilsin. (fortress_director/utils/npc_behavior.py + tests/test_npc_behavior.py)

Faz C - Performans ve Guardrail

- [x] Map/NPC fonksiyonlari icin cagri limitleri ve batching uygula; profile_turn/perf_watchdog raporlarina `map_fn_latency`, `snapshot_batch_ms` gibi yeni metrikler ekle. (SafeFunctionExecutor metrikleri + telemetry_aggregate/perf_watchdog gunceli)
- [x] Validator kurallarini genislet; map diff'lerini schema + is kuralina gore dogrula, hatada otomatik rollback + oyuncu-facing fallback metni yaz. (map_diff_validator + guardrail notlari ve fallback mesaji)
- [x] Siklikla kullanilan fonksiyonlarin ozetini ana prompt'a ekleyip nadir fonksiyonlar icin lookup tablo kullan; token maliyetini dusur.

Faz D - Icerik, Replay ve Sosyal Katman

- [x] `docs/theme_prompt_backlog.md` u oyuncu perspektifiyle tekrar yaz; map/NPC fonksiyonlarini kullanan yeni senaryolar planla. (oyuncu hedefleri + safe function kancalari tablo halinde)
- [x] NPC loyalty, kaynak baskisi ve event zincirlerini UI'da gorunur kilarak karar-sonuc bagini guclendir. (fortress_director/demo/web/index.html loyalty/resource/event + meta panelleri)
- [x] Meta progression (kilit acma, basari, paylasilabilir hikaye ozetleri) icin taslak hazirla ve telemetri raporlarini buna gore duzenle. (docs/meta_progression_plan.md + player_view/telemetry meta fields)

Faz E - Gercek Modellerle Oynanabilir Pilot

- [x] LLM cikti planlarini mikroadim event queue'suna dokun; oyuncu aksiyonlariyla carpisma durumlari icin lock/priority sistemi yaz.
- [x] Dusek gecikmeli modeller (quantized/adapter) ve cache stratejileri sec; canli modellerle tur surelerini <=3 saniye hedefle.
- Web/desktop pilot istemcisi baglayip oyuncu oynarken LLM'in map/NPC degisikliklerini gosteren entegrasyonu tamamla; KPI'lar icin go/no-go kriterleri belirle.

Faz F - Canli Opsiyonlar ve Ekonomi

- [x] fortress_director/live_ops/ altindaki planlayici tamamen kaldirildi; live ops tetikleyicileri ve JSON planlari artik desteklenmiyor.
- [x] tools/resource_balancer.py ile kaynak ekonomisi sim araci yaz; player_view metric'lerinden veri cekip riskli delta'lari raporla, balance tablosunu docs/economy_tuning.md'de tut. (CLI `resource_balance` + JSON rapor opsiyonu + docs notlari)
- [x] Sosyal paylasim pipeline'ini (docs/meta_progression_plan.md) otomatik screenshot + hikaye ozetleri ile genislet; Discord/webhook entegrasyonunu ops checklist'ine ekle. (tools/share_card_pipeline.py + ops/social_share_checklist.md + telemetry/perf_watchdog baglantilari)

Faz G - Platform ve Operasyon

- [x] Gercek zamanli modeller icin autoscaling ve GPU havuz ayarlarini Cloud/infra.md altinda runbook olarak yaz; perf_watchdog ciktilarini alarm esiklerine bagla. (Cloud/infra runbook + `tools/publish_autoscale_metrics.py`)
- [x] Data privacy/compliance checklist'ini hazirla; player_view ve logs icin maskleme/regulation notlarini docs/compliance.md dosyasina bagla. (mask_player_identifiers util + docs/compliance.md + telemetry wiring)
- [x] Release candidate pipeline'ini nightly ve canary olarak ayir; .github/workflows/labs-canary.yml ile theme paketleri + safe function setlerini otomatik olarak test et. (scheduled workflow + release checklist adimlari)

Faz H - Global Lansman ve Lokalizasyon

- [x] `localization/phrasebook/*.yaml` yapisini kurup themes paketlerinin `strings.json` dosyalariyla build sirasinda birlestir; fortress_director/prompt_runtime icinde dil fallback zincirini ve pluralization kurallarini uygulamaya al.
- [x] UI asset'leri ve player_view metinlerini i18n pipeline'ina bagla; RTL ve dusuk bant genisligi modlari icin `ui/localization_preview.html` prototipini calistirip docs/localization_guide.md altinda QA checklist'i olustur.
- [x] Region bazli event/gateway ayarlarini Cloud/region_matrix.md dokumaninda topla; telemetry_etl'yi locale filtreleriyle genisletip CDN/infra secimlerine veri sagla.

Faz I - Model Adaptasyonu ve Deney Platformu

- [x] tools/experiment_hub.py ile prompt/model/config kombinasyonlarini YAML bazli tarif edip CI uzerinden A/B ve canary testlerine dagit; sonuc raporlarini runs/experiments/ altinda sakla.
- [x] fortress_director/model_registry/ paketine quantized + adapter model metadata'si ekle; cache stratejileri icin benchmark scriptleri (tools/model_cache_probe.py) yaz ve perf_watchdog'a bagla.
- [x] Judge/safe function ajanlari icin otomatik regression veri setleri olustur; acceptance_tests/model_guardrail.jsonl dosyasina yeni vaka turlerini ekleyip nightly pipeline'da takip et.

Faz J - Creator Ekosistemi ve Studio Entegrasyonu

- [x] fortress_director/sdk/cli.py altinda paketlenecek "creator kit" komutlarini (theme init, prompt lint, safe function mock) yaz; docs/sdk_getting_started.md ile destekle.
- [x] Theme/safe function paketleri icin versiyonlu API yayinla; repository'ye `docs/demo_overview.md` ekleyip CI'da dogrula. (Creator manifest API + schema + tests)
- [x] Topluluk yapimlarini (story pack, NPC kit, map layer) kataloglayacak web tabanli gallery mock'u hazirla; ops tarafinda guvenlik taramalari ve telif incelemeleri icin checklist olustur. (`ui/community_gallery.html` + `/creator/v1/gallery` + `ops/community_gallery_checklist.md`)

