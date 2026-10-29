import type { TopicMapResult } from "../../domain/topicMap";
import { dominantApplicant, evolutionSentence, formatNumber } from "../../application/topicSummary";
import * as S from "./strings";
import styles from "./TopicMapPage.module.css";

const WIDTH = 880;
const HEIGHT = 280;
const LEFT = 8;
const BOTTOM = 40;
const TOP = 14;

export function EvolutionView({ result }: { readonly result: TopicMapResult }) {
  const sentence = evolutionSentence(result);
  const dominant = dominantApplicant(result);
  const documents = new Map(result.trend.map((t) => [t.year, t.documents]));
  const applicant = new Map(result.years.map((y, i) => [y, result.top_applicant_recent?.by_year[i] ?? 0]));
  const first = Math.min(...result.trend.map((t) => t.year));
  const last = Math.max(...result.trend.map((t) => t.year));
  const years = Number.isFinite(first) ? Array.from({ length: last - first + 1 }, (_, i) => first + i) : [];
  const hasGap = years.some((y) => !documents.has(y));
  const peak = Math.max(1, ...documents.values());
  const scale = (n: number) => (n / peak) * (HEIGHT - BOTTOM - TOP);
  const step = (WIDTH - LEFT) / Math.max(1, years.length);
  return (
    <>
      <h1>{S.views.evolucion}</h1>
      <p className={styles.lead}>{sentence}</p>
      {years.length > 0 && (
        <>
          <svg className={styles.chart} viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label={sentence}>
            {years.map((year, i) => {
              const x = LEFT + i * step + 2;
              const width = step - 4;
              const n = documents.get(year);
              const base = HEIGHT - BOTTOM;
              return (
                <g key={year}>
                  {n === undefined ? (
                    <>
                      <rect className={styles.gap} x={x} y={TOP} width={width} height={base - TOP} />
                      <title>{S.noDataIn(year)}</title>
                    </>
                  ) : (
                    <>
                      <rect className={styles.bar} x={x} y={base - scale(n)} width={width} height={scale(n)} />
                      {dominant && (
                        <rect className={styles.barApplicant} x={x} y={base - scale(applicant.get(year) ?? 0)} width={width} height={scale(applicant.get(year) ?? 0)}>
                          <title>{S.applicantTitle(dominant.name, year, formatNumber(applicant.get(year) ?? 0))}</title>
                        </rect>
                      )}
                      <title>{S.documentsIn(year, formatNumber(n))}</title>
                    </>
                  )}
                  {year % 5 === 0 && (
                    <text className={styles.axis} x={year === last ? x + width : year === first ? x : x + width / 2} y={HEIGHT - 10} textAnchor={year === last ? "end" : year === first ? "start" : "middle"}>
                      {year}
                    </text>
                  )}
                </g>
              );
            })}
          </svg>
          <div className={styles.legend}>
            <span><i className={`${styles.swatch} ${styles.bar}`} />{S.allDocuments}</span>
            {dominant && <span><i className={`${styles.swatch} ${styles.barApplicant}`} />{S.onlyApplicant(dominant.name)}</span>}
            {hasGap && <span><i className={`${styles.swatch} ${styles.gap}`} />{S.gapLegend(years.find((y) => !documents.has(y))!)}</span>}
          </div>
        </>
      )}
      <p className={styles.note}>{S.axisReminder}</p>
    </>
  );
}
