"""
Layer 4 -- Path existence verifiers.

Every path-typed field across all pipeline artifacts (and the sub-agent
fragments that feed them) should resolve against the repository on disk.
A missing path is a strong signal a claim was hallucinated or stale.
Findings are emitted as WARN so the pipeline still proceeds.

Coverage map (modality A in the verifier catalog):

  Node 0 (verify_recon_paths)
    registry.areas[].directories[]            dir
    architecture.{frontend,backend,shared}Dir dir (optional)
    persistence.schemaLocation                file|dir (optional)
    externalServices[].configLocation         file|dir
    dispatchPlan[].directories[]              dir
    keyFiles[].path                           file

  Node 1 (verify_events_paths)
    metadata.scanAreas[].directories[]        dir
    metadata.scanAreas[].filesScanned[]       file
    metadata.scanAreas[].filesSkipped[]       file
    events[].location.file                    file
    events[].hotSpots[].location.file         file
    hotSpotSummary[].location.file            file

  Node 2 (verify_aggregates_paths)
    aggregates[].keyFiles[].file              file
    aggregates[].states[].location.file       file
    aggregates[].transitions[].codeLocation.file file
    aggregates[].gaps[].codeLocation.file     file

  Node 4 (verify_spec_paths)
    fileIndex[].file                          file

  Fragments (verify_fragment_paths)
    Node1Fragment.filesScanned[]              file
    Node1Fragment.filesSkipped[]              file
    Node1Fragment.events[].location.file      file
    Node1Fragment.events[].hotSpots[].location.file file
    Node2Fragment.keyFiles[].file             file
    Node2Fragment.states[].location.file      file
    Node2Fragment.transitions[].codeLocation.file file
    Node2Fragment.gaps[].codeLocation.file    file
    Node3Fragment: no path fields
"""

from __future__ import annotations

from pathlib import Path
from typing import Union

from ..fragments import Node1Fragment, Node2Fragment, Node3Fragment
from ..nodes.node0 import Node0Output
from ..nodes.node1 import Node1Output
from ..nodes.node2 import Node2Output
from ..nodes.node4 import Node4Output
from ..primitives import Finding, FindingLevel


RULE_MISSING = "L4-path-missing"
RULE_WRONG_KIND = "L4-path-wrong-kind"


def _warn(node: int, where: str, message: str, rule: str = RULE_MISSING) -> Finding:
    return Finding(level=FindingLevel.WARN, node=node, where=where, message=message, rule=rule)


def _check(
    repo_root: Path,
    rel: str,
    where: str,
    *,
    expect: str,  # "file" | "dir" | "any"
    node: int,
) -> Finding | None:
    target = repo_root / rel
    if not target.exists():
        return _warn(node, where, f"path does not exist: {rel}")
    if expect == "file" and not target.is_file():
        return _warn(node, where, f"expected file, found directory: {rel}", RULE_WRONG_KIND)
    if expect == "dir" and not target.is_dir():
        return _warn(node, where, f"expected directory, found file: {rel}", RULE_WRONG_KIND)
    return None


# -- Node 0 -------------------------------------------------------------------


def verify_recon_paths(n0: Node0Output, repo_root: Path) -> list[Finding]:
    """Probe every path-typed field in Node 0 against ``repo_root``."""
    findings: list[Finding] = []

    for i, area in enumerate(n0.registry.areas):
        for j, d in enumerate(area.directories):
            f = _check(repo_root, d, f"registry.areas[{i}={area.code}].directories[{j}]", expect="dir", node=0)
            if f:
                findings.append(f)

    arch = n0.architecture
    if arch.frontend_dir is not None:
        f = _check(repo_root, arch.frontend_dir, "architecture.frontendDir", expect="dir", node=0)
        if f:
            findings.append(f)
    if arch.backend_dir is not None:
        f = _check(repo_root, arch.backend_dir, "architecture.backendDir", expect="dir", node=0)
        if f:
            findings.append(f)
    if arch.shared_dir is not None:
        f = _check(repo_root, arch.shared_dir, "architecture.sharedDir", expect="dir", node=0)
        if f:
            findings.append(f)

    if n0.persistence.schema_location is not None:
        f = _check(repo_root, n0.persistence.schema_location, "persistence.schemaLocation", expect="any", node=0)
        if f:
            findings.append(f)

    for i, svc in enumerate(n0.external_services):
        f = _check(repo_root, svc.config_location, f"externalServices[{i}={svc.name}].configLocation", expect="any", node=0)
        if f:
            findings.append(f)

    for i, dp in enumerate(n0.dispatch_plan):
        for j, d in enumerate(dp.directories):
            f = _check(repo_root, d, f"dispatchPlan[{i}={dp.code}].directories[{j}]", expect="dir", node=0)
            if f:
                findings.append(f)

    for i, kf in enumerate(n0.key_files):
        f = _check(repo_root, kf.path, f"keyFiles[{i}]", expect="file", node=0)
        if f:
            findings.append(f)

    return findings


# -- Node 1 -------------------------------------------------------------------


