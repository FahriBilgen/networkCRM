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
2.2 Neo4j Şema Tasarımı
Node Labels
:Person
:Vision
:Goal
:Project
Properties
Person
name, sector, tags, relationship_strength, notes, company, role, linkedin_url, embeddings
Goal
title, description, due_date, priority
Vision
title, description, priority
Project
title, description, status, priority, start_date, end_date
Relationship Types
1.	(:Person)-[:KNOWS {relationship_strength, relationship_type, last_interaction_date}]->(:Person)
2.	(:Person)-[:SUPPORTS {relevance_score, added_by_user, notes}]->(:Goal|:Project)
3.	(:Goal)-[:BELONGS_TO {order}]->(:Vision)
4.	(:Project)-[:BELONGS_TO {order}]->(:Goal)
Birkaç query örneği
Bir hedef için en uygun kişileri bul:
MATCH (p:Person)-[s:SUPPORTS]->(g:Goal {id: "goal_1"})
RETURN p, s.relevance_score
ORDER BY s.relevance_score DESC
Bir kişinin tüm networkü:
MATCH (p:Person {id: "person_123"})-[:KNOWS*1..2]-(others)
RETURN others
Bir vizyonun tüm alt hedef ve projeleri:
MATCH (v:Vision {id:"vision_1"})<-[:BELONGS_TO*]-(n)
RETURN n
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
Backend için net bir tercih yapıyorum:
•	Python + FastAPI
o	AI ve embedding işleri için Python ekosistemi rahat
o	Async IO destekli, performansı yeterli
o	Tip desteği ile orta-uzun vadede kod kalitesi korunur
Diğer seçenek Node/NestJS de olur ama AI tarafıyla çok uğraşacağın için Python daha doğal.
3.2 Modüler yapı
Backend’i modüllere böl:
•	auth
•	person
•	vision_goal_project
•	graph
•	ai
Örnek dosya yapısı:
app/
  main.py
  api/
    v1/
      person.py
      vision.py
      goal.py
      project.py
      graph.py
      ai.py
  core/
    config.py
    security.py
  services/
    neo4j_client.py
    ai_client.py
    graph_service.py
    recommendation_service.py
  models/
    person.py
    vision.py
    goal.py
    project.py
  schemas/
    person.py
    ...
3.3 API endpoint’leri (netleştirme)
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
Başlangıç için mantıklı bir setup:
•	Frontend:
o	Static build (React) → Vercel / Netlify / S3 + CloudFront
•	Backend (FastAPI):
o	Docker image
o	Fly.io, Render, Railway, DigitalOcean, vs.
o	Küçük bir instance ile başlar
•	Neo4j:
o	Neo4j Aura (managed service)
veya
o	Kendi Docker container’ında Neo4j
Config:
•	.env:
o	DB_URI, DB_USER, DB_PASS
o	OPENAI_API_KEY
o	CORS origins
o	JWT secret (eğer auth ekleyeceksen)
MVP’de auth çok basit tutulabilir (tek kullanıcı / basic token) ama ürünleşecekse JWT/OAuth düşünülmeli.


