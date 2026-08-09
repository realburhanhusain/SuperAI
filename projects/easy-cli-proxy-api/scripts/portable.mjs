import { createHash } from 'node:crypto';
import { existsSync } from 'node:fs';
import { chmod, copyFile, mkdir, readFile, readdir, rm, writeFile } from 'node:fs/promises';
import { basename, dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { readAppVersion } from './version.mjs';

const args = new Map();
for (let index = 2; index < process.argv.length; index += 2) {
  args.set(process.argv[index], process.argv[index + 1]);
}

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const output = resolve(args.get('--output') ?? join(root, 'bin-work'));
const binary = resolve(args.get('--binary') ?? join(root, 'src-tauri', 'target', 'release', process.platform === 'win32' ? 'cpa-gui.exe' : 'cpa-gui'));
const targetOS = args.get('--os') ?? ({ linux: 'linux', darwin: 'darwin', win32: 'windows' })[process.platform];
const targetArch = args.get('--arch') ?? ({ x64: 'amd64', arm64: 'aarch64' })[process.arch];
const shouldDownload = args.get('--download') === 'true';
const preserveRuntimeConfig = args.get('--preserve-runtime-config') === 'true';

if (!targetOS || !targetArch) throw new Error(`Unsupported target: ${process.platform}/${process.arch}`);
if (!existsSync(binary)) throw new Error(`GUI binary not found: ${binary}`);

const rawVersion = (await readFile(join(root, 'core-version.txt'), 'utf8')).trim();
if (!/^v?\d+(?:\.\d+)+$/.test(rawVersion)) throw new Error(`Invalid core-version.txt: ${rawVersion}`);
const version = rawVersion.replace(/^v/i, '');
const appVersion = await readAppVersion();
const extension = targetOS === 'windows' ? 'zip' : 'tar.gz';
const assetName = `CLIProxyAPI_${version}_${targetOS}_${targetArch}.${extension}`;
const sourceDir = join(root, 'cpa-core');
const sourceArchive = join(sourceDir, assetName);
const checksumsPath = join(sourceDir, 'checksums.txt');

await mkdir(sourceDir, { recursive: true });
if (!existsSync(sourceArchive)) {
  if (!shouldDownload) {
    throw new Error(`Built-in core archive not found: ${sourceArchive}`);
  }
  const tag = `v${version}`;
  const releaseBase = `https://github.com/router-for-me/CLIProxyAPI/releases/download/${tag}`;
  const [archiveResponse, checksumsResponse] = await Promise.all([
    fetch(`${releaseBase}/${assetName}`),
    fetch(`${releaseBase}/checksums.txt`),
  ]);
  if (!archiveResponse.ok) throw new Error(`Download ${assetName} failed: HTTP ${archiveResponse.status}`);
  if (!checksumsResponse.ok) throw new Error(`Download checksums.txt failed: HTTP ${checksumsResponse.status}`);
  await writeFile(sourceArchive, Buffer.from(await archiveResponse.arrayBuffer()));
  await writeFile(checksumsPath, await checksumsResponse.text());
}

if (existsSync(checksumsPath)) {
  const checksums = await readFile(checksumsPath, 'utf8');
  const expected = checksums.split(/\r?\n/).map((line) => line.trim().split(/\s+/)).find((parts) => parts[1]?.replace(/^\*/, '') === assetName)?.[0]?.toLowerCase();
  if (!expected) throw new Error(`checksums.txt does not contain ${assetName}`);
  const actual = createHash('sha256').update(await readFile(sourceArchive)).digest('hex');
  if (actual !== expected) throw new Error(`SHA-256 mismatch for ${assetName}`);
}

await mkdir(output, { recursive: true });
const outputBinary = join(output, targetOS === 'windows' ? 'EasyCLIProxyAPI.exe' : 'EasyCLIProxyAPI');
const legacyOutputBinary = join(output, targetOS === 'windows' ? 'cpa-gui.exe' : 'cpa-gui');
await rm(legacyOutputBinary, { force: true });
await copyFile(binary, outputBinary);
if (targetOS !== 'windows') await chmod(outputBinary, 0o755);
await copyFile(join(root, 'core-version.txt'), join(output, 'core-version.txt'));
await writeFile(join(output, 'portable-app.json'), `${JSON.stringify({
  schemaVersion: 1,
  application: 'EasyCLIProxyAPI',
  version: appVersion,
  platform: targetOS,
  arch: targetArch,
  autoUpdate: targetOS === 'windows',
}, null, 2)}\n`);

const coreOutput = join(output, 'cpa-core');
if (preserveRuntimeConfig) {
  await mkdir(coreOutput, { recursive: true });
  const entries = await readdir(coreOutput, { withFileTypes: true });
  await Promise.all(entries
    .filter((entry) => entry.name !== 'config.yaml')
    .map((entry) => rm(join(coreOutput, entry.name), { recursive: true, force: true })));
} else {
  await rm(coreOutput, { recursive: true, force: true });
}
await mkdir(coreOutput, { recursive: true });
await copyFile(sourceArchive, join(coreOutput, assetName));
const coreEntries = await readdir(coreOutput, { withFileTypes: true });
const bundledArchive = coreEntries.find((entry) => entry.isFile() && entry.name === assetName);
if (!bundledArchive) {
  throw new Error(`Core output must contain ${assetName}`);
}
if (!preserveRuntimeConfig && coreEntries.length !== 1) {
  throw new Error(`Core output must contain only ${assetName}`);
}

console.log(`Prepared portable directory: ${output}`);
console.log(`Bundled core: ${basename(sourceArchive)}${preserveRuntimeConfig ? ' (preserved cpa-core/config.yaml)' : ' (archive only)'}`);
