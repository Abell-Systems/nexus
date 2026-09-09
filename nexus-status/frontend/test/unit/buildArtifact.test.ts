import { describe, it, expect, afterAll } from 'vitest';
import * as fs from 'node:fs';
import * as path from 'node:path';
import { build } from 'vite';
import { parseProjectStatus } from '../../src/domain/status';
import { parseScientificResults } from '../../src/domain/scientificResults';

describe('Nexus Status Build Artifact & Pages Deployment Invariant', () => {
  const rootContractPath = path.resolve(__dirname, '../../../../project_status.json');
  const rootScientificResultsPath = path.resolve(__dirname, '../../../../scientific_results.json');
  const frontendDir = path.resolve(__dirname, '../../');
  const distDir = path.resolve(frontendDir, 'dist');
  const distContractPath = path.resolve(distDir, 'project_status.json');
  const distScientificResultsPath = path.resolve(distDir, 'scientific_results.json');
  const distIndexPath = path.resolve(distDir, 'index.html');

  afterAll(() => {
    // Clean up dist directory after test execution to prevent working tree side-effects
    if (fs.existsSync(distDir)) {
      fs.rmSync(distDir, { recursive: true, force: true });
    }
  });

  it('ensures root canonical contracts exist before build', () => {
    expect(fs.existsSync(rootContractPath)).toBe(true);
    expect(fs.existsSync(rootScientificResultsPath)).toBe(true);
  });

  it('builds static SPA and emits canonical project_status.json into dist matching root', async () => {
    // Programmatic build using Vite API with exact project configuration
    await build({
      root: frontendDir,
      configFile: path.resolve(frontendDir, 'vite.config.ts'),
      logLevel: 'silent',
    });

    // 1. Verify dist/index.html exists
    expect(fs.existsSync(distIndexPath)).toBe(true);
    const indexContent = fs.readFileSync(distIndexPath, 'utf-8');
    expect(indexContent).toContain('<div id="root"></div>');

    // 2. Verify dist/project_status.json exists
    expect(fs.existsSync(distContractPath)).toBe(true);

    // 3. Verify content matches root project_status.json exactly
    const rootRaw = fs.readFileSync(rootContractPath, 'utf-8');
    const distRaw = fs.readFileSync(distContractPath, 'utf-8');
    expect(JSON.parse(distRaw)).toEqual(JSON.parse(rootRaw));

    // 4. Verify dist contract validates successfully against domain model
    const parsedDist = parseProjectStatus(JSON.parse(distRaw));
    expect(parsedDist.schema_version).toBe('1.0.0');
    expect(parsedDist.overall_status).toBeDefined();
    expect(Object.keys(parsedDist.dimensions).length).toBeGreaterThanOrEqual(7);
  });

  it('builds static SPA and emits canonical scientific_results.json into dist matching root', async () => {
    await build({
      root: frontendDir,
      configFile: path.resolve(frontendDir, 'vite.config.ts'),
      logLevel: 'silent',
    });

    // 1. Verify dist/scientific_results.json exists as its own sibling artifact
    expect(fs.existsSync(distScientificResultsPath)).toBe(true);
    expect(distScientificResultsPath).not.toBe(distContractPath);

    // 2. Verify content matches root scientific_results.json exactly
    const rootRaw = fs.readFileSync(rootScientificResultsPath, 'utf-8');
    const distRaw = fs.readFileSync(distScientificResultsPath, 'utf-8');
    expect(JSON.parse(distRaw)).toEqual(JSON.parse(rootRaw));

    // 3. Verify dist contract validates successfully against the read model
    const parsedDist = parseScientificResults(JSON.parse(distRaw));
    expect(parsedDist.executions.length).toBeGreaterThan(0);
    expect(parsedDist.executions[0].track).toBe('discovery');
  });
});
