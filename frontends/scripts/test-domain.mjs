import { build } from 'esbuild';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

const dir = await mkdtemp(join(tmpdir(), 'sidequest-domain-'));
try {
  for (const [index, entry] of ['tests/domain-parity.ts', 'tests/wallet-network.ts'].entries()) {
    const output = join(dir, `checks-${index}.mjs`);
    await build({ entryPoints: [resolve(entry)], bundle: true, platform: 'node', format: 'esm', target: 'node24', outfile: output });
    await import(pathToFileURL(output).href);
  }
} finally {
  await rm(dir, { recursive: true, force: true });
}
