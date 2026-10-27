import { sha256Hex } from "./sha256";

// Contract vertical 3 §6.1. T18 = load error, T19 = integrity error. In neither case is anything parsed.
export class LoadError extends Error {}
export class IntegrityError extends Error {}

export type HashManifest = Readonly<Record<string, string | undefined>>;

export async function loadVerifiedJson<T>(
  url: string,
  manifest: HashManifest | undefined,
  fetcher: typeof fetch = fetch,
): Promise<T> {
  let bytes: Uint8Array;
  try {
    const response = await fetcher(url, { cache: "no-store" });
    if (response.status !== 200) throw new LoadError(`HTTP ${response.status}`);
    bytes = new Uint8Array(await response.arrayBuffer());
  } catch (error) {
    throw error instanceof LoadError ? error : new LoadError("network failure");
  }
  const expected = manifest?.[url];
  if (!expected) throw new IntegrityError("no hash in the manifest");
  let actual: string;
  try {
    actual = sha256Hex(bytes);
  } catch {
    throw new IntegrityError("hash could not be computed");
  }
  if (actual !== expected) throw new IntegrityError("hash differs from the manifest");
  return JSON.parse(new TextDecoder().decode(bytes)) as T;
}
