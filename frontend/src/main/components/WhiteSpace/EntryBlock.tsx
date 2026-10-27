import { useId, useState, type FormEvent } from "react";
import { ENTRY_TEXT as T, TEXT, UNOBSERVED_TEXT } from "../../domain/whitespace";
import styles from "./WhiteSpacePage.module.css";

// IPC sections are A to H by definition; the block cannot read the data (nothing is fetched until the person asks).
const SECTIONS = ["A", "B", "C", "D", "E", "F", "G", "H"];
const ADR_0036 = "https://github.com/Abell-Systems/nexus/blob/main/docs/adr/0036-technology-white-space-scientific-scope.md";

interface Props {
  onSubmit: (query: string, section: string) => void;
}

// A way in: it states what the tool shows, takes a symbol or a section and hands them to «Pares no observados»; it fetches nothing,
// lists nothing and recommends nothing. The notice and the status line of the study stay visible beside it.
export function EntryBlock({ onSubmit }: Props) {
  const [query, setQuery] = useState("");
  const [section, setSection] = useState("");
  const ids = { title: useId(), subclass: useId(), section: useId() };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    onSubmit(query, section);
  };

  return (
    <section className={styles.entry} aria-labelledby={ids.title}>
      <h2 id={ids.title}>{T.title}</h2>
      <p>{T.sentence}</p>
      <form className={styles.controls} role="search" onSubmit={submit}>
        <div>
          <label htmlFor={ids.subclass}>{T.subclass}</label>
          <input id={ids.subclass} type="search" autoComplete="off" value={query} placeholder="p. ej. G06N" onChange={(e) => setQuery(e.target.value)} />
        </div>
        <div>
          <label htmlFor={ids.section}>{T.section}</label>
          <select id={ids.section} value={section} onChange={(e) => setSection(e.target.value)}>
            <option value="">{T.noSection}</option>
            {SECTIONS.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
        <div>
          <button type="submit" className={styles.primary}>{T.submit}</button>
        </div>
      </form>
      <p className={styles.note}>
        {UNOBSERVED_TEXT.notice} <a href={ADR_0036}>ADR 0036</a>
      </p>
      <p className={styles.note}><strong>{TEXT.status}</strong></p>
      <p className={styles.note}>
        <a href="#cobertura">{T.howMeasured}</a>
      </p>
    </section>
  );
}
