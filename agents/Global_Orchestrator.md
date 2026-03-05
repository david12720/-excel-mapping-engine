# Global_Orchestrator

## Role
Sequence the agents. Define who runs when, what each agent hands off, and what constitutes a valid transition between phases.
Does not implement logic. Does not write code.

---

## Execution Phases

```
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 0 — Architecture Lock                                    │
│  Agent: Architect_Agent                                         │
│  Output: Signed-off config schema + behavioral contracts        │
│  Gate: All 8 parameters defined. All contracts documented.      │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│  PHASE 1 — Core Implementation                                  │
│  Agent: Coder_Agent                                             │
│  Input: Architect_Agent.md contracts                            │
│  Output: 4 engine modules (strategies, source_reader,           │
│          master_writer, orchestrator) + main.py                 │
│  Gate: All modules import cleanly. upsert() is pure function.   │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│  PHASE 2A — Unit Testing                                        │
│  Agent: Tester_Agent (Phase A)                                  │
│  Input: Coder_Agent Phase A deliverable                         │
│  Output: Passing unit tests for all engine functions            │
│  Gate: Zero test failures. All behavioral contracts exercised.  │
│  On failure: Return to Coder_Agent with specific failure report │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│  PHASE 2B — Integration Testing                                 │
│  Agent: Tester_Agent (Phase B)                                  │
│  Input: Real example files + explicit parameters from USER      │
│  Trigger: Tester_Agent declares file requirements to user       │
│  Output: Passing end-to-end tests. Final summary report.        │
│  Gate: All I-0x test cases pass. Master idempotency confirmed.  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Handoff Contracts

### Architect_Agent → Coder_Agent
- Deliverable: `Architect_Agent.md` fully written and stable.
- Coder must not begin implementation until the schema and all behavioral contracts are locked.

### Coder_Agent → Tester_Agent (Phase A)
- Deliverable: All four engine modules importable with no errors.
- `upsert()` must be a pure function (no file I/O) so Tester can call it directly.
- Coder documents any known edge cases not yet handled.

### Tester_Agent (Phase A) → Tester_Agent (Phase B)
- Gate: 100% of Phase A unit tests passing.
- Tester declares the exact file structure and parameters needed from the user.
- No Phase B work begins until user confirms files are available.

### Tester_Agent → User (file request)
- Tester produces a filled-in version of the Phase B file request template.
- User supplies files and fills in the `___` placeholders with real values.
- Tester runs Phase B with those exact values — no assumptions.

---

## Failure Routing

| Failure Point | Action |
|---------------|--------|
| Phase A unit test fails | Tester returns specific failing test ID + error to Coder. Coder fixes and resubmits. |
| Phase B integration test fails | Tester identifies whether failure is in engine code or in supplied files. Routes accordingly. |
| Config validation fails at startup | `main.py` halts with a clear error message listing missing fields. No agent involvement. |
| Unexpected exception in engine loop | Logged with full traceback. Loop continues. Summarized at end of run. |

---

## Extension Protocol

When a new capability is needed (e.g. GUI, new extraction strategy, async processing):
1. Architect_Agent updates the schema and/or contracts.
2. Coder_Agent implements against the updated spec.
3. Tester_Agent adds test cases for the new behavior.
4. Global_Orchestrator updates phase gates if the delivery sequence changes.

No agent modifies another agent's owned files without declaring the change here first.
