# Formal Language Theory Through the Lens of EDE

How the Domain Extraction Engine implements concepts from automata theory, the Chomsky hierarchy, and compiler architecture -- without anyone planning it that way.

---

## 1. The Language Your System Speaks

When EDE runs `validate_pipeline()` and returns `valid: true` or `valid: false`, it is solving the oldest problem in theoretical computer science: **the membership problem**.

A *formal language* is a set of strings. Not English sentences -- any set of sequences over some alphabet. The **membership problem** asks: given a string, does it belong to the language?

EDE's language is the set of all JSON documents that pass the three membership layers -- L1, L2, and L3. (L4 exists and is discussed in Section 14, but it is deliberately not part of this definition: it asks a question no grammar can ask.) A specific Node 2 JSON blob is a "string." The alphabet is the set of characters that can appear in valid JSON, but more usefully, EDE's effective alphabet is the set of all valid field values: enum members like `"CRITICAL"`, ID strings like `"E-US-01"`, integers, booleans, and the structural tokens (`{`, `}`, `[`, `]`) that compose them.

The membership oracle is `validate_pipeline()` (`constraints.py:457`). It takes a `PipelineData` dictionary and returns a `ValidationResult` with a binary verdict. In `cli.py:66-70`, L1 failure raises `Exit(1)`. In `cli.py:86-87`, L2/L3 errors do the same. Accept or reject. This binary decision is the fundamental operation of every automaton in the theory.

Here is the key insight that structures everything that follows: **not all membership checks are equally hard**. Checking whether a string matches `^E-[A-Z]{2,4}-\d{1,3}$` requires almost no memory. Checking whether a `GoalNode` tree is well-formed requires tracking nesting depth. Checking whether `"E-US-02"` is a valid predecessor requires scanning a completely different part of the document. Each of these requires a more powerful computational mechanism. That hierarchy of power is the Chomsky hierarchy, and it is why EDE has three membership layers.

---

## 2. Grammars as Generators -- What Pydantic Models Actually Are

A formal grammar has four components:

1. **Terminals** -- the literal symbols that appear in valid output
2. **Nonterminals** -- named categories that expand into sequences of terminals and other nonterminals
3. **Production rules** -- rules that define how each nonterminal expands
4. **Start symbol** -- the nonterminal where derivation begins

EDE's Pydantic models map directly onto this:

**Terminals** are the concrete values: enum members (`"CRITICAL"`, `"HIGH"`, `"MED"`, `"LOW"` from `primitives.py:74-78`), literal values (`"0.1.0"` in `PipelineEnvelope`), and any string matching an ID regex. These are the atoms that cannot be broken down further.

**Nonterminals** are the model classes. `Aggregate`, `GoalNode`, `Node2Output` -- each is a named category that expands into a combination of fields. When you write `class Aggregate(EdeBaseModel)` with its fields, you are writing a production rule.

**Production rules** are the field definitions. Consider `Node2Output` (`node2.py:106-113`):

```
Node2Output -> PipelineEnvelope
             + aggregates: list[Aggregate]
             + cross_agg_transitions: list[CrossAggTransition]
             + impossible_combinations: list[ImpossibleCombination]
             + migration_priority: list[MigrationCandidate]
             + gap_summary: GapSummary
```

This is a production rule in BNF-like notation. It says: a `Node2Output` is composed of a pipeline envelope, one or more aggregates, zero or more cross-aggregate transitions, and so on. Each referenced nonterminal (`Aggregate`, `GapSummary`) has its own production rule expanding it further.

**Start symbol** is the specific `NodeNOutput` for each pipeline stage, or more globally, `PipelineData` which encompasses all nodes.

`model_validate()` performs the inverse of generation: **parsing**. Given a string (a JSON blob), it determines whether that string can be derived from the start symbol using the production rules. If yes, it returns the **parse tree** -- which is the validated model instance, with every field typed and every nesting level resolved. If no, it raises `ValidationError`. This is exactly what a parser does in compiler theory.

---

## 3. The Chomsky Hierarchy -- Why Three Membership Layers Exist

EDE's three membership layers are not an arbitrary design choice. They correspond to three distinct levels of the Chomsky hierarchy, each requiring a strictly more powerful computational mechanism to check. A fourth layer, L4, sits outside this hierarchy entirely; Section 14 explains why.

