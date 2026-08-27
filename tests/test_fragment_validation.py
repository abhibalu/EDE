"""Tests for the validate-fragment CLI command."""

import json
from pathlib import Path

from typer.testing import CliRunner

from ede.cli import app

runner = CliRunner()


def _write_json(tmp_path: Path, name: str, data: dict) -> Path:
    p = tmp_path / f"{name}.json"
    p.write_text(json.dumps(data))
    return p


class TestValidateFragmentCommand:
    def test_invalid_node_number(self, tmp_path):
        f = _write_json(tmp_path, "frag", {})
        result = runner.invoke(app, ["validate-fragment", "--node", "5", "--fragment", str(f)])
        assert result.exit_code == 1
        assert "must be 1, 2, or 3" in result.output

    def test_missing_file(self):
        result = runner.invoke(app, ["validate-fragment", "--node", "1", "--fragment", "/nonexistent.json"])
        assert result.exit_code == 1
        assert "does not exist" in result.output

    def test_valid_node1_fragment(self, tmp_path):
        data = {
            "areaCode": "US",
            "areaName": "User Service",
            "filesScanned": ["src/user.ts"],
            "filesSkipped": [],
            "events": [
                {
                    "name": "UserRegistered",
                    "trigger": "POST /register",
                    "location": {"file": "src/user.ts", "anchor": "register"},
                    "predecessorNames": [],
                    "successorNames": [],
                    "stateChange": "none -> pending",
                    "evidence": "Line 42: await db.user.create({ status: 'pending' })",
                    "hotSpots": [],
                },
            ],
        }
        f = _write_json(tmp_path, "US", data)
        result = runner.invoke(app, ["validate-fragment", "--node", "1", "--fragment", str(f)])
        assert result.exit_code == 0
        assert "L1 OK" in result.output
        assert "Fragment valid" in result.output

    def test_invalid_node1_fragment_bad_evidence(self, tmp_path):
        data = {
            "areaCode": "US",
            "areaName": "User Service",
            "filesScanned": ["src/user.ts"],
            "filesSkipped": [],
            "events": [
                {
                    "name": "UserRegistered",
                    "trigger": "POST /register",
                    "location": {"file": "src/user.ts", "anchor": "register"},
                    "predecessorNames": [],
                    "successorNames": [],
                    "stateChange": "none -> pending",
                    "evidence": "short",
                    "hotSpots": [],
                },
            ],
        }
        f = _write_json(tmp_path, "US", data)
        result = runner.invoke(app, ["validate-fragment", "--node", "1", "--fragment", str(f)])
        assert result.exit_code == 1
        assert "L1 FAIL" in result.output

    def test_valid_node2_fragment(self, tmp_path):
        data = {
            "aggCode": "US",
            "aggName": "User",
            "rootEntity": "User",
            "keyFiles": [{"file": "src/user.ts", "anchor": "module"}],
            "states": [
                {
                    "name": "Pending",
                    "type": "atomic",
                    "representation": "status='pending'",
                    "location": {"file": "src/user.ts", "anchor": "42"},
                    "evidence": "Prisma enum UserStatus { PENDING ACTIVE }",
                },
                {
                    "name": "Active",
                    "type": "atomic",
                    "representation": "status='active'",
                    "location": {"file": "src/user.ts", "anchor": "78"},
                    "evidence": "Prisma enum UserStatus { PENDING ACTIVE }",
                },
            ],
            "transitions": [
                {
                    "source": "Pending",
                    "target": "Active",
                    "eventName": "UserActivated",
                    "guard": None,
                    "sideEffects": [],
                    "annotation": None,
                    "evidence": "user.status = 'active' on line 92",
                    "codeLocation": {"file": "src/user.ts", "anchor": "92"},
                },
            ],
            "gaps": [],
            "trivialLifecycle": True,
        }
        f = _write_json(tmp_path, "US", data)
        result = runner.invoke(app, ["validate-fragment", "--node", "2", "--fragment", str(f)])
        assert result.exit_code == 0
        assert "L1 OK" in result.output
        assert "L2 OK" in result.output

    def test_node2_fragment_bad_transition_ref(self, tmp_path):
        data = {
            "aggCode": "US",
            "aggName": "User",
            "rootEntity": "User",
            "keyFiles": [{"file": "src/user.ts", "anchor": "module"}],
            "states": [
                {
                    "name": "Pending",
                    "type": "atomic",
                    "representation": "status='pending'",
                    "location": {"file": "src/user.ts", "anchor": "42"},
                    "evidence": "Prisma enum UserStatus { PENDING ACTIVE }",
                },
            ],
            "transitions": [
                {
                    "source": "Pending",
                    "target": "NonExistent",
                    "eventName": "UserActivated",
                    "guard": None,
                    "sideEffects": [],
                    "annotation": None,
                    "evidence": "user.status = 'active' on line 92",
                    "codeLocation": {"file": "src/user.ts", "anchor": "92"},
                },
            ],
            "gaps": [],
            "trivialLifecycle": True,
        }
        f = _write_json(tmp_path, "US", data)
        result = runner.invoke(app, ["validate-fragment", "--node", "2", "--fragment", str(f)])
        assert result.exit_code == 1
        assert "L2 FAIL" in result.output
        assert "NonExistent" in result.output

    def test_valid_node3_fragment(self, tmp_path):
        data = {
            "aggCode": "US",
            "aggName": "User",
            "newObstacles": [
                {
                    "seq": 1,
                    "violatesGoals": ["G1.1"],
                    "evidence": "src/user.ts:10 -- no rate limit",
                    "description": "No rate limiting on registration",
                    "severity": "HIGH",
                    "resolutionType": "New requirement",
                },
            ],
        }
        f = _write_json(tmp_path, "US", data)
        result = runner.invoke(app, ["validate-fragment", "--node", "3", "--fragment", str(f)])
        assert result.exit_code == 0
        assert "L1 OK" in result.output

    def test_node3_fragment_empty_obstacles(self, tmp_path):
        data = {
            "aggCode": "US",
            "aggName": "User",
            "newObstacles": [],
        }
        f = _write_json(tmp_path, "US", data)
        result = runner.invoke(app, ["validate-fragment", "--node", "3", "--fragment", str(f)])
        assert result.exit_code == 0
        assert "L1 OK" in result.output
