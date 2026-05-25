# Node 1 — Domain Event Extraction

## Purpose
Extract a structured catalogue of every domain event — every meaningful state change — in this codebase. The output feeds Node 2 (statechart extraction).

## Input
Read the Node 0 output JSON from `docs/pipeline/runs/{RUN_DATE}/00-recon.json`. Use its registry and dispatch plan.

## What Counts as a Domain Event

INCLUDE:
- State transitions: a status field changes value (e.g., `status = "generated"`)
- Entity lifecycle moments: creation, completion, deletion, archival
- Business decisions: an agent/algorithm produces a verdict, score, or classification
- External interactions: an API call that changes external state (TTS, uploads, sends)
- User actions with domain significance: approval, rejection, selection, configuration

EXCLUDE:
- Pure reads / queries / fetches that don't change state
- Internal technical operations (middleware, logging, caching)
- UI rendering, component mounting, style changes
- Generic CRUD with no domain name — prefer "SessionGenerated" over "Row Inserted"

## Output Schema

The final output is a single JSON object. No markdown. No preamble.

```typescript
interface Node1Output {
  pipelineVersion: "0.1.0";
  node: 1;
  generatedAt: string;
  registry: Registry;                // carried forward from Node 0

  metadata: {
    totalFilesScanned: number;
    scanAreas: ScanArea[];
  };
  events: DomainEvent[];             // max 15 per area
  hotSpotSummary: HotSpot[];
  truncation: {                      // null if no area exceeded 15 events
    estimatedTotal: number;
    areasAffected: string[];
  } | null;
}

interface ScanArea {
  name: string;
  areaCode: string;                  // must match registry area code
  directories: string[];
  filesScanned: string[];            // every file actually opened
  filesSkipped: string[];            // files skipped and why
}

interface DomainEvent {
  id: string;                        // format: E-{AreaCode}-{seq} e.g. "E-MS-01"
  name: string;                      // PascalCase, past tense e.g. "AudioMixedWithAmbient"
  trigger: string;                   // what causes this, imperative mood
  location: CodeRef;
  predecessors: string[];            // EventIDs that must happen before, or []
  successors: string[];              // EventIDs that typically happen after, or []
  stateChange: string;               // what data changes, from what to what
  evidence: string;                  // REQUIRED — see ReAct Protocol below
  hotSpots: HotSpot[];
}

interface CodeRef {
  file: string;                      // filepath relative to repo root
  anchor: string;                    // function name or line number
}

interface HotSpot {
  description: string;
  location: CodeRef;
}
```

## Execution Strategy — Sub-Agents with ReAct Protocol

### Step 1: Plan dispatch
Read the Node 0 output. Use its `dispatchPlan` to decide sub-agent assignments.

### Step 2: Dispatch sub-agents
Spawn one sub-agent per scan area. Give each sub-agent the **Sub-Agent Prompt** below. Each sub-agent follows the ReAct protocol.

### Step 3: Output Fragments
Each sub-agent writes its fragment JSON to `docs/pipeline/runs/{RUN_DATE}/fragments/node1/{AREA_CODE}.json`.

Do NOT deduplicate, assign EventIDs, or compile the final catalogue yourself.
Run the assembler:

```
ede assemble --fragments-dir docs/pipeline/runs/{RUN_DATE}/fragments/node1/ --node 1 --registry-file docs/pipeline/runs/{RUN_DATE}/00-recon.json --output docs/pipeline/runs/{RUN_DATE}/01-events.json
```

The assembler handles:
- Deduplication (by event name + file location)
- Sequential ID assignment (E-{code}-01, E-{code}-02, ...)
- Cross-area predecessor/successor resolution (name -> EventID)
- Symmetry enforcement (if A->B successor, B gets A as predecessor)
- Hot spot summary compilation

Then validate:
```
ede validate --node0 docs/pipeline/runs/{RUN_DATE}/00-recon.json --node1 docs/pipeline/runs/{RUN_DATE}/01-events.json
```

Fix any errors the validator reports, then proceed to Node 2.

---

## Sub-Agent Prompt

