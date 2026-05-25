"""
Constraint Validators -- Layers 2 & 3

Layer 1 (schema) is handled by Pydantic model_validate().
Layer 2 (referential integrity) checks that IDs resolve across nodes.
Layer 3 (semantic invariants) checks domain-level correctness.

All validators are project-agnostic. They derive allowed ID prefixes
from the Registry, not from hardcoded constants.
"""

from __future__ import annotations

import re
from typing import TypedDict

from .nodes.node0 import Node0Output
from .nodes.node1 import Node1Output
from .nodes.node2 import Node2Output
from .nodes.node3 import GoalNode, Node3Output
from .nodes.node4 import Node4Output
from .primitives import Finding, FindingLevel


# -- Helpers ------------------------------------------------------------------


def _error(node: int, where: str, message: str, rule: str | None = None) -> Finding:
    return Finding(level=FindingLevel.ERROR, node=node, where=where, message=message, rule=rule)


def _warn(node: int, where: str, message: str, rule: str | None = None) -> Finding:
    return Finding(level=FindingLevel.WARN, node=node, where=where, message=message, rule=rule)


def _info(node: int, where: str, message: str, rule: str | None = None) -> Finding:
    return Finding(level=FindingLevel.INFO, node=node, where=where, message=message, rule=rule)


_AGG_PREFIX_RE = re.compile(r"^(?:E-|R-|O-)([A-Z]{2,4})-|^([A-Z]{2,4})-G")


def agg_prefix(id_: str) -> str | None:
    """Extract the AggCode prefix from a compound ID."""
    m = _AGG_PREFIX_RE.match(id_)
    if m:
        return m.group(1) or m.group(2)
    return None


# -- Tree helpers -------------------------------------------------------------


def collect_goal_ids(node: GoalNode) -> set[str]:
    """Recursively collect all goal IDs from the tree."""
    ids = {node.id}
    for child in node.children:
        ids |= collect_goal_ids(child)
    return ids


def collect_leaf_goals(node: GoalNode) -> set[str]:
    """Collect leaf goal IDs (no children)."""
    if not node.children:
        return {node.id}
    leaves: set[str] = set()
    for child in node.children:
        leaves |= collect_leaf_goals(child)
    return leaves


# -- Node 0 Constraints ------------------------------------------------------


def validate_node0(n0: Node0Output) -> list[Finding]:
    findings: list[Finding] = []
    codes: set[str] = set()

    for area in n0.registry.areas:
        if area.code in codes:
            findings.append(_error(0, f"Registry area {area.code}", "Duplicate area code", "L2-unique-area-codes"))
        codes.add(area.code)

    # dispatch plan areas should match registry
    registry_codes = {a.code for a in n0.registry.areas}
    for dp in n0.dispatch_plan:
        if dp.code not in registry_codes:
            findings.append(
                _error(0, f"Dispatch plan {dp.code}", "Area code not in registry", "L2-dispatch-matches-registry")
            )

    # L3: if persistence.database is not "none", schema_entities should be non-empty
    if n0.persistence.database.lower() != "none" and len(n0.schema_entities) == 0:
        findings.append(
            _warn(0, "Persistence", "Database declared but no schema entities found", "L3-schema-completeness")
        )

    return findings


# -- Node 1 Constraints ------------------------------------------------------


def validate_node1(n1: Node1Output, n0: Node0Output) -> list[Finding]:
    findings: list[Finding] = []
    valid_codes = {a.code for a in n0.registry.areas}
    event_index = {e.id: e for e in n1.events}

    for event in n1.events:
        # L2: area code prefix must be in registry
        prefix = agg_prefix(event.id)
        if prefix and prefix not in valid_codes:
            findings.append(
                _error(1, f"Event {event.id}", f"Area code '{prefix}' not in registry", "L2-event-area-code")
            )

        # L2: predecessor/successor IDs must resolve
        for pred in event.predecessors:
            if pred not in event_index:
                findings.append(
                    _error(1, f"Event {event.id}", f"Predecessor '{pred}' not found in catalogue", "L2-predecessor-resolves")
                )
        for succ in event.successors:
            if succ not in event_index:
                findings.append(
                    _error(1, f"Event {event.id}", f"Successor '{succ}' not found in catalogue", "L2-successor-resolves")
                )

        # L3: no self-referential links
        if event.id in event.predecessors:
            findings.append(
                _error(1, f"Event {event.id}", "Lists itself as predecessor", "L3-no-self-reference")
            )
        if event.id in event.successors:
            findings.append(
                _error(1, f"Event {event.id}", "Lists itself as successor", "L3-no-self-reference")
            )

        # L3: predecessor/successor symmetry
        for succ in event.successors:
            target = event_index.get(succ)
            if target and event.id not in target.predecessors:
                findings.append(
                    _warn(
                        1,
                        f"Event {event.id}",
                        f"Lists '{succ}' as successor, but '{succ}' doesn't list '{event.id}' as predecessor",
                        "L3-link-symmetry",
                    )
                )

    # L3: if fewer than 5 events, likely missed state changes
    if len(n1.events) < 5 and not n1.truncation:
        findings.append(
            _warn(1, "Event catalogue", f"Only {len(n1.events)} events found -- likely incomplete", "L3-minimum-events")
        )

    # L2: unique event IDs
    seen_ids: set[str] = set()
    for event in n1.events:
        if event.id in seen_ids:
            findings.append(_error(1, f"Event {event.id}", "Duplicate event ID", "L2-unique-event-ids"))
        seen_ids.add(event.id)

    return findings


