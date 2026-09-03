import { useState } from "react";
import { AbellMark, BrandHeader } from "../shared/BrandHeader";
import styles from "./LandingView.module.css";

interface LandingViewProps {
  onStartAnalysis: (domain: string, query: string) => void;
  onOpenHistory?: () => void;
  isLoading?: boolean;
}

function SearchIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="11" cy="11" r="6.5" fill="none" stroke="currentColor" strokeWidth="1.8" />
      <path d="m16 16 4.2 4.2" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

function LayersIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="m12 4 8 4-8 4-8-4 8-4Z" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" />
      <path d="m4 12 8 4 8-4M4 16l8 4 8-4" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" />
    </svg>
  );
}

function ShieldIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 3.5 19 6v5.3c0 4.2-2.7 7.6-7 9.2-4.3-1.6-7-5-7-9.2V6l7-2.5Z" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" />
      <path d="m9 12 2 2 4-4" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function LandingView({ onStartAnalysis, onOpenHistory, isLoading }: LandingViewProps) {
  const [domain, setDomain] = useState("Solid-state electrolytes for EV batteries");
  const [query, setQuery] = useState("solid electrolyte interphase");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (domain.trim()) {
      onStartAnalysis(domain.trim(), query.trim());
    }
  }

  return (
    <main className={styles.page}>
      <div className={styles.glow} aria-hidden="true" />
      <div className={styles.decorShape} aria-hidden="true" />

      <header className={styles.nav}>
        <BrandHeader />
        <div className={styles.navRight}>
          <div className={styles.productBadge}>
            <span className={styles.badgeSpark}>✦</span>
            Patent Innovation Agent
          </div>
          {onOpenHistory && (
            <button type="button" className={styles.historyLink} onClick={onOpenHistory}>
              Past analyses
            </button>
          )}
        </div>
      </header>

      <section className={styles.hero}>
        <div className={styles.copy}>
          <div className={styles.eyebrow}>
            <span>✦</span> AI-POWERED PATENT INTELLIGENCE
          </div>

          <h1 className={styles.title}>
            Find invention opportunities <span>before others do.</span>
          </h1>

          <div className={styles.titleRule} aria-hidden="true" />

          <p className={styles.subtitle}>
            Our AI agent researches prior art, discovers white-space, generates invention candidates and stress-tests them before scoring the survivors.
          </p>

          <div className={styles.features}>
            <div className={styles.feature}>
              <span className={styles.featureIcon}><SearchIcon /></span>
              <div>
                <strong>Research</strong>
                <span>Deep search across the patent landscape</span>
              </div>
            </div>
            <div className={styles.feature}>
              <span className={styles.featureIcon}><LayersIcon /></span>
              <div>
                <strong>Generate</strong>
                <span>Create novel invention candidates</span>
              </div>
            </div>
            <div className={styles.feature}>
              <span className={styles.featureIcon}><ShieldIcon /></span>
              <div>
                <strong>Attack &amp; score</strong>
                <span>Stress-test and rank the survivors</span>
              </div>
            </div>
          </div>
        </div>

        <form className={styles.formCard} onSubmit={handleSubmit}>
          <div className={styles.formIntro}>
            <div className={styles.formMark}><AbellMark size={30} /></div>
            <div>
              <h2>Start your analysis</h2>
              <p>Define your domain and research focus to begin.</p>
            </div>
          </div>

          <div className={styles.fieldGroup}>
            <label htmlFor="domainInput">Technology domain <span className={styles.info}>i</span></label>
            <div className={styles.inputWrap}>
              <span className={styles.inputIcon}><LayersIcon /></span>
              <input
                id="domainInput"
                type="text"
                className={styles.input}
                value={domain}
                onChange={(e) => setDomain(e.target.value)}
                placeholder="e.g. Solid-state electrolytes for EV batteries"
                required
              />
            </div>
          </div>

          <div className={styles.fieldGroup}>
            <label htmlFor="queryInput">
              Research query <span className={styles.optional}>(optional)</span>
              <span className={styles.info}>i</span>
            </label>
            <div className={styles.inputWrap}>
              <span className={styles.inputIcon}><SearchIcon /></span>
              <input
                id="queryInput"
                type="text"
                className={styles.input}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="e.g. solid electrolyte interphase"
              />
            </div>
          </div>

          <button type="submit" className={styles.submitBtn} disabled={isLoading}>
            <span>{isLoading ? "Starting analysis…" : "Analyze opportunity"}</span>
            {!isLoading && <span className={styles.arrow}>→</span>}
          </button>

          <div className={styles.formNote}>
            <ShieldIcon />
            Analysis typically takes 2–3 minutes
          </div>
        </form>
      </section>

      <footer className={styles.footer}>
        <span>✧ Built for focused patent research</span>
      </footer>
    </main>
  );
}
