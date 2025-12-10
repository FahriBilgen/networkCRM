# Fortress Director × Prison Labyrinth Escape Entegrasyon Spesi

Bu doküman, Fortress Director yapay zekâ motoru ile “Prison Labyrinth Escape” gerçek zamanlı kaçış oyunu arasında kurulacak entegrasyonun tek kaynağıdır. Decision tick temelli haberleşme sözleşmesini, world snapshot formatını, ActionList çıktı yapısını, güvenli fonksiyon (safe function) yüzeyini, doğrulama kurallarını ve hata durumlarında uygulanacak geri dönüş mekanizmalarını kapsar.

---

## 1. Amaç ve Kapsam

- AI Director oyun döngüsünde dramatik tempoyu, NPC davranışlarını, çevresel olayları ve anlatıyı yönetir; fizik, pathfinding, animasyon ve render katmanlarına doğrudan müdahale etmez.
- Realtime oyun, deterministik karar periyotlarına (decision tick) ayrılarak her **N = 3 saniyede** Fortress Director’a senkron world snapshot gönderir ve alınan ActionList çıktısını uygular.
- Veri alışverişi iki yönlüdür:
  - Oyun ⟶ Director: `/director/decide` endpoint’ine `WorldSnapshot` JSON.
  - Director ⟶ Oyun: Aynı isteğin HTTP 200 yanıtında `ActionList` JSON.
- Tüm taraflar bu dokümanı referans alarak API sözleşmelerini, doğrulama kriterlerini ve güvenlik kıstaslarını uygular.

---

## 2. Decision Tick Modeli

1. Oyun döngüsü snapshot üretir ve maksimum 25 ms içinde `/director/decide` çağrısını başlatır.
2. Fortress Director pipeline’ı sırasıyla `WorldModel → DirectorAgent → Planner → Executor` alt sistemlerinden geçerek karar üretir.
3. Çıktı olarak `action_list` alanı içinde sıralı operasyonlar gönderilir.
4. Oyun yanıtı aldıktan sonra maksimum 3 s içinde tüm aksiyonları uygular ve uygulama başarısını takip eden tick’te `recent_events` içine raporlar.

### 2.1 Decision Tick JSON Şemaları

