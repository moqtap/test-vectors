#!/usr/bin/env node
import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import Ajv2020 from "ajv/dist/2020.js";
import addFormats from "ajv-formats";

const ajv = new Ajv2020({ allErrors: true, strict: false });
addFormats(ajv);

const readJson = (path) => JSON.parse(readFileSync(path, "utf8"));

const validateCodec = ajv.compile(readJson("schema/codec-vector.schema.json"));
const validateCatalog = ajv.compile(
  readJson("schema/catalog-vector.schema.json"),
);
const validateMeta = ajv.compile(readJson("schema/meta.schema.json"));
const validateManifest = ajv.compile(readJson("schema/manifest.schema.json"));

function walk(dir) {
  const results = [];
  if (!existsSync(dir)) return results;
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) {
      results.push(...walk(full));
    } else if (full.endsWith(".json")) {
      results.push(full);
    }
  }
  return results;
}

let failed = 0;
let passed = 0;

function check(validate, file, data) {
  const rel = relative(".", file);
  if (validate(data)) {
    passed++;
  } else {
    failed++;
    console.error(`FAIL: ${rel}`);
    for (const err of validate.errors) {
      console.error(`  ${err.instancePath} ${err.message}`);
    }
  }
}

// Validate manifest.json, then every version it lists: a spec directory the
// manifest names is a spec directory this walks, whichever spec it is.
const manifest = readJson("manifest.json");
check(validateManifest, "manifest.json", manifest);

const byCategory = { codec: validateCodec, catalog: validateCatalog };
for (const spec of Object.values(manifest.specs)) {
  for (const version of spec.versions) {
    const meta = join(version.path, "meta.json");
    check(validateMeta, meta, readJson(meta));
    for (const [category, validate] of Object.entries(byCategory)) {
      for (const file of walk(join(version.path, category))) {
        check(validate, file, readJson(file));
      }
    }
  }
}

console.log(`\nSchema validation: ${passed} passed, ${failed} failed`);
process.exit(failed > 0 ? 1 : 0);
