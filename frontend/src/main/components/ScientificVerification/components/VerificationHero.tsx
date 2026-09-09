import React from "react";
import type { VerificationState } from "../useScientificVerification";

interface VerificationHeroProps {
  state: VerificationState;
  datasetId?: string;
  commitSha?: string;
  evaluatedAt?: string;
}

export const VerificationHero: React.FC<VerificationHeroProps> = ({
  state,
  datasetId,
  commitSha,
  evaluatedAt,
}) => {
  const getBadge = () => {
    switch (state) {
      case "verified":
        return {
          label: "✓ VERIFICADO",
          bg: "bg-emerald-950/80 border-emerald-500/50 text-emerald-300",
          sub: "El corpus y las condiciones de ejecución cumplen los requisitos de integridad del protocolo.",
        };
      case "failed":
        return {
          label: "✕ NO VERIFICADO",
          bg: "bg-rose-950/80 border-rose-500/50 text-rose-300",
          sub: "Se han detectado discrepancias en la verificación de integridad o en las restricciones temporales.",
        };
      case "loading":
        return {
          label: "CARGANDO...",
          bg: "bg-slate-800 border-slate-600 text-slate-400",
          sub: "Verificando evidencia criptográfica y contrato de estado...",
        };
      case "unavailable":
      default:
        return {
          label: "⚠ VERIFICACIÓN NO DISPONIBLE",
          bg: "bg-amber-950/80 border-amber-500/50 text-amber-300",
          sub: "No se dispone de un reporte de auditoría completo o válido para esta versión.",
        };
    }
  };

  const badge = getBadge();
  const commitShort = commitSha ? commitSha.slice(0, 8) : "desconocido";
  const formattedDate = evaluatedAt ? evaluatedAt.split("T")[0] : "fecha no registrada";

  return (
    <div className="w-full bg-slate-800/80 border border-slate-700 rounded-2xl p-6 sm:p-8 shadow-xl mb-8 backdrop-blur-sm">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-2xl">🔬</span>
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white">
              Abell Nexus · Verificación Científica
            </h1>
          </div>
          <p className="text-slate-300 text-sm sm:text-base max-w-2xl">
            {badge.sub}
          </p>
        </div>

        <div
          className={`inline-flex flex-col items-center justify-center px-6 py-4 rounded-xl border text-center font-semibold text-lg sm:text-xl tracking-wide ${badge.bg} shadow-md`}
        >
          <span>{badge.label}</span>
          <span className="text-xs font-normal opacity-80 mt-1">
            Auditoría Empírica
          </span>
        </div>
      </div>

      {/* Point-in-time Provenance & Anti-Staleness Box */}
      <div className="mt-6 pt-6 border-t border-slate-700/60 flex flex-wrap items-center justify-between gap-3 text-xs sm:text-sm text-slate-400">
        <div>
          <span className="text-slate-500 mr-1">Corpus auditado:</span>
          <code className="text-slate-200 bg-slate-900/60 px-2 py-0.5 rounded font-mono">
            {datasetId || "nexus-pilot-16-evaluation-corpus-v1"}
          </code>
        </div>
        <div>
          <span className="text-slate-500 mr-1">Versión / Commit:</span>
          {commitSha ? (
            <a
              href={`https://github.com/Abell-Systems/nexus/commit/${commitSha}`}
              target="_blank"
              rel="noreferrer"
              className="text-cyan-400 hover:text-cyan-300 underline font-mono"
            >
              {commitShort}
            </a>
          ) : (
            <span className="font-mono text-slate-300">n/a</span>
          )}
        </div>
        <div>
          <span className="text-slate-500 mr-1">Fecha de evaluación:</span>
          <span className="text-slate-300">{formattedDate}</span>
        </div>
      </div>
    </div>
  );
};