```
You are extracting domain events from a specific area of a codebase.
You MUST follow the ReAct protocol: every claim about code must be grounded in an observation.

SCAN AREA: [SCAN_AREA_NAME]
AREA CODE: [AREA_CODE]
TARGET: [TARGET_DIRECTORIES]

## ReAct Protocol

You work in a loop of THOUGHT → ACTION → OBSERVATION → THOUGHT.

ACTIONS available to you:
- READ_FILE <filepath>         — read a source file's contents
- SEARCH <pattern> <directory> — search for a text pattern across files

RULES:
1. Before claiming any state change exists, you MUST have an OBSERVATION showing the relevant code.
2. The `evidence` field of every event MUST be a direct excerpt from an OBSERVATION — the actual code you saw.
3. If you cannot find evidence for a suspected event, do NOT include it. No observation = no event.
4. Record EVERY file you open in your filesScanned list, even if it yielded no events.

## Protocol Execution

PHASE 1 — SURVEY
THOUGHT: I need to understand what files exist in my scan area.
ACTION: List the files in [TARGET_DIRECTORIES].
OBSERVATION: [file list]
THOUGHT: Based on filenames, these files likely contain state changes: [list with reasoning]

PHASE 1.5 — FILTER
THOUGHT: Before reading full files, I'll narrow candidates using state-change patterns.
ACTION: SEARCH for these patterns in [TARGET_DIRECTORIES]:
  - `status\s*=` or `status:` (status field assignments)
  - `.create(` or `.insert(` (entity creation)
  - `.update(` or `.upsert(` (entity mutation)
  - `.emit(` or `dispatch(` or `publish(` (event emission)
  - `setState` or `state =` (direct state changes)
  - `.delete(` or `.destroy(` (entity lifecycle end)
OBSERVATION: [files matching each pattern]
THOUGHT: Based on pattern matches, I can prioritize:
  - HIGH priority (multiple patterns matched): [files]
  - LOW priority (no matches but in target dir): [files]
  - SKIP (no matches, utility/helper name): [files]

Proceed to PHASE 2 with HIGH priority files first, then LOW priority.
Files marked SKIP still go into filesSkipped with reason "no state-change patterns found".

PHASE 2 — EXTRACT (repeat for each candidate file)
THOUGHT: I'm examining [filename] looking for state changes — database writes, status mutations, external API calls, enum transitions, event emissions.
ACTION: READ_FILE [filepath]
OBSERVATION: [file contents]
THOUGHT: I found [N] state changes in this file:
  - Line [X]: [description of what I see]
  - Line [Y]: [description of what I see]
  (or: No state changes found in this file.)

For each state change found, construct an event entry with the evidence populated from the observation.

PHASE 3 — LINK
THOUGHT: Now I connect predecessor/successor relationships based on what I observed across files. [Event A] must happen before [Event B] because [reasoning grounded in code].

## Large Area Protocol

If your scan area has >20 candidate files after PHASE 1 (SURVEY):
1. Split your extraction into multiple fragments.
2. Name them: `{AREA_CODE}_part1.json`, `{AREA_CODE}_part2.json`, etc.
3. Each fragment MUST be a valid Node1Fragment with the same areaCode and areaName.
4. Distribute files across parts — each file should appear in exactly one part's filesScanned.
5. The assembler handles merging: it iterates all fragments, deduplicates by name::file,
   and assigns IDs globally. Multiple fragments with the same area_code merge naturally.

If ≤20 candidate files, produce a single `{AREA_CODE}.json` as normal.

PHASE 4 — EMIT
Produce the sub-agent output JSON (schema below).

After writing your fragment JSON, validate it:
  ede validate-fragment --node 1 --fragment docs/pipeline/runs/{RUN_DATE}/fragments/node1/{AREA_CODE}.json
If validation fails, read the error output, fix your JSON, and re-validate.

## What to look for in code

Database writes: INSERT, UPDATE, DELETE, .create(), .update(), .upsert(), .delete()
Status mutations: status =, setState, state =, .status =
External API calls that change state: .send(), .upload(), .generate(), .create() on external SDKs
Enum/state transitions: switch/case on status, if (status ===)
Event emissions: .emit(), dispatch(), publish(), trigger()

## What to SKIP

Pure reads: .find(), .select(), .get(), .query(), .fetch() with no subsequent write
Technical internals: middleware, logging, caching, auth checks
UI rendering: component mounting, CSS, style changes
Generic CRUD: if the operation has no domain-specific name, skip it

## Hot Spots — flag with 🔴 when you see:
- Missing error handling / silent fallbacks (try/except that swallows errors)
- Implicit state (boolean flag combos instead of explicit status)
- Temporal coupling (A must happen before B but nothing enforces it)
- Dead code / unreachable state changes
- TODO/FIXME/HACK near state changes

## Sub-Agent Output Schema (Fragment)

Produce JSON matching the Node1Fragment schema. Note: use event NAMES for linking,
not IDs. The assembler resolves names to EventIDs.

{
  "areaCode": "[AREA_CODE]",
  "areaName": "[SCAN_AREA_NAME]",
  "filesScanned": ["every file you opened"],
  "filesSkipped": ["files skipped with reason"],
  "events": [
    {
      "name": "PascalCasePastTense",
      "trigger": "what causes this",
      "location": { "file": "path/to/file.ts", "anchor": "functionName" },
      "predecessorNames": [],
      "successorNames": [],
      "stateChange": "from what -> to what",
      "evidence": "ACTUAL CODE from your observation, e.g. 'Line 42: await db.session.update({ status: \"generated\" })'",
      "hotSpots": []
    }
  ]
}

Run `ede schema --fragment node1` to regenerate this if the schema changes.

### Fragment Schema

```json
{
  "$defs": {
    "CodeRef": {
      "properties": {
        "file": { "minLength": 1, "type": "string" },
        "anchor": { "minLength": 1, "type": "string" }
      },
      "required": ["file", "anchor"],
      "type": "object"
    },
    "EventFragment": {
      "properties": {
        "name": { "pattern": "^[A-Z][a-zA-Z0-9]+$", "type": "string" },
        "trigger": { "minLength": 1, "type": "string" },
        "location": { "$ref": "#/$defs/CodeRef" },
        "predecessorNames": { "items": { "type": "string" }, "type": "array" },
        "successorNames": { "items": { "type": "string" }, "type": "array" },
        "stateChange": { "minLength": 1, "type": "string" },
        "evidence": { "minLength": 10, "type": "string" },
        "hotSpots": { "items": { "$ref": "#/$defs/HotSpot" }, "type": "array" }
      },
      "required": ["name", "trigger", "location", "predecessorNames", "successorNames", "stateChange", "evidence", "hotSpots"],
      "type": "object"
    },
    "HotSpot": {
      "properties": {
        "description": { "minLength": 1, "type": "string" },
        "location": { "$ref": "#/$defs/CodeRef" }
      },
      "required": ["description", "location"],
      "type": "object"
    }
  },
  "properties": {
    "areaCode": { "pattern": "^[A-Z]{2,4}$", "type": "string" },
    "areaName": { "minLength": 1, "type": "string" },
    "filesScanned": { "items": { "type": "string" }, "minItems": 1, "type": "array" },
    "filesSkipped": { "items": { "type": "string" }, "type": "array" },
    "events": { "items": { "$ref": "#/$defs/EventFragment" }, "type": "array" }
  },
  "required": ["areaCode", "areaName", "filesScanned", "filesSkipped", "events"],
  "type": "object"
}
```

### Common Schema Mistakes

Your output MUST parse against the fragment schema. These mistakes will cause assembly to fail:

- `hotSpots` must be objects: `{"description": "...", "location": {"file": "...", "anchor": "..."}}` -- NOT plain strings
- `predecessorNames` / `successorNames` are event NAME strings (e.g. `"UserActivated"`), not EventIDs (not `"E-US-02"`)
- `evidence` must be at least 10 characters of actual code observed -- not a summary
- `name` must be PascalCase matching `^[A-Z][a-zA-Z0-9]+$`
- `location` must be an object `{"file": "...", "anchor": "..."}` -- NOT a string

CONSTRAINTS:
- Every event must trace to a file you READ and code you SAW. No invented events.
- The evidence field must contain actual code -- not a description of what you think exists.
- If you find 0 events, say so explicitly and return an empty events array.
- Do NOT suggest fixes. Read-only extraction.
```

---

## Constraints
- Every event must trace to a specific file and function with code evidence.
- Do NOT include framework internals unless they implement domain logic.
- Do NOT suggest fixes. Read-only extraction.
- Per-area cap of 15 events. The assembler truncates areas exceeding 15 and populates the `truncation` field.
- If fewer than 5 events found across all areas, re-scan — you likely missed state changes.
- Output ONLY the final JSON object. No markdown wrapping. No explanation.
- Any event without a non-empty `evidence` field must be discarded during assembly.
