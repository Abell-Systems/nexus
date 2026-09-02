import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { LandingView } from "../../src/main/components/UserZero/LandingView";

describe("LandingView Component", () => {
  it("renders form inputs and submit button", () => {
    render(<LandingView onStartAnalysis={vi.fn()} />);
    expect(screen.getByText("Start your analysis")).toBeDefined();
    expect(screen.getByRole("button", { name: /analyze opportunity/i })).toBeDefined();
  });

  it("submits analysis form with entered domain and query", () => {
    const onStartAnalysis = vi.fn();
    render(<LandingView onStartAnalysis={onStartAnalysis} />);

    const domainInput = screen.getByLabelText(/technology domain/i);
    fireEvent.change(domainInput, { target: { value: "Battery electrolytes" } });

    const submitButton = screen.getByRole("button", { name: /analyze opportunity/i });
    fireEvent.click(submitButton);

    expect(onStartAnalysis).toHaveBeenCalledWith("Battery electrolytes", "solid electrolyte interphase");
  });
});
