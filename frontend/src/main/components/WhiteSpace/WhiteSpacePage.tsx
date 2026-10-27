import { useEffect, useState } from "react";
import { whitespaceData } from "../../infrastructure/whitespaceData";
import { TEXT } from "../../domain/whitespace";
import { BrandHeader } from "../shared/BrandHeader";
import { CoverageSection } from "./CoverageSection";
import { EntryBlock } from "./EntryBlock";
import { SectionMapSection } from "./SectionMapSection";
import { UnobservedPairsSection, type PairsRequest } from "./UnobservedPairsSection";
import { SubclassExplorerSection } from "./SubclassExplorerSection";
import { SensitivitySection } from "./SensitivitySection";
import { TraceabilitySection } from "./TraceabilitySection";
import styles from "./WhiteSpacePage.module.css";

export function WhiteSpacePage() {
  const [request, setRequest] = useState<PairsRequest | null>(null);
  useEffect(() => {
    document.title = "Abell Nexus — Cobertura y ausencias del corpus de patentes";
  }, []);
  const { exposure, density, sensitivity, provenance, corpusIdentity } = whitespaceData;
  // The entry block hands a symbol or a section to «Pares no observados» and moves there; nothing is fetched until it does.
  const goToPairs = (query: string, section: string) => {
    setRequest((previous) => ({ id: (previous?.id ?? 0) + 1, query, section }));
    window.location.hash = "pares-no-observados";
  };

  return (
    <div className={styles.page}>
      <div className={styles.content}>
        <BrandHeader />
        <nav className={styles.nav} aria-label="Secciones de la página">
          <a href="#resumen">Resumen</a>
          <a href="#cobertura">Cobertura</a>
          <a href="#mapa">Mapa de co-clasificación</a>
          <a href="#explorador">Explorador de subclases</a>
          <a href="#pares-no-observados">Pares no observados</a>
          <a href="#sensibilidad">Qué mueve los recuentos</a>
          <a href="#trazabilidad">Trazabilidad</a>
          <a href="#estado">Estado</a>
        </nav>
        <main>
          <section id="resumen" aria-labelledby="resumen-titulo">
            <h1 id="resumen-titulo" className={styles.title}>Cobertura y ausencias del corpus de patentes</h1>
            <p className={styles.lead}>
              Estado descriptivo del estudio sobre combinaciones de subclases IPC en las publicaciones de la OEPM: qué datos tiene el corpus, cuáles
              faltan y qué se ha medido hasta ahora.
            </p>
            <EntryBlock onSubmit={goToPairs} />
            <p className={styles.banner}>
              <strong>{TEXT.notValidation}</strong> {TEXT.absenceIsNotOpportunity}
            </p>
          </section>
          <CoverageSection results={exposure} />
          <SectionMapSection density={density} />
          <SubclassExplorerSection />
          <UnobservedPairsSection request={request} />
          <SensitivitySection results={sensitivity} />
          <TraceabilitySection provenance={provenance} corpusIdentity={corpusIdentity} exposure={exposure} />
          <section id="estado" className={styles.status} aria-labelledby="estado-titulo">
            <h2 id="estado-titulo">Estado de la función de white spaces</h2>
            <p><strong>{TEXT.status}</strong></p>
            <p>No hay en esta página ninguna puntuación, ranking ni selección de combinaciones: el explorador solo describe qué pares se han observado.</p>
          </section>
        </main>
        <footer className={styles.footer}>
          <p>{TEXT.attribution}. {TEXT.downloadDate} {TEXT.noSponsorship}</p>
        </footer>
      </div>
    </div>
  );
}
