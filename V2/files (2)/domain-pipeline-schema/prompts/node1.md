# Node 1 — Domain Event Extraction

## Purpose
Extract a structured catalogue of every domain event — every meaningful state change — in this codebase. The output feeds Node 2 (statechart extraction).

## Input
Read the Node 0 output JSON from `docs/pipeline/output/00-recon.json`. Use its registry and dispatch plan.

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
  events: DomainEvent[];             // max 50
  hotSpotSummary: HotSpot[];
  truncation: {                      // null if ≤50 events
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

### Step 3: Assemble
Collect all sub-agent outputs. Then you:
1. Deduplicate events found by multiple sub-agents
2. Fill in cross-area predecessor/successor links (using EventIDs)
3. Assign sequential IDs per area (E-{code}-01, E-{code}-02, ...)
4. Compile the hotSpotSummary
5. Verify every event has a non-empty `evidence` field. Any event without evidence is DISCARDED.
6. Produce the final JSON.

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

PHASE 4 — EMIT
Produce the sub-agent output JSON (schema below).

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

## Sub-Agent Output Schema

Produce JSON:

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
      "predecessors": [],
      "successors": [],
      "stateChange": "from what → to what",
      "evidence": "ACTUAL CODE from your observation, e.g. 'Line 42: await db.session.update({ status: \"generated\" })'",
      "hotSpots": []
    }
  ]
}

CONSTRAINTS:
- Every event must trace to a file you READ and code you SAW. No invented events.
- The evidence field must contain actual code — not a description of what you think exists.
- If you find 0 events, say so explicitly and return an empty events array.
- Do NOT suggest fixes. Read-only extraction.
```

---

## Constraints
- Every event must trace to a specific file and function with code evidence.
- Do NOT include framework internals unless they implement domain logic.
- Do NOT suggest fixes. Read-only extraction.
- Cap at 50 events. If more exist, populate the `truncation` field.
- If fewer than 5 events found across all areas, re-scan — you likely missed state changes.
- Output ONLY the final JSON object. No markdown wrapping. No explanation.
- Any event without a non-empty `evidence` field must be discarded during assembly.
