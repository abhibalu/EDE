# Node 1 — Domain Event Extraction

## Purpose
Extract a structured catalogue of every domain event — every meaningful state change — in this codebase. The output feeds Node 2 (statechart extraction).

## Input
Read the Node 0 reconnaissance output from `docs/pipeline/output/00-recon.md` to understand the codebase structure and sub-agent dispatch plan.

## What Counts as a Domain Event

✅ INCLUDE:
- State transitions: a status field changes value (e.g., `status = "generated"`)
- Entity lifecycle moments: creation, completion, deletion, archival
- Business decisions: an agent/algorithm produces a verdict, score, or classification
- External interactions: an API called that changes external state (TTS, uploads, sends)
- User actions with domain significance: approval, rejection, selection, configuration

❌ EXCLUDE:
- Pure reads / queries / fetches that don't change state
- Internal technical operations (middleware, logging, caching)
- UI rendering, component mounting, style changes
- Generic CRUD with no domain name — prefer "SessionGenerated" over "Row Inserted"

## Execution Strategy — Use Sub-Agents

### Step 1: Plan dispatch
Read the Node 0 output. Use its "Directory Map for Sub-Agent Dispatch" to decide how many sub-agents to spawn and what directories each one covers.

### Step 2: Dispatch sub-agents
Spawn one sub-agent per scan area. Give each sub-agent the Sub-Agent Prompt below with the appropriate target directory.

### Step 3: Assemble
Collect all sub-agent outputs. Then you:
1. Deduplicate events found by multiple sub-agents
2. Fill in cross-area predecessor/successor links
3. Group events by entity/domain area
4. Draw the Event Flow Summary
5. Compile the Hot Spot Summary

---

## Sub-Agent Prompt

```
You are extracting domain events from a specific area of a codebase.

SCAN AREA: [SCAN_AREA_NAME]
TARGET: [TARGET_DIRECTORY]

A domain event is a past-tense record of a meaningful state change. For EACH source file in your target directory:

1. Open the file. Look for: database writes (INSERT/UPDATE/DELETE), status field mutations, external API calls that change state (uploads, sends, creates), enum/state transitions, event emissions.
2. For each state change, produce an event entry in the format below.
3. If a file has no state changes, skip it.

INCLUDE as domain events:
- Status field changes (e.g., status = "generated")
- Entity lifecycle: creation, completion, deletion, archival
- Agent/algorithm verdicts, scores, classifications
- External API calls that change state (TTS generation, file uploads, email sends)
- User actions with domain significance (selections, approvals, configuration)

EXCLUDE (not domain events):
- Pure reads/queries/fetches
- Technical internals (middleware, logging, caching, auth checks)
- UI rendering, component mounting, CSS
- Generic CRUD with no domain name

For each event, output this EXACT format:

#### [EventName]
- **Trigger**: [what causes this, imperative mood]
- **Location**: `[filepath:function_name]`
- **Predecessor events**: [what must happen before, or "None identified"]
- **Successor events**: [what typically happens after, or "None identified"]
- **State change**: [what data changes, from what to what]
- **Hot spots**: [🔴 + description, or "None"]

EXAMPLE:

#### AudioMixedWithAmbient
- **Trigger**: Mix TTS audio with ambient background (called after TTS generation completes)
- **Location**: `backend/app/services/audio_mixer.py:mix_with_ambient`
- **Predecessor events**: SpeechGenerated
- **Successor events**: MixedAudioUploaded
- **State change**: Raw TTS bytes → combined MP3 with ambient overlay at specified volume
- **Hot spots**: 🔴 Silent fallback — try/except returns raw TTS on any mixing failure. The caller never knows mixing failed. No logging of the failure cause.

Flag 🔴 hot spots when you see:
- Missing error handling / silent fallbacks (try/except that swallows errors)
- Implicit state (boolean flag combos instead of explicit status)
- Temporal coupling (A must happen before B but nothing enforces it)
- Dead code / unreachable state changes
- TODO/FIXME/HACK near state changes

CONSTRAINTS:
- Every event must trace to a real file and function. Do NOT invent events.
- Do NOT suggest fixes. Read-only extraction.
- List files you scanned at the top of your response.
- If you find 0 events, say so explicitly — do not pad with non-events.
```

---

## Output Format

Your first line must be `# Domain Event Catalogue`. No preamble.

```markdown
# Domain Event Catalogue

## System Overview
- **Repo**: [name]
- **Primary language(s)**: [languages]
- **Persistence layer**: [database/storage]
- **Sub-agents dispatched**: [count and scan areas]
- **Total files scanned**: [sum across sub-agents]

## Event Catalogue

### [Entity/Area Name] Events

---

#### [EventName]
- **Trigger**: [cause]
- **Location**: `[filepath:function_name]`
- **Predecessor events**: [what before]
- **Successor events**: [what after]
- **State change**: [what changes]
- **Hot spots**: [🔴 or "None"]
- **Found by**: [which sub-agent/scan area]

---

(repeat for each event, grouped by entity/area)

## Event Flow Summary

(ASCII arrows showing happy-path sequence across all areas)

## Cross-Area Dependencies

| Predecessor (area) | Successor (area) | Integration seam |
|--------------------|------------------|-----------------|
| [event (area)] | [event (area)] | [API endpoint or mechanism] |

## Hot Spot Summary

(All 🔴 flags, sorted by severity, one sentence each)

## Dead Code Events

(Any fully implemented but unreachable event handlers found)
```

## Constraints
- Every event must trace to a specific file and function.
- Do NOT include framework internals unless they implement domain logic.
- Do NOT suggest fixes. Read-only extraction.
- Cap at 50 events. If more exist, note: "Catalogue truncated at 50. ~[N] additional events in [areas]."
- If fewer than 5 events found, re-scan — you likely missed state changes.
- Your first line of output must be `# Domain Event Catalogue`. No preamble or project overview.
