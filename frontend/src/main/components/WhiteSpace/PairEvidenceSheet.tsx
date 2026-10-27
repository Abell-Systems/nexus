import { useEffect, useId, useRef, useState } from "react";
import { buildEvidence, type YearPoint } from "../../application/pairEvidence";
import { SHEET_TEXT as T, TEXT, UNOBSERVED_TEXT, type UnobservedPairsResults } from "../../domain/whitespace";
import styles from "./WhiteSpacePage.module.css";

const count = new Intl.NumberFormat("es-ES");
const nine = new Intl.NumberFormat("es-ES", { minimumFractionDigits: 9, maximumFractionDigits: 9 });
// Presentation only: the terms are shown shortened by default; the sum and the stored value always carry the nine stored decimals,
// and the concordance is decided on the full values (expectedTerms.ts), never on what is displayed.
const four = new Intl.NumberFormat("es-ES", { minimumFractionDigits: 4, maximumFractionDigits: 4 });
const SERIES_A = "#2f5d8a";
const SERIES_B = "#6b7b93";

const WIDTH = 560;
const HEIGHT = 150;
const PAD = { left: 38, right: 8, top: 10, bottom: 22 };

interface Props {
  data: UnobservedPairsResults;
  a: string;
  b: string;
  /** SHA-256 of the result the page verified before drawing anything (the entry of the bundle's manifest). */
  resultSha256: string;
  /** Identity of the OEPM inventory, taken from the exposure result and not from this one. */
  authorityFile: { name: string; sha256: string };
  onClose: () => void;
}

function ActivityChart({ symbol, points, pick, max, tone }: { symbol: string; points: YearPoint[]; pick: (p: YearPoint) => number | null; max: number; tone: string }) {
  const ids = { t: useId(), d: useId() };
  const slot = (WIDTH - PAD.left - PAD.right) / points.length;
  const plotHeight = HEIGHT - PAD.top - PAD.bottom;
  return (
    <svg className={styles.chart} viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-labelledby={`${ids.t} ${ids.d}`} data-max={max}>
      <title id={ids.t}>Documentos por año de {symbol}</title>
      <desc id={ids.d}>
        Documentos por año de publicación de la subclase {symbol}, de {points[0].year} a {points[points.length - 1].year}, con la misma escala que la otra subclase
        (máximo {count.format(max)}). {points.some((p) => pick(p) === null) ? `Los años sin publicaciones en el corpus se marcan como hueco: ${T.gap}` : ""}
      </desc>
      <line className={styles.gridline} x1={PAD.left} x2={WIDTH - PAD.right} y1={HEIGHT - PAD.bottom} y2={HEIGHT - PAD.bottom} />
      <text className={styles.axis} x={PAD.left - 4} y={PAD.top + 8} textAnchor="end">{count.format(max)}</text>
      <text className={styles.axis} x={PAD.left - 4} y={HEIGHT - PAD.bottom} textAnchor="end">0</text>
      {points.map((point, index) => {
        const value = pick(point);
        const x = PAD.left + index * slot;
        if (value === null) {
          return (
            <rect key={point.year} className={styles.gap} x={x + 1} y={PAD.top} width={Math.max(slot - 2, 1)} height={plotHeight} data-gap={point.year}>
              <title>{point.year}: {T.gap}</title>
            </rect>
          );
        }
        const height = (value / max) * plotHeight;
        return (
          <rect key={point.year} className={tone} x={x + 1} y={HEIGHT - PAD.bottom - height} width={Math.max(slot - 2, 1)} height={height}>
            <title>{point.year}: {count.format(value)}</title>
          </rect>
        );
      })}
      {points.map((point, index) =>
        index % 5 === 0 || index === points.length - 1 ? (
          <text key={point.year} className={styles.axis} x={PAD.left + index * slot + slot / 2} y={HEIGHT - 6} textAnchor="middle">{point.year}</text>
        ) : null,
      )}
    </svg>
  );
}

