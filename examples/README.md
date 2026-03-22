# Integration examples

Copy-pasteable snippets showing how to load and run test vectors in different languages. These demonstrate the pattern — they are **not maintained libraries**.

Each example shows:

1. How to locate and load vector files
2. How to iterate test cases
3. How to decode hex and compare with expected values
4. How to handle canonical vs. non-canonical vectors

If examples drift slightly from the latest vector schema, the pattern is what matters. See the vector files themselves as the source of truth.

## Languages

| Language | File | Notes |
|----------|------|-------|
| Rust | `rust/tests/codec_vectors.rs` | Uses `serde_json` + `hex` crates |
| TypeScript | `typescript/codec-vectors.test.ts` | Vitest, imports via `@moqtap/test-vectors` |
| Go | `go/codec_vectors_test.go` | Standard library only |
| Python | `python/test_codec_vectors.py` | No dependencies beyond stdlib |
| C | `c/test_codec_vectors.c` | Uses cJSON for JSON parsing |
