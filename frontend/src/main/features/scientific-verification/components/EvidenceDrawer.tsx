import React from "react";
import { ProjectStatusPayload, CheckResult } from "../types";

interface EvidenceDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  payload: ProjectStatusPayload | null;
}

export const EvidenceDrawer: React.FC<EvidenceDrawerProps> = ({
  isOpen,
  onClose,
  payload,
}) => {
  if (!isOpen) return null;

  const scientificDim = payload?.dimensions?.scientific_integrity;
  const checks = scientificDim?.checks || [];

  return (
    <div
      className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex justify-end"
      role="dialog"
      aria-modal="true"
    >
      <div className="w-full max-w-2xl bg-slate-900 border-l border-slate-700 h-full p-6 sm:p-8 flex flex-col justify-between overflow-y-auto shadow-2xl animate-in slide-in-from-right duration-200">
        <div>
          <div className="flex items-center justify-between pb-4 border-b border-slate-800 mb-6">
            <h2 className="text-lg sm:text-xl font-bold text-white flex items-center gap-2">
              <span>🔬</span> Auditoría y Evidencia Técnica
            </h2>
            <button
              type="button"
              onClick={onClose}
              className="text-slate-400 hover:text-white text-sm px-3 py-1.5 rounded-lg border border-slate-700 bg-slate-800"
            >
              Cerrar
            </button>
          </div>

          <p className="text-xs sm:text-sm text-slate-300 mb-6 leading-relaxed">
            Esta evidencia ha sido producida de forma determinista por las puertas de calidad automatizadas de CI en GitHub Actions y registrada en{" "}
            <code className="bg-slate-800 px-1.5 py-0.5 rounded text-cyan-300 font-mono text-xs">
              project_status.json
            </code>.
          </p>

          <div className="mb-6 bg-slate-800/60 p-4 rounded-xl border border-slate-700/60 text-xs">
            <div className="font-semibold text-slate-200 mb-2">
              Metadatos del Contrato de Auditoría (ADR 0022):
            </div>
            <div className="grid grid-cols-2 gap-2 text-slate-300 font-mono">
              <div>Commit SHA: {payload?.commit_sha.slice(0, 12)}...</div>
              <div>Versión Esquema: {payload?.schema_version}</div>
              <div>Estado Global: {payload?.overall_status}</div>
              <div>Evaluado: {payload?.evaluated_at?.split("T")[0]}</div>
            </div>
          </div>

          <h3 className="text-sm font-semibold text-white mb-3 flex items-center justify-between">
            <span>Comprobaciones de Integridad Científica</span>
            <span className="text-xs text-slate-400 font-normal">
              {checks.length} comprobaciones
            </span>
          </h3>

          <div className="space-y-3 mb-8">
            {checks.map((c: CheckResult) => (
              <div
                key={c.name}
                className="bg-slate-800/40 p-3 rounded-lg border border-slate-800 text-xs"
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-mono text-cyan-300 font-medium">
                    {c.name}
                  </span>
                  <span
                    className={`font-bold px-2 py-0.5 rounded text-[11px] ${
                      c.status === "PASS"
                        ? "text-emerald-400 bg-emerald-950/60"
                        : c.status === "SKIPPED"
                        ? "text-amber-400 bg-amber-950/60"
                        : "text-rose-400 bg-rose-950/60"
                    }`}
                  >
                    {c.status}
                  </span>
                </div>
                {c.detail && (
                  <div className="text-slate-400 font-mono text-[11px] break-all">
                    {c.detail}
                  </div>
                )}
                {c.policy_ref && (
                  <div className="mt-1 text-[11px] text-amber-300">
                    Gobernanza: {c.policy_ref} ({c.reason})
                  </div>
                )}
              </div>
            ))}
          </div>

          <div className="pt-4 border-t border-slate-800 text-xs text-slate-400 space-y-2">
            <div className="font-semibold text-slate-300">
              Documentos de Arquitectura Vinculantes (ADRs):
            </div>
            <ul className="list-disc list-inside space-y-1 text-slate-300">
              <li>
                <a
                  href="https://github.com/Abell-Systems/nexus/blob/main/docs/adr/0006-dataset-checksum-verification.md"
                  target="_blank"
                  rel="noreferrer"
                  className="text-cyan-400 hover:underline"
                >
                  ADR 0006: Verificación de Checksum de Dataset
                </a>
              </li>
              <li>
                <a
                  href="https://github.com/Abell-Systems/nexus/blob/main/docs/adr/0018-temporal-pool-eligibility-contract.md"
                  target="_blank"
                  rel="noreferrer"
                  className="text-cyan-400 hover:underline"
                >
                  ADR 0018: Restricciones de Prior-Art Temporal (Φ_temporal)
                </a>
              </li>
              <li>
                <a
                  href="https://github.com/Abell-Systems/nexus/blob/main/docs/adr/0019-annotation-pool-temporal-eligibility-under-unknown-posting-date.md"
                  target="_blank"
                  rel="noreferrer"
                  className="text-cyan-400 hover:underline"
                >
                  ADR 0019: Elegibilidad Temporal en Anotación Ciega
                </a>
              </li>
              <li>
                <a
                  href="https://github.com/Abell-Systems/nexus/blob/main/docs/adr/0022-project-status-contract.md"
                  target="_blank"
                  rel="noreferrer"
                  className="text-cyan-400 hover:underline"
                >
                  ADR 0022: Contrato Epistemológico de Project Status
                </a>
              </li>
            </ul>
          </div>
        </div>

        <div className="pt-6 border-t border-slate-800 mt-6 flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="w-full sm:w-auto px-5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-white text-xs sm:text-sm font-medium transition-colors"
          >
            Cerrar Panel
          </button>
        </div>
      </div>
    </div>
  );
};
