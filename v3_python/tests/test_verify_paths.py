"""Tests for L4 path-existence verifier."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from ede.cli import app
from ede.fragments import Node1Fragment, Node2Fragment
from ede.nodes import Node0Output
from ede.nodes.node1 import Node1Output
from ede.nodes.node2 import Node2Output
from ede.nodes.node4 import Node4Output
from ede.verifiers import (
    verify_aggregates_paths,
    verify_events_paths,
    verify_fragment_paths,
    verify_recon_paths,
    verify_spec_paths,
)

runner = CliRunner()


def _build_repo(tmp_path: Path, node0_data: dict) -> Path:
    """Create every path referenced by ``node0_data`` under tmp_path."""
    repo = tmp_path / "repo"
    repo.mkdir()

    for area in node0_data["registry"]["areas"]:
        for d in area["directories"]:
            (repo / d).mkdir(parents=True, exist_ok=True)

    for k in ("frontendDir", "backendDir", "sharedDir"):
        d = node0_data["architecture"].get(k)
        if d:
            (repo / d).mkdir(parents=True, exist_ok=True)

    sl = node0_data["persistence"].get("schemaLocation")
    if sl:
        (repo / sl).parent.mkdir(parents=True, exist_ok=True)
        (repo / sl).write_text("// stub")

    for svc in node0_data["externalServices"]:
        cl = repo / svc["configLocation"]
        cl.parent.mkdir(parents=True, exist_ok=True)
        cl.write_text("// stub")

    for dp in node0_data["dispatchPlan"]:
        for d in dp["directories"]:
            (repo / d).mkdir(parents=True, exist_ok=True)

    for kf in node0_data["keyFiles"]:
        target = repo / kf["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("// stub")

    return repo


class TestVerifyPathsModule:
    def test_all_paths_present(self, node0_data, tmp_path):
        repo = _build_repo(tmp_path, node0_data)
        n0 = Node0Output.model_validate(node0_data)
        findings = verify_recon_paths(n0, repo)
        assert findings == []

    def test_missing_key_file(self, node0_data, tmp_path):
        repo = _build_repo(tmp_path, node0_data)
        node0_data["keyFiles"].append({"path": "src/ghost.ts", "rationale": "not on disk"})
        n0 = Node0Output.model_validate(node0_data)
        findings = verify_recon_paths(n0, repo)
        assert len(findings) == 1
        assert findings[0].rule == "L4-path-missing"
        assert "ghost.ts" in findings[0].message
        assert "keyFiles[2]" in findings[0].where

    def test_missing_area_dir(self, node0_data, tmp_path):
        repo = _build_repo(tmp_path, node0_data)
        node0_data["registry"]["areas"][0]["directories"].append("src/services/nonexistent")
        n0 = Node0Output.model_validate(node0_data)
        findings = verify_recon_paths(n0, repo)
        # Same dir is also in dispatchPlan (registry.areas == dispatchPlan in fixture),
        # so the missing path surfaces twice — once per occurrence.
        wheres = [f.where for f in findings]
        assert any("registry.areas[0=US]" in w for w in wheres)
        assert all(f.rule == "L4-path-missing" for f in findings)

    def test_file_where_dir_expected(self, node0_data, tmp_path):
        repo = _build_repo(tmp_path, node0_data)
        # Replace an area directory with a file.
        bad = node0_data["registry"]["areas"][0]["directories"][0]
        target = repo / bad
        # nuke the dir, create a file with the same name
        for child in target.iterdir():
            child.unlink() if child.is_file() else None
        target.rmdir()
        target.write_text("not a dir")
        n0 = Node0Output.model_validate(node0_data)
        findings = verify_recon_paths(n0, repo)
        assert any(f.rule == "L4-path-wrong-kind" for f in findings)

    def test_optional_paths_skipped_when_null(self, node0_data, tmp_path):
        # frontendDir and sharedDir already null in fixture (backend-only).
        repo = _build_repo(tmp_path, node0_data)
        n0 = Node0Output.model_validate(node0_data)
        findings = verify_recon_paths(n0, repo)
        assert findings == []


class TestVerifyPathsCLI:
    def _write(self, tmp_path: Path, data: dict) -> Path:
        p = tmp_path / "node0.json"
        p.write_text(json.dumps(data))
        return p

    def test_clean_run(self, node0_data, tmp_path):
        repo = _build_repo(tmp_path, node0_data)
        f0 = self._write(tmp_path, node0_data)
        result = runner.invoke(app, ["verify-paths", "--node0", str(f0), "--repo", str(repo)])
        assert result.exit_code == 0
        assert "0 finding(s)" in result.output

    def test_reports_missing(self, node0_data, tmp_path):
        repo = _build_repo(tmp_path, node0_data)
        node0_data["keyFiles"].append({"path": "src/ghost.ts", "rationale": "missing"})
        f0 = self._write(tmp_path, node0_data)
        result = runner.invoke(app, ["verify-paths", "--node0", str(f0), "--repo", str(repo)])
        # Advisory: exit 0 even with findings.
        assert result.exit_code == 0
        assert "ghost.ts" in result.output
        assert "L4-path-missing" in result.output

    def test_repo_must_be_dir(self, node0_data, tmp_path):
        f0 = self._write(tmp_path, node0_data)
        missing_repo = tmp_path / "nope"
        result = runner.invoke(app, ["verify-paths", "--node0", str(f0), "--repo", str(missing_repo)])
        assert result.exit_code == 1
        assert "not a directory" in result.output


def _materialize(repo: Path, rel: str, kind: str) -> None:
    """Create `rel` under `repo` as file or dir."""
    target = repo / rel
    if kind == "dir":
        target.mkdir(parents=True, exist_ok=True)
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            target.write_text("// stub")


def _build_node1_repo(tmp_path: Path, node1_data: dict) -> Path:
    repo = tmp_path / "repo1"
    repo.mkdir()
    for area in node1_data["metadata"]["scanAreas"]:
        for d in area["directories"]:
            _materialize(repo, d, "dir")
        for fn in area["filesScanned"]:
            _materialize(repo, fn, "file")
        for fn in area["filesSkipped"]:
            _materialize(repo, fn, "file")
    for ev in node1_data["events"]:
        _materialize(repo, ev["location"]["file"], "file")
        for hs in ev["hotSpots"]:
            _materialize(repo, hs["location"]["file"], "file")
    for hs in node1_data["hotSpotSummary"]:
        _materialize(repo, hs["location"]["file"], "file")
    return repo


def _build_node2_repo(tmp_path: Path, node2_data: dict) -> Path:
    repo = tmp_path / "repo2"
    repo.mkdir()
    for agg in node2_data["aggregates"]:
        for kf in agg["keyFiles"]:
            _materialize(repo, kf["file"], "file")
        for st in agg["states"]:
            _materialize(repo, st["location"]["file"], "file")
        for tr in agg["transitions"]:
            _materialize(repo, tr["codeLocation"]["file"], "file")
        for gap in agg["gaps"]:
            _materialize(repo, gap["codeLocation"]["file"], "file")
    return repo


def _build_node4_repo(tmp_path: Path, node4_data: dict) -> Path:
    repo = tmp_path / "repo4"
    repo.mkdir()
    for entry in node4_data["fileIndex"]:
        _materialize(repo, entry["file"], "file")
    return repo


class TestVerifyEventsPaths:
    def test_clean(self, node1_data, tmp_path):
        repo = _build_node1_repo(tmp_path, node1_data)
        n1 = Node1Output.model_validate(node1_data)
        assert verify_events_paths(n1, repo) == []

    def test_missing_event_location(self, node1_data, tmp_path):
        repo = _build_node1_repo(tmp_path, node1_data)
        node1_data["events"][0]["location"]["file"] = "src/services/user/ghost.ts"
        n1 = Node1Output.model_validate(node1_data)
        findings = verify_events_paths(n1, repo)
        assert len(findings) == 1
        assert findings[0].node == 1
        assert "events[0=E-US-01].location.file" in findings[0].where
        assert findings[0].rule == "L4-path-missing"

    def test_missing_files_scanned(self, node1_data, tmp_path):
        repo = _build_node1_repo(tmp_path, node1_data)
        node1_data["metadata"]["scanAreas"][0]["filesScanned"].append("src/services/user/ghost.ts")
        n1 = Node1Output.model_validate(node1_data)
        findings = verify_events_paths(n1, repo)
        assert any("filesScanned" in f.where for f in findings)

    def test_missing_hotspot_location(self, node1_data, tmp_path):
        repo = _build_node1_repo(tmp_path, node1_data)
        node1_data["hotSpotSummary"][0]["location"]["file"] = "src/ghost.ts"
        n1 = Node1Output.model_validate(node1_data)
        findings = verify_events_paths(n1, repo)
        assert any("hotSpotSummary[0]" in f.where for f in findings)


class TestVerifyAggregatesPaths:
    def test_clean(self, node2_data, tmp_path):
        repo = _build_node2_repo(tmp_path, node2_data)
        n2 = Node2Output.model_validate(node2_data)
        assert verify_aggregates_paths(n2, repo) == []

    def test_missing_state_location(self, node2_data, tmp_path):
        repo = _build_node2_repo(tmp_path, node2_data)
        node2_data["aggregates"][0]["states"][0]["location"]["file"] = "src/ghost.ts"
        n2 = Node2Output.model_validate(node2_data)
        findings = verify_aggregates_paths(n2, repo)
        assert any("aggregates[0=US].states[0=Pending]" in f.where for f in findings)
        assert all(f.node == 2 for f in findings)

    def test_missing_gap_code_location(self, node2_data, tmp_path):
        repo = _build_node2_repo(tmp_path, node2_data)
        node2_data["aggregates"][1]["gaps"][0]["codeLocation"]["file"] = "src/ghost.ts"
        n2 = Node2Output.model_validate(node2_data)
        findings = verify_aggregates_paths(n2, repo)
        assert any("gaps[0=OR-G1]" in f.where for f in findings)


class TestVerifySpecPaths:
    def test_clean(self, node4_data, tmp_path):
        repo = _build_node4_repo(tmp_path, node4_data)
        n4 = Node4Output.model_validate(node4_data)
        assert verify_spec_paths(n4, repo) == []

    def test_missing_file_index_entry(self, node4_data, tmp_path):
        repo = _build_node4_repo(tmp_path, node4_data)
        node4_data["fileIndex"].append(
            {"file": "src/ghost.ts", "category": "other", "requirements": ["R-OR-01"]}
        )
        n4 = Node4Output.model_validate(node4_data)
        findings = verify_spec_paths(n4, repo)
        assert len(findings) == 1
        assert findings[0].node == 4
        assert "fileIndex[3]" in findings[0].where


class TestVerifyFragmentPaths:
    def _n1_fragment(self) -> dict:
        return {
            "areaCode": "US",
            "areaName": "User Service",
            "filesScanned": ["src/services/user/index.ts"],
            "filesSkipped": [],
            "events": [
                {
                    "name": "UserRegistered",
                    "trigger": "POST /api/register",
                    "location": {"file": "src/services/user/index.ts", "anchor": "registerUser"},
                    "predecessorNames": [],
                    "successorNames": [],
                    "stateChange": "no user -> pending",
                    "evidence": "db.user.create call observed",
                    "hotSpots": [],
                }
            ],
        }

    def _n2_fragment(self) -> dict:
        return {
            "aggCode": "US",
            "aggName": "User",
            "rootEntity": "User",
            "keyFiles": [{"file": "src/services/user/index.ts", "anchor": "module"}],
            "states": [
                {
                    "name": "Pending",
                    "type": "atomic",
                    "representation": "status = 'pending'",
                    "location": {"file": "src/services/user/index.ts", "anchor": "42"},
                    "evidence": "Prisma enum observed",
                }
            ],
            "transitions": [],
            "gaps": [],
            "trivialLifecycle": True,
        }

    def test_node1_fragment_clean(self, tmp_path):
        data = self._n1_fragment()
        repo = tmp_path / "repo"
        repo.mkdir()
        _materialize(repo, "src/services/user/index.ts", "file")
        frag = Node1Fragment.model_validate(data)
        assert verify_fragment_paths(frag, repo) == []

    def test_node1_fragment_catches_hallucinated_event_path(self, tmp_path):
        data = self._n1_fragment()
        data["events"][0]["location"]["file"] = "src/ghost.ts"
        repo = tmp_path / "repo"
        repo.mkdir()
        _materialize(repo, "src/services/user/index.ts", "file")
        frag = Node1Fragment.model_validate(data)
        findings = verify_fragment_paths(frag, repo)
        assert len(findings) == 1
        assert findings[0].node == 1
        assert "events[0=UserRegistered]" in findings[0].where

    def test_node2_fragment_clean(self, tmp_path):
        data = self._n2_fragment()
        repo = tmp_path / "repo"
        repo.mkdir()
        _materialize(repo, "src/services/user/index.ts", "file")
        frag = Node2Fragment.model_validate(data)
        assert verify_fragment_paths(frag, repo) == []

    def test_node2_fragment_catches_hallucinated_state_path(self, tmp_path):
        data = self._n2_fragment()
        data["states"][0]["location"]["file"] = "src/ghost.ts"
        repo = tmp_path / "repo"
        repo.mkdir()
        _materialize(repo, "src/services/user/index.ts", "file")
        frag = Node2Fragment.model_validate(data)
        findings = verify_fragment_paths(frag, repo)
        assert any("states[0=Pending]" in f.where for f in findings)
        assert all(f.node == 2 for f in findings)


class TestVerifyPathsCLIMultiNode:
    def test_node1_via_cli(self, node1_data, tmp_path):
        repo = _build_node1_repo(tmp_path, node1_data)
        f1 = tmp_path / "node1.json"
        f1.write_text(json.dumps(node1_data))
        result = runner.invoke(app, ["verify-paths", "--node1", str(f1), "--repo", str(repo)])
        assert result.exit_code == 0
        assert "node1: 0 finding(s)" in result.output

    def test_multiple_nodes_via_cli(self, node0_data, node1_data, tmp_path):
        # Build a combined repo that satisfies both Node 0 and Node 1 claims.
        repo = _build_repo(tmp_path, node0_data)
        for area in node1_data["metadata"]["scanAreas"]:
            for d in area["directories"]:
                _materialize(repo, d, "dir")
            for fn in area["filesScanned"]:
                _materialize(repo, fn, "file")
        for ev in node1_data["events"]:
            _materialize(repo, ev["location"]["file"], "file")
        for hs in node1_data["hotSpotSummary"]:
            _materialize(repo, hs["location"]["file"], "file")

        f0 = tmp_path / "node0.json"
        f0.write_text(json.dumps(node0_data))
        f1 = tmp_path / "node1.json"
        f1.write_text(json.dumps(node1_data))
        result = runner.invoke(
            app, ["verify-paths", "--node0", str(f0), "--node1", str(f1), "--repo", str(repo)]
        )
        assert result.exit_code == 0
        assert "node0: 0 finding(s)" in result.output
        assert "node1: 0 finding(s)" in result.output

    def test_at_least_one_node_required(self, tmp_path):
        result = runner.invoke(app, ["verify-paths", "--repo", str(tmp_path)])
        assert result.exit_code == 1
        assert "at least one" in result.output


class TestValidateFragmentWithRepo:
    def test_fragment_path_check_reports_missing(self, tmp_path):
        frag_data = {
            "areaCode": "US",
            "areaName": "User Service",
            "filesScanned": ["src/services/user/index.ts"],
            "filesSkipped": [],
            "events": [
                {
                    "name": "UserRegistered",
                    "trigger": "POST /api/register",
                    "location": {"file": "src/ghost.ts", "anchor": "registerUser"},
                    "predecessorNames": [],
                    "successorNames": [],
                    "stateChange": "no user -> pending",
                    "evidence": "db.user.create call observed",
                    "hotSpots": [],
                }
            ],
        }
        frag_file = tmp_path / "frag.json"
        frag_file.write_text(json.dumps(frag_data))
        repo = tmp_path / "repo"
        repo.mkdir()
        _materialize(repo, "src/services/user/index.ts", "file")

        result = runner.invoke(
            app,
            ["validate-fragment", "--node", "1", "--fragment", str(frag_file), "--repo", str(repo)],
        )
        # L4 is advisory — exit code 0 even with path findings.
        assert result.exit_code == 0
        assert "L4-path-missing" in result.output
        assert "ghost.ts" in result.output
        assert "Fragment valid." in result.output
