import React from "react";
import type { MilestoneItem, DimensionResult } from "../types";

interface MilestonesProgressProps {
  milestones: MilestoneItem[];
  dimensions?: Record<string, DimensionResult>;
}

export const MilestonesProgress: React.FC<MilestonesProgressProps> = ({
  milestones,
  dimensions = {},
}) => {
  const getMilestoneStatus = (item: MilestoneItem) => {
    if (!item.dimension_key || !dimensions[item.dimension_key]) {
      return {
        label: item.phase === "Fase 2" ? "Próxima etapa" : "En progreso",
        color: "text-slate-400 bg-slate-900/60 border-slate-700",
      };
    }

    const dim = dimensions[item.dimension_key];
    if (dim.status === "PASS") {
      return {
        label: "✓ Verificado",
        color: "text-emerald-400 bg-emerald-950/40 border-emerald-700/50",
      };
    } else if (dim.status === "FAIL") {
      return {
        label: "✕ No verificado",
        color: "text-rose-400 bg-rose-950/40 border-rose-700/50",
      };
    } else {
      return {
        label: "Pendiente",
        color: "text-amber-400 bg-amber-950/40 border-amber-700/50",
      };
    }
  };

  return (
    <div className="w-full bg-slate-800/60 border border-slate-700/80 rounded-xl p-6 mb-8 shadow-sm">
      <h2 className="text-lg sm:text-xl font-semibold text-white mb-4 flex items-center gap-2">
        <span className="text-cyan-400">¿En qué punto estamos?</span>
      </h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {milestones.map((m) => {
          const status = getMilestoneStatus(m);
          return (
            <div
              key={m.id}
              className="flex flex-col justify-between p-4 rounded-lg bg-slate-900/40 border border-slate-700/50"
            >
              <div>
                <div className="flex items-center justify-between gap-2 mb-1.5">
                  <span className="text-sm font-semibold text-white">
                    {m.title}
                  </span>
                  <span
                    className={`text-xs px-2.5 py-0.5 rounded-full border font-medium ${status.color}`}
                  >
                    {status.label}
                  </span>
                </div>
                <p className="text-xs text-slate-300 leading-relaxed">
                  {m.description}
                </p>
              </div>
              <div className="mt-3 text-[11px] text-slate-500 font-mono">
                {m.phase}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
