/// <reference types="vitest" />
import { defineConfig, type Plugin } from 'vite'
import react from '@vitejs/plugin-react'
import * as fs from 'node:fs'
import * as path from 'node:path'
import { fileURLToPath } from 'node:url'

function canonicalContractPlugin(): Plugin {
  const currentDir = path.dirname(fileURLToPath(import.meta.url));
  const rootContractPath = path.resolve(currentDir, '../../project_status.json');

  return {
    name: 'canonical-contract-plugin',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        if (req.url === '/project_status.json' || req.url === './project_status.json') {
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
          fileName: 'project_status.json',
          source: fs.readFileSync(rootContractPath, 'utf-8'),
        });
      }
    },
  };
}

export default defineConfig({
  base: './',
  plugins: [react(), canonicalContractPlugin()],
  build: {
    outDir: 'dist',
  },
  test: {
    globals: true,
    environment: 'jsdom',
    include: ['test/**/*.{test,spec}.{ts,tsx}'],
  },
})


