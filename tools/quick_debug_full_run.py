import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fortress_director.orchestrator.orchestrator import Orchestrator, StateStore
from fortress_director.agents.event_agent import EventAgent
from fortress_director.agents.world_agent import WorldAgent
from fortress_director.agents.character_agent import CharacterAgent
from fortress_director.agents.judge_agent import JudgeAgent
from fortress_director.rules.rules_engine import RulesEngine
from fortress_director.codeaware.function_registry import SafeFunctionRegistry
from fortress_director.codeaware.function_validator import FunctionCallValidator
from fortress_director.codeaware.rollback_system import RollbackSystem
from fortress_director.utils.metrics_manager import MetricManager
from fortress_director.settings import DEFAULT_WORLD_STATE

def main():
    out_dir = Path("runs") / "debug_full_run"
    out_dir.mkdir(parents=True, exist_ok=True)
    orch = Orchestrator.__new__(Orchestrator)
    store = StateStore(out_dir / "world_state.json")
    orch.state_store = store
    orch.event_agent = EventAgent()
    orch.world_agent = WorldAgent()
    orch.character_agent = CharacterAgent()
    orch.judge_agent = JudgeAgent()
    orch.rules_engine = RulesEngine(judge_agent=orch.judge_agent)
    orch.function_registry = SafeFunctionRegistry()
    orch.function_validator = FunctionCallValidator(orch.function_registry, max_calls_per_function=10, max_total_calls=50)
    orch.rollback_system = RollbackSystem(snapshot_provider=store.snapshot, restore_callback=store.persist, max_checkpoints=10)
    orch._register_default_safe_functions()

    baseline = dict(DEFAULT_WORLD_STATE)
    MetricManager(baseline, log_sink=[])
    store.persist(baseline)

    major_flag = False
    sf_executed = False
    for t in range(1, 11):
        print(f"\n--- Turn {t} ---")
        result = orch.run_turn()
        state = store.snapshot()
        print("options:", len(result.get("options", [])))
        print("flags:", state.get("flags", []))
        print("effects:", result.get("effects", []))
        if any("change_weather" in str(e) for e in result.get("effects", [])):
            sf_executed = True
        if any("major_" in f for f in state.get("flags", [])):
            major_flag = True
    print("major_flag:", major_flag, "safe_fn:", sf_executed)

if __name__ == "__main__":
    os.environ.setdefault("FORTRESS_USE_OLLAMA", "1")
    main()
