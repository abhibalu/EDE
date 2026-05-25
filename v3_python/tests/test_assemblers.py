"""Assembler tests: fragment -> node output."""

from ede.assemblers import assemble_node1, assemble_node2, assemble_node3
from ede.constraints import validate_node1, validate_node2
from ede.fragments import Node1Fragment, Node2Fragment, Node3Fragment
from ede.primitives import Registry


def _make_registry() -> Registry:
    return Registry.model_validate({
        "project": "TestApp",
        "version": "0.1.0",
        "areas": [
            {"code": "US", "name": "User Service", "directories": ["src/services/user"]},
            {"code": "OR", "name": "Order Service", "directories": ["src/services/order"]},
        ],
    })


def _make_node1_fragments() -> list[Node1Fragment]:
    return [
        Node1Fragment.model_validate({
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
                    "successorNames": ["UserActivated"],
                    "stateChange": "No user -> pending",
                    "evidence": "Line 42: await db.user.create({ status: 'pending' })",
                    "hotSpots": [],
                },
                {
                    "name": "UserActivated",
                    "trigger": "Email verification",
                    "location": {"file": "src/services/user/index.ts", "anchor": "verifyEmail"},
                    "predecessorNames": ["UserRegistered"],
                    "successorNames": [],
                    "stateChange": "pending -> active",
                    "evidence": "Line 78: await db.user.update({ status: 'active' })",
                    "hotSpots": [],
                },
            ],
        }),
        Node1Fragment.model_validate({
            "areaCode": "OR",
            "areaName": "Order Service",
            "filesScanned": ["src/services/order/index.ts"],
            "filesSkipped": [],
            "events": [
                {
                    "name": "OrderCreated",
                    "trigger": "POST /api/orders",
                    "location": {"file": "src/services/order/index.ts", "anchor": "createOrder"},
                    "predecessorNames": ["UserActivated"],
                    "successorNames": [],
                    "stateChange": "No order -> draft",
                    "evidence": "Line 15: const order = await db.order.create({ status: 'draft' })",
                    "hotSpots": [],
                },
            ],
        }),
    ]


