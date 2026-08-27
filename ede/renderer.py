"""
Deterministic Markdown Renderer -- Zero LLM cost.

Reads all 5 node outputs and produces a human-readable domain specification.
No Jinja2 dependency -- pure f-strings and list comprehensions.
"""

from __future__ import annotations

from .nodes.node0 import Node0Output
from .nodes.node1 import Node1Output
from .nodes.node2 import Node2Output, Aggregate
from .nodes.node3 import GoalNode, Node3Output
from .nodes.node4 import Node4Output


def render_markdown(
    node0: Node0Output,
    node1: Node1Output,
    node2: Node2Output,
    node3: Node3Output,
    node4: Node4Output,
) -> str:
    """Render the complete markdown domain specification from 5 node outputs."""
    event_by_id = {e.id: e for e in node1.events}
    req_by_id = {r.id: r for r in node3.requirements}
    all_obstacles = {o.id: o for o in node3.confirmed_obstacles}
    all_obstacles.update({o.id: o for o in node3.new_obstacles})

    sections = [
        _header(node0, node4),
        _how_to_use(node0.identity.repo),
        _notation_guide(),
        _system_purpose(node4),
        _goal_tree(node3),
        _aggregate_reference(node2, node3, event_by_id, req_by_id),
        _cross_aggregate(node2, node3, req_by_id),
        _obstacle_register(node3),
        _requirements_delta(node3),
        _roadmap(node3, req_by_id),
        _file_index(node4),
        _metrics(node4),
        _changelog(node4),
    ]

    return "\n\n---\n\n".join(sections) + "\n"


# -- Section Renderers --------------------------------------------------------


def _header(node0: Node0Output, node4: Node4Output) -> str:
    return f"""# {node0.identity.repo} — Domain Specification

> **Generated**: {node4.generated_at.strftime("%Y-%m-%d")}
> **Pipeline**: 5-node domain extraction v{node4.pipeline_version}
> **Status**: Baseline"""


def _how_to_use(repo: str) -> str:
    return f"""## How to Use This Spec

**Deciding what to build next?** Jump to the **Implementation Roadmap** section. Phase 1 lists the highest-priority requirements.

**Implementing a specific requirement?** Search for its ID (e.g., `R-OR-01`), trace it to the obstacle it resolves, then check the **File Index** to find which source files are involved.

**Handing work to an AI agent?** Copy the relevant **Aggregate Reference** section — it's self-contained with states, transitions, gaps, and requirements for that domain area."""


def _notation_guide() -> str:
    return """## Notation Guide

| Prefix | Meaning | Example | Introduced |
|--------|---------|---------|------------|
| `E-{XX}-{NN}` | Domain event | E-MS-01 | Node 1 |
| `{XX}-G{N}` | Gap in statechart | MS-G1 | Node 2 |
| `O-{XX}-{N}` | Confirmed obstacle | O-MS-1 | Node 3 |
| `O-N{N}` | New obstacle (forward analysis) | O-N1 | Node 3 |
| `R-{XX}-{NN}` | Requirement | R-MS-01 | Node 3 |
| `R-XA-{NN}` | Cross-aggregate requirement | R-XA-01 | Node 3 |
| `G{N}.{N}` | Goal | G1.2 | Node 3 |"""


def _system_purpose(node4: Node4Output) -> str:
    return f"## System Purpose\n\n{node4.system_purpose}"


def _goal_tree(node3: Node3Output) -> str:
    return f"## Goal Tree\n\n{_render_goal(node3.goal_tree)}"


def _render_goal(goal: GoalNode, depth: int = 0) -> str:
    indent = "  " * depth
    line = f"{indent}- **{goal.id}**: {goal.description}"
    if goal.decomposition:
        line += f" [{goal.decomposition.value}]"
    if goal.agent:
        line += f" — *{goal.agent}*"
    if goal.obstacle_refs:
        refs = ", ".join(goal.obstacle_refs)
        line += f" ⚠ {refs}"
    lines = [line]
    for child in goal.children:
        lines.append(_render_goal(child, depth + 1))
    return "\n".join(lines)


def _aggregate_reference(
    node2: Node2Output,
    node3: Node3Output,
    event_by_id: dict,
    req_by_id: dict,
) -> str:
    sections = ["## Aggregate Reference"]
    for agg in node2.aggregates:
        sections.append(_render_aggregate(agg, node3, event_by_id, req_by_id))
    return "\n\n".join(sections)