**Request – `/director/decide`**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "WorldSnapshot",
  "type": "object",
  "required": [
    "tick_id",
    "timestamp_utc",
    "delta_mode",
    "player",
    "npcs",
    "map",
    "items",
    "global_state",
    "recent_events"
  ],
  "properties": {
    "tick_id": { "type": "integer", "minimum": 0 },
    "timestamp_utc": { "type": "string", "format": "date-time" },
    "delta_mode": { "type": "string", "enum": ["full", "incremental"] },
    "player": { "$ref": "#/$defs/player" },
    "npcs": {
      "type": "array",
      "items": { "$ref": "#/$defs/npc" },
      "maxItems": 32
    },
    "map": { "$ref": "#/$defs/map_state" },
    "items": {
      "type": "array",
      "items": { "$ref": "#/$defs/item" },
      "maxItems": 64
    },
    "global_state": { "$ref": "#/$defs/global_state" },
    "recent_events": {
      "type": "array",
      "items": { "$ref": "#/$defs/event" },
      "maxItems": 10
    },
    "removed_entities": { "$ref": "#/$defs/removed_entities" }
  },
  "$defs": {
    "vector2": {
      "type": "object",
      "required": ["x", "y"],
      "properties": {
        "x": { "type": "number" },
        "y": { "type": "number" }
      },
      "additionalProperties": false
    },
    "player": {
      "type": "object",
      "required": [
        "position",
        "state",
        "inventory",
        "noise_level",
        "visibility",
        "reputation",
        "health",
        "status_effects"
      ],
      "properties": {
        "position": { "$ref": "#/$defs/vector2" },
        "state": {
          "type": "string",
          "enum": ["running", "hiding", "talking", "injured", "captured"]
        },
        "inventory": {
          "type": "array",
          "items": { "type": "string" },
          "maxItems": 12
        },
        "noise_level": { "type": "number", "minimum": 0, "maximum": 1 },
        "visibility": { "type": "number", "minimum": 0, "maximum": 1 },
        "reputation": { "type": "number", "minimum": -1, "maximum": 1 },
        "health": { "type": "integer", "minimum": 0, "maximum": 100 },
        "status_effects": {
          "type": "array",
          "items": { "type": "string" },
          "maxItems": 8
        }
      },
      "additionalProperties": false
    },
    "npc": {
      "type": "object",
      "required": [
        "id",
        "type",
        "pos",
        "state",
        "awareness_level",
        "suspicion",
        "relationship_to_player"
      ],
      "properties": {
        "id": { "type": "string" },
        "type": {
          "type": "string",
          "enum": ["guard", "prisoner", "informant", "named_npc"]
        },
        "pos": { "$ref": "#/$defs/vector2" },
        "state": {
          "type": "string",
          "enum": [
            "patrol",
            "chase",
            "idle",
            "talk_wait",
            "talk_active",
            "incapacitated"
          ]
        },
        "awareness_level": { "type": "number", "minimum": 0, "maximum": 1 },
        "suspicion": { "type": "number", "minimum": 0, "maximum": 1 },
        "relationship_to_player": {
          "type": "string",
          "enum": ["hostile", "neutral", "ally", "uncertain"]
        },
        "goal": { "type": "string" },
        "hp": { "type": "integer", "minimum": 0, "maximum": 150 },
        "inventory": {
          "type": "array",
          "items": { "type": "string" },
          "maxItems": 6
        },
        "memory": {
          "type": "array",
          "items": { "type": "string" },
          "maxItems": 10
        }
      },
      "additionalProperties": false
    },
    "map_state": {
      "type": "object",
      "properties": {
        "floor_patch": { "$ref": "#/$defs/floor_patch" },
        "doors": {
          "type": "array",
          "items": { "$ref": "#/$defs/door" },
          "maxItems": 32
        },
        "moving_walls": {
          "type": "array",
          "items": { "$ref": "#/$defs/moving_wall" },
          "maxItems": 16
        },
        "traps": {
          "type": "array",
          "items": { "$ref": "#/$defs/trap" },
          "maxItems": 16
        },
        "lights": {
          "type": "array",
          "items": { "$ref": "#/$defs/light" },
          "maxItems": 32
        }
      },
      "additionalProperties": false
    },
    "floor_patch": {
      "type": "object",
      "required": ["anchor", "tiles"],
      "properties": {
        "anchor": { "$ref": "#/$defs/vector2" },
        "tiles": {
          "type": "array",
          "minItems": 1,
          "items": {
            "type": "array",
            "minItems": 1,
            "items": { "type": "string" }
          }
        }
      },
      "additionalProperties": false
    },
    "door": {
      "type": "object",
      "required": ["id", "pos", "locked", "open"],
      "properties": {
        "id": { "type": "string" },
        "pos": { "$ref": "#/$defs/vector2" },
        "locked": { "type": "boolean" },
        "open": { "type": "boolean" }
      },
      "additionalProperties": false
    },
    "moving_wall": {
      "type": "object",
      "required": ["id", "pos", "direction", "active"],
      "properties": {
        "id": { "type": "string" },
        "pos": { "$ref": "#/$defs/vector2" },
        "direction": {
          "type": "string",
          "enum": ["north", "south", "east", "west"]
        },
        "active": { "type": "boolean" }
      },
      "additionalProperties": false
    },
    "trap": {
      "type": "object",
      "required": ["id", "type", "active", "pos"],
      "properties": {
        "id": { "type": "string" },
        "type": { "type": "string" },
        "active": { "type": "boolean" },
        "pos": { "$ref": "#/$defs/vector2" }
      },
      "additionalProperties": false
    },
    "light": {
      "type": "object",
      "required": ["id", "intensity", "mode"],
      "properties": {
        "id": { "type": "string" },
        "intensity": { "type": "number", "minimum": 0, "maximum": 1 },
        "mode": {
          "type": "string",
          "enum": ["normal", "flicker", "alert"]
        }
      },
      "additionalProperties": false
    },
    "item": {
      "type": "object",
      "required": ["id", "item_type", "pos", "owner", "state"],
      "properties": {
        "id": { "type": "string" },
        "item_type": { "type": "string" },
        "pos": { "$ref": "#/$defs/vector2" },
        "owner": { "type": ["string", "null"] },
        "state": {
          "type": "string",
          "enum": ["intact", "broken", "used"]
        },
        "tags": {
          "type": "array",
          "items": { "type": "string" },
          "maxItems": 6
        }
      },
      "additionalProperties": false
    },
    "global_state": {
      "type": "object",
      "required": ["alarm_level", "security_mode", "time_elapsed"],
      "properties": {
        "alarm_level": { "type": "integer", "minimum": 0, "maximum": 3 },
        "security_mode": {
          "type": "string",
          "enum": ["normal", "heightened", "lockdown"]
        },
        "time_elapsed": { "type": "number", "minimum": 0 },
        "weather": { "type": "string" },
        "power_grid": { "type": "string" }
      },
      "additionalProperties": true
    },
    "event": {
      "oneOf": [
        { "type": "string" },
        {
          "type": "object",
          "required": ["type"],
          "properties": {
            "type": { "type": "string" },
            "payload": { "type": "object" }
          },
          "additionalProperties": false
        }
      ]
    },
    "removed_entities": {
      "type": "object",
      "properties": {
        "npcs": {
          "type": "array",
          "items": { "type": "string" },
          "maxItems": 32,
          "uniqueItems": true
        },
        "items": {
          "type": "array",
          "items": { "type": "string" },
          "maxItems": 32,
          "uniqueItems": true
        },
        "doors": {
          "type": "array",
          "items": { "type": "string" },
          "maxItems": 32,
          "uniqueItems": true
        },
        "moving_walls": {
          "type": "array",
          "items": { "type": "string" },
          "maxItems": 16,
          "uniqueItems": true
        },
        "traps": {
          "type": "array",
          "items": { "type": "string" },
          "maxItems": 16,
          "uniqueItems": true
        },
        "lights": {
          "type": "array",
          "items": { "type": "string" },
          "maxItems": 32,
          "uniqueItems": true
        }
      },
      "additionalProperties": false
    }
  }
}
```

`$defs` alanları oyuncu, NPC, harita, item ve global state yapılarının validasyonunu kesinleştirir; incremental snapshot yalnızca değişen nesneleri içerir ve gönderilmeyen alanlar Director tarafında son bilinen değerlerle doldurulur.

**Response – ActionList**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "ActionList",
  "type": "object",
  "required": ["tick_id", "action_list"],
  "properties": {
    "tick_id": { "type": "integer", "minimum": 0 },
    "latency_ms": { "type": "integer", "minimum": 0 },
    "action_list": {
      "type": "array",
      "items": { "$ref": "#/$defs/action" },
      "maxItems": 12
    }
  },
  "$defs": {
    "action": {
      "type": "object",
      "required": ["name", "kwargs"],
      "properties": {
        "name": {
          "type": "string",
          "enum": [
            "open_door",
            "close_door",
            "lock_door",
            "unlock_door",
            "shift_wall",
            "toggle_light",
            "set_light_mode",
            "set_light_intensity",
            "activate_trap",
            "deactivate_trap",
            "toggle_laser_grid",
            "raise_barrier",
            "lower_barrier",
            "rotate_gate",
            "set_moving_wall_pattern",
            "spawn_guard",
            "spawn_prisoner",
            "spawn_informant",
            "spawn_named_npc",
            "despawn_npc",
            "assign_patrol_route",
            "update_patrol_node",
            "set_guard_goal",
            "set_guard_alert_level",
            "npc_follow_player",
            "npc_hold_position",
            "npc_block_path",
            "npc_flee",
            "npc_seek_player",
            "npc_call_backup",
            "npc_drop_item",
            "npc_give_item",
            "npc_investigate_noise",
            "npc_say",
            "spawn_item",
            "destroy_item",
            "move_item",
            "assign_item_to_npc",
            "set_item_state",
            "highlight_item",
            "recharge_item",
            "drop_item_to_ground",
            "mark_item_interactive",
            "unlock_container",
            "play_alarm_sound",
            "stop_alarm_sound",
            "emit_dialogue",
            "set_scene_mood",
            "update_music_layer",
            "queue_objective",
            "complete_objective",
            "show_ui_hint"
          ]
        },
        "kwargs": { "type": "object", "additionalProperties": true },
        "priority": { "type": "integer", "minimum": 0, "maximum": 3 },
        "expires_in_ticks": { "type": "integer", "minimum": 1, "maximum": 4 }
      },
      "additionalProperties": false
    }
  }
}
```

