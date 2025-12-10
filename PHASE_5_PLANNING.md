# PHASE 5: Extended Agent Integration - Planning & Roadmap

**Status**: Planning phase  
**Estimated Timeline**: 2-3 days  
**Difficulty**: Medium (pattern already established)  
**Dependencies**: Phase 1-4 complete ✅

---

## 🎯 Objective

Extend the State Archive context injection to **PlannerAgent** and **WorldRendererAgent**, ensuring all 3 agents receive historical campaign context for consistent narrative decision-making.

---

## 📋 Work Breakdown

### Task 1: PlannerAgent Archive Integration

**Goal**: PlannerAgent receives historical context like DirectorAgent

**Steps**:
1. Locate `fortress_director/agents/planner_agent.py`
2. Add `archive` and `turn_number` parameters to `generate_plan()`
3. Modify `_build_prompt()` to inject archive context
4. Update TurnManager to pass archive to PlannerAgent
5. Create 2-3 tests for PlannerAgent + archive

**Expected Impact**:
- Planner makes decisions aware of campaign history
- Story flow consistency with director intent
- Reduced NPC contradictions

### Task 2: WorldRendererAgent Archive Integration

**Goal**: WorldRendererAgent receives historical context

**Steps**:
1. Locate `fortress_director/agents/world_renderer_agent.py`
2. Add `archive` and `turn_number` parameters to `render_world()`
3. Modify `_build_prompt()` to inject archive context
4. Update TurnManager to pass archive to WorldRendererAgent
5. Create 2-3 tests for WorldRendererAgent + archive

**Expected Impact**:
- World descriptions reference past events
- Location state consistency
- Atmosphere matches campaign progress

### Task 3: Integration Testing

**Goal**: All 3 agents work together with shared archive context

**Tests to Create**:
- Test all 3 agents receive same archive
- Test context injection consistency
- Test narrative flow across agents
- Test campaign-long coherence (20+ turns)

**Expected**: 4-5 integration tests

### Task 4: Documentation

**Goal**: Document Phase 5 completion

**Deliverables**:
- PHASE_5_AGENT_INTEGRATION_COMPLETE.md
- Updated architecture diagrams
- Usage examples

---

## 🔍 Technical Details

### PlannerAgent Pattern

Current signature (example):
```python
def generate_plan(
    self,
    game_state: GameState,
    theme: ThemeConfig,
    threat_snapshot: ThreatSnapshot
) -> Dict[str, Any]:
```

New signature:
```python
def generate_plan(
    self,
    game_state: GameState,
    theme: ThemeConfig,
    threat_snapshot: ThreatSnapshot,
    archive: StateArchive | None = None,      # ← NEW
    turn_number: int = 0                      # ← NEW
) -> Dict[str, Any]:
```

Implementation in `_build_prompt()`:
```python
prompt = render_prompt(self._prompt_template, replacements)

if archive is not None and turn_number > 0:
    prompt = inject_archive_to_prompt(
        archive, turn_number, prompt
    )
return prompt
```

### WorldRendererAgent Pattern

Same approach:
- Add `archive` + `turn_number` parameters
- Call `inject_archive_to_prompt()` in prompt building
- Update TurnManager to pass archive

### Integration Points in TurnManager

Current (Phase 4 state):
```python
director_output = self.run_director_sync(
    projected_state,
    choice_id,
    threat_snapshot=threat_snapshot,
    archive=archive,           # ← Already passes
    turn_number=turn_number
)
```

New additions needed:
```python
# For PlannerAgent
planner_output = self.planner_agent.generate_plan(
    game_state,
    theme,
    threat_snapshot=threat_snapshot,
    archive=archive,           # ← ADD
    turn_number=turn_number    # ← ADD
)

# For WorldRendererAgent
world_output = self.world_renderer_agent.render_world(
    ...,
    archive=archive,           # ← ADD
    turn_number=turn_number    # ← ADD
)
```

---

## 🧪 Test Plan

### PlannerAgent Tests (2-3 tests)