class TestNode1Assembler:
    def test_basic_assembly(self):
        registry = _make_registry()
        fragments = _make_node1_fragments()
        result = assemble_node1(registry, fragments)
        assert len(result.output.events) == 3
        assert result.output.events[0].id == "E-US-01"
        assert result.output.events[1].id == "E-US-02"
        assert result.output.events[2].id == "E-OR-01"

    def test_name_to_id_resolution(self):
        registry = _make_registry()
        fragments = _make_node1_fragments()
        result = assemble_node1(registry, fragments)
        # UserRegistered should have successor E-US-02 (UserActivated)
        user_registered = result.output.events[0]
        assert "E-US-02" in user_registered.successors

    def test_symmetry_enforcement(self):
        registry = _make_registry()
        fragments = _make_node1_fragments()
        result = assemble_node1(registry, fragments)
        # OrderCreated has predecessor UserActivated, so UserActivated should get OrderCreated as successor
        user_activated = result.output.events[1]
        order_created = result.output.events[2]
        assert order_created.id in user_activated.successors
        assert user_activated.id in order_created.predecessors

    def test_deduplication(self):
        registry = _make_registry()
        fragments = _make_node1_fragments()
        # Add a duplicate event in a second fragment for the same area
        dup_fragment = Node1Fragment.model_validate({
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
                    "stateChange": "No user -> pending",
                    "evidence": "Line 42: await db.user.create({ status: 'pending' })",
                    "hotSpots": [],
                },
            ],
        })
        fragments.append(dup_fragment)
        result = assemble_node1(registry, fragments)
        # Should still only have 3 events (duplicate removed)
        assert len(result.output.events) == 3
        dedup_findings = [f for f in result.findings if f.rule == "ASSEMBLE-dedup"]
        assert len(dedup_findings) == 1

    def test_unresolved_link_produces_warning(self):
        registry = _make_registry()
        fragment = Node1Fragment.model_validate({
            "areaCode": "US",
            "areaName": "User Service",
            "filesScanned": ["src/services/user/index.ts"],
            "filesSkipped": [],
            "events": [
                {
                    "name": "UserRegistered",
                    "trigger": "POST /api/register",
                    "location": {"file": "src/services/user/index.ts", "anchor": "registerUser"},
                    "predecessorNames": ["NonExistentEvent"],
                    "successorNames": [],
                    "stateChange": "No user -> pending",
                    "evidence": "Line 42: await db.user.create({ status: 'pending' })",
                    "hotSpots": [],
                },
            ],
        })
        result = assemble_node1(registry, [fragment])
        warn_rules = [f.rule for f in result.findings if f.level == "WARN"]
        assert "ASSEMBLE-unresolved-predecessor" in warn_rules

    def test_per_area_truncation(self):
        """Areas with >15 events are truncated to 15."""
        registry = Registry.model_validate({
            "project": "TestApp", "version": "0.1.0",
            "areas": [{"code": "BG", "name": "Big Area", "directories": ["src/big"]}],
        })
        events = []
        for i in range(20):
            events.append({
                "name": f"Event{i + 1:02d}",
                "trigger": f"trigger {i}",
                "location": {"file": f"src/big/f{i}.ts", "anchor": f"fn{i}"},
                "predecessorNames": [],
                "successorNames": [],
                "stateChange": f"change {i}",
                "hotSpots": [],
                "evidence": f"Line {i}: some code evidence here",
            })
        fragment = Node1Fragment.model_validate({
            "areaCode": "BG", "areaName": "Big Area",
            "filesScanned": [f"src/big/f{i}.ts" for i in range(20)],
            "filesSkipped": [], "events": events,
        })
        result = assemble_node1(registry, [fragment])
        assert len(result.output.events) == 15
        assert result.output.truncation is not None
        assert result.output.truncation.estimated_total == 20
        assert "BG" in result.output.truncation.areas_affected
        trunc_findings = [f for f in result.findings if f.rule == "ASSEMBLE-area-truncation"]
        assert len(trunc_findings) == 1

    def test_no_truncation_below_threshold(self):
        """Areas with <=15 events are not truncated."""
        registry = _make_registry()
        fragments = _make_node1_fragments()
        result = assemble_node1(registry, fragments)
        assert result.output.truncation is None
        trunc_findings = [f for f in result.findings if f.rule == "ASSEMBLE-area-truncation"]
        assert len(trunc_findings) == 0

    def test_multi_area_independent_caps(self):
        """Each area is capped independently; one large area doesn't affect others."""
        registry = Registry.model_validate({
            "project": "TestApp", "version": "0.1.0",
            "areas": [
                {"code": "BG", "name": "Big", "directories": ["src/big"]},
                {"code": "SM", "name": "Small", "directories": ["src/small"]},
            ],
        })
        big_events = []
        for i in range(20):
            big_events.append({
                "name": f"BigEvent{i + 1:02d}",
                "trigger": f"trigger {i}",
                "location": {"file": f"src/big/f{i}.ts", "anchor": f"fn{i}"},
                "predecessorNames": [],
                "successorNames": [],
                "stateChange": f"change {i}",
                "hotSpots": [],
                "evidence": f"Line {i}: some big area code evidence",
            })
        small_events = []
        for i in range(5):
            small_events.append({
                "name": f"SmallEvent{i + 1:02d}",
                "trigger": f"trigger {i}",
                "location": {"file": f"src/small/f{i}.ts", "anchor": f"fn{i}"},
                "predecessorNames": [],
                "successorNames": [],
                "stateChange": f"change {i}",
                "hotSpots": [],
                "evidence": f"Line {i}: some small area code evidence",
            })
        fragments = [
            Node1Fragment.model_validate({
                "areaCode": "BG", "areaName": "Big",
                "filesScanned": [f"src/big/f{i}.ts" for i in range(20)],
                "filesSkipped": [], "events": big_events,
            }),
            Node1Fragment.model_validate({
                "areaCode": "SM", "areaName": "Small",
                "filesScanned": [f"src/small/f{i}.ts" for i in range(5)],
                "filesSkipped": [], "events": small_events,
            }),
        ]
        result = assemble_node1(registry, fragments)
        # BG truncated to 15, SM kept at 5 = 20 total
        assert len(result.output.events) == 20
        assert result.output.truncation is not None
        assert result.output.truncation.areas_affected == ["BG"]
        assert result.output.truncation.estimated_total == 25

    def test_assembled_output_passes_l1_and_l2(self):
        """Assembled output should pass both L1 (parsing) and L2+L3 (constraints)."""
        registry = _make_registry()
        fragments = _make_node1_fragments()
        result = assemble_node1(registry, fragments)
        # L1 already passed (output is a Node1Output)
        # L2+L3
        from ede.nodes.node0 import Node0Output
        n0 = Node0Output.model_validate({
            "pipelineVersion": "0.1.0",
            "node": 0,
            "generatedAt": result.output.generated_at.isoformat(),
            "registry": registry.model_dump(by_alias=True),
            "identity": {"repo": "test", "languages": ["TS"], "frameworks": [], "packageManagers": []},
            "architecture": {"type": "backend-only", "frontendDir": None, "backendDir": "src", "sharedDir": None},
            "persistence": {"database": "none", "orm": "none", "schemaLocation": None, "storage": None},
            "externalServices": [],
            "dispatchPlan": registry.model_dump(by_alias=True)["areas"],
            "schemaEntities": [],
            "keyFiles": [{"path": "src/index.ts", "rationale": "Entry point"}],
        })
        findings = validate_node1(result.output, n0)
        errors = [f for f in findings if f.level == "ERROR"]
        assert len(errors) == 0, f"L2+L3 errors: {errors}"


