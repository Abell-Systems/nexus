/// <reference types="vitest" />
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    exclude: ['**/node_modules/**', 'test/e2e/**'],
    environment: 'jsdom',
    reporters: ['default', 'junit'],
    outputFile: {
      junit: 'coverage/junit.xml',
    },
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov'],
      reportsDirectory: 'coverage',
      include: ['src/main/**/*.{ts,tsx}'],
      exclude: ['src/main/main.tsx', 'src/main/**/*.d.ts'],
    },
  },
})