---

## 3. World Snapshot Ayrıntıları (Oyun ⟶ AI Director)

### 3.1 Player

```json
"player": {
  "position": { "x": 12.4, "y": 8.0 },
  "state": "hiding",
  "inventory": ["lockpick", "smoke_bomb"],
  "noise_level": 0.32,
  "visibility": 0.45,
  "reputation": -0.2,
  "health": 74,
  "status_effects": ["silent_steps"]
}
```

- `state` enum: `running`, `hiding`, `talking`, `injured`, `captured`.
- `inventory` sıralı string listesi; maksimum 12 öğe.
- `noise_level` ve `visibility` 0‑1 arası normalize değerler.
- `reputation` −1 ile 1 arası; NPC davranışını belirler.

### 3.2 NPC Listesi

`npcs[]` öğeleri:

```json
{
  "id": "npc_guard_03",
  "type": "guard",
  "pos": { "x": 10.1, "y": 5.8 },
  "state": "patrol",
  "awareness_level": 0.3,
  "suspicion": 0.15,
  "relationship_to_player": "hostile",
  "goal": "patrol_sector_c",
  "hp": 100,
  "inventory": ["stun_baton"],
  "memory": ["heard_noise_c3"]
}
```

Type enum: `guard`, `prisoner`, `informant`, `named_npc`. `state` enum: `patrol`, `chase`, `idle`, `talk_wait`, `talk_active`, `incapacitated`. Awareness ve suspicion 0‑1 arası. `relationship_to_player` enum: `hostile`, `neutral`, `ally`, `uncertain`.

### 3.3 Map State

```json
"map": {
  "floor_patch": {
    "anchor": { "x": 8, "y": 6 },
    "tiles": [
      ["corridor", "corridor", "wall"],
      ["corridor", "trap", "wall"]
    ]
  },
  "doors": [
    { "id": "D12", "pos": { "x": 7, "y": 6 }, "locked": true, "open": false }
  ],
  "moving_walls": [
    { "id": "MW4", "pos": { "x": 11, "y": 3 }, "direction": "north", "active": false }
  ],
  "traps": [
    { "id": "T3", "type": "gas", "active": false, "pos": { "x": 9, "y": 4 } }
  ],
  "lights": [
    { "id": "L7", "intensity": 0.7, "mode": "normal" }
  ]
}
```

`tiles` alanı incremental patch (opsiyonel). `direction` enum: `north`, `south`, `east`, `west`. `lights[].mode`: `normal`, `flicker`, `alert`.

### 3.4 Items

```json
{
  "id": "item_keycard_B",
  "item_type": "keycard",
  "pos": { "x": 6, "y": 5 },
  "owner": null,
  "state": "intact",
  "tags": ["mission_critical"]
}
```

`state` enum: `intact`, `broken`, `used`. `owner` NPC veya `player`.

### 3.5 Global State

```json
"global_state": {
  "alarm_level": 1,
  "security_mode": "normal",
  "time_elapsed": 742.8,
  "weather": "storm",
  "power_grid": "stable"
}
```

- `alarm_level`: 0‑3 arasında tam sayı. 2 üzeri yüksek alarm.
- `security_mode` enum: `normal`, `heightened`, `lockdown`.
- `time_elapsed`: saniye.
- Opsiyonel bağlamsal alanlar (hava, enerji) incremental snapshot’ta atlanabilir.

### 3.6 Snapshot Kuralları

- Snapshot incremental modda varsayılan olarak **yalnızca değişen** oyuncu/NPC/item/map elemanlarını taşır. `delta_mode = "full"` olduğunda tüm alanlar gönderilir.
- Oyun aynı tick’te bir varlığı birden fazla kez güncelleyemez; RFC3339 timestamp monotondur.
- Gönderilmeyen nesneler Director tarafında cache’de tutulur; 5 tick boyunca gelmeyen nesneler `recent_events` aracılığıyla “expired” bildirimi alır.
- Snapshot boyutu 32 KB üstüne çıktığında oyun, NPC listesini yakınlık önceliğiyle kırpar.

### 3.7 State / Delta Yapıları

- Incremental snapshot gönderirken oyun, `removed_entities.{npcs|items|doors|...}` alanlarıyla artık sahnede bulunmayan nesneleri bildirir. Bu alanlar yalnızca delta modunda gönderilir ve benzersiz kimlik listelerinden oluşur.
- NPC, item veya map kayıtları yalnızca değiştiğinde gönderilir; değişmeyen kayıtlar atlanır. Bir kayıt önce `removed_entities` içinde bildirildikten sonra tekrar gönderilirse Director onu yeni bir varlık olarak kabul eder.
- Harita yaması (`map.floor_patch`) tile bazında **ekle-güncelle** semantiğine sahiptir; silinen karo eşleşmeleri `map.floor_patch.tiles` içindeki `"void"` değeriyle temsil edilir.
- Delta tutarlılığı için oyun tarafı, her snapshot’ta `tick_id`’yi artırır ve `recent_events` dizisine `ack_action:<action_id>` kalıplı girdiler ekleyerek önceki action uygulama durumunu raporlar.
- Aşağıdaki örnek incremental snapshot, bir NPC güncellemesi, bir item kaldırma talebi ve bir kapı silme bildirimini aynı tick’te taşır:

```json
{
  "tick_id": 205,
  "timestamp_utc": "2024-05-05T14:15:37Z",
  "delta_mode": "incremental",
  "npcs": [
    { "id": "guard_bravo", "type": "guard", "pos": { "x": 14, "y": 9 }, "state": "chase", "awareness_level": 0.7, "suspicion": 0.8, "relationship_to_player": "hostile" }
  ],
  "items": [],
  "map": {
    "doors": [
      { "id": "D17", "pos": { "x": 9, "y": 10 }, "locked": true, "open": false }
    ]
  },
  "removed_entities": {
    "items": ["item_keycard_B"],
    "doors": ["D05"]
  },
  "recent_events": ["ack_action:lock_door#D17", "player_triggered_alarm"]
}
```