# -- Node 2 Constraints ------------------------------------------------------


def validate_node2(n2: Node2Output, n1: Node1Output) -> list[Finding]:
    findings: list[Finding] = []
    event_index = {e.id for e in n1.events}
    agg_codes: set[str] = set()

    for agg in n2.aggregates:
        # L2: unique aggregate codes
        if agg.code in agg_codes:
            findings.append(_error(2, f"Aggregate {agg.code}", "Duplicate aggregate code", "L2-unique-agg-codes"))
        agg_codes.add(agg.code)

        # L2: transition events resolve to catalogue
        for t in agg.transitions:
            if t.event not in event_index:
                findings.append(
                    _error(
                        2,
                        f"Aggregate {agg.code}, transition {t.source}->{t.target}",
                        f"Event '{t.event}' not in Node 1 catalogue",
                        "L2-transition-event-resolves",
                    )
                )

        # L2: gap ID prefix matches aggregate code
        for gap in agg.gaps:
            prefix = gap.id.replace(re.search(r"-G\d+$", gap.id).group(), "") if re.search(r"-G\d+$", gap.id) else ""
            if prefix != agg.code:
                findings.append(
                    _error(2, f"Gap {gap.id}", f"Prefix '{prefix}' doesn't match aggregate '{agg.code}'", "L2-gap-prefix")
                )

        # L2: transition source/target must be declared states
        state_names = {s.name for s in agg.states}
        for t in agg.transitions:
            if t.source not in state_names:
                findings.append(
                    _error(2, f"Aggregate {agg.code}", f"Transition source '{t.source}' is not a declared state", "L2-state-exists")
                )
            if t.target not in state_names:
                findings.append(
                    _error(2, f"Aggregate {agg.code}", f"Transition target '{t.target}' is not a declared state", "L2-state-exists")
                )

        # L3: states with no outgoing transitions (dead ends) -- warn unless final
        for state in agg.states:
            if state.type == "final":
                continue
            has_outgoing = any(t.source == state.name for t in agg.transitions)
            if not has_outgoing:
                findings.append(
                    _warn(
                        2,
                        f"Aggregate {agg.code}, state '{state.name}'",
                        "No outgoing transitions (dead-end state)",
                        "L3-no-dead-ends",
                    )
                )

        # L2: unique state names within aggregate
        seen_states: set[str] = set()
        for state in agg.states:
            if state.name in seen_states:
                findings.append(_error(2, f"Aggregate {agg.code}", f"Duplicate state name '{state.name}'", "L2-unique-states"))
            seen_states.add(state.name)

    # L2: cross-aggregate transitions reference valid events and aggregates
    for cat in n2.cross_agg_transitions:
        if cat.from_event not in event_index:
            findings.append(
                _error(2, "Cross-agg transition", f"Event '{cat.from_event}' not in catalogue", "L2-cross-agg-event")
            )
        if cat.to_event not in event_index:
            findings.append(
                _error(2, "Cross-agg transition", f"Event '{cat.to_event}' not in catalogue", "L2-cross-agg-event")
            )
        if cat.from_aggregate not in agg_codes:
            findings.append(
                _error(2, "Cross-agg transition", f"Aggregate '{cat.from_aggregate}' not defined", "L2-cross-agg-code")
            )
        if cat.to_aggregate not in agg_codes:
            findings.append(
                _error(2, "Cross-agg transition", f"Aggregate '{cat.to_aggregate}' not defined", "L2-cross-agg-code")
            )

    # NOTE: gap-counts-match is now an L1 model_validator on GapSummary

    return findings


