"""L2+L3 constraint validation tests."""

import copy

from ede.constraints import validate_pipeline
from ede.nodes import (
    Node0Output,
    Node1Output,
    Node2Output,
    Node3Output,
    Node4Output,
)


def _parse_pipeline(n0d, n1d, n2d, n3d, n4d):
    return {
        "node0": Node0Output.model_validate(n0d),
        "node1": Node1Output.model_validate(n1d),
        "node2": Node2Output.model_validate(n2d),
        "node3": Node3Output.model_validate(n3d),
        "node4": Node4Output.model_validate(n4d),
    }


class TestFullPipeline:
    def test_valid_pipeline(
        self, node0_data, node1_data, node2_data, node3_data, node4_data,
    ):
        pipeline = _parse_pipeline(node0_data, node1_data, node2_data, node3_data, node4_data)
        result = validate_pipeline(pipeline)
        errors = [f for f in result["findings"] if f.level == "ERROR"]
        assert result["valid"], f"Pipeline should be valid, got errors: {errors}"

    def test_partial_pipeline_node0_only(self, node0_data):
        n0 = Node0Output.model_validate(node0_data)
        result = validate_pipeline({"node0": n0})
        assert result["valid"]

    def test_partial_pipeline_node0_node1(self, node0_data, node1_data):
        n0 = Node0Output.model_validate(node0_data)
        n1 = Node1Output.model_validate(node1_data)
        result = validate_pipeline({"node0": n0, "node1": n1})
        assert result["valid"]


class TestNode1Constraints:
    def test_broken_predecessor_ref(self, node0_data, node1_data):
        data = copy.deepcopy(node1_data)
        data["events"][0]["predecessors"] = ["E-XX-99"]
        n0 = Node0Output.model_validate(node0_data)
        n1 = Node1Output.model_validate(data)
        result = validate_pipeline({"node0": n0, "node1": n1})
        error_rules = [f.rule for f in result["findings"] if f.level == "ERROR"]
        assert "L2-predecessor-resolves" in error_rules

    def test_duplicate_event_id(self, node0_data, node1_data):
        data = copy.deepcopy(node1_data)
        # Duplicate the first event
        data["events"].append(copy.deepcopy(data["events"][0]))
        n0 = Node0Output.model_validate(node0_data)
        n1 = Node1Output.model_validate(data)
        result = validate_pipeline({"node0": n0, "node1": n1})
        error_rules = [f.rule for f in result["findings"] if f.level == "ERROR"]
        assert "L2-unique-event-ids" in error_rules

    def test_self_reference_detected(self, node0_data, node1_data):
        data = copy.deepcopy(node1_data)
        data["events"][0]["predecessors"] = ["E-US-01"]  # self-reference
        n0 = Node0Output.model_validate(node0_data)
        n1 = Node1Output.model_validate(data)
        result = validate_pipeline({"node0": n0, "node1": n1})
        error_rules = [f.rule for f in result["findings"] if f.level == "ERROR"]
        assert "L3-no-self-reference" in error_rules


class TestNode2Constraints:
    def test_gap_prefix_mismatch(self, node0_data, node1_data, node2_data):
        data = copy.deepcopy(node2_data)
        # Change gap ID prefix to not match aggregate
        data["aggregates"][0]["gaps"][0]["id"] = "XX-G1"
        data["gapSummary"] = {"critical": 0, "high": 1, "med": 2, "low": 0, "total": 3}
        n0 = Node0Output.model_validate(node0_data)
        n1 = Node1Output.model_validate(node1_data)
        n2 = Node2Output.model_validate(data)
        result = validate_pipeline({"node0": n0, "node1": n1, "node2": n2})
        error_rules = [f.rule for f in result["findings"] if f.level == "ERROR"]
        assert "L2-gap-prefix" in error_rules

    def test_dead_end_state_warning(self, node0_data, node1_data, node2_data):
        """The fixture has dead-end states (Active, Submitted) -- should produce warnings."""
        n0 = Node0Output.model_validate(node0_data)
        n1 = Node1Output.model_validate(node1_data)
        n2 = Node2Output.model_validate(node2_data)
        result = validate_pipeline({"node0": n0, "node1": n1, "node2": n2})
        warn_rules = [f.rule for f in result["findings"] if f.level == "WARN"]
        assert "L3-no-dead-ends" in warn_rules


class TestNode3Constraints:
    def test_critical_without_must(self, node0_data, node1_data, node2_data, node3_data):
        data = copy.deepcopy(node3_data)
        # Make an obstacle CRITICAL but ensure no MUST requirement resolves it
        data["confirmedObstacles"][0]["severity"] = "CRITICAL"
        # Change the requirement that resolves it to SHOULD
        for req in data["requirements"]:
            if "O-US-1" in req["resolves"]:
                req["priority"] = "SHOULD"
        # Fix metrics
        data["metrics"]["must"] = 1
        data["metrics"]["should"] = 3
        n0 = Node0Output.model_validate(node0_data)
        n1 = Node1Output.model_validate(node1_data)
        n2 = Node2Output.model_validate(node2_data)
        n3 = Node3Output.model_validate(data)
        result = validate_pipeline({"node0": n0, "node1": n1, "node2": n2, "node3": n3})
        warn_rules = [f.rule for f in result["findings"] if f.level == "WARN"]
        assert "L3-critical-needs-must" in warn_rules


class TestNode4Constraints:
    def test_metrics_consistency(
        self, node0_data, node1_data, node2_data, node3_data, node4_data,
    ):
        data = copy.deepcopy(node4_data)
        data["metrics"]["totalEvents"] = 999  # wrong
        n0 = Node0Output.model_validate(node0_data)
        n1 = Node1Output.model_validate(node1_data)
        n2 = Node2Output.model_validate(node2_data)
        n3 = Node3Output.model_validate(node3_data)
        n4 = Node4Output.model_validate(data)
        result = validate_pipeline({"node0": n0, "node1": n1, "node2": n2, "node3": n3, "node4": n4})
        warn_rules = [f.rule for f in result["findings"] if f.level == "WARN"]
        assert "L3-metrics-consistency" in warn_rules
