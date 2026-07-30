import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import vm from 'node:vm';

const sourcePath = 'saulteaux-cree-parity-source.html';
const standalonePaths = ['index.html', 'saulteaux-game-shell.html'];
const rosterPath = 'saulteaux-300-word-roster.csv';
const expectedAssets = [
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

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function sha256(bytes) {
  return createHash('sha256').update(bytes).digest('hex');
}

function scriptFrom(html, path) {
  const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)];
  assert(scripts.length === 1, `${path}: expected one inline game script`);
  return scripts[0][1];
}

function parseCsv(text) {
  const lines = String(text).trim().split(/\r?\n/);
  function line(lineText) {
    const output = [];
    let value = '';
    let quoted = false;
    for (let index = 0; index < lineText.length; index += 1) {
      const character = lineText[index];
      if (character === '"' && lineText[index + 1] === '"') {
        value += '"';
        index += 1;
      } else if (character === '"') {
        quoted = !quoted;
      } else if (character === ',' && !quoted) {
        output.push(value);
        value = '';
      } else {
        value += character;
      }
    }
    output.push(value);
    return output;
  }
  const headers = line(lines[0]);
  return lines.slice(1).filter(Boolean).map((lineText) => {
    const values = line(lineText);
    return Object.fromEntries(headers.map((header, index) => [header, values[index] || '']));
  });
}

function declaration(script, name) {
  const match = script.match(new RegExp(`var ${name} = [\\s\\S]*?;\\n`));
  assert(match, `Missing ${name} declaration`);
  return match[0];
}

function functionText(script, name) {
  const marker = `function ${name}(`;
  const start = script.indexOf(marker);
  assert(start >= 0, `Missing ${name} function`);
  const firstBrace = script.indexOf('{', start);
  let depth = 0;
  let quote = '';
  let escaped = false;
  for (let index = firstBrace; index < script.length; index += 1) {
    const character = script[index];
    if (quote) {
      if (escaped) escaped = false;
      else if (character === '\\') escaped = true;
      else if (character === quote) quote = '';
      continue;
    }
    if (character === '"' || character === "'" || character === '`') {
      quote = character;
      continue;
    }
    if (character === '{') depth += 1;
    if (character === '}') {
      depth -= 1;
      if (depth === 0) return script.slice(start, index + 1);
    }
  }
  throw new Error(`Unclosed ${name} function`);
}

const [source, rosterText, ...standalones] = await Promise.all([
  readFile(sourcePath, 'utf8'),
  readFile(rosterPath, 'utf8'),
  ...standalonePaths.map((path) => readFile(path, 'utf8'))
]);

const sourceScript = scriptFrom(source, sourcePath);
new Function(sourceScript);
assert(!source.includes('text-shadow'), 'Text shadows must remain absent');
assert(source.includes('user-select:none') && source.includes('-webkit-touch-callout:none'), 'Touch controls must be non-selectable');
assert(source.includes('var HELP_DELAY = 7000;'), 'Eagle help delay must be 7 seconds');
for (const required of ['function beginQuiz(', 'function finishArena(', "bindPress('start-button'", "bindPress('select-button'", "bindPress('button-a'", "bindPress('button-b'"]) {
  assert(source.includes(required), `Missing parity feature: ${required}`);
}

const roster = parseCsv(rosterText);
assert(roster.length === 300, `Roster contains ${roster.length}, expected 300`);
assert(roster.every((row) => row.saulteau_source_form.trim()), 'Every roster row must have a Saulteaux form');
assert(new Set(roster.map((row) => row.saulteau_source_form)).size === 300, 'Saulteaux roster forms must be unique');

const isolatedCampaignCode = [
  declaration(sourceScript, 'ROUND_SIZE'),
  declaration(sourceScript, 'WORLD_ARENA_COUNTS'),
  declaration(sourceScript, 'WORLD_TITLES'),
  declaration(sourceScript, 'WORLD_SUBTITLES'),
  declaration(sourceScript, 'ARENA_NAMES'),
  'var campaign = []; var worlds = [];',
  functionText(sourceScript, 'normalize'),
  functionText(sourceScript, 'fallbackRoster'),
  functionText(sourceScript, 'categoryFor'),
  functionText(sourceScript, 'scoreForWorld'),
  functionText(sourceScript, 'buildCampaign'),
  'buildCampaign(inputRows); result = {campaign: campaign, worlds: worlds};'
].join('\n');
const sandbox = { inputRows: roster, result: null };
vm.runInNewContext(isolatedCampaignCode, sandbox);
const { campaign, worlds } = sandbox.result;
assert(campaign.length === 50, `Campaign contains ${campaign.length}, expected 50 arenas`);
assert(worlds.length === 7, `Campaign contains ${worlds.length}, expected 7 worlds`);
assert(campaign.every((arena) => arena.entries.length === 6), 'Every arena must contain exactly 6 entries');
const assignedIds = campaign.flatMap((arena) => arena.entries.map((entry) => entry._id));
assert(assignedIds.length === 300 && new Set(assignedIds).size === 300, 'All 300 roster entries must be assigned exactly once');
assert(JSON.stringify(worlds.map((world) => world.arenas.length)) === JSON.stringify([5, 4, 7, 6, 5, 12, 11]), 'World arena allocation changed');

for (let standaloneIndex = 0; standaloneIndex < standalones.length; standaloneIndex += 1) {
  const path = standalonePaths[standaloneIndex];
  const html = standalones[standaloneIndex];
  new Function(scriptFrom(html, path));
  const assetStart = html.indexOf('      var INLINE_ASSETS = ') + '      var INLINE_ASSETS = '.length;
  const assetEnd = html.indexOf(';\n      var INLINE_ROSTER = ', assetStart);
  assert(assetStart >= 0 && assetEnd > assetStart, `${path}: missing embedded assets`);
  const embeddedAssets = JSON.parse(html.slice(assetStart, assetEnd));
  assert(Object.keys(embeddedAssets).length === expectedAssets.length, `${path}: embedded asset count changed`);
  for (const assetPath of expectedAssets) {
    const dataUrl = embeddedAssets[assetPath];
    assert(dataUrl?.startsWith('data:image/png;base64,'), `${path}: missing ${assetPath}`);
    const embeddedBytes = Buffer.from(dataUrl.split(',')[1], 'base64');
    const originalBytes = await readFile(assetPath);
    assert(sha256(embeddedBytes) === sha256(originalBytes), `${path}: ${assetPath} does not match its source`);
  }
  const rosterStart = assetEnd + ';\n      var INLINE_ROSTER = '.length;
  const rosterEnd = html.indexOf(';\n      var SAVE_KEY = ', rosterStart);
  assert(rosterEnd > rosterStart, `${path}: missing embedded roster`);
  assert(JSON.parse(html.slice(rosterStart, rosterEnd)) === rosterText, `${path}: embedded roster does not match the CSV`);
}

console.log('PASS: 7 worlds, 50 arenas, 300 unique entries, 6 entries per arena.');
console.log('PASS: find/quiz progression, 7-second eagle help, save/journal, and GBA controls are present.');
console.log('PASS: both standalone entries contain all 16 verified art assets and the full roster.');