### 3.8 `recent_events` Tipleri ve ACK Protokolü

`recent_events[]` dizisi, Director’a gönderilen son 10 önemli olayı içerir; olaylar ya sade string ya da `{type, payload}` nesneleridir. Desteklenen kalıplar:

- `player_event:<event_tag>` – Oyuncu davranışları (`player_entered_sector_c`, `player_used_item#lockpick`).
- `system_event:<tag>` – Motor seviyesindeki olaylar (`network_timeout`, `snapshot_full_resend`).
- `ack_action:<action_id>` – Bir AI aksiyonunun başarıyla uygulandığını belirtir.
- `action_error:<action_id>:<error_code>` – Hata kodları: `invalid_target`, `cooldown_active`, `blocked_by_player`, `line_of_sight_blocked`, `state_conflict`.
- `action_expired:<action_id>` – `expires_in_ticks` süresi dolduğu için uygulanmayan aksiyon.
- `director_error:<reason>` – Director yanıtı parse/validate edilemediğinde.
- `validator_reject:<rule_id>` – Bölüm 7’deki kurallardan hangisinin ihlal edildiğini belirtir.
- `{ "type": "cinematic_event", "payload": { "id": "cutscene_intro", "duration": 5.0 } }` gibi nesne tabanlı bildirimler.

Örnek event dizisi:

```json
"recent_events": [
  "player_event:entered_hub",
  "ack_action:182#0",
  "action_error:182#1:line_of_sight_blocked",
  "validator_reject:softlock_guardrail",
  { "type": "cinematic_event", "payload": { "id": "flashback_a", "duration": 3.2 } }
]
```

---

## 4. AI Output Format (ActionList) – AI Director ⟶ Oyun

ActionList, uygulanabilir güvenli fonksiyon çağrılarının sıralı listesidir. Her aksiyon:

```json
{
  "name": "open_door",
  "kwargs": { "door_id": "D12" },
  "priority": 2,
  "expires_in_ticks": 2
}
```

### 4.1 Map Ops

| İşlev | Parametreler | Açıklama |
| --- | --- | --- |
| `open_door` | `door_id` | Kapıyı açar, kilitliyi otomatik çözmez. |
| `close_door` | `door_id` | Kapıyı kapatır, oyuncu üzerine kapanmaz. |
| `lock_door` | `door_id`, `lock_level` | Kilitleme seviyesi 0‑3. |
| `unlock_door` | `door_id` | Kilidi kaldırır. |
| `shift_wall` | `segment_id`, `pattern` | Hareketli duvar sekansını değiştirir. |
| `activate_trap` | `trap_id`, `intensity` | Tetikleme gücü 0‑1. |
| `deactivate_trap` | `trap_id` | Tuzağı devre dışı bırakır. |
| `set_light_mode` | `light_id`, `mode`, `intensity` | `mode`: normal/flicker/alert. |

### 4.2 NPC Ops

- `spawn_guard(npc_template, pos, loadout)`
- `spawn_prisoner(npc_template, pos)`
- `spawn_informant(template_id, pos, entry_dialogue)`
- `despawn_npc(npc_id)`
- `assign_patrol_route(npc_id, route_id)`
- `set_guard_goal(npc_id, goal_tag)`
- `set_guard_alert_level(npc_id, level)`
- `npc_follow_player(npc_id, distance)`
- `npc_block_path(npc_id, doorway_id)`
- `npc_flee(npc_id, waypoint_id)`
- `npc_call_backup(npc_id, sector)`
- `npc_say(npc_id, line_id)`

### 4.3 Item Ops

- `spawn_item(item_template, pos)`
- `move_item(item_id, pos)`
- `assign_item_to_npc(item_id, npc_id)`
- `destroy_item(item_id)`
- `set_item_state(item_id, state)`
- `highlight_item(item_id, duration)`

### 4.4 Dialog / Narrative Ops

- `emit_dialogue(channel, payload)`
- `play_alarm_sound(preset)`
- `stop_alarm_sound()`
- `set_scene_mood(mood, weight)`
- `queue_objective(objective_id)`

Her aksiyon `SAFE FUNCTIONS` kümesinden seçilmelidir (Bölüm 6). Aynı tick içinde çelişen aksiyonlar (örn. aynı kapıya `lock_door` ve `unlock_door`) validator tarafından reddedilir.

### 4.5 Action Uygulama & Geri Bildirim Sözleşmesi

- Fortress Director her aksiyon için zımni bir `action_id = "<tick_id>#<index>"` kuralı kullanır. Oyun uygulama sırasını ActionList sırasıyla aynı tutar.
- `priority` alanı yalnızca validator tarafından aynı hedefe yönelik çakışmaların çözülmesinde kullanılır; oyun uygularken ActionList sırasını bozmaz.
- `expires_in_ticks` süresi dolmuş aksiyonlar uygulanmaz; oyun, `recent_events` dizisine `action_expired:<action_id>` kaydı düşer.
- Oyun, uygulanan her aksiyon için `recent_events` içinde `ack_action:<action_id>` bildirimi gönderir. Başarısız denemelerde `action_error:<action_id>:<error_code>` formatı kullanılır (`invalid_target`, `cooldown_active`, `line_of_sight_blocked` vb.).
- Director, bir aksiyon iki tick üst üste `action_error` dönerse aynı hedef için otomatik geri çekme logic’i uygular ve buna dair fallback planı Section 8’deki kurallara göre devreye sokar.

---

## 5. AI Internal State & Projection Rules

- Fortress Director LLM katmanı tam oyun durumunu görmez; snapshot’tan yalnızca:
  - Oyuncu çevresindeki 5 × 5 karo patch’i,
  - Oyuncuya en yakın 6 NPC,
  - Son 3 `recent_events`,
  - Global `alarm_level` ve `security_mode`,
  - Oyuncu sağlık/reputation değerleri,
  - Hedef odaklı aktif görevler.