The hierarchy is a nested sequence of language classes, each strictly containing the one below:

- **Type 3 (Regular languages):** Patterns you can check by scanning left-to-right with fixed, finite memory. The machine: a finite automaton (DFA/NFA). No stack, no tape. Just a current state and an input symbol.

- **Type 2 (Context-free languages):** Patterns that require matching nested structure. The machine: a pushdown automaton (PDA). A finite automaton plus a stack that can grow without bound.

- **Type 1 (Context-sensitive languages):** Patterns where the validity of one part depends on what appears elsewhere in the string. The machine: a linear bounded automaton (LBA). A Turing machine whose tape is limited to the length of the input.

- **Type 0 (Recursively enumerable):** Anything a Turing machine can recognize. Unrestricted. Potentially non-terminating.

EDE's layers map as follows:

| Layer | Chomsky Type | Mechanism | Example |
|-------|-------------|-----------|---------|
| L1 (regex) | Type 3 -- Regular | DFA | `^E-[A-Z]{2,4}-\d{1,3}$` |
| L1 (schema) | Type 2 -- Context-free | PDA | `GoalNode.children: list[GoalNode]` |
| L2 | Type 1 -- Context-sensitive | LBA | `validate_node2(n2, n1)` |
| L3 | Type 1 (with domain semantics) | LBA | `L3-critical-needs-must` |

Each level requires a **strictly more powerful** machine. You cannot check context-sensitive properties with a context-free parser. This is not a limitation of Pydantic's implementation; it is a mathematical impossibility proven by the hierarchy.

This is why `architecture-decisions.md:12` reads: *"Do NOT collapse L2/L3 into `@model_validator` -- those checks need data from other nodes."* That decision is not just engineering preference. A `@model_validator` has access only to the data within its own model instance. That is context-free scope. But L2 checks need data from other models. That is context-sensitive scope. The decision to keep them separate is forced by the Chomsky hierarchy.

---

## 4. Regular Languages -- The Machines Behind ID Patterns

Open `primitives.py:43-44`:

```python
EventID = Annotated[str, StringConstraints(pattern=r"^E-[A-Z]{2,4}-\d{1,3}$")]
```

This regular expression defines a **regular language**: the set of all strings that match the pattern. By **Kleene's theorem** (1956), every regular expression has an equivalent deterministic finite automaton (DFA), and vice versa. They are exactly equal in power.

The DFA for `EventID` works like this in prose: start in an initial state. Read `E` -- transition to state 1. Read `-` -- state 2. Read an uppercase letter -- state 3 (one letter seen). Read another -- state 4 (two seen; this is already a valid area code length). Optionally read one or two more uppercase letters (states 5, 6). Then read `-` -- transition to the digit-reading states. Read one to three digits, ending in an accept state. Any unexpected character at any point transitions to a dead reject state.

The critical property: **fixed, finite memory**. The machine has a bounded number of states. It never needs to "remember" anything from earlier in the string beyond which state it currently occupies. It processes one character at a time, left to right, and decides.

EDE defines six ID patterns (`primitives.py:39-61`), each a regular language:

| Pattern | Regex | What the DFA tracks |
|---------|-------|-------------------|
| `AggCode` | `^[A-Z]{2,4}$` | Count of uppercase letters (2-4) |
| `EventID` | `^E-[A-Z]{2,4}-\d{1,3}$` | Prefix `E-`, area code length, digit count |
| `GapID` | `^[A-Z]{2,4}-G\d{1,3}$` | Area code length, literal `G`, digit count |
| `GoalID` | `^G\d{1,2}(\.\d{1,2})?$` | Literal `G`, digit count, optional dot-digits |
| `ObstacleID` | `^O-([A-Z]{2,4}\|XA)-\d{1,3}$\|^O-N\d{1,3}$` | Two alternate paths (confirmed vs new) |
| `ReqID` | `^R-([A-Z]{2,4}\|XA)-\d{1,3}$` | Same as ObstacleID but with `R-` prefix |

Each pattern is a separate DFA. When Pydantic validates an `EventID` field, it compiles the regex and runs the equivalent automaton against the input string. This is L1 validation for individual tokens.

