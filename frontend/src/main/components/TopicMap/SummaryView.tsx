import type { TopicMapResult } from "../../domain/topicMap";
import { summarySentence } from "../../application/topicSummary";
import * as S from "../../application/topicMapStrings";
import styles from "./TopicMapPage.module.css";

export function SummaryView({ result }: { readonly result: TopicMapResult }) {
  return (
    <>
      <h1>{result.topic.name}</h1>
      <p className={styles.lead}>{summarySentence(result)}</p>
      <ul className={styles.bigLinks}>
        {(Object.keys(S.views) as (keyof typeof S.views)[]).map((v) => (
          <li key={v}>
            <a href={`#/${result.topic.key}/${v}`}>{S.views[v]}</a>
          </li>
        ))}
      </ul>
    </>
  );
}
