"""L1 negative tests: invalid data rejected with correct errors."""

import copy

import pytest
from pydantic import ValidationError

from ede.nodes import (
    Node1Output,
    Node2Output,
    Node3Output,
)
from ede.nodes.node2 import GapSummary
from ede.nodes.node3 import NewObstacle, Node3Metrics


class TestSchemaRejection:
    def test_evidence_too_short(self, node1_data: dict) -> None:
        data = copy.deepcopy(node1_data)
        data["events"][0]["evidence"] = "short"  # < 10 chars
        with pytest.raises(ValidationError, match="string_too_short"):
            Node1Output.model_validate(data)

    def test_malformed_event_id(self, node1_data: dict) -> None:
        data = copy.deepcopy(node1_data)
        data["events"][0]["id"] = "BAD-ID"  # doesn't match E-XX-NN
        with pytest.raises(ValidationError, match="pattern"):
            Node1Output.model_validate(data)

    def test_event_name_not_pascal_case(self, node1_data: dict) -> None:
        data = copy.deepcopy(node1_data)
        data["events"][0]["name"] = "user_registered"  # not PascalCase
        with pytest.raises(ValidationError, match="pattern"):
            Node1Output.model_validate(data)

    def test_per_area_cap_enforced_by_assembler(self) -> None:
        """Assembler truncates areas with >15 events (replaced global 50 cap)."""
        from ede.assemblers import assemble_node1
        from ede.fragments import Node1Fragment
        from ede.primitives import Registry

        registry = Registry.model_validate({
            "project": "Test", "version": "0.1.0",
            "areas": [{"code": "BG", "name": "Big", "directories": ["src"]}],
        })
        events = []
        for i in range(20):
            events.append({
                "name": f"Event{i + 1:02d}",
                "trigger": f"trigger {i}",
                "location": {"file": f"src/f{i}.ts", "anchor": f"fn{i}"},
                "predecessorNames": [],
                "successorNames": [],
                "stateChange": f"change {i}",
                "hotSpots": [],
                "evidence": f"Line {i}: some code evidence here",
            })
        frag = Node1Fragment.model_validate({
            "areaCode": "BG",
            "areaName": "Big",
            "filesScanned": [f"src/f{i}.ts" for i in range(20)],
            "filesSkipped": [],
            "events": events,
        })
        result = assemble_node1(registry, [frag])
        assert len(result.output.events) == 15  # truncated from 20
        assert result.output.truncation is not None
        assert "BG" in result.output.truncation.areas_affected


class TestL1Promotions:
    """Tests for checks promoted from L3 to L1 via model_validator."""

    def test_gap_summary_total_mismatch(self) -> None:
        with pytest.raises(ValidationError, match="total.*!=.*sum"):
            GapSummary.model_validate({
                "critical": 1, "high": 1, "med": 1, "low": 1, "total": 99,
            })

    def test_gap_summary_total_correct(self) -> None:
        gs = GapSummary.model_validate({
            "critical": 1, "high": 2, "med": 3, "low": 4, "total": 10,
        })
        assert gs.total == 10

    def test_node3_metrics_total_mismatch(self) -> None:
        with pytest.raises(ValidationError, match="totalRequirements"):
            Node3Metrics.model_validate({
                "totalGoals": 5, "leafGoals": 2,
                "confirmedObstacles": 3, "newObstacles": 1,
                "totalRequirements": 99, "must": 2, "should": 2, "could": 0,
            })

    def test_new_obstacle_wrong_prefix(self) -> None:
        with pytest.raises(ValidationError, match="O-N prefix"):
            NewObstacle.model_validate({
                "id": "O-US-1",  # should be O-N prefix
                "violatesGoals": ["G1"],
                "evidence": "some evidence",
                "description": "desc",
                "severity": "HIGH",
                "resolutionType": "New requirement",
            })

    def test_new_obstacle_correct_prefix(self) -> None:
        o = NewObstacle.model_validate({
            "id": "O-N1",
            "violatesGoals": ["G1"],
            "evidence": "some evidence",
            "description": "desc",
            "severity": "HIGH",
            "resolutionType": "New requirement",
        })
        assert o.id == "O-N1"