**What regular languages cannot do.** They cannot count to arbitrary depth. They cannot match balanced parentheses. And critically for EDE: they cannot verify that an ID referenced in one place *exists* in another place. The question "Is `E-US-02` a valid predecessor?" cannot be answered by scanning the predecessor field alone. You need to look at the event catalogue defined elsewhere in the document. This is why regex validation is L1 only.

The **pumping lemma** gives the intuition: if a language is regular, then any sufficiently long string in it contains a section that can be "pumped" (repeated) while staying in the language. But consider the constraint "every ID in a `predecessors` list must exist in the `events` list." You cannot pump any part of a predecessor reference and guarantee it still exists in the catalogue. The dependency between two separate parts of the document breaks regularity. This is a context-sensitive property, and no finite automaton can check it.

---

## 5. Context-Free Languages -- GoalNode's Recursive Secret

Look at `node3.py:37-43`:

```python
class GoalNode(EdeBaseModel):
    id: GoalID
    description: str = Field(min_length=1)
    decomposition: GoalDecomposition | None
    agent: str | None
    children: list[GoalNode] = []
    obstacle_refs: list[ObstacleID] = []
```

Line 42 is the key: `children: list[GoalNode]`. A `GoalNode` contains `GoalNodes`. This is **direct recursion** -- a production rule that references itself:

```
GoalNode -> GoalID description decomposition? agent? GoalNode*
```

The set of all valid `GoalNode` JSON trees is a **context-free language**. No regular expression can describe it, because regular languages cannot match structures nested to arbitrary depth. A regex for "balanced JSON braces containing GoalNode objects" would need to count opening and closing braces, which requires unbounded memory -- exactly what a DFA lacks.

A **pushdown automaton (PDA)** is a finite automaton equipped with a stack. The stack provides the unbounded memory that nesting requires. When you encounter an opening `{` for a child GoalNode, push onto the stack. When you encounter the matching `}`, pop. If the stack is empty at the end and the automaton is in an accept state, the tree is well-formed. The stack depth tracks the nesting depth -- something no DFA can do.

Line 46, `GoalNode.model_rebuild()`, is Pydantic's mechanism for handling this. Forward-referencing a class within its own definition requires special handling at the Python type level, but conceptually it is defining a context-free grammar with a self-referencing production rule.

The recursive tree walkers in `constraints.py:54-69` make this explicit:

```python
def collect_goal_ids(node: GoalNode) -> set[str]:
    ids = {node.id}
    for child in node.children:
        ids |= collect_goal_ids(child)
    return ids
```

This function is a tree traversal -- the standard algorithm for processing context-free parse trees. The Python call stack during execution mirrors the PDA's stack. Each recursive call pushes a frame; each return pops one. The recursion in the validation code is a direct implementation of the pushdown automaton.

**Why L1 promotions work within this framework.** The checks promoted from L3 to L1 -- `GapSummary.check_total()` (`node2.py:98-103`), `Node3Metrics.check_totals()` (`node3.py:102-109`), and `NewObstacle.check_new_prefix()` (`node3.py:67-71`) -- could be promoted precisely because they are **intra-model**. They only reference data within the same model instance. `GapSummary.check_total` verifies that `total == critical + high + med + low` using only fields of `GapSummary` itself. This is a context-free check: the validation depends only on the structure of the current subtree. The boundary between what can and cannot live in L1 is exactly the boundary between context-free and context-sensitive.

---

## 6. Context-Sensitive Languages -- Why L2 Cannot Live Inside Pydantic

Open `constraints.py:183-191`:

```python
for t in agg.transitions:
    if t.event not in event_index:
        findings.append(
            _error(2, f"Aggregate {agg.code}, transition {t.source}->{t.target}",
                   f"Event '{t.event}' not in Node 1 catalogue",
                   "L2-transition-event-resolves")
        )
```

This is `L2-transition-event-resolves`. It checks that every transition's `event` field in Node 2 references an `EventID` that exists in Node 1's event catalogue. The `event_index` on line 173 was built from Node 1: `event_index = {e.id for e in n1.events}`. The validity of a value in Node 2 depends on the content of Node 1.

In formal terms, this is a **context-sensitive** constraint. Context-sensitive grammars have production rules of the form `alpha A beta -> alpha gamma beta` -- the replacement of nonterminal `A` depends on its surrounding context (`alpha` and `beta`). In EDE terms: whether `"E-OR-02"` is valid in a transition's event field depends on the context of the entire Node 1 event catalogue.

