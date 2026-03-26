# Agent Orchestration

## Available Agents

Located in `~/.claude/agents/`. 170+ specialized agents available covering:

| Category | Key Agents | When to Use |
|----------|------------|-------------|
| Planning | planner, architect-reviewer | Complex features, architectural decisions |
| Testing | tdd-guide, integration-test-engineer, qa-expert, test-automator | New features, bug fixes, E2E flows |
| Code Quality | code-reviewer, refactoring-specialist | After writing code, code maintenance |
| Security | security-auditor, security-engineer, penetration-tester | Before commits, security analysis |
| Build | build-engineer, build-error-resolver | When build fails, optimization |
| Documentation | documentation-engineer, technical-writer | Updating docs |
| Language Review | typescript-reviewer, python-reviewer, rust-reviewer, go-reviewer, etc. | Language-specific code review |
| Infrastructure | docker-expert, kubernetes-specialist, terraform-engineer | Infra changes |
| DevOps | devops-engineer, ci-cd-engineer, deployment-engineer | Pipeline and deployment |

## Immediate Agent Usage

No user prompt needed:
1. Complex feature requests - Use **planner** agent
2. Code just written/modified - Use **code-reviewer** agent
3. Bug fix or new feature - Use **tdd-guide** agent
4. Architectural decision - Use **architect-reviewer** agent

## Parallel Task Execution

ALWAYS use parallel Task execution for independent operations:

```markdown
# GOOD: Parallel execution
Launch 3 agents in parallel:
1. Agent 1: Security analysis of auth module
2. Agent 2: Performance review of cache system
3. Agent 3: Type checking of utilities

# BAD: Sequential when unnecessary
First agent 1, then agent 2, then agent 3
```

## Multi-Perspective Analysis

For complex problems, use split role sub-agents:
- Factual reviewer
- Senior engineer
- Security expert
- Consistency reviewer
- Redundancy checker
