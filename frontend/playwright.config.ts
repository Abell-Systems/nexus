import { defineConfig } from "@playwright/test";

const PORT = 8090;

// Real browser against the real product with the frozen artifacts; always started fresh (never reused),
// so a stale build can not answer.
export default defineConfig({
  testDir: "./test/e2e",
  use: { baseURL: `http://127.0.0.1:${PORT}`, browserName: "chromium" },
  webServer: {
    // One process serves the built SPA and the API, the same shape the container runs.
    command: `npm run build && cd ../backend/src/main && python -m infrastructure.mvp_entrypoint --artifacts ../../../data/snapshots/operational_corpus_v1 --static ../../../frontend/dist --port ${PORT}`,
    url: `http://127.0.0.1:${PORT}/api/demand-examples`,
    reuseExistingServer: false,
    timeout: 180_000,
  },
});
