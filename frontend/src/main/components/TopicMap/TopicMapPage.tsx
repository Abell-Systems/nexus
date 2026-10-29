import { useEffect, useState } from "react";
import type { TopicMapResult } from "../../domain/topicMap";
import { TOPICS, loadTopicMap } from "../../infrastructure/topicMapLoader";
import { CluesView } from "./CluesView";
import { EntryView } from "./EntryView";
import { EvolutionView } from "./EvolutionView";
import { HelpDialog } from "./HelpDialog";
import { PlayersView } from "./PlayersView";
import { SummaryView } from "./SummaryView";
import { ThemesView } from "./ThemesView";
import * as S from "./strings";
import styles from "./TopicMapPage.module.css";

const VIEWS = { evolucion: EvolutionView, tema: ThemesView, quien: PlayersView, pistas: CluesView } as const;
type ViewKey = keyof typeof VIEWS;
type Loaded = { topic: string; result: TopicMapResult | null };

function useHashRoute() {
  const read = () => window.location.hash.replace(/^#\/?/, "").split("/");
  const [parts, setParts] = useState(read);
  useEffect(() => {
    const onChange = () => setParts(read());
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  const topic = TOPICS.find((t) => t.key === parts[0]);
  return { topic, view: Object.hasOwn(VIEWS, parts[1]) ? (parts[1] as ViewKey) : null };
}

export function TopicMapPage({ load = loadTopicMap }: { readonly load?: (topic: string) => Promise<TopicMapResult> }) {
  const { topic, view } = useHashRoute();
  const [loaded, setLoaded] = useState<Loaded | null>(null);
  const key = topic?.key;
  useEffect(() => {
    if (!key) return;
    let current = true;
    // Any rejection means no data at all: never a partial page.
    load(key).then(
      (result) => current && setLoaded({ topic: key, result }),
      () => current && setLoaded({ topic: key, result: null }),
    );
    return () => {
      current = false;
    };
  }, [key, load]);

  const settled = loaded?.topic === key ? loaded : null;
  const result = settled?.result ?? null;
  const View = view ? VIEWS[view] : SummaryView;
  const crumbs = topic ? [S.home, topic.name, ...(view ? [S.views[view]] : [])] : [S.home];

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <nav aria-label={S.breadcrumbLabel}>
          {crumbs.map((c, i) => (
            <span key={c}>
              {i > 0 && S.crumbSeparator}
              {i === 0 && topic ? <a href="#/">{c}</a> : i === 1 && view ? <a href={`#/${topic?.key}`}>{c}</a> : c}
            </span>
          ))}
        </nav>
        <HelpDialog />
      </header>
      <main className={styles.content}>
        {!topic ? (
          <EntryView />
        ) : !settled ? (
          <p>{S.loading}</p>
        ) : !result ? (
          <p>{S.unavailable}</p>
        ) : (
          <>
            {!result.names_reviewed && <p className={styles.unreviewed}><strong>{S.unreviewedMark}</strong> {S.unreviewedExplanation}</p>}
            <View result={result} />
          </>
        )}
      </main>
    </div>
  );
}
