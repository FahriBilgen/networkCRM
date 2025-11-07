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
- [x] fortress_director/ui altinda metrik barlari, NPC kartlari, guardrail feed ve safe function gecmisi gosteren basit prototip calistir.
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

- [x] fortress_director/cli.py'ya 'theme validate' ve 'theme simulate' komutlarini ekle; themes/theme_schema.json uzerinden veri dogrulamasi yap ve diff cikart.
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

- Turn HUD'una kazanma/kaybetme kosullari, kalan tur sayisi ve kaynak barlarini ekle; risk gostergeleri ve Judge vetolari icin aksiyon onerileri uret.
- Ilk 3 turu kapsayan tutorial senaryosu yaz; Character/Judge ajan promptlarina onboarding ornekleri ekle.
- UI prototipini oyuncu testiyle dogrula, erisilebilirlik (kontrast, font, renk) hedeflerini belirle.

Faz B - Dinamik Dunya Katmani

- FunctionRegistry'ye map ve NPC odakli yeni safe function'lar (`update_map_layer`, `adjust_npc_role`, `spawn_event_marker`) ekle; JSON schema + limitleri tanimla.
- Safe function ciktilarini isleyip SSE/WebSocket ile UI'ya aktaran map diff adapter'i yaz; client tarafinda animasyonlu guncelleme uygula.
- NPC davranis sablonlarini tanimla; LLM yalnizca hedef/niyet cikarirken pathfinding ve tepki suresi deterministik motor tarafindan yonetilsin.

Faz C - Performans ve Guardrail

- Map/NPC fonksiyonlari icin cagri limitleri ve batching uygula; profile_turn/perf_watchdog raporlarina `map_fn_latency`, `snapshot_batch_ms` gibi yeni metrikler ekle.
- Validator kurallarini genislet; map diff'lerini schema + is kuralina gore dogrula, hatada otomatik rollback + oyuncu-facing fallback metni yaz.
- Siklikla kullanilan fonksiyonlarin ozetini ana prompt'a ekleyip nadir fonksiyonlar icin lookup tablo kullan; token maliyetini dusur.

Faz D - Icerik, Replay ve Sosyal Katman

- `docs/theme_prompt_backlog.md` u oyuncu perspektifiyle tekrar yaz; map/NPC fonksiyonlarini kullanan yeni senaryolar planla.
- NPC loyalty, kaynak baskisi ve event zincirlerini UI'da gorunur kilarak karar-sonuc bagini guclendir.
- Meta progression (kilit acma, basari, paylasilabilir hikaye ozetleri) icin taslak hazirla ve telemetri raporlarini buna gore duzenle.

Faz E - Gercek Modellerle Oynanabilir Pilot

- LLM cikti planlarini mikroadim event queue'suna dokun; oyuncu aksiyonlariyla carpisma durumlari icin lock/priority sistemi yaz.
- Dusek gecikmeli modeller (quantized/adapter) ve cache stratejileri sec; canli modellerle tur surelerini <=3 saniye hedefle.
- Web/desktop pilot istemcisi baglayip oyuncu oynarken LLM'in map/NPC degisikliklerini gosteren entegrasyonu tamamla; KPI'lar icin go/no-go kriterleri belirle.
