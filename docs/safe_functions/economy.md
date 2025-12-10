# Economy & Resources Functions

Economy kategorisi, stok yönetimi ve kaynak optimizasyonu için kullanılan fonksiyonları kapsar. Gıda, mühimmat, malzeme ve üretim kapasitesi üzerinde çalışırlar.

Örnek fonksiyonlar:

- `allocate_food(amount:int, target:str)` — Mevcut erzakı belirli birimlere yönlendirir.
- `gather_supplies(region:str, effort:int)` — Keşif birlikleriyle yeni kaynak toplar.
- `boost_production(workshop:str, focus:str)` — Belirli bir üretim hattına ekstra iş gücü atar.
- `check_inventory(resource:str)` — Belirli kaynakların güncel stok seviyelerini raporlar.

Bu fonksiyonlar `metrics.resources`, `stockpiles`, `logs` ve bazen `world.resources` alanlarını günceller.
