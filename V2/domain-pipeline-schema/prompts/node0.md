# Node 0 — Codebase Reconnaissance

## Purpose
Understand the codebase structure before dispatching sub-agents in later nodes. This node runs without sub-agents — you do it yourself by reading the directory tree and key config files. You produce the **Registry** that all subsequent nodes inherit.

## Input
The codebase root directory.

## Procedure

1. Read the top-level directory structure (2 levels deep).
2. Identify and read key config files: package.json, pyproject.toml, requirements.txt, Cargo.toml, go.mod, Dockerfile, docker-compose.yml, or equivalent.
3. Read any README.md, CLAUDE.md, or docs/ index files.
4. Read the database schema if present (migrations/, schema.sql, models/, prisma/schema.prisma, or equivalent).
5. Assign a 2-4 letter uppercase **area code** to each logical scan area for sub-agent dispatch. These codes become the ID prefixes for the entire pipeline.

## Output Schema

Produce a single JSON object conforming to this structure. No markdown. No preamble. Just the JSON.

```typescript
interface Node0Output {
  // ── Envelope (every node carries this) ──
  pipelineVersion: "0.1.0";
  node: 0;
  generatedAt: string;                  // ISO 8601 datetime
  registry: {
    project: string;                     // repo name
    version: "0.1.0";
    areas: AreaDef[];                    // one per scan area — THIS SEEDS ALL FUTURE IDs
  };

  // ── Node 0 payload ──
  identity: {
    repo: string;
    languages: string[];                 // e.g. ["TypeScript", "Python"]
    frameworks: string[];                // e.g. ["Next.js 16", "FastAPI"]
    packageManagers: string[];           // e.g. ["npm", "pip"]
  };
  architecture: {
    type: "monorepo" | "frontend-only" | "backend-only" | "fullstack";
    frontendDir: string | null;
    backendDir: string | null;
    sharedDir: string | null;
  };
  persistence: {
    database: string;                    // e.g. "Supabase/Postgres" or "none"
    orm: string;                         // e.g. "Prisma" or "none"
    schemaLocation: string | null;
    storage: string | null;              // e.g. "Supabase Storage", "S3"
  };
  externalServices: {
    name: string;
    purpose: string;
    configLocation: string;              // filepath where this service is configured
  }[];
  dispatchPlan: AreaDef[];               // same as registry.areas — the sub-agent assignments
  schemaEntities: {
    table: string;
    keyColumns: string[];
    relationships: string[];             // e.g. ["orders.user_id → users.id"]
  }[];
  keyFiles: {
    path: string;
    rationale: string;                   // why this file matters for domain analysis
  }[];                                   // 5-20 files
}

interface AreaDef {
  code: string;       // 2-4 UPPERCASE letters. e.g. "MS", "VP", "AUD"
  name: string;       // human-readable. e.g. "Meditation Session Service"
  directories: string[];  // which directories this area covers
}
```

## Area Code Assignment Rules

Area codes are the backbone of the entire pipeline. Every event, gap, obstacle, and requirement will inherit its prefix from these codes.

1. Each code must be **2-4 uppercase letters**, derived from the area name.
2. Codes must be **unique** across all areas.
3. Assign one area per logical sub-agent scan zone. Typical zones:
   - Backend routers/API handlers
   - Backend services/business logic
   - Backend agents/AI pipeline (if any)
   - Frontend hooks/state management
   - Frontend components with domain logic
4. If fewer than 15 source files total, use 2-3 areas instead of 5.
5. If no frontend or no backend exists, skip those areas.

## Constraints
- Do NOT scan test files, node_modules, __pycache__, .git, or build output.
- Do NOT read every file — only config, schema, and README-type files.
- Do NOT begin domain analysis. This node is purely structural reconnaissance.
- Output ONLY the JSON object. No markdown wrapping. No explanation before or after.
- If persistence.database is not "none", schemaEntities must be non-empty.
