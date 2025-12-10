# Safe Function Catalog

Bu katalog, Fortress Director güvenli fonksiyon motorunda tanımlanan 7 kategorideki 65+ fonksiyonun tamamını ve temel parametrelerini özetler. Her fonksiyon `demo_spec` tabanlı oyun durumunu deterministik şekilde değiştirir; gaz maliyetleri registry içindeki `gas_cost` alanlarından gelir.

## Combat
- `apply_combat_pressure(intensity:int)` — tehdit ↑, moral ↓ (Gas 3)
- `reduce_threat(amount:int)` — tehdit skorunu düşürür (Gas 2)
- `ranged_attack(target_area:str, intensity:int)` — menzilli baskı uygular (Gas 3)
- `melee_engagement(attacker_ids:list[npc_id], defender_ids:list[npc_id], structure_id:structure_id?)` — yakın dövüş başlatır (Gas 3)
- `suppressive_fire(sector:str, duration:int)` — baskı ateşi atar (Gas 2)
- `scout_enemy_positions(npc_id:npc_id, direction:str)` — keşif yapar (Gas 2)
- `fortify_combat_zone(zone:str, armor_boost:int)` — savaş hattını güçlendirir (Gas 4)
- `deploy_archers(x:int, y:int, volleys:int?)` — okçuları konumlandırır (Gas 3)
- `set_ambush(npc_id:npc_id, x:int, y:int)` — pusu kurar (Gas 4)
- `counter_attack(force:str, focus:str)` — karşı saldırı (Gas 4)

## Structure
- `reinforce_wall(structure_id:str, amount:int, material:str?)` — sur bütünlüğünü artırır (Gas 3)
- `repair_gate(gate_id:str, amount:int)` — kapı onarır (Gas 3)
- `patch_wall_section(section_id:str, amount:int)` — hızlı yama (Gas 2)
- `strengthen_tower(tower_id:str, amount:int)` — kule güçlendirmesi (Gas 3)
- `extinguish_fire(structure_id:str, intensity:int)` — yangın söndürür, moral kazanır (Gas 2)
- `build_barricade(location:str, materials:int)` — bariyer kurar (Gas 3)
- `reinforce_trench(trench_id:str, amount:int)` — siper güçlendirir (Gas 2)
- `deploy_defense_net(section_id:str, coverage:int)` — tırmanma önler (Gas 2)
- `clear_rubble(section_id:str, effort:int)` — moloz temizliği (Gas 2)
- `inspect_wall(section_id:str)` — hasarı raporlar (Gas 1)

## NPC
- `move_npc(npc_id:npc_id, x:int, y:int, room:str?)` — NPC taşır (Gas 2)
- `assign_role(npc_id:npc_id, role:str)` — rol değiştirir (Gas 2)
- `heal_npc(npc_id:npc_id, amount:int)` — moral/sağlık iyileştirir (Gas 2)
- `rest_npc(npc_id:npc_id, duration:int)` — dinlenme moduna alır (Gas 1)
- `increase_npc_focus(npc_id:npc_id, amount:int)` — fokus yükseltir (Gas 2)
- `reduce_npc_focus(npc_id:npc_id, amount:int)` — fokus azaltır (Gas 2)
- `give_equipment(npc_id:npc_id, item:str)` — ekipman verir (Gas 2)
- `send_on_patrol(npc_id:npc_id, duration:int)` — devriye gönderir (Gas 3)
- `return_from_patrol(npc_id:npc_id, report:str?)` — devriyeyi döndürür (Gas 2)
- `rally_npc(npc_id:npc_id, message:str?)` — motivasyon konuşması (Gas 1)

## Economy / Resources
- `allocate_food(amount:int, target:str)` — erzak dağıtır (Gas 2)
- `ration_food(severity:int)` — az tüketim moduna geçer (Gas 2)
- `gather_supplies(region:str, effort:int)` — kaynak toplar (Gas 3)
- `craft_ammo(workshop:str, batch:int)` — mühimmat üretir (Gas 2)
- `salvage_material(location:str, amount:int)` — malzeme geri kazanır (Gas 2)
- `store_resources(resource:str, amount:int)` — depolama yapar (Gas 1)
- `redistribute_stockpile(from_stock:str, to_stock:str, amount:int)` — stok transferi (Gas 3)
- `limit_consumption(resource:str, percent:int)` — tüketim sınırı (Gas 1)
- `boost_production(workshop:str, focus:str)` — üretimi hızlandırır (Gas 3)
- `check_inventory(resource:str)` — stok raporu (Gas 1)

## Morale / Social
- `inspire_troops(speech:str, bonus:int?)` — moral artışı (Gas 2)
- `calm_civilians(zone:str, effort:int)` — panik azaltır (Gas 2)
- `hold_speech(topic:str, audience:str)` — resmi konuşma (Gas 3)
- `punish_treason(npc_id:npc_id, severity:int)` — disiplin uygular (Gas 3)
- `reward_bravery(npc_id:npc_id, reward:str)` — ödül verir (Gas 2)
- `celebrate_small_victory(location:str)` — küçük kutlama (Gas 1)
- `reduce_panic(zone:str, amount:int)` — panik metriğini düşürür (Gas 2)
- `hold_council_meeting(agenda:str)` — konsey toplar (Gas 2)
- `comfort_wounded(ward:str, care:int)` — yaralılarla ilgilenir (Gas 2)
- `assign_morale_officer(npc_id:npc_id, sector:str)` — moral görevlisi atar (Gas 2)

## Event / World
- `spawn_event_marker(marker_id:str, x:int, y:int, severity:int?)` — harita işareti (Gas 2)
- `remove_event_marker(marker_id:str)` — işareti kaldırır (Gas 1)
- `trigger_alarm(level:str, message:str?)` — alarm moduna geçer (Gas 2)
- `create_storm(duration:int, intensity:int)` — atmosferi değiştirir (Gas 4)
- `extinguish_storm(duration:int)` — fırtınayı bastırır (Gas 3)
- `collapse_tunnel(tunnel_id:str)` — tünel çökertir (Gas 3)
- `reinforce_tunnel(tunnel_id:str, amount:int)` — tüneli sağlamlaştırır (Gas 2)
- `flood_area(zone:str, severity:int)` — alanı sular altında bırakır (Gas 3)
- `create_signal_fire(location:str, intensity:int)` — işaret ateşi (Gas 2)
- `set_watch_lights(section:str, brightness:int)` — nöbet ışıkları (Gas 1)

## Utility
- `adjust_metric(metric:str, delta:int, cause:str?)` — metrik ayarlar (Gas 1)
- `log_message(message:str, severity:str?)` — log girdisi ekler (Gas 1)
- `tag_state(tag:str)` — durum etiketi ekler (Gas 1)
- `set_flag(flag:str)` — global bayrak açar (Gas 1)
- `clear_flag(flag:str)` — bayrak kaldırır (Gas 1)

Her fonksiyonun ayrıntılı parametre şeması `fortress_director/core/function_registry.py` içindeki metadata listesinde bulunur ve `tests/safe_functions` altındaki testler şemayı doğrular.