- WorldModel eksik alanları doğrusal projeksiyonlarla tahmin eder (örneğin devriye noktalarını son 4 konum vektörüyle tahmini).
- Projection kuralları:
  1. Hareketli NPC’ler için maksimum hız 2 karo/sn varsayılır.
  2. Alarm seviyesi iki tick arka arkaya değişmediyse sabit kabul edilir.
  3. Oyuncunun görülme ihtimali 2 tick üst üste 0.8’in üstündeyse LLM `high_visibility` etiketi kazanır.
- Ek bellekler (session memory) 30 tick’ten sonra temizlenir; named NPC’ler için hatırlatıcı etiketler saklanır (`favor_debt`, `betrayal_flag` vb.).

---

## 6. Safe Function Listesi (Hapishane Versiyonu)

Fortress Director yalnızca aşağıdaki fonksiyonları çağırabilir. Toplam 52 fonksiyon, kategori bazında listelenmiştir.

**Map Functions**

| # | Fonksiyon | Zorunlu `kwargs` | Kurallar |
| --- | --- | --- | --- |
| 1 | `open_door` | `door_id` | Kapı kilitliyse önce `unlock_door` çağrısı gerekir. |
| 2 | `close_door` | `door_id` | Oyuncu veya dost NPC kapı aralığındaysa reddedilir. |
| 3 | `lock_door` | `door_id`, `lock_level` (0‑3) | Yalnızca kapı kapalıyken uygulanır. |
| 4 | `unlock_door` | `door_id` | Elektronik kilitler için güvenlik modu ≥ 2 ise reddedilir. |
| 5 | `shift_wall` | `segment_id`, `pattern` | `pattern` değerleri `A/B/C`; 2 saniyede bir çağrılabilir. |
| 6 | `toggle_light` | `light_id` | Modu `normal ↔ alert` arasında değiştirir. |
| 7 | `set_light_mode` | `light_id`, `mode`, (ops.) `intensity` | `mode`: `normal`, `flicker`, `alert`. |
| 8 | `set_light_intensity` | `light_id`, `intensity` (0‑1) | Işık yoğunluğu 0.1’den düşük olamaz. |
| 9 | `activate_trap` | `trap_id`, (ops.) `intensity` | Gaz tuzaklarında `intensity` 0.8 üstü yasak. |
| 10 | `deactivate_trap` | `trap_id` | Aktif olmayan tuzaklarda no-op kabul edilir. |
| 11 | `toggle_laser_grid` | `grid_id` | 30 sn cooldown; alarm seviyesi 3’te otomatik kilitlenir. |
| 12 | `raise_barrier` | `barrier_id` | Bariyer hattında oyuncu varsa uygulanmaz. |
| 13 | `lower_barrier` | `barrier_id` | Enerji kesintisi varsa otomatik reddedilir. |
| 14 | `rotate_gate` | `gate_id`, `orientation` (N/E/S/W) | Yalnızca hareketli kapı segmentlerinde geçerlidir. |
| 15 | `set_moving_wall_pattern` | `wall_id`, `pattern_id` | Pattern `linear`, `pulse`, `loop`. |

**NPC Functions**

| # | Fonksiyon | Zorunlu `kwargs` | Kurallar |
| --- | --- | --- | --- |
| 16 | `spawn_guard` | `npc_template`, `pos`, `loadout` | Aktif guard sayısı 8’i aşamaz. |
| 17 | `spawn_prisoner` | `npc_template`, `pos` | Duvar içi koordinatlar reddedilir. |
| 18 | `spawn_informant` | `template_id`, `pos`, `entry_dialogue` | Aynı anda en fazla 2 informant. |
| 19 | `spawn_named_npc` | `name_id`, `pos`, `script_tag` | Unique `name_id` zorunlu. |
| 20 | `despawn_npc` | `npc_id` | Spawn’dan ≤ 1 tick sonra çalıştırılamaz. |
| 21 | `assign_patrol_route` | `npc_id`, `route_id` | Route map sınırları içinde olmalı. |
| 22 | `update_patrol_node` | `npc_id`, `index`, `waypoint` | `index` mevcut rota uzunluğunu aşamaz. |
| 23 | `set_guard_goal` | `npc_id`, `goal_tag` | `goal_tag`: `patrol`, `investigate`, `capture`. |
| 24 | `set_guard_alert_level` | `npc_id`, `level` (0‑3) | Level artışı tick başına +1 ile sınırlı. |
| 25 | `npc_follow_player` | `npc_id`, `distance` | `distance` 2‑6 karo arası. |
| 26 | `npc_hold_position` | `npc_id`, `pos` | Pozisyon line-of-sight dâhilinde olmalı. |
| 27 | `npc_block_path` | `npc_id`, `doorway_id` | Aynı kapıya 2 bloklayıcı atanamaz. |
| 28 | `npc_flee` | `npc_id`, `waypoint_id` | Guard tipi NPC’ler için yasak. |
| 29 | `npc_seek_player` | `npc_id`, `search_radius` | Radius max 8 karo. |
| 30 | `npc_call_backup` | `npc_id`, `sector` | Sektörde aktif guard yoksa spawn izni tetikler. |
| 31 | `npc_drop_item` | `npc_id`, `item_id` | Item NPC envanterinde olmalı. |
| 32 | `npc_give_item` | `from_npc_id`, `to_npc_id`, `item_id` | İki NPC birbirine 3 karo yakın olmalı. |
| 33 | `npc_investigate_noise` | `npc_id`, `pos` | Noise kaynağı 6 karm içinde olmalı. |
| 34 | `npc_say` | `npc_id`, `line_id` | `line_id` narrative sisteminde kayıtlı olmalı. |

**Item Functions**

| # | Fonksiyon | Zorunlu `kwargs` | Kurallar |
| --- | --- | --- | --- |
| 35 | `spawn_item` | `item_template`, `pos` | Aynı karede en fazla 2 item. |
| 36 | `destroy_item` | `item_id` | Görev kritik item’lar (tag `mission_critical`) yasak. |
| 37 | `move_item` | `item_id`, `pos` | Teleport yerine anlık taşıma; 5 karo sınırı. |
| 38 | `assign_item_to_npc` | `item_id`, `npc_id` | NPC envanter limiti 4. |
| 39 | `set_item_state` | `item_id`, `state` | `state`: `intact`, `broken`, `used`. |
| 40 | `highlight_item` | `item_id`, `duration` | Duration 1‑3 tick. |
| 41 | `recharge_item` | `item_id`, `amount` | Shock cihazları `<amount ≤ 50>` gerektirir. |
| 42 | `drop_item_to_ground` | `item_id`, `pos` | Pozisyon NPC yakınında olmalı. |
| 43 | `mark_item_interactive` | `item_id`, `hint_text` | UI hint otomatik tetiklenir. |
| 44 | `unlock_container` | `container_id`, `method` | `method`: `keycard`, `override`, `puzzle`. |

