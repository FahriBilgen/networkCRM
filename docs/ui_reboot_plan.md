# 2D Taktik Oyun ï¿½ Konsept + Oyun Tasarï¿½mï¿½ + UI/UX + Final Sistemi

Bu dokï¿½man, geliï¿½tirilmekte olan 2D taktik oyunun **temel konseptini**, **oyuncu hedeflerini**, **core loop**ï¿½unu, **ajan sistemini**, **UI/UX gereksinimlerini** ve **dinamik final mimarisini** tanï¿½mlar. Hem oyun tasarï¿½mcï¿½sï¿½ hem de frontend/backend geliï¿½tirici iï¿½in referans niteliï¿½indedir.

---

## Gï¿½ncel Uygulama Durumu (Kasï¿½m 2025)

* **Radial baï¿½lam menï¿½sï¿½** oyuncu saï¿½ tï¿½kladï¿½ï¿½ï¿½nda veya Interaction panelindeki ï¿½Radialï¿½ dï¿½ï¿½mesine bastï¿½ï¿½ï¿½nda aï¿½ï¿½lï¿½yor; kare merkezine hizalanï¿½yor, fade-out uygulanï¿½yor ve safe function ï¿½aï¿½rï¿½larï¿½ tetikleniyor. Sprite yanï¿½nda kï¿½ï¿½ï¿½k panel varyantï¿½ NPC spritelarï¿½na kilitlenip konum/durum ï¿½zetini doï¿½rudan gï¿½steriyor.
* **Envanter sï¿½rï¿½kle-bï¿½rak** HUD slotlarï¿½ndan ï¿½alï¿½ï¿½ï¿½yor; allowed tile/area verisi vardï¿½rsa Pixi ï¿½zerinde highlight ediliyor, alan dï¿½ï¿½ï¿½na bï¿½rakma kï¿½rmï¿½zï¿½ ghost + ï¿½aï¿½rï¿½ iptaliyle sonuï¿½lanï¿½yor.
* **NPC & oyuncu animasyonlarï¿½** grid geï¿½iï¿½lerinde ease-out tween ile yumuï¿½uyor; engel temaslarï¿½nda hafif wobble uygulanï¿½yor. Bu, 6.1 ve 7.2ï¿½deki ï¿½akï¿½ï¿½kan hareketï¿½ gereksinimini karï¿½ï¿½lï¿½yor.
* **Atmosfer efekt katmanï¿½** `scene.effects` verisini yaï¿½mur/sis/glitch/kamera overlayï¿½lerine dï¿½nï¿½ï¿½tï¿½rï¿½yor; tema bazlï¿½ sprite/palet geï¿½iï¿½i + JSON ï¿½ asset hattï¿½ artï¿½k Pixi partikï¿½l katmanï¿½nda yaï¿½mur/kar/glitch efektlerini ve mini map motiflerini taï¿½ï¿½yor.
* **Final telemetri** Map Activity feedï¿½ine tek satï¿½rlï¿½k ï¿½Finaleï¿½ girdisi dï¿½ï¿½ï¿½yor; fade-out animasyonu ve status etiketi final tonunu yansï¿½tï¿½yor.
* **Mini harita & gï¿½rï¿½ï¿½ konisi** Scene kartï¿½ndaki mini map tema paletiyle eï¿½leï¿½iyor, oyuncu pulseï¿½ï¿½ ve dï¿½ï¿½man NPC gï¿½rï¿½ï¿½ konileri Pixi katmanï¿½nda overlay ediliyor.
* **Agent Dominance paneli** safe function ï¿½ï¿½ktï¿½larï¿½nï¿½n alan bazlï¿½ oranlarï¿½nï¿½ gï¿½sterip ajan baskï¿½nlï¿½ï¿½ï¿½ trend/hafï¿½za logunu tutuyor; telemetry snapshotï¿½ï¿½na da ekleniyor.
* **Harita katman overlayï¿½leri** `update_map_layer` artï¿½k tile/bï¿½lge sï¿½nï¿½rlarï¿½nï¿½ JSON olarak alï¿½p Pixi sahnesi ve mini map ï¿½zerinde ajan kaynaklï¿½ bï¿½lgeleri boyuyor; bound verisi safe functionï¿½dan otomatik normalize ediliyor.
* **Agent Influence motoru** safe function oranlarï¿½ hedef altï¿½na dï¿½ï¿½ï¿½nce ajanlar otomatik olarak map layer, NPC rolleri, event kuyruklarï¿½, hava durumu, stok ve finale progresyonunu manipï¿½le ediyor.

Yeni sohbet oturumlarï¿½nda hï¿½zlï¿½ baï¿½langï¿½ï¿½ iï¿½in bu ï¿½zet gï¿½ncel durumu ï¿½zetlemektedir.

## 0. Sistematik ï¿½lerleme ï¿½zeti (Kasï¿½m 2025)