The machine that recognizes context-sensitive languages is the **linear bounded automaton (LBA)**: a Turing machine whose tape is bounded by the length of the input. It can scan back and forth across the entire input, using the input itself as working memory. This is exactly what the L2 validators do. They scan across multiple node outputs (the "tape"), building indices and checking cross-references.

Every L2 validator follows the same pattern:

1. Build an index from a prior node: `event_index = {e.id for e in n1.events}`
2. Iterate over the current node's references
3. Check that each reference resolves in the index

This is a two-pass scan: first pass builds the index, second pass checks membership. It is the LBA pattern -- scanning the tape to build state, then scanning again to verify.

The progressive dependency structure of `validate_pipeline()` (`constraints.py:457-491`) makes the context-sensitivity explicit:

```python
if n0:          findings.extend(validate_node0(n0))
if n1 and n0:   findings.extend(validate_node1(n1, n0))
if n2 and n1:   findings.extend(validate_node2(n2, n1))
if n3 and n2:   findings.extend(validate_node3(n3, n2))
if n4 and n3 and n2 and n1:  findings.extend(validate_node4(n4, n3, n2, n1))
```

Each validator needs access to prior nodes. The "context" grows with each stage. `validate_node4` needs **four** prior nodes -- the largest context window in the pipeline. This growing context requirement is the signature of context-sensitive computation.

Every L2 rule in `constraint-rules.md:28-52` follows the same structural pattern: "value X in node N must exist as a key in node M." There are 20 such rules. Each one is a context-sensitive cross-reference check that no amount of Pydantic schema engineering can express within a single model.

---

## 7. L3 -- Semantic Analysis and the Limits of Syntax

L2 checks structural well-formedness: do references resolve? L3 checks something different: does this make **domain sense**?

Consider `L3-critical-needs-must` (`constraints.py:312-319`):

```python
for oid, ob in obstacle_index.items():
    if ob["severity"] == "CRITICAL":
        has_musts = any(r.priority == "MUST" and oid in r.resolves for r in n3.requirements)
        if not has_musts:
            findings.append(_warn(3, f"Obstacle {oid}",
                "CRITICAL severity but no MUST requirement resolves it",
                "L3-critical-needs-must"))
```

A document could pass L1 (all IDs well-formed) and L2 (all IDs resolve) while violating this rule. A CRITICAL obstacle with only COULD requirements is syntactically valid but semantically suspicious. The validator is no longer checking structure -- it is checking meaning.

In compiler theory, this is the **semantic analysis** phase. The lexer tokenizes, the parser builds a syntax tree, and the semantic analyzer checks properties that depend on meaning: type compatibility, scope rules, and domain invariants. EDE's L3 is semantic analysis.

In formal language theory, **attribute grammars** (Knuth, 1968) extend context-free grammars by attaching computed attributes to nonterminals. L3 is computing *synthesized attributes* -- values computed from child nodes and propagated upward -- then checking their consistency. `collect_goal_ids()` synthesizes the set of all goal IDs from the tree. `L3-metrics-match` (`constraints.py:333-350`) computes actual counts by traversing the data and compares them to declared metrics. The validator is computing attributes and verifying that they agree.

The ERROR vs WARN distinction (`constraints.py:28-33`) maps to the hard/soft error distinction in compilers. L2 violations produce ERROR: the document is structurally broken. L3 violations produce WARN: the document is structurally valid but possibly wrong. A type error in C is fatal. A signed/unsigned comparison warning is not. EDE makes the same distinction.

Critically, L3 remains **decidable and terminating**. It does not venture into undecidable territory. Every L3 check is a finite, deterministic computation over the validated data: count items, compare counts, check severity-priority alignment, detect dead-end states. No unbounded search. No Turing-completeness.

---

## 8. The Compiler Analogy

The parallel between EDE and a compiler front-end is exact:

**Lexer** = regex/enum checks (L1 token validation). In a compiler, the lexer converts a raw character stream into tokens using regular expressions (DFAs). In EDE, the regex patterns on ID types and enum constraints play this role. `EventID`'s regex pattern is a DFA that tokenizes event identifiers. `Severity`'s enum is a finite set of valid tokens. Both are Type 3 (regular) checks.