export function PairEvidenceSheet({ data, a, b, resultSha256, authorityFile, onClose }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const [fullPrecision, setFullPrecision] = useState(false);
  const evidence = buildEvidence(data, a, b);
  useEffect(() => ref.current?.focus(), [a, b]);
  if (!evidence) return null;
  const { reconstruction: r, years } = evidence;
  const parameters = data.configuration.parameters;

  return (
    <div ref={ref} tabIndex={-1} className={styles.detail} role="region" aria-label={`${T.title} ${a} y ${b}`}>
      <h3>{T.title} {a} y {b}</h3>

      <h4>{T.documents}</h4>
      <p>
        {a}: {count.format(evidence.documentsA)} documentos · {b}: {count.format(evidence.documentsB)} documentos.
      </p>

      <h4>{T.activityTitle}</h4>
      <p className={styles.legend}>
        <span><i className={styles.swatch} style={{ background: SERIES_A }} />{a}</span>
        <span><i className={styles.swatch} style={{ background: SERIES_B }} />{b}</span>
      </p>
      <p className={styles.note}>{a}</p>
      <ActivityChart symbol={a} points={years} pick={(p) => p.countA} max={evidence.maxCount} tone={styles.present} />
      <p className={styles.note}>{b}</p>
      <ActivityChart symbol={b} points={years} pick={(p) => p.countB} max={evidence.maxCount} tone={styles.seriesB} />
      <details>
        <summary>Tabla de datos de la actividad por año</summary>
        <div className={styles.scroll}>
          <table className={styles.table}>
            <caption>{T.activityTitle}</caption>
            <thead>
              <tr>
                <th scope="col">Año</th>
                <th scope="col">{UNOBSERVED_TEXT.columns.docsA}</th>
                <th scope="col">{UNOBSERVED_TEXT.columns.docsB}</th>
              </tr>
            </thead>
            <tbody>
              {years.map((y) =>
                y.countA === null ? (
                  <tr key={y.year}>
                    <th scope="row">{y.year}</th>
                    <td colSpan={2}>{T.gap}</td>
                  </tr>
                ) : (
                  <tr key={y.year}>
                    <th scope="row">{y.year}</th>
                    <td>{count.format(y.countA)}</td>
                    <td>{count.format(y.countB ?? 0)}</td>
                  </tr>
                ),
              )}
            </tbody>
          </table>
        </div>
      </details>

      <p>{T.bothZero}.</p>
      <p className={styles.note}>{TEXT.absenceIsNotOpportunity}</p>

      <h4>{T.termsTitle}</h4>
      <p>{T.definition}</p>
      <dl>
        <dt>Suma reconstruida</dt>
        <dd>{nine.format(r.rounded)}</dd>
        <dt>{UNOBSERVED_TEXT.columns.expected}, valor almacenado</dt>
        <dd>{nine.format(evidence.stored)}</dd>
      </dl>
      {r.concordant ? (
        <p role="status">{T.concordant}</p>
      ) : (
        <p role="alert">
          {T.discrepancy} Diferencia: {nine.format(r.rounded - evidence.stored)}.
        </p>
      )}
      <details>
        <summary>Tabla de los términos por año</summary>
        <p className={styles.note}>
          {fullPrecision ? "Términos con 9 decimales." : "Términos con 4 decimales para leerlos; la suma reconstruida se calcula con los valores completos."}{" "}
          <button type="button" aria-pressed={fullPrecision} onClick={() => setFullPrecision(!fullPrecision)}>
            Mostrar precisión completa
          </button>
        </p>
        <div className={styles.scroll}>
          <table className={styles.table}>
            <caption>{T.termsTitle}</caption>
            <thead>
              <tr>
                <th scope="col">Año</th>
                <th scope="col">{UNOBSERVED_TEXT.columns.docsA}</th>
                <th scope="col">{UNOBSERVED_TEXT.columns.docsB}</th>
                <th scope="col">Documentos del año</th>
                <th scope="col">Término</th>
              </tr>
            </thead>
            <tbody>
              {r.terms.map((t) => (
                <tr key={t.year}>
                  <th scope="row">{t.year}</th>
                  <td>{count.format(t.countA)}</td>
                  <td>{count.format(t.countB)}</td>
                  <td>{count.format(t.total)}</td>
                  <td>{(fullPrecision ? nine : four).format(t.term)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>

      <h4>{T.identityTitle}</h4>
      <dl>
        <dt>Corpus</dt>
        <dd>{data.corpus.source_id}</dd>
        <dt>SHA-256 del resultado</dt>
        <dd className={styles.mono}>{resultSha256}</dd>
        <dt>Identificador de configuración</dt>
        <dd className={styles.mono}>{data.configuration.id}</dd>
        <dt>Parámetros de la configuración</dt>
        <dd>
          Año de referencia {parameters.origin}; mínimo de {parameters.min_documents} documentos para una subclase activa; esperado mínimo del tipo con esperado ≥ 1: {parameters.e_min};
          unidad: identificador de publicación ({String(parameters.unit)}); cantidad: {String(parameters.quantity)}.
        </dd>
        <dt>Inventario de la OEPM (tomado del resultado de exposición)</dt>
        <dd>
          {authorityFile.name} · <span className={styles.mono}>{authorityFile.sha256}</span>
        </dd>
      </dl>
      <details>
        <summary>SHA-256 de los {Object.keys(data.corpus.files).length} ficheros del corpus</summary>
        <div className={styles.scroll}>
          <table className={styles.table}>
            <caption>Ficheros del corpus</caption>
            <thead>
              <tr>
                <th scope="col">Fichero</th>
                <th scope="col">SHA-256</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(data.corpus.files).map(([name, hash]) => (
                <tr key={name}>
                  <th scope="row">{name}</th>
                  <td className={styles.mono}>{hash}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
      <p className={styles.note}>{TEXT.attribution}. {TEXT.downloadDate}</p>

      <h4>{T.listsTitle}</h4>
      <p>{T.listsUnavailable}</p>

      <h4>{T.limitsTitle}</h4>
      <p className={styles.note}>{UNOBSERVED_TEXT.limits}</p>
      <p className={styles.note}>{UNOBSERVED_TEXT.parameters}</p>
      <p>{T.beforeInterpreting}</p>

      <button type="button" onClick={onClose}>{T.close}</button>
    </div>
  );
}
