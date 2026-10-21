import { sensitivityRows } from "../../application/sensitivity";
import type { SensitivityResults } from "../../domain/whitespace";
import styles from "./WhiteSpacePage.module.css";

export function SensitivitySection({ results }: { readonly results: SensitivityResults }) {
  const rows = sensitivityRows(results);
  const fmt = new Intl.NumberFormat("es-ES");
  return (
    <section id="sensibilidad" className={styles.section} aria-labelledby="sens-titulo">
      <h2 id="sens-titulo">Qué mueve los recuentos</h2>
      <p>
        Positivos: pares no vistos hasta el origen que aparecen juntos en los tres años siguientes. Son el evento que el estudio intenta describir y
        predecir, no oportunidades.
      </p>
      <div className={styles.scroll}>
        <table className={styles.table}>
          <caption>Positivos en los orígenes de desarrollo bajo cuatro escenarios</caption>
          <thead>
            <tr>
              <th scope="col">Origen</th>
              <th scope="col">Corpus observado</th>
              <th scope="col">Quitando un año de historia (rango)</th>
              <th scope="col">Últimos 3 años de historia</th>
              <th scope="col">Pérdida aleatoria simulada (2,5–97,5 %)</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.origin}>
                <th scope="row">{row.origin}</th>
                <td>{fmt.format(row.observed)}</td>
                <td>{fmt.format(row.removedYearMin)} – {fmt.format(row.removedYearMax)}</td>
                <td>{fmt.format(row.shortenedHistory)}</td>
                <td>{fmt.format(row.simulatedLow)} – {fmt.format(row.simulatedHigh)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <ul>
        <li>Los recuentos dependen mucho más de la longitud y composición de la historia que de una pérdida aleatoria a las tasas conocidas.</li>
        <li>Quitar un año o acortar la historia cambia el problema (qué pares se consideran no vistos), no solo la cobertura.</li>
        <li>La simulación aleatoria no puede representar la ausencia del tipo Y: no hay publicaciones Y observadas en esos años que borrar ni a las que parecerse.</li>
      </ul>
    </section>
  );
}
