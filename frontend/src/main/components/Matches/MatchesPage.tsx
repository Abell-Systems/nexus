import { BrandHeader } from "../shared/BrandHeader";
import { SkipLink } from "../shared/SkipLink";
import { MatchesView } from "./MatchesView";
import styles from "./MatchesView.module.css";

export function MatchesPage() {
  return (
    <div className={styles.page}>
      <SkipLink />
      <div className={styles.content}>
        <BrandHeader />
        <main id="contenido" tabIndex={-1}>
          <MatchesView />
        </main>
      </div>
    </div>
  );
}
