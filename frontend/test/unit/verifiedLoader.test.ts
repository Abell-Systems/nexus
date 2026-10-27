import { createHash } from "node:crypto";
import { afterEach, describe, expect, it, vi } from "vitest";
import { sha256Hex } from "../../src/main/infrastructure/sha256";
import { IntegrityError, LoadError, loadVerifiedJson } from "../../src/main/infrastructure/verifiedLoader";

const URL_ = "/data/x.json";
const body = JSON.stringify({ pairs: ["A01B|A01C"], note: "abc" });
const bytes = new TextEncoder().encode(body);
const goodHash = sha256Hex(bytes);

const respond = (b: Uint8Array | string, status = 200) =>
  vi.fn(async () => new Response(b, { status })) as unknown as typeof fetch;

describe("sha256Hex", () => {
  it.each([
    ["", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"],
    ["abc", "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"],
    ["abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq", "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1"],
  ])("shouldMatchPublishedVectorWhenInputIs %j", (input, expected) => {
    expect(sha256Hex(new TextEncoder().encode(input))).toBe(expected);
  });

  it.each([
    [55, "9f4390f8d30c2dd92ec9f095b65e2b9ae9b0a925a5258e241c9f1e910f734318"],
    [56, "b35439a4ac6f0948b6d6f9e3c6af0f5f590ce20f1bde7090ef7970686ec6738a"],
    [64, "ffe054fe7ae0cb6dc65c3af9b61d5209f439851db43d0ba5997337df154668eb"],
    [119, "31eba51c313a5c08226adf18d4a359cfdfd8d2e816b13f4af952f7ea6584dcfb"],
    [1_000_000, "cdc76e5c9914fb9281a1c7e284d73e67f1809a48a497200e046d39ccc7112cd0"],
  ])("shouldMatchReferenceWhenInputIs%iBytesOfA", (n, expected) => {
    expect(sha256Hex(new Uint8Array(n).fill(0x61))).toBe(expected);
  });

  it("shouldMatchNodeCryptoWhenInputIsAtLeast2point5MB", () => {
    const data = Uint8Array.from({ length: 2_600_001 }, (_, i) => (i * 131 + (i >> 8)) & 255);
    expect(sha256Hex(data)).toBe(createHash("sha256").update(data).digest("hex"));
  });

  it("shouldMatchNodeCryptoWhenInputCrossesBlockBoundaries", () => {
    for (const n of [55, 56, 63, 64, 65, 119, 120, 1000, 100000]) {
      const data = Uint8Array.from({ length: n }, (_, i) => (i * 31 + 7) & 255);
      expect(sha256Hex(data)).toBe(createHash("sha256").update(data).digest("hex"));
    }
  });
});

describe("loadVerifiedJson accepted", () => {
  it("shouldReturnParsedDataWhenHashMatches", async () => {
    const fetcher = respond(bytes);
    await expect(loadVerifiedJson(URL_, { [URL_]: goodHash }, fetcher)).resolves.toEqual(JSON.parse(body));
    expect(fetcher).toHaveBeenCalledWith(URL_, { cache: "no-store" });
  });
});

describe("loadVerifiedJson rejected as integrity error, nothing parsed", () => {
  const cases: [string, Uint8Array, Record<string, string | undefined> | undefined][] = [
    ["one changed byte", new TextEncoder().encode(body.replace("abc", "abd")), { [URL_]: goodHash }],
    ["truncated body", bytes.slice(0, bytes.length - 3), { [URL_]: goodHash }],
    ["empty body", new Uint8Array(), { [URL_]: goodHash }],
    ["file absent from manifest", bytes, {}],
    ["entry without hash", bytes, { [URL_]: undefined }],
    ["manifest missing", bytes, undefined],
  ];
  afterEach(() => vi.restoreAllMocks());

  it.each(cases)("shouldRejectWhen %s", async (_n, payload, manifest) => {
    const parse = vi.spyOn(JSON, "parse");
    await expect(loadVerifiedJson(URL_, manifest, respond(payload))).rejects.toBeInstanceOf(IntegrityError);
    expect(parse).not.toHaveBeenCalled();
  });
});

describe("loadVerifiedJson rejected as load error", () => {
  it.each([206, 304, 404, 500])("shouldRejectWhenStatusIs %i", async (status) => {
    await expect(loadVerifiedJson(URL_, { [URL_]: goodHash }, respond(bytes, status))).rejects.toBeInstanceOf(LoadError);
  });

  it("shouldRejectWhenFetchFails", async () => {
    const fetcher = vi.fn(async () => { throw new TypeError("offline"); }) as unknown as typeof fetch;
    await expect(loadVerifiedJson(URL_, { [URL_]: goodHash }, fetcher)).rejects.toBeInstanceOf(LoadError);
  });

  it("shouldRejectWhenReadingBodyFails", async () => {
    const broken = { status: 200, arrayBuffer: async () => { throw new TypeError("cut"); }, json: vi.fn() };
    const fetcher = (async () => broken) as unknown as typeof fetch;
    await expect(loadVerifiedJson(URL_, { [URL_]: goodHash }, fetcher)).rejects.toBeInstanceOf(LoadError);
    expect(broken.json).not.toHaveBeenCalled();
  });
});

describe("loadVerifiedJson never uses response.json", () => {
  it("shouldReadBytesWhenJsonIsUnavailable", async () => {
    const res = { status: 200, arrayBuffer: async () => bytes.buffer.slice(0) } as unknown as Response;
    const fetcher = (async () => res) as unknown as typeof fetch;
    await expect(loadVerifiedJson(URL_, { [URL_]: goodHash }, fetcher)).resolves.toEqual(JSON.parse(body));
  });
});

describe("loadVerifiedJson without crypto.subtle", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("shouldAcceptTheCorrectFileAndRejectOneChangedByteWhenSubtleIsUndefined", async () => {
    vi.stubGlobal("crypto", { subtle: undefined });
    expect(crypto.subtle).toBeUndefined();
    await expect(loadVerifiedJson(URL_, { [URL_]: goodHash }, respond(bytes))).resolves.toEqual(JSON.parse(body));
    const changed = new TextEncoder().encode(body.replace("abc", "abd"));
    await expect(loadVerifiedJson(URL_, { [URL_]: goodHash }, respond(changed))).rejects.toBeInstanceOf(IntegrityError);
  });
});
