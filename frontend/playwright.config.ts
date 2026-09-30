import { defineConfig } from "@playwright/test";

const BACKEND_PORT = 8090;
const FRONTEND_PORT = 5173; // the only dev origin the backend CORS list allows

// Real browser against a real backend with the frozen artifacts; servers are always started fresh (never reused),
// so a stale build can not answer.
export default defineConfig({
  testDir: "./test/e2e",
  use: { baseURL: `http://127.0.0.1:${FRONTEND_PORT}`, browserName: "chromium" },
  webServer: [
    {
      command: `NEXUS_MVP_ENABLED=1 uvicorn main:app --app-dir backend/src/main --port ${BACKEND_PORT}`,
      cwd: "..",
      url: `http://127.0.0.1:${BACKEND_PORT}/api/demand-examples`,
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command: `VITE_API_BASE_URL=http://127.0.0.1:${BACKEND_PORT} npm run dev -- --port ${FRONTEND_PORT} --strictPort`,
      url: `http://127.0.0.1:${FRONTEND_PORT}/matches`,
      reuseExistingServer: false,
      timeout: 60_000,
    },
  ],
});