| Alan | Durum | Notlar |
| --- | --- | --- |
| Radial baï¿½lam menï¿½sï¿½ | Tamamlandï¿½ | Saï¿½ tï¿½k veya Interaction panelindeki radial butonu ile aï¿½ï¿½lï¿½yor, kare merkezine hizalanï¿½p fade-out ile kapanï¿½yor, safe function ï¿½aï¿½rï¿½larï¿½nï¿½ tetikliyor. |
| NPC yan panel varyantï¿½ | Tamamlandï¿½ | Radial menï¿½ artï¿½k NPC spriteï¿½ï¿½na kenetleniyor ve mini bilgi paneli hedefin konum/durumunu gï¿½steriyor. |
| Envanter sï¿½rï¿½kle-bï¿½rak | Tamamlandï¿½ | HUD slotlarï¿½ndan ï¿½alï¿½ï¿½ï¿½yor, allowed tile/area varsa Pixi katmanï¿½nda highlight, alan dï¿½ï¿½ï¿½na bï¿½rakmada kï¿½rmï¿½zï¿½ ghost + ï¿½aï¿½rï¿½ iptali var. |
| NPC & oyuncu animasyonlarï¿½ | Tamamlandï¿½ | Grid geï¿½iï¿½leri ease-out tween, engel temasï¿½nda hafif wobble, 6.1 ve 7.2ï¿½deki ï¿½akï¿½ï¿½kan hareketï¿½ gereksinimini saï¿½lï¿½yor. |
| Atmosfer efekt katmanï¿½ | Tamamlandï¿½ | Tema paketlerindeki `notes.effects` sahneye aktarï¿½lï¿½yor; JSON ï¿½ Pixi hattï¿½ mini map ve cinematic layerï¿½da anlï¿½k renk/sprite geï¿½iï¿½i saï¿½lï¿½yor. |
| Kamera pan/zoom scriptleri | Tamamlandï¿½ | Pixi sahnesi orta tekerlek zoom + orta tuï¿½ pan destekliyor, kamera auto-follow toggle ile ajan odaklï¿½ ï¿½alï¿½ï¿½ï¿½yor. |
| Final telemetri + trigger pipeline | Tamamlandï¿½ | Finale yï¿½nelik sinyaller ajan dramaturji profilinden ve finale safe function ï¿½aï¿½rï¿½larï¿½ndan besleniyor. |
| Agent Dominance paneli | Tamamlandï¿½ | Safe function oranlarï¿½ + trend/hafï¿½za logu ve domain baï¿½ï¿½na son safe call listesi telemetry snapshotï¿½ï¿½na dï¿½ï¿½ï¿½yor, ajan dengesizliï¿½i uyarï¿½larï¿½ HUDï¿½a basï¿½lï¿½yor. |
| Encoding temizliï¿½i | Tamamlandï¿½ | UTF-8 karakter seti normalize edildi; dokï¿½manda mojibake kalmadï¿½. |
| Tema motoru (sprite/palet entegrasyonu) | Tamamlandï¿½ | Theme palette artï¿½k HUD/CSS/Pixi sahnesine uygulanï¿½yor; `theme_assets` UIï¿½ya taï¿½ï¿½nï¿½p chipï¿½lerde gï¿½steriliyor. |

## 1. Oyun Konsepti

### 1.1 Yï¿½ksek Seviye Tanï¿½m

ï¿½2D grid tabanlï¿½, ajan destekli, taktik/gï¿½zlem oyunu.ï¿½

Oyuncu kï¿½ï¿½ï¿½k bir avatarla 2D haritada dolaï¿½ï¿½r; haritadaki NPCï¿½ler, eventï¿½ler ve hava durumlarï¿½ ï¿½eï¿½itli ajanlar tarafï¿½ndan yï¿½netilir. Oyuncu bu dï¿½nyayï¿½ hem **kontrol etmeye** hem de **anlamaya** ï¿½alï¿½ï¿½ï¿½r, fakat ajanlar aynï¿½ anda oyuncuyu yï¿½nlendirir, manipï¿½le eder ve sonunda farklï¿½ finallere iter.

### 1.2 Fantazi (Oyuncunun ï¿½ï¿½indeki Fikir)

Oyuncu ï¿½unu hissetmeli:

> ï¿½Burasï¿½ yaï¿½ayan bir sistem. Ben komutanï¿½m/sistem operatï¿½rï¿½yï¿½m, ama sistem de beni izliyor.ï¿½

* Dï¿½nya ï¿½kontrol paneliï¿½ gibi deï¿½il; canlï¿½ bir taktik sahne gibi.
* Oyuncu karar aldï¿½kï¿½a ajanlar onu inceliyor ve buna gï¿½re ï¿½neri, event ve final manipï¿½lasyonu yapï¿½yor.
* Oyuncu hiï¿½bir zaman bï¿½tï¿½n resmi tam gï¿½remiyor; kï¿½smi bilgi ile taktik kararlar alï¿½yor.

### 1.3 Tï¿½r ve Ton

* Tï¿½r: Taktik + hafif roguelike ï¿½ï¿½eler + ajan destekli simï¿½lasyon.
* Perspektif: Top-down 2D grid.
* Ton: Hafif karanlï¿½k, biraz paranoyak, sistem odaklï¿½. Temaya gï¿½re deï¿½iï¿½ebilen atmosfer (siege, sci-fi, occult vb.)

---

## 2. Oyuna Baï¿½lamadan ï¿½nce Belirlenecek Temel ï¿½eyler

Bu kï¿½sï¿½m, projeye baï¿½lanmadan ï¿½nce netleï¿½tirilmesi gerekenler iï¿½in checklist gibi dï¿½ï¿½ï¿½nï¿½lebilir.

### 2.1 Hedef Platform

* PC tarayï¿½cï¿½ (web) mi, standalone masaï¿½stï¿½ mï¿½?
* Mobil desteï¿½i dï¿½ï¿½ï¿½nï¿½lï¿½yor mu? (Kontrol ï¿½emasï¿½nï¿½ ciddi etkiler.)

> ï¿½u anki tasarï¿½m klavye + mouse odaklï¿½, yani ilk hedefi: PC.

### 2.2 Hedef Oyuncu Profili

* Taktik oyun seven, sistemi kurcalamayï¿½ ve ï¿½burada ne oluyor?ï¿½ hissini seven oyuncu.
* Derin lore yerine ï¿½mekaniksel hikï¿½yeï¿½ sevenler.
* ï¿½ok hï¿½zlï¿½ aksiyondan ziyade, dï¿½ï¿½ï¿½nerek oynayan, ajan ï¿½nerilerini okumaya ï¿½ï¿½enmeyen tip.

