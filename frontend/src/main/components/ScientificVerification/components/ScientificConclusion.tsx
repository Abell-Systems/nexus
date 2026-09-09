import React from "react";

interface ScientificConclusionProps {
  conclusion: string;
  onOpenEvidence: () => void;
}

export const ScientificConclusion: React.FC<ScientificConclusionProps> = ({
  conclusion,
  onOpenEvidence,
}) => {
  return (
    <div className="w-full bg-slate-800/90 border border-slate-700 rounded-xl p-6 mb-8 shadow-md">
      <h2 className="text-base sm:text-lg font-semibold text-white mb-2 flex items-center gap-2">
        <span>📋</span>
        <span className="text-cyan-400">Conclusión Científica</span>
      </h2>
      <p className="text-slate-200 text-sm sm:text-base leading-relaxed mb-6 font-serif italic bg-slate-900/60 p-4 rounded-lg border border-slate-700/50">
        "{conclusion}"
      </p>

      <div className="flex flex-wrap items-center justify-between gap-4 pt-2">
        <button
          type="button"
          onClick={onOpenEvidence}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-medium text-xs sm:text-sm transition-colors shadow"
        >
          🔍 Ver Evidencia Técnica (Hashes y Manifiestos)
        </button>

        <a
          href="https://github.com/Abell-Systems/nexus/blob/main/docs/empirical-study-protocol.md"
          target="_blank"
          rel="noreferrer"
          className="text-xs sm:text-sm text-slate-400 hover:text-slate-200 underline"
        >
          Consultar Protocolo Empírico Completo →
        </a>
      </div>
    </div>
  );
};
