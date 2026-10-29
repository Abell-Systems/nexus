import type { TopicMapResult } from "../../domain/topicMap";
import { formatNumber } from "../../application/topicSummary";
import { FoldedList } from "./FoldedList";
import * as S from "../../application/topicMapStrings";
import styles from "./TopicMapPage.module.css";

export function CluesView({ result }: { readonly result: TopicMapResult }) {
  const joined = result.topic.joined;
  return (
    <>
      <h1>{S.views.pistas}</h1>
      {result.rare.length === 0 ? (
        <p className={styles.lead}>{S.noClues}</p>
      ) : (
        <>
          <p className={styles.lead}>{S.cluesIntro(joined)}</p>
          <p>{S.cluesUnknown}</p>
          {/* Order as given (alphabetical): never by ratio, no score. */}
          <FoldedList
            items={result.rare}
            row={(r) => (
              <li key={r.name}>
                <strong>{r.name}</strong> <small className={styles.mark}>{S.clueMark}</small>
                <p>{S.clueRow(formatNumber(r.observed), Math.round(r.observed) === 1, joined, formatNumber(r.expected))}</p>
              </li>
            )}
          />
        </>
      )}
      <p className={styles.note}>{S.provisional}</p>
    </>
  );
}
