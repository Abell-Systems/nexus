import { commonPeak, mapCells } from "../../application/sectionMap";
import { TEXT, type DensityResults, type SectionDensity } from "../../domain/whitespace";
import styles from "./WhiteSpacePage.module.css";

function SectionMap({ map, peak }: { readonly map: SectionDensity; readonly peak: number }) {
  const { sections, rows } = mapCells(map, peak);
  const fmt = new Intl.NumberFormat("es-ES");
  return (
    <div className={styles.scroll}>
      <table className={`${styles.table} ${styles.heat}`}>
        <caption>Origen {map.origin}: % de pares de subclases activas ya vistos juntos, por sección</caption>
        <thead>
          <tr>
            <th scope="col"><span className={styles.sr}>Sección</span></th>
            {sections.map((section) => (
              <th key={section} scope="col">{section}<small>{map.active_subclasses_by_section[section]}</small></th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={sections[index]}>
              <th scope="row">{sections[index]}<small>{map.active_subclasses_by_section[sections[index]]}</small></th>
              {row.map((cell) => (
                <td
                  key={cell.column}
                  className={styles[`l${cell.level}` as keyof typeof styles]}
                  title={`${fmt.format(cell.seenPairs)} de ${fmt.format(cell.possiblePairs)} pares posibles`}
                >
                  {cell.seenPercent.toFixed(0)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function SectionMapSection({ density }: { readonly density: DensityResults }) {
  const maps = Object.keys(density).sort((a, b) => a.localeCompare(b)).map((origin) => density[origin]);
  const peak = commonPeak(maps);
  return (
    <section id="mapa" className={styles.section} aria-labelledby="mapa-titulo">
      <h2 id="mapa-titulo">Mapa de co-clasificación observada</h2>
      <p>
        Entre las subclases IPC activas (al menos {maps[0].min_documents} documentos), qué porcentaje de pares ya aparece junto en algún documento
        publicado hasta el origen, agrupado por sección IPC (A a H; bajo cada letra, el número de subclases activas). {TEXT.absenceIsNotOpportunity}
      </p>
      <p>
        Escala de color <strong>común a ambos mapas</strong>:{" "}
        <span className={styles.ramp} aria-hidden="true">
          {[0, 1, 2, 3, 4, 5].map((n) => <i key={n} className={styles[`l${n}` as keyof typeof styles]} />)}
        </span>
        de 0 % a {peak.toFixed(0)} %. Pase el cursor por una celda para ver el recuento.
      </p>
      <div className={styles.maps}>
        {maps.map((map) => <SectionMap key={map.origin} map={map} peak={peak} />)}
      </div>
      <p>Los datos de 2022 incluyen la historia con el hueco de 2010 y la ausencia del tipo Y.</p>
    </section>
  );
}
