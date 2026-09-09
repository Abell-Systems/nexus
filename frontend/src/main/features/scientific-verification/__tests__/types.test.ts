import { describe, it, expect } from "vitest";
import contextData from "../scientific_context.json";
import { ScientificContext } from "../types";

describe("ScientificContext schema", () => {
  it("conforms to ScientificContext interface", () => {
    const context = contextData as ScientificContext;
    expect(context.project_overview.title).toBe("Abell Nexus");
    expect(context.project_overview.description.length).toBeGreaterThan(20);
    expect(context.milestones.length).toBeGreaterThanOrEqual(4);
    expect(context.epistemic_boundaries.demonstrated.length).toBeGreaterThan(0);
    expect(context.epistemic_boundaries.not_yet_demonstrated.length).toBeGreaterThan(0);
    expect(context.epistemic_boundaries.next_scientific_step.description.length).toBeGreaterThan(10);
  });
});