### 2.3 Oyun Sï¿½resi ve Ritmi

* Tek run hedef sï¿½resi: 20-40 dakika (tema ve final yoluna gï¿½re deï¿½iï¿½ebilir).
* Oyuncu kï¿½sa oturumlarda oynayabilmeli; run yarï¿½da bï¿½rakï¿½labilirse snapshot kaydï¿½ mantï¿½ï¿½ï¿½ belirlenmeli.

### 2.4 Zorluk Seviyesi

* Baï¿½langï¿½ï¿½ta ï¿½ï¿½renilebilir, ama ï¿½sistem beni trollediï¿½ hissi verecek kadar karmaï¿½ï¿½k.
* Zorluk: Ajanlarï¿½n ne kadar agresif manipï¿½le ettiï¿½i ve event sï¿½klï¿½ï¿½ï¿½yla ayarlanï¿½r.

### 2.5 Meta Hedefler (ï¿½leride)

* Run sonunda yeni tema aï¿½ï¿½lmasï¿½.
* Yeni harita modlarï¿½ (daha zor, daha glitchï¿½li).
* Oyuncunun sonraki runï¿½larda ufak kalï¿½cï¿½ buff veya bilgi avantajï¿½ taï¿½ï¿½masï¿½ (ï¿½rneï¿½in daha ï¿½nce gï¿½rmediï¿½i bir final tï¿½rï¿½nï¿½ artï¿½k HUDï¿½da sembol olarak gï¿½rmesi).

---

## 3. ï¿½ekirdek Oynanï¿½ï¿½ (Core Loop)

### 3.1 ï¿½zet

1. Oyuncu 2D grid ï¿½zerinde avatarï¿½nï¿½ hareket ettirir.
2. NPCï¿½ler, eventï¿½ler ve hava durumu ajanlar tarafï¿½ndan gï¿½ncellenir.
3. Planner ajan oyuncuya ï¿½neriler sunar.
4. Oyuncu:
   * Kendi kararï¿½nï¿½ verir veya
   * Ajanlarï¿½n ï¿½nerilerini kabul eder.
5. Safe functionï¿½lar ï¿½aï¿½ï¿½rï¿½lï¿½r, dï¿½nya deï¿½iï¿½ir.
6. Dï¿½nya deï¿½iï¿½tikï¿½e, final sistemi yavaï¿½ yavaï¿½ ï¿½ekillenir.

### 3.2 Oyuncunun Gï¿½rï¿½nï¿½r Hedefleri

Oyuncu ï¿½unlarï¿½ bildiï¿½ini sanï¿½r:

* Belirli alanlarï¿½ savunmak / keï¿½fetmek.
* Bazï¿½ NPCï¿½leri korumak veya yï¿½nlendirmek.
* Belirli metrikleri (morale, order, resources, glitch) ï¿½iyiï¿½ seviyede tutmak.

Ama:

* Gerï¿½ek nihai hedef her runï¿½da tam olarak aï¿½ï¿½klanmaz.
* Ajanlar, final tï¿½rï¿½nï¿½ arkada seï¿½er ve oyuncuyu buna doï¿½ru iter.

---

## 4. Ajan Sistemi ve Roller

### 4.1 Ajan Tipleri

**Planner Ajan**

* Her ï¿½turnï¿½ sonunda ï¿½neri listesi ï¿½retir.
* ï¿½neriler: hareket, harita kontrolï¿½, event tetikleme, NPC ile etkileï¿½im vs.
* UI: Komuta panelinde buton/simge olarak gï¿½sterilir, Space/Q/E ile yï¿½netilir.

**Map Ajanï¿½**

* Safe function ï¿½rnekleri: `reinforce_section`, `toggle_gate`, `spawn_dynamic_weather`, `render_overlay`.
* Haritanï¿½n savunma durumunu, yollarï¿½, gï¿½rï¿½ï¿½ï¿½ ve atmosferi deï¿½iï¿½tirir.

**NPC Ajanï¿½**

* `schedule_patrol`, `adjust_role`, `assign_follow_player` vb. fonksiyonlarla NPC davranï¿½ï¿½larï¿½nï¿½, rol daï¿½ï¿½lï¿½mï¿½nï¿½ ve oyuncuya olan mesafelerini yï¿½netir.

**Event Ajanï¿½**

* `spawn_emergency`, `open_side_quest`, `broadcast_alert` gibi fonksiyonlarla dramatik olaylar ve yan gï¿½revler yaratï¿½r, final yaklaï¿½ï¿½rken daha kritik eventï¿½ler ï¿½retir.

**Item Ajanï¿½**

* `spawn_item`, `craft_item`, `consume_resource` gibi fonksiyonlarla oyuncunun envanteri ve kaynak yï¿½netimi ï¿½zerinden taktik seï¿½enekler ï¿½retir.

### 4.2 Ajanlarï¿½n Oyuncuyu Manipï¿½le Etmesi

Ajanlar, oyuncunun ï¿½neri kabul oranï¿½nï¿½, risk davranï¿½ï¿½ï¿½nï¿½, harita keï¿½if oranï¿½nï¿½, NPCï¿½lere yaklaï¿½ï¿½mï¿½nï¿½ ve kaynak harcama stilini sï¿½rekli gï¿½zlemler. Bu veriler, ï¿½nerilerin tonunu ve final yolunu belirlemek iï¿½in kullanï¿½lï¿½r.

---

## 5. UI/UX Tasarï¿½mï¿½ ï¿½ Genel ï¿½lkeler

### 5.1 Temel Felsefe

* Kart tabanlï¿½ arayï¿½z yok; klasik oyun HUDï¿½u var.
* Oyun, ï¿½debug ekranï¿½ï¿½ gibi deï¿½il ï¿½oynanabilir sahneï¿½ gibi hissettirmeli.
* Input her zaman anï¿½nda gï¿½rsel tepki vermeli; backend daha ï¿½ok ï¿½gerï¿½eklik kayï¿½t cihazï¿½ï¿½ gibi ï¿½alï¿½ï¿½malï¿½.

