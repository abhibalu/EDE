"""Tests for L4 path-existence verifier."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from ede.cli import app
from ede.nodes import Node0Output
from ede.verifiers import verify_recon_paths

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
