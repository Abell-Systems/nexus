import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import "@testing-library/jest-dom";
import { VerificationHero } from "../components/VerificationHero";
import { VerificationPillars } from "../components/VerificationPillars";
import { EpistemicBoundaryCard } from "../components/EpistemicBoundaryCard";
import contextData from "../scientific_context.json";
import type { PillarViewModel } from "../types";

describe("Epistemic Invariants", () => {
  it("never asserts universal model efficacy or '100% reproducible'", () => {
    render(
      <VerificationHero
        state="verified"
        datasetId="nexus-pilot-16-evaluation-corpus-v1"
        commitSha="7928e22"
        evaluatedAt="2026-09-09T08:00:00Z"
      />
    );
    expect(screen.queryByText(/el modelo es universalmente válido/i)).toBeNull();
    expect(screen.queryByText(/100% reproducible/i)).toBeNull();
    expect(screen.queryByText(/modelo universal/i)).toBeNull();
  });

  it("renders temporal eligibility exceptions explicitly with ADR governance reference", () => {
    const mockPillars: {
      dataIntegrity: PillarViewModel;
      protocol: PillarViewModel;
      reproducibility: PillarViewModel;
    } = {
      dataIntegrity: {
        name: "Integridad de los Datos",
        status: "PASS",
        summary: "Integridad verificada frente a hashes.",
        checks: [
          { name: "dataset_sha_sidecar", status: "PASS" },
          { name: "dataset_sha_manifest", status: "PASS" },
        ],
      },
      protocol: {
        name: "Protocolo Temporal",
        status: "PASS",
        summary: "Protocolo temporal auditado.",
        hasAcceptedExceptions: true,
        checks: [
          {
            name: "temporal_eligibility",
            status: "SKIPPED",
            detail: "3 temporal violations formally accepted as exceptions under ADR-0018/ADR-0019 (accepted_temporal_exception)",
          },
        ],
      },
      reproducibility: {
        name: "Reproducibilidad",
        status: "PASS",
        summary: "Trazabilidad reproducible confirmada.",
        checks: [
          { name: "dataset_id", status: "PASS" },
        ],
      },
    };

    render(<VerificationPillars pillars={mockPillars} />);
    expect(screen.getByText(/ADR-0018\/ADR-0019/i)).toBeInTheDocument();
    expect(screen.getByText(/3 violaciones temporales congeladas y aceptadas bajo protocolo formal/i)).toBeInTheDocument();
  });

  it("renders UNAVAILABLE and zero verified elements when report is missing or broken", () => {
    render(
      <VerificationHero
        state="unavailable"
        datasetId={undefined}
        commitSha={undefined}
        evaluatedAt={undefined}
      />
    );
    expect(screen.getByText(/VERIFICACIÓN NO DISPONIBLE/i)).toBeInTheDocument();
    expect(screen.queryByText(/^VERIFICADO$/i)).toBeNull();
  });

  it("displays explicit epistemic boundaries acknowledging what is NOT yet demonstrated", () => {
    render(<EpistemicBoundaryCard boundaries={contextData.epistemic_boundaries} />);
    expect(screen.getByText(/Demostrado con evidencia objetiva/i)).toBeInTheDocument();
    expect(screen.getByText(/No demostrado aún/i)).toBeInTheDocument();
    expect(screen.getByText(/Siguiente paso científico/i)).toBeInTheDocument();

    // Verify negative boundaries are present
    const boundariesContent = screen.getByText(/Validez transfronteriza y multilingüe/i);
    expect(boundariesContent).toBeInTheDocument();
  });
});
