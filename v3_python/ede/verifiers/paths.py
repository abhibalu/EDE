"""
Layer 4 -- Path existence verifier for Node 0 (Reconnaissance).

Every path-typed field in Node 0 should resolve against the repository
on disk. A missing path is a strong signal the recon was hallucinated
or stale. Findings are emitted as WARN so the pipeline still proceeds.

Fields checked (modality A in the verifier catalog):
  - registry.areas[].directories[]       (dir)
  - architecture.frontendDir              (dir, if non-null)
  - architecture.backendDir               (dir, if non-null)
  - architecture.sharedDir                (dir, if non-null)
  - persistence.schemaLocation            (file or dir, if non-null)
  - externalServices[].configLocation     (file or dir)
  - dispatchPlan[].directories[]          (dir)
  - keyFiles[].path                       (file)
"""

from __future__ import annotations

from pathlib import Path

from ..nodes.node0 import Node0Output
from ..primitives import Finding, FindingLevel


RULE_MISSING = "L4-path-missing"
RULE_WRONG_KIND = "L4-path-wrong-kind"


def _warn(where: str, message: str, rule: str = RULE_MISSING) -> Finding:
    return Finding(level=FindingLevel.WARN, node=0, where=where, message=message, rule=rule)


def _check(
    repo_root: Path,
    rel: str,
    where: str,
    *,
    expect: str,  # "file" | "dir" | "any"
) -> Finding | None:
    target = repo_root / rel
    if not target.exists():
        return _warn(where, f"path does not exist: {rel}")
    if expect == "file" and not target.is_file():
        return _warn(where, f"expected file, found directory: {rel}", RULE_WRONG_KIND)
    if expect == "dir" and not target.is_dir():
        return _warn(where, f"expected directory, found file: {rel}", RULE_WRONG_KIND)
    return None


def verify_recon_paths(n0: Node0Output, repo_root: Path) -> list[Finding]:
    """Probe every path-typed field in Node 0 against ``repo_root``."""
    findings: list[Finding] = []

    for i, area in enumerate(n0.registry.areas):
        for j, d in enumerate(area.directories):
            f = _check(repo_root, d, f"registry.areas[{i}={area.code}].directories[{j}]", expect="dir")
            if f:
                findings.append(f)

    arch = n0.architecture
    if arch.frontend_dir is not None:
        f = _check(repo_root, arch.frontend_dir, "architecture.frontendDir", expect="dir")
        if f:
            findings.append(f)
    if arch.backend_dir is not None:
        f = _check(repo_root, arch.backend_dir, "architecture.backendDir", expect="dir")
        if f:
            findings.append(f)
    if arch.shared_dir is not None:
        f = _check(repo_root, arch.shared_dir, "architecture.sharedDir", expect="dir")
        if f:
            findings.append(f)

    if n0.persistence.schema_location is not None:
        f = _check(repo_root, n0.persistence.schema_location, "persistence.schemaLocation", expect="any")
        if f:
            findings.append(f)

    for i, svc in enumerate(n0.external_services):
        f = _check(repo_root, svc.config_location, f"externalServices[{i}={svc.name}].configLocation", expect="any")
        if f:
            findings.append(f)

    for i, dp in enumerate(n0.dispatch_plan):
        for j, d in enumerate(dp.directories):
            f = _check(repo_root, d, f"dispatchPlan[{i}={dp.code}].directories[{j}]", expect="dir")
            if f:
                findings.append(f)

    for i, kf in enumerate(n0.key_files):
        f = _check(repo_root, kf.path, f"keyFiles[{i}]", expect="file")
        if f:
            findings.append(f)

    return findings
