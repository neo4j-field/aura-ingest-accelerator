# aura-ingest-accelerator

A modular Python-based ingestion framework designed for rapid Neo4j Aura prototyping. This library provides a scalable quick-start alternative to distributed ETL jobs, allowing for secure, high-performance data loading from GCS and BigQuery within VPC environments. Features include batch-optimized Cypher execution, pre-load data transformations, modular datasources

---

## Quick Start

```sh
git clone https://github.com/pdrangeid/aura-ingest-accelerator
cd aura-ingest-accelerator
source activate_env.sh
uv pip install -e .[dev]
cp .env.example .env  # fill in credentials
```

## Documentation

- `ARCHITECTURE.md` — system design and component overview
- `docs/usage_instructions.md` — detailed usage guide

## License

MIT
