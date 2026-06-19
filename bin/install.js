#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const os = require('os');

const SKILL_NAME = 'anything-to-okf';
const pkgRoot = path.join(__dirname, '..');
const dest = path.join(os.homedir(), '.claude', 'skills', SKILL_NAME);
const SKILL_FILES = ['SKILL.md', 'scripts', 'references', 'evals'];

function copyDir(src, dst) {
  fs.mkdirSync(dst, { recursive: true });
  for (const entry of fs.readdirSync(src, { withFileTypes: true })) {
    const s = path.join(src, entry.name);
    const d = path.join(dst, entry.name);
    if (entry.isDirectory()) copyDir(s, d);
    else fs.copyFileSync(s, d);
  }
}

fs.mkdirSync(dest, { recursive: true });
for (const file of SKILL_FILES) {
  const src = path.join(pkgRoot, file);
  if (!fs.existsSync(src)) continue;
  const dst = path.join(dest, file);
  fs.statSync(src).isDirectory() ? copyDir(src, dst) : fs.copyFileSync(src, dst);
}

console.log(`\n✅ anything-to-okf installed → ${dest}\n`);
console.log('Restart Claude Code, then type in chat:');
console.log('  /anything-to-okf generate  – convert files to OKF bundle');
console.log('  /anything-to-okf refine    – polish generated concepts');
console.log('  /anything-to-okf score     – evaluate bundle quality');
console.log('  /anything-to-okf enhance   – apply feedback to concepts');
console.log('  /anything-to-okf export    – prepare for Obsidian / git / Hugo\n');