**Narrative / System Functions**

| # | Fonksiyon | Zorunlu `kwargs` | Kurallar |
| --- | --- | --- | --- |
| 45 | `play_alarm_sound` | `preset` | `preset`: `yellow_alert`, `red_alert`, `lockdown`. |
| 46 | `stop_alarm_sound` | (none) | Yalnızca aktif alarm varsa çalışır. |
| 47 | `emit_dialogue` | `channel`, `payload` | `channel`: `radio`, `pa`, `proximity`. |
| 48 | `set_scene_mood` | `mood`, `weight` | `mood`: `tense`, `hopeful`, `ominous`. |
| 49 | `update_music_layer` | `layer_id`, `state` | `state`: `mute`, `fade_in`, `full`. |
| 50 | `queue_objective` | `objective_id` | Aynı ID tekrarlandığında stacklenmez. |
| 51 | `complete_objective` | `objective_id` | Objective aktif değilse no-op. |
| 52 | `show_ui_hint` | `hint_id`, `duration` | Duration 1‑5 saniye; tekrarlarda cooldown 10s. |

Her fonksiyon çağrısı aynı şemayı izler:

```json
{
  "name": "open_door",
  "kwargs": {
    "door_id": "D12"
  }
}
```

### 6.2 Kwargs Şema Referansı

ActionList üreticileri ve validator tarafı için, bütün safe fonksiyonların parametre tipleri aşağıdaki JSON sözlüğüyle tanımlanır:

```json
{
  "open_door": { "required": ["door_id"], "properties": { "door_id": "string" } },
  "close_door": { "required": ["door_id"], "properties": { "door_id": "string" } },
  "lock_door": { "required": ["door_id", "lock_level"], "properties": { "door_id": "string", "lock_level": "integer" } },
  "unlock_door": { "required": ["door_id"], "properties": { "door_id": "string" } },
  "shift_wall": { "required": ["segment_id", "pattern"], "properties": { "segment_id": "string", "pattern": "string" } },
  "toggle_light": { "required": ["light_id"], "properties": { "light_id": "string" } },
  "set_light_mode": { "required": ["light_id", "mode"], "properties": { "light_id": "string", "mode": "string", "intensity": "number" } },
  "set_light_intensity": { "required": ["light_id", "intensity"], "properties": { "light_id": "string", "intensity": "number" } },
  "activate_trap": { "required": ["trap_id"], "properties": { "trap_id": "string", "intensity": "number" } },
  "deactivate_trap": { "required": ["trap_id"], "properties": { "trap_id": "string" } },
  "toggle_laser_grid": { "required": ["grid_id"], "properties": { "grid_id": "string" } },
  "raise_barrier": { "required": ["barrier_id"], "properties": { "barrier_id": "string" } },
  "lower_barrier": { "required": ["barrier_id"], "properties": { "barrier_id": "string" } },
  "rotate_gate": { "required": ["gate_id", "orientation"], "properties": { "gate_id": "string", "orientation": "string" } },
  "set_moving_wall_pattern": { "required": ["wall_id", "pattern_id"], "properties": { "wall_id": "string", "pattern_id": "string" } },
  "spawn_guard": { "required": ["npc_template", "pos", "loadout"], "properties": { "npc_template": "string", "pos": "vector2", "loadout": "object" } },
  "spawn_prisoner": { "required": ["npc_template", "pos"], "properties": { "npc_template": "string", "pos": "vector2" } },
  "spawn_informant": { "required": ["template_id", "pos", "entry_dialogue"], "properties": { "template_id": "string", "pos": "vector2", "entry_dialogue": "string" } },
  "spawn_named_npc": { "required": ["name_id", "pos", "script_tag"], "properties": { "name_id": "string", "pos": "vector2", "script_tag": "string" } },
  "despawn_npc": { "required": ["npc_id"], "properties": { "npc_id": "string" } },
  "assign_patrol_route": { "required": ["npc_id", "route_id"], "properties": { "npc_id": "string", "route_id": "string" } },
  "update_patrol_node": { "required": ["npc_id", "index", "waypoint"], "properties": { "npc_id": "string", "index": "integer", "waypoint": "vector2" } },
  "set_guard_goal": { "required": ["npc_id", "goal_tag"], "properties": { "npc_id": "string", "goal_tag": "string" } },
  "set_guard_alert_level": { "required": ["npc_id", "level"], "properties": { "npc_id": "string", "level": "integer" } },
  "npc_follow_player": { "required": ["npc_id", "distance"], "properties": { "npc_id": "string", "distance": "number" } },
  "npc_hold_position": { "required": ["npc_id", "pos"], "properties": { "npc_id": "string", "pos": "vector2" } },
  "npc_block_path": { "required": ["npc_id", "doorway_id"], "properties": { "npc_id": "string", "doorway_id": "string" } },
  "npc_flee": { "required": ["npc_id", "waypoint_id"], "properties": { "npc_id": "string", "waypoint_id": "string" } },
  "npc_seek_player": { "required": ["npc_id", "search_radius"], "properties": { "npc_id": "string", "search_radius": "number" } },
  "npc_call_backup": { "required": ["npc_id", "sector"], "properties": { "npc_id": "string", "sector": "string" } },
  "npc_drop_item": { "required": ["npc_id", "item_id"], "properties": { "npc_id": "string", "item_id": "string" } },
  "npc_give_item": { "required": ["from_npc_id", "to_npc_id", "item_id"], "properties": { "from_npc_id": "string", "to_npc_id": "string", "item_id": "string" } },
  "npc_investigate_noise": { "required": ["npc_id", "pos"], "properties": { "npc_id": "string", "pos": "vector2" } },
  "npc_say": { "required": ["npc_id", "line_id"], "properties": { "npc_id": "string", "line_id": "string" } },
  "spawn_item": { "required": ["item_template", "pos"], "properties": { "item_template": "string", "pos": "vector2" } },
  "destroy_item": { "required": ["item_id"], "properties": { "item_id": "string" } },
  "move_item": { "required": ["item_id", "pos"], "properties": { "item_id": "string", "pos": "vector2" } },
  "assign_item_to_npc": { "required": ["item_id", "npc_id"], "properties": { "item_id": "string", "npc_id": "string" } },
  "set_item_state": { "required": ["item_id", "state"], "properties": { "item_id": "string", "state": "string" } },
  "highlight_item": { "required": ["item_id", "duration"], "properties": { "item_id": "string", "duration": "integer" } },
  "recharge_item": { "required": ["item_id", "amount"], "properties": { "item_id": "string", "amount": "integer" } },
  "drop_item_to_ground": { "required": ["item_id", "pos"], "properties": { "item_id": "string", "pos": "vector2" } },
  "mark_item_interactive": { "required": ["item_id", "hint_text"], "properties": { "item_id": "string", "hint_text": "string" } },
  "unlock_container": { "required": ["container_id", "method"], "properties": { "container_id": "string", "method": "string" } },
  "play_alarm_sound": { "required": ["preset"], "properties": { "preset": "string" } },
  "stop_alarm_sound": { "required": [], "properties": {} },
  "emit_dialogue": { "required": ["channel", "payload"], "properties": { "channel": "string", "payload": "object" } },
  "set_scene_mood": { "required": ["mood", "weight"], "properties": { "mood": "string", "weight": "number" } },
  "update_music_layer": { "required": ["layer_id", "state"], "properties": { "layer_id": "string", "state": "string" } },
  "queue_objective": { "required": ["objective_id"], "properties": { "objective_id": "string" } },
  "complete_objective": { "required": ["objective_id"], "properties": { "objective_id": "string" } },
  "show_ui_hint": { "required": ["hint_id", "duration"], "properties": { "hint_id": "string", "duration": "number" } }
}
```

