import { readFile, writeFile } from 'node:fs/promises';
import { extname } from 'node:path';

const sourcePath = 'saulteaux-cree-parity-source.html';
const rosterPath = 'saulteaux-300-word-roster.csv';
const outputPaths = ['index.html', 'saulteaux-game-shell.html'];
const assetPaths = [
  'saulteaux-preview/assets/master/turtle-island-gba-style.png',
  'saulteaux-preview/assets/characters/makwa-walk-sheet-gba.png',
  'saulteaux-preview/assets/characters/eagle-flying-sheet-gba.png',
  'saulteaux-preview/assets/characters/eagle-prompt-sheet-gba.png',
  'saulteaux-preview/assets/objects/object-atlas-01-gba.png',
  'saulteaux-preview/assets/objects/object-atlas-02-gba.png',
  'saulteaux-preview/assets/objects/object-atlas-03-gba.png',
  'saulteaux-preview/assets/objects/object-atlas-04-gba.png',
  'saulteaux-preview/assets/water/frames/frame-00.png',
  'saulteaux-preview/assets/water/frames/frame-01.png',
  'saulteaux-preview/assets/water/frames/frame-02.png',
  'saulteaux-preview/assets/water/frames/frame-03.png',
  'saulteaux-preview/assets/water/frames/frame-04.png',
  'saulteaux-preview/assets/water/frames/frame-05.png',
  'saulteaux-preview/assets/water/frames/frame-06.png',
  'saulteaux-preview/assets/water/frames/frame-07.png'
];

function mimeType(path) {
  const extension = extname(path).toLowerCase();
  if (extension === '.png') return 'image/png';
  throw new Error(`Unsupported asset type: ${path}`);
}

const [source, roster] = await Promise.all([
  readFile(sourcePath, 'utf8'),
  readFile(rosterPath, 'utf8')
]);

const pairs = await Promise.all(assetPaths.map(async (path) => {
  const bytes = await readFile(path);
  return [path, `data:${mimeType(path)};base64,${bytes.toString('base64')}`];
}));

const inlineAssets = Object.fromEntries(pairs);
const assetMarker = "      var INLINE_ASSETS = {};";
const rosterMarker = "      var INLINE_ROSTER = '';";

if (!source.includes(assetMarker) || !source.includes(rosterMarker)) {
  throw new Error('Build markers are missing from the source HTML.');
}

const standalone = source
  .replace(assetMarker, `      var INLINE_ASSETS = ${JSON.stringify(inlineAssets)};`)
  .replace(rosterMarker, `      var INLINE_ROSTER = ${JSON.stringify(roster)};`);

for (const outputPath of outputPaths) {
  await writeFile(outputPath, standalone);
}

console.log(`Built ${outputPaths.join(' and ')} with ${assetPaths.length} embedded art assets and the 300-entry roster.`);
