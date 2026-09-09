/// <reference types="vitest" />
import { defineConfig, type Plugin } from 'vite'
import react from '@vitejs/plugin-react'
import * as fs from 'node:fs'
import * as path from 'node:path'
import { fileURLToPath } from 'node:url'

// Serves and bundles a canonical repo-root artifact (project_status.json,
// scientific_results.json) as a plain static file — both are statically-published,
// git-tracked sibling artifacts (ADR 0022/0023/0025); neither is a live backend/API.
function staticContractPlugin(fileName: string): Plugin {
  const currentDir = path.dirname(fileURLToPath(import.meta.url));
  const rootContractPath = path.resolve(currentDir, '../../', fileName);

  return {
    name: `static-contract-plugin:${fileName}`,
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        if (req.url === `/${fileName}` || req.url === `./${fileName}`) {
          if (fs.existsSync(rootContractPath)) {
            res.setHeader('Content-Type', 'application/json');
            res.end(fs.readFileSync(rootContractPath, 'utf-8'));
            return;
          }
        }
        next();
      });
    },
    generateBundle() {
      if (fs.existsSync(rootContractPath)) {
        this.emitFile({
          type: 'asset',
          fileName,
          source: fs.readFileSync(rootContractPath, 'utf-8'),
        });
      }
    },
  };
}

export default defineConfig({
  base: './',
  plugins: [
    react(),
    staticContractPlugin('project_status.json'),
    staticContractPlugin('scientific_results.json'),
  ],
  build: {
    outDir: 'dist',
  },
  test: {
    globals: true,
    environment: 'jsdom',
    include: ['test/**/*.{test,spec}.{ts,tsx}'],
  },
})