**Parser** = `model_validate()` (L1 structural validation). The parser checks that tokens form valid syntactic structures according to a grammar. Pydantic's `model_validate()` does exactly this: it checks that JSON fields have the right types, required fields are present, nested objects conform to their schemas, and recursive structures like `GoalNode` are well-formed. This is context-free parsing.

**Semantic analyzer** = L2/L3 validators (cross-reference and domain checks). The semantic analyzer checks meaning-dependent properties that syntax alone cannot capture. In EDE, these are the cross-node referential integrity checks and domain invariants.

The complete flow:

```
Compiler:  source code -> [lexer] -> tokens -> [parser] -> AST -> [semantic] -> annotated AST
EDE:       JSON blob   -> [regex]  -> typed   -> [model]  -> model -> [L2/L3] -> validated
                          [enum]     fields     [validate]  instance             pipeline
```

EDE's `__init__.py:4` describes the system as *"Formal grammar and validators for the 5-node domain extraction pipeline."* The word "grammar" is not metaphorical. It is technically precise.

The model instance is the **intermediate representation (IR)** -- the structured output of parsing that the semantic analyzer operates on. In a compiler, the AST is the IR. In EDE, the Pydantic model instance is the IR.

This analogy clarifies two architectural decisions:

1. **L1 promotions work** because the promoted checks were always context-free. `GapSummary.check_total()` is like moving a simple type check from the semantic analyzer into the parser. It works because the check is local to the current subtree.

2. **L2 cannot be promoted** because cross-node references are context-sensitive. It is like checking that a variable is declared before use. The parser processes one file; the semantic analyzer needs the symbol table from all files. A `@model_validator` processes one model; L2 needs the indices from all prior nodes.

---

## 9. Machines Within Machines -- Node 2's FSMs

Node 2's `Aggregate` model (`node2.py:58-67`) is a data structure that **encodes a finite state machine**:

```python
class Aggregate(EdeBaseModel):
    code: AggCode
    name: str
    root_entity: str
    key_files: list[CodeRef]
    states: list[StateEntry]      # <- the FSM's state set
    transitions: list[Transition]  # <- the FSM's transition function
    gaps: list[Gap]
    trivial_lifecycle: bool = False
```

`states` is the set Q. `transitions` defines the function delta. The `StateType` enum (`primitives.py:87-91`) -- `atomic`, `compound`, `parallel`, `final` -- references Harel's statechart formalism, which extends basic finite automata with hierarchy and concurrency.

This creates a **meta-circular** structure: EDE uses formal language theory mechanisms (regex DFAs, schema PDAs, constraint LBAs) to validate data that **itself describes finite automata**. The validators validate the validators' subject matter.

When `L3-no-dead-ends` (`constraints.py:214-227`) checks for non-final states with no outgoing transitions, it is performing **liveness analysis** on the described FSM. A dead-end state is a state from which no further progress is possible. Detecting dead-end states is a property of the state machine being described, checked by the state-machine-like validation machinery. Machines analyzing machines.

`CrossAggTransition` (`node2.py:69-74`) represents **composition** of state machines. When the User aggregate's activation event enables Order creation, that is an inter-machine dependency. The L2 rules `L2-cross-agg-event` and `L2-cross-agg-code` validate that these cross-machine links are well-formed. This is EDE validating the composition of the automata it describes.

`TransitionAnnotation` (`primitives.py:94-96`) adds another layer. `DISCOVERED` means the transition was found in the actual codebase. `PROPOSED` means it was hypothesized as a missing behavior. This is metadata about the relationship between the described FSM and the real system -- a level of abstraction above the machine itself. EDE is not just describing automata; it is describing the epistemology of those automata.

---

## 10. Assemblers as Transducers

A **finite state transducer (FST)** is like a finite automaton but it produces output as well as consuming input. For each input symbol, it emits an output symbol (or sequence). It transforms one language into another.

EDE's assemblers transform fragments (a language of ID-free, name-linked structures) into node outputs (a language of ID-assigned, ID-linked structures). This is a language-to-language transformation -- the defining property of a transducer.

Walk through `assemble_node1()` (`assemblers.py:46-187`) as a transducer:

**Step 1 (Deduplicate, lines 54-70):** The transducer scans the input fragment stream and emits each event only if not previously seen. The `seen` dictionary is internal state. This is a *stateful filter* -- a transducer that sometimes emits and sometimes suppresses.

