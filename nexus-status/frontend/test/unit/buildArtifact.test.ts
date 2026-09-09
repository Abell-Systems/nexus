import { describe, it, expect } from 'vitest';
import * as fs from 'node:fs';
import * as path from 'node:path';
import { execSync } from 'node:child_process';
import { parseProjectStatus } from '../../src/domain/status';

describe('Nexus Status Build Artifact & Pages Deployment Invariant', () => {
  const rootContractPath = path.resolve(__dirname, '../../../../project_status.json');
  const frontendDir = path.resolve(__dirname, '../../');
  const distDir = path.resolve(frontendDir, 'dist');
  const distContractPath = path.resolve(distDir, 'project_status.json');
  const distIndexPath = path.resolve(distDir, 'index.html');

  it('ensures root canonical contract exists before build', () => {
    expect(fs.existsSync(rootContractPath)).toBe(true);
  });

  it('builds static SPA and emits canonical project_status.json into dist matching root', () => {
    // Execute production build to verify Vite bundler emits canonical contract
    execSync('npm run build', {
      cwd: frontendDir,
      stdio: 'pipe',
      encoding: 'utf-8',
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
});