class TestNode2Assembler:
    def test_basic_assembly(self):
        registry = _make_registry()
        n1_fragments = _make_node1_fragments()
        n1_result = assemble_node1(registry, n1_fragments)

        n2_fragment = Node2Fragment.model_validate({
            "aggCode": "US",
            "aggName": "User",
            "rootEntity": "User",
            "keyFiles": [{"file": "src/services/user/index.ts", "anchor": "module"}],
            "states": [
                {"name": "Pending", "type": "atomic", "representation": "status='pending'", "location": {"file": "src/services/user/index.ts", "anchor": "42"}, "evidence": "Prisma enum UserStatus { PENDING ACTIVE }"},
                {"name": "Active", "type": "atomic", "representation": "status='active'", "location": {"file": "src/services/user/index.ts", "anchor": "78"}, "evidence": "Prisma enum UserStatus { PENDING ACTIVE }"},
            ],
            "transitions": [
                {"source": "Pending", "target": "Active", "eventName": "UserActivated", "guard": None, "sideEffects": [], "annotation": None},
            ],
            "gaps": [
                {"seq": 1, "severity": "MED", "description": "No deactivation path", "codeLocation": {"file": "src/services/user/index.ts", "anchor": "78"}},
            ],
            "trivialLifecycle": True,
        })

        result = assemble_node2(registry, [n2_fragment], n1_result.output)
        assert len(result.output.aggregates) == 1
        assert result.output.aggregates[0].code == "US"

    def test_gap_id_prefixing(self):
        registry = _make_registry()
        n1_fragments = _make_node1_fragments()
        n1_result = assemble_node1(registry, n1_fragments)

        n2_fragment = Node2Fragment.model_validate({
            "aggCode": "US",
            "aggName": "User",
            "rootEntity": "User",
            "keyFiles": [{"file": "src/services/user/index.ts", "anchor": "module"}],
            "states": [
                {"name": "Pending", "type": "atomic", "representation": "status='pending'", "location": {"file": "src/services/user/index.ts", "anchor": "42"}, "evidence": "Prisma enum UserStatus { PENDING ACTIVE }"},
            ],
            "transitions": [],
            "gaps": [
                {"seq": 1, "severity": "HIGH", "description": "gap1", "codeLocation": {"file": "a.ts", "anchor": "1"}},
                {"seq": 2, "severity": "LOW", "description": "gap2", "codeLocation": {"file": "a.ts", "anchor": "2"}},
            ],
            "trivialLifecycle": True,
        })

        result = assemble_node2(registry, [n2_fragment], n1_result.output)
        gaps = result.output.aggregates[0].gaps
        assert gaps[0].id == "US-G1"
        assert gaps[1].id == "US-G2"

    def test_gap_summary_computation(self):
        registry = _make_registry()
        n1_fragments = _make_node1_fragments()
        n1_result = assemble_node1(registry, n1_fragments)

        n2_fragment = Node2Fragment.model_validate({
            "aggCode": "US",
            "aggName": "User",
            "rootEntity": "User",
            "keyFiles": [{"file": "a.ts", "anchor": "m"}],
            "states": [
                {"name": "S1", "type": "atomic", "representation": "x", "location": {"file": "a.ts", "anchor": "1"}, "evidence": "some evidence for state discovery"},
            ],
            "transitions": [],
            "gaps": [
                {"seq": 1, "severity": "HIGH", "description": "g1", "codeLocation": {"file": "a.ts", "anchor": "1"}},
                {"seq": 2, "severity": "MED", "description": "g2", "codeLocation": {"file": "a.ts", "anchor": "2"}},
            ],
            "trivialLifecycle": True,
        })

        result = assemble_node2(registry, [n2_fragment], n1_result.output)
        gs = result.output.gap_summary
        assert gs.high == 1
        assert gs.med == 1
        assert gs.total == 2


