import type { TopicMapResult } from "../../domain/topicMap";
import { formatNumber } from "../../application/topicSummary";
import { listAnd } from "../../application/spanishList";
import { FoldedList } from "./FoldedList";
import * as S from "./strings";
import styles from "./TopicMapPage.module.css";

export function ThemesView({ result }: { readonly result: TopicMapResult }) {
  const top = result.subareas.reduce<TopicMapResult["subareas"][number] | null>((a, s) => (!a || s.documents > a.documents ? s : a), null);
  const peak = Math.max(1, ...result.subareas.map((s) => s.documents));
  const names = result.neighbours.slice(0, 3).map((n) => n.name);
  return (
    <>
      <h1>{S.views.tema}</h1>
      {top && top.documents > 0 && result.total_documents > 0 && (
        <p className={styles.lead}>{S.themesSentence(top.name, formatNumber((100 * top.documents) / result.total_documents))}</p>
      )}
      <h2>{S.subareasHeading}</h2>
      <FoldedList
        items={result.subareas}
        row={(s) => (
          <li key={s.key}>
            <strong>{s.name}</strong> <span className={styles.note}>{S.documents(formatNumber(s.documents))}</span>
            <div className={styles.meter} aria-hidden="true"><span style={{ width: `${(100 * s.documents) / peak}%` }} /></div>
            <p>{s.description}</p>
          </li>
        )}
      />
      {names.length > 0 && (
        <>
          <h2>{S.neighboursHeading}</h2>
          <p>{S.neighboursSentence(listAnd(names))}</p>
          <FoldedList
            items={result.neighbours}
            row={(n) => (
              <li key={n.name}>
                <strong>{n.name}</strong> <span className={styles.note}>{S.documents(formatNumber(n.documents))}</span>
              </li>
            )}
          />
        </>
      )}
    </>
  );
}
