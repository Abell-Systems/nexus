import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, getMatches } from "../../src/main/infrastructure/operationalClient";

function respond(status: number, body: unknown) {
  vi.stubGlobal("fetch", () => Promise.resolve(new Response(JSON.stringify(body), { status })));
}

describe("operationalClient", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("shouldThrowApiErrorWithCodeAndMessageWhenServerAnswersWithErrorContract", async () => {
    respond(404, { code: "DEMAND_NOT_FOUND", message: "La demanda 'X' no existe." });
    const error = await getMatches("X").catch((e) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ code: "DEMAND_NOT_FOUND", message: "La demanda 'X' no existe." });
  });

  it("shouldThrowApiErrorWithUnknownCodeWhenErrorBodyIsNotTheContract", async () => {
    respond(502, { detail: "bad gateway" });
    const error = await getMatches("X").catch((e) => e);
    expect(error).toMatchObject({ code: "UNKNOWN_ERROR" });
  });
});