### 5.2 Sahne Teknolojisi

* 2D Canvas/Pixi sahnesi.
* Grid tabanlï¿½ harita, tile sprite setleri.
* Basit partikï¿½l sistemleri: yaï¿½mur, sis, glitch, kum fï¿½rtï¿½nasï¿½ (tema baï¿½lï¿½).

### 5.3 Gerï¿½ek Zaman Hissi

* Motor turn bazlï¿½, fakat:
  * Klavye ve mouse girdileri anï¿½nda sahnede iï¿½lenir.
  * `move_player` gibi eylemler log iï¿½in backendï¿½e gider.
* Bï¿½ylece oyuncu ï¿½tek tek kare hareketï¿½ deï¿½il, akï¿½ï¿½kan bir macera hissi alï¿½r.

---

## 6. Kullanï¿½cï¿½ Etkileï¿½imi ï¿½ Detaylar

### 6.1 Hareket

* WASD veya ok tuï¿½larï¿½ ile kare kare hareket.
* Her hï¿½cre geï¿½iï¿½inde avatar kï¿½ï¿½ï¿½k bir yï¿½rï¿½me animasyonu oynatï¿½r, `move_player` safe functionï¿½ï¿½ tetiklenir.
* Engellere ï¿½arptï¿½ï¿½ï¿½nda avatar hafif geri sekme/sarsï¿½ntï¿½ animasyonu alï¿½r.

### 6.2 Mouse Etkileï¿½imi

* NPC/objeye tï¿½klanï¿½nca:
  * Baï¿½lam menï¿½sï¿½ (radial veya kï¿½ï¿½ï¿½k panel) NPCï¿½nin yanï¿½nda aï¿½ï¿½lï¿½r.
  * Seï¿½enekler: ï¿½Konuï¿½ï¿½, ï¿½ï¿½nceleï¿½, ï¿½Yardï¿½m isteï¿½, ï¿½Takip etï¿½, vb.
  * Her seï¿½enek ilgili safe functionï¿½ï¿½ tetikler.
* Baï¿½lam menï¿½sï¿½, bir sï¿½re kullanï¿½lmazsa fade-out olur.

### 6.3 Kï¿½sayollar

* `Space`: Seï¿½ili ajan ï¿½nerisini uygular.
* `Q/E`: ï¿½neriler arasï¿½nda gezinir.
* `Tab`: Harita katmanlarï¿½nï¿½ (tehlike, sis, hava olaylarï¿½ vs.) aï¿½/kapat.

### 6.4 Envanter

* HUD ï¿½zerinde slotlar halinde gï¿½sterilir.
* Item sï¿½rï¿½kle-bï¿½rak:
  * Harita ï¿½zerindeki uygun hedefler highlight olur.
  * Uygun olmayan yere bï¿½rakmak istenirse kï¿½rmï¿½zï¿½ uyarï¿½/gï¿½rsel feedback alï¿½nï¿½r.
* ï¿½rnek:
  * Flare itemï¿½i haritaya bï¿½rakï¿½ldï¿½ï¿½ï¿½nda `deploy_flare` tetiklenir.
  * Sahnede ï¿½ï¿½ï¿½k patlamasï¿½ ve aydï¿½nlatï¿½lan bir daire efekti oynar.

---

## 7. Gï¿½rsel Katmanlar

### 7.1 Harita

* Tile grid + overlay katmanlarï¿½:
  * Tehlike alanlarï¿½,
  * Sis,
  * Yaï¿½mur,
  * Glitch zonlarï¿½.
* Map diffï¿½leri geldiï¿½inde sadece deï¿½iï¿½en kï¿½sï¿½mlar animasyonlu gï¿½ncellenir (hard cut yok).

### 7.2 NPC Hareketi

* `npc_locations` zaman damgasï¿½na gï¿½re interpolate edilerek yumuï¿½ak hareket.
* Dï¿½ï¿½man NPCï¿½lerin gï¿½rï¿½ï¿½ konisi optional overlay.

### 7.3 Efektler

* Yaï¿½mur: Ekran dï¿½ï¿½ï¿½ndan gelen ince ï¿½izgiler.
* Sis: Yavaï¿½ hareket eden yarï¿½ saydam bulutlar.
* Glitch: Pikselli bozulmalar ve renk kaymalarï¿½, ï¿½zellikle glitch metriï¿½i yï¿½kseldikï¿½e.

### 7.4 HUD

* Sol alt: Mini map (oyuncu iï¿½in pulse iï¿½areti).
* Saï¿½ ï¿½st: metrik barlarï¿½ (morale/order/resources/glitch).
* Alt orta: Event log (scroll edilebilir kï¿½sa log satï¿½rlarï¿½).

---

## 8. Teknik Mimari (Kï¿½saca)

### 8.1 Front-end

* React + Zustand store.
* Canvas/Pixi render katmanï¿½.

### 8.2 Backend Entegrasyonu

* REST:
  * Turn submission,
  * safe function ï¿½aï¿½rï¿½larï¿½.
* WebSocket / SSE:
  * Telemetri akï¿½ï¿½ï¿½,
  * State diffï¿½leri.
* Ajan ï¿½nerileri iï¿½in `/game/recommendations` endpointï¿½i.

### 8.3 Input Sistemi

* Fiziksel hareket clientï¿½ta simï¿½le edilir.
* Backendï¿½e sadece anlamlï¿½ eylemler (karar seviyesi aksiyonlar) gider.

---

## 9. Tema Sistemi

### 9.1 Genel

