import { useState } from "react";
import { TOPICS } from "../../infrastructure/topicMapLoader";
import * as S from "../../application/topicMapStrings";
import styles from "./TopicMapPage.module.css";

const plain = (s: string) => s.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase().trim();

export function EntryView() {
  const [query, setQuery] = useState("");
  const found = TOPICS.filter((t) => plain(t.name).includes(plain(query)));
  return (
    <>
      <h1>{S.entryHeading}</h1>
      <label className={styles.search}>
        {S.searchLabel}
        <input type="search" value={query} onChange={(e) => setQuery(e.target.value)} />
      </label>
      {found.length ? (
        <ul className={styles.bigLinks}>
          {found.map((t) => (
            <li key={t.key}>
              <a href={`#/${t.key}`}>{t.name}</a>
            </li>
          ))}
        </ul>
      ) : (
        <p>{S.noTopic}</p>
      )}
    </>
  );
}
