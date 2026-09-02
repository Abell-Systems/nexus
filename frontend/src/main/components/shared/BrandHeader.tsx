import styles from "./BrandHeader.module.css";

interface BrandHeaderProps {
  domain?: string | null;
}

// A simplified, icon-scale take on the Abell Systems mark (docs/abell-systems.jpeg):
// a triangular ring in the brand's violet-to-pink gradient, standing in for the
// full Penrose-triangle/orbit artwork which doesn't read at header/favicon size.
export function AbellMark({ size = 34 }: { size?: number }) {
  return (
    <svg
      className={styles.logoMark}
      style={{ width: size, height: size }}
      viewBox="0 0 48 48"
      aria-hidden="true"
    >
      <defs>
        <linearGradient id="abell-gradient" x1="6" y1="10" x2="42" y2="38">
          <stop offset="0%" stopColor="#7c3fc4" />
          <stop offset="55%" stopColor="#b23a9a" />
          <stop offset="100%" stopColor="#e0217a" />
        </linearGradient>
      </defs>
      <path
        fillRule="evenodd"
        clipRule="evenodd"
        d="M24 5 44 42 4 42Z M24 17 35 34 13 34Z"
        fill="url(#abell-gradient)"
      />
    </svg>
  );
}

export function BrandHeader({ domain }: BrandHeaderProps) {
  return (
    <div className={styles.row}>
      <div className={styles.brand}>
        <AbellMark />
        <span className={styles.brandName}>
          ABELL <strong>SYSTEMS</strong>
        </span>
      </div>
      {domain && <div className={styles.domainBadge}>{domain}</div>}
    </div>
  );
}
