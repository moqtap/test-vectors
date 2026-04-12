#!/usr/bin/env node
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import Ajv2020 from "ajv/dist/2020.js";
import addFormats from "ajv-formats";

const ajv = new Ajv2020({ allErrors: true, strict: false });
addFormats(ajv);

const codecSchema = JSON.parse(
  readFileSync("schema/codec-vector.schema.json", "utf8"),
);
const metaSchema = JSON.parse(
  readFileSync("schema/meta.schema.json", "utf8"),
);
const manifestSchema = JSON.parse(
  readFileSync("schema/manifest.schema.json", "utf8"),
);

const validateCodec = ajv.compile(codecSchema);
const validateMeta = ajv.compile(metaSchema);
const validateManifest = ajv.compile(manifestSchema);

function walk(dir, pattern) {
  const results = [];
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) {
      results.push(...walk(full, pattern));
    } else if (full.endsWith(".json") && pattern(full)) {
      results.push(full);
    }
  }
  return results;
}

let failed = 0;
let passed = 0;

// Validate codec vectors
const codecFiles = walk("transport", (f) => f.includes("codec"));
for (const file of codecFiles) {
  const data = JSON.parse(readFileSync(file, "utf8"));
  const valid = validateCodec(data);
  const rel = relative(".", file);
  if (valid) {
    passed++;
  } else {
    failed++;
    console.error(`FAIL: ${rel}`);
    for (const err of validateCodec.errors) {
      console.error(`  ${err.instancePath} ${err.message}`);
    }
  }
}

// Validate meta.json files
const metaFiles = walk("transport", (f) => f.endsWith("meta.json"));
for (const file of metaFiles) {
  const data = JSON.parse(readFileSync(file, "utf8"));
  const valid = validateMeta(data);
  const rel = relative(".", file);
  if (valid) {
    passed++;
  } else {
    failed++;
    console.error(`FAIL: ${rel}`);
    for (const err of validateMeta.errors) {
      console.error(`  ${err.instancePath} ${err.message}`);
    }
  }
}

// Validate manifest.json
const manifestData = JSON.parse(readFileSync("manifest.json", "utf8"));
if (validateManifest(manifestData)) {
  passed++;
} else {
  failed++;
  console.error("FAIL: manifest.json");
  for (const err of validateManifest.errors) {
    console.error(`  ${err.instancePath} ${err.message}`);
  }
}

console.log(`\nSchema validation: ${passed} passed, ${failed} failed`);
process.exit(failed > 0 ? 1 : 0);
