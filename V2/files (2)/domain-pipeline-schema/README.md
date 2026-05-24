# @ootomic/domain-pipeline-schema

Formal grammar for the 5-node domain extraction pipeline. Defines the intermediate representation (IR) that flows between nodes, with three-layer validation.

## Architecture

```
Code (ephemeral)
  ↓
Node 0 → JSON  ──→  Validator L1+L2
  ↓
Node 1 → JSON  ──→  Validator L1+L2+L3 (needs Node 0)
  ↓
Node 2 → JSON  ──→  Validator L1+L2+L3 (needs Node 1)
  ↓
Node 3 → JSON  ──→  Validator L1+L2+L3 (needs Node 2)
  ↓
Node 4 → JSON  ──→  Validator L1+L2+L3 (needs all prior)
  ↓
Renderer → Markdown (human-readable spec)
```

The code is never stored. Only the JSON artifacts persist. Node 4 adds the file index and computes metrics; a separate renderer produces the human-readable markdown.

## Three Validation Layers

| Layer | What | How | When |
|-------|------|-----|------|
| L1 — Schema | Structural validity | `NodeNOutput.parse(data)` | Per-node, immediate |
| L2 — Referential | IDs resolve across nodes | `validateNodeN(current, previous)` | At node boundary |
| L3 — Semantic | Domain-level correctness | Same validators, different rules | At node boundary |

See `CONSTRAINT_RULES.md` for the complete rule catalogue.

## Usage

```typescript
import { Node1Output, validateNode1, validatePipeline } from '@ootomic/domain-pipeline-schema';

// Layer 1: parse and validate structure
const node1 = Node1Output.parse(rawJsonFromLLM);

// Layer 2 + 3: cross-reference checks
const result = validateNode1(node1, node0);
if (result.some(f => f.level === 'ERROR')) {
  // reject and re-prompt the LLM
}

// Full pipeline validation
const fullResult = validatePipeline({ node0, node1, node2, node3, node4 });
```

## Design Decisions

**Why JSON intermediates, not markdown?**
Nodes 0–3 are consumed by the next LLM in the chain, not by humans. JSON is unambiguous, parseable, and validatable. Markdown is only produced at the rendering stage (after Node 4).

**Why Zod, not JSON Schema?**
Single source of truth: TypeScript types at compile time + runtime validation from the same definition. Refinements (constraint rules) compose naturally. JSON Schema can be exported for external tooling when needed.

**Why a Registry?**
The pipeline is project-agnostic. No hardcoded aggregate codes. Node 0 establishes the registry; every subsequent ID is built from it. A new project gets a new registry — grammar, validators, and constraints are unchanged.

**Why an `evidence` field?**
Events (Node 1) and states (Node 2) are factual claims about code. The evidence field is the ReAct grounding contract: it forces the LLM to record what it actually observed in the code before asserting a state change exists. An ungrounded claim fails L1 validation.

**Why CodeRef as `{ file, anchor }` not `"file:line"`?**
LLMs are inconsistent with delimiter formats. Explicit fields eliminate parsing ambiguity and make file-existence checks trivial for the CLI tool.

## File Structure

```
src/
  primitives.ts        # ID patterns, CodeRef, Registry, enums
  nodes/
    node0.ts           # Recon output schema
    node1.ts           # Event catalogue (with evidence for ReAct)
    node2.ts           # Statechart analysis (state evidence)
    node3.ts           # Goal tree, obstacles, requirements
    node4.ts           # Compiled spec + file index
  constraints.ts       # L2 + L3 validators, per-node and full-pipeline
  index.ts             # Public API
  test.ts              # Positive smoke test
  test-negative.ts     # Negative tests (broken references, bad formats)

CONSTRAINT_RULES.md    # Human-readable rule catalogue
```

## Next Steps

1. **Updated node prompts**: each prompt includes the Zod type definition for its output, instructing the LLM to produce JSON conforming to the schema
2. **Per-node validation in the pipeline runner**: validate at each boundary, re-prompt on L1/L2 errors
3. **Renderer module**: transforms Node 4 JSON → markdown spec (replaces current Node 4 prompt)
4. **CLI tool**: `ootomic-pipeline run --repo ./my-app --output ./pipeline-results/`
5. **ReAct protocol for Node 1**: Thought→Action→Observation loop with the evidence field as the grounding target
