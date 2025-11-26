# Safe Function Lookup

Bu tablo sahne yazarları ve ajan prompt'ları için nadir/günlük safe function'ların hızlı referansıdır.

## Sık Kullanılanlar

| Fonksiyon | Amaç | Temel kwargs |
|-----------|------|--------------|
| `update_map_layer` | Katman görünürlüğü/tehdit seviyesini güncelle | `layer_id`, `label`, `status`, `summary` |
| `adjust_npc_role` | NPC rol/stance/lokasyonunu hizala | `npc_id`, `role`, `stance`, `location` |
| `spawn_event_marker` | Haritada uyarı/etkinlik işareti çıkar | `marker_id`, `room`, `severity`, `summary` |
| `adjust_metric` | Morale/order/resources gibi metriklere delta uygula | `metric`, `delta`, `cause` |
| `move_npc` | NPC'yi sahnede başka odaya taşı | `npc_id`, `location` |
| `change_weather` | Atmosfer ve sensory detaylarını değiştir | `atmosphere`, `sensory_details` |

## Nadir / Lookup

| Fonksiyon | Kullanım Durumu |
|-----------|-----------------|
| `schedule_npc_activity` | NPC Behavior Engine ile uyumlu deterministik rota planla |
| `queue_major_event` | Major olay kuyruğunu doldur; risk bütçesi uygunsa |
| `reinforce_structure` | Duvar/kapı dayanımını yükselt |
| `repair_breach` | Belirli breach noktalarını tamir et (kaynak harcar) |
| `adjust_stockpile` | Stok seviyelerini ince ayarla; negatif değer yok |
| `set_watcher_route` | Watcher devriyelerini çok odalı rotalara ata |

> Not: CLI `share_card` komutu ve `/game/share-card` endpoint'i run başına hangi unlock/başarıların tetiklendiğini de gösterir.
