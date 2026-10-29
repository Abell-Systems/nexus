import type { ReactNode } from "react";
import { visibleAndFolded } from "../../application/topicSummary";
import * as S from "../../application/topicMapStrings";
import styles from "./TopicMapPage.module.css";

export function FoldedList<T>({ items, row }: { readonly items: T[]; readonly row: (item: T) => ReactNode }) {
  const { visible, folded } = visibleAndFolded(items);
  return (
    <>
      <ul className={styles.rows}>{visible.map(row)}</ul>
      {folded.length > 0 && (
        <details>
          <summary>{S.more(folded.length)}</summary>
          <ul className={styles.rows}>{folded.map(row)}</ul>
        </details>
      )}
    </>
  );
}
