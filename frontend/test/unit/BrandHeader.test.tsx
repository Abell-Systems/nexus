import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { BrandHeader, AbellMark } from "../../src/main/components/shared/BrandHeader";

describe("BrandHeader Component", () => {
  it("renders header brand title", () => {
    render(<BrandHeader />);
    expect(screen.getByText(/ABELL/i)).toBeDefined();
    expect(screen.getByText(/SYSTEMS/i)).toBeDefined();
  });

  it("renders domain badge when domain prop is provided", () => {
    render(<BrandHeader domain="Solid-state electrolytes" />);
    expect(screen.getByText("Solid-state electrolytes")).toBeDefined();
  });

  it("renders AbellMark SVG with default or custom size", () => {
    const { container } = render(<AbellMark size={40} />);
    const svg = container.querySelector("svg");
    expect(svg).toBeDefined();
    expect(svg?.getAttribute("style")).toContain("40px");
  });
});