Buradaki `"vector2"` ifadesi `{ "x": "number", "y": "number" }`, `"object"` serbest sözlükler ve `"number"/"integer"/"string"` temel tipleri temsil eder. Validator tarafı, ActionList içindeki her aksiyonun `kwargs` alanını bu sözlükle eşleştirerek tip güvenliğini sağlar.

`kwargs` içindeki alanlar fonksiyon tanımında belirtilen tiplerle birebir uyuşmalıdır; ek alanlar reddedilir.

---

## 7. Validation Rules

### 7.1 Softlock Prevention

- En az bir kaçış rotası (oyuncudan çıkış kapısına giden yol) açık kabul edilmelidir; validator, tüm `open_door`/`close_door` kombinasyonlarını path-finding ile doğrular.
- Oyuncu ile herhangi bir save point arasındaki yol süresiz bloklanamaz; bariyer ve duvar operasyonları 2 tick’ten uzun süreli kapanma yaratırsa aksiyon iptal edilir.

### 7.2 NPC Sanity Rules

- NPC aynı tick’te iki farklı hedef alamaz; `assign_patrol_route` ve `set_guard_goal` aynı NPC için eşzamanlı gelirse en yüksek öncelikli olan uygulanır, diğeri reddedilir.
- Devriye rotaları map sınırları dışına taşınamaz; route kayıtları loader’da doğrulanır.
- Spawn edilen NPC en az 1 saniye (≥ 1 tick) aktif kalmalıdır; aksi halde `despawn_npc` komutu geciktirilir.
- Maksimum aktif NPC limitleri: Guard ≤ 8, Prisoner ≤ 12, Named NPC ≤ 4.

### 7.3 Pacing Rules

- Arka arkaya iki tick’te toplam map aksiyonu sayısı 3’ü geçemez (ör. 3 kapı değişimi + 1 duvar kayması yasak).
- Alarm seviyesi yalnızca kademeli yükselir: 0→1→2→3 veya ters yönde. 0’dan 3’e tek tick’te sıçrama validator tarafından bloke edilir.
- Aynı objeye ait `lock_door` ve `unlock_door` çağrıları aynı listede bulunamaz.

### 7.4 Constraint Matrisi

| Kategori | Constraint | Validasyon / Remark |
| --- | --- | --- |
| Map erişimi | Aynı tick’te 3’ten fazla kapı/duvar değişikliği yapılamaz | Validator `map_ops_per_tick` sayaçlarıyla sınırlar |
| Kapı kilitleme | `lock_level` yalnızca kapı kapalıyken ayarlanabilir | Oyun, açık kapıda gelen komutu `action_error` olarak bildirir |
| Hareketli duvarlar | Pattern değişimi 2 saniyede bir olabilir | Snapshot `recent_events` içinde `action_error:cooldown_active` dönebilir |
| NPC spawn | Guard ≤ 8, Prisoner ≤ 12, Named ≤ 4 | Director spawn öncesi aktif sayaçları kontrol eder |
| NPC hedefleri | Aynı NPC aynı tick’te iki hedef alamaz | Scheduler `npc_goal_mutex` ile çakışan aksiyonları reddeder |
| Item ekonomisi | Görev kritik (`mission_critical`) item yok edilemez | `destroy_item` yasaklı ID’lerde validator bloklar |
| Alarm | 0‑3 arasında tek adımlık geçiş | `action_error:*:alarm_step_violation` döndürülür |
| Delta boyutu | Snapshot 32 KB’ı aşarsa NPC listesi kırpılır | Oyun log’una `snapshot_trimmed` event’i düşer |
| ACK zorunluluğu | Alınan aksiyonların 2 tick içinde `ack_action` veya `action_error` alması gerekir | Director, 2 tick boyunca geri bildirim yoksa aksiyonu tekrar kuyruğa koymaz |
| Softlock | En az bir kaçış rotası açık olmalı | Path validator her kapı/duvar kombinasyonunu A* ile test eder |

---

## 8. Failure Modes & Fallbacks

