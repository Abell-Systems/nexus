import { TEXT, type CorpusIdentity, type ExposureResults, type Provenance } from "../../domain/whitespace";
import styles from "./WhiteSpacePage.module.css";

export function TraceabilitySection({
  provenance,
  corpusIdentity,
  exposure,
}: {
  readonly provenance: Provenance;
  readonly corpusIdentity: CorpusIdentity;
  readonly exposure: ExposureResults;
}) {
  const files = Object.entries(corpusIdentity.files);
  return (
    <section id="trazabilidad" className={styles.section} aria-labelledby="traza-titulo">
      <h2 id="traza-titulo">Trazabilidad</h2>
      <p>
        Cada gráfico se dibuja a partir de un resultado versionado en el repositorio; el navegador no recalcula nada. Las copias incluidas en esta
        página son idénticas a los originales, y sus huellas SHA-256 se comprueban en las pruebas.
      </p>
      <div className={styles.scroll}>
        <table className={styles.table}>
          <caption>Resultados que alimentan la página</caption>
          <thead>
            <tr><th scope="col">Fichero y SHA-256</th><th scope="col">Producido por</th><th scope="col">Cambio</th></tr>
          </thead>
          <tbody>
            {provenance.files.map((file) => (
              <tr key={file.file}>
                <th scope="row">
                  {file.source}
                  <span className={styles.mono} style={{ display: "block", fontWeight: 400 }}>{file.sha256}</span>
                </th>
                <td>{file.producedBy}</td>
                <td>#{file.pullRequest}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p>
        Inventario oficial usado: <span className={styles.mono}>{exposure.authority_file.name}</span>, SHA-256{" "}
        <span className={styles.mono}>{exposure.authority_file.sha256}</span>.
      </p>
      <p>{TEXT.downloadDate}</p>
      <details>
        <summary>Identidad del corpus: {files.length} ficheros verificados por huella</summary>
        <div className={styles.scroll}>
          <table className={styles.table}>
            <caption>Ficheros bibliográficos del corpus (2000–2025)</caption>
            <thead><tr><th scope="col">Fichero</th><th scope="col">SHA-256</th></tr></thead>
            <tbody>
              {files.map(([name, file]) => (
                <tr key={name}><th scope="row">{name}</th><td className={styles.mono}>{file.sha256}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </section>
  );
}
