# Multi-Agent Architecture Decision Record — AFK Mode

## Decision

**Single reasoning agent with two capability-isolation sub-agents.**

One well-prompted `CodingAgent` handles planning and implementation in a single context. Two sub-agents exist solely for capability isolation: `GitHubAgent` (git clone, push, PR) and `DBAgent` (migration apply, rollback). Both are capability gates, not peer reasoners.

## Why multi-agent

The initial multi-agent decision is justified by trust/capability isolation:

- `GitHubAgent` — scopes destructive git operations away from the main reasoning agent. A coding agent that also holds `git push` to a tenant's production repo is a security liability. Narrow tool grant, explicit approval gate before push.
- `DBAgent` — write access to a production database behind an explicit gate. Must not be held by the main reasoning agent. Rollback must be available before any migration runs.

## Why the planner/editor split was rejected

A proposed planner/editor split was rejected on two grounds:

**Principle 2 — conflicting implicit decisions.** The planner's choices about approach, module structure, naming, and test strategy constrain every line the editor writes. These agents share implicit decisions throughout. Running them as separate agents without full trace sharing produces inconsistent output. Running them with full trace sharing is one agent with a planning phase.

**Specialization alone.** A focused system prompt achieves the same "planner" and "editor" behavior in a single agent without the coordination cost. The skill explicitly rejects specialization as a justification for an agent boundary.

**The structural lesson:** a justified multi-agent decision (trust isolation for git/db) does not justify all subsequent boundaries. Each boundary requires its own reason from the four valid options — provably independent parallelism, context window hard limit, trust/capability isolation, or distributed team ownership. A system that justifies multi-agent via trust isolation and then adds a planner/editor split on top has re-introduced the specialization problem inside a valid architecture. The gate applies per boundary, not once at the system level.

## Why multi-tenancy doesn't change the topology

Multi-tenancy is an infrastructure concern, not an agent topology concern. Thousands of concurrent users requires isolated execution environments, tenant-scoped tool access, and resource limits per run. None of that requires more agents per task. It means one agent instance per user request, running in isolation — not more agents per request.

## Architecture

```
CodingAgent (Sonnet)
  → GitHubAgent.clone(repo)           ← capability agent, Haiku
  → [plan + implement, single context] ← no handoff, no boundary
  → DBAgent.migrate(if needed)         ← capability agent, Sonnet, gated
  → GitHubAgent.push(branch, PR)       ← capability agent, gated
```

**CodingAgent** uses `GitHubAgent` and `DBAgent` as tool-wrapped sub-agents via the tool-as-agent pattern — it sees `github_ops(request: str)` and `db_ops(request: str)`, not raw git or database tools.

## Compound reliability

3 sequential steps at 95% per-agent = 86% pipeline reliability — below the 95% default requirement. With one code-enforced retry per step (`1-(1-p)² = 99.75%` effective per-agent), the pipeline reaches 99%. Retry must be code-enforced in CodingAgent, not prompt-only.

## Irreversible action gates

Both `git push` and `migration apply` require CodingAgent to log an explicit confirmation before calling the capability agent. No silent execution of either operation.

## Open questions before building

1. **Tenant credential injection** — how are per-tenant GitHub credentials and DB connection strings passed to capability agents securely? Defines both agents' input schemas.
2. **DBAgent scope** — production database or sandbox? If production, the approval gate requires human confirmation, not just orchestrator confirmation.
3. **Task isolation mechanism** — how is each task's working directory enforced across tenants? Container-per-task or path validation in tool code.

## Disposition

**Proceed with conditions.** The topology is sound. Open questions 1–3 must be resolved before building — they define the input schemas for both capability agents and determine the security model for multi-tenancy.