def _render_aggregate(
    agg: Aggregate,
    node3: Node3Output,
    event_by_id: dict,
    req_by_id: dict,
) -> str:
    key_files = ", ".join(f"`{kf.file}`" for kf in agg.key_files)

    # States table
    state_rows = []
    for s in agg.states:
        loc = f"`{s.location.file}:{s.location.anchor}`"
        stype = s.type.value if hasattr(s.type, "value") else s.type
        state_rows.append(f"| {s.name} | {stype} | {s.representation} | {loc} |")
    states_table = "| State | Type | Representation | Location |\n|-------|------|----------------|----------|\n" + "\n".join(state_rows)

    # Statechart transitions
    transition_lines = []
    for t in agg.transitions:
        event = event_by_id.get(t.event)
        event_name = event.name if event else t.event
        guard_str = f"/{t.guard}" if t.guard else ""
        annotation_str = ""
        if t.annotation:
            ann_val = t.annotation.value if hasattr(t.annotation, "value") else t.annotation
            annotation_str = f"  *({ann_val})*"
        transition_lines.append(f"  {t.source} --[{event_name}{guard_str}]--> {t.target}{annotation_str}")
    statechart = "\n".join(transition_lines) if transition_lines else "  *(no transitions)*"

    # Gaps table
    if agg.gaps:
        gap_rows = []
        for g in agg.gaps:
            sev = g.severity.value if hasattr(g.severity, "value") else g.severity
            loc = f"`{g.code_location.file}:{g.code_location.anchor}`"
            gap_rows.append(f"| {g.id} | {sev} | {g.description} | {loc} |")
        gaps_table = "| ID | Severity | Description | Location |\n|----|----------|-------------|----------|\n" + "\n".join(gap_rows)
    else:
        gaps_table = "*(no gaps identified)*"

    # Requirements for this aggregate
    agg_reqs = _filter_reqs_for_aggregate(agg.code, node3, req_by_id)
    reqs_section = _render_requirements_by_priority(agg_reqs, req_by_id)

    return f"""### {agg.name} (`{agg.code}`)

**Root entity:** {agg.root_entity}
**Key files:** {key_files}
**Trivial lifecycle:** {"Yes" if agg.trivial_lifecycle else "No"}

#### States

{states_table}

#### Statechart

```
{statechart}
```

#### Gaps

{gaps_table}

#### Requirements

{reqs_section}"""


def _filter_reqs_for_aggregate(
    agg_code: str,
    node3: Node3Output,
    req_by_id: dict,
) -> list[str]:
    """Find requirement IDs that resolve obstacles belonging to this aggregate."""
    # Obstacles for this aggregate
    agg_obstacle_ids = set()
    for o in node3.confirmed_obstacles:
        if o.id.startswith(f"O-{agg_code}-"):
            agg_obstacle_ids.add(o.id)
    for o in node3.new_obstacles:
        # New obstacles (O-N*) need to be matched by checking which gaps/goals they reference
        # Simpler: check if any requirement resolving this obstacle also has agg_code prefix
        pass

    # Requirements that resolve any agg obstacle, or have this agg code prefix
    req_ids = []
    for r in node3.requirements:
        if r.id.startswith(f"R-{agg_code}-"):
            req_ids.append(r.id)
        elif any(obs_id in agg_obstacle_ids for obs_id in r.resolves):
            req_ids.append(r.id)
    return req_ids


def _render_requirements_by_priority(req_ids: list[str], req_by_id: dict) -> str:
    groups: dict[str, list] = {"MUST": [], "SHOULD": [], "COULD": []}
    for rid in req_ids:
        req = req_by_id.get(rid)
        if req:
            prio = req.priority.value if hasattr(req.priority, "value") else req.priority
            resolves = ", ".join(req.resolves)
            groups.setdefault(prio, []).append(f"| {req.id} | {req.description} | {resolves} |")

    parts = []
    header = "| ID | Requirement | Resolves |\n|----|-------------|----------|"
    for prio in ("MUST", "SHOULD", "COULD"):
        rows = groups.get(prio, [])
        if rows:
            parts.append(f"**{prio}:**\n\n{header}\n" + "\n".join(rows))
    return "\n\n".join(parts) if parts else "*(no requirements)*"


def _cross_aggregate(
    node2: Node2Output,
    node3: Node3Output,
    req_by_id: dict,
) -> str:
    parts = ["## Cross-Aggregate Architecture"]

    # Transition map
    if node2.cross_agg_transitions:
        rows = []
        for t in node2.cross_agg_transitions:
            rows.append(f"| {t.from_event} ({t.from_aggregate}) | {t.to_event} ({t.to_aggregate}) | {t.mechanism} |")
        table = "| From | To | Mechanism |\n|------|----|-----------|\n" + "\n".join(rows)
        parts.append(f"### Transition Map\n\n{table}")
    else:
        parts.append("### Transition Map\n\n*(none)*")

    # Impossible combinations
    if node2.impossible_combinations:
        rows = []
        for ic in node2.impossible_combinations:
            rows.append(f"| {ic.combination} | {ic.risk} | {ic.source} |")
        table = "| Combination | Risk | Source |\n|-------------|------|--------|\n" + "\n".join(rows)
        parts.append(f"### Impossible State Combinations\n\n{table}")

    # Cross-aggregate requirements
    xa_reqs = [r for r in node3.requirements if r.id.startswith("R-XA-")]
    if xa_reqs:
        rows = []
        for r in xa_reqs:
            resolves = ", ".join(r.resolves)
            prio = r.priority.value if hasattr(r.priority, "value") else r.priority
            rows.append(f"| {r.id} | {prio} | {r.description} | {resolves} |")
        table = "| ID | Priority | Requirement | Resolves |\n|----|----------|-------------|----------|\n" + "\n".join(rows)
        parts.append(f"### Cross-Aggregate Requirements\n\n{table}")

    return "\n\n".join(parts)


