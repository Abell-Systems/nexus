import React from "react";
import type { EpistemicBoundaries } from "../types";

interface EpistemicBoundaryCardProps {
  boundaries: EpistemicBoundaries;
}

export const EpistemicBoundaryCard: React.FC<EpistemicBoundaryCardProps> = ({
  boundaries,
}) => {
  return (
    <div className="w-full bg-slate-800/60 border border-slate-700/80 rounded-xl p-6 mb-8 shadow-sm">
      <h2 className="text-lg sm:text-xl font-semibold text-white mb-2 flex items-center gap-2">
        <span className="text-cyan-400">Frontera Epistemológica</span>
      </h2>
      <p className="text-xs sm:text-sm text-slate-400 mb-6">
        Delimitación explícita entre lo validado empíricamente en esta ejecución y las hipótesis aún abiertas.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Demonstrated */}
        <div className="bg-emerald-950/20 border border-emerald-800/40 rounded-lg p-5">
          <h3 className="text-sm font-semibold text-emerald-300 mb-3 flex items-center gap-2">
            <span>✓</span> Demostrado con evidencia objetiva
          </h3>
          <ul className="space-y-2 text-xs sm:text-sm text-slate-300">
            {boundaries.demonstrated.map((item, idx) => (
              <li key={idx} className="flex items-start gap-2">
                <span className="text-emerald-400 text-xs mt-1">•</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Not Yet Demonstrated */}
        <div className="bg-amber-950/20 border border-amber-800/40 rounded-lg p-5">
          <h3 className="text-sm font-semibold text-amber-300 mb-3 flex items-center gap-2">
            <span>⚠</span> No demostrado aún
          </h3>
          <ul className="space-y-2 text-xs sm:text-sm text-slate-300">
            {boundaries.not_yet_demonstrated.map((item, idx) => (
              <li key={idx} className="flex items-start gap-2">
                <span className="text-amber-400 text-xs mt-1">•</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* Next Scientific Step */}
      <div className="mt-6 pt-5 border-t border-slate-700/60 bg-slate-900/40 p-4 rounded-lg border border-slate-700/40">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-2">
          <span className="text-xs font-bold uppercase tracking-wider text-cyan-400">
            Siguiente paso científico ({boundaries.next_scientific_step.target_milestone})
          </span>
          <span className="text-sm font-medium text-white">
            {boundaries.next_scientific_step.title}
          </span>
        </div>
        <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
          {boundaries.next_scientific_step.description}
        </p>
      </div>
    </div>
  );
};