**Step 2 (Assign IDs, lines 98-102):** For each event in each area, emit `E-{area_code}-{idx+1:02d}`. The output depends on both the current input (the event) and the current state (the sequential counter `idx`). In automata theory, this is a **Mealy machine** -- a transducer where the output depends on the current state and the current input.

**Step 3 (Resolve names -> IDs, lines 104-136):** Replace each `predecessor_name` with the corresponding `EventID` from the `name_to_id` lookup table. This is a **substitution transduction**: replace each token in the input language with a token in the output language, using a fixed mapping.

**Step 4 (Enforce symmetry, lines 138-150):** If event A lists B as a successor, ensure B lists A as a predecessor. This is a **fixpoint computation** on the output -- it iterates until no more changes are needed. This goes slightly beyond a single-pass FST, but it is still deterministic and terminating because the event set is finite and each iteration can only add links (never remove them), so it must converge.

The word "deterministically" in `architecture-decisions.md:14` is doing heavy theoretical lifting. It means the assembler is a **function**, not a relation. Given the same input fragments, it always produces exactly the same output. No nondeterminism. No LLM involvement. Pure mechanical transformation -- exactly what transducers provide.

---

## 11. The Pipeline as a State Machine

The five-node pipeline is itself a finite state machine:

```
[Start] -> Node0 -> Node1 -> Node2 -> Node3 -> Node4 -> [Accept]
             |        |        |        |        |
             v        v        v        v        v
          [Retry]  [Retry]  [Retry]  [Retry]  [Retry]
```

Each node is a state. The transition from one state to the next has a **guard condition**: validation must pass. If `ede validate` returns errors, the pipeline stays in the current state and re-attempts. This is the retry loop described in `architecture-decisions.md:47-54` -- Claude Code reads findings, fixes its output, and re-validates. The retry is a self-loop on the current state, not a backward transition.

`validate_pipeline()` (`constraints.py:457-479`) encodes the dependency DAG. The progressive conditionals -- `if n1 and n0`, `if n2 and n1`, `if n3 and n2`, `if n4 and n3 and n2 and n1` -- formalize the state ordering. Node 2 cannot be validated without Node 1. Node 4 cannot be validated without Nodes 1, 2, and 3.

Registry propagation (`primitives.py:135-139`) is the **state variable** that carries forward through every transition. `PipelineEnvelope` includes `registry: Registry`. Established at Node 0, never modified, carried immutably in every node's output. In automata terms, it is a component of the state that is set once and read at every subsequent transition. The registry is the pipeline's persistent memory.

---

## 12. Decidability and Termination -- What EDE Guarantees

A **decidable** problem is one where an algorithm exists that always halts with the correct YES/NO answer for any input. EDE's validation is decidable. For any JSON input, the validator will terminate in finite time with either VALID or INVALID. This is not trivially guaranteed -- there exist languages where membership is undecidable (the halting problem being the canonical example).

The termination argument for each layer:

**L1 (Pydantic):** `model_validate()` iterates over a finite schema. Regex matching terminates because DFAs process finite strings in O(n). `GoalNode` recursion terminates because JSON documents are finite trees -- there are no cycles, and the depth is bounded by the document size. The Python call stack during `collect_goal_ids()` (`constraints.py:54-59`) is bounded by tree depth, which is bounded by document size.

**L2 (Constraint validators):** Each validator iterates over finite lists, builds finite dictionaries, and performs finite lookups. There are no `while` loops, no unbounded recursion (tree traversal is bounded as above), and no external I/O. The computational complexity is O(n^2) in the worst case (quadratic in the number of IDs, due to cross-reference checking), which is comfortably polynomial.

**L3 (Semantic validators):** Same structure as L2. Finite iteration over finite data with finite computations. No unbounded search, no recursion beyond tree traversal.

**The pipeline:** Terminates because it is a finite linear chain of 5 nodes, each checked once.

EDE's 46 rules (15 L1, 20 L2, 11 L3) all terminate by construction. EDE maintains decidability by intentionally avoiding:

- **Arbitrary code execution** in validators (no eval, no dynamic rule loading)
- **Graph-recursive types** (`GoalNode` is tree-recursive, not graph-recursive -- no cycles allowed in the data)
- **External state dependencies** (no network calls, no filesystem reads during validation)
- **Dynamic constraint learning** (all 46 rules are static Python code)

