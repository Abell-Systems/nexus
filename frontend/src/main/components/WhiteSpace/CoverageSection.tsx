import { barScale, coverageBars, yearsWhereEveryKindYIsAbsent } from "../../application/coverage";
import { TEXT, type ExposureResults } from "../../domain/whitespace";
import styles from "./WhiteSpacePage.module.css";

const WIDTH = 880;
const HEIGHT = 300;
const LEFT = 46;
const BOTTOM = 28;
const TOP = 14;

export function CoverageSection({ results }: { readonly results: ExposureResults }) {
  const bars = coverageBars(results);
  const scale = barScale(bars, HEIGHT - BOTTOM - TOP);
  const step = (WIDTH - LEFT - 8) / bars.length;
  const peak = Math.max(...bars.map((bar) => bar.inventory));
  const ticks = Array.from({ length: Math.floor(peak / 10000) + 1 }, (_, i) => i * 10000);
  const yearsY = yearsWhereEveryKindYIsAbsent(results);
  const accumulated = results.exposure.accumulated_up_to_origin;
  const fmt = new Intl.NumberFormat("es-ES");

  return (
    <section id="cobertura" className={styles.section} aria-labelledby="cobertura-titulo">
      <h2 id="cobertura-titulo">Cobertura: qué publicaciones tiene el corpus</h2>
      <p>
        El inventario oficial de la OEPM (el <em>Authority File</em>) lista {fmt.format(results.exposure.inventory_publications)} publicaciones
        entre 2000 y 2025. El corpus bibliográfico contiene {fmt.format(results.exposure.corpus_publications)} claves de publicación distintas.
        Cada barra es el inventario de ese año; su parte sólida es lo presente en el corpus.
      </p>
      <svg className={styles.chart} viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-labelledby="cov-t cov-d">
        <title id="cov-t">Publicaciones por año de publicación: presentes y ausentes del corpus</title>
        <desc id="cov-d">
          Barras apiladas de 2000 a 2025. Se distinguen las publicaciones presentes, las ausentes del tipo Y y las demás ausentes. En 2010 no hay
          ninguna publicación presente. El detalle numérico está en la tabla siguiente.
        </desc>
        <defs>
          <pattern id="hatch-y" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
            <rect width="6" height="6" className={styles.hatchBg} />
            <line x1="0" y1="0" x2="0" y2="6" className={styles.hatchLine} />
          </pattern>
        </defs>
        {ticks.map((tick) => (
          <g key={tick}>
            <line className={styles.gridline} x1={LEFT} x2={WIDTH - 8} y1={HEIGHT - BOTTOM - scale(tick)} y2={HEIGHT - BOTTOM - scale(tick)} />
            <text className={styles.axis} x={LEFT - 6} y={HEIGHT - BOTTOM - scale(tick) + 4} textAnchor="end">
              {tick / 1000} mil
            </text>
          </g>
        ))}
        {bars.map((bar, index) => {
          const x = LEFT + index * step + 2;
          const width = step - 4;
          let base = HEIGHT - BOTTOM;
          const parts = [
            { value: bar.present, className: styles.present },
            { value: bar.absentRest, className: styles.absentRest },
            { value: bar.absentY, className: styles.absentY },
          ];
          return (
            <g key={bar.year}>
              {parts.map(({ value, className }, part) => {
                const height = scale(value);
                base -= height;
                return height > 0 ? <rect key={part} className={className} x={x} y={base} width={width} height={height} /> : null;
              })}
              {(bar.year % 2 === 0 || bar.year === 2025) && (
                <text className={styles.axis} x={x + width / 2} y={HEIGHT - 10} textAnchor="middle">
                  {bar.year}
                </text>
              )}
            </g>
          );
        })}
      </svg>
      <div className={styles.legend}>
        <span><i className={styles.swatch} style={{ background: "#2f5d8a" }} />Presente en el corpus</span>
        <span><i className={styles.swatch} style={{ background: "#d19a3d" }} />Ausente, resto de tipos</span>
        <span><i className={styles.swatch} style={{ background: "repeating-linear-gradient(45deg,#b2473e 0 2px,#fff 2px 5px)", border: "1px solid #b2473e" }} />Ausente, tipo Y</span>
      </div>
      <ul className={styles.facts}>
        <li className={styles.fact}>
          <strong>100 %</strong>
          <span>de las publicaciones de tipo Y de {yearsY[0]} a {yearsY[yearsY.length - 1]} están ausentes del corpus</span>
        </li>
        <li className={styles.fact}>
          <strong>{fmt.format(results.exposure.by_year["2010"].ep_translation.inventory + results.exposure.by_year["2010"].kind_y.inventory + results.exposure.by_year["2010"].other.inventory)}</strong>
          <span>publicaciones de 2010 existen en el inventario; el corpus no tiene ninguna</span>
        </li>
        <li className={styles.fact}>
          <strong>{accumulated["2003"].all_groups.absent_share_percent.toFixed(2).replace(".", ",")} % · {accumulated["2006"].all_groups.absent_share_percent.toFixed(2).replace(".", ",")} %</strong>
          <span>del inventario acumulado hasta 2003 y hasta 2006 falta en el corpus</span>
        </li>
        <li className={styles.fact}>
          <strong>{accumulated["2003"].years_with_corpus_publications} y {accumulated["2006"].years_with_corpus_publications} años</strong>
          <span>de historia observada en los orígenes 2003 y 2006: el corpus empieza en 2000</span>
        </li>
      </ul>
      <p>{TEXT.yUnknown}</p>
      <details>
        <summary>Tabla de datos de la cobertura</summary>
        <div className={styles.scroll}>
          <table className={styles.table}>
            <caption>Publicaciones del inventario por año de publicación</caption>
            <thead>
              <tr><th scope="col">Año</th><th scope="col">Inventario</th><th scope="col">Presentes</th><th scope="col">Ausentes, tipo Y</th><th scope="col">Ausentes, resto</th><th scope="col">% ausente</th></tr>
            </thead>
            <tbody>
              {bars.map((bar) => (
                <tr key={bar.year}>
                  <th scope="row">{bar.year}</th>
                  <td>{fmt.format(bar.inventory)}</td><td>{fmt.format(bar.present)}</td><td>{fmt.format(bar.absentY)}</td><td>{fmt.format(bar.absentRest)}</td>
                  <td>{bar.absentShare.toFixed(1).replace(".", ",")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </section>
  );
}
