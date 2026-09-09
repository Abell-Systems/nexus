import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import "@testing-library/jest-dom";
import { VerificationHero } from "../components/VerificationHero";
import { ProjectContextCard } from "../components/ProjectContextCard";
import { MilestonesProgress } from "../components/MilestonesProgress";
import { EpistemicBoundaryCard } from "../components/EpistemicBoundaryCard";
import { VerificationPillars } from "../components/VerificationPillars";
import { ScientificConclusion } from "../components/ScientificConclusion";
import { EvidenceDrawer } from "../components/EvidenceDrawer";
import contextData from "../scientific_context.json";
import { PillarViewModel, ProjectStatusPayload } from "../types";

describe("Scientific Verification Components", () => {
  it("VerificationHero renders exact point-in-time provenance statement", () => {
    render(
      <VerificationHero
        state="verified"
        datasetId="nexus-pilot-16-evaluation-corpus-v1"
        commitSha="7928e22"
        evaluatedAt="2026-09-09T08:00:00Z"
      />
    );
    expect(screen.getByText(/VERIFICADO/i)).toBeInTheDocument();
    expect(screen.getByText(/nexus-pilot-16-evaluation-corpus-v1/)).toBeInTheDocument();
    expect(screen.getByText(/7928e22/)).toBeInTheDocument();
    expect(screen.getByText(/2026-09-09/)).toBeInTheDocument();
  });

  it("ProjectContextCard renders project narrative and links", () => {
    render(<ProjectContextCard context={contextData.project_overview} />);
    expect(screen.getByText(/¿Qué es Abell Nexus\?/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /protocolo empírico/i })).toHaveAttribute(
      "href",
      contextData.project_overview.protocol_url
    );
  });

  it("MilestonesProgress renders milestones dynamically from context", () => {
    const mockDimensions = {
      scientific_integrity: { status: "PASS" as const, checks: [] as any, evidence_source: "", evidence_available: true, requirement_level: "required" as const },
      backend_testing: { status: "PASS" as const, checks: [] as any, evidence_source: "", evidence_available: true, requirement_level: "required" as const }
    };
    render(<MilestonesProgress milestones={contextData.milestones} dimensions={mockDimensions} />);
    expect(screen.getByText(/¿En qué punto estamos\?/i)).toBeInTheDocument();
    expect(screen.getByText(/Corpus y Benchmark Piloto/i)).toBeInTheDocument();
    expect(screen.getByText(/Escalado de Corpus y Anotación Ciega/i)).toBeInTheDocument();
  });

  it("EpistemicBoundaryCard renders demonstrated vs not yet demonstrated vs next step", () => {
    render(<EpistemicBoundaryCard boundaries={contextData.epistemic_boundaries} />);
    expect(screen.getByText(/Frontera Epistemológica/i)).toBeInTheDocument();
    expect(screen.getByText(/Demostrado con evidencia objetiva/i)).toBeInTheDocument();
    expect(screen.getByText(/No demostrado aún/i)).toBeInTheDocument();
    expect(screen.getByText(/Siguiente paso científico/i)).toBeInTheDocument();
  });

  it("VerificationPillars renders 3 pillars and highlights accepted exceptions", () => {
    const mockPillars: {
      dataIntegrity: PillarViewModel;
      protocol: PillarViewModel;
      reproducibility: PillarViewModel;
    } = {
      dataIntegrity: {
        name: "Integridad de los Datos",
        status: "PASS",
        summary: "Dataset íntegro.",
        checks: [{ name: "dataset_sha_manifest", status: "PASS", detail: "ok" }],
      },
      protocol: {
        name: "Protocolo Temporal",
        status: "PASS",
        summary: "3 excepciones aceptadas.",
        hasAcceptedExceptions: true,
        checks: [{ name: "temporal_eligibility", status: "SKIPPED", detail: "3 frozen violations under ADR 0018" }],
      },
      reproducibility: {
        name: "Trazabilidad Reproducible",
        status: "PASS",
        summary: "Trazabilidad reproducible confirmada.",
        checks: [{ name: "dataset_sha_sidecar", status: "PASS", detail: "ok" }],
      },
    };
    render(<VerificationPillars pillars={mockPillars} />);
    expect(screen.getByRole("heading", { name: /Integridad de los Datos/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Protocolo Temporal/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Trazabilidad Reproducible/i })).toBeInTheDocument();
    expect(screen.getByText(/Excepciones Documentadas/i)).toBeInTheDocument();
  });

  it("ScientificConclusion triggers onOpenEvidence", () => {
    const handleOpen = vi.fn();
    render(
      <ScientificConclusion
        conclusion="Corpus verificado correctamente."
        onOpenEvidence={handleOpen}
      />
    );
    const btn = screen.getByRole("button", { name: /ver evidencia técnica/i });
    fireEvent.click(btn);
    expect(handleOpen).toHaveBeenCalledTimes(1);
  });

  it("EvidenceDrawer renders checks and close button", () => {
    const handleClose = vi.fn();
    const mockPayload: ProjectStatusPayload = {
      schema_version: "1.0.0",
      commit_sha: "7928e22",
      evaluated_at: "2026-09-09T08:00:00Z",
      overall_status: "PASS",
      aggregation_rule: "all required pass",
      dimensions: {
        scientific_integrity: {
          status: "PASS",
          requirement_level: "required",
          evidence_source: "scripts/audit_dataset_identity.py",
          evidence_available: true,
          checks: [
            { name: "dataset_sha_sidecar", status: "PASS", detail: "file=bf7c501f817f..." },
          ],
        },
      },
    };
    render(
      <EvidenceDrawer
        isOpen={true}
        onClose={handleClose}
        payload={mockPayload}
      />
    );
    expect(screen.getByText(/Auditoría y Evidencia Técnica/i)).toBeInTheDocument();
    expect(screen.getByText(/dataset_sha_sidecar/)).toBeInTheDocument();
    const closeBtn = screen.getByRole("button", { name: /^cerrar$/i });
    fireEvent.click(closeBtn);
    expect(handleClose).toHaveBeenCalledTimes(1);
  });
});