```python
def test_planner_with_archive():
    """Test PlannerAgent accepts archive parameter."""
    planner = PlannerAgent(use_llm=False)
    archive = StateArchive("test_session")
    # ... add 10 turns to archive ...
    
    result = planner.generate_plan(
        game_state,
        theme,
        threat_snapshot,
        archive=archive,
        turn_number=10
    )
    
    assert result is not None
    assert "strategic_intent" in result or "actions" in result

def test_planner_without_archive():
    """Test PlannerAgent backward compatible."""
    # Call without archive - should work
    result = planner.generate_plan(...)
    assert result is not None
```

### WorldRendererAgent Tests (2-3 tests)

```python
def test_world_renderer_with_archive():
    """Test WorldRendererAgent accepts archive."""
    renderer = WorldRendererAgent(use_llm=False)
    archive = StateArchive("test_session")
    
    result = renderer.render_world(
        ...,
        archive=archive,
        turn_number=10
    )
    
    assert result is not None
    assert "world_description" in result

def test_world_renderer_without_archive():
    """Test backward compatibility."""
    result = renderer.render_world(...)
    assert result is not None
```

### Integration Tests (3-4 tests)

```python
def test_all_agents_receive_archive():
    """Test all 3 agents get same archive context."""
    # Director, Planner, WorldRenderer all called with same archive
    # Verify context injected consistently

def test_archive_context_consistency():
    """Test context format is identical across agents."""
    # Same archive, same turn → same context injection

def test_campaign_coherence_20_turns():
    """Test narrative stays coherent for 20+ turns."""
    # Record 20 turns, all agents see full history
```

---

## 📊 Expected Test Coverage

| Component | Tests | Status |
|-----------|-------|--------|
| DirectorAgent + Archive | 2 | ✅ Already done |
| PlannerAgent + Archive | 2 | ⏳ Phase 5 |
| WorldRendererAgent + Archive | 2 | ⏳ Phase 5 |
| All 3 Agents Integration | 4 | ⏳ Phase 5 |
| **Total Phase 5** | **8** | **⏳ Pending** |

---

## 🏗️ Architecture Changes

### Before Phase 5
```
TurnManager
├─ DirectorAgent (has archive)    ✅
├─ PlannerAgent (no archive)      ❌
└─ WorldRendererAgent (no archive) ❌
```

### After Phase 5
```
TurnManager
├─ DirectorAgent (has archive)     ✅
├─ PlannerAgent (has archive)      ✅
└─ WorldRendererAgent (has archive) ✅
```

**Result**: All 3 agents see shared campaign history!

---

## 🎯 Success Criteria

✅ PlannerAgent accepts and uses archive  
✅ WorldRendererAgent accepts and uses archive  
✅ Both pass archive parameters correctly from TurnManager  
✅ Backward compatibility maintained (archive optional)  
✅ 8/8 new tests passing  
✅ Total test count: 41/41 passing (33 Phase 1-4 + 8 Phase 5)  
✅ No regression in existing tests  

---

## 📈 Impact

### Narrative Improvement

| Scenario | Before | After |
|----------|--------|-------|
| DirectorAgent story | Aware of history | ✅ |
| PlannerAgent strategy | Ignores history | ✅ Aware |
| WorldRendererAgent descriptions | Generic | ✅ Contextual |
| NPC consistency | Varies | ✅ Unified |

### Code Quality

| Metric | Before | After |
|--------|--------|-------|
| Archive-aware agents | 1/3 (33%) | 3/3 (100%) |
| Test coverage | 33 tests | 41 tests |
| Pattern consistency | 1 agent | 3 agents |

---

## ⏱️ Estimated Timeline

| Task | Time | Complexity |
|------|------|-----------|
| PlannerAgent integration | 4-6 hours | Low |
| WorldRendererAgent integration | 4-6 hours | Low |
| Integration testing | 3-4 hours | Medium |
| Documentation | 1-2 hours | Low |
| **Total** | **12-18 hours** | **Medium** |

**Estimated**: 2-3 development days

---

