"""
Shared fixtures for all EDE tests.

All fixtures use camelCase dicts — this tests the JSON->model path,
which is what Claude Code actually produces. The round-trip verification
depends on this being right.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# -- Raw dict fixtures (camelCase, as Claude Code would produce) --------------


@pytest.fixture()
def registry_data() -> dict:
    return {
        "project": "TestApp",
        "version": "0.1.0",
        "areas": [
            {"code": "US", "name": "User Service", "directories": ["src/services/user"]},
            {"code": "OR", "name": "Order Service", "directories": ["src/services/order"]},
        ],
    }


@pytest.fixture()
def envelope_data(registry_data: dict) -> dict:
    return {
        "pipelineVersion": "0.1.0",
        "generatedAt": _now_iso(),
        "registry": registry_data,
    }


@pytest.fixture()
def node0_data(envelope_data: dict, registry_data: dict) -> dict:
    return {
        **envelope_data,
        "node": 0,
        "identity": {
            "repo": "test-app",
            "languages": ["TypeScript"],
            "frameworks": ["Express"],
            "packageManagers": ["npm"],
        },
        "architecture": {
            "type": "backend-only",
            "frontendDir": None,
            "backendDir": "src",
            "sharedDir": None,
        },
        "persistence": {
            "database": "PostgreSQL",
            "orm": "Prisma",
            "schemaLocation": "prisma/schema.prisma",
            "storage": None,
        },
        "externalServices": [
            {"name": "Stripe", "purpose": "Payments", "configLocation": "src/config/stripe.ts"},
        ],
        "dispatchPlan": registry_data["areas"],
        "schemaEntities": [
            {"table": "users", "keyColumns": ["id", "email", "status"], "relationships": ["orders.user_id"]},
            {"table": "orders", "keyColumns": ["id", "user_id", "status"], "relationships": ["users.id"]},
        ],
        "keyFiles": [
            {"path": "src/services/user/index.ts", "rationale": "User lifecycle logic"},
            {"path": "src/services/order/index.ts", "rationale": "Order state machine"},
        ],
    }


@pytest.fixture()
def node1_data(envelope_data: dict) -> dict:
    return {
        **envelope_data,
        "node": 1,
        "metadata": {
            "totalFilesScanned": 12,
            "scanAreas": [
                {
                    "name": "User Service",
                    "areaCode": "US",
                    "directories": ["src/services/user"],
                    "filesScanned": ["src/services/user/index.ts", "src/services/user/auth.ts"],
                    "filesSkipped": [],
                },
                {
                    "name": "Order Service",
                    "areaCode": "OR",
                    "directories": ["src/services/order"],
                    "filesScanned": ["src/services/order/index.ts"],
                    "filesSkipped": [],
                },
            ],
        },
        "events": [
            {
                "id": "E-US-01",
                "name": "UserRegistered",
                "trigger": "POST /api/register with valid payload",
                "location": {"file": "src/services/user/index.ts", "anchor": "registerUser"},
                "predecessors": [],
                "successors": ["E-US-02"],
                "stateChange": "No user -> user record with status='pending'",
                "hotSpots": [],
                "evidence": "Line 42: await db.user.create({ data: { ...input, status: 'pending' } })",
            },
            {
                "id": "E-US-02",
                "name": "UserActivated",
                "trigger": "Email verification link clicked",
                "location": {"file": "src/services/user/auth.ts", "anchor": "verifyEmail"},
                "predecessors": ["E-US-01"],
                "successors": [],
                "stateChange": "user.status: 'pending' -> 'active'",
                "hotSpots": [],
                "evidence": "Line 78: await db.user.update({ where: { id }, data: { status: 'active' } })",
            },
            {
                "id": "E-OR-01",
                "name": "OrderCreated",
                "trigger": "POST /api/orders by authenticated user",
                "location": {"file": "src/services/order/index.ts", "anchor": "createOrder"},
                "predecessors": ["E-US-02"],
                "successors": ["E-OR-02"],
                "stateChange": "No order -> order with status='draft'",
                "hotSpots": [],
                "evidence": "Line 15: const order = await db.order.create({ data: { userId, status: 'draft' } })",
            },
            {
                "id": "E-OR-02",
                "name": "OrderSubmitted",
                "trigger": "User confirms order",
                "location": {"file": "src/services/order/index.ts", "anchor": "submitOrder"},
                "predecessors": ["E-OR-01"],
                "successors": [],
                "stateChange": "order.status: 'draft' -> 'submitted'",
                "hotSpots": [
                    {
                        "description": "No payment validation before submission",
                        "location": {"file": "src/services/order/index.ts", "anchor": "submitOrder:28"},
                    },
                ],
                "evidence": "Line 30: await db.order.update({ where: { id }, data: { status: 'submitted' } })",
            },
        ],
        "hotSpotSummary": [
            {
                "description": "No payment validation before submission",
                "location": {"file": "src/services/order/index.ts", "anchor": "submitOrder:28"},
            },
        ],
        "truncation": None,
    }


@pytest.fixture()
def node2_data(envelope_data: dict) -> dict:
    return {
        **envelope_data,
        "node": 2,
        "aggregates": [
            {
                "code": "US",
                "name": "User",
                "rootEntity": "User",
                "keyFiles": [
                    {"file": "src/services/user/index.ts", "anchor": "module"},
                    {"file": "src/services/user/auth.ts", "anchor": "module"},
                ],
                "states": [
                    {
                        "name": "Pending",
                        "type": "atomic",
                        "representation": "status = 'pending'",
                        "location": {"file": "src/services/user/index.ts", "anchor": "42"},
                        "evidence": "Prisma enum UserStatus { PENDING ACTIVE SUSPENDED }",
                    },
                    {
                        "name": "Active",
                        "type": "atomic",
                        "representation": "status = 'active'",
                        "location": {"file": "src/services/user/auth.ts", "anchor": "78"},
                        "evidence": "Prisma enum UserStatus { PENDING ACTIVE SUSPENDED }",
                    },
                ],
                "transitions": [
                    {
                        "source": "Pending",
                        "target": "Active",
                        "event": "E-US-02",
                        "guard": "valid email token",
                        "sideEffects": ["send welcome email"],
                        "annotation": None,
                        "evidence": "user.status = 'active' on line 92",
                        "codeLocation": {"file": "src/services/user/auth.ts", "anchor": "92"},
                    },
                ],
                "gaps": [
                    {
                        "id": "US-G1",
                        "severity": "MED",
                        "description": "No transition from Active back to any state (no deactivation path)",
                        "codeLocation": {"file": "src/services/user/auth.ts", "anchor": "78"},
                    },
                ],
                "trivialLifecycle": True,
            },
            {
                "code": "OR",
                "name": "Order",
                "rootEntity": "Order",
                "keyFiles": [{"file": "src/services/order/index.ts", "anchor": "module"}],
                "states": [
                    {
                        "name": "Draft",
                        "type": "atomic",
                        "representation": "status = 'draft'",
                        "location": {"file": "src/services/order/index.ts", "anchor": "15"},
                        "evidence": "Line 15: status: 'draft' in create call",
                    },
                    {
                        "name": "Submitted",
                        "type": "atomic",
                        "representation": "status = 'submitted'",
                        "location": {"file": "src/services/order/index.ts", "anchor": "30"},
                        "evidence": "Line 30: status: 'submitted' in update call",
                    },
                ],
                "transitions": [
                    {
                        "source": "Draft",
                        "target": "Submitted",
                        "event": "E-OR-02",
                        "guard": None,
                        "sideEffects": [],
                        "annotation": None,
                        "evidence": "order.status = 'submitted' on line 30",
                        "codeLocation": {"file": "src/services/order/index.ts", "anchor": "30"},
                    },
                ],
                "gaps": [
                    {
                        "id": "OR-G1",
                        "severity": "HIGH",
                        "description": "No payment validation before submission",
                        "codeLocation": {"file": "src/services/order/index.ts", "anchor": "submitOrder:28"},
                    },
                    {
                        "id": "OR-G2",
                        "severity": "MED",
                        "description": "Submitted is a dead-end state -- no fulfilment or cancellation path",
                        "codeLocation": {"file": "src/services/order/index.ts", "anchor": "30"},
                    },
                ],
                "trivialLifecycle": True,
            },
        ],
        "crossAggTransitions": [
            {
                "fromEvent": "E-US-02",
                "fromAggregate": "US",
                "toEvent": "E-OR-01",
                "toAggregate": "OR",
                "mechanism": "User must be active to create orders (auth middleware)",
            },
        ],
        "impossibleCombinations": [],
        "migrationPriority": [
            {"rank": 1, "aggregate": "OR", "rationale": "Most gaps and most complex lifecycle"},
            {"rank": 2, "aggregate": "US", "rationale": "Simpler but foundational"},
        ],
        "gapSummary": {"critical": 0, "high": 1, "med": 2, "low": 0, "total": 3},
    }


@pytest.fixture()
def node3_data(envelope_data: dict) -> dict:
    return {
        **envelope_data,
        "node": 3,
        "goalTree": {
            "id": "G0",
            "description": "Enable users to register, browse, and place orders",
            "decomposition": "AND",
            "agent": None,
            "children": [
                {
                    "id": "G1",
                    "description": "Manage user lifecycle",
                    "decomposition": "AND",
                    "agent": None,
                    "children": [
                        {
                            "id": "G1.1",
                            "description": "Allow self-service registration and activation",
                            "decomposition": None,
                            "agent": "[Software: UserService]",
                            "children": [],
                            "obstacleRefs": ["O-US-1"],
                        },
                    ],
                    "obstacleRefs": [],
                },
                {
                    "id": "G2",
                    "description": "Manage order lifecycle",
                    "decomposition": "AND",
                    "agent": None,
                    "children": [
                        {
                            "id": "G2.1",
                            "description": "Allow order creation and submission",
                            "decomposition": None,
                            "agent": "[Software: OrderService]",
                            "children": [],
                            "obstacleRefs": ["O-OR-1", "O-OR-2"],
                        },
                    ],
                    "obstacleRefs": [],
                },
            ],
            "obstacleRefs": [],
        },
        "confirmedObstacles": [
            {
                "id": "O-US-1",
                "violatesGoals": ["G1.1"],
                "gapSource": "US-G1",
                "description": "No deactivation path -- user can never be suspended or deleted",
                "severity": "MED",
            },
            {
                "id": "O-OR-1",
                "violatesGoals": ["G2.1"],
                "gapSource": "OR-G1",
                "description": "No payment validation before submission",
                "severity": "HIGH",
            },
            {
                "id": "O-OR-2",
                "violatesGoals": ["G2.1"],
                "gapSource": "OR-G2",
                "description": "Submitted is a dead-end -- no fulfilment or cancellation",
                "severity": "MED",
            },
        ],
        "newObstacles": [
            {
                "id": "O-N1",
                "violatesGoals": ["G2.1"],
                "evidence": "src/services/order/index.ts:createOrder -- no stock check",
                "description": "Orders can be created for out-of-stock items",
                "severity": "HIGH",
                "resolutionType": "New requirement",
            },
        ],
        "requirements": [
            {
                "id": "R-US-01",
                "priority": "SHOULD",
                "description": "Add user deactivation/suspension endpoint",
                "resolves": ["O-US-1"],
            },
            {
                "id": "R-OR-01",
                "priority": "MUST",
                "description": "Validate payment method before allowing order submission",
                "resolves": ["O-OR-1"],
            },
            {
                "id": "R-OR-02",
                "priority": "SHOULD",
                "description": "Add order fulfilment and cancellation states and transitions",
                "resolves": ["O-OR-2"],
            },
            {
                "id": "R-OR-03",
                "priority": "MUST",
                "description": "Check stock availability during order creation",
                "resolves": ["O-N1"],
            },
        ],
        "roadmap": [
            {
                "number": 1,
                "name": "Payment & Stock Safety",
                "scope": "Close MUST requirements on Order aggregate",
                "requirements": ["R-OR-01", "R-OR-03"],
                "gapsClosed": ["OR-G1", "O-N1"],
                "riskReduced": "Orders can no longer be submitted without payment or for out-of-stock items",
            },
            {
                "number": 2,
                "name": "Order Lifecycle Completion",
                "scope": "Add fulfilment path and user management",
                "requirements": ["R-OR-02", "R-US-01"],
                "gapsClosed": ["OR-G2", "US-G1"],
                "riskReduced": "Full lifecycle coverage for orders and users",
            },
        ],
        "metrics": {
            "totalGoals": 5,
            "leafGoals": 2,
            "confirmedObstacles": 3,
            "newObstacles": 1,
            "totalRequirements": 4,
            "must": 2,
            "should": 2,
            "could": 0,
        },
    }


@pytest.fixture()
def node4_data(envelope_data: dict) -> dict:
    return {
        **envelope_data,
        "node": 4,
        "systemPurpose": "TestApp is an e-commerce backend enabling user registration and order management.",
        "fileIndex": [
            {"file": "src/services/user/index.ts", "category": "backend-service", "requirements": ["R-US-01"]},
            {"file": "src/services/user/auth.ts", "category": "backend-service", "requirements": ["R-US-01"]},
            {"file": "src/services/order/index.ts", "category": "backend-service", "requirements": ["R-OR-01", "R-OR-02", "R-OR-03"]},
        ],
        "changelog": [{"date": "2026-04-26", "change": "Baseline: initial spec from 5-node pipeline"}],
        "metrics": {
            "totalGoals": 5,
            "totalAggregates": 2,
            "totalEvents": 4,
            "totalGaps": 3,
            "confirmedObstacles": 3,
            "newObstacles": 1,
            "totalRequirements": 4,
            "must": 2,
            "should": 2,
            "could": 0,
            "phases": 2,
            "filesIndexed": 3,
        },
        "sources": {
            "node0": "pipeline/output/00-recon.json",
            "node1": "pipeline/output/01-events.json",
            "node2": "pipeline/output/02-statecharts.json",
            "node3": "pipeline/output/03-goals.json",
        },
    }
