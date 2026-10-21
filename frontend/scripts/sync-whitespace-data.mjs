// Copies the versioned results of the white-space study into the frontend as static data, and writes the manifest
// the traceability panel shows. The browser recomputes nothing: it draws what these files state.
//
//   npm run sync-data
import { createHash } from "node:crypto";
import { copyFileSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { basename, dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const target = join(root, "frontend", "src", "main", "infrastructure", "data");

export const SOURCES = [
  { source: "docs/whitespace/oepm-corpus-exposure-results.json", producedBy: "scripts/report_oepm_corpus_exposure.py", pullRequest: 140 },
  { source: "docs/whitespace/oepm-omission-sensitivity-results.json", producedBy: "scripts/report_oepm_omission_sensitivity.py", pullRequest: 141 },
  { source: "docs/whitespace/oepm-section-density-results.json", producedBy: "scripts/report_oepm_section_density.py", pullRequest: 142 },
  { source: "config/whitespace/oepm_biblio_2000_2025.json", producedBy: "scripts/reproduce_oepm_biblio_characterization.py", pullRequest: 130 },
];

mkdirSync(target, { recursive: true });
const files = SOURCES.map((entry) => {
  const name = basename(entry.source);
  copyFileSync(join(root, entry.source), join(target, name));
  const bytes = readFileSync(join(target, name));
  return { file: name, ...entry, bytes: bytes.length, sha256: createHash("sha256").update(bytes).digest("hex") };
});
writeFileSync(join(target, "provenance.json"), JSON.stringify({ files }, null, 2) + "\n");
console.log(`copied ${files.length} result files and wrote provenance.json`);
