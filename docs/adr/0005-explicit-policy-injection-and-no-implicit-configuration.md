# ADR 0005: Explicit Policy Injection and No Implicit Configuration

**Status:** Accepted  
**Date:** 2026-09-03  
**Scope:** All application/domain components whose behavior depends on MatchingPolicyConfig or other runtime policy/configuration.

## Context

Nexus repeatedly encountered the same architectural failure mode: a component was correctly designed to consume externalized policy, but retained an implicit fallback that loaded `default_matching_policy.json` from a repository-relative path or supplied a business default when the policy was omitted.

This creates a hidden second composition root and makes behavior depend on the process working directory and repository layout. It also makes tests appear policy-driven while production behavior can silently use a different configuration source.

Externalization is therefore insufficient by itself. The dependency boundary must be explicit.

## Decision

### 1. Policy/configuration dependencies are mandatory at the boundary

If a component's behavior is materially affected by policy/configuration, that dependency MUST be passed explicitly by the caller.

Preferred:

```python
def map_concept_to_cpc(
    concept: str,
    policy: MatchingPolicyConfig,
) -> list[str]:
    ...
```

Forbidden:

```python
def map_concept_to_cpc(
    concept: str,
    policy: MatchingPolicyConfig | None = None,
) -> list[str]:
    policy = policy or load_default_policy()
```

### 2. Domain/application logic MUST NOT resolve repository-relative configuration

Code under `domain/` and application services MUST NOT contain repository-relative paths such as:

```text
config/policies/...
```

nor use the current working directory as an implicit configuration source.

Configuration loading belongs to the composition/bootstrap boundary. The loaded, validated, cryptographically verified configuration is then injected into the components that need it.

### 3. No business-policy fallback values in executable code

Values that affect matching behavior MUST NOT silently fall back to literals in Python/TypeScript/etc. Examples include:

- retrieval limits;
- candidate-pool limits;
- ranking weights;
- confidence thresholds;
- evidence/sufficiency thresholds;
- CPC concordance levels;
- taxonomy mappings;
- jurisdiction or eligibility rules;
- normalization parameters that alter scientific interpretation.

If required policy is absent, the system MUST fail explicitly.

### 4. Compatibility APIs must not weaken the contract

Optional parameters are acceptable only when absence has semantics that are independent of policy.

A compatibility overload MUST NOT use omission to select a hidden policy, default business value, or alternate algorithm.

### 5. One policy object per evaluation context

A matching evaluation MUST use one explicit `MatchingPolicyConfig` instance throughout the complete evaluation path. Components must not independently reload or reinterpret policy files.

This guarantees that the policy ID, version, SHA-256 digest, and actual behavioral parameters correspond to the same immutable evaluation context.

## Consequences

### Positive

- Behavior is independent of repository layout and process working directory.
- Tests can prove behavior against arbitrary policy instances without filesystem coupling.
- Policy provenance is genuinely auditable rather than merely recorded after implicit resolution.
- There is a single composition point where configuration is loaded, validated, and sealed.
- Missing policy becomes an explicit configuration error instead of silent behavior drift.

### Negative

- Call sites must pass policy explicitly.
- Some legacy convenience functions need signature changes.
- Application bootstrap must own policy loading.

These costs are intentional: explicit dependency injection is preferred over convenience when configuration changes system semantics.

## Enforcement

A change is non-compliant if production matching code contains any of the following patterns:

1. `Path("config/policies/...`)` outside the configuration/bootstrap layer.
2. `policy or load_*_policy()` inside domain/application matching logic.
3. A business-relevant numeric/string/list fallback used when policy is absent.
4. Independent policy-file loading by multiple matching components.
5. A public matching API where `policy=None` silently changes behavior.

Required tests SHOULD include:

- evaluation with two different policy objects producing intentionally different results;
- failure when a mandatory policy is absent;
- proof that the same injected policy instance is used throughout evaluation;
- execution from a different working directory without changing matching behavior.

## Relationship to Existing ADRs

- **ADR 0002:** reinforces dependency inversion and single responsibility.
- **ADR 0003:** extends externalized policy and provenance from file format to runtime dependency boundaries.
- **ADR 0004:** makes the `MatchingPolicyConfig` injection requirement operational and testable.
