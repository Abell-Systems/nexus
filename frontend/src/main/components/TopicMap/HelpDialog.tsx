import { useEffect, useRef, useState } from "react";
import * as S from "./strings";
import styles from "./TopicMapPage.module.css";

export function HelpDialog() {
  const [open, setOpen] = useState(false);
  const opener = useRef<HTMLButtonElement>(null);
  const closer = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (open) closer.current?.focus();
  }, [open]);
  const dismiss = () => {
    setOpen(false);
    opener.current?.focus();
  };
  return (
    <>
      <button ref={opener} type="button" className={styles.helpButton} onClick={() => setOpen(true)}>
        {S.help}
      </button>
      {open && (
        <div className={styles.backdrop}>
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="topic-help-title"
            className={styles.dialog}
            onKeyDown={(e) => {
              if (e.key === "Escape") dismiss();
              if (e.key === "Tab") e.preventDefault(); // ponytail: the close button is the only focusable element
            }}
          >
            <h2 id="topic-help-title">{S.helpHeading}</h2>
            <ul>
              {S.helpPoints.map((p) => (
                <li key={p}>{p}</li>
              ))}
            </ul>
            <button ref={closer} type="button" className={styles.helpButton} onClick={dismiss}>
              {S.close}
            </button>
          </div>
        </div>
      )}
    </>
  );
}
