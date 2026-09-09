import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import "@testing-library/jest-dom";
import { ScientificVerificationView } from "../../src/main/components/ScientificVerification/ScientificVerificationView";

describe("ScientificVerificationView", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders verified view and opens EvidenceDrawer when clicking 'Ver Evidencia Técnica'", async () => {
    const mockStatus = {
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
            { name: "dataset_sha_sidecar", status: "PASS", detail: "ok" },
            { name: "dataset_sha_manifest", status: "PASS", detail: "ok" },
            { name: "temporal_policy_binding", status: "PASS", detail: "ok" },
            {
              name: "temporal_eligibility",
              status: "SKIPPED",
              detail: "3 temporal violations formally accepted as exceptions under ADR-0018/ADR-0019 (accepted_temporal_exception)"
            }
          ]
        }
      }
    };

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockStatus,
    });

    render(<ScientificVerificationView fetchUrl="/test_status.json" />);

    // Wait for data load
    await waitFor(() => expect(screen.getAllByText(/VERIFICADO/i).length).toBeGreaterThan(0));

    // Check all sections are rendered
    expect(screen.getByText(/¿Qué es Abell Nexus\?/i)).toBeInTheDocument();
    expect(screen.getByText(/¿En qué punto estamos\?/i)).toBeInTheDocument();
    expect(screen.getByText(/Frontera Epistemológica/i)).toBeInTheDocument();
    expect(screen.getByText(/Pilares de Verificación Científica/i)).toBeInTheDocument();
    expect(screen.getByText(/Conclusión Científica/i)).toBeInTheDocument();

    // EvidenceDrawer initially not open
    expect(screen.queryByText(/Auditoría y Evidencia Técnica/i)).toBeNull();

    // Click "Ver Evidencia Técnica"
    const evidenceBtn = screen.getByRole("button", { name: /ver evidencia técnica/i });
    fireEvent.click(evidenceBtn);

    // EvidenceDrawer should now be visible
    expect(screen.getByText(/Auditoría y Evidencia Técnica/i)).toBeInTheDocument();

    // Close drawer
    const closeBtn = screen.getByRole("button", { name: /^cerrar$/i });
    fireEvent.click(closeBtn);
    expect(screen.queryByText(/Auditoría y Evidencia Técnica/i)).toBeNull();
  });

  it("renders unavailable notice when fetch fails", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      json: async () => ({}),
    });

    render(<ScientificVerificationView fetchUrl="/missing.json" />);
    await waitFor(() =>
      expect(screen.getByText(/VERIFICACIÓN NO DISPONIBLE/i)).toBeInTheDocument()
    );
  });
});
