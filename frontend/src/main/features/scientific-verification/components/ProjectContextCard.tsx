import React from "react";
import { ScientificContext } from "../types";

interface ProjectContextCardProps {
  context: ScientificContext["project_overview"];
}

export const ProjectContextCard: React.FC<ProjectContextCardProps> = ({ context }) => {
  return (
    <div className="w-full bg-slate-800/60 border border-slate-700/80 rounded-xl p-6 mb-8 shadow-sm">
      <h2 className="text-lg sm:text-xl font-semibold text-white mb-2 flex items-center gap-2">
        <span className="text-cyan-400">¿Qué es Abell Nexus?</span>
      </h2>
      <p className="text-slate-300 text-sm sm:text-base leading-relaxed mb-4">
        {context.description}
      </p>
      <div className="flex flex-wrap gap-4 pt-2 border-t border-slate-700/40 text-xs sm:text-sm">
        <a
          href={context.protocol_url}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1.5 text-cyan-400 hover:text-cyan-300 underline font-medium"
        >
          📄 Protocolo Empírico
        </a>
        <a
          href={context.repository_url}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1.5 text-slate-300 hover:text-white underline font-medium"
        >
          📦 Repositorio en GitHub
        </a>
      </div>
    </div>
  );
};
