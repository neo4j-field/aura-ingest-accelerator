# Session: Baseline Extraction — [REPO-NAME]

Date: YYYY-MM-DD
Repo: [repo-name]
Branch: develop
Status: draft

---

## Goal

Extract all locked architectural decisions, integration contracts, known constraints,
and key data shapes from existing project documentation and produce a populated
`.session/specs/[repo-name]-baseline.md` file. This is a one-time migration session
to bring this repo into the `.session/` workflow convention.

No code changes. Documentation output only.

---

## Context & Constraints

- **Out of scope**: Do not modify any source code, claude.md, README.md, or ARCHITECTURE.md
- **Out of scope**: Do not make new architectural decisions — only extract what is already documented
- **Out of scope**: Do not infer or speculate — if something is ambiguous, note it as `[UNCLEAR]`
- **Output target**: `.session/specs/[repo-name]-baseline.md`

---

## Instructions

1. Read `claude.md` — specifically the `## Project-Specific` section.
2. Read `README.md` — extract any stated design constraints, integration points, or usage contracts.
3. Read `ARCHITECTURE.md` — extract data flow, component responsibilities, and any locked decisions.
4. Read any files in `docs/` that contain design decisions.
5. Produce `.session/specs/[repo-name]-baseline.md` using the output format below.
6. Do NOT modify any source files. Commit the new specs file when done.

---

## Output Format for `.session/specs/[repo-name]-baseline.md`

```markdown
# Baseline Spec: [repo-name]

Extracted: YYYY-MM-DD
Source: README.md, ARCHITECTURE.md, claude.md ## Project-Specific
Status: baseline (locked — update via new session file)

---

## Locked Decisions

<!-- Things that are decided and should not be revisited without deliberate intent -->

- [Decision statement] — Source: [file]
- ...

## Integration Contracts

<!-- How this repo interfaces with other repos or external systems -->

| Interface | Direction | Contract |
|:---|:---|:---|
| [other-repo or system] | [in/out] | [what the contract is] |

## Key Data Shapes

<!-- Core Pydantic models, graph node/rel types, payload formats -->

[Paste or summarize the key schemas here]

## Known Constraints

<!-- Technical constraints, environment requirements, things that must not change -->

- [Constraint] — Reason: [why]

## Known Tech Debt / Deferred Items

<!-- Things that are known issues but intentionally deferred -->

- [Item] — Deferred because: [reason]

## Unclear / Needs Clarification

<!-- Things found in docs that are ambiguous or contradictory -->

- [UNCLEAR]: [description]
```

---

## Decisions Made This Session

_None yet._