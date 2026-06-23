---
name: multi-agent-orchestration
description: Design, implement, and debug multi-agent systems including agent graphs, task delegation, message passing, parallel execution, and coordination patterns. Triggers on requests about agent pipelines, orchestrators, subagents, agent networks, LLM routing, or multi-agent workflows.
---

# multi-agent-orchestration

You have the `multi-agent-orchestration` skill. Use it when the user wants to design or implement systems where multiple AI agents collaborate.

## Core Concepts

- **Orchestrator Agent**: A supervisor agent that routes tasks to specialist subagents
- **Subagent**: A focused agent with a specific role and toolset
- **Agent Graph**: A directed graph of agents and their communication flow
- **Task Delegation**: Breaking a complex task into subtasks and assigning them to appropriate agents
- **Parallel Execution**: Running multiple agents concurrently for speed
- **Message Passing**: How agents communicate results to each other

## Common Patterns

### 1. Supervisor Pattern
```
User → Orchestrator → [Analyst, Researcher, Writer, Coder] → Orchestrator → User
```

### 2. Pipeline Pattern
```
User → Agent A → Agent B → Agent C → User
```

### 3. Fan-out / Fan-in Pattern
```
User → Orchestrator → [Agent A, Agent B, Agent C] → Aggregator → User
```

### 4. Debate / Validation Pattern
```
User → Proposer Agent → Critic Agent → Resolver Agent → User
```

## Implementation Guidelines

### Defining Agent Roles
- Each agent should have a single, clear responsibility
- Define explicit input/output contracts for each agent
- Use descriptive role names (e.g., "Financial Analyst", "Risk Assessor")

### Task Decomposition
1. Identify the top-level goal
2. Break into parallel vs sequential subtasks
3. Define dependencies between subtasks
4. Assign each subtask to the most capable agent

### Communication
- Pass structured data (JSON) between agents when possible
- Include context and prior results in subsequent agent prompts
- Log inter-agent messages for debugging

### Error Handling
- Each agent should return status + result
- Orchestrator should handle agent failures gracefully
- Implement retry logic for transient failures

## For AI-Finance Context

Key agent roles for a financial AI system:
- **Market Data Agent**: Fetches and preprocesses market data
- **Quantitative Analyst Agent**: Runs models, backtests, computes metrics
- **Risk Agent**: Assesses portfolio risk, computes VaR/CVaR
- **Regulatory Compliance Agent**: Validates outputs against rules
- **Report Generation Agent**: Formats and presents results
- **UX Agent**: Handles user interaction and feedback loops

## Tools to Use

- `define_subagent` — Define a new specialized subagent
- `invoke_subagent` — Launch subagents in parallel or sequence
- `send_message` — Communicate with running subagents
- `manage_subagents` — Monitor and control active subagents

## Verification Checklist

- [ ] Each agent has a clearly defined role and scope
- [ ] Agents do not have overlapping responsibilities
- [ ] Communication contracts are well-defined
- [ ] Error handling and fallbacks are implemented
- [ ] Parallel vs sequential execution is optimized
- [ ] The orchestrator aggregates results coherently
