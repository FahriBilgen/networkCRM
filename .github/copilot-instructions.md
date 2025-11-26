# Copilot Instructions for Fortress Director

You are coding inside the **Fortress Director** project — a deterministic, local-first multi-agent AI game engine.

---

## 🧱 Architecture Overview

The engine is built around several specialized AI agents and a deterministic orchestration layer:

EventAgent → WorldAgent → CharacterAgent → RulesEngine → StateStore

yaml
Kodu kopyala

**Orchestrator (Python)**  
Controls the serialized async flow of turns. Each turn includes:
1. Event generation  
2. World description  
3. Player choice  
4. Character reactions  
5. Rules validation and state update  

**Agents (LLM-based)**  
- `EventAgent` (Mistral 7B): short scene + 3 diegetic options  
- `WorldAgent` (Phi-3 Mini): atmosphere & sensory description  
- `CharacterAgent` (Gemma 2B): NPC intents, actions, dialogue  
- `JudgeAgent` (Qwen 1.5B): checks lore consistency  
All must return **pure JSON outputs** (no markdown, no code blocks).

**Rules Engine**  
Validates and applies deterministic logic:
- Tier 1: rejects physical impossibilities  
- Tier 2: asks JudgeAgent for lore consistency  

**State Store (SQLite + JSON)**  
Maintains player, NPCs, world, and progress.  
Every turn ends with one atomic state transaction.

---

## 🧩 Code-Aware Layer

`fortress_director/codeaware/function_registry.py` defines a **SafeFunctionRegistry** - functions the AI can safely call (e.g. `move_npc`, `add_rock_to_map`, `change_weather`, `spawn_item`).  
Each function has a validator and rollback mechanism.

---

## 🧠 MVP Context: Siege of Lornhaven

Test scenario:
- Small mountain village under siege (3-day cycle)
- NPCs: *Scout Rhea*, *Merchant Boris*
- Motifs: defense, trade, risk
- Major event: "The Wall Collapses" (Day 3)

Goal: validate the full agent chain and safe function execution.

---

## ⚙️ Developer Workflow

- Run orchestrator locally:  
  ```bash
  python fortress_director/cli.py run_turn
State persistence in data/world_state.json and db/game_state.sqlite

Use mock model outputs during development

Test deterministic logic before LLM integration

💡 Project Conventions
All model outputs → JSON only

Serialized async flow (no parallel execution)

Atomic state updates

Deterministic rules first, AI decisions second

Prefer modular, stateless agents

🧭 Example Directories
kotlin
Kodu kopyala
fortress_director/
  orchestrator/
  agents/
  rules/
  codeaware/
  prompts/
  data/
  db/
  cache/
  cli.py
  settings.py
Copilot should always:

Follow these structures and naming conventions.

Avoid adding frameworks or async runners.

Focus on deterministic logic, clarity, and modularity.
