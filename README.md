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
  draft18/                  MoQ Transport draft-18
  draft19/                  MoQ Transport draft-19
  draft20/                  MoQ Transport draft-20
    codec/
      varint.json           VarInt encoding (§1.4.1 from draft-17, RFC 9000 §16 before it)
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
  "spec_section": "10.7",
  "vectors": [
    {
      "id": "with-subgroup-filter",
      "description": "SUBSCRIBE with one SUBGROUP_FILTER: SetID 0, Subgroup ID range 2-4",
      "hex": "0300130101046c69766505766964656f012503000202",
      "decoded": {
        "request_id": "1",
        "track_namespace": ["live"],
        "track_name": "video",
        "parameters": [
          {
            "type": "0x25",
            "name": "subgroup_filter",
            "value": { "set_id": "0", "ranges": [{ "start": "2", "end": "4" }] }
          }
        ]
      }
    },
    {
      "id": "unknown-extension-param",
      "description": "SUBSCRIBE with a Message Parameter type draft-19 does not define",
      "hex": "0300140101046c69766505766964656f014104deadbeef",
      "error": "invalid_parameter",
      "error_detail": "message parameter type 0x41 is not defined by draft-19"
    }
  ]
}
```

Valid vectors have a `decoded` object. Invalid vectors have an `error` category and optional `error_detail`. These are mutually exclusive, enforced by JSON Schema.

The `error` category names the kind of complaint a decoder must make, and `profiles` names which consumers a vector's expectation binds. Both are defined in [`schema/codec-vector.schema.json`](schema/codec-vector.schema.json), which is also what the validator reads.

## Design decisions

**Integers as strings.** All protocol integer values — VarInts, fixed-width 8-bit fields, error codes, status codes — are JSON strings unconditionally. This avoids IEEE 754 precision loss for 64-bit values and eliminates type-checking ambiguity across languages. Same convention as Protocol Buffers' JSON mapping for `uint64`.

```json
{
  "request_id": "1",
  "parameters": [
    { "type": "0x20", "name": "subscriber_priority", "value": "128" },
    { "type": "0x10", "name": "forward", "value": "0" }
  ]
}
```

**Parameters are a list, not a map.** Every Key-Value-Pair block in a `decoded` message — `parameters`, `setup_parameters`, `options`, `track_properties`, `track_extensions` — is an array of entries in the order the wire carried them. Each entry has a `type` (lowercase hex), an optional `name` the draft gives that type, and exactly one of `value` (decoded) or `raw_hex` (not modelled here). A map keyed by name reads better and cannot express three things the drafts require: a parameter type that repeats, which AUTHORIZATION_TOKEN and the five Range Filters are allowed to do; the ascending order that drafts 16 and later close the session over; and a type the draft names nothing, which has no key to sit under. As a list, each of those is an ordinary entry and needs no special case.

Two blocks on the *data* plane, `extension_headers` and `object_properties`, are Key-Value lists too and keep an older shape. Nothing regenerates them, so converting them would mean editing values by hand that no consumer checks.

**Bidirectional by default.** Valid vectors test both `decode(hex) == decoded` and `encode(decoded) == hex`. Vectors marked `"canonical": false` are decode-only (valid but non-minimal encodings, e.g., a 2-byte VarInt encoding the value 0).

**Numeric, not symbolic.** Filter types, error codes, and status codes are numeric strings matching the spec-defined wire values. The `description` field names the constant (e.g., "SUBSCRIBE_ERROR with Unauthorized (0x1)").

**One file per message type.** Each control message gets its own file. Data streams (subgroup, datagram, fetch header) live under `data-streams/`. This makes selective consumption trivial.

**Self-contained drafts.** VarInt vectors are repeated in every draft directory rather than shared, so each works in isolation with no cross-references. The encoding is not the same throughout: draft-00..16 use the RFC 9000 §16 varint, and draft-17 replaced it with MoQT's own (§1.4.1), where the number of leading 1 bits in the first byte gives the length, one byte covers 0–127, and nine bytes cover the full 64-bit range. Draft-17 alone omits the 7-byte form and treats it as a protocol violation.

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

Coverage spans drafts 00 through 20. Drafts 00–06 use an earlier wire format (single OBJECT message, flat track names, no data streams) while drafts 07+ establish the modern structure (subgroup-based data streams, tuple namespaces, subscribe IDs). All drafts are self-contained.

The two type columns count files — one per control message type, one per data stream or datagram type. A **negative** vector is one carrying an `error` category instead of a `decoded` block: bytes a conforming decoder must refuse, and the column worth watching, since a corpus of only valid frames tests half a codec.

| Spec | Draft | Control messages | Data streams | Vectors | Of those, negative |
|------|-------|-----------------|--------------|---------|--------------------|
| MoQ Transport | draft-00 | 11 | — | 68 | 22 |
| MoQ Transport | draft-01 | 16 | — | 77 | 22 |
| MoQ Transport | draft-02 | 14 | 4 | 85 | 22 |
| MoQ Transport | draft-03 | 14 | 4 | 84 | 21 |
| MoQ Transport | draft-04 | 17 | 4 | 104 | 24 |
| MoQ Transport | draft-05 | 17 | 4 | 100 | 24 |
| MoQ Transport | draft-06 | 22 | 3 | 117 | 28 |
| MoQ Transport | draft-07 | 26 | 3 | 130 | 34 |
| MoQ Transport | draft-08 | 27 | 4 | 152 | 37 |
| MoQ Transport | draft-09 | 27 | 4 | 154 | 38 |
| MoQ Transport | draft-10 | 27 | 4 | 154 | 38 |
| MoQ Transport | draft-11 | 27 | 3 | 159 | 35 |
| MoQ Transport | draft-12 | 30 | 3 | 190 | 38 |
| MoQ Transport | draft-13 | 31 | 3 | 213 | 39 |
| MoQ Transport | draft-14 | 31 | 3 | 228 | 39 |
| MoQ Transport | draft-15 | 24 | 3 | 177 | 30 |
| MoQ Transport | draft-16 | 25 | 3 | 189 | 32 |
| MoQ Transport | draft-17 | 19 | 3 | 219 | 41 |
| MoQ Transport | draft-18 | 20 | 3 | 248 | 39 |
| MoQ Transport | draft-19 | 20 | 3 | 268 | 39 |
| MoQ Transport | draft-20 | 21 | 3 | 324 | 57 |
| | **all** | | | **3440** | **699** |

## Scope

This repo tests **codec correctness** — wire encoding and decoding of individual messages. It does not test session state machines, transport-layer behavior, or media-layer concerns. Session conformance testing (state transitions, race conditions, interop flows) requires a dynamic test harness.

## License

MIT