These constraints keep EDE below the Turing-complete threshold. It could express more if it allowed general computation, but it would lose the guarantee that validation always terminates.

---

## 13. Why the Layers Cannot Be Collapsed

Restating in automata terms:

- L1 regex checks: recognized by **DFA** (finite automaton)
- L1 schema validation: recognized by **PDA** (pushdown automaton)
- L2 cross-node validation: recognized by **LBA** (linear bounded automaton)
- L3 semantic validation: also recognized by LBA, with domain interpretation
- L4 path verification: **not an automaton at all** -- an oracle query (Section 14)

The **strict power hierarchy**: DFA < PDA < LBA < TM. Each class recognizes strictly more languages than the one below it. This is not a conjecture; it is proven.

The practical implication is mathematical: **a `@model_validator` cannot implement L2 checks**. A model validator has access to the data within its own model instance. This is context-free scope -- the validator sees one subtree of the parse tree. But L2 checks need data from other models. This is context-sensitive scope -- the validator needs to compare subtrees from different parts of the overall structure. No amount of clever Pydantic engineering can bridge this gap. It is like trying to match `a^n b^n c^n` with a context-free grammar -- the language is provably not context-free.

`architecture-decisions.md:42` explicitly rejects this: *"`@model_validator` for all L2/L3"* with the reason *"Only true for intra-model checks. Cross-node validation cannot be model validators."* The architecture document is stating a consequence of the Chomsky hierarchy.

The L1 promotions (`architecture-decisions.md:24-31`) are the mirror case. `GapSummary.check_total()`, `Node3Metrics.check_totals()`, and `NewObstacle.check_new_prefix()` were moved **down** the hierarchy. They were implemented at L3 in V2 (the Zod version), but they were always context-free -- they only reference fields within their own model. Moving them to `@model_validator` places them at the correct hierarchy level. These promotions do not collapse the hierarchy; they correct a V2 implementation that placed checks too high.

---

## 14. L4 -- The Layer Outside the Language

Sections 1 through 13 describe three layers, and that is deliberate: L1, L2,
and L3 are the layers that decide **membership**. Each asks a closed question
about a string -- does this document belong to the language? Each is answerable
by inspecting the document and nothing else. That is exactly what places them
on the Chomsky hierarchy at all.

L4 is not on the hierarchy, and the reason is not that it is harder. It is that
it asks a different kind of question.

Consider `L4-path-missing`. The claim under test is that `events[3].location.file`
names a file that exists. Nothing in the document can settle this. Two documents
that are byte-identical -- indistinguishable to any grammar, any automaton, any
parser -- can disagree on this predicate, because the answer lives in the
filesystem rather than in the string.

In logical terms, L1 through L3 are **proof-theoretic**: they ask whether a
string is derivable from a grammar. L4 is **model-theoretic**: it asks whether
the names in a string denote anything under an interpretation. The filesystem
*is* the interpretation. Without fixing one, "the language of JSON documents
whose file paths exist" does not name a language at all -- membership is not a
function of the string.

Two consequences follow, and both are visible in the code.

**L4 is parameterized by a snapshot.** Every verifier takes `repo_root: Path`
as an argument, because the predicate is meaningless without it. The same
artifact validated against two commits can produce different findings, and
neither is wrong. L1 through L3 need no such parameter -- their answers depend
only on the artifact.

**L4 findings are `WARN`, never `ERROR`.** This looks like a severity choice
and is really a soundness one. An L2 violation is a proof that the document is
malformed, and that proof does not expire. An L4 violation is an observation
about the world at a moment: the file may have been renamed, moved, or deleted
after a correct extraction. Promoting it to a hard error would assert a
certainty the check cannot supply.

None of this makes L4 the weak layer. It is the only layer that can catch the
failure the other three are structurally blind to. L1 through L3 can certify a
document in which every single path was invented, because such a document can
be perfectly self-consistent -- and a model producing fluent, coherent,
entirely fabricated references is not a hypothetical failure mode. Internal
consistency is exactly what a language-membership check certifies, and exactly
what a confident fabrication supplies.

The grammar tells you the artifact is well-formed. Only an oracle tells you it
is about the code.

---

## 15. What EDE Intentionally Cannot Express

Every formal system has an expressiveness boundary. EDE's boundary is carefully chosen to guarantee decidability while covering the validation needs of the domain extraction pipeline.