- **Bozuk JSON**: Fortress Director yanıtı parse edilemezse oyun tick’i `no-op` sayar, `recent_events` içine `director_error` yazar ve bir sonraki tick’te `fallback_plan_id` ile deterministic devriye planına döner.
- **Plan Validator Hatası**: Aksiyonlardan biri constraint’i ihlal ederse tüm ActionList reddedilir, oyun `validator_reject` event’i gönderir ve AI Director’a son geçerli snapshot tekrar yollanır.
- **Eksik Snapshot**: Oyun yeterli veri gönderemezse endpoint HTTP 400 döner; oyun `safe no-op tick` uygular (tüm aksiyonlar boş), bir sonraki tick’te `delta_mode = "full"` zorunlu olur.
- **Zaman Aşımı**: Director 200 ms içinde yanıt vermezse oyun fallback devriye senaryosu çalıştırır ve NETWORK log’una `timeout` yazar.

---

## 9. Örnek Tick Input / Output

### 9.1 Normal Tick – Devriye Güncellemesi & Item Spawn

**Input (`WorldSnapshot`)**

```json
{
  "tick_id": 128,
  "timestamp_utc": "2024-05-05T14:03:21Z",
  "delta_mode": "incremental",
  "player": {
    "position": { "x": 6.2, "y": 4.9 },
    "state": "hiding",
    "inventory": ["lockpick"],
    "noise_level": 0.18,
    "visibility": 0.22,
    "reputation": -0.1,
    "health": 82,
    "status_effects": []
  },
  "npcs": [
    {
      "id": "guard_A",
      "type": "guard",
      "pos": { "x": 9.0, "y": 4.0 },
      "state": "patrol",
      "awareness_level": 0.25,
      "suspicion": 0.05,
      "relationship_to_player": "hostile",
      "goal": "patrol_east",
      "hp": 100,
      "inventory": ["stun_baton"],
      "memory": []
    }
  ],
  "map": {
    "doors": [{ "id": "D5", "pos": { "x": 7, "y": 4 }, "locked": false, "open": true }],
    "lights": [{ "id": "L2", "intensity": 0.6, "mode": "normal" }]
  },
  "items": [],
  "global_state": {
    "alarm_level": 0,
    "security_mode": "normal",
    "time_elapsed": 485.0
  },
  "recent_events": ["player_entered_sector_c"]
}
```

**Output (`ActionList`)**

```json
{
  "tick_id": 128,
  "latency_ms": 42,
  "action_list": [
    {
      "name": "assign_patrol_route",
      "kwargs": { "npc_id": "guard_A", "route_id": "sector_c_loop" },
      "priority": 1,
      "expires_in_ticks": 2
    },
    {
      "name": "spawn_item",
      "kwargs": { "item_template": "smoke_bomb", "pos": { "x": 5, "y": 6 } },
      "priority": 0,
      "expires_in_ticks": 1
    }
  ]
}
```

### 9.2 High Alert Tick – Alarm Artışı & Kapı Kilitleme

**Input**

```json
{
  "tick_id": 182,
  "timestamp_utc": "2024-05-05T14:11:39Z",
  "delta_mode": "incremental",
  "player": {
    "position": { "x": 12.0, "y": 8.0 },
    "state": "running",
    "inventory": ["keycard_B"],
    "noise_level": 0.82,
    "visibility": 0.78,
    "reputation": -0.4,
    "health": 65,
    "status_effects": ["bleeding"]
  },
  "npcs": [
    {
      "id": "guard_alpha",
      "type": "guard",
      "pos": { "x": 13.0, "y": 8.2 },
      "state": "chase",
      "awareness_level": 0.9,
      "suspicion": 0.95,
      "relationship_to_player": "hostile",
      "goal": "capture_player",
      "hp": 100,
      "inventory": ["rifle"],
      "memory": ["saw_player_in_sector_d"]
    },
    {
      "id": "informant_beth",
      "type": "informant",
      "pos": { "x": 10.5, "y": 7.0 },
      "state": "talk_wait",
      "awareness_level": 0.4,
      "suspicion": 0.2,
      "relationship_to_player": "ally",
      "goal": "escort_player",
      "hp": 80,
      "inventory": [],
      "memory": []
    }
  ],
  "map": {
    "doors": [
      { "id": "D12", "pos": { "x": 11, "y": 8 }, "locked": false, "open": true },
      { "id": "D13", "pos": { "x": 12, "y": 9 }, "locked": false, "open": true }
    ],
    "lights": [{ "id": "L6", "intensity": 0.9, "mode": "alert" }]
  },
  "items": [],
  "global_state": {
    "alarm_level": 2,
    "security_mode": "heightened",
    "time_elapsed": 655.0
  },
  "recent_events": ["guard_alpha_saw_player", "player_triggered_trap"]
}
```

**Output**

```json
{
  "tick_id": 182,
  "latency_ms": 55,
  "action_list": [
    {
      "name": "lock_door",
      "kwargs": { "door_id": "D12", "lock_level": 2 },
      "priority": 2,
      "expires_in_ticks": 1
    },
    {
      "name": "set_guard_alert_level",
      "kwargs": { "npc_id": "guard_alpha", "level": 3 },
      "priority": 3,
      "expires_in_ticks": 1
    },
    {
      "name": "play_alarm_sound",
      "kwargs": { "preset": "red_alert_loop" },
      "priority": 1,
      "expires_in_ticks": 2
    },
    {
      "name": "queue_objective",
      "kwargs": { "objective_id": "reach_service_tunnel" },
      "priority": 0,
      "expires_in_ticks": 3
    }
  ]
}
```

---

## 10. Finalization

- Bu spesifikasyon, Fortress Director ile Prison Labyrinth Escape entegrasyonunun tek doğruluk kaynağıdır; değişiklik talepleri sürüm kontrollü olarak bu doküman üzerinden işlenir.
- Engine ekibi (runtime, networking, validator) ve oyun tasarım ekibi (narrative, level design, AI scripting) aynı referans dokümanı paylaşır; release öncesi checklist bütün bölümlerin uygulanıp uygulanmadığını doğrular.
- Karar tick sözleşmesi, snapshot alan adları, safe function listesi veya doğrulama kurallarındaki sapmalar prodüksiyon ortamında desteklenmez; yeni revizyonlar `spec_version` alanıyla versiyonlanmalıdır.

--- 
