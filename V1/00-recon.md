# Node 0 — Codebase Reconnaissance

## Purpose
Understand the codebase structure before dispatching sub-agents in later nodes. This node runs without sub-agents — you do it yourself by reading the directory tree and key config files.

## Procedure

1. Read the top-level directory structure (2 levels deep).
2. Identify and read key config files: package.json, pyproject.toml, requirements.txt, Cargo.toml, go.mod, Dockerfile, docker-compose.yml, or equivalent.
3. Read any README.md, CLAUDE.md, or docs/ index files.
4. Read the database schema if present (migrations/, schema.sql, models/, prisma/schema.prisma, or equivalent).

## Output Format

Your first line must be `# Codebase Reconnaissance`. No preamble.

```markdown
# Codebase Reconnaissance

## Identity
- **Repo name**: [name]
- **Primary languages**: [e.g., TypeScript, Python]
- **Frameworks**: [e.g., Next.js 16, FastAPI]
- **Package manager(s)**: [e.g., npm, pip, cargo]

## Architecture
- **Type**: [monorepo | frontend-only | backend-only | fullstack-split]
- **Frontend dir**: [path or "none"]
- **Backend dir**: [path or "none"]
- **Shared/common dir**: [path or "none"]

## Persistence
- **Database**: [e.g., Supabase/Postgres, SQLite, none]
- **ORM/query layer**: [e.g., Prisma, SQLAlchemy, raw SQL]
- **Schema location**: [filepath]
- **Storage**: [e.g., Supabase Storage, S3, local filesystem]

## External Services
List every external API or service dependency found in config/code:
| Service | Purpose | Config Location |
|---------|---------|-----------------|
| [name]  | [what for] | [filepath] |

## Directory Map for Sub-Agent Dispatch
Recommend how later nodes should split the codebase for sub-agents:

| Sub-agent | Target directory | Rationale |
|-----------|-----------------|-----------|
| Backend Routers | [path] | API endpoint handlers |
| Backend Services | [path] | Business logic |
| Backend Agents | [path] | AI/ML pipeline (if exists) |
| Frontend Hooks | [path] | State management + side effects |
| Frontend Components | [path] | Components with domain logic |

If fewer than 15 source files total, recommend 2-3 sub-agents instead of 5.
If no frontend or no backend exists, note which sub-agents to skip.

## Schema Summary
List the main database tables/collections with their columns and relationships:
| Table | Key Columns | Relationships |
|-------|------------|---------------|
| [name] | [columns] | [FK references] |

If no schema found, note: "No schema file found — state may be client-side only."

## Key Files for Domain Analysis
List the 10-15 most important files for domain event extraction (files most likely to contain state changes, business logic, and lifecycle management):
| File | Why it matters |
|------|---------------|
| [path] | [reason] |
```

## Constraints
- Do NOT scan test files, node_modules, __pycache__, .git, or build output.
- Do NOT read every file — only config, schema, and README-type files.
- Do NOT begin domain analysis. This node is purely structural reconnaissance.
- Keep the output under 300 lines. This is a map, not the territory.