* Tema, sprite paletini, partikï¿½l sistemlerini, HUD renklerini ve final atmosferini belirler.
* Theme ID ï¿½ Theme JSON ï¿½ sprite, renk, efekt seti.

### 9.2 ï¿½rnek Temalar

* **Siege**: Kuï¿½atma altï¿½ndaki kale; yaï¿½mur, sis, metal bariyerler.
* **Sci-fi**: Neon ï¿½ehir, glitch, droneï¿½lar, parlak HUD.
* **Desert**: Kum, sï¿½cak hava dalgasï¿½, sï¿½nï¿½rlï¿½ gï¿½rï¿½ï¿½.
* **Occult/Rogue**: Garip semboller, karanlï¿½k sis, bozuk geometri.

---

## 10. Dinamik Final Sistemi

### 10.1 Felsefe

Oyun, tek bir sabit finale deï¿½il; oyuncu davranï¿½ï¿½ï¿½ + ajan kararlarï¿½ + tema kombinasyonuna gï¿½re ï¿½ekillenen erken, geï¿½ ve tematik finallere sahiptir.

Oyuncu:

* Bir amaca sahip olduï¿½unu sanï¿½r.
* Ajanlar bu algï¿½yï¿½ kullanarak harita, NPC ve eventï¿½leri manipï¿½le eder.
* Final, oyuncunun sandï¿½ï¿½ï¿½ ile gerï¿½ekte olan arasï¿½ndaki farktan doï¿½ar.

### 10.2 Ajan Rolleri Finalde

**Planner**

* Son turlarda ï¿½neri tonunu deï¿½iï¿½tirir (daha panik, daha ï¿½aresiz, daha saldï¿½rgan).
* Erken final gerektiï¿½inde ï¿½kaï¿½ï¿½ï¿½ yolu yokï¿½ hissi veren ï¿½neriler sunabilir.

**Event**

* Final ï¿½ncesi ritim: olay frekansï¿½ artar, risk bï¿½yï¿½r.
* ï¿½rnek: global alarm, bï¿½yï¿½k saldï¿½rï¿½, sistem ï¿½ï¿½kï¿½ï¿½ï¿½.

**NPC**

* Bazï¿½ NPCï¿½ler kaï¿½maya, bazï¿½larï¿½ oyuncuya yapï¿½ï¿½maya baï¿½lar.
* ï¿½hanet, kaï¿½ï¿½ï¿½, fedakï¿½rlï¿½k gibi dramatik davranï¿½ï¿½lar gï¿½sterir.

**Map**

* Alanlar kapanï¿½r, sis yoï¿½unlaï¿½ï¿½r, glitch zonu geniï¿½ler.
* Harita daha sï¿½kï¿½ï¿½ï¿½k veya daha uï¿½urum gibi hissedilir.

### 10.3 Final Tï¿½rleri

**Erken Final**

* Oyuncu ï¿½ok riskli veya ï¿½ok pasif oynarsa.
* Metrikler dï¿½ï¿½er (morale/order/resources) veya glitch patlar.
* ï¿½rnek sonuï¿½lar:
  * Kale dï¿½ï¿½er, NPCï¿½ler kaï¿½ar.
  * Sistem aï¿½ï¿½rï¿½ glitch olup kendini kapatï¿½r.

**Geï¿½ Final**

* Oyuncu uzun sï¿½re dengede gider.
* Final bï¿½yï¿½k bir kï¿½rï¿½lma anï¿½ iï¿½erir:
  * Harita ï¿½ï¿½ker,
  * Bï¿½yï¿½k fï¿½rtï¿½na gelir,
  * Ana NPC ihanet eder,
  * Oyuncu ï¿½ï¿½st sistemiï¿½ keï¿½feder.

**Tematik Finaller**

* Siege: Son dalga saldï¿½rï¿½ ve savunma; surlar yï¿½kï¿½lï¿½r ya da dayanï¿½r.
* Sci-fi: Ana AI kapanï¿½r, evren resetlenir veya oyuncu sistemden kaï¿½ar.
* Desert: Kum fï¿½rtï¿½nasï¿½nda kayboluï¿½ ya da antik yapï¿½ keï¿½fi.
* Occult: Harita gerï¿½ek yï¿½zï¿½nï¿½ gï¿½sterir; oyuncu tanrï¿½sal/ï¿½eytansï¿½ bir varlï¿½kla yï¿½zleï¿½ir.

### 10.4 Finalin UI Akï¿½ï¿½ï¿½

Final yaklaï¿½ï¿½rken:

* HUD metrik barlarï¿½ hafif titrer.
* Mini mapï¿½te kara delik gibi gï¿½rï¿½nmeyen bï¿½lgeler oluï¿½ur.
* ï¿½neri paneli tuhaf ï¿½neriler ï¿½ï¿½karabilir (ï¿½zellikle glitch yï¿½ksekse).
* Hava olaylarï¿½ yoï¿½unlaï¿½ï¿½r, ekran efektleri artar.

Final anï¿½nda:

* Ekran hafif karartï¿½lï¿½r, tema rengine kayar.
* Harita overlayï¿½leri sï¿½rayla sï¿½ner.
* NPCï¿½ler son animasyonlarï¿½nï¿½ oynar.
* Event logï¿½da tek bir bï¿½yï¿½k ï¿½final satï¿½rï¿½ï¿½ belirir (daha bï¿½yï¿½k font, fade-out efekti).

### 10.5 Oyuncu Davranï¿½ï¿½ï¿½ ï¿½ Final Seï¿½imi

Sistem sï¿½rekli oyuncuyu ï¿½lï¿½er:

