import { describe, it, expect } from "vitest";
import type { PatentRecord, JobStatusResponse } from "../../src/main/domain/patent";

describe("Frontend Domain Types", () => {
  it("creates valid patent record object shape", () => {
    const record: PatentRecord = {
      publication_number: "ES-2849102-B2",
      title: "Detergent composition",
      abstract: "Biodegradable surfactant formulation",
      assignee: ["Laboratorios Bilper"],
      filing_date: "2020-05-12",
      country_code: "ES",
      cpc_codes: ["C11D1/00"],
      citation_count: 6,
    };
    expect(record.publication_number).toBe("ES-2849102-B2");
    expect(record.citation_count).toBe(6);
  });
});
