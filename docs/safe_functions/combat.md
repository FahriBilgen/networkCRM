# Combat Functions

Combat kategorisi, kuşatma baskısını yönetmek ve düşman tehdidine karşı aktif savunma hamleleri üretmek için kullanılır. Bu fonksiyonlar tehdit seviyesini manipüle eder, moral üzerinde baskı kurar ve savaş alanındaki birlikleri yönlendirir.

Örnek fonksiyonlar:

- `apply_combat_pressure(intensity:int)` — Tehdit skorunu yükseltip moral düşürerek saldırı hissini güçlendirir.
- `reduce_threat(amount:int)` — Kontratak veya planlı geri çekilme ile tehdit seviyesini düşürür.
- `deploy_archers(position:coord, volleys:int?)` — Uzak menzilli saldırı düzenleyerek belirli koordinatlara baskı uygular.
- `set_ambush(npc_id:str, x:int, y:int)` — Birliği gizli pozisyona çekerek bir sonraki turda avantaj sağlar.

Combat fonksiyonları genelde `threat`, `morale` ve `log` alanlarında belirgin değişiklikler yapar.
