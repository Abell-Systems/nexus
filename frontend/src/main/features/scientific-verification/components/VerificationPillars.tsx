import React from "react";
import type { PillarViewModel } from "../types";

interface VerificationPillarsProps {
  pillars: {
    dataIntegrity: PillarViewModel;
    protocol: PillarViewModel;
    reproducibility: PillarViewModel;
  };
}

export const VerificationPillars: React.FC<VerificationPillarsProps> = ({ pillars }) => {
  const pillarList = [pillars.dataIntegrity, pillars.protocol, pillars.reproducibility];

  return (
    <div className="w-full mb-8">
      <h2 className="text-lg sm:text-xl font-semibold text-white mb-4 flex items-center gap-2">
        <span className="text-cyan-400">Pilares de Verificación Científica</span>
      </h2>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {pillarList.map((pillar) => {
          const isPass = pillar.status === "PASS";
          const isFail = pillar.status === "FAIL";

          return (
            <div
              key={pillar.name}
              className="bg-slate-800/80 border border-slate-700/80 rounded-xl p-5 flex flex-col justify-between shadow-md"
            >
              <div>
                <div className="flex items-center justify-between gap-2 mb-3">
                  <h3 className="text-base font-semibold text-white">
                    {pillar.name}
                  </h3>
                  <span
                    className={`text-xs px-2.5 py-1 rounded-full font-bold border ${
                      isPass
                        ? "bg-emerald-950/60 border-emerald-500/50 text-emerald-300"
                        : isFail
                        ? "bg-rose-950/60 border-rose-500/50 text-rose-300"
                        : "bg-amber-950/60 border-amber-500/50 text-amber-300"
                    }`}
                  >
                    {isPass ? "✓ VERIFICADO" : isFail ? "✕ FALLO" : "PENDIENTE"}
                  </span>
                </div>

                <p className="text-xs sm:text-sm text-slate-300 leading-relaxed mb-4">
                  {pillar.summary}
                </p>

                {pillar.hasAcceptedExceptions && (
                  <div className="mb-4 p-2.5 bg-amber-950/30 border border-amber-700/40 rounded text-amber-300 text-xs">
                    <span className="font-semibold block mb-0.5">
                      ⚠ Excepciones Documentadas
                    </span>
                    3 violaciones temporales congeladas y aceptadas bajo protocolo formal (ADR-0018/ADR-0019).
                  </div>
                )}
              </div>

              <div className="pt-3 border-t border-slate-700/50 text-[11px] text-slate-400 flex items-center justify-between">
                <span>{pillar.checks ? pillar.checks.length : 0} comprobaciones ejecutadas</span>
                <span className="font-mono text-slate-500">ADR 0022</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
