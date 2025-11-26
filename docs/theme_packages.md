# Theme Packages

Faz 4 hedefi dogrultusunda tema paketleri ayni motoru farkli konseptlere (siege, sci-fi, vb.) tasimak icin gerekli prompt yollarini, world-state override'larini ve safe-function politikalarini tek bir JSON dosyasinda toplar.

## Dizin Yapisi

```
themes/
â”œâ”€â”€ theme_schema.json      # JSON Schema, otomatik validasyon icin
â”œâ”€â”€ siege_default.json     # Varsayilan kale savunmasi temasi
â”œâ”€â”€ orbital_frontier.json  # Ornek retro-future istasyon temasi
â””â”€â”€ scifi/
    â””â”€â”€ prompts/
        â”œâ”€â”€ event_prompt.txt
        â””â”€â”€ world_prompt.txt
```

## Schema Ozet

`themes/theme_schema.json` asagidaki alanlari tanimlar:

| Alan | Aciklama |
|------|---------|
| `id` | Tema kimligi (slug). CLI secimlerinde kullanilir. |
| `label`, `description` | UI/metinlerde gosterilecek baslik ve ozet. |
| `version` | Paket revizyonu. |
| `inherits` | Baska bir temadan miras alinacak kimlik. |
| `prompt_overrides` | Agent bazinda prompt dosya yolu eslestirmeleri. Bos birakilirsa varsayilan `prompts/` klasoru kullanilir. |
| `world_state_overrides` | `DEFAULT_WORLD_STATE` uzerine uygulanacak kismi JSON. |
| `safe_function_overrides` | Enable/disable listeleri ve gaz butcesi ayarlari. |
| `assets` | Motif havuzlari, NPC roster ozeti gibi temaya ozgu veriler. |

## Ornekler

### Siege (varsayilan)

`themes/siege_default.json` mevcut kale senaryosunu belgeler. Prompt dosyalarini referans gosterir, world-state uzerinde sadece kampanya kimligi, oyuncu envanteri ve bazi yapi ayarlarini override eder. Safe-function politikalari yapi/gaz limitlerini guclendirir.

### Orbital Frontier

`themes/orbital_frontier.json` `siege_default` temadan miras alir, bazi promptlari `themes/scifi/prompts/` altindaki yeni metinlerle degistirir ve world-state'i uzay istasyonu terminolojisine gore uyarlar. Glitch/anomaly odakli safe function setini aktife eder.

## Kullanim Plani

1. **Secim Kaynagi**: CLI veya API baslatilirken `--theme orbital_frontier` gibi bir parametre ile istenen JSON yuklenir.
2. **Yukleme Sirasi**:
   - JSON dosyasi okunur, gerekirse `inherits` zinciriyle birlestirilir.
   - `world_state_overrides` `DEFAULT_WORLD_STATE` uzerine uygulanir.
   - `prompt_overrides` her agent icin template path'ini gunceller.
   - `safe_function_overrides` FunctionCallValidator gaz butcesine aktarilir.
3. **Telemetri**: Secilen tema id'si `state["theme_id"]` alanina yazilir ve turn recaps / finale kartlari bu bilgiyle etiketlenir.

### CLI Ornekleri

```bash
py fortress_director/scripts/cli.py --theme siege_default run_turn --turns 2 --reset-before
```

Bu komut once `themes/siege_default.json` dosyasini yukler, world_state'i tema override'lariyla sifirlar ve ardindan iki tur calistirir. Farkli tema secmek icin `--theme orbital_frontier` gibi baska bir kimlik ya da dogrudan JSON yolu verilebilir.

Tema calismalari icin yeni CLI komutlari:

```bash
# Paketi dogrula ve ozetini gor
py fortress_director/scripts/cli.py theme validate siege_default  # Theme validate

# Temayi sandbox'ta simule et
py fortress_director/scripts/cli.py theme simulate orbital_frontier --turns 2 --random-choices --keep-state  # Theme Simulate
```

`theme validate` prompt/world/safe-function override anahtarlarini raporlar. `theme simulate` secilen temayi yukler, belirtilen sayida tur calistirir ve varsayilan olarak state'i basa dondurur (`--keep-state` ile kalici yapabilirsin). Komut varsayilan olarak OfflineOllamaClient stub'lari ile calisir; gercek Ollama modellerini kullanmak icin `--live-models` ekle. `--output report.json` cikti kaydeder, `--include-raw` ise her turun tam JSON'unu ekler.

### Creator Manifest

Tema ve safe function paketlerini paylaşmak için artık `fortress_director/demo` içindeki yeni manifest araçlarını kullanacağız. Eski `creator_portal/manifest.schema.json` ve ilişkili kod kaldırıldı; güncel manifest şeması ve CLI entegrasyonu bu doküman güncellenirken eklenecek.

## Yeni Tema Olusturma Adimlari

1. `themes/<id>.json` dosyasini olusturun, `theme_schema.json` ile valide edin (ornegin `py -m jsonschema`).
2. Tema ozel promptlar gerekiyorsa `themes/<id>/prompts` altinda dosyalar acin.
3. World-state override'larini minimal tutun: sadece kampanya/metin degisiklikleri icin kullanin.
4. Safe function listelerini gozden gecirip, temaya ozel fonksiyonlari aktife edin (ornegin sci-fi temada `trigger_environment_hazard`).
5. `docs/theme_packages.md` dosyasina kisa giris ekleyerek takim olarak temayi nasil sectiginizi belgelendirin.

## Sonraki Adimlar

- Loader implementasyonu: CLI'ye `--theme` bayragi eklenmesi ve `SETTINGS` yapisinin tema dosyasina gore guncellenmesi.
- Testler: Parametrik pytest senaryosu ile farkli temalarin world-state ve prompt yollarini dogrulamak.
- UI/Grafik: Tema metadata'sindaki renk/motif bilgilerini oyuncu paneline yansitmak.