## 🚀 Execution Plan

### Day 1: Core Implementation
- [ ] Modify PlannerAgent (1 hour)
- [ ] Modify WorldRendererAgent (1 hour)
- [ ] Update TurnManager (1 hour)
- [ ] Create agent tests (2-3 hours)

### Day 2: Integration & Testing
- [ ] Create integration tests (2-3 hours)
- [ ] Run full test suite (30 min)
- [ ] Fix any failures (1-2 hours)
- [ ] Performance validation (1 hour)

### Day 3: Documentation & Polish
- [ ] Write Phase 5 documentation (1-2 hours)
- [ ] Update architecture diagrams (30 min)
- [ ] Final testing & validation (1 hour)
- [ ] Commit & push (30 min)

---

## 📋 Checklist

### Implementation
- [ ] PlannerAgent: Add archive parameter
- [ ] PlannerAgent: Modify _build_prompt()
- [ ] PlannerAgent: Test coverage
- [ ] WorldRendererAgent: Add archive parameter
- [ ] WorldRendererAgent: Modify _build_prompt()
- [ ] WorldRendererAgent: Test coverage
- [ ] TurnManager: Pass archive to both agents
- [ ] Backward compatibility verified

### Testing
- [ ] 2 PlannerAgent tests passing
- [ ] 2 WorldRendererAgent tests passing
- [ ] 4 integration tests passing
- [ ] All 33 Phase 1-4 tests still passing
- [ ] Total: 41/41 passing

### Documentation
- [ ] PHASE_5_AGENT_INTEGRATION_COMPLETE.md
- [ ] Architecture diagrams updated
- [ ] Code examples added
- [ ] Commit message written

---

## 🔄 Next After Phase 5

### Phase 6: Long Campaign Testing
- Test 100-200 turn campaigns
- Profile memory + performance
- Validate LLM context quality
- Performance benchmarking

### Phase 7: Combat System Clarification
- Define resolve_combat() mechanics
- Archive-aware combat resolution
- Combat consistency testing
- Threat model integration

### Phase 8: React UI Frontend
- Session browser
- Turn replay
- Campaign statistics
- Real-time updates

---

## 📚 References

### Existing Code
- `fortress_director/agents/director_agent.py` (reference implementation)
- `fortress_director/core/state_archive.py` (inject_archive_to_prompt function)
- `fortress_director/pipeline/turn_manager.py` (integration point)

### Documentation
- `STATE_ARCHIVE_ALL_PHASES_COMPLETE.md` (architecture)
- `PHASE_3_LLM_INJECTION_COMPLETE.md` (DirectorAgent pattern)
- `PHASE_4_PERSISTENCE_COMPLETE.md` (database layer)

---

## 🎓 Learning from Phase 3

**What Worked**:
- Minimal changes to existing code
- Pattern: Add parameter → Modify prompt → Inject context
- Tests very straightforward
- No breaking changes

**What to Replicate in Phase 5**:
- Same 3-step pattern for both agents
- Similar test structure
- Same injection logic

**What to Avoid**:
- Over-engineering the integration
- Complex test setups
- Changing existing agent signatures where not needed

---

## ✨ Summary

**Phase 5** extends the State Archive concept from 1 agent (DirectorAgent) to all 3 agents (Director + Planner + WorldRenderer).

**Result**: All agents see campaign history, enabling truly coherent narrative experiences across long campaigns.

**Status**: Ready to implement once Phase 1-4 are confirmed stable.

**Recommended**: Start Phase 5 when:
- All Phase 1-4 tests consistently passing ✅
- DirectorAgent injection working correctly ✅
- No database persistence issues ✅

---

**Next Step**: Run the command below to confirm readiness:

```bash
pytest fortress_director/tests/test_state_archive.py \
        fortress_director/tests/test_archive_api_integration.py \
        fortress_director/tests/test_director_agent_archive.py \
        fortress_director/tests/test_archive_persistence.py -v

# Expected: 33/33 ✅ PASSING
```

Then proceed with Phase 5 implementation.
