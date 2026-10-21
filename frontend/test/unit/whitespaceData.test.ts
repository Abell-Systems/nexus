import { createHash } from "node:crypto";
import { readdirSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import provenance from "../../src/main/infrastructure/data/provenance.json";

const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..", "..");
const data = join(root, "frontend", "src", "main", "infrastructure", "data");
const publicData = join(root, "frontend", "public", "data");
const copyOf = (entry: { file: string; served: string }) => join(entry.served === "on_demand" ? publicData : data, entry.file);

describe("the white-space data shipped with the frontend", () => {
  it("shouldCopyEveryVersionedResultByteForByteWhenTheFrontendIsBuilt", () => {
    expect(provenance.files.length).toBeGreaterThanOrEqual(5);
    for (const entry of provenance.files) {
      const original = readFileSync(join(root, entry.source));
      const copy = readFileSync(copyOf(entry));
      expect(Buffer.compare(original, copy), entry.source).toBe(0);
    }
  });

  it("shouldRecordTheSha256AndSizeOfEachCopyWhenTheFrontendIsBuilt", () => {
    for (const entry of provenance.files) {
      const copy = readFileSync(copyOf(entry));
      expect(createHash("sha256").update(copy).digest("hex"), entry.file).toBe(entry.sha256);
      expect(copy.length, entry.file).toBe(entry.bytes);
    }
  });

  it("shouldNameTheScriptAndThePullRequestThatProducedEachResult", () => {
    for (const entry of provenance.files) {
      expect(readFileSync(join(root, entry.producedBy)).length, entry.producedBy).toBeGreaterThan(0);
      expect(entry.pullRequest).toBeGreaterThan(0);
    }
  });

  it("shouldServeThePairsResultOnDemandAndNotBundleItWhenTheFrontendIsBuilt", () => {
    const entry = provenance.files.find((f) => f.file === "oepm-subclass-pairs-results.json");
    expect(entry?.served).toBe("on_demand");
    expect(readdirSync(data)).not.toContain("oepm-subclass-pairs-results.json");
  });
});
