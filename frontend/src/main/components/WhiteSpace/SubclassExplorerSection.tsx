import { useEffect, useId, useRef, useState } from "react";
import {
  filterRows,
  pairDetail,
  pairRows,
  searchSubclasses,
  sortRows,
  type SeenFilter,
  type SortKey,
} from "../../application/subclassExplorer";
import { EXPLORER_TEXT, TEXT, type PairsResults } from "../../domain/whitespace";
import { loadSubclassPairs } from "../../infrastructure/subclassPairsLoader";
import styles from "./WhiteSpacePage.module.css";

const fmt = new Intl.NumberFormat("es-ES");
const MAX_MATCHES = 12;

export function SubclassExplorerSection() {
  const [data, setData] = useState<PairsResults | null>(null);
  const [failed, setFailed] = useState(false);
  const [started, setStarted] = useState(false);
  const [enterPending, setEnterPending] = useState(false);
  const [originKey, setOriginKey] = useState("2022");
  const [query, setQuery] = useState("");
  const [symbol, setSymbol] = useState<string | null>(null);
  const [seen, setSeen] = useState<SeenFilter>("all");
  const [section, setSection] = useState("all");
  const [sort, setSort] = useState<SortKey>("symbol");
  const [other, setOther] = useState<string | null>(null);
  const detailRef = useRef<HTMLDivElement>(null);
  const ids = { origin: useId(), search: useId(), seen: useId(), section: useId(), sort: useId() };

  // On demand: the 6 MB file is fetched when the user first touches a control of the explorer, not when the page opens.
  const start = () => {
    if (data) return;
    setStarted(true);
    setFailed(false);
    loadSubclassPairs().then(setData, () => setFailed(true));
  };
  useEffect(() => {
    if (other) detailRef.current?.focus();
  }, [other]);

  const origin = data?.[originKey];
  const matches = origin ? searchSubclasses(origin, query) : [];
  const chosen = origin && symbol && symbol in origin.active ? symbol : null;
  const rows = origin && chosen ? sortRows(filterRows(pairRows(origin, chosen), { seen, section }), sort) : [];
  const sections = origin ? [...new Set(Object.keys(origin.active).map((s) => s[0]))].sort((a, b) => a.localeCompare(b)) : [];
  const detail = origin && chosen && other ? pairDetail(origin, chosen, other) : null;

  const choose = (next: string) => {
    setSymbol(next);
    setOther(null);
    setQuery(next);
  };
  // Enter pressed while the file was still arriving is applied when it arrives, not lost.
  useEffect(() => {
    if (!enterPending || !origin) return;
    setEnterPending(false);
    const [first] = searchSubclasses(origin, query);
    if (first) {
      setSymbol(first);
      setOther(null);
      setQuery(first);
    }
  }, [enterPending, origin, query]);

  return (
    <section id="explorador" className={styles.section} aria-labelledby="explorador-titulo">
      <h2 id="explorador-titulo">Explorador de subclases</h2>
      <p>
        Elija una subclase IPC y vea, para cada otra subclase activa, si el par se ha observado junto en el corpus y con qué recuentos. Es una consulta
        descriptiva: {EXPLORER_TEXT.noScore} {EXPLORER_TEXT.symbolsOnly}
      </p>
      <div className={styles.controls} onFocus={start}>
        <div>
          <label htmlFor={ids.origin}>Origen</label>
          <select id={ids.origin} value={originKey} onChange={(e) => { setOriginKey(e.target.value); setOther(null); }}>
            {Object.keys(data ?? { "2022": 0, "2006": 0 }).sort((a, b) => a.localeCompare(b)).map((key) => <option key={key} value={key}>{key}</option>)}
          </select>
        </div>
        <div>
          <label htmlFor={ids.search}>Buscar subclase por símbolo</label>
          <input
            id={ids.search}
            type="search"
            autoComplete="off"
            value={query}
            placeholder="p. ej. G06N"
            onChange={(e) => { setQuery(e.target.value); start(); }}
            onKeyDown={(e) => {
              if (e.key !== "Enter") return;
              if (!origin) setEnterPending(true);
              else if (matches.length > 0) choose(matches[0]);
            }}
          />
        </div>
      </div>
      <p className={styles.note}>{EXPLORER_TEXT.limits} {EXPLORER_TEXT.universe}</p>

      {failed && <p role="alert">No se han podido cargar los datos del explorador.</p>}
      {!data && !failed && started && <p role="status">Cargando datos…</p>}

      {origin && query.trim() && (
        <div role="region" aria-label="Subclases que coinciden con la búsqueda">
          {matches.length === 0 ? (
            <p>Ninguna subclase activa en {originKey} coincide con «{query.trim()}». {EXPLORER_TEXT.universe}</p>
          ) : (
            <ul className={styles.matches}>
              {matches.slice(0, MAX_MATCHES).map((match) => (
                <li key={match}>
                  <button type="button" aria-pressed={match === chosen} onClick={() => choose(match)}>
                    {match} <small>{fmt.format(origin.active[match])} documentos</small>
                  </button>
                </li>
              ))}
              {matches.length > MAX_MATCHES && <li>… {matches.length - MAX_MATCHES} más: escriba más caracteres.</li>}
            </ul>
          )}
        </div>
      )}

      {origin && chosen && (
        <>
          <h3>
            {chosen} en el origen {originKey}
          </h3>
          <p>
            Sección {chosen[0]} · {fmt.format(origin.active[chosen])} documentos publicados hasta {originKey} · primer año visto: {origin.first_years[chosen]}.
          </p>
          <div className={styles.controls}>
            <div>
              <label htmlFor={ids.seen}>Par</label>
              <select id={ids.seen} value={seen} onChange={(e) => setSeen(e.target.value as SeenFilter)}>
                <option value="all">Todos</option>
                <option value="seen">Observados</option>
                <option value="unseen">No observados</option>
              </select>
            </div>
            <div>
              <label htmlFor={ids.section}>Sección de la otra subclase</label>
              <select id={ids.section} value={section} onChange={(e) => setSection(e.target.value)}>
                <option value="all">Todas</option>
                {sections.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div>
              <label htmlFor={ids.sort}>Ordenar por</label>
              <select id={ids.sort} value={sort} onChange={(e) => setSort(e.target.value as SortKey)}>
                <option value="symbol">Símbolo</option>
                <option value="documents">Documentos</option>
                <option value="both">Documentos con ambas</option>
              </select>
            </div>
          </div>
          {seen !== "seen" && <p className={styles.note}>{TEXT.absenceIsNotOpportunity}</p>}
          <p className={styles.note}>{EXPLORER_TEXT.definitions}</p>
          <p role="status">Mostrando {fmt.format(rows.length)} subclases.</p>
          <div className={styles.scroll}>
            <table className={styles.table}>
              <caption>Subclases activas en {originKey} frente a {chosen}</caption>
              <thead>
                <tr>
                  <th scope="col">Subclase</th>
                  <th scope="col">Documentos</th>
                  <th scope="col">Par</th>
                  <th scope="col">Documentos con ambas</th>
                  <th scope="col">Primer año visto juntas</th>
                  <th scope="col"><span className={styles.sr}>Detalle</span></th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.symbol}>
                    <th scope="row">{row.symbol}</th>
                    <td>{fmt.format(row.documents)}</td>
                    <td>{row.seen ? "observada" : EXPLORER_TEXT.unseen}</td>
                    <td>{fmt.format(row.both)}</td>
                    <td>{row.firstYear ?? EXPLORER_TEXT.noYear}</td>
                    <td>
                      <button type="button" onClick={() => setOther(row.symbol)} aria-label={`Ver el par ${chosen} y ${row.symbol}`}>
                        Ver par
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {detail && (
        <div ref={detailRef} tabIndex={-1} className={styles.detail} role="region" aria-label={`Par ${detail.a} y ${detail.b}`}>
          <h3>
            Par {detail.a} y {detail.b} · origen {originKey}
          </h3>
          {detail.seen ? (
            <>
              <p>
                {fmt.format(detail.documents)} documentos con ambas hasta {originKey}; primer año visto juntas: {detail.firstYear}.
              </p>
              <div className={styles.scroll}>
                <table className={styles.table}>
                  <caption>Coincidencias por año de publicación</caption>
                  <thead><tr><th scope="col">Año</th><th scope="col">Coincidencias</th></tr></thead>
                  <tbody>
                    {detail.byYear.map(({ year, count }) => (
                      <tr key={year}><th scope="row">{year}</th><td>{fmt.format(count)}</td></tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          ) : (
            <>
              <p>Par {EXPLORER_TEXT.unseen}. Primer año visto juntas: {EXPLORER_TEXT.noYear}.</p>
              <p>{TEXT.absenceIsNotOpportunity}</p>
            </>
          )}
          <button type="button" onClick={() => setOther(null)}>Cerrar el par</button>
        </div>
      )}
    </section>
  );
}