* ï¿½neri kabul etme oranï¿½ (ajanlara ne kadar ï¿½teslimï¿½?)
* Risk seviyesi (tehlikeli alanlara girme vs.)
* Kaï¿½ NPC kurtarï¿½ldï¿½ / feda edildi?
* Haritanï¿½n ne kadarï¿½ keï¿½fedildi?
* Kaynaklar nasï¿½l kullanï¿½ldï¿½ (aï¿½gï¿½zlï¿½, dikkatli, savurgan)?

Bu profil, final seï¿½imini etkiler:

* ï¿½ok uysal oyuncu ï¿½ ï¿½Ajanlarï¿½n oyuncaï¿½ï¿½ï¿½ temalï¿½ finaller.
* ï¿½ok isyankï¿½r oyuncu ï¿½ ï¿½Sistem kï¿½rï¿½ldï¿½ï¿½ veya ï¿½yalnï¿½z kurtuluï¿½ï¿½ finalleri.

### 10.6 Final Sonrasï¿½

Final ekranï¿½:

* Temaya uygun statik/yarï¿½ animasyonlu sahne.
* Kï¿½sa anlatï¿½m metni (oyuncunun run ï¿½ykï¿½sï¿½).
* Aï¿½ï¿½lan ï¿½eyler: yeni tema, yeni harita, yeni ajan davranï¿½ï¿½ modu, kalï¿½cï¿½ kï¿½ï¿½ï¿½k bonuslar.

---

## 11. Yol Haritasï¿½ (Geliï¿½tirme Aï¿½amalarï¿½)

1. **Konsept & ï¿½n ï¿½retim Netleï¿½tirme**
   * Hedef platform, hedef oyuncu, run sï¿½resi, ilk tema.
2. **Sahne & Input Prototipi**
   * Canvas grid, player/NPC placeholder, WASD, SSE snapshot okuma.
3. **Safe Function UI & Animasyon Katmanï¿½**
   * Safe function ï¿½aï¿½rï¿½larï¿½n sahnede karï¿½ï¿½lï¿½ï¿½ï¿½nï¿½n tanï¿½mlanmasï¿½.
4. **Ajan ï¿½neri Sistemi**
   * `/game/recommendations` ï¿½ UIï¿½de komuta paneli, ï¿½neri kï¿½sayollarï¿½.
5. **Envanter & NPC Davranï¿½ï¿½larï¿½**
   * HUD, sï¿½rï¿½kle-bï¿½rak, NPC stance overlay.
6. **Tema Motoru**
   * Theme JSON ï¿½ sprite/effect paleti + geï¿½iï¿½ animasyonlarï¿½.
7. **Dinamik Final Sistemi**
   * Erken/geï¿½/tematik final triggerï¿½larï¿½, UI sinyalleri, final ekranï¿½.
8. **Polish**
   * Ses, mikro animasyonlar, glitch efektleri, meta progression gï¿½rselleï¿½tirmeleri.

---

## 12. Ajan Hakimiyeti ï¿½ Oyun Mekaniï¿½inin %70+ï¿½i Ajanlar Tarafï¿½ndan Yï¿½netilir

### Durum ï¿½zeti

| Bï¿½lï¿½m | Durum |
| --- | --- |
| 5. UI/UX ï¿½lkeleri | Tamamlandï¿½ | Radial menï¿½, drag-drop envanter, mini HUD ve eriï¿½ilebilirlik kontrolleri ï¿½retimde. |
| 6. Detaylï¿½ Etkileï¿½imler | Tamamlandï¿½ | WASD/ok hareketi, baï¿½lam menï¿½leri, kï¿½sayollar ve envanter safe function akï¿½ï¿½ï¿½yla baï¿½lï¿½. |
| 7. Gï¿½rsel Katmanlar | Tamamlandï¿½ | Pixi grid/overlay/vision katmanlarï¿½ ve mini harita anlï¿½k gï¿½ncelleniyor. |
| 8. Teknik Mimari | Tamamlandï¿½ | Pixi sahnesi iï¿½in ileri seviye parï¿½acï¿½k/overlay katmanï¿½ devrede; `scene.effects` artï¿½k canlï¿½ yaï¿½mur/kar/glitch partikï¿½lleri ï¿½retip kamera/paletle senkron akï¿½yor. |
| 9. Tema Sistemi | Tamamlandï¿½ | Theme JSON loader world state, HUD paleti ve chip'leri besliyor. |
| 10. Dinamik Final Sistemi | Tamamlandï¿½ | Final telemetrisi, Map Activity finale girdisi ve final overlay/timeline akï¿½ï¿½ï¿½ devrede. |
| 11. Yol Haritasï¿½ | Tamamlandï¿½ | Yol haritasï¿½ndaki kalemler gï¿½ncel build'de adreslendi. |
| 12. Ajan Hakimiyeti | TamamlandÄ± | Agent Influence motoru safe function oranlarÄ±nÄ± izleyip map/NPC/event/weather/item/text/finale alanlarÄ±nÄ± otomatik manipÃ¼le ediyor. |

Ayrýca **Agent Influence motoru**, safe function daðýlýmlarý hedeflerin altýnda kaldýðýnda harita katmanlarý, NPC rolleri, event kuyruklarý, hava durumu, stok seviyeleri, kilitli seçenekler ve finale progresyonu otomatik manipüle ederek ajan hakimiyetini görünür kýlar.
Bu oyunda asï¿½l amaï¿½, ï¿½dï¿½nya statikti, oyuncu oynadï¿½ï¿½ mantï¿½ï¿½ï¿½nï¿½ kï¿½rmak. Bunun yerine:

> **Dï¿½nya oynar, oyuncu onun iï¿½indeki bilinï¿½li anomalidir.**

