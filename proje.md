1. MUST (MVP için kesin gerekli)
Bunlar olmadan ürün çalışmaz.
A. Kullanıcı Deneyimi (MUST)
1.	Kullanıcı giriş ve temel hesap sistemi
2.	Kişi kartı oluşturma (manuel)
3.	Kişi kartında minimum alanlar:
o	Ad / Soyad
o	Sektör
o	Etiketler
o	İlişki gücü (0–5 arası)
o	Not
4.	Kişilerin graf üzerinde node olarak görünmesi
5.	Node tiplerinin ayrımı (kişi, hedef, vizyon, proje)
6.	Sürükle-bırak ile graph düzenleme
7.	Filtreleme: sektör, ilişki gücü, etiket

### MUST Gereksinimleri Durum Tablosu

| Gereksinim | Durum | Backend | Frontend |
| --- | --- | --- | --- |
| Kullanıcı girişi ve temel hesap sistemi | ✅ JWT tabanlı AuthController (backend-java/src/main/java/com/fahribilgen/networkcrm/controller/AuthController.java) | ✅ LoginOverlay + authStore (frontend/src/components/LoginOverlay.tsx, frontend/src/store/authStore.ts) |
| Kişi kartı oluşturma / minimum alanlar | ✅ NodeService + NodeController (backend-java/src/main/java/com/fahribilgen/networkcrm/controller/NodeController.java) | ✅ NodeModal ve NodeDetailPanel (frontend/src/components/NodeModal.tsx, frontend/src/panels/NodeDetailPanel.tsx) |
| Node tipleri (Person/Goal/Vision/Project) | ✅ NodeType enum + doğrulamalar (backend-java/src/main/java/com/fahribilgen/networkcrm/enums/NodeType.java) | ✅ VisionTreePanel, GraphCanvas görünümleri (frontend/src/panels/VisionTreePanel.tsx, frontend/src/panels/GraphCanvas.tsx) |
| Graph üzerinde node gösterimi | ✅ GraphService / /api/graph (backend-java/src/main/java/com/fahribilgen/networkcrm/service/impl/GraphServiceImpl.java) | ✅ React Flow tabanlı GraphCanvas (frontend/src/panels/GraphCanvas.tsx) |
| Sürükle-bırak düzenleme | ✅ Pozisyon güncellemeleri için NodeService.updateNode (backend-java/src/main/java/com/fahribilgen/networkcrm/service/impl/NodeServiceImpl.java) | ✅ Drag event’lerinde updateNode çağrısı (frontend/src/panels/GraphCanvas.tsx) |
| Filtreleme: sektör/ilişki gücü/etiket | ✅ FilterNodes uç noktası (backend-java/src/main/java/com/fahribilgen/networkcrm/service/impl/NodeServiceImpl.java#L163) | ✅ FiltersPanel bileşeni (frontend/src/panels/FiltersPanel.tsx) |
| Graph üzerinde yakınlık hesaplama | ✅ NodeProximityResponse servisi (backend-java/src/main/java/com/fahribilgen/networkcrm/service/impl/NodeServiceImpl.java#L201) | ✅ NodeDetailPanel’de yakınlık isteği (frontend/src/panels/NodeDetailPanel.tsx) |
| Basit arama | ✅ filterNodes(searchTerm) desteği (backend-java/src/main/java/com/fahribilgen/networkcrm/service/impl/NodeServiceImpl.java#L187) | ✅ TopNav arama bileşeni + searchStore (frontend/src/components/TopNav.tsx, frontend/src/store/searchStore.ts) |
### Web Kokpit + Mobil Hafif Sosyal Vizyonu

Yu anki mimari iki katmanlŽñ bir deneyime evriliyor: web tarafŽñnda tÇ¬m graph, filtreler, AI ÇôngÇôrüleri ve karmaYŽñ timeline akƒõYŽñnŽñ yÇ«neten zengin bir ƒ?okokpitƒ??, mobilde ise daha hafif ama sosyal aŽY odaklŽñ bir eYlik uygulamasŽñ. Mobil uygulamanŽñ ana amacŽñ, sahada yeni tanŽYŽñlan kiYileri saniyeler iÇinde kayda almak, kart gÇ«rünümünde bilgilerini gÇ«rmek ve graphƒ?ta ilgili sektÇ«r katmanŽna otomatik yerletirmek.

- **Web (masaÇ«stÇ«) tarafŽñ**: Graph dÇ«zenleme, hedef/vizyon/proje hiyerarisi, gelişmiş filtreler, timeline yorumlama, AI ƒ?ogoal suggestionƒ??, export ve raporlama gibi gÇ«rev yoŽlunluklu yetenekler burada kalŽ«r. KullanŽcŽlar networklerini analiz eder, graphƒ?ta katmanlŽñ gÇ«rünümü yönetir ve AIÇõn Ç«nerdiŽYi baŽlantŽlarƒ? sÇ«rÇ«kle bŽ«rak ile harekete geçirir.
- **Mobil sosyal uygulama**: KullanŽcŽlar LinkedIn yerine bu uygulamada birbiriyle elenir, herkesin profil kartŽñ bulunur, grafikten daha sade bir katman gÇ«rünümü (sektÇ«r bazlŽñ listeler veya ƒ?odeğerƒ?? odaklŽñ sıralama) sunulur. Grafhƒ?daki en kritik kiYiler tikla seÇïilir, diŽer katmanlar ƒ?odaha az kritikƒ?? kuralŽyla açŽlŽr; yeni bir kişi eklendiğinde kart anŽnda backend ile senkron olur.
- **Veri senkronizasyonu**: Spring Boot + PostgreSQL tabanlŽñ mevcut backend, hem web SPA hem mobil istemcinin tek kaynaŽğ olmaya devam eder. Graph nodeƒ?larŽñ, timeline JSONƒ?larŽñ ve AI embeddingƒ?lerindeki her güncelleme, JWT tabanlŽñ API aracŽlŽğŽyla anŽnda iki yÇ«ne de yansŽ«r; ekstra servis ayrŽmŽñ gerekmiyor.

B. Veri Modeli (MUST)
1.	Person node
2.	Vision node
3.	Goal node
4.	Relation edges:
o	Person–Person (iletişim)
o	Person–Goal (destek ilişkisi)
o	Goal–Vision (hiyerarşi)
5.	Node metadata: renk, tip, sektör, etiketler
6.	Graph DB veya graph benzeri yapı (Neo4j veya Postgres + adjacency)

> **Gerçekleştirme Notu:** Kod tabanı Spring Boot 3.5 + Java 21 + PostgreSQL 16 (pgvector) + React 19 stack’i ile çalışır. Aşağıdaki kavramsal açıklamalarda geçen FastAPI/Neo4j önerileri, canlı projede Spring Boot servisleri ve JPA tabanlı PostgreSQL şemasıyla uygulanmaktadır.

C. Fonksiyonel (MUST)
1.	Kişi ekleme, düzenleme, silme
2.	Vision → Goal → Project hiyerarşisi ekleme
3.	Kişiyi bir hedefe bağlama
4.	Graph üzerinde yakınlık hesaplaması (1-hop ilişkiler)
5.	Basit arama (isim, sektör, etiket)
D. AI Kapasitesi (MUST)
MVP’de çok minimal tutulmalı:
1.	Hedef açıklamasına göre ilgili kişileri öneren basit embedding tabanlı bir “match score”
2.	Kişilerin kısa açıklamalarının embedding olarak saklanması
Bu, AI modülünü ileride büyütmek için temel atar ama MVP’yi şişirmez.
________________________________________
2. SHOULD (MVP sonrası kısa vadede olması gerekenler)
Ürünü güçlü ve etkili yapan fakat MVP’ye şart olmayan özellikler.
A. SHOULD UX
1.	Graph üzerinde otomatik layout algoritmaları (force-directed)
2.	Node’ların otomatik renklendirilmesi (sektör bazlı)
3.	Sağ tık menüsü ile hızlı aksiyonlar (kişiye göre filtre, bağ ekle)
B. SHOULD Data Model
1.	İlişki gücüne göre edge ağırlığı
2.	En son iletişim tarihinin saklanması
3.	“Öncelik” alanı (kişinin senin hedeflerine göre önemi)
C. SHOULD Fonksiyonel
1.	Hedef–vizyon–proje yapısının otomatik tasnifi
2.	Graph’ın PDF veya PNG olarak export edilmesi
3.	“Influence score” hesaplaması (centrality)
4.	Kişiye zaman bazlı notlar ekleme (timeline)
D. SHOULD AI
1.	Sektör önerileri: kişi açıklamalarından sektör çıkarımı
2.	“Bu hedef için network’ün yeterince güçlü mü?” tarzı analiz
3.	“Bu sektörde ağın zayıf” şeklinde gap analysis
4.	Basit ilişki kuvvetlendirme önerileri: “X kişisiyle uzun süredir etkileşim yok”
________________________________________
3. COULD (orta vadede ürün büyürse)
Bu özellikler ürünü çok ileri taşır ama başlangıç için şart değil.
A. COULD UX
1.	Mind-map modu + Graph modu arasında geçiş
2.	Çok büyük networklerde cluster feedback
3.	Node gruplarının otomatik kümelenmesi
B. COULD Fonctional
1.	LinkedIn bağlantı export içeriğini içeri aktarma (CSV)
2.	Otomatik sektör sınıflandırıcı
3.	Kişilerin “görüşme notları”nın AI ile özetlenmesi
4.	Graph içi path-based öneriler
o	“X hedefine ulaşmak için 2 bağlantı uzağında Y kişisi var”
C. COULD AI
1.	Tam öneri motoru:
o	“Bu projeye başlarken en kritik 3 kişi: A, B, C”
o	“Network’te oluşabilecek yeni fırsatlar”
2.	Predictive modelling:
o	“Bu hedef için 60 gün içinde şunlarla konuşmalısın”
________________________________________
4. WON’T (şu an yapılmayacak, gelecek için)
Bunları bilerek ertelemek önemli; yoksa proje dağılır.
A. WON’T UX
1.	Kullanıcılar arası sosyal ağ (şimdilik yok)
B. WON’T Fonksiyonel
1.	Otomatik LinkedIn API entegrasyonu
Çünkü: API kapalı ve lisans sıkıntılı.
C. WON’T AI
1.	Tam otomatik proje yönetimi öneri motoru
2.	LLM tabanlı uzun diyalog analizi ve ilişki tahmini
Bu alanlar ileride yapılabilir ama MVP ve kısa vadeli ürün için gereksiz yük olur.
________________________________________
Bu gereksinim seti bize ne sağladı?
1.	Ürün kapsamı kesinleşti: Ne var, ne yok belli.
2.	Mimari netleşti: Graph yapısı, veri modeli, AI temeli.
3.	MVP fazla şişmiyor: Kritik özellikler korunarak hızlı prototip mümkün.
4.	Gelecek evreleri doğru planlanabilir: Ürün ölçeklenebilir temelde.





1. Konseptüel Veri Modeli
Ürün doğası gereği graph tabanlı bir yapı istiyor. Node’lar 4 ana kategori, edge’ler 3 ana ilişki tipi.
1.1 Node Türleri
A. Person (Kişi)
Kullanıcının networkündeki bireyler.
Zorunlu alanlar:
•	id
•	name
•	sector
•	tags (liste)
•	relationship_strength (0–5)
•	notes
•	created_at
•	updated_at
Opsiyonel alanlar:
•	linkedin_url
•	company
•	role
•	embeddings (AI için)
B. Vision (Vizyon)
Kullanıcının büyük resmi. Ürünün “strateji haritası” kısmının kök nodu.
Alanlar:
•	id
•	title
•	description
•	priority (1–5)
C. Goal (Hedef)
Vizyonu gerçekleştirmek için alt hedefler.
Alanlar:
•	id
•	title
•	description
•	due_date
•	priority (1–5)
D. Project (Proje)
Hedef altında daha operasyonel seviye.
Alanlar:
•	id
•	title
•	description
•	status (todo, doing, done)
•	priority
•	start_date
•	end_date
________________________________________
1.2 Edge Türleri
A. KNOWS (Person → Person)
İki kişi arasındaki ilişki.
Alanlar:
•	relationship_strength
•	relationship_type (arkadaş, iş ilişkisi, mentor, müşteri…)
•	last_interaction_date
B. SUPPORTS (Person → Goal/Project)
Bir kişinin hedefe veya projeye katkı potansiyeli.
Alanlar:
•	relevance_score (AI hesaplayacak)
•	added_by_user (user-defined vs AI-suggested)
•	notes
C. BELONGS_TO (Goal → Vision, Project → Goal)
Hiyerarşik bağ.
Alanlar:
•	order (sıralama)
________________________________________
2. Teknik Tasarım
Şimdi bunu JSON, Neo4j, API seviyesine indiriyorum.
________________________________________
2.1 JSON Veri Modeli
Person
{
  "id": "person_123",
  "type": "person",
  "name": "Ahmet Yılmaz",
  "sector": "Fintech",
  "tags": ["mentor", "yatırımcı"],
  "relationship_strength": 4,
  "notes": "İlk görüşme için müsait.",
  "linkedin_url": "https://linkedin.com/...",
  "company": "ABC Ventures",
  "role": "Partner",
  "embeddings": [0.012, 0.554, ...],
  "created_at": "2025-02-10",
  "updated_at": "2025-02-10"
}
Vision
{
  "id": "vision_1",
  "type": "vision",
  "title": "Girişimimi 12 ayda ticarileştirmek",
  "description": "Temel hedef ürün-pazar uyumunu bulmak.",
  "priority": 5
}
Goal
{
  "id": "goal_1",
  "type": "goal",
  "title": "MVP lansmanı",
  "description": "İlk kullanıcıları edinmek.",
  "priority": 4,
  "due_date": "2025-06-01"
}
Project
{
  "id": "proj_9",
  "type": "project",
  "title": "Kullanıcı onboarding akışı",
  "description": "Onboarding funnel tasarımı",
  "status": "todo",
  "priority": 3,
  "start_date": null,
  "end_date": null
}
Edges
KNOWS edge
{
  "from": "person_123",
  "to": "person_421",
  "type": "knows",
  "relationship_strength": 3,
  "relationship_type": "iş",
  "last_interaction_date": "2024-11-02"
}
SUPPORTS edge
{
  "from": "person_123",
  "to": "goal_1",
  "type": "supports",
  "relevance_score": 0.82,
  "notes": "Bu hedef için sektörel uzmanlığı var.",
  "added_by_user": true
}
BELONGS_TO edge
{
  "from": "goal_1",
  "to": "vision_1",
  "type": "belongs_to",
  "order": 1
}
________________________________________
2.2 PostgreSQL (pgvector) Şema Tasarımı
Tablolar
- `nodes` (Person/Vision/Goal/Project tipleri `type` kolonunda tutulur)
- `edges` (KNOWS/SUPPORTS/BELONGS_TO tipleri)
- `node_tags` (çoktan çoğa etiketler)

Örnek Node kolonları
- `id` (UUID)
- `user_id` (tenant)
- `type` (enum)
- `name`, `description`, `sector`, `notes`
- `relationship_strength`, `priority`, `due_date`, `status`
- `embedding` (pgvector veya JSONB olarak saklanan embedding listesi)

Örnek Edge kolonları
- `id`, `source_node_id`, `target_node_id`, `type`
- `weight`, `relationship_strength`, `relationship_type`
- `last_interaction_date`, `relevance_score`, `sort_order`

Sorgu örnekleri (SQL)
Bir hedef için en yüksek relevanslı kişileri:
```sql
SELECT p.id, p.name, e.relevance_score
FROM edges e
JOIN nodes p ON p.id = e.source_node_id
WHERE e.type = 'SUPPORTS' AND e.target_node_id = :goal_id
ORDER BY e.relevance_score DESC
LIMIT 5;
```
Bir vizyonun ağaç yapısı:
```sql
SELECT n.*
FROM nodes n
JOIN edges e ON e.source_node_id = n.id
WHERE e.type = 'BELONGS_TO' AND e.target_node_id = :vision_id;
```
________________________________________
2.3 API Endpoint Taslakları
Backend için restful taslak:
Person
POST /person
GET /person/{id}
PUT /person/{id}
DELETE /person/{id}
GET /person?sector=&tag=&q=
Vision / Goal / Project
POST /vision
POST /goal
POST /project

GET /vision/{id}
GET /goal/{id}
GET /project/{id}
Graph Operasyonları
POST /relation/knows
POST /relation/supports
POST /relation/belongs

GET /graph/network?person_id={id}
GET /graph/vision_tree?vision_id={id}
AI
POST /ai/relevance-score
POST /ai/suggest-people-for-goal
POST /ai/embed/person
POST /ai/embed/goal
________________________________________
Bu veri modelinin avantajları
1.	Esnek: Kişi, hedef, vizyon, proje gibi kavramlar genişleyebilir.
2.	Analitiğe hazır: Graph olarak hem AI hem network analytics kullanılabilir.
3.	MVP için hafif, uzun vadede güçlü.
4.	Çok fazla node/edge olduğunda ölçeklenebilir (Neo4j doğru seçim).
5.	AI entegrasyonu temiz ve modüler.

























1. Üst Düzey Ekran Akışı (User Flow)
Kullanıcının üründe izleyeceği doğal yol şöyle:
1.	Onboarding / İlk Kurulum
o	Hesap oluşturma
o	İlk vizyonu ekleme
o	İlk bir kaç kişiyi ekleme önerisi
2.	Ana Dashboard (Graph View)
o	Tüm kişileri, hedefleri, vizyonu bir graph olarak görme
o	Filtre uygulama
o	Kişi/Node detaylarını açma
3.	Kişi Detay Ekranı (Side Panel)
o	Kişi bilgisi
o	Sektör/etiket düzenleme
o	İlişki gücü
o	Bağlı olduğu hedefler/projeler
o	“Bu kişi kimlerle bağlantılı?” mini graph
4.	Vizyon–Hedef–Proje Paneli
o	Solda ağaç görünümü
o	Vision
→ Goal
→ Project
o	Her katman tıklanınca detay panel açılır
o	Kişileri sürükleyerek hedeflere bağlayabilme
5.	Filtre & Arama Paneli
o	Sektör filtreleri
o	İlişki gücü aralığı
o	Etiket filtreleri
o	Kişi arama
o	Sadece hedefler veya sadece kişiler modları
6.	AI Öneri Paneli
o	Seçili hedef için en uygun kişiler listesi
o	Network zayıflık/kuvvet analizleri
o	Sektörel dağılım
o	“Bu proje için kimlere gitmelisin?”
Bu akış, hem yeni kullanıcı hem de ileri seviye kullanıcı için sezgisel.
________________________________________
2. Wireframe Seviyesinde Tasarım
Şimdi her ana ekranın kabaca arayüz modelini çıkarıyorum.
Bu model bileşenleri netleştirdiği için frontend’de React Flow, Cytoscape, side-panel mimarisi, component tree çok daha kolay oluşur.
________________________________________
2.1 Ana Ekran: Graph View
 ----------------------------------------------------------
| Top Nav (Logo | Search Bar | Add Person + Add Goal Btns) |
 ----------------------------------------------------------
| Left Panel (Collapsible):                                |
| - Vision–Goal–Project Tree                               |
| - Filters (Sector / Relationship Strength / Tags)        |
|                                                          |
|                                                          |
|                       GRAPH AREA                         |
|          (zoom, pan, drag, click to open detail)         |
|                                                          |
|  Node States:                                             |
|  - Person nodes (circle)                                 |
|  - Goal nodes (rounded square)                           |
|  - Vision node (büyük merkez node)                       |
|                                                          |
 ----------------------------------------------------------
| Right Side Panel (contextual):                           |
| Açılır kapanır                                           |
 ----------------------------------------------------------
Graph Area fonksiyonları:
•	Çift tık → yeni node yaratma (opsiyonel)
•	Sürükle bırak düzenleme
•	Node hover → mini bilgi kartı
•	Node click → sağ panel açılır
•	Edge click → ilişki bilgisi düzenlenebilir
________________________________________
2.2 Kişi Detay Paneli (Right Side Panel)
 -----------------------------------------
| Person Card Panel                       |
 -----------------------------------------
| FOTO / İSİM / ROL / ŞİRKET              |
| Sector: [dropdown]                      |
| Tags: [tag input]                       |
| Relationship Strength: slider (0–5)     |
| Notes: textarea                         |
|                                         |
| Connections: mini-graph visualization   |
| - Kimlerle bağlantılı                   |
| - Edge strength gösterimi               |
|                                         |
| Linked Goals / Projects                 |
| - Goal 1 (relevance score)              |
| - Goal 2                                |
|                                         |
| Button: “Bu kişiyi hedefe bağla”        |
| Button: “AI analizi göster”             |
 -----------------------------------------
Bu panel uygulamanın en sık kullanılan bölümlerinden biri.
________________________________________
2.3 Vision–Goal–Project Tree (Left Panel)
 ----------------------------------------
| VISION TREE                             |
 ----------------------------------------
| [Vision] Girişimi ticarileştirmek       |
|    > Goal: MVP lansmanı                 |
|         > Project: Onboarding akışı     |
|         > Project: Beta kullanıcı list. |
|    > Goal: Network genişletme           |
|         > Project: Yatırımcı buluşmaları|
 ----------------------------------------
Fonksiyonlar:
•	Vision/Goal/Project ekleme
•	Drag & drop ile sıralama
•	Hiyerarşide yer değişikliği (Goal → başka Vision)
•	Node click → sağ panelde detay
•	Sürüklenip graph üzerindeki kişilere bırakılabilir
→ otomatik SUPPORTS edge oluşturur
________________________________________
2.4 Filtre Paneli
 -----------------------------------------
| Filters                                 |
 -----------------------------------------
| Sector Filter: [dropdown list]          |
| Relationship Strength: [0–5 range]      |
| Tags: [multi-select]                    |
| Node Type:                              |
|   [x] Persons                            |
|   [x] Goals                              |
|   [x] Projects                           |
|   [ ] Vision only                        |
 -----------------------------------------
| Buttons                                 |
|  - Apply Filter                          |
|  - Clear Filter                          |
 -----------------------------------------
Graph sadece istenen düğümleri gösterir; diğerleri gri-out olur veya tamamen gizlenir.
________________________________________
2.5 AI Paneli (Insights)
Bu panel hedef odaklı açılır.
 ------------------------------------------------
| AI Insights for “MVP lansmanı”                 |
 ------------------------------------------------
| Suggested Contacts (score’a göre sıralı)       |
|   1. Ahmet Yılmaz (0.82)                        |
|   2. Deniz Kara (0.74)                          |
|   3. Ece Demir (0.66)                           |
|                                                 |
| Network Gaps                                    |
| - Fintech sektöründe güçlü                      |
| - Marketing sektöründe zayıf                    |
|                                                 |
| Opportunities                                    |
| - “Şu 2 kişiyle son 60 gündür iletişim yok”     |
| - “Bu projenin kritik aşamasında X kişisi lazım”|
 ------------------------------------------------
Bu panel MVP’de basit, sonra gelişir.
________________________________________
2.6 Kişi Ekle Modalı
 -----------------------------------------
| Add Person                              |
 -----------------------------------------
| Name:                                   |
| Sector: dropdown                         |
| Tags: input                              |
| Role / Company                           |
| Relationship Strength: slider            |
| Notes: textarea                          |
| [Save]                                   |
 -----------------------------------------
Basit ama kritik.
________________________________________
3. Akış Senaryosu
Aşağıda tipik bir kullanıcı senaryosunu ekliyorum, tasarımın mantığı otursun:
1.	Kullanıcı dashboard’a girer, ortada graph boş.
2.	Soldan ilk vizyonu ekler.
3.	Altına 2–3 hedef ekler.
4.	Üstten kişi ekler (Ahmet, Deniz…).
5.	Kişiyi tutup hedef üzerine sürükler.
→ SUPPORTS edge oluşur.
6.	Graph anında güncellenir.
7.	Seçili hedef için AI panel açılır;
→ “Bu hedefe en uygun kişiler şunlar.”
8.	Filtre açılır: “Fintech + yüksek ilişki gücü”
Graph temizleşir.
9.	Sağ panelden kişi notu ekler.
10.	Vision ağacı büyüdükçe graph stratejik haritaya dönüşür.
________________________________________
Bu aşamada ne elde ettik?
1.	Ürünün tüm ekran yapısı netleşti.
2.	Bileşenler bağımsız geliştirilebilir hale geldi.
3.	Graph tabanlı arayüz için gerekli tüm UI fonksiyonları listelendi.
4.	AI paneli MVP’de hafif, uzun vadede güçlü olacak şekilde konumlandırıldı.














1. Yüksek seviye sistem mimarisi
Şu yapıyı hedefliyorum:
•	Frontend (React SPA)
o	Graph UI, kişi/vizyon/goal yönetimi, filtreler, AI paneli
•	Backend API (FastAPI)
o	Auth, CRUD, graph işlemleri, AI servisleri için gateway
•	Graph Database (Neo4j)
o	Person, Goal, Vision, Project node’ları
o	KNOWS, SUPPORTS, BELONGS_TO edge’leri
•	AI Service (aynı backend içinde modül veya ayrı servis)
o	Embedding al
o	Relevance score hesapla
o	Basit network analizleri
•	Storage (ileride)
o	Loglar, event tracking vs. için ayrı bir Postgres/Clickhouse düşünülebilir ama MVP’de şart değil.
İlk etapta her şey tek backend serviste toplanabilir; ileride “AI servis” ayrı mikroservise ayrılabilir.
________________________________________
2. Frontend: teknoloji ve component tree
2.1 Teknolojiler
•	React + TypeScript
Tip güvenliği + daha rahat refactor.
•	Graph library:
o	İlk tercih: React Flow (node/edge tabanlı, editor / mind-map vibe’ı için uygun).
o	Alternatif: Cytoscape.js (daha ağır, network analizi tarafında çok güçlü).
•	State management:
o	Basit ve local için: Zustand
o	Daha klasik pattern istersen Redux Toolkit
•	UI:
o	Tailwind CSS
o	Component kütüphanesi olarak Radix UI veya shadcn/ui tarzı bir şey kullanılabilir.
MVP için React + TS + React Flow yeterince güçlü.
2.2 Component Tree (kabaca)
<App>
  <AuthProvider>
    <Router>
      <Layout>
        <TopNav />
        <Main>
          <GraphPage>
            <VisionGoalTree />      // Sol panel
            <GraphCanvas />         // Orta alan
            <RightPanel />          // Sağ panel (contextual)
          </GraphPage>
        </Main>
      </Layout>
    </Router>
  </AuthProvider>
</App>
Detay:
•	<TopNav />
o	SearchBar
o	“Add Person”, “Add Goal”, “Add Vision” butonları
o	Kullanıcı menüsü
•	<VisionGoalTree />
o	<VisionTreeItem />
o	Her Vision altında <GoalTreeItem />
o	Her Goal altında <ProjectTreeItem />
•	<GraphCanvas />
o	React Flow wrapper
o	Node renderer:
	PersonNode
	GoalNode
	VisionNode
	ProjectNode
o	Context menü, zoom, pan
•	<RightPanel />
o	Mode’a göre:
	<PersonDetailPanel />
	<GoalDetailPanel />
	<VisionDetailPanel />
	<ProjectDetailPanel />
	<AiInsightPanel />
•	Modal’lar:
o	<AddPersonModal />
o	<AddGoalModal />
o	<AddVisionModal />
o	<AddProjectModal />
State:
•	graphStore (Zustand):
o	nodes, edges, selectedNodeId, filters
•	uiStore:
o	openPanels, modals, loading flags
Bu yapı hem okunaklı hem de büyümeye uygun.
________________________________________
3. Backend: teknoloji ve servis mimarisi
3.1 Teknoloji seçimi
Mevcut backend Spring Boot 3.5 + Java 21 + Maven tabanlı; Spring Boot Web/Data JPA/Security starter'ları, PostgreSQL 16 + pgvector, LangChain4j + Ollama entegrasyonu ve test tarafında JUnit/Mockito/Testcontainers kullanılıyor.

3.2 Modüler yapı
`backend-java/src/main/java/com/fahribilgen/networkcrm` altında aşağıdaki paketler bulunuyor:
- `controller` (Auth, Node, Graph, Ai vb.)
- `service` + `service.impl` (NodeService, RecommendationService, GraphService...)
- `entity`, `repository`, `payload`, `security`, `config`
- `config/AiConfig` LangChain4j bağlayıcısı, `security` JWT filtreleri

3.3 API endpoint’leri (netleştirme)
Spring Boot RestController yapısıyla `/api/auth`, `/api/nodes`, `/api/graph`, `/api/ai`, `/api/visions`, `/api/goals`, `/api/projects` patikleri hazır; README'deki "Useful APIs" tablosu güncel referanstır.
Önceden taslağını yaptık, şimdi bir tık daha konkretize ediyorum.
Person:
•	POST /api/v1/person
•	GET /api/v1/person/{id}
•	PUT /api/v1/person/{id}
•	DELETE /api/v1/person/{id}
•	GET /api/v1/person?sector=&tags=&q=
Graph:
•	GET /api/v1/graph/main
o	Kullanıcının ana graph’ını getirir (nodes + edges)
•	POST /api/v1/graph/relation/knows
•	POST /api/v1/graph/relation/supports
•	POST /api/v1/graph/relation/belongs
AI:
•	POST /api/v1/ai/goal/{goal_id}/suggest-people
•	POST /api/v1/ai/embed/person/{person_id}
•	POST /api/v1/ai/embed/goal/{goal_id}
FastAPI ile OpenAPI spec otomatik çıkacağı için frontend’in entegrasyonu kolay olur.
________________________________________
4. AI Pipeline Tasarımı
Amaç:
•	Kişi ve hedef açıklamalarını embedding’e çevir
•	Goal ↔ Person eşleşmesini skorla
•	İlkel ama işe yarar bir öneri motoru üret
4.1 Embedding stratejisi
•	String birleştirme:
o	Person için: "{name} - {role} - {company} - {sector} - {notes}"
o	Goal için: "{title} - {description} - {priority}"
•	Bu string’i alıp embedding modeline gönder
o	Örnek: text-embedding-3-large gibi bir model (OpenAI tarafında)
•	Embedding’leri Neo4j’de property olarak değil, ayrı bir store’da da tutabilirsin. MVP’de Neo4j node property’si olarak dahi tutulabilir (float array).
4.2 Relevance score hesaplama
Basit formül:
1.	Goal embedding’i ile Person embedding’i arasında cosine similarity
2.	Gerektiğinde sektör uyumu gibi bir çarpan eklenebilir:
Örneğin:
•	similarity = cosine(goal_vec, person_vec)
•	sector_bonus = 0.1 eğer aynı sektördelerse
•	final_score = similarity + sector_bonus
SUPPORTS edge’inin relevance_score alanını bu hesapla set edebilirsin.
4.3 AI service akışı
1.	Frontend, “bu hedef için öneri ver” der:
o	POST /ai/goal/{goal_id}/suggest-people
2.	Backend:
o	Goal node’u ve embedding’ini alır
o	İlgili tüm Person node’larının embedding’lerini çeker
o	Skorları hesaplar
o	En yüksek 10 kişiyi döner
3.	Frontend:
o	Sağ panelde “AI Insights” listesi gösterir
o	Kullanıcı isterse “Bu kişiyi hedefe bağla” butonuna basar
→ SUPPORTS edge oluşturulur
Bu pipeline hem basit hem de genişlemeye açık.
________________________________________
5. Deployment ve altyapı
Başlangıç için önerilen kurulum:
- Frontend: React build çıktısını Vercel/Netlify/S3+CloudFront üzerinde servis etmek.
- Backend (Spring Boot): Docker imajı olarak Fly.io, Render, Railway veya herhangi bir JVM destekli PaaS; PostgreSQL erişimi olan küçük bir instance yeterli.
- PostgreSQL 16 + pgvector: Docker Compose ile yerel, üretimde ise managed Postgres veya RDS + pgvector uzantısı.
- Opsiyonel olarak Ollama/LLM servisleri için ayrı host.

Konfigürasyon:
- `SPRING_DATASOURCE_URL/USERNAME/PASSWORD`
- `APP_JWTSECRET`
- `LANGCHAIN4J_OLLAMA_BASE_URL`
- `VITE_API_BASE_URL`

JWT zorunlu olduğu için üretimde güçlü secret/rotate politikası ve HTTPS reverse proxy önerilir.

--------------------------------------------------------------------------------------------------



# MOBİL ÜRÜN – KİLİTLENMİŞ VİZYON & ÖZELLİK SETİ

## 1. Mobil Ürünün Vizyonu

**Mobil uygulama, tanıştığın insanları kaybetmemen ve ihtiyaç duyduğunda hızlıca bulman içindir.**

* LinkedIn rakibi değil
* Sosyal ağ değil
* Chat uygulaması değil

Mobil = **kişisel network hafızası**

---

## 2. Mobilin Rolü (Scope)

Mobil:

* Sahada hızlı veri girişi
* Hafızaya alma
* Basit erişim

Mobil **değildir**:

* Analiz aracı
* Strateji aracı
* AI ürünü
* Graph aracı

Web:

* Graph
* Vision / Goal / Project
* AI analiz
* Premium

---

## 3. Çözülen Temel Problemler

1. Tanıştım ama unuttum
2. Arıyorum ama bulamıyorum
3. Kimdi bu, ne konuşmuştuk?

Mobil sadece bu 3 probleme odaklanır.

---

## 4. Mobil Özellikler (KESİN)

### 4.1 Kayıt & Profil

Kayıt olurken alınır:

* İsim
* Sektör
* Kısa bio (1 satır)
* Telefon
* Email
* Opsiyonel LinkedIn

**Prensip:**
İletişim bilgisi alınır ama **private** tutulur.

---

### 4.2 Ana Ekran – Sektör Dizini

* Sektör listesi
* Her sektör altında kişi sayısı
* Sektör içine girince kişi listesi

Sıralama:

* Varsayılan: son eklenen
* Alternatif: son etkileşim

---

### 4.3 Kişi Kartı

Zorunlu:

* İsim
* Sektör
* Etiketler

Opsiyonel:

* Nerede tanıştık
* Ne konuştuk
* Tarih (otomatik)
* Telefon / Email / LinkedIn

İletişim bilgisi yoksa:

* Görsel olarak “eksik” hissi verilir
* Ama zorlanmaz

---

### 4.4 Hızlı Kişi Ekleme

Alanlar:

* İsim (zorunlu)
* Sektör (zorunlu)
* 1 satır not (opsiyonel)

Hedef süre: **< 15 saniye**

---

### 4.5 Kayıtlı Kullanıcıyla Ekleşme

Akış:

1. İsim + sektörle arama
2. Mini profil görüntüleme
3. “Tanıştık” isteği
4. Kabul edilince otomatik ekleme ve sınıflandırma

Sosyal ağ değil, doğrulama.

---

### 4.6 İletişim Paylaşımı (kritik karar)

**Kayıt sırasında:**

* Telefon / Email alınır
* Varsayılan: private

**Bağlantı sonrası:**

* Kullanıcı isterse paylaşır
* Telefon / Email / LinkedIn için ayrı ayrı opt-in

Otomatik paylaşım yok.

---

### 4.7 İletişim Kurma

Uygulama:

* Arama yapmaz
* Mesaj göndermez

Sadece:

* 📞 Ara
* ✉️ Mail at
* 🔗 LinkedIn’de aç

---

## 5. Mobilde BİLİNÇLİ OLARAK OLMAYANLAR

* AI
* Graph
* Vision / Goal / Project
* Chat
* Network analizi
* Karmaşık filtreler
* Sosyal feed
* Influence score

---

## 6. Mobil – Web Ayrımı

Mobil:

* Input
* Hafıza
* Free

Web:

* Analiz
* Strateji
* AI
* Premium

Tek backend, tek veri modeli.

---

## 7. Gizlilik & Güven Prensibi

> **İletişim bilgisi bizde durur, paylaşım kararı kullanıcıdadır.**

Bu prensip:

* Spam’i önler
* Güveni artırır
* Sosyal baskıyı azaltır

---

## 8. Mobil Başarı Metrikleri

* Ortalama kişi ekleme süresi (<15 sn)
* 7 gün sonra arama oranı
* Kişi başına iletişim bilgisi ekleme oranı
* “Geri dönüp bulma” davranışı

---

## 9. Tek Cümlelik Mobil Tanım

**“Tanıştığın insan kaybolmaz.”**

---

## 10. Kilitlenmiş Kararlar (özet)

* Mobil ayrı ürün, ortak platform
* Mobil AI’sız
* Sektör bazlı hafıza
* İletişim bilgisi alınır, paylaşım opt-in
* Web premium, mobil free

---

Bu dokümanla:

* Mobil scope kilitlendi
* Feature creep önlendi
* Web ile sınırlar netleşti


Aşağıdaki teknik plan, konuştuğumuz mobil vizyonu **mevcut Spring Boot + Postgres + React web** altyapısına oturtacak şekilde “yapılabilir ve kontrol edilebilir” biçimde tasarlanmıştır. Amaç: **tek backend, tek veri modeli**, mobil için ayrı ürün davranışı.

---

## 1. Veri Modeli Değişiklikleri

### 1.1 `users` tablosu: profil + iletişim (private)

Kayıtta alınacak alanlar:

* `full_name` (zorunlu)
* `sector` (zorunlu)
* `bio` (opsiyonel, kısa)
* `email` (zorunlu veya opsiyonel karar; pratikte auth için zaten email kullanıyorsan zorunlu)
* `phone_e164` (opsiyonel ama teşvikli)
* `linkedin_url` (opsiyonel)

Not: `phone_e164` formatını standardize et (E.164). UI tarafında ülke seçimi ile normalize et.

### 1.2 “Kişi kartı” (NodeType.PERSON) iletişim alanları

Mobilde kişi kartı iki tür olabilir:

* **Manual person**: kullanıcı kendi ekledi, iletişim alanları serbest
* **Registered person**: uygulamadaki kullanıcıdan türeyen kişi, iletişim paylaşımı opt-in

Bu ayrımı tutmak için `nodes` içine minimal ek alanlar:

* `owner_user_id` (zaten var)
* `linked_user_id` (nullable) → bu person node’u bir uygulama kullanıcısına bağlıysa
* `contact_phone` (nullable)
* `contact_email` (nullable)
* `contact_linkedin` (nullable)

Kural:

* `linked_user_id != null` olan person node’unda `contact_*` alanları **varsayılan boş** gelir.
* Bu alanlar sadece karşı taraf “paylaş” açınca doldurulur.

### 1.3 İletişim paylaşım politikası: `user_contact_shares`

Kayıtlı kullanıcıların hangi bilgilerini bağlantılarına açtığını tutan bir tablo:

`user_contact_shares`

* `id`
* `user_id` (paylaşan)
* `share_phone` (bool)
* `share_email` (bool)
* `share_linkedin` (bool)
* `updated_at`

İstersen “kişiye özel paylaşım” (A’ya açık, B’ye kapalı) da yapabilirsin ama ilk faz için global toggle yeterli.

### 1.4 “Ekleşme” (mutual connect) modeli: `connection_requests` + `connections`

İki aşamalı model net ve abuse yönetimi için gerekli.

`connection_requests`

* `id`
* `from_user_id`
* `to_user_id`
* `status` (PENDING/ACCEPTED/REJECTED/CANCELLED)
* `created_at`, `responded_at`

`connections`

* `id`
* `user_a_id`
* `user_b_id`
* `created_at`

Kural: ACCEPTED olunca `connections` yarat.

### 1.5 Otomatik sınıflandırma (sektör) nasıl olacak?

* Karşı tarafın `users.sector` değeri var.
* Connection kabul edilince, kabul eden kullanıcının graph’ında bir `Person` node yaratılır:

  * `name = users.full_name`
  * `sector = users.sector`
  * `linked_user_id = users.id`
  * `tags = []`
  * `relationship_strength = default` (ör. 2)
  * `notes = null`
  * `created_at = now`
* Aynı işlem diğer taraf için de yapılır (opsiyon: iki taraf da otomatik birbirini node olarak eklesin).

---

## 2. Backend API Tasarımı

### 2.1 Auth & Profile

* `POST /api/auth/register`

  * body: `fullName, sector, bio?, email, password, phone?, linkedinUrl?`
* `GET /api/me`
* `PUT /api/me`

  * profil güncelleme (sector/bio/phone/linkedin)

### 2.2 Mobile directory: kullanıcı arama (isim + sektör)

Salt isim riskli olduğu için minimum doğrulama bilgisi döndür:

* `GET /api/users/search?q=&sector=`

  * response item: `userId, fullName, sector, bioShort, linkedinUrl? (opsiyon)`

Rate limit burada önemli (abuse). En azından IP/user bazlı basit limit.

### 2.3 Connection request akışı

* `POST /api/connections/requests`

  * body: `toUserId`
* `GET /api/connections/requests?status=PENDING` (inbound/outbound ayrı)
* `POST /api/connections/requests/{id}/accept`
* `POST /api/connections/requests/{id}/reject`
* `GET /api/connections` (list)

ACCEPT sırasında:

1. `connections` kaydı yarat
2. Her iki kullanıcı için `Person` node oluştur / varsa reuse et
3. Bu node’ları “sektör klasörü”nde otomatik görünür kıl

### 2.4 Contact sharing (opt-in)

* `GET /api/me/contact-sharing`
* `PUT /api/me/contact-sharing`

  * body: `{ sharePhone, shareEmail, shareLinkedin }`

Bağlantı listesinde karşı tarafın paylaşıma açtığı alanları döndürmek için:

* `GET /api/connections/contacts`

  * response: `connectionUserId, sharedPhone?, sharedEmail?, sharedLinkedin?`

Backend kuralı:

* Paylaşım kapalıysa alanlar null döner.

### 2.5 Mobil kişi yönetimi (manual person)

Mevcut Node API’n varsa onu kullan, yoksa mobil için sade uçlar aç:

* `POST /api/mobile/people`

  * body: `name, sector, tags?, notes?, phone?, email?, linkedin?`
  * type=PERSON
* `GET /api/mobile/people?sector=&q=&tag=`
* `GET /api/mobile/people/{id}`
* `PUT /api/mobile/people/{id}`
* `DELETE /api/mobile/people/{id}`

Not: `sector` indexlenmeli, `q` için trigram/GIN (Postgres) veya basit ILIKE yeter.

---

## 3. Servis Katmanı: kritik iş kuralları

### 3.1 Person node oluşturma (registered user’dan)

`PersonFromUserFactory` gibi bir servis:

* idempotent çalışsın: aynı `linked_user_id` için tekrar node açmasın
* kullanıcı bazında (`owner_user_id`) unique olsun

Unique constraint önerisi:

* `(owner_user_id, linked_user_id)` unique

### 3.2 Contact paylaşımı sync

Bağlantı kabul edildikten sonra paylaşım toggle değişince ne olacak?

İki seçenek:

1. **Runtime fetch**: Mobil kişi kartında iletişim bilgisi gösterirken `/connections/contacts` üzerinden anlık getir, node’a yazma.
2. **Materialize**: Paylaşıma açılınca ilgili `Person` node’lara `contact_*` yaz.

Gerçekçi ve temiz seçenek: **(1) Runtime fetch**

* Veriyi iki yerde tutmazsın
* Privacy bug riski düşer

Yani `Person` node’daki `contact_*` alanları sadece manual kişiler için; registered bağlantılarda iletişim “connection contacts” üzerinden gelir.

---

## 4. Mobil Uygulama Mimarisi

### 4.1 Teknoloji seçimi

Gerçekçi seçenekler:

* **React Native + Expo** (hızlı iterasyon, tek codebase)
* Alternatif: Flutter (daha ağır yatırım)

Senin stack React olduğu için RN/Expo mantıklı.

### 4.2 Ekranlar (minimum ama tam)

1. Auth

* Register (profil + iletişim)
* Login

2. Home (Sektör Dizini)

* sektör listesi + kişi sayıları

3. SectorPeopleList

* liste + arama (name/tag)
* sort: recent / lastInteraction

4. PersonDetail

* kişi bilgileri
* contact actions: Call / Email / LinkedIn
* notes + tags edit

5. AddPerson (Quick add)

* name + sector + note + (optional contact)

6. Connect (Kayıtlı kullanıcı ara + istek)

* search users
* send request
* inbound requests inbox

7. Settings

* Contact sharing toggles
* Profile edit

### 4.3 Local cache (offline-first hafif)

Mobilde “kaydetme hızlı” olmalı. Minimum:

* SQLite (Expo SQLite) veya MMKV/AsyncStorage + server sync
* Create/update işlemlerini kuyruklayıp online olunca gönder

Ama ilk fazda bile:

* “Kaydet tuşuna basınca kaybolmasın” için optimistic UI şart.

---

## 5. Güvenlik ve Abuse Kontrolleri

Bu işin ölçeği küçük olsa bile temel kontrol şart.

* `users/search` rate limit
* Connection request limit:

  * günde X istek
  * aynı kullanıcıya tekrar istek engeli
* Blocklist (erken koymak iyi):

  * `POST /api/connections/block/{userId}`
  * block’lu kullanıcı aramada çıkmaz, istek atamaz

Privacy:

* Phone/email varsayılan private
* Paylaşım toggles default false
* Paylaşım kapandığında API null döndürür (geçmiş loglarda saklamazsın)

---

## 6. Web Premium ile Uyumluluk

Web’i “dokunma” moduna almıştın. Burada sadece iki şey gerekir:

1. Web’de premium:

* AI/graph vs zaten var.
* Mobilin ürettiği manual persons web graph’ta görünür.

2. Web’de “hijyen göstergeleri” (çok düşük efor, yüksek değer):

* “İletişim bilgisi eksik kişi sayısı”
* “Son 30 gün temas yok listesi” (AI’sız bile manuel lastInteraction ile)

Bunlar premium değerini artırır ama mobil scope’u bozmaz.

---

## 7. Uygulama Planı

### Faz 1: Temel mobil (hafıza)

* Register/Login
* Quick add manual person
* Sector index + search
* Person detail + Call/Email/LinkedIn actions

### Faz 2: Ekleşme (kayıtlı kullanıcı)

* User search
* Connection requests
* Contact sharing toggles
* Connection contacts fetch

### Faz 3: Hijyen ve kalite

* Offline queue
* Block/rate limit
* lastInteraction alanı (manuel “bugün konuştuk” butonu)

---

## 8. “Done” Tanımı

Mobil teknik olarak “bitti” demek için:

* 15 saniyede kişi ekleniyor
* Sektöre göre 2 tap ile kişi bulunuyor
* Kişi kartından tek tap ile arama/mail/linkedin açılıyor
* Kayıtlı kullanıcı ekleşmesi çalışıyor
* İletişim paylaşımı opt-in ve geri alınabilir

---