def verify_events_paths(n1: Node1Output, repo_root: Path) -> list[Finding]:
    """Probe every path-typed field in Node 1 against ``repo_root``."""
    findings: list[Finding] = []

    for i, area in enumerate(n1.metadata.scan_areas):
        for j, d in enumerate(area.directories):
            f = _check(repo_root, d, f"metadata.scanAreas[{i}={area.area_code}].directories[{j}]", expect="dir", node=1)
            if f:
                findings.append(f)
        for j, fn in enumerate(area.files_scanned):
            f = _check(repo_root, fn, f"metadata.scanAreas[{i}={area.area_code}].filesScanned[{j}]", expect="file", node=1)
            if f:
                findings.append(f)
        for j, fn in enumerate(area.files_skipped):
            f = _check(repo_root, fn, f"metadata.scanAreas[{i}={area.area_code}].filesSkipped[{j}]", expect="file", node=1)
            if f:
                findings.append(f)

    for i, ev in enumerate(n1.events):
        f = _check(repo_root, ev.location.file, f"events[{i}={ev.id}].location.file", expect="file", node=1)
        if f:
            findings.append(f)
        for j, hs in enumerate(ev.hot_spots):
            f = _check(repo_root, hs.location.file, f"events[{i}={ev.id}].hotSpots[{j}].location.file", expect="file", node=1)
            if f:
                findings.append(f)

    for i, hs in enumerate(n1.hot_spot_summary):
        f = _check(repo_root, hs.location.file, f"hotSpotSummary[{i}].location.file", expect="file", node=1)
        if f:
            findings.append(f)

    return findings


# -- Node 2 -------------------------------------------------------------------


def verify_aggregates_paths(n2: Node2Output, repo_root: Path) -> list[Finding]:
    """Probe every path-typed field in Node 2 against ``repo_root``."""
    findings: list[Finding] = []

    for i, agg in enumerate(n2.aggregates):
        for j, kf in enumerate(agg.key_files):
            f = _check(repo_root, kf.file, f"aggregates[{i}={agg.code}].keyFiles[{j}].file", expect="file", node=2)
            if f:
                findings.append(f)
        for j, st in enumerate(agg.states):
            f = _check(repo_root, st.location.file, f"aggregates[{i}={agg.code}].states[{j}={st.name}].location.file", expect="file", node=2)
            if f:
                findings.append(f)
        for j, tr in enumerate(agg.transitions):
            f = _check(repo_root, tr.code_location.file, f"aggregates[{i}={agg.code}].transitions[{j}].codeLocation.file", expect="file", node=2)
            if f:
                findings.append(f)
        for j, gap in enumerate(agg.gaps):
            f = _check(repo_root, gap.code_location.file, f"aggregates[{i}={agg.code}].gaps[{j}={gap.id}].codeLocation.file", expect="file", node=2)
            if f:
                findings.append(f)

    return findings


# -- Node 4 -------------------------------------------------------------------


def verify_spec_paths(n4: Node4Output, repo_root: Path) -> list[Finding]:
    """Probe every path-typed field in Node 4 against ``repo_root``."""
    findings: list[Finding] = []

    for i, entry in enumerate(n4.file_index):
        f = _check(repo_root, entry.file, f"fileIndex[{i}].file", expect="file", node=4)
        if f:
            findings.append(f)

    return findings


# -- Fragments ----------------------------------------------------------------


Fragment = Union[Node1Fragment, Node2Fragment, Node3Fragment]


def verify_fragment_paths(fragment: Fragment, repo_root: Path) -> list[Finding]:
    """
    Probe every path-typed field in a sub-agent fragment against ``repo_root``.

    Fragment-level checks catch hallucinated paths at the sub-agent boundary,
    before assembly washes them into the final node output.
    """
    findings: list[Finding] = []

    if isinstance(fragment, Node1Fragment):
        node = 1
        for j, fn in enumerate(fragment.files_scanned):
            f = _check(repo_root, fn, f"filesScanned[{j}]", expect="file", node=node)
            if f:
                findings.append(f)
        for j, fn in enumerate(fragment.files_skipped):
            f = _check(repo_root, fn, f"filesSkipped[{j}]", expect="file", node=node)
            if f:
                findings.append(f)
        for i, ev in enumerate(fragment.events):
            f = _check(repo_root, ev.location.file, f"events[{i}={ev.name}].location.file", expect="file", node=node)
            if f:
                findings.append(f)
            for j, hs in enumerate(ev.hot_spots):
                f = _check(repo_root, hs.location.file, f"events[{i}={ev.name}].hotSpots[{j}].location.file", expect="file", node=node)
                if f:
                    findings.append(f)

    elif isinstance(fragment, Node2Fragment):
        node = 2
        for j, kf in enumerate(fragment.key_files):
            f = _check(repo_root, kf.file, f"keyFiles[{j}].file", expect="file", node=node)
            if f:
                findings.append(f)
        for j, st in enumerate(fragment.states):
            f = _check(repo_root, st.location.file, f"states[{j}={st.name}].location.file", expect="file", node=node)
            if f:
                findings.append(f)
        for j, tr in enumerate(fragment.transitions):
            f = _check(repo_root, tr.code_location.file, f"transitions[{j}].codeLocation.file", expect="file", node=node)
            if f:
                findings.append(f)
        for j, gap in enumerate(fragment.gaps):
            f = _check(repo_root, gap.code_location.file, f"gaps[{j}].codeLocation.file", expect="file", node=node)
            if f:
                findings.append(f)

    # Node3Fragment carries no path-typed fields.

    return findings
