import logging
from fortress_director.orchestrator.orchestrator import Orchestrator


def test_creativity_agent_integration_and_logging(tmp_path, caplog):
    caplog.set_level(logging.INFO)
    orch = Orchestrator.build_default()
    # Zorunlu state reset (her şey default olsun)
    orch.state_store.persist(orch.state_store._fresh_default())
    # 3. turda motif injection ve logda creativity adımı beklenir
    debug_outputs = []
    for turn in range(1, 5):
        result = orch.run_turn()
        debug_outputs.append(
            f"[DEBUG] turn={turn} result type: {type(result)} value: {repr(result)}"
        )
        try:
            assert isinstance(
                result, dict
            ), f"run_turn beklenmeyen tip döndürdü: {type(result)}\nDeğer: {result}"
        except AssertionError as e:
            debug_outputs.append(f"[ERROR] turn={turn} AssertionError: {e}")
            break
        # Her turda orchestrator loglarında CreativityAgent adımı olmalı
        creativity_logs = [
            r for r in caplog.records if "CreativityAgent" in r.getMessage()
        ]
        assert creativity_logs, f"CreativityAgent logu bulunamadı (turn={turn})"
        # 3. turda motif injection state'e yansır
        if turn == 3:
            motifs = result.get("WORLD_CONTEXT", {}).get("recent_motifs", [])
            assert any(
                m in motifs for m in orch.creativity_agent.MOTIF_TABLE
            ), f"3. turda motif injection bekleniyordu, motifs: {motifs}, result: {result}"
    # Print all debug outputs at the end
    import sys

    for line in debug_outputs:
        print(line, file=sys.stderr)