def _obstacle_register(node3: Node3Output) -> str:
    # Merge confirmed + new obstacles
    all_obs = []
    for o in node3.confirmed_obstacles:
        sev = o.severity.value if hasattr(o.severity, "value") else o.severity
        goals = ", ".join(o.violates_goals)
        all_obs.append((sev, o.id, o.description, goals))
    for o in node3.new_obstacles:
        sev = o.severity.value if hasattr(o.severity, "value") else o.severity
        goals = ", ".join(o.violates_goals)
        all_obs.append((sev, o.id, o.description, goals))

    # Summary
    counts: dict[str, int] = {"CRITICAL": 0, "HIGH": 0, "MED": 0, "LOW": 0}
    for sev, _, _, _ in all_obs:
        counts[sev] = counts.get(sev, 0) + 1
    summary_rows = [f"| {s} | {c} |" for s, c in counts.items() if c > 0]
    summary = "| Severity | Count |\n|----------|-------|\n" + "\n".join(summary_rows)

    # Grouped listing
    groups: dict[str, list[str]] = {}
    for sev, oid, desc, goals in all_obs:
        groups.setdefault(sev, []).append(f"- **{oid}**: {desc} — violates {goals}")

    listing_parts = []
    for sev in ("CRITICAL", "HIGH", "MED", "LOW"):
        items = groups.get(sev, [])
        if items:
            listing_parts.append(f"### {sev}\n\n" + "\n".join(items))

    listing = "\n\n".join(listing_parts) if listing_parts else "*(no obstacles)*"

    return f"## Obstacle Register\n\n### Summary\n\n{summary}\n\n{listing}"


def _requirements_delta(node3: Node3Output) -> str:
    counts: dict[str, int] = {"MUST": 0, "SHOULD": 0, "COULD": 0}
    for r in node3.requirements:
        prio = r.priority.value if hasattr(r.priority, "value") else r.priority
        counts[prio] = counts.get(prio, 0) + 1

    rows = [f"| {p} | {c} |" for p, c in counts.items() if c > 0]
    table = "| Priority | Count |\n|----------|-------|\n" + "\n".join(rows)
    return f"## Requirements Delta\n\n{table}"


def _roadmap(node3: Node3Output, req_by_id: dict) -> str:
    parts = ["## Implementation Roadmap"]
    for phase in node3.roadmap:
        req_rows = []
        for rid in phase.requirements:
            req = req_by_id.get(rid)
            desc = req.description if req else "*(unknown)*"
            req_rows.append(f"| {rid} | {desc} |")
        req_table = "| Requirement | Description |\n|-------------|-------------|\n" + "\n".join(req_rows)

        parts.append(f"""### Phase {phase.number}: {phase.name}

**Scope:** {phase.scope}
**Risk reduced:** {phase.risk_reduced}

{req_table}""")

    return "\n\n".join(parts)


def _file_index(node4: Node4Output) -> str:
    if not node4.file_index:
        return "## File Index\n\n*(no files indexed)*"

    # Group by category
    by_cat: dict[str, list] = {}
    for entry in node4.file_index:
        cat = entry.category.value if hasattr(entry.category, "value") else entry.category
        by_cat.setdefault(cat, []).append(entry)

    rows = []
    for cat in sorted(by_cat.keys()):
        for entry in by_cat[cat]:
            cat_val = entry.category.value if hasattr(entry.category, "value") else entry.category
            reqs = ", ".join(entry.requirements)
            rows.append(f"| `{entry.file}` | {cat_val} | {reqs} |")

    table = "| File | Category | Requirements |\n|------|----------|--------------|\n" + "\n".join(rows)
    return f"## File Index\n\n{table}"


def _metrics(node4: Node4Output) -> str:
    m = node4.metrics
    return f"""## Metrics

| Metric | Value |
|--------|-------|
| Total goals | {m.total_goals} |
| Total aggregates | {m.total_aggregates} |
| Total events | {m.total_events} |
| Total gaps | {m.total_gaps} |
| Confirmed obstacles | {m.confirmed_obstacles} |
| New obstacles | {m.new_obstacles} |
| Total requirements | {m.total_requirements} |
| MUST | {m.must} |
| SHOULD | {m.should} |
| COULD | {m.could} |
| Phases | {m.phases} |
| Files indexed | {m.files_indexed} |"""


def _changelog(node4: Node4Output) -> str:
    rows = [f"| {e.date} | {e.change} |" for e in node4.changelog]
    table = "| Date | Change |\n|------|--------|\n" + "\n".join(rows)
    return f"## Changelog\n\n{table}"
