# moqtap/test-vectors

Language-agnostic test vectors for the [Media over QUIC Transport (MoQT)](https://datatracker.ietf.org/doc/draft-ietf-moq-transport/) protocol family. Canonical hex-encoded wire bytes paired with expected decoded representations, enabling any MoQT implementation to validate its codec against a shared, authoritative test suite.

## Quick start

```bash
git clone https://github.com/moqtap/test-vectors.git
```

Load any vector file as JSON, iterate the `vectors` array, hex-decode the `hex` field, and compare your codec's output against `decoded` (valid cases) or assert failure for `error` cases.

See [`examples/`](examples/README.md) for copy-pasteable integration snippets in Rust, Go, TypeScript, Python, and C.

## Repository layout

```
transport/
  draft00/                  MoQ Transport draft-00
  draft01/                  MoQ Transport draft-01
  draft02/                  MoQ Transport draft-02
  draft03/                  MoQ Transport draft-03
  draft04/                  MoQ Transport draft-04
  draft05/                  MoQ Transport draft-05
  draft06/                  MoQ Transport draft-06
  draft07/                  MoQ Transport draft-07
  draft08/                  MoQ Transport draft-08
  draft09/                  MoQ Transport draft-09
  draft10/                  MoQ Transport draft-10
  draft11/                  MoQ Transport draft-11
  draft12/                  MoQ Transport draft-12
  draft13/                  MoQ Transport draft-13
  draft14/                  MoQ Transport draft-14
  draft15/                  MoQ Transport draft-15
  draft16/                  MoQ Transport draft-16
  draft17/                  MoQ Transport draft-17
    codec/
      varint.json           VarInt encoding (RFC 9000 §16)
      messages/*.json       One file per control message type
      data-streams/*.json   Subgroup, datagram, fetch header vectors
    meta.json               Version metadata
schema/                     JSON Schemas for vector file validation
scripts/                    CI validation scripts
examples/                   Integration examples (not maintained libraries)
manifest.json               Machine-readable index of all specs and versions
```

Each draft directory is **fully self-contained** — no inheritance, no overlays. Adding or removing a draft affects nothing else.

## Vector file format

Every vector file is a JSON object with a `vectors` array. Each vector has a unique `id`, a human-readable `description`, and hex-encoded wire bytes:

```json
{
  "message_type": "subscribe",
  "message_type_id": "0x03",
  "spec_section": "9.7",
  "vectors": [
    {
      "id": "filter-latest-group",
      "description": "SUBSCRIBE with LatestGroup filter, no parameters",
      "hex": "0300120101046c69766505766964656f8000000100",
      "decoded": {
        "request_id": "1",
        "track_namespace": ["live"],
        "track_name": "video",
        "subscriber_priority": "128",
        "group_order": "0",
        "forward": "0",
        "filter_type": "1",
        "parameters": {}
      }
    },
    {
      "id": "truncated",
      "description": "truncated SUBSCRIBE — missing track_name",
      "hex": "0300120101046c697665",
      "error": "incomplete",
      "error_detail": "unexpected end of input while reading track_name"
    }
  ]
}
```

Valid vectors have a `decoded` object. Invalid vectors have an `error` category and optional `error_detail`. These are mutually exclusive, enforced by JSON Schema.

## Design decisions

**Integers as strings.** All protocol integer values — VarInts, fixed-width 8-bit fields, error codes, status codes — are JSON strings unconditionally. This avoids IEEE 754 precision loss for 64-bit values and eliminates type-checking ambiguity across languages. Same convention as Protocol Buffers' JSON mapping for `uint64`.

```json
{ "request_id": "1", "subscriber_priority": "128", "forward": "0" }
```

**Bidirectional by default.** Valid vectors test both `decode(hex) == decoded` and `encode(decoded) == hex`. Vectors marked `"canonical": false` are decode-only (valid but non-minimal encodings, e.g., a 2-byte VarInt encoding the value 0).

**Numeric, not symbolic.** Filter types, error codes, and status codes are numeric strings matching the spec-defined wire values. The `description` field names the constant (e.g., "SUBSCRIBE_ERROR with Unauthorized (0x1)").

**One file per message type.** Each control message gets its own file. Data streams (subgroup, datagram, fetch header) live under `data-streams/`. This makes selective consumption trivial.

**Self-contained drafts.** VarInt vectors are duplicated across drafts even though the encoding is identical — each draft directory works in isolation with no cross-references.

**Data, not code.** This repo ships JSON files. No runtime dependencies, no codec libraries. The `examples/` directory has copy-pasteable snippets showing the integration pattern, but they are not maintained libraries.

## Consuming

**Git submodule:**
```bash
git submodule add https://github.com/moqtap/test-vectors.git test-vectors
```

**npm:**
```bash
npm install --save-dev @moqtap/test-vectors
```
```typescript
import vectors from '@moqtap/test-vectors/transport/draft14/codec/messages/subscribe.json';
```

**CI fetch (GitHub Actions):**
```yaml
- uses: actions/checkout@v4
  with:
    repository: moqtap/test-vectors
    path: test-vectors
    ref: v0.1.0
```

**Programmatic discovery:** Load `manifest.json` to enumerate available specs and versions at runtime.

## Specs covered

Coverage spans drafts 00 through 17. Drafts 00–06 use an earlier wire format (single OBJECT message, flat track names, no data streams) while drafts 07+ establish the modern structure (subgroup-based data streams, tuple namespaces, subscribe IDs). All drafts are self-contained.

| Spec | Draft | Messages | Data streams | Total vectors |
|------|-------|----------|-------------|---------------|
| MoQ Transport | draft-00 | 11 control messages | — | 68 |
| MoQ Transport | draft-01 | 16 control messages | — | 77 |
| MoQ Transport | draft-02 | 14 control messages | 4 stream types | 85 |
| MoQ Transport | draft-03 | 14 control messages | 4 stream types | 84 |
| MoQ Transport | draft-04 | 17 control messages | 4 stream types | 104 |
| MoQ Transport | draft-05 | 17 control messages | 4 stream types | 100 |
| MoQ Transport | draft-06 | 22 control messages | 3 stream types | 117 |
| MoQ Transport | draft-07 | 26 control messages | 3 stream types | 130 |
| MoQ Transport | draft-08 | 27 control messages | 4 stream types | 152 |
| MoQ Transport | draft-09 | 27 control messages | 4 stream types | 154 |
| MoQ Transport | draft-10 | 27 control messages | 4 stream types | 154 |
| MoQ Transport | draft-11 | 27 control messages | 3 stream types | 158 |
| MoQ Transport | draft-12 | 30 control messages | 3 stream types | 188 |
| MoQ Transport | draft-13 | 31 control messages | 3 stream types | 212 |
| MoQ Transport | draft-14 | 31 control messages | 3 stream types | 222 |
| MoQ Transport | draft-15 | 24 control messages | 3 stream types | 170 |
| MoQ Transport | draft-16 | 25 control messages | 3 stream types | 183 |
| MoQ Transport | draft-17 | 19 control messages | 3 stream types | 185 |

## Scope

This repo tests **codec correctness** — wire encoding and decoding of individual messages. It does not test session state machines, transport-layer behavior, or media-layer concerns. Session conformance testing (state transitions, race conditions, interop flows) requires a dynamic test harness.

## License

MIT
