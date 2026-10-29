import type { TopicMapResult } from "../../domain/topicMap";
import { formatNumber } from "../../application/topicSummary";
import { listAnd } from "../../application/spanishList";
import { FoldedList } from "./FoldedList";
import * as S from "./strings";
import styles from "./TopicMapPage.module.css";

export function PlayersView({ result }: { readonly result: TopicMapResult }) {
  const [top, ...rest] = result.applicants;
  return (
    <>
      <h1>{S.views.quien}</h1>
      {top && result.total_documents > 0 && (
        <p className={styles.lead}>
          {S.playersSentence(top.name, formatNumber((100 * top.documents) / result.total_documents), listAnd(rest.slice(0, 2).map((a) => a.name)))}
        </p>
      )}
      <FoldedList
        items={result.applicants}
        row={(a) => (
          <li key={a.name} title={a.originals.join("; ")}>
            <strong>{a.name}</strong> <span className={styles.note}>{S.documents(formatNumber(a.documents))}</span>
          </li>
        )}
      />
      <p className={styles.note}>{S.applicantsNote}</p>
    </>
  );
}
