from fastapi import FastAPI, Body
from fortress_director.orchestrator.orchestrator import Orchestrator

app = FastAPI()
orchestrator = Orchestrator.build_default()


@app.post("/motif/update")
def update_motif(new_motif: str = Body(..., embed=True)):
    orchestrator.update_motif(new_motif)
    return {"status": "success", "motif": new_motif}


@app.post("/character/update")
def update_character(
    name: str = Body(...),
    summary: str = Body(...),
    stats: dict = Body(None),
    inventory: list = Body(None),
):
    orchestrator.update_character(name, summary, stats, inventory)
    return {"status": "success", "character": name}


@app.post("/prompt/update")
def update_prompt(
    agent: str = Body(...),
    new_prompt: str = Body(...),
    persist_to_file: bool = Body(True),
):
    orchestrator.update_prompt(agent, new_prompt, persist_to_file)
    return {"status": "success", "agent": agent}


@app.post("/safe_function/mutate")
def mutate_safe_function(name: str = Body(...), remove: bool = Body(False)):
    # For demo, only support removal via API
    orchestrator.mutate_safe_function(name, remove=remove)
    return {"status": "success", "name": name, "removed": remove}
