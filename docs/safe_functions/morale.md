# Morale & Social Functions

Morale kategorisi, asker ve sivillerin moralini dengelemek, paniği azaltmak ve motivasyonu artırmak için tasarlanmıştır. Sosyal ritüeller, ödüller ve disiplin hamleleri bu grupta yer alır.

Örnek fonksiyonlar:

- `inspire_troops(speech:str, bonus:int?)` — Cephedeki birliklere moral desteği verir.
- `calm_civilians(zone:str, effort:int)` — Halkın paniğini azaltmak için destek ekipleri gönderir.
- `reward_bravery(npc_id:str, reward:str)` — Başarılı NPC'leri ödüllendirir.
- `assign_morale_officer(npc_id:str, sector:str)` — Belirli bir bölgede moral takibi için sorumlu atar.

Bu fonksiyonlar `metrics.morale`, `logs` ve NPC durum alanlarında değişikliğe yol açar.
