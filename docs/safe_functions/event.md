# Event & World Functions

Event kategorisi, dünya durumuna dair olay işaretleri, çevresel tepkiler ve alarm mekanizmalarını içerir. Bu fonksiyonlar harita işaretlerini oluşturur, kaldırır ya da çevre koşullarını değiştirir.

Örnek fonksiyonlar:

- `spawn_event_marker(marker_id:str, x:int, y:int, severity:int?)` — Haritada yeni bir uyarı işareti oluşturur.
- `trigger_alarm(level:str, message:str?)` — Kale içinde uyarı seviyesi artırılır.
- `create_storm(duration:int, intensity:int)` — Atmosferik koşulları değiştirir.
- `reinforce_tunnel(tunnel_id:str, amount:int)` — Yer altı erişimlerini sağlamlaştırır.

Event fonksiyonları `map_event_markers`, `environment` alanları ve turn loglarını etkiler.
