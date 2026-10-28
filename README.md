# moqtap/test-vectors

Language-agnostic test vectors for the [Media over QUIC Transport (MoQT)](https://datatracker.ietf.org/doc/draft-ietf-moq-transport/) protocol family. Canonical hex-encoded wire bytes paired with expected decoded representations, enabling any MoQT implementation to validate its codec against a shared, authoritative test suite.

Beside the transport codec vectors sit catalog vectors for the [MOQT Streaming Format (MSF)](https://datatracker.ietf.org/doc/draft-ietf-moq-msf/) and its CMAF extension [CMSF](https://datatracker.ietf.org/doc/draft-ietf-moq-cmsf/): the exact text of catalog objects, independent and delta, paired with the catalog they resolve to or the complaint they must draw.

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
  draft21/                  MoQ Transport draft-21
  draft22/                  MoQ Transport draft-22
    codec/
      varint.json           VarInt encoding (§8.1 in drafts 21–22, §1.4.1 in drafts 17–20, RFC 9000 §16 before)
      messages/*.json       One file per control message type
      data-streams/*.json   Subgroup, datagram, fetch header vectors
    meta.json               Version metadata
msf/
  draft00/                  MOQT Streaming Format draft-00
  draft01/                  MOQT Streaming Format draft-01
    catalog/
      independent.json      Independent catalogs, the draft's own examples among them
      delta.json            Delta updates: every operation, and what it may not do
      update.json           Independent catalogs that follow one another
      invalid.json          Catalogs a validator or a reader must refuse
      init-data.json        initDataList and initRef (draft-01)
    meta.json
cmsf/
  draft00/                  CMAF MOQT Streaming Format draft-00
  draft01/                  CMAF MOQT Streaming Format draft-01 (extends MSF draft-01)
    catalog/
      cmaf.json             packaging cmaf, SAP starting types, the SAP Type timeline track
      init-data.json        initData (draft-00); initDataList and initRef (draft-01)
      content-protection.json  contentProtections and contentProtectionRefIDs (draft-01)
    meta.json
schema/                     JSON Schemas for vector file validation
scripts/                    CI validation scripts
examples/                   Integration examples (not maintained libraries)
manifest.json               Machine-readable index of all specs and versions
```

Each draft directory is **fully self-contained** — no inheritance, no overlays. Adding or removing a draft affects nothing else. A version that extends another says so in its `meta.json` (`requires`), and its vectors still repeat everything they need.

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

### Catalog vectors

A catalog vector holds the exact payload of a catalog object — `{"text": ...}`, or `{"hex": ...}` when the bytes matter — never a parsed object, since member order is asserted (MSF-01 5.1.7). Later objects on the same track follow in `steps`: a delta applies to what came before it, an independent catalog replaces it. Then exactly one of `resolved`, the catalog after the last object as a plain JSON document, or `error` with an optional `error_detail` and, when there are steps, `error_at` naming the object that fails (0 is `input`).

```json
{
  "id": "clone-with-parent-namespace",
  "description": "A clone naming its parent's namespace ...",
  "input": { "text": "{\"version\": \"draft-01\", \"tracks\": [...]}" },
  "steps": [
    { "text": "{\"generatedAt\": 1746104606044, \"deltaUpdate\": [{\"op\": \"clone\", ...}]}" }
  ],
  "resolved": { "version": "draft-01", "generatedAt": 1746104606044, "tracks": [ ... ] }
}
```

`resolved` is stated at the level of the draft: the document an independent catalog would hold now, with unknown fields kept, a clone holding its parent's attributes and its own overrides, and nothing filled in that the payload does not say. Tracks compare as a set keyed by namespace and name.

`profiles` is `validator` — bound by every rule the draft states, including those it states only for a catalog's producer — or `reader`, a subscriber bound by the rules for a parser and by what it needs to resolve the document; omitted means both. Where a draft is silent and a vector records what a tolerant reader must do to keep going, it carries `"tolerant": true`, binds `reader` alone, and says so in its description. Every other expectation cites the sentence of the draft that decides it. The categories and both profiles are defined in [`schema/catalog-vector.schema.json`](schema/catalog-vector.schema.json).

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

**Parameters are a list, not a map.** Every Key-Value-Pair block in a `decoded` message — `parameters`, `setup_parameters`, `options`, `track_properties`, `track_extensions`, and on the data plane `extension_headers` and `object_properties` — is an array of entries in the order the wire carried them. Each entry has a `type` (lowercase hex), an optional `name` the draft gives that type, and exactly one of `value` (decoded) or `raw_hex` (not modelled here). A map keyed by name reads better and cannot express three things the drafts require: a parameter type that repeats, which AUTHORIZATION_TOKEN and the five Range Filters are allowed to do; the ascending order that drafts 16 and later close the session over; and a type the draft names nothing, which has no key to sit under. As a list, each of those is an ordinary entry and needs no special case.

On the data plane an odd-typed property's bytes are `raw_hex`, and Immutable Properties (0xB) carry their contents as a nested list in `value`.

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
import deltas from '@moqtap/test-vectors/msf/draft01/catalog/delta.json';
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

Coverage spans drafts 00 through 22. Drafts 00–06 use an earlier wire format (single OBJECT message, flat track names, no data streams) while drafts 07+ establish the modern structure (subgroup-based data streams, tuple namespaces, subscribe IDs). All drafts are self-contained.

Draft-21 restructured draft-20 and changed nothing else: every code point, every table row and every wire diagram is identical, so its vectors carry byte-for-byte the same `hex` and `decoded` as draft-20's. What moved is where the draft says things — 200 numbered sections became 214, and only 11 keep both their title and their number — so the two directories differ in the sections their prose cites and in nothing a decoder can observe. A codec that passes draft-20 passes draft-21, and a consumer can use that: running both is a check on the consumer's own draft plumbing, since any disagreement between them is its bug rather than the protocol's.

Draft-22 is not wire-identical to draft-21. It changes one thing on the wire: LOCATION_FILTER (0x21) now begins with a Location Filter Type where draft-21 had a byte Length. The type alone says which fields follow (0x00 none, 0x01 relative start, 0x02 absolute start, 0x03 absolute start to the end of a group, 0x04 absolute range, 0x05 Next Object), and any other type is a protocol violation. Every other vector carries draft-21's `hex` and `decoded` unchanged, and every LOCATION_FILTER value gains a `filter_type`. One meaning moves with it: `21 02 00 00` is now the absolute start {0,0}, not the Next Object, which is `21 05`. With fields below 128 a type equals the old Length byte for byte, so the vectors that tell a draft-22 decoder from a draft-21 one are those with a type 0x05, a multi-byte or non-minimal field, or a type 0x06 and above.

MSF and CMSF carry catalogs only. MSF-00 writes `version` as a Number and a delta as `deltaUpdate: true` with `addTracks`, `removeTracks` and `cloneTracks`; MSF-01 writes `version` as a String and `deltaUpdate` as an ordered array of `{op, tracks}`. CMSF-00 puts each CMAF header in the track's `initData`; CMSF-01 moves it to a root `initDataList` that tracks point into with `initRef`, and adds `contentProtections`. CMSF-00 extends the WARP Streaming Format draft that preceded MSF, which is not included; its vectors cover only what CMSF-00 itself defines. Where a draft contradicts itself — `mimeType` in its field table and `mimetype` in its examples; `"draft-XX"` as the version convention and `"1"` in every example; examples whose Base64 is elided with `...` — the vector's description says so.

The two type columns count files — one per control message type, one per data stream or datagram type; a catalog spec has neither, and its row counts catalog vectors. A **negative** vector is one carrying an `error` category instead of a `decoded` block: input a conforming consumer must refuse.

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
| MoQ Transport | draft-15 | 24 | 3 | 186 | 30 |
| MoQ Transport | draft-16 | 25 | 3 | 189 | 32 |
| MoQ Transport | draft-17 | 19 | 3 | 224 | 42 |
| MoQ Transport | draft-18 | 20 | 3 | 253 | 40 |
| MoQ Transport | draft-19 | 20 | 3 | 273 | 40 |
| MoQ Transport | draft-20 | 21 | 3 | 337 | 63 |
| MoQ Transport | draft-21 | 21 | 3 | 337 | 63 |
| MoQ Transport | draft-22 | 21 | 3 | 347 | 65 |
| MOQT Streaming Format | draft-00 | — | — | 47 | 27 |
| MOQT Streaming Format | draft-01 | — | — | 66 | 36 |
| CMAF MOQT Streaming Format | draft-00 | — | — | 12 | 7 |
| CMAF MOQT Streaming Format | draft-01 | — | — | 23 | 15 |
| | **all** | | | **4309** | **921** |

## Scope

This repo tests **codec correctness** — wire encoding and decoding of individual messages — and **catalog correctness**: parsing MSF and CMSF catalogs and applying their deltas. It does not test session state machines, transport-layer behavior, or media-layer concerns such as the boxes inside a CMAF header. Session conformance testing (state transitions, race conditions, interop flows) requires a dynamic test harness.

## License

MIT