Ajanlar bu dï¿½nyanï¿½n gerï¿½ek yï¿½neticileri; oyuncu sadece bu akï¿½ï¿½ï¿½ bozma, hï¿½zlandï¿½rma, yavaï¿½latma, ï¿½aï¿½ï¿½rtma ve yï¿½n deï¿½iï¿½tirme yeteneï¿½ine sahip bir faktï¿½rdï¿½r. Oyuncu hiï¿½bir zaman tam kontrol sahibi olmaz ï¿½ bilerek. Bu da oynanï¿½ï¿½ tansiyonunu ve final manipï¿½lasyonunu zenginleï¿½tirir.

### 12.1 Harita Yï¿½netimi (Map Ajanï¿½ Dominant)

Haritanï¿½n kendisi statik bir grid deï¿½ildir; ajan tarafï¿½ndan dinamik ï¿½ekilde yeniden ï¿½ekillenir. Ajan ï¿½unlarï¿½ yapabilir:

* Yol kapatma / aï¿½ma.
* Tehlike alanï¿½ yer deï¿½iï¿½tirme.
* Sis yoï¿½unluï¿½unu artï¿½rma veya azaltma.
* Yeni overlay ekleme (glitch zonu, sï¿½caklï¿½k alanï¿½, gï¿½rï¿½ï¿½ daraltï¿½cï¿½ sis).
* Harita dï¿½zenini roguelike mantï¿½ï¿½ï¿½nda mikro-diffï¿½lerle deï¿½iï¿½tirme.
* ï¿½nemli mekanlarï¿½ taï¿½ï¿½ma (ï¿½rneï¿½in ï¿½gï¿½venli bï¿½lgeï¿½ bir anda yer deï¿½iï¿½tirir).
* Oyuncunun bulunduï¿½u yer yakï¿½nlarï¿½na olay tohumlayabilir.

Oyuncu bunu ï¿½dï¿½nya tepki veriyorï¿½ diye okur, ama aslï¿½nda dï¿½nya ajan tarafï¿½ndan ï¿½ekillendiriliyordur.

### 12.2 NPC Yï¿½netimi (NPC Ajanï¿½ = Mikro Drama Motoru)

NPCï¿½ler yalnï¿½zca hareket eden spriteï¿½lar deï¿½il; tamamen ajan tarafï¿½ndan yï¿½nlendirilen dramatik araï¿½lardï¿½r. NPC ajanï¿½:

* Her NPCï¿½ye gï¿½nlï¿½k plan oluï¿½turur.
* Rol deï¿½iï¿½tirir (dost ï¿½ nï¿½tr ï¿½ dï¿½ï¿½man; asker ï¿½ sivil ï¿½ lider).
* Oyuncuya gï¿½re tavï¿½r belirler (gï¿½venir, korkar, takip eder, kaï¿½ï¿½nï¿½r).
* NPCï¿½nin konuï¿½acaï¿½ï¿½ diyalogu yazabilir.
* NPCï¿½nin vereceï¿½i gï¿½revi event ajanï¿½yla eï¿½gï¿½dï¿½mlï¿½ kurabilir.
* NPCï¿½yi final iï¿½in ï¿½hazï¿½rlï¿½kï¿½ pozisyonlarï¿½na sokabilir (ihanet, kaï¿½ï¿½ï¿½, fedakï¿½rlï¿½k).
* Oyuncunun profilini ï¿½lï¿½erek manipï¿½le edecek, yanï¿½ltacak, gerï¿½eï¿½i ï¿½arpï¿½tacak diyaloglar seï¿½er.

### 12.3 Event Yï¿½netimi (Event Ajanï¿½ = Master of Drama)

Event ajanï¿½, oyunun ritmini belirleyen unsurdur. Sï¿½radan bir event sistemi deï¿½il; **dï¿½nya ï¿½apï¿½nda dramatik dï¿½zenleyici**.

* Her turn iï¿½in ï¿½anlatï¿½ sï¿½caklï¿½ï¿½ï¿½ï¿½ belirler.
* Tehlike seviyesini artï¿½rï¿½r/azaltï¿½r.
* Oyuncuya verdiï¿½i hedefleri manipï¿½le eder.
* Oyuncunun hatalarï¿½nï¿½ bï¿½yï¿½tï¿½r veya gï¿½rmezden gelir.
* Yan gï¿½revleri planlar.
* Bï¿½yï¿½k olaylarï¿½ tetikler (kuï¿½atma, ï¿½ï¿½kï¿½ï¿½, enerji kesintisi, kum fï¿½rtï¿½nasï¿½, AI glitchï¿½i, NPC ayaklanmasï¿½).
* Finalin tonunu son 3-5 turn boyunca hazï¿½rlar.

### 12.4 Hava Durumu ve Atmosfer Yï¿½netimi

Hava durumu kozmetik deï¿½ildir; ajan tarafï¿½ndan taktisyen gibi kullanï¿½lï¿½r.

* Gï¿½rï¿½ï¿½ mesafesini daraltabilir.
* Oyuncunun hissettiï¿½i hareket hï¿½zï¿½nï¿½ etkiler (sis, karanlï¿½k, parazit).
* NPC davranï¿½ï¿½larï¿½nï¿½ tetikler (fï¿½rtï¿½na gelince NPCï¿½ler saklanï¿½r).
* Oyuncuya yanï¿½ltï¿½cï¿½ gï¿½ven hissi verir (aniden aï¿½an hava ï¿½ daha bï¿½yï¿½k tehlike ï¿½ncesi sinyal).
* Final atmosferi iï¿½in ï¿½tone shiftï¿½ yaratï¿½r.

### 12.5 Item Yï¿½netimi (Item Ajanï¿½ = Kaynak Manipï¿½latï¿½rï¿½)

Item ajanï¿½ sadece item spawn etmez ï¿½ oyuncunun kaynak psikolojisini yï¿½netir.

