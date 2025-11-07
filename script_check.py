from fortress_director.orchestrator.orchestrator import Orchestrator
from fortress_director.settings import CREATIVITY_MOTIF_INTERVAL

orch = Orchestrator.build_default()
orch.state_store.persist(orch.state_store._fresh_default())
for turn in range(1, CREATIVITY_MOTIF_INTERVAL + 2):
    result = orch.run_turn()
    state = orch.state_store.snapshot()
    print('turn', turn, 'motifs', state.get('recent_motifs'))