# -- Node 3 Constraints ------------------------------------------------------


def validate_node3(n3: Node3Output, n2: Node2Output) -> list[Finding]:
    findings: list[Finding] = []

    goal_ids = collect_goal_ids(n3.goal_tree)
    leaf_goals = collect_leaf_goals(n3.goal_tree)
    gap_index: dict[str, str] = {}
    for agg in n2.aggregates:
        for gap in agg.gaps:
            gap_index[gap.id] = gap.severity

    # Build obstacle index (both confirmed + new)
    obstacle_index: dict[str, dict] = {}
    for o in n3.confirmed_obstacles:
        obstacle_index[o.id] = {"severity": o.severity, "violates_goals": o.violates_goals}
    for o in n3.new_obstacles:
        obstacle_index[o.id] = {"severity": o.severity, "violates_goals": o.violates_goals}

    # L2: confirmed obstacles reference valid gaps
    for o in n3.confirmed_obstacles:
        if o.gap_source not in gap_index:
            findings.append(
                _error(3, f"Obstacle {o.id}", f"Gap source '{o.gap_source}' not found in Node 2", "L2-obstacle-gap-source")
            )

    # L2: obstacles reference valid goals
    for o in [*n3.confirmed_obstacles, *n3.new_obstacles]:
        for gid in o.violates_goals:
            if gid not in goal_ids:
                findings.append(
                    _error(3, f"Obstacle {o.id}", f"Goal '{gid}' not in goal tree", "L2-obstacle-goal-ref")
                )

    # L2: requirements resolve valid obstacles
    for req in n3.requirements:
        for oid in req.resolves:
            if oid not in obstacle_index:
                findings.append(
                    _error(3, f"Requirement {req.id}", f"Resolves '{oid}' which is not a defined obstacle", "L2-req-resolves")
                )

    # L2: phase requirements all exist
    req_index = {r.id for r in n3.requirements}
    for phase in n3.roadmap:
        for rid in phase.requirements:
            if rid not in req_index:
                findings.append(
                    _error(3, f"Phase {phase.number}", f"Requirement '{rid}' not defined", "L2-phase-req-exists")
                )

    # L3: CRITICAL severity -> at least one MUST requirement
    for oid, ob in obstacle_index.items():
        if ob["severity"] == "CRITICAL":
            has_musts = any(r.priority == "MUST" and oid in r.resolves for r in n3.requirements)
            if not has_musts:
                findings.append(
                    _warn(3, f"Obstacle {oid}", "CRITICAL severity but no MUST requirement resolves it", "L3-critical-needs-must")
                )

    # L3: every requirement should appear in at least one phase
    scheduled_reqs = {rid for phase in n3.roadmap for rid in phase.requirements}
    for req in n3.requirements:
        if req.id not in scheduled_reqs:
            findings.append(
                _warn(3, f"Requirement {req.id}", "Not scheduled in any roadmap phase", "L3-req-in-roadmap")
            )

    # L3: goal tree root is G0
    if n3.goal_tree.id != "G0":
        findings.append(_error(3, "Goal tree", f"Root is '{n3.goal_tree.id}', expected 'G0'", "L3-root-is-G0"))

    # L3: metrics match actual (totalGoals, leafGoals — needs tree traversal, can't be L1)
    actual_counts = {
        "totalGoals": len(goal_ids),
        "leafGoals": len(leaf_goals),
        "confirmedObstacles": len(n3.confirmed_obstacles),
        "newObstacles": len(n3.new_obstacles),
    }
    metric_fields = {
        "totalGoals": n3.metrics.total_goals,
        "leafGoals": n3.metrics.leaf_goals,
        "confirmedObstacles": n3.metrics.confirmed_obstacles,
        "newObstacles": n3.metrics.new_obstacles,
    }
    for key in actual_counts:
        if metric_fields[key] != actual_counts[key]:
            findings.append(
                _warn(3, "Metrics", f"'{key}' declared {metric_fields[key]}, actual {actual_counts[key]}", "L3-metrics-match")
            )

    # L2: unique obstacle IDs
    seen_obstacles: set[str] = set()
    for o in [*n3.confirmed_obstacles, *n3.new_obstacles]:
        if o.id in seen_obstacles:
            findings.append(_error(3, f"Obstacle {o.id}", "Duplicate obstacle ID", "L2-unique-obstacle-ids"))
        seen_obstacles.add(o.id)

    # L2: unique requirement IDs
    seen_reqs: set[str] = set()
    for r in n3.requirements:
        if r.id in seen_reqs:
            findings.append(_error(3, f"Requirement {r.id}", "Duplicate requirement ID", "L2-unique-req-ids"))
        seen_reqs.add(r.id)

    return findings


