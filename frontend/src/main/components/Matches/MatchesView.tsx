import { useEffect, useRef, useState } from "react";
import type { AssetResult, DemandExamplesResponse, MatchesResponse } from "../../domain/operational";
import * as defaultApi from "../../infrastructure/operationalClient";

type Api = Pick<typeof defaultApi, "getDemandExamples" | "getMatches">;

const IP_TYPE_LABEL: Record<string, string> = {
  patent: "Patente",
  utility_model: "Modelo de utilidad",
};

function Notices({ notices }: { readonly notices: readonly string[] }) {
  return (
    <aside aria-label="Avisos" className="rounded-lg border border-amber-500/40 bg-amber-500/10 p-4 text-sm text-amber-100 space-y-1">
      {notices.map((notice) => (
        <p key={notice}>{notice}</p>
      ))}
    </aside>
  );
}

function AssetCard({ asset }: { readonly asset: AssetResult }) {
  return (
    <article className="rounded-lg border border-slate-700 bg-slate-800 p-4 space-y-2">
      <header className="flex items-baseline gap-3">
        <span className="text-lg font-semibold text-violet-300">#{asset.rank}</span>
        <h3 className="font-semibold">{asset.title}</h3>
      </header>
      <p className="text-sm text-slate-300">
        <span>{IP_TYPE_LABEL[asset.ip_type] ?? asset.ip_type}</span>
        {" · "}
        <span>{asset.publication_id}</span>
        {asset.publication_date ? ` · ${asset.publication_date}` : ""}
      </p>
      <p className="text-sm">Titular: {asset.assignees.length > 0 ? asset.assignees.join(", ") : "No disponible"}</p>
      <details className="text-sm">
        <summary className="cursor-pointer text-violet-300">Datos del activo</summary>
        <p className="mt-2 text-slate-200">{asset.abstract}</p>
        {asset.inventors.length > 0 && <p className="mt-2">Inventores: {asset.inventors.join(", ")}</p>}
        {asset.cpc_codes.length > 0 && <p className="mt-2">CPC del activo: {asset.cpc_codes.join(", ")}</p>}
      </details>
      <p className="text-sm">
        Fuente:{" "}
        <a className="text-violet-300 underline" href={asset.source_links.google_patents} target="_blank" rel="noreferrer">
          Google Patents
        </a>
        {" · "}
        <a className="text-violet-300 underline" href={asset.source_links.espacenet} target="_blank" rel="noreferrer">
          Espacenet
        </a>
      </p>
    </article>
  );
}

export function MatchesView({ api = defaultApi }: { readonly api?: Api }) {
  const [examples, setExamples] = useState<DemandExamplesResponse | null>(null);
  const [result, setResult] = useState<MatchesResponse | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const latestRequest = useRef(0);

  useEffect(() => {
    api.getDemandExamples().then(setExamples).catch(() => setError("No se pudieron cargar las demandas de ejemplo."));
  }, [api]);

  const choose = (demandId: string) => {
    const request = ++latestRequest.current;
    setSelected(demandId);
    setResult(null);
    setError(null);
    setLoading(true);
    api
      .getMatches(demandId)
      .then((response) => {
        if (request === latestRequest.current) setResult(response);
      })
      .catch(() => {
        if (request === latestRequest.current) setError("No se pudieron cargar los resultados.");
      })
      .finally(() => {
        if (request === latestRequest.current) setLoading(false);
      });
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">De una demanda real a activos españoles</h1>
      <p className="text-slate-300 text-sm">
        Demandas de ejemplo ingeridas desde Innoget. Elige una para ver qué activos de propiedad industrial españoles
        pueden ser relevantes.
      </p>
      {examples && <Notices notices={examples.notices} />}

      <section aria-label="Demandas" className="grid gap-2 sm:grid-cols-2">
        {examples?.demands.map((demand) => (
          <button
            key={demand.demand_id}
            type="button"
            onClick={() => choose(demand.demand_id)}
            aria-pressed={selected === demand.demand_id}
            className={`text-left rounded-lg border p-3 ${
              selected === demand.demand_id ? "border-violet-400 bg-slate-800" : "border-slate-700 hover:border-slate-500"
            }`}
          >
            <span className="font-medium">{demand.title}</span>
          </button>
        ))}
      </section>

      {loading && <p>Buscando activos…</p>}
      {error && <p role="alert" className="text-rose-300">{error}</p>}
      {result && result.assets.length === 0 && <p>No hay activos elegibles para esta demanda.</p>}
      {result && result.assets.length > 0 && (
        <section aria-label="Resultados" className="space-y-3">
          {result.assets.map((asset) => (
            <AssetCard key={asset.publication_id} asset={asset} />
          ))}
        </section>
      )}
    </div>
  );
}