**No temporal ordering.** L2 can check that event IDs exist, but cannot verify that events happened in a particular temporal order in the actual codebase. Temporal properties require runtime traces -- a fundamentally different input than static JSON documents.

**No behavioral equivalence.** L2 can verify that a state machine's transitions are syntactically well-formed, but cannot verify that the described state machine actually matches the behavior of the code it models. Behavioral equivalence of programs is undecidable in general, by Rice's theorem: any non-trivial semantic property of programs is undecidable.

**No completeness of extraction.** L3 can warn about suspiciously few events (`L3-minimum-events`, `constraints.py:153-156`: "Only N events found -- likely incomplete"). But it cannot guarantee that all domain events were found. Completeness of program analysis is undecidable -- you cannot prove that you have found everything without solving the halting problem.

**No cyclic goal dependencies.** `GoalNode` is tree-structured (`node3.py:37-43`), preventing cycles by construction. Goals that might have mutual dependencies in reality must be linearized into a tree. This is a deliberate expressiveness trade-off: trees are context-free (recognizable by PDA), while general graphs with cycle detection would require context-sensitive computation even at L1.

**No dynamic constraints.** All 46 rules are static Python code in `constraints.py`. The system cannot learn new constraints from data. This keeps validation deterministic and reviewable -- every rule is human-auditable -- at the cost of requiring code changes to add new rules.

Each limitation traces back to a known result in computability theory. EDE accepts them because the alternative -- a more expressive but potentially non-terminating validation system -- would undermine the core guarantee that `ede validate` always returns a definitive answer.

---

## 16. Where to Go From Here

The concepts in this document connect to a deep body of theory. Here are entry points for further study, organized by the sections they extend:

**Foundations (Sections 1-3):** Michael Sipser, *Introduction to the Theory of Computation* (3rd ed., Cengage). The standard graduate text. Chapters 1-5 cover everything from DFAs through decidability. Sipser's presentation is unusually clear, and every concept in this document has a corresponding formal treatment there.

**Automata in Depth (Sections 4-6):** Hopcroft, Motwani & Ullman, *Introduction to Automata Theory, Languages, and Computation* (3rd ed., Pearson). More detailed than Sipser on automata constructions. Chapter 4 on context-free grammars and Chapter 9 on undecidability are particularly relevant to Sections 5 and 15.

**Compiler Architecture (Section 8):** Aho, Lam, Sethi & Ullman, *Compilers: Principles, Techniques, and Tools* (2nd ed., "The Dragon Book"). Chapters 2-6 cover the lexer-parser-semantic-analyzer pipeline that EDE mirrors. Chapter 5 on syntax-directed translation formalizes the attribute grammar concept mentioned in Section 7.

**Statecharts (Section 9):** David Harel, "Statecharts: A Visual Formalism for Complex Systems" (1987). The original paper that introduced the compound/parallel/hierarchy extensions to flat state machines. Node 2's `StateType` enum directly references this formalism. Available as Harel (1987), *Science of Computer Programming* 8(3), pp. 231-274.

**KAOS Goal Modeling (Section 5 and Node 3):** Axel van Lamsweerde, *Requirements Engineering: From System Goals to UML Models to Software Specifications* (Wiley, 2009). EDE's Node 3 goal tree is a KAOS model. The book formalizes how goals decompose into sub-goals, how obstacles threaten goals, and how requirements resolve obstacles -- exactly the structure that `GoalNode`, `ConfirmedObstacle`, and `Requirement` encode.

**Transducers (Section 10):** Berstel, *Transductions and Context-Free Languages* (Teubner, 1979). The formal theory behind the assembler-as-transducer analogy. More accessible: the Wikipedia article on "Finite-state transducer" gives the essential definitions.

**Decidability (Sections 12, 15):** Sipser again, Chapters 4-5. Rice's theorem (Section 15) is in Chapter 5. The key takeaway: EDE stays below the Turing-complete threshold on purpose, and the theory explains exactly what it gives up in exchange for guaranteed termination.

---

*This document maps the EDE codebase to formal language theory and automata. It is a companion to `architecture-decisions.md` (which records the engineering decisions) and `constraint-rules.md` (which catalogues the validation rules). Together, the three documents answer: what rules exist, why the architecture is the way it is, and what theoretical framework underlies both.*
