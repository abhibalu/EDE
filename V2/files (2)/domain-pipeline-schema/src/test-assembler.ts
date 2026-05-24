/**
 * Test the Node 1 assembler with realistic fragments.
 * Run with: npx tsx src/test-assembler.ts
 */

import { Node1Fragment } from "./fragments.js";
import { Node1Output } from "./nodes/node1.js";
import { assembleNode1 } from "./assemblers.js";
import { validateNode1 } from "./constraints.js";

const registry = {
  project: "TestApp",
  version: "0.1.0" as const,
  areas: [
    { code: "US", name: "User Service", directories: ["src/user"] },
    { code: "OR", name: "Order Service", directories: ["src/order"] },
  ],
};

// ── Fragment from User Service sub-agent ──
const userFragment = Node1Fragment.parse({
  areaCode: "US",
  areaName: "User Service",
  filesScanned: ["src/user/index.ts", "src/user/auth.ts"],
  filesSkipped: [],
  events: [
    {
      name: "UserRegistered",
      trigger: "POST /api/register",
      location: { file: "src/user/index.ts", anchor: "registerUser" },
      predecessorNames: [],
      successorNames: ["UserActivated"],
      stateChange: "none → pending",
      evidence: "Line 42: await db.user.create({ status: 'pending' })",
      hotSpots: [],
    },
    {
      name: "UserActivated",
      trigger: "Email verification",
      location: { file: "src/user/auth.ts", anchor: "verifyEmail" },
      predecessorNames: ["UserRegistered"],
      successorNames: [],
      stateChange: "pending → active",
      evidence: "Line 78: await db.user.update({ status: 'active' })",
      hotSpots: [],
    },
  ],
});

// ── Fragment from Order Service sub-agent ──
const orderFragment = Node1Fragment.parse({
  areaCode: "OR",
  areaName: "Order Service",
  filesScanned: ["src/order/index.ts"],
  filesSkipped: ["src/order/types.ts — type definitions only"],
  events: [
    {
      name: "OrderCreated",
      trigger: "POST /api/orders",
      location: { file: "src/order/index.ts", anchor: "createOrder" },
      predecessorNames: ["UserActivated"],  // ← cross-area link by name!
      successorNames: ["OrderSubmitted"],
      stateChange: "none → draft",
      evidence: "Line 15: await db.order.create({ status: 'draft' })",
      hotSpots: [],
    },
    {
      name: "OrderSubmitted",
      trigger: "User confirms order",
      location: { file: "src/order/index.ts", anchor: "submitOrder" },
      predecessorNames: ["OrderCreated"],
      successorNames: [],
      stateChange: "draft → submitted",
      evidence: "Line 30: await db.order.update({ status: 'submitted' })",
      hotSpots: [
        {
          description: "No payment validation",
          location: { file: "src/order/index.ts", anchor: "submitOrder:28" },
        },
      ],
    },
  ],
});

// ── Assemble ──
console.log("=== Assembling Node 1 from fragments ===\n");

const { output, findings: assemblyFindings } = assembleNode1({
  registry,
  fragments: [userFragment, orderFragment],
});

// Show assembly findings
if (assemblyFindings.length > 0) {
  console.log("Assembly findings:");
  for (const f of assemblyFindings) {
    const icon = f.level === "ERROR" ? "❌" : f.level === "WARN" ? "⚠️" : "ℹ️";
    console.log(`  ${icon} ${f.where}: ${f.message}`);
  }
  console.log();
}

// ── Verify the assembled output ──
console.log("=== Checking assembled output ===\n");

// 1. IDs assigned correctly
console.log("Event IDs:");
for (const e of output.events) {
  console.log(`  ${e.id} — ${e.name}`);
}
console.log();

// 2. Cross-area links resolved
console.log("Cross-area link resolution:");
const orderCreated = output.events.find((e) => e.name === "OrderCreated")!;
const userActivated = output.events.find((e) => e.name === "UserActivated")!;
console.log(`  OrderCreated.predecessors = [${orderCreated.predecessors}]`);
console.log(`  UserActivated.successors  = [${userActivated.successors}]`);
console.log(`  ↑ Cross-area link: User → Order resolved by name matching`);
console.log();

// 3. Symmetry enforced
console.log("Symmetry check:");
for (const e of output.events) {
  for (const succId of e.successors) {
    const succ = output.events.find((s) => s.id === succId)!;
    const symmetric = succ.predecessors.includes(e.id);
    console.log(`  ${e.name} → ${succ.name}: ${symmetric ? "✅ symmetric" : "❌ broken"}`);
  }
}
console.log();

// 4. L1 schema validation
console.log("=== L1 Schema Validation ===");
try {
  Node1Output.parse(output);
  console.log("✅ Assembled output passes schema validation\n");
} catch (e: any) {
  console.log("❌ Schema validation failed:", e.errors);
}

// 5. L2+L3 constraint validation
console.log("=== L2+L3 Constraint Validation ===");
const n0 = {
  pipelineVersion: "0.1.0" as const,
  node: 0 as const,
  generatedAt: new Date().toISOString(),
  registry,
  identity: { repo: "test", languages: ["TS"], frameworks: [], packageManagers: [] },
  architecture: { type: "backend-only" as const, frontendDir: null, backendDir: "src", sharedDir: null },
  persistence: { database: "postgres", orm: "prisma", schemaLocation: "prisma/schema.prisma", storage: null },
  externalServices: [],
  dispatchPlan: registry.areas,
  schemaEntities: [{ table: "users", keyColumns: ["id"], relationships: [] }],
  keyFiles: [{ path: "src/user/index.ts", rationale: "user logic" }],
};

const constraintFindings = validateNode1(output, n0);
for (const f of constraintFindings) {
  const icon = f.level === "ERROR" ? "❌" : f.level === "WARN" ? "⚠️" : "ℹ️";
  console.log(`  ${icon} ${f.where}: ${f.message} [${f.rule}]`);
}
if (constraintFindings.length === 0) {
  console.log("  ✅ No constraint violations");
}

console.log("\n=== Summary ===");
console.log(`Events assembled: ${output.events.length}`);
console.log(`Files scanned: ${output.metadata.totalFilesScanned}`);
console.log(`Hot spots: ${output.hotSpotSummary.length}`);
console.log(`Assembly findings: ${assemblyFindings.length}`);
console.log(`Constraint findings: ${constraintFindings.length}`);
