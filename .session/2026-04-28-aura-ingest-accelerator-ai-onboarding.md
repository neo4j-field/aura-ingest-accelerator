# Session Handoff: AI-Assisted Connector Development Onboarding
# aura-ingest-accelerator

Status: complete
Date: 2026-04-28
Topic: aura-ingest-accelerator-ai-onboarding

---

## Goal

Add two pieces of customer-facing AI onboarding to the `aura-ingest-accelerator` repo: (1) a pre-written `.session/add-connector.md` session file that gives an AI coding agent (The AI Coding Agent, Codex, Copilot) the full context it needs to implement a new `sources/` connector while respecting the repo architecture; and (2) a new section in `poc_walkthrough.ipynb` titled "Using AI to Add a New Connector" that walks a customer through the workflow with tool-specific tips for The AI Coding Agent, GitHub Copilot, and OpenAI Codex. The `.session/` directory and `_template.md` already exist — do not recreate them.

---

## Context & Constraints

### Locked decisions
- The `.session/` convention uses structured markdown with these required sections: **Goal**, **Context & Constraints**, **Relevant Specs / Schemas / Examples**, **Instructions** (numbered, imperative), **Decisions Made This Session**. Header must include `Status: draft|active|complete`.
- Session files are named `YYYY-MM-DD-[topic].md`. The `_template.md` is already present — do not overwrite it.
- The `add-connector.md` session file must be **pre-filled** (not a blank template) with actual repo content: real `BaseSource` signature, real file layout, the `main.py` registration pattern, and a worked skeleton based on one of the two existing sources.
- There is no package manager scaffolding (`uv`, `pyproject.toml`) — the repo uses plain `pip` + `venv`. Do not reference `uv` commands anywhere.
- There is no Jupyter Book `_toc.yml`. Documentation lives in `poc_walkthrough.ipynb` — the new AI guide goes in as an additional notebook section at the end, not a separate file.
- Sources are **not auto-discovered** — a new source must be explicitly imported and instantiated in `main.py`. The session file instructions must cover this step.
- Do **not** modify `importer.py`, `sources/base.py`, or either existing source implementation.
- Do **not** add new pip dependencies without flagging them explicitly in Decisions Made This Session.

### Out of scope
- Automating connector registration.
- CI/CD or testing infrastructure changes.
- Changes to `config.yaml` structure or the `Neo4jImporter` class.

### Reference files (read before writing)
- `sources/base.py` — `BaseSource` ABC; the only contract a new source must satisfy
- `sources/bigquery_source.py` — primary worked example (streaming, lazy iterator)
- `sources/gcs_source.py` — secondary example (blob download then parse)
- `main.py` — shows how sources are instantiated, how `TRANSFORMS` dict is defined and referenced, and how `run_poc()` wires everything together
- `config.yaml` — shows the full job schema a new source entry must conform to
- `poc_walkthrough.ipynb` — identify the last cell/section; append the new AI guide section after it

---

## Relevant Specs / Schemas / Examples

### Repo layout
```
├── importer.py                  # Core Neo4j batch importer — do not modify
├── main.py                      # Instantiates sources, defines TRANSFORMS, calls run_poc()
├── poc_walkthrough.ipynb        # Jupyter walkthrough — append new section here
├── sources/
│   ├── base.py                  # BaseSource ABC — do not modify
│   ├── bigquery_source.py       # Streaming example
│   └── gcs_source.py            # Blob-download example
├── config.yaml                  # All import jobs
├── env.sample
├── .session/
│   ├── _template.md             # Already exists — do not overwrite
│   └── add-connector.md         # CREATE THIS
└── .gitignore
```

### `BaseSource` contract (copy actual signature from `sources/base.py`)
```python
# Populate this section with the real class body after reading sources/base.py.
# It will look something like:
from abc import ABC, abstractmethod

class BaseSource(ABC):
    @abstractmethod
    def get_batches(self, batch_size: int):
        """Yield lists of dicts, each list being one batch."""
        ...
```

### New source file layout
```
sources/
└── <source_name>_source.py      # Single file — matches existing naming convention
```

No subdirectory. No `__init__.py`. One file, named `<source_name>_source.py`.

### Registration pattern (from `main.py`)
A new source requires **two** manual edits to `main.py`:

1. Import the class:
   ```python
   from sources.<source_name>_source import <SourceName>Source
   ```

2. Instantiate and pass to `run_import()` (or add a new job call inside `run_poc()`).
   There is no auto-discovery — the source object must be explicitly constructed.

If the source requires a transform, also add an entry to the `TRANSFORMS` dict:
```python
TRANSFORMS = {
    "transform_<source_name>_row": transform_<source_name>_row,
}
```

### `config.yaml` job schema
```yaml
imports:
  - name: "My New Source Import"
    source: <source_name>          # arbitrary label; match what main.py uses
    # source-specific keys (e.g. query, bucket/blob, connection string)
    cypher: |
      UNWIND $rows AS row
      MERGE (n:MyLabel {id: row.id})
      SET n.name = row.name
    batch_size: 1000
    transform: transform_<source_name>_row   # optional
```

### Worked skeleton (model on the simpler of the two existing sources)
```python
# sources/snowflake_source.py  — illustrative; adapt to your actual target system
from sources.base import BaseSource

class SnowflakeSource(BaseSource):
    def __init__(self, query: str, connection_params: dict):
        self.query = query
        self.connection_params = connection_params

    def get_batches(self, batch_size: int):
        batch = []
        for row in self._stream_rows():
            batch.append(dict(row))
            if len(batch) >= batch_size:
                yield batch
                batch = []
        if batch:
            yield batch

    def _stream_rows(self):
        # Open connection, execute self.query, yield rows
        raise NotImplementedError
```

