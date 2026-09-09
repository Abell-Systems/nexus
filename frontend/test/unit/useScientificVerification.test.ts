import { renderHook, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { useScientificVerification } from "../../src/main/components/ScientificVerification/useScientificVerification";

describe("useScientificVerification", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("handles missing project_status.json as unavailable without crashing", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      json: async () => ({}),
    });
    const { result } = renderHook(() => useScientificVerification("/missing.json"));
    await waitFor(() => expect(result.current.state).toBe("unavailable"));
    expect(result.current.error).toContain("No se pudo cargar el reporte de verificación");
    expect(result.current.data).toBeNull();
  });

  it("handles malformed JSON payload as unavailable", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ unexpected: "payload" }),
    });
    const { result } = renderHook(() => useScientificVerification("/corrupt.json"));
    await waitFor(() => expect(result.current.state).toBe("unavailable"));
    expect(result.current.error).toContain("formato del reporte");
  });

  it("evaluates state as failed when scientific_integrity is FAIL even if overall_status was misreported", async () => {
    const mockStatus = {
      schema_version: "1.0.0",
      commit_sha: "7928e22",
      evaluated_at: "2026-09-09T08:00:00Z",
      overall_status: "PASS", // Misreported overall
      dimensions: {
        scientific_integrity: {
          status: "FAIL",
          requirement_level: "required",
          evidence_source: "scripts/audit_dataset_identity.py",
          evidence_available: true,
          checks: [
            { name: "dataset_sha_sidecar", status: "PASS" },
            { name: "temporal_policy_binding", status: "FAIL", detail: "mismatch" }
          ]
        }
      }
    };
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockStatus,
    });
    const { result } = renderHook(() => useScientificVerification("/status.json"));
    await waitFor(() => expect(result.current.state).toBe("failed"));
    expect(result.current.data?.isVerified).toBe(false);
  });

  it("extracts 3 pillars with accepted exceptions preserved when verified", async () => {
    const mockStatus = {
      schema_version: "1.0.0",
      commit_sha: "7928e22",
      evaluated_at: "2026-09-09T08:00:00Z",
      overall_status: "PASS",
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
    const { result } = renderHook(() => useScientificVerification("/project_status.json"));
    await waitFor(() => expect(result.current.state).toBe("verified"));
    expect(result.current.data?.isVerified).toBe(true);
    expect(result.current.data?.provenance.commitSha).toBe("7928e22");
    expect(result.current.data?.pillars.protocol.hasAcceptedExceptions).toBe(true);
    expect(result.current.data?.conclusion).toContain("ADR-0018/ADR-0019");
  });
});
