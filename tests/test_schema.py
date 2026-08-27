"""L1 positive tests: all 5 node fixtures parse through Pydantic."""

from ede.nodes import (
    Node0Output,
    Node1Output,
    Node2Output,
    Node3Output,
    Node4Output,
)


class TestSchemaValidation:
    def test_node0_parses(self, node0_data: dict) -> None:
        n0 = Node0Output.model_validate(node0_data)
        assert n0.node == 0
        assert n0.identity.repo == "test-app"
        assert len(n0.registry.areas) == 2

    def test_node1_parses(self, node1_data: dict) -> None:
        n1 = Node1Output.model_validate(node1_data)
        assert n1.node == 1
        assert len(n1.events) == 4
        assert n1.events[0].name == "UserRegistered"

    def test_node2_parses(self, node2_data: dict) -> None:
        n2 = Node2Output.model_validate(node2_data)
        assert n2.node == 2
        assert len(n2.aggregates) == 2
        assert n2.gap_summary.total == 3

    def test_node3_parses(self, node3_data: dict) -> None:
        n3 = Node3Output.model_validate(node3_data)
        assert n3.node == 3
        assert n3.goal_tree.id == "G0"
        assert len(n3.requirements) == 4

    def test_node4_parses(self, node4_data: dict) -> None:
        n4 = Node4Output.model_validate(node4_data)
        assert n4.node == 4
        assert len(n4.file_index) == 3
        assert n4.metrics.total_events == 4

    def test_all_nodes_parse(
        self, node0_data: dict, node1_data: dict, node2_data: dict,
        node3_data: dict, node4_data: dict,
    ) -> None:
        """Full pipeline L1 validation."""
        Node0Output.model_validate(node0_data)
        Node1Output.model_validate(node1_data)
        Node2Output.model_validate(node2_data)
        Node3Output.model_validate(node3_data)
        Node4Output.model_validate(node4_data)
