# EDE Pipeline Execution

## Setup

Ensure `ede` is installed: `pip install -e /path/to/EDE`

## Running the pipeline

Execute nodes sequentially. After each node, validate before proceeding.

### Node 0 -- Reconnaissance

1. Read `prompts/node0.md` for instructions.
2. Scan the codebase structure (2 levels deep), config files, schema files.
3. Write JSON output to `pipeline/output/00-recon.json`
4. Run: `ede validate --node0 pipeline/output/00-recon.json`
5. If errors: read findings, fix the JSON, re-validate until clean.

### Node 1 -- Event Extraction

1. Read `prompts/node1.md` for instructions.
2. Read `pipeline/output/00-recon.json` for registry and dispatch plan.
3. For each scan area: read source files, extract events with evidence.
4. Write sub-agent fragments to `pipeline/output/fragments/node1/`
5. Run: `ede assemble --fragments-dir pipeline/output/fragments/node1/ --node 1 --registry-file pipeline/output/00-recon.json --output pipeline/output/01-events.json`
6. Run: `ede validate --node0 pipeline/output/00-recon.json --node1 pipeline/output/01-events.json`
7. Run: `ede coverage --node0 pipeline/output/00-recon.json --node1 pipeline/output/01-events.json`
8. If errors: fix and re-validate.

### Node 2 -- Statechart Extraction

1. Read `prompts/node2.md` for instructions.
2. Read `pipeline/output/01-events.json` for event catalogue.
3. For each aggregate: discover states (read code for evidence), map transitions, find gaps.
4. Write fragments to `pipeline/output/fragments/node2/`
5. Run: `ede assemble --fragments-dir pipeline/output/fragments/node2/ --node 2 --registry-file pipeline/output/00-recon.json --node1-file pipeline/output/01-events.json --output pipeline/output/02-statecharts.json`
6. Run: `ede validate --node0 pipeline/output/00-recon.json --node1 pipeline/output/01-events.json --node2 pipeline/output/02-statecharts.json`
7. If errors: fix and re-validate.

### Node 3 -- Goal Tree & Obstacles

1. Read `prompts/node3.md` for instructions.
2. Read `pipeline/output/02-statecharts.json` for aggregates and gaps.
3. Build goal tree, map obstacles, generate requirements.
4. Write output to `pipeline/output/03-goals.json`
5. Run: `ede validate --node0 pipeline/output/00-recon.json --node1 pipeline/output/01-events.json --node2 pipeline/output/02-statecharts.json --node3 pipeline/output/03-goals.json`
6. If errors: fix and re-validate.

### Node 4 -- Spec Assembly

1. Read `prompts/node4.md` for instructions.
2. Read ALL prior outputs (00 through 03).
3. Build file index, compute metrics, render markdown spec.
4. Write JSON to `pipeline/output/04-spec.json`, markdown to `docs/domain-spec.md`.
5. Final validation: `ede validate --node0 pipeline/output/00-recon.json --node1 pipeline/output/01-events.json --node2 pipeline/output/02-statecharts.json --node3 pipeline/output/03-goals.json --node4 pipeline/output/04-spec.json`

## Key rules

- Every event and state entry MUST have an `evidence` field with actual code observed.
- Events without evidence are invalid and will fail validation.
- Use `ede schema --node N` to check the expected output schema if unsure.
- Fragment files are intermediate -- the assembled output is what gets validated and stored.