### `poc_walkthrough.ipynb` AI guide — section outline
Append as a new markdown + code cell group at the very end of the notebook:

```markdown
## Using AI to Add a New Connector

The repo is designed so that an AI coding agent can implement a new data source
connector with minimal hand-holding, as long as it's pointed at the right context first.

### Prerequisites
- Repo cloned, venv active (see Quickstart in README)
- `.env` configured with AuraDB credentials
- An AI coding agent: The AI Coding Agent (recommended), GitHub Copilot Workspace,
  or ChatGPT / Codex with file upload

---

### Workflow

#### Step 1 — Orient the agent
Point it at the session file before writing a single line of code:

> "Read `.session/add-connector.md` completely, then implement a connector
>  for [source system]. Ask me for any credential or schema details you need."

#### Step 2 — Name your connector and describe your source
Tell the agent the source system (e.g. Snowflake, Databricks, Oracle, S3, Postgres)
and provide any connection credential shape or SDK name you know.

#### Step 3 — Review the generated code
Before running anything, verify:
- [ ] New file is at `sources/<source_name>_source.py`
- [ ] `get_batches()` **yields lists of dicts** (not a single dict, not a generator of scalars)
- [ ] Class is imported and instantiated in `main.py`
- [ ] A new entry exists in `config.yaml` with valid Cypher using `UNWIND $rows AS row`
- [ ] An index exists for any property used in a `MERGE` clause (see Indexing section in README)

#### Step 4 — Test with a small batch
Set `batch_size: 10` in `config.yaml` for the new job and run:
```python
from main import run_poc
run_poc("config.yaml")
```

Check the summary log output. Fix any errors before increasing batch size.

#### Step 5 — Open a PR
Conventional commit prefix: `feat(sources): add <source_name> connector`

---

### Tool-Specific Tips

#### The AI Coding Agent
Paste this as your opening message in a The AI Coding Agent session:

```
Read .session/add-connector.md completely, then implement a connector for [source system].
Ask me for any credential structure or SDK details before writing code.
```

The AI Coding Agent can read repo files directly — give it access to the full working directory.

#### GitHub Copilot Workspace
- Open a new Workspace task; paste the **Goal** section of `add-connector.md` as the task description.
- Attach `sources/base.py` and `sources/bigquery_source.py` as context files.
- Use the "Generate plan" step and review before accepting code.

#### ChatGPT / Codex with file upload
- Upload `sources/base.py` and `sources/bigquery_source.py`.
- Paste the **Instructions** section from `.session/add-connector.md` verbatim as your first message.
- Ask for one file at a time to stay within context limits.

---

### What the AI Should NOT Change
- `sources/base.py` — the abstract interface is frozen
- `importer.py` — do not touch
- Existing source implementations

### Common Failures
| Symptom | Fix |
|---|---|
| Agent modified `sources/base.py` | Re-prompt: "Do not modify `sources/base.py`." Revert the file and retry. |
| `get_batches()` yields single dicts instead of lists | Re-prompt: "Each `yield` must produce a **list** of dicts, not a single dict." |
| New source never runs | Check `main.py` — the source must be imported and explicitly instantiated. There is no auto-discovery. |
| MERGE is slow or times out | Create an index on the MERGE property before running the import. See the Indexing section in README. |
| Agent adds unknown pip packages | Review `requirements` in generated code; install manually and note in your PR description. |
```

---

## Instructions

1. **Read** `sources/base.py`, `sources/bigquery_source.py`, `sources/gcs_source.py`, and `main.py` before writing any files. Note the exact `BaseSource` signature, the `get_batches()` yield contract, and the full instantiation pattern used in `main.py`.

2. **Create** `.session/add-connector.md` as a fully pre-filled session file with `Status: active`. Populate **Relevant Specs / Schemas / Examples** with: the real `BaseSource` class body (copied verbatim from `sources/base.py`), the single-file naming convention, the two-step `main.py` registration pattern (import + instantiate), the `config.yaml` job schema, and a worked skeleton modeled on the simpler of the two existing source files. Populate **Instructions** with numbered steps covering: read base class → create source file → implement `get_batches()` → add import to `main.py` → add instantiation to `run_poc()` → add `config.yaml` entry → add MERGE index → test with `batch_size: 10`.

3. **Update `.ai-standards.md`** to add a `## AI Session Files` section (after existing sections, before any footer):
   ```markdown
   ## AI Session Files

   The `.session/` directory contains structured handoff files for AI coding agents.
   To add a new data source connector, start here:

       .session/add-connector.md

   Read that file completely before writing any code. It contains the BaseSource
   contract, file naming convention, main.py registration steps, and config.yaml
   schema.
   ```

4. **Append** the new section from the Relevant Specs outline above to `poc_walkthrough.ipynb` as a markdown cell group at the end of the notebook. Do not restructure or renumber existing cells.

5. **Do not** overwrite `.session/_template.md`.

6. **Do not** modify `importer.py`, `sources/base.py`, or either existing source file.

7. **Verify** the notebook opens cleanly: confirm no JSON syntax errors in the `.ipynb` file after editing (e.g. `python -c "import json; json.load(open('poc_walkthrough.ipynb'))"`).

---

## Decisions Made This Session

- Modeled the worked skeleton in `add-connector.md` on `BigQuerySource` (simpler of the two —
  no auth branching, just constructor args + lazy row iteration).
- Registration instructions describe the `build_source()` `elif` pattern (actual main.py
  structure) rather than a direct `run_poc()` instantiation, which matches the real code.
- No new pip dependencies introduced.