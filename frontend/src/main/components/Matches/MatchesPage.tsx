import { BrandHeader } from "../shared/BrandHeader";
import { MatchesView } from "./MatchesView";
import styles from "./MatchesView.module.css";

export function MatchesPage() {
  return (
    <div className={styles.page}>
      <div className={styles.content}>
        <BrandHeader />
        <main>
          <MatchesView />
        </main>
      </div>
    </div>
  );
}
