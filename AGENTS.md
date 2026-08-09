# AGENTS.md — LogPulse

## What this project is

A tool that ingests OSS/BSS-style log excerpts, classifies error patterns,
and suggests likely root causes — automating manual RCA triage work.

## Base rules

- Plan lives in SPECS.md, never in built-in plan-mode (Part 0 pre-rule).
- Never hand-patch a wrong agent output. Fix the instruction/doc that caused
  it, then let the agent redo the work. (Tip 1)
- No code change ships without a docs lookup + update. (Tip 7)
- On a real external blocker: stop and write to blocked.md. Do not guess. (Tip 16)

## Routing table

| Situation                          | Open this file         |
| ---------------------------------- | ---------------------- |
| touching classification categories | docs/business-logic.md |
| adding endpoint/component          | docs/architecture.md   |
| picking library/dependency         | docs/tech-stack.md     |
| code style question                | docs/patterns.md       |

## Memory rules

- One task, one fresh chat. Never continue a long chat past its task. (Tip 8)
- Never let the agent auto-compact context — start fresh instead. (Tip 8)
- Heavy research (multi-file/multi-source digging) → spawn a helper agent.
  Helper does research ONLY, returns a summary, never implements,
  never sees full docs/rules. (Tip 9)
- Every commit: detailed message — what, why, order. (Tip 10)
- Every significant change → new branch, same name as its tasks/ subfolder,
  holding that unit's SPECS.md. (Tip 10)
- Every implementation gets a test — regression fence for future bug hunts. (Tip 11)