* Nadiren yï¿½ksek deï¿½erli item yaratï¿½r.
* Oyuncunun davranï¿½ï¿½ stiline gï¿½re item bolluï¿½unu ayarlar.
* Kritik anda kaynak keser (ï¿½zellikle erken final istiyorsa).
* NPCï¿½ler aracï¿½lï¿½ï¿½ï¿½yla item daï¿½ï¿½tabilir veya geri aldï¿½rabilir.
* Item aï¿½ï¿½klamalarï¿½nï¿½ bile manipï¿½le edebilir (text dahil).

Oyuncu ï¿½ï¿½anslï¿½yï¿½m / ï¿½anssï¿½zï¿½mï¿½ diye dï¿½ï¿½ï¿½nï¿½rken, aslï¿½nda sistem gerektiï¿½inde ona bolluk veya kï¿½tlï¿½k yaï¿½atï¿½yordur.

### 12.6 Text ve Aï¿½ï¿½klama Yï¿½netimi (Narrative AI Ajanï¿½)

Tï¿½m metinler, UI aï¿½ï¿½klamalarï¿½, NPC konuï¿½malarï¿½, event ï¿½zetleriï¿½ Bunlarï¿½n ï¿½oï¿½u **ajan tarafï¿½ndan dinamik ï¿½retilir**.

Bu ajan, oyunun ï¿½anlatï¿½cï¿½ beyniï¿½.

* NPCï¿½nin sï¿½ylediï¿½i cï¿½mle.
* Eventï¿½in aï¿½ï¿½klama metni.
* Objeye tï¿½klanï¿½nca ï¿½ï¿½kan ï¿½inceleï¿½ yazï¿½sï¿½.
* Side quest aï¿½ï¿½klamasï¿½.
* HUDï¿½da beliren sistem mesajlarï¿½nï¿½n tonu.
* Oyuncuya verilen ipuï¿½larï¿½nï¿½n gï¿½venilir olup olmamasï¿½.

Bu ajan asla tamamen yalancï¿½ deï¿½ildir; ama hep *eksik* bilgi verir. Oyuncu sï¿½rekli ï¿½anladï¿½m mï¿½?ï¿½ diye sorgular.

### 12.7 Gï¿½rsel Katmanlar Bile Ajan Kontrolï¿½nde

Ajanlar ï¿½unlara bile dokunabilir:

* Mini map gï¿½sterim kurallarï¿½.
* Overlay yoï¿½unluï¿½u.
* UI renk tonlarï¿½ (glitch yï¿½kseldikï¿½e HUD bozulmasï¿½).
* NPC ikonlarï¿½nï¿½n gï¿½rï¿½nï¿½rlï¿½ï¿½ï¿½.
* Kritik anda kamera zoom-in / zoom-out efektleri.

Oyuncunun gï¿½rsel gerï¿½ekliï¿½i ajanlarï¿½n iradesine baï¿½lï¿½dï¿½r.

### 12.8 Oyunun Mekaniksel %70-80ï¿½i Ajanlarda Olunca Ne Oluyor?

1. Oyun **aynï¿½ haritada bile her runï¿½da farklï¿½** olur.
2. Oyuncu hiï¿½bir zaman gerï¿½ek kontrolï¿½n onda olmadï¿½ï¿½ï¿½nï¿½ bilmez.
3. Ajanlar oyuncunun kararlarï¿½na gï¿½re:
   * yardï¿½m edebilir,
   * sabote edebilir,
   * manipï¿½le edebilir,
   * yï¿½nlendirebilir.
4. Final sistemi ï¿½ok daha gï¿½ï¿½lï¿½ olur; ajanlar son 5 turn boyunca haritayï¿½, NPCï¿½leri, eventï¿½leri ve metinleri birbirine baï¿½layarak hikï¿½yeyi dokur.

Oyuncunun zihni ï¿½kontrol bendeï¿½, ajanlarï¿½n zihni ï¿½hikï¿½yeyi biz ï¿½rï¿½yoruzï¿½. Bu gerilim oyunu benzersiz kï¿½lar.

### 12.9 Ajanlarï¿½n Dï¿½nyayï¿½ ï¿½ekillendirme Oranï¿½

ï¿½nerilen oranlar:

* **Harita deï¿½iï¿½ikliklerinin %70ï¿½i** ï¿½ Ajan
* **NPC davranï¿½ï¿½larï¿½nï¿½n %90ï¿½ï¿½** ï¿½ Ajan
* **Eventï¿½lerin %100ï¿½ï¿½** ï¿½ Ajan
* **Hava durumunun %100ï¿½ï¿½** ï¿½ Ajan
* **Item spawn/craftingï¿½in %80ï¿½i** ï¿½ Ajan
* **Text / aï¿½ï¿½klama metinlerinin %70ï¿½i** ï¿½ Ajan
* **Final yolunun %100ï¿½ï¿½** ï¿½ Ajan

Bu oranlar oyunu hem yordamsal hem de bilinï¿½li manipï¿½lasyon iï¿½eren hibrit bir sistem haline getirir. Oyuncu, dï¿½nya ile etkileï¿½ime girip ï¿½yazï¿½lmamï¿½ï¿½ï¿½ bir hikï¿½yenin ortaï¿½ï¿½ olur.

### 12.10 Bu Yapï¿½nï¿½n Oyun Deneyimine Katkï¿½sï¿½

* Her run farklï¿½ bir film gibi hissedilir.
* Oyuncu her zaman hafif bir gï¿½vensizlik, merak, belirsizlik iï¿½indedir.
* Final bï¿½yï¿½k bir ï¿½ahaï¿½ anï¿½ yaratï¿½r.
* Oyun sistemleri sonsuz esnekliï¿½e kavuï¿½ur.
* Geliï¿½tiriciler yeni event veya NPC eklediï¿½inde sistem otomatik ï¿½ï¿½renir ve manipï¿½lasyon seï¿½eneklerini geniï¿½letir.

---
