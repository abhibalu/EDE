"""
Assemblers -- Deterministic Fragment -> Node Output

These functions take validated fragments (from sub-agents) and produce
the final node output. All mechanical operations that LLMs do poorly:
- ID assignment (sequential, prefixed)
- Deduplication (by name + location)
- Name -> ID resolution (predecessors/successors)
- Count computation (metrics, summaries)

Every assembler returns AssembleResult(output, findings) where findings
captures any issues encountered during assembly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Generic, TypeVar

from .fragments import EventFragment, Node1Fragment, Node2Fragment, Node3Fragment
from .nodes.node1 import Node1Output
from .nodes.node2 import Node2Output
from .primitives import Finding, FindingLevel, HotSpot, Registry

T = TypeVar("T")


@dataclass
class AssembleResult(Generic[T]):
    output: T
    findings: list[Finding] = field(default_factory=list)


def _info(node: int, where: str, message: str, rule: str | None = None) -> Finding:
    return Finding(level=FindingLevel.INFO, node=node, where=where, message=message, rule=rule)


def _warn(node: int, where: str, message: str, rule: str | None = None) -> Finding:
    return Finding(level=FindingLevel.WARN, node=node, where=where, message=message, rule=rule)


# -- Node 1 Assembler ---------------------------------------------------------


def assemble_node1(
    registry: Registry,
    fragments: list[Node1Fragment],
    generated_at: datetime | None = None,
) -> AssembleResult[Node1Output]:
    findings: list[Finding] = []
    generated_at = generated_at or datetime.now(timezone.utc)

    # Step 1: Deduplicate
    seen: dict[str, tuple[str, EventFragment]] = {}  # key -> (areaCode, event)
    deduped_by_area: dict[str, list[EventFragment]] = {}

    for fragment in fragments:
        if fragment.area_code not in deduped_by_area:
            deduped_by_area[fragment.area_code] = []
        for event in fragment.events:
            key = f"{event.name}::{event.location.file}"
            if key in seen:
                original_area = seen[key][0]
                findings.append(
                    _info(1, f"Event {event.name}", f"Duplicate in '{fragment.area_code}', already in '{original_area}'", "ASSEMBLE-dedup")
                )
                continue
            seen[key] = (fragment.area_code, event)
            deduped_by_area[fragment.area_code].append(event)

    # Step 1.5: Per-area truncation (max 15 events per area)
    MAX_EVENTS_PER_AREA = 15
    truncation = None
    areas_truncated = []
    estimated_total = sum(len(evts) for evts in deduped_by_area.values())

    for area_code in list(deduped_by_area.keys()):
        if len(deduped_by_area[area_code]) > MAX_EVENTS_PER_AREA:
            areas_truncated.append(area_code)
            findings.append(
                _warn(
                    1,
                    f"Area {area_code}",
                    f"Area has {len(deduped_by_area[area_code])} events, "
                    f"truncated to {MAX_EVENTS_PER_AREA}",
                    "ASSEMBLE-area-truncation",
                )
            )
            deduped_by_area[area_code] = deduped_by_area[area_code][:MAX_EVENTS_PER_AREA]

    if areas_truncated:
        truncation = {
            "estimatedTotal": estimated_total,
            "areasAffected": areas_truncated,
        }

    # Step 2: Assign IDs
    name_to_id: dict[str, str] = {}
    for area_code, events in deduped_by_area.items():
        for idx, event in enumerate(events):
            name_to_id[event.name] = f"E-{area_code}-{idx + 1:02d}"

    # Step 3: Resolve names -> IDs, build final events
    all_events = []
    for area_code, events in deduped_by_area.items():
        for idx, event in enumerate(events):
            eid = f"E-{area_code}-{idx + 1:02d}"

            predecessors: list[str] = []
            for name in event.predecessor_names:
                resolved = name_to_id.get(name)
                if resolved:
                    predecessors.append(resolved)
                else:
                    findings.append(_warn(1, f"Event {event.name} ({eid})", f"Predecessor '{name}' not found", "ASSEMBLE-unresolved-predecessor"))

            successors: list[str] = []
            for name in event.successor_names:
                resolved = name_to_id.get(name)
                if resolved:
                    successors.append(resolved)
                else:
                    findings.append(_warn(1, f"Event {event.name} ({eid})", f"Successor '{name}' not found", "ASSEMBLE-unresolved-successor"))

            all_events.append({
                "id": eid,
                "name": event.name,
                "trigger": event.trigger,
                "location": {"file": event.location.file, "anchor": event.location.anchor},
                "predecessors": predecessors,
                "successors": successors,
                "stateChange": event.state_change,
                "evidence": event.evidence,
                "hotSpots": [{"description": h.description, "location": {"file": h.location.file, "anchor": h.location.anchor}} for h in event.hot_spots],
            })

    # Step 4: Enforce symmetry
    event_by_id = {e["id"]: e for e in all_events}
    for event in all_events:
        for succ_id in event["successors"]:
            succ = event_by_id.get(succ_id)
            if succ and event["id"] not in succ["predecessors"]:
                succ["predecessors"].append(event["id"])
                findings.append(_info(1, f"Event {succ['name']} ({succ['id']})", f"Auto-added predecessor '{event['id']}' for symmetry", "ASSEMBLE-symmetry-fix"))
        for pred_id in event["predecessors"]:
            pred = event_by_id.get(pred_id)
            if pred and event["id"] not in pred["successors"]:
                pred["successors"].append(event["id"])
                findings.append(_info(1, f"Event {pred['name']} ({pred['id']})", f"Auto-added successor '{event['id']}' for symmetry", "ASSEMBLE-symmetry-fix"))

    # Step 5: Build metadata
    scan_areas = []
    for fragment in fragments:
        area_dirs = []
        for a in registry.areas:
            if a.code == fragment.area_code:
                area_dirs = a.directories
                break
        scan_areas.append({
            "name": fragment.area_name,
            "areaCode": fragment.area_code,
            "directories": area_dirs,
            "filesScanned": fragment.files_scanned,
            "filesSkipped": fragment.files_skipped,
        })

    hot_spot_summary = []
    for e in all_events:
        hot_spot_summary.extend(e["hotSpots"])

    output_data = {
        "pipelineVersion": "0.1.0",
        "node": 1,
        "generatedAt": generated_at.isoformat(),
        "registry": registry.model_dump(by_alias=True),
        "metadata": {
            "totalFilesScanned": sum(len(f.files_scanned) for f in fragments),
            "scanAreas": scan_areas,
        },
        "events": all_events,
        "hotSpotSummary": hot_spot_summary,
        "truncation": truncation,
    }

    output = Node1Output.model_validate(output_data)
    return AssembleResult(output=output, findings=findings)


# -- Node 2 Assembler ---------------------------------------------------------


def assemble_node2(
    registry: Registry,
    fragments: list[Node2Fragment],
    node1: Node1Output,
    generated_at: datetime | None = None,
) -> AssembleResult[Node2Output]:
    findings: list[Finding] = []
    generated_at = generated_at or datetime.now(timezone.utc)

    event_name_to_id = {e.name: e.id for e in node1.events}

    aggregates = []
    for frag in fragments:
        transitions = []
        for t in frag.transitions:
            event_id = event_name_to_id.get(t.event_name)
            if not event_id:
                findings.append(_warn(2, f"{frag.agg_code} {t.source}->{t.target}", f"Event '{t.event_name}' not in catalogue", "ASSEMBLE-unresolved-event"))
            transitions.append({
                "source": t.source,
                "target": t.target,
                "event": event_id or f"UNRESOLVED:{t.event_name}",
                "guard": t.guard,
                "sideEffects": t.side_effects,
                "annotation": t.annotation,
                "evidence": t.evidence,
                "codeLocation": {"file": t.code_location.file, "anchor": t.code_location.anchor},
            })

        gaps = []
        for g in frag.gaps:
            gaps.append({
                "id": f"{frag.agg_code}-G{g.seq}",
                "severity": g.severity,
                "description": g.description,
                "codeLocation": {"file": g.code_location.file, "anchor": g.code_location.anchor},
            })

        states = []
        for s in frag.states:
            states.append({
                "name": s.name,
                "type": s.type,
                "representation": s.representation,
                "location": {"file": s.location.file, "anchor": s.location.anchor},
                "evidence": s.evidence,
            })

        aggregates.append({
            "code": frag.agg_code,
            "name": frag.agg_name,
            "rootEntity": frag.root_entity,
            "keyFiles": [{"file": kf.file, "anchor": kf.anchor} for kf in frag.key_files],
            "states": states,
            "transitions": transitions,
            "gaps": gaps,
            "trivialLifecycle": frag.trivial_lifecycle,
        })

    gap_summary = {"critical": 0, "high": 0, "med": 0, "low": 0, "total": 0}
    for agg in aggregates:
        for gap in agg["gaps"]:
            sev = gap["severity"].lower() if isinstance(gap["severity"], str) else gap["severity"].value.lower()
            gap_summary[sev] += 1
            gap_summary["total"] += 1

    output_data = {
        "pipelineVersion": "0.1.0",
        "node": 2,
        "generatedAt": generated_at.isoformat(),
        "registry": registry.model_dump(by_alias=True),
        "aggregates": aggregates,
        "crossAggTransitions": [],
        "impossibleCombinations": [],
        "migrationPriority": [],
        "gapSummary": gap_summary,
    }

    output = Node2Output.model_validate(output_data)
    return AssembleResult(output=output, findings=findings)


# -- Node 3 Assembler ---------------------------------------------------------
# Only handles forward analysis obstacle fragments. Goal tree, confirmed
# obstacles, requirements, and roadmap are Claude Code's analytical work.


def assemble_node3(
    fragments: list[Node3Fragment],
) -> AssembleResult[list[dict]]:
    """Merge obstacle fragments into a deduplicated list with O-N{seq} IDs.

    Returns assembled NewObstacle dicts (not a full Node3Output — that's
    Claude Code's job). Claude Code merges these into its analytical output.
    """
    findings: list[Finding] = []

    # Deduplicate by description + evidence (same obstacle found by multiple sub-agents)
    seen: dict[str, dict] = {}  # dedup key -> obstacle dict
    for frag in fragments:
        for obs in frag.new_obstacles:
            key = f"{obs.description}::{obs.evidence}"
            if key in seen:
                findings.append(_info(3, f"Obstacle '{obs.description[:40]}...'", f"Duplicate from '{frag.agg_code}', already seen", "ASSEMBLE-dedup"))
                continue
            seen[key] = {
                "violatesGoals": obs.violates_goals,
                "evidence": obs.evidence,
                "description": obs.description,
                "severity": obs.severity.value if hasattr(obs.severity, "value") else obs.severity,
                "resolutionType": obs.resolution_type.value if hasattr(obs.resolution_type, "value") else obs.resolution_type,
            }

    # Assign globally sequential O-N IDs
    obstacles = []
    for seq, (_, obs_dict) in enumerate(seen.items(), start=1):
        obs_dict["id"] = f"O-N{seq}"
        obstacles.append(obs_dict)

    findings.append(_info(3, "Node 3 assembly", f"Assembled {len(obstacles)} new obstacles from {len(fragments)} fragments", "ASSEMBLE-summary"))

    return AssembleResult(output=obstacles, findings=findings)
