"""CLI smoke tests."""

import json
from pathlib import Path

from typer.testing import CliRunner

from ede.cli import app
from ede.nodes import Node0Output, Node1Output

runner = CliRunner()


def _write_node_json(tmp_path: Path, name: str, data: dict) -> Path:
    p = tmp_path / f"{name}.json"
    p.write_text(json.dumps(data))
    return p


class TestValidateCommand:
    def test_no_flags(self):
        result = runner.invoke(app, ["validate"])
        assert result.exit_code == 1
        assert "at least one" in result.output

    def test_validate_node0(self, node0_data, tmp_path):
        f = _write_node_json(tmp_path, "node0", node0_data)
        result = runner.invoke(app, ["validate", "--node0", str(f)])
        assert result.exit_code == 0
        assert "L1 OK: node0" in result.output

    def test_validate_node0_and_node1(self, node0_data, node1_data, tmp_path):
        f0 = _write_node_json(tmp_path, "node0", node0_data)
        f1 = _write_node_json(tmp_path, "node1", node1_data)
        result = runner.invoke(app, ["validate", "--node0", str(f0), "--node1", str(f1)])
        assert result.exit_code == 0
        assert "Valid: True" in result.output

    def test_validate_invalid_json(self, node1_data, tmp_path):
        data = node1_data.copy()
        data["events"][0]["evidence"] = "short"
        f = _write_node_json(tmp_path, "node1", data)
        result = runner.invoke(app, ["validate", "--node1", str(f)])
        assert result.exit_code == 1
        assert "L1 FAIL" in result.output


class TestSchemaCommand:
    def test_schema_node0(self):
        result = runner.invoke(app, ["schema", "--node", "0"])
        assert result.exit_code == 0
        schema = json.loads(result.output)
        assert "properties" in schema

    def test_schema_node3(self):
        result = runner.invoke(app, ["schema", "--node", "3"])
        assert result.exit_code == 0
        schema = json.loads(result.output)
        assert "properties" in schema

    def test_schema_invalid_node(self):
        result = runner.invoke(app, ["schema", "--node", "9"])
        assert result.exit_code == 1

    def test_schema_fragment_node1(self):
        result = runner.invoke(app, ["schema", "--fragment", "node1"])
        assert result.exit_code == 0
        schema = json.loads(result.output)
        assert "EventFragment" in str(schema)

    def test_schema_fragment_node2(self):
        result = runner.invoke(app, ["schema", "--fragment", "node2"])
        assert result.exit_code == 0
        schema = json.loads(result.output)
        assert "TransitionFragment" in str(schema)

    def test_schema_fragment_node3(self):
        result = runner.invoke(app, ["schema", "--fragment", "node3"])
        assert result.exit_code == 0
        schema = json.loads(result.output)
        assert "ObstacleFragment" in str(schema)

    def test_schema_fragment_invalid(self):
        result = runner.invoke(app, ["schema", "--fragment", "node99"])
        assert result.exit_code == 1

    def test_schema_no_args(self):
        result = runner.invoke(app, ["schema"])
        assert result.exit_code == 1


class TestCoverageCommand:
    def test_coverage_all_scanned(self, node0_data, node1_data, tmp_path):
        f0 = _write_node_json(tmp_path, "node0", node0_data)
        f1 = _write_node_json(tmp_path, "node1", node1_data)
        result = runner.invoke(app, ["coverage", "--node0", str(f0), "--node1", str(f1)])
        assert "Coverage check passed" in result.output or "All key files were scanned" in result.output

    def test_coverage_missing_file(self, node0_data, node1_data, tmp_path):
        # Add a key file that won't be in scanned files
        node0_data["keyFiles"].append({"path": "src/never-scanned.ts", "rationale": "test"})
        f0 = _write_node_json(tmp_path, "node0", node0_data)
        f1 = _write_node_json(tmp_path, "node1", node1_data)
        result = runner.invoke(app, ["coverage", "--node0", str(f0), "--node1", str(f1)])
        assert result.exit_code == 1
        assert "never-scanned.ts" in result.output
