# NPC Functions

NPC kategorisi, bireysel karakterlerin pozisyonlarını, rollerini ve durumlarını yönetmek için kullanılır. Bu fonksiyonlar doğrudan `npc_locations` ve ilişkili alanlarda değişiklik yapar.

Örnek fonksiyonlar:

- `move_npc(npc_id:str, x:int, y:int, room:str?)` — Seçilen NPC'yi yeni koordinatlara taşır.
- `assign_role(npc_id:str, role:str)` — Operasyonel rolü değiştirir.
- `heal_npc(npc_id:str, amount:int)` — Morali ve sağlık durumunu iyileştirir.
- `send_on_patrol(npc_id:str, duration:int)` — NPC'yi belirli süreliğine devriyeye çıkarır.

NPC fonksiyonları koordinat verilerini günceller, hedef NPC'nin rol ve statülerini değiştirir ve genellikle log girdileri oluşturur.
