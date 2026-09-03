# ADR 0002: Minimal Clean Code & SOLID

**Status:** Accepted  
**Date:** 2026-09-03  
**Scope:** Entire Nexus repository  

## Context

Nexus is developed under Clean Architecture and must remain a small, understandable, maintainable product.

New functionality must solve the required product problem without accumulating speculative abstractions, duplicated logic, unnecessary comments, compatibility layers, or code introduced solely for the empirical study.

The repository is worked on by both humans and coding agents. Therefore, the standard for code size, structure, comments, and abstractions must be explicit and consistent.

## Decision

### 1. Minimal implementation

Implement the **smallest clean solution that satisfies the requirement and its acceptance criteria**.

Do not add code for:
* hypothetical future requirements;
* unused extension points;
* speculative abstractions;
* premature generalization;
* duplicated compatibility paths;
* paper-specific functionality;
* coverage targets without behavioral value.

Every production abstraction must have a current responsibility.

### 2. Clean Code

Production code must favor:
* clear names;
* small cohesive functions;
* single responsibility;
* straightforward control flow;
* explicit dependencies;
* low coupling;
* high cohesion;
* simple data transformations;
* early validation of invalid state.

Prefer readable code over clever code.

Do not obscure simple behavior behind unnecessary layers, factories, wrappers, or generic frameworks.

### 3. SOLID

Apply SOLID principles pragmatically.

In particular:
* **SRP:** each class/module has one coherent responsibility.
* **OCP:** introduce extensibility when there is an actual current variation, not merely a hypothetical one.
* **LSP:** implementations of domain/application protocols must honor the complete contract.
* **ISP:** protocols expose only the operations their clients require.
* **DIP:** domain and application depend on abstractions; infrastructure provides implementations.

SOLID is not a justification for abstraction proliferation.

The preferred design is:
> **the simplest design that preserves the required architectural boundary and responsibility.**

### 4. Comments

Comments are **exceptional, not routine**.

Code should explain itself through naming and structure.

Do not add comments that merely restate obvious implementation details.

A comment is justified only when it explains information that cannot reasonably be expressed by the code itself, such as:
* a non-obvious domain rule;
* a deliberate algorithmic choice;
* a compatibility constraint;
* a numerical or performance invariant;
* an external standard whose requirement affects the implementation;
* a subtle reason why an apparently simpler implementation would be incorrect.

Comments must explain **why**, not narrate **what**.

### 5. Documentation

Do not create documentation for trivial implementation details.

Architectural decisions belong in ADRs.

Public contracts and genuinely non-obvious behavior may be documented where appropriate.

Do not duplicate an ADR inside source-code comments.

### 6. Tests

Tests follow ADR 0001.

Do not add production code merely to make testing easier.

Do not add tests merely to increase coverage.

Test behavior at the layer that owns it.

### 7. Experimental code

The empirical study does not justify a parallel application architecture.

Production Nexus code must remain product code.

Paper-specific analysis belongs downstream of Nexus outputs.

Names such as:
* `WorldPatentInformationService`;
* `PaperTableGenerator`;
* `ReviewerResponse`;
* `ExperimentSpecificService`;

must not be introduced into the Nexus domain or application merely to support the paper.

### 8. Refactoring rule

When modifying existing code:
> **Improve only what is necessary to implement the current requirement safely and cleanly.**

Do not perform unrelated architectural rewrites.

If an existing defect directly prevents a clean implementation, fix the smallest relevant part and test the behavior.

### 9. Agent rule

Before adding a class, interface, protocol, helper, abstraction, dependency, or comment, an agent must be able to identify its **current concrete responsibility**.

If that responsibility cannot be stated clearly, the addition should not be made.

Agents must prefer:
```text
existing abstraction + small extension
```
over:
```text
new abstraction + wrapper + adapter + factory
```
unless the latter is required by an actual architectural boundary or variation.

## Consequences

This ADR intentionally favors a small codebase over an extensively abstracted one.

Expected consequences:
* fewer production lines;
* fewer dependencies;
* easier review;
* easier reasoning;
* lower maintenance cost;
* clearer Clean Architecture boundaries;
* less agent-generated code noise;
* fewer speculative abstractions;
* comments that carry genuine information.

A feature is not considered higher quality because it contains more abstractions, comments, classes, or documentation.

**Code economy is an explicit engineering requirement.**

## Normative Rule

For every Nexus contribution:
> **Minimum code. Maximum clarity. No speculative abstraction. No explanatory noise. Comments only when they explain non-obvious why. Apply Clean Code and SOLID pragmatically.**
