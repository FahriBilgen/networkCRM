# Structure Functions

Structure kategorisi, surların ve kritik savunma yapılarının dayanıklılığını artırmaya odaklanır. Bu fonksiyonlar belirli yapıların dayanımı, durumu ve bütünlüğünü günceller.

Örnek fonksiyonlar:

- `reinforce_wall(structure_id:str, amount:int, material:str?)` — Seçilen duvar bölümünün bütünlüğünü yükseltir.
- `repair_gate(gate_id:str, amount:int)` — Kapılardaki hasarı azaltır ve tekrar kullanım için hazırlar.
- `clear_rubble(section_id:str)` — Kuşatma molozlarını temizleyerek hareket alanı açar.
- `inspect_wall(section_id:str)` — Hasarı raporlar, potansiyel zayıf noktaları ortaya çıkarır.

Structure fonksiyonları tipik olarak `structures`, `metrics.wall_integrity` ve `log` alanlarını etkiler.
