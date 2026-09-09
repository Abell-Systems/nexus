import { useState, useEffect } from "react";
import contextData from "./scientific_context.json";
import type {
  ProjectStatusPayload,
  ScientificContext,
  VerificationViewModel,
  PillarViewModel,
  CheckResult,
} from "./types";

export type VerificationState = "loading" | "verified" | "failed" | "unavailable";

export function useScientificVerification(fetchUrl = "./project_status.json"): {
  state: VerificationState;
  data: VerificationViewModel | null;
  error: string | null;
} {
  const [state, setState] = useState<VerificationState>("loading");
  const [data, setData] = useState<VerificationViewModel | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isCancelled = false;

    async function loadStatus() {
      try {
        setState("loading");
        setError(null);

        const response = await fetch(fetchUrl);
        if (!response.ok) {
          throw new Error(`No se pudo cargar el reporte de verificación (HTTP ${response.status})`);
        }

        const payload = (await response.json()) as ProjectStatusPayload;

        // Strict Contract Validation (ADR 0022 & schema v1.0.0)
        if (
          !payload ||
          payload.schema_version !== "1.0.0" ||
          !payload.commit_sha ||
          !payload.dimensions ||
          typeof payload.dimensions !== "object"
        ) {
          throw new Error("El formato del reporte de verificación no es válido (esquema incompatible)");
        }

        // Evaluate scientific integrity dimension strictly per ADR 0022
        const sciDim = payload.dimensions.scientific_integrity;
        if (!sciDim || sciDim.requirement_level !== "required") {
          throw new Error("El reporte no incluye la dimensión obligatoria 'scientific_integrity'");
        }

        const checks = sciDim.checks || [];
        const hasFailedCheck = checks.some((c: CheckResult) => c.status === "FAIL");

        // Determine verified state: overall_status must be PASS, scientific_integrity must be PASS,
        // and no individual check in scientific_integrity can be FAIL.
        const isOverallFail = payload.overall_status === "FAIL" || sciDim.status === "FAIL" || hasFailedCheck;
        const isOverallUnverified = payload.overall_status === "UNVERIFIED" || sciDim.status === "UNVERIFIED";

        let computedState: VerificationState = "unavailable";
        if (isOverallFail) {
          computedState = "failed";
        } else if (isOverallUnverified) {
          computedState = "unavailable";
        } else if (payload.overall_status === "PASS" && sciDim.status === "PASS" && !hasFailedCheck) {
          computedState = "verified";
        }

        // Group checks into the 3 scientific pillars
        const dataIntegrityCheckNames = new Set([
          "dataset_sha_sidecar",
          "dataset_sha_manifest",
          "manifest_counts",
          "no_duplicate_demand_ids",
          "no_duplicate_patent_ids",
          "annotations_reference_known_ids",
          "embeddings_artifact_sha",
          "embeddings_dataset_sha",
          "embeddings_demand_ids",
          "embeddings_patent_ids",
          "embeddings_dimension",
          "snapshots_raw_sha",
          "snapshots_count",
          "evaluation_subset_of_snapshots",
        ]);

        const protocolCheckNames = new Set([
          "temporal_policy_binding",
          "temporal_eligibility",
        ]);

        const dataIntegrityChecks = checks.filter((c: CheckResult) => dataIntegrityCheckNames.has(c.name));
        const protocolChecks = checks.filter((c: CheckResult) => protocolCheckNames.has(c.name));

        const dataIntegrityStatus = dataIntegrityChecks.some((c: CheckResult) => c.status === "FAIL")
          ? "FAIL"
          : dataIntegrityChecks.every((c: CheckResult) => c.status === "PASS")
          ? "PASS"
          : "UNVERIFIED";

        const protocolHasFail = protocolChecks.some((c: CheckResult) => c.status === "FAIL");
        const protocolHasExceptions = protocolChecks.some(
          (c: CheckResult) => c.status === "SKIPPED"
        );
        const protocolStatus = protocolHasFail
          ? "FAIL"
          : protocolChecks.length > 0
          ? "PASS"
          : "UNVERIFIED";

        const dataIntegrityPillar: PillarViewModel = {
          name: "Integridad de los Datos",
          status: dataIntegrityStatus,
          summary:
            dataIntegrityStatus === "PASS"
              ? "Dataset íntegro, manifiestos validados y correspondencia de embeddings verificada."
              : "Discrepancias detectadas en la identidad o manifiestos del corpus.",
          checks: dataIntegrityChecks,
        };

        const protocolPillar: PillarViewModel = {
          name: "Protocolo Temporal",
          status: protocolStatus,
          summary: protocolHasExceptions
            ? "Cumplimiento de restricciones temporales con 3 excepciones documentadas bajo ADR-0018/ADR-0019."
            : protocolStatus === "PASS"
            ? "Cumplimiento estricto de restricciones temporales verificado."
            : "Violaciones no aceptadas de prior-art temporal detectadas.",
          checks: protocolChecks,
          hasAcceptedExceptions: protocolHasExceptions,
        };

        const reproducibilityPillar: PillarViewModel = {
          name: "Trazabilidad Reproducible",
          status: sciDim.status,
          summary:
            sciDim.status === "PASS"
              ? "Artefactos identificados criptográficamente y condiciones reproducibles confirmadas."
              : "Condiciones de reproducibilidad no verificadas.",
          checks: [
            ...dataIntegrityChecks.filter((c: CheckResult) => c.name.includes("sha")),
            ...protocolChecks.filter((c: CheckResult) => c.name.includes("binding")),
          ],
        };

        // Synthesis conclusion
        let conclusion = "";
        if (computedState === "verified") {
          conclusion = protocolHasExceptions
            ? "El corpus piloto y las condiciones de ejecución cumplen las restricciones de integridad y trazabilidad definidas por el protocolo, con 3 excepciones temporales formalmente aceptadas bajo ADR-0018/ADR-0019."
            : "El corpus piloto y las condiciones de ejecución cumplen íntegramente las restricciones de integridad y trazabilidad definidas por el protocolo.";
        } else if (computedState === "failed") {
          conclusion =
            "Se han detectado discrepancias en la verificación de integridad de datos o en las restricciones temporales del protocolo.";
        } else {
          conclusion =
            "La evidencia de verificación científica no está disponible o se encuentra incompleta para esta versión.";
        }

        const viewModel: VerificationViewModel = {
          provenance: {
            commitSha: payload.commit_sha,
            evaluatedAt: payload.evaluated_at,
            datasetId: "nexus-pilot-16-evaluation-corpus-v1",
          },
          overallStatus: payload.overall_status,
          isVerified: computedState === "verified",
          pillars: {
            dataIntegrity: dataIntegrityPillar,
            protocol: protocolPillar,
            reproducibility: reproducibilityPillar,
          },
          conclusion,
          rawPayload: payload,
          context: contextData as ScientificContext,
        };

        if (!isCancelled) {
          setData(viewModel);
          setState(computedState);
        }
      } catch (err: unknown) {
        if (!isCancelled) {
          const msg = err instanceof Error ? err.message : "Error inesperado al cargar verificación";
          setError(msg);
          setState("unavailable");
          setData(null);
        }
      }
    }

    loadStatus();

    return () => {
      isCancelled = true;
    };
  }, [fetchUrl]);

  return { state, data, error };
}
