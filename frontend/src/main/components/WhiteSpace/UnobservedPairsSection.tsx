import { useEffect, useId, useRef, useState } from "react";
import { listPairs, searchSymbols, sectionsOf, type PairSort, type PairType } from "../../application/unobservedPairs";
import { TEXT, UNOBSERVED_TEXT as T, type UnobservedPairsResults } from "../../domain/whitespace";
import { loadUnobservedPairs } from "../../infrastructure/unobservedPairsLoader";
import { IntegrityError } from "../../infrastructure/verifiedLoader";
import styles from "./WhiteSpacePage.module.css";

const MAX_MATCHES = 12;
const PAGE = 200;
const ADR_0036 = "https://github.com/Abell-Systems/nexus/blob/main/docs/adr/0036-technology-white-space-scientific-scope.md";
const count = new Intl.NumberFormat("es-ES");
const oneDecimal = new Intl.NumberFormat("es-ES", { minimumFractionDigits: 1, maximumFractionDigits: 1 });

type Load = { state: "idle" | "loading" | "load-error" | "integrity-error" } | { state: "ready"; data: UnobservedPairsResults };

export interface PairsRequest {
  id: number;
  query: string;
  section: string;
}

export function UnobservedPairsSection({ request = null }: { request?: PairsRequest | null }) {
  const [load, setLoad] = useState<Load>({ state: "idle" });
  const [query, setQuery] = useState("");
  const [symbol, setSymbol] = useState<string | null>(null);
  const [section, setSection] = useState("");
  const [type, setType] = useState<PairType>("all");
  const [sort, setSort] = useState<PairSort>("symbol");
  const [shown, setShown] = useState(PAGE);
  const ids = { search: useId(), section: useId(), type: useId(), sort: useId() };
  const searchRef = useRef<HTMLInputElement>(null);
  const handled = useRef(0);
  const pending = useRef<string | null>(null);

  // The file is fetched at the first touch of a control, never when the page opens; no pair is drawn until a subclass or a section is chosen.
  const fetchData = () => {
    setLoad({ state: "loading" });
    loadUnobservedPairs().then(
      (data) => setLoad({ state: "ready", data }),
      (error) => setLoad({ state: error instanceof IntegrityError ? "integrity-error" : "load-error" }),
    );
  };
  const start = () => {
    if (load.state === "idle") fetchData();
  };

  const data = load.state === "ready" ? load.data : null;
  const matches = data ? searchSymbols(data, query) : [];
  const rows = data ? listPairs(data, { symbol, section, type, sort }) : [];
  const chosen = Boolean(data && (symbol || section));
  // «No match» is its own state: verified data are in, something was typed, no active subclass contains it and none is selected.
  // It is neither the initial state (nothing chosen yet) nor an error. Its sentence goes into a live region that is always in the page,
  // so that the change is announced without moving the focus and without a new request.
  const noMatchText = data && !symbol && query.trim() && matches.length === 0 ? T.noMatch(query.trim()) : "";
  const reset = () => setShown(PAGE);

  // A request from the entry block: take its symbol and section, fetch if nothing has been fetched yet, and move the focus to the search.
  // Choosing the subclass waits for the verified data, and only when the text is exactly an active symbol; nothing else selects it.
  useEffect(() => {
    if (!request || handled.current === request.id) return;
    handled.current = request.id;
    setQuery(request.query);
    setSection(request.section);
    setSymbol(null);
    setShown(PAGE);
    pending.current = request.query.trim().toUpperCase() || null;
    if (load.state === "idle") fetchData();
    searchRef.current?.focus();
  }, [request]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (!data || pending.current === null) return;
    if (pending.current in data.active) setSymbol(pending.current);
    pending.current = null;
  }, [data]);

  return (
    <section id="pares-no-observados" className={styles.section} aria-labelledby="pares-no-observados-titulo">
      <h2 id="pares-no-observados-titulo">{T.title}</h2>
      <p className={styles.banner}>
        {T.notice} <a href={ADR_0036}>ADR 0036</a>
      </p>
      <p className={styles.note}>{T.parameters}</p>
      <p className={styles.note}>{T.limits}</p>
      <p className={styles.note}>{TEXT.absenceIsNotOpportunity}</p>

      <div className={styles.controls} onFocus={start}>
        <div>
          <label htmlFor={ids.search}>Buscar subclase por símbolo</label>
          <input ref={searchRef} id={ids.search} type="search" autoComplete="off" value={query} placeholder="p. ej. G06N" onChange={(e) => { setQuery(e.target.value); setSymbol(null); reset(); start(); }} />
        </div>
        <div>
          <label htmlFor={ids.section}>Sección</label>
          <select id={ids.section} value={section} onChange={(e) => { setSection(e.target.value); reset(); }}>
            <option value="">Ninguna</option>
            {(data ? sectionsOf(data) : []).map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
        <div>
          <label htmlFor={ids.type}>Tipo</label>
          <select id={ids.type} value={type} onChange={(e) => { setType(e.target.value as PairType); reset(); }}>
            <option value="all">{T.types.all}</option>
            <option value="expected">{T.types.expected}</option>
          </select>
        </div>
        <div>
          <label htmlFor={ids.sort}>Orden</label>
          <select id={ids.sort} value={sort} onChange={(e) => { setSort(e.target.value as PairSort); reset(); }}>
            <option value="symbol">{T.sorts.symbol}</option>
            <option value="docsA">{T.sorts.docsA}</option>
            <option value="docsB">{T.sorts.docsB}</option>
            <option value="expected">{T.sorts.expected}</option>
          </select>
        </div>
      </div>

      {load.state === "loading" && <p role="status">{T.loading}</p>}
      {load.state === "load-error" && (
        <p role="alert">{T.loadError} <button type="button" onClick={fetchData}>Reintentar</button></p>
      )}
      {load.state === "integrity-error" && <p role="alert">{T.integrityError}</p>}

      {data && query.trim() && !symbol && matches.length > 0 && (
        <ul className={styles.matches} aria-label="Subclases que coinciden con la búsqueda">
          {matches.slice(0, MAX_MATCHES).map((match) => (
            <li key={match}>
              <button type="button" onClick={() => { setSymbol(match); setQuery(match); reset(); }}>
                {match} <small>{count.format(data.active[match])} documentos</small>
              </button>
            </li>
          ))}
          {matches.length > MAX_MATCHES && <li>… {matches.length - MAX_MATCHES} más: escriba más caracteres.</li>}
        </ul>
      )}

      <p role="status" className={styles.note}>{noMatchText}</p>
      {(load.state === "idle" || (data && !chosen)) && !noMatchText && <p>{T.start}</p>}
      {chosen && sort === "expected" && <p className={styles.note} role="note">{T.expectedSortNotice}</p>}
      {chosen && rows.length === 0 && <p>{symbol && !section && type === "all" ? T.noPairsForSubclass : T.none}</p>}
      {chosen && rows.length > 0 && (
        <>
          <p role="status">Mostrando {count.format(Math.min(shown, rows.length))} de {count.format(rows.length)} pares.</p>
          <div className={styles.scroll}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th scope="col">{T.columns.a}</th>
                  <th scope="col">{T.columns.b}</th>
                  <th scope="col">{T.columns.docsA}</th>
                  <th scope="col">{T.columns.docsB}</th>
                  <th scope="col">{T.columns.expected}</th>
                </tr>
              </thead>
              <tbody>
                {rows.slice(0, shown).map((row) => (
                  <tr key={`${row.a}|${row.b}`}>
                    <th scope="row">{row.a}</th>
                    <td>{row.b}</td>
                    <td>{count.format(row.docsA)}</td>
                    <td>{count.format(row.docsB)}</td>
                    <td>{oneDecimal.format(row.expected)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {shown < rows.length && <button type="button" onClick={() => setShown(shown + PAGE)}>Mostrar más</button>}
        </>
      )}
    </section>
  );
}
