import React, { useState } from "react";
import { useScientificVerification } from "./useScientificVerification";
import { VerificationHero } from "./components/VerificationHero";
import { ProjectContextCard } from "./components/ProjectContextCard";
import { MilestonesProgress } from "./components/MilestonesProgress";
import { EpistemicBoundaryCard } from "./components/EpistemicBoundaryCard";
import { VerificationPillars } from "./components/VerificationPillars";
import { ScientificConclusion } from "./components/ScientificConclusion";
import { EvidenceDrawer } from "./components/EvidenceDrawer";

interface ScientificVerificationViewProps {
  fetchUrl?: string;
  onNavigateHome?: () => void;
}

export const ScientificVerificationView: React.FC<ScientificVerificationViewProps> = ({
  fetchUrl = "./project_status.json",
  onNavigateHome,
}) => {
  const { state, data, error } = useScientificVerification(fetchUrl);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  return (
    <div className="w-full max-w-5xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
      {/* Top navigation back button if provided */}
      <div className="mb-6 flex items-center justify-between">
        <button
          type="button"
          onClick={onNavigateHome || (() => { window.location.hash = ""; })}
          className="inline-flex items-center gap-2 text-xs sm:text-sm text-slate-400 hover:text-white transition-colors"
        >
          ← Volver a Nexus Patent Agent
        </button>
        <span className="text-xs text-slate-500 font-mono">
          Scientific Verification SPA · v1.0.0
        </span>
      </div>

      {/* Hero with Point-in-time Provenance */}
      <VerificationHero
        state={state}
        datasetId={data?.provenance.datasetId}
        commitSha={data?.provenance.commitSha}
        evaluatedAt={data?.provenance.evaluatedAt}
      />

      {error && (
        <div className="mb-8 p-4 bg-amber-950/40 border border-amber-800/60 rounded-xl text-amber-200 text-xs sm:text-sm">
          <span className="font-semibold block mb-1">Aviso de Auditoría:</span>
          {error}
        </div>
      )}

      {/* 1. ¿Qué es Abell Nexus? */}
      {data?.context && (
        <ProjectContextCard context={data.context.project_overview} />
      )}

      {/* 2. ¿En qué punto estamos? (Roadmap & Live Dimensions) */}
      {data?.context && (
        <MilestonesProgress
          milestones={data.context.milestones}
          dimensions={data.rawPayload?.dimensions}
        />
      )}

      {/* 3. Frontera Epistemológica */}
      {data?.context && (
        <EpistemicBoundaryCard boundaries={data.context.epistemic_boundaries} />
      )}

      {/* 4. Pilares de Verificación Científica */}
      {data?.pillars && <VerificationPillars pillars={data.pillars} />}

      {/* 5. Conclusión Científica & Acceso a Evidencia */}
      {data && (
        <ScientificConclusion
          conclusion={data.conclusion}
          onOpenEvidence={() => setIsDrawerOpen(true)}
        />
      )}

      {/* Slide-over Evidence Drawer */}
      <EvidenceDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        payload={data?.rawPayload || null}
      />
    </div>
  );
};

export default ScientificVerificationView;
