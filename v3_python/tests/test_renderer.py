"""Tests for the deterministic markdown renderer."""

import json
from pathlib import Path

from typer.testing import CliRunner

from ede.cli import app
from ede.nodes.node0 import Node0Output
from ede.nodes.node1 import Node1Output
from ede.nodes.node2 import Node2Output
from ede.nodes.node3 import Node3Output
from ede.nodes.node4 import Node4Output
from ede.renderer import render_markdown

runner = CliRunner()


def _build_models(node0_data, node1_data, node2_data, node3_data, node4_data):
    return (
        Node0Output.model_validate(node0_data),
        Node1Output.model_validate(node1_data),
        Node2Output.model_validate(node2_data),
        Node3Output.model_validate(node3_data),
        Node4Output.model_validate(node4_data),
    )


class TestRenderer:
    def test_render_produces_markdown(self, node0_data, node1_data, node2_data, node3_data, node4_data):
        n0, n1, n2, n3, n4 = _build_models(node0_data, node1_data, node2_data, node3_data, node4_data)
        md = render_markdown(n0, n1, n2, n3, n4)
        assert md.startswith("# test-app")
        assert "## Goal Tree" in md
        assert "## Aggregate Reference" in md
        assert "## Obstacle Register" in md
        assert "## Requirements Delta" in md
        assert "## Implementation Roadmap" in md
        assert "## File Index" in md
        assert "## Metrics" in md
        assert "## Changelog" in md

    def test_render_contains_all_event_ids_in_transitions(self, node0_data, node1_data, node2_data, node3_data, node4_data):
        """Event names appear in statechart transitions where they are referenced."""
        n0, n1, n2, n3, n4 = _build_models(node0_data, node1_data, node2_data, node3_data, node4_data)
        md = render_markdown(n0, n1, n2, n3, n4)
        # Events referenced in transitions should appear by name
        for agg in n2.aggregates:
            for t in agg.transitions:
                event = next((e for e in n1.events if e.id == t.event), None)
                if event:
                    assert event.name in md, f"Event {event.name} (used in transition) not in output"

    def test_render_contains_all_requirements(self, node0_data, node1_data, node2_data, node3_data, node4_data):
        n0, n1, n2, n3, n4 = _build_models(node0_data, node1_data, node2_data, node3_data, node4_data)
        md = render_markdown(n0, n1, n2, n3, n4)
        for req in n3.requirements:
            assert req.id in md, f"Requirement {req.id} not in rendered output"

    def test_render_goal_tree_depth(self, node0_data, node1_data, node2_data, node3_data, node4_data):
        n0, n1, n2, n3, n4 = _build_models(node0_data, node1_data, node2_data, node3_data, node4_data)
        md = render_markdown(n0, n1, n2, n3, n4)
        # Root (depth 0), child (depth 1), leaf (depth 2)
        assert "- **G0**:" in md
        assert "  - **G1**:" in md
        assert "    - **G1.1**:" in md

    def test_render_aggregate_sections(self, node0_data, node1_data, node2_data, node3_data, node4_data):
        n0, n1, n2, n3, n4 = _build_models(node0_data, node1_data, node2_data, node3_data, node4_data)
        md = render_markdown(n0, n1, n2, n3, n4)
        assert "### User (`US`)" in md
        assert "### Order (`OR`)" in md

    def test_render_metrics_match(self, node0_data, node1_data, node2_data, node3_data, node4_data):
        n0, n1, n2, n3, n4 = _build_models(node0_data, node1_data, node2_data, node3_data, node4_data)
        md = render_markdown(n0, n1, n2, n3, n4)
        assert f"| Total goals | {n4.metrics.total_goals} |" in md
        assert f"| Total events | {n4.metrics.total_events} |" in md
        assert f"| MUST | {n4.metrics.must} |" in md

    def test_render_cli_writes_file(self, node0_data, node1_data, node2_data, node3_data, node4_data, tmp_path):
        # Write all 5 JSON files to tmp_path
        files = {}
        for name, data in [("n0", node0_data), ("n1", node1_data), ("n2", node2_data), ("n3", node3_data), ("n4", node4_data)]:
            p = tmp_path / f"{name}.json"
            p.write_text(json.dumps(data))
            files[name] = p

        output = tmp_path / "spec.md"
        result = runner.invoke(app, [
            "render",
            "--node0", str(files["n0"]),
            "--node1", str(files["n1"]),
            "--node2", str(files["n2"]),
            "--node3", str(files["n3"]),
            "--node4", str(files["n4"]),
            "--output", str(output),
        ])
        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert output.exists()
        content = output.read_text()
        assert "# test-app" in content
        assert "Rendered to" in result.output