# -- Node 4 Constraints ------------------------------------------------------


def validate_node4(
    n4: Node4Output,
    n3: Node3Output,
    n2: Node2Output,
    n1: Node1Output,
) -> list[Finding]:
    findings: list[Finding] = []

    # Collect all requirement IDs from Node 3
    all_req_ids = {r.id for r in n3.requirements}

    # L2: file index references valid requirements
    for entry in n4.file_index:
        for rid in entry.requirements:
            if rid not in all_req_ids:
                findings.append(
                    _error(4, f"File index '{entry.file}'", f"Requirement '{rid}' not defined in Node 3", "L2-file-index-req")
                )

    # L3: every requirement should appear in file index
    indexed_reqs = {rid for e in n4.file_index for rid in e.requirements}
    for rid in all_req_ids:
        if rid not in indexed_reqs:
            findings.append(
                _warn(4, f"Requirement {rid}", "Not assigned to any file in File Index", "L3-req-in-file-index")
            )

    # L3: metrics consistency
    goal_ids = collect_goal_ids(n3.goal_tree)
    expected = {
        "totalGoals": len(goal_ids),
        "totalAggregates": len(n2.aggregates),
        "totalEvents": len(n1.events),
        "totalGaps": sum(len(a.gaps) for a in n2.aggregates),
        "confirmedObstacles": len(n3.confirmed_obstacles),
        "newObstacles": len(n3.new_obstacles),
        "totalRequirements": len(n3.requirements),
        "must": sum(1 for r in n3.requirements if r.priority == "MUST"),
        "should": sum(1 for r in n3.requirements if r.priority == "SHOULD"),
        "could": sum(1 for r in n3.requirements if r.priority == "COULD"),
        "phases": len(n3.roadmap),
        "filesIndexed": len(n4.file_index),
    }
    metric_map = {
        "totalGoals": n4.metrics.total_goals,
        "totalAggregates": n4.metrics.total_aggregates,
        "totalEvents": n4.metrics.total_events,
        "totalGaps": n4.metrics.total_gaps,
        "confirmedObstacles": n4.metrics.confirmed_obstacles,
        "newObstacles": n4.metrics.new_obstacles,
        "totalRequirements": n4.metrics.total_requirements,
        "must": n4.metrics.must,
        "should": n4.metrics.should,
        "could": n4.metrics.could,
        "phases": n4.metrics.phases,
        "filesIndexed": n4.metrics.files_indexed,
    }
    for key in expected:
        if metric_map[key] != expected[key]:
            findings.append(
                _warn(4, "Metrics", f"'{key}' declared {metric_map[key]}, actual {expected[key]}", "L3-metrics-consistency")
            )

    return findings


# -- Full Pipeline Validation -------------------------------------------------


class PipelineData(TypedDict, total=False):
    node0: Node0Output
    node1: Node1Output
    node2: Node2Output
    node3: Node3Output
    node4: Node4Output


class ValidationResult(TypedDict):
    valid: bool
    errors: int
    warnings: int
    infos: int
    findings: list[Finding]


def validate_pipeline(data: PipelineData) -> ValidationResult:
    """Run all constraint checks across the full pipeline.

    Can also run partial: pass only the nodes you have.
    """
    findings: list[Finding] = []

    n0 = data.get("node0")
    n1 = data.get("node1")
    n2 = data.get("node2")
    n3 = data.get("node3")
    n4 = data.get("node4")

    if n0:
        findings.extend(validate_node0(n0))
    if n1 and n0:
        findings.extend(validate_node1(n1, n0))
    if n2 and n1:
        findings.extend(validate_node2(n2, n1))
    if n3 and n2:
        findings.extend(validate_node3(n3, n2))
    if n4 and n3 and n2 and n1:
        findings.extend(validate_node4(n4, n3, n2, n1))

    errors = sum(1 for f in findings if f.level == FindingLevel.ERROR)
    warnings = sum(1 for f in findings if f.level == FindingLevel.WARN)
    infos = sum(1 for f in findings if f.level == FindingLevel.INFO)

    return ValidationResult(
        valid=errors == 0,
        errors=errors,
        warnings=warnings,
        infos=infos,
        findings=findings,
    )
