import { useCallback, useEffect, useRef, useState } from "react";
import type { AssetResult, DemandExamplesResponse, MatchesResponse } from "../../domain/operational";
import * as defaultApi from "../../infrastructure/operationalClient";
import { ApiError } from "../../infrastructure/operationalClient";
import styles from "./MatchesView.module.css";

type Api = Pick<typeof defaultApi, "getDemandExamples" | "getMatches">;

const IP_TYPE_LABEL: Record<string, string> = {
  patent: "Patente",
  utility_model: "Modelo de utilidad",
};

function Notices({ notices }: { readonly notices: readonly string[] }) {
  return (
    <aside aria-label="Avisos" className={styles.notices}>
      {notices.map((notice) => (
        <p key={notice}>{notice}</p>
      ))}
    </aside>
  );
}

function AssetCard({ asset, defaultOpen }: { readonly asset: AssetResult; readonly defaultOpen: boolean }) {
  return (
    <article className={styles.card}>
      <header className={styles.cardHeader}>
        <span className={styles.rank}>#{asset.rank}</span>
        <h3 className={styles.assetTitle}>{asset.title}</h3>
      </header>
      <p className={styles.meta}>
        <span>{IP_TYPE_LABEL[asset.ip_type] ?? asset.ip_type}</span>
        {" · "}
        <span>{asset.publication_id}</span>
        {asset.publication_date ? ` · ${asset.publication_date}` : ""}
      </p>
      <p className={styles.holder}>Titular: {asset.assignees.length > 0 ? asset.assignees.join(", ") : "No disponible"}</p>
      <details className={styles.details} open={defaultOpen}>
        <summary>Datos del activo</summary>
        {asset.abstract_language === "en" && <p className={styles.note}>Resumen en inglés</p>}
        <p>{asset.abstract}</p>
        {asset.inventors.length > 0 && <p>Inventores: {asset.inventors.join(", ")}</p>}
        {asset.cpc_codes.length > 0 && <p>CPC del activo: {asset.cpc_codes.join(", ")}</p>}
      </details>
      <p className={styles.source}>
        Fuente:{" "}
        <a href={asset.source_links.google_patents} target="_blank" rel="noreferrer">
          Google Patents
        </a>
        {" · "}
        <a href={asset.source_links.espacenet} target="_blank" rel="noreferrer">
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
  const selectedPanel = useRef<HTMLElement | null>(null);

  // The demand list is long: bring the chosen demand and its results into view. Again when results arrive,
  // because the page is too short to scroll that far until they do.
  useEffect(() => {
    selectedPanel.current?.scrollIntoView?.({ block: "start" });
  }, [selected, result]);

  const choose = useCallback(
    (demandId: string) => {
      const request = ++latestRequest.current;
      setSelected(demandId);
      window.history.replaceState(null, "", `${window.location.pathname}?demanda=${encodeURIComponent(demandId)}`);
      setResult(null);
      setError(null);
      setLoading(true);
      api
        .getMatches(demandId)
        .then((response) => {
          if (request === latestRequest.current) setResult(response);
        })
        .catch((err) => {
          if (request === latestRequest.current) {
            setError(err instanceof ApiError && err.code !== "UNKNOWN_ERROR" ? err.message : "No se pudieron cargar los resultados.");
          }
        })
        .finally(() => {
          if (request === latestRequest.current) setLoading(false);
        });
    },
    [api],
  );

  useEffect(() => {
    api
      .getDemandExamples()
      .then((response) => {
        setExamples(response);
        const requested = new URLSearchParams(window.location.search).get("demanda");
        if (requested && response.demands.some((d) => d.demand_id === requested)) choose(requested);
      })
      .catch(() => setError("No se pudieron cargar las demandas de ejemplo."));
  }, [api, choose]);

  const selectedDemand = examples?.demands.find((d) => d.demand_id === selected);

  return (
    <div className={styles.view}>
      <h1 className={styles.title}>De una demanda real a activos españoles</h1>
      <p className={styles.intro}>
        Demandas de ejemplo ingeridas desde Innoget. Elige una para ver qué activos de propiedad industrial españoles
        pueden ser relevantes.
      </p>
      {examples && <Notices notices={examples.notices} />}

      <section aria-label="Demandas" className={styles.demands}>
        {examples?.demands.map((demand) => (
          <button
            key={demand.demand_id}
            type="button"
            onClick={() => choose(demand.demand_id)}
            aria-pressed={selected === demand.demand_id}
            className={`${styles.demand} ${selected === demand.demand_id ? styles.demandSelected : ""}`}
          >
            {demand.title}
          </button>
        ))}
      </section>

      {selectedDemand && (
        <section aria-label="Demanda seleccionada" ref={selectedPanel} className={styles.selectedDemand}>
          <h2 className={styles.selectedTitle}>{selectedDemand.title}</h2>
          <p className={styles.selectedText}>{selectedDemand.description}</p>
          {selectedDemand.source_url && (
            <p className={styles.source}>
              <a href={selectedDemand.source_url} target="_blank" rel="noreferrer">
                Ver demanda original
              </a>
            </p>
          )}
        </section>
      )}

      {loading && <p role="status" className={styles.status}>Buscando activos…</p>}
      {error && <p role="alert" className={styles.error}>{error}</p>}
      {result && result.assets.length === 0 && <p className={styles.status}>No hay activos elegibles para esta demanda.</p>}
      {result && result.assets.length > 0 && (
        <section aria-label="Resultados" className={styles.results}>
          <p className={styles.status}>
            Mostrando {result.assets.length} de {result.meta.eligible_count.toLocaleString("es-ES")} activos elegibles
          </p>
          {result.assets.map((asset, index) => (
            <AssetCard key={asset.publication_id} asset={asset} defaultOpen={index === 0} />
          ))}
        </section>
      )}
    </div>
  );
}