class TestNode3Assembler:
    def test_basic_assembly(self):
        frags = [
            Node3Fragment.model_validate({
                "aggCode": "US",
                "aggName": "User",
                "newObstacles": [
                    {"seq": 1, "violatesGoals": ["G1.1"], "evidence": "src/user.ts:10 -- no rate limit", "description": "No rate limiting on registration", "severity": "HIGH", "resolutionType": "New requirement"},
                ],
            }),
            Node3Fragment.model_validate({
                "aggCode": "OR",
                "aggName": "Order",
                "newObstacles": [
                    {"seq": 1, "violatesGoals": ["G2.1"], "evidence": "src/order.ts:45 -- no stock check", "description": "Orders can be created for out-of-stock items", "severity": "HIGH", "resolutionType": "New requirement"},
                ],
            }),
        ]
        result = assemble_node3(frags)
        assert len(result.output) == 2
        assert result.output[0]["id"] == "O-N1"
        assert result.output[1]["id"] == "O-N2"

    def test_globally_sequential_ids(self):
        frags = [
            Node3Fragment.model_validate({
                "aggCode": "US",
                "aggName": "User",
                "newObstacles": [
                    {"seq": 1, "violatesGoals": ["G1.1"], "evidence": "a.ts:1 -- issue A", "description": "Issue A", "severity": "MED", "resolutionType": "New requirement"},
                    {"seq": 2, "violatesGoals": ["G1.1"], "evidence": "a.ts:2 -- issue B", "description": "Issue B", "severity": "LOW", "resolutionType": "New requirement"},
                ],
            }),
            Node3Fragment.model_validate({
                "aggCode": "OR",
                "aggName": "Order",
                "newObstacles": [
                    {"seq": 1, "violatesGoals": ["G2.1"], "evidence": "b.ts:1 -- issue C", "description": "Issue C", "severity": "HIGH", "resolutionType": "New requirement"},
                ],
            }),
        ]
        result = assemble_node3(frags)
        ids = [o["id"] for o in result.output]
        assert ids == ["O-N1", "O-N2", "O-N3"]

    def test_deduplication(self):
        frags = [
            Node3Fragment.model_validate({
                "aggCode": "US",
                "aggName": "User",
                "newObstacles": [
                    {"seq": 1, "violatesGoals": ["G1.1"], "evidence": "src/shared.ts:10 -- same issue", "description": "Shared issue found by both agents", "severity": "HIGH", "resolutionType": "New requirement"},
                ],
            }),
            Node3Fragment.model_validate({
                "aggCode": "OR",
                "aggName": "Order",
                "newObstacles": [
                    {"seq": 1, "violatesGoals": ["G2.1"], "evidence": "src/shared.ts:10 -- same issue", "description": "Shared issue found by both agents", "severity": "HIGH", "resolutionType": "New requirement"},
                ],
            }),
        ]
        result = assemble_node3(frags)
        assert len(result.output) == 1
        assert result.output[0]["id"] == "O-N1"
        dedup_findings = [f for f in result.findings if f.rule == "ASSEMBLE-dedup"]
        assert len(dedup_findings) == 1

    def test_empty_fragments(self):
        frags = [
            Node3Fragment.model_validate({
                "aggCode": "US",
                "aggName": "User",
                "newObstacles": [],
            }),
        ]
        result = assemble_node3(frags)
        assert len(result.output) == 0

    def test_output_fields_preserved(self):
        frags = [
            Node3Fragment.model_validate({
                "aggCode": "OR",
                "aggName": "Order",
                "newObstacles": [
                    {"seq": 1, "violatesGoals": ["G2.1"], "evidence": "src/order.ts:45", "description": "Missing validation", "severity": "CRITICAL", "resolutionType": "New requirement"},
                ],
            }),
        ]
        result = assemble_node3(frags)
        obs = result.output[0]
        assert obs["id"] == "O-N1"
        assert obs["violatesGoals"] == ["G2.1"]
        assert obs["severity"] == "CRITICAL"
        assert obs["resolutionType"] == "New requirement"
        assert obs["evidence"] == "src/order.ts:45"
        assert obs["description"] == "Missing validation"
