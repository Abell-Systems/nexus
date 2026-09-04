# ADR 0009: Provider-Agnostic Agent Invocation and Decoupled LLM Runtime

**Status:** Proposed  
**Date:** 2026-09-04  
**Scope:** Repository-wide (`domain/protocols/agents.py`, `application/synthesis/`, `infrastructure/adk/`, `infrastructure/llm/`, `backend/requirements.txt`, `.importlinter`)  

---

## Context

Under ADR 0002 (Clean Architecture), ADR 0004 (Matching Engine Contract), and ADR 0008 (Automated Architectural Enforcement), Nexus is governed by a core invariant: **the engine solves the problem through decoupled architecture, never via vendor lock-in or opportunistic coupling**.

During initial prototyping, the repository declared:
```text
google-adk[extensions]==2.7.0
```
as a global top-level dependency in `backend/requirements.txt`.

An audit of this dependency revealed two severe liabilities:
1. **Architectural Contamination:** `google-adk[extensions]` pulls hundreds of megabytes of transitive dependencies across competing frameworks—including Anthropic, OpenAI, LiteLLM, LangGraph, LlamaIndex, Kubernetes, and boto3. This conflated the Nexus core (pure deterministic information retrieval, evaluation, and matching) with multi-agent orchestration frameworks.
2. **CI Bloat & Inefficient Economics:** In CI, every pull request—even those touching only evaluation metrics or SQL data normalizers—was forced to restore over 310 MB of wheels and spend 1 to 2 minutes resolving and installing massive vendor SDKs.
3. **Vendor Asymmetry:** While Nexus evaluated prior art using Groq (`llama-3.3-70b-versatile` via an OpenAI-compatible interface) and Google ADK in parallel, the application layer was vulnerable to concrete SDK dependencies.

## Decision

We establish that **Nexus Core is completely provider-agnostic and does not depend on any agent framework or LLM vendor SDK**.

### 1. Architectural Model

```text
                    ┌──────────────────────────┐
                    │        Nexus Core        │
                    │                          │
                    │ domain/protocols/agents   │
                    │ application/synthesis    │
                    │ application/evaluation   │
                    │ application/matching     │
                    └────────────┬─────────────┘
                                 │
                         Agent Invoker Port
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                  │
        ┌─────▼──────┐     ┌─────▼──────┐     ┌─────▼──────┐
        │   Google   │     │    Groq/   │     │  Anthropic │
        │ ADK Adapter│     │OpenAI Adapt│     │   Adapter  │
        └────────────┘     └────────────┘     └────────────┘
```

The core defines **business capabilities and contracts**, not vendor SDKs or LLM transport details:
1. **`domain/protocols/agents.py`** declares capability ports:
   - `InventorAgentProtocol`: receives demand signals and prior art, returns typed `InventionCandidate`.
   - `AdversarialAgentProtocol`: attacks candidates with prior art citations, returns typed `AdversarialVerdict`.
   - `GovernorAgentProtocol`: evaluates novelty, risk, and differentiation, returns typed `ScoreCard`.
   These ports contain zero LLM transport abstractions (no chat completions, prompts, temperatures, or token counts).
2. **`application/synthesis`** orchestrates invention use cases exclusively through these domain capability ports via dependency injection (`SynthesisEngine(inventor=..., adversarial=...)`).
3. **`infrastructure`** houses concrete provider adapters and externalized configuration:
   - `infrastructure/llm/provider_config.py`: `ProviderConfig` externalizing endpoint base URL, model name, credentials, and timeouts.
   - `infrastructure/llm/client_protocol.py`: low-level LLM transport protocol (`LlmClientProtocol`).
   - `infrastructure/llm/groq_client.py`: lightweight HTTP transport client implementing `LlmClientProtocol` using injected `ProviderConfig`.
   - `infrastructure/llm/adapters.py`: `LlmAgentAdapter` adapting capability ports (`InventorAgentProtocol`, `AdversarialAgentProtocol`) to concrete LLM transports.
   - `infrastructure/adk/`: Google ADK multi-agent workflow adapter.
4. **Clean Architecture Isolation:**
   Neither `domain` nor `application` may import `google`, `openai`, `anthropic`, `litellm`, `langgraph`, `llama_index`, or any external provider SDK.

### 2. Dependency Stratification

Dependencies are segregated into clear, orthogonal files:

1. **`backend/requirements.txt` (Core Runtime):**
   Only dependencies required by Nexus domain and application core:
   - `pydantic>=2.10.0`
   - `numpy>=2.0.0`
   - `scipy>=1.14.0`
   - `pyarrow>=15.0.0`
   - `duckdb>=0.10.0`
   - `fastapi>=0.115.0`
   - `uvicorn[standard]>=0.30.0`
   - `python-dotenv>=1.0.0`
   - `httpx>=0.28.0` (standard HTTP client used by provider adapters)

2. **`backend/requirements-dev.txt` (Developer & CI Tooling):**
   - `pytest>=8.3.0`
   - `pytest-mock>=3.14.0`
   - `pytest-cov>=5.0.0`
   - `pytest-asyncio>=0.24.0`
   - `ruff>=0.9.0`
   - `mypy>=1.14.0`
   - `import-linter>=2.14`

3. **`backend/requirements-adk.txt` (Google ADK Adapter — Optional / Isolated):**
   - `google-adk==2.7.0` (without `[extensions]`, preventing transitive pull of LiteLLM, LangGraph, Kubernetes, etc.)
   - `google-cloud-bigquery==3.43.0`

### 3. Automated Enforcement via Import Linter (`.importlinter`)

We add explicit contracts to `.importlinter`:
```ini
[importlinter:contract:provider-sdk-isolation]
name = Domain and Application must not import provider SDKs
type = forbidden
source_modules =
    domain
    application
forbidden_modules =
    google
    openai
    anthropic
    litellm
    langgraph
    llama_index
```

Any attempt to introduce a provider SDK into the domain or application layer causes `lint-imports` and `scripts/check_architecture.py` to fail in CI.

---

## Consequences

### Positive
- **Vendor Independence:** Switching from Google ADK to OpenAI Agents SDK, LangGraph, or plain HTTP adapters requires zero changes to core domain, matching, evaluation, or synthesis logic.
- **Dramatically Faster CI:** Core CI jobs (Architecture Gate, Python Quality, Backend Tests) install only lightweight dependencies, cutting pip setup time by 70–80%.
- **Zero Transitive Bloat:** Eliminates unnecessary third-party packages from production runtime environments.

### Negative
- Running Google ADK workflows requires explicitly installing the ADK adapter dependencies (`pip install -r backend/requirements-adk.txt`).
- Concrete provider adapters in `infrastructure/llm` must implement capability ports (`InventorAgentProtocol`, `AdversarialAgentProtocol`) and map internal LLM responses into domain schemas.

---

## Enforcement

1. Declarative import contract `provider-sdk-isolation` in `.importlinter`.
2. Python AST checks in `scripts/check_architecture.py`.
3. Invariant test in `backend/test/unit/architecture/` verifying that neither domain nor application imports external agent frameworks.
