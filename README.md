# moqtap/test-vectors

Language-agnostic test vectors for the [Media over QUIC Transport (MoQT)](https://datatracker.ietf.org/doc/draft-ietf-moq-transport/) protocol family. Canonical hex-encoded wire bytes paired with expected decoded representations, enabling any MoQT implementation to validate its codec against a shared, authoritative test suite.

Beside the transport codec vectors sit catalog vectors for the [MOQT Streaming Format (MSF)](https://datatracker.ietf.org/doc/draft-ietf-moq-msf/) and its CMAF extension [CMSF](https://datatracker.ietf.org/doc/draft-ietf-moq-cmsf/): the exact text of catalog objects, independent and delta, paired with the catalog they resolve to or the complaint they must draw. MSF also has timeline vectors: the payload of a media or event timeline Object, and MSF-01's media timeline template, paired with the records they hold. CMSF also has object vectors, the payload of one Object of a CMAF track read against the track's CMAF header, and timeline vectors, the records of its SAP Type timeline. Property vectors cover the [Low Overhead Media Container (LOC)](https://datatracker.ietf.org/doc/draft-ietf-moq-loc/): one property value at a time, paired with what it means under each LOC draft.

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
    timeline/
      media.json            Media timeline records
      event.json            Event timeline records, their data as the payload has it
      template.json         Media timeline templates and the entries they yield (draft-01)
    meta.json
cmsf/
  draft00/                  CMAF MOQT Streaming Format draft-00
  draft01/                  CMAF MOQT Streaming Format draft-01 (extends MSF draft-01)
    catalog/
      cmaf.json             packaging cmaf, SAP starting types, the SAP Type timeline track
      init-data.json        initData (draft-00); initDataList and initRef (draft-01)
      content-protection.json  contentProtections and contentProtectionRefIDs (draft-01)
    objects/
      structure.json        moof and mdat, other top-level boxes, malformed boxes
      track-id.json         tfhd track_ID against the header's tkhd, one track per Object
      sap.json              the first sample's flags and SAP type, the SAP at a Group's start
      timing.json           earliest presentation time, in ticks and in milliseconds
    timeline/
      sap.json              SAP Type timeline records
    meta.json
loc/
  draft00/                  Low Overhead Media Container draft-00
  draft01/                  Low Overhead Media Container draft-01 (wire-identical to draft-00)
  draft02/                  Low Overhead Media Container draft-02
  draft03/                  Low Overhead Media Container draft-03
  draft04/                  Low Overhead Media Container draft-04
    properties/
      capture-timestamp.json  Capture Timestamp (draft-00, draft-01)
      timestamp.json        Timestamp (draft-03, draft-04)
      timescale.json        Timescale (draft-02 on)
      video-config.json     Video Config
      video-frame-marking.json  Video Frame Marking
      audio-config.json     Audio Config (draft-03 on)
      audio-level.json      Audio Level (not draft-02)
      conflicts.json        Types the draft gives more than one meaning (draft-02)
    meta.json
mzanaty-loc/
  draft05/                  draft-mzanaty-moq-loc-05, the LOC draft MSF-00 cites
    properties/
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

### Property vectors

A property vector holds one LOC property as a transport Key-Value-Pair delivers it: a `property_type` and, for an even type, the `value` its varint carried, in decimal, or for an odd type its bytes as `value_hex`. Then exactly one of `decoded`, what the value means under that draft, or `error` with an optional `error_detail`. Vectors do not depend on the transport's framing or varint encoding; where a draft bounds a value by its encoded size, the description names the varint of the transport draft it cites.

```json
{
  "id": "two-octet-range",
  "description": "Video Frame Marking: 41221 fits the 2-octet form ... and the 3-octet form with a zero first octet ... so both are candidates.",
  "property_type": "0x04",
  "value": "41221",
  "decoded": {
    "name": "Video Frame Marking",
    "candidates": [
      { "octets": "2", "S": true, "E": false, "I": true, "D": false, "B": false, "TID": "1", "LID": "5" },
      { "octets": "3", "S": false, "E": false, "I": false, "D": false, "B": false, "TID": "0", "LID": "161", "TL0PICIDX": "5" }
    ]
  }
}
```

`decoded` takes one of four shapes:

- **A reading:** `name` and the value's fields.
- **Candidates:** `name` and `candidates`, two or more complete readings, when the draft leaves the form of the value open. A decoder reports them all and picks none.
- **Uninterpreted:** `name` and `"uninterpreted": true`, when the draft admits the value but defines no reading for it. A decoder shows the value raw.
- **Ambiguous:** `ambiguous` alone, listing the meanings the draft gives the property type. A decoder shows the value raw under those names.

Frame Marking fields are named as RFC 9626 names them: `S`, `E`, `I`, `D` and `B` as booleans, `TID`, `LID` and `TL0PICIDX` as integers, and `octets` for the form. In draft-00 to draft-02, Frame Marking travels in the least significant bits of a varint. Those drafts say neither which form was sent nor how a multi-octet form is packed into the integer. The vectors read the first octet as the most significant, and every value below 2^16 lists each form it fits. Audio Level's `voice_activity` is the RFC 6464 V bit and `level` its 7-bit level. Video Config and Audio Config give only their `length`: the drafts pass the codec's configuration on as it is.

Vectors cover the value of one property. They do not cover which LOC draft a track uses, nor the property types a transport draft claims for itself at Object scope (draft-19 and later claim 0x02 and 0x06, draft-19 Sections 12.1 and 12.2). The error categories are defined in [`schema/property-vector.schema.json`](schema/property-vector.schema.json).

### Object vectors

An object vector holds the payload of one Object of a `cmaf` track as `object`, and the CMAF header the catalog gives the track, decoded from its Base64, as `header`; both are `{"hex": ...}`. A vector without `header` reads the Object without one. `first_in_group: true` marks the first Object of a Group, which must begin with a SAP of type 1 or 2: CMSF 3.4 says the Group 'MUST begin with an Object containing a stream access point (SAP) type 1 or 2', and 3.6.1 requires the SAP type that Object begins with to be 1 or 2. Then exactly one of `decoded` or `error` with an optional `error_detail`.

```json
{
  "id": "sample-presented-earlier",
  "description": "A sync first sample presented at 6000 and a second sample presented at 3000 ...",
  "header": { "hex": "0000001866747970636d6632..." },
  "object": { "hex": "0000006c6d6f6f66000000106d666864..." },
  "decoded": {
    "boxes": ["moof", "mdat"],
    "chunks": [
      { "sequence_number": "1", "trafs": [{ "track_id": "1", "base_media_decode_time": "0", "sample_count": "2" }] }
    ],
    "track_id_in_header": true,
    "timescale": "90000",
    "first_sample": { "flags_from": "trun_first_sample_flags", "is_leading": "0", "depends_on": "2", "sync": true, "sap_type": ["2", "3"] },
    "earliest_presentation_time": "3000",
    "ept_ms": ["33"]
  }
}
```

`decoded` says what the payload and header state:

- `boxes`: every top-level box, in order. CMSF neither allows nor forbids boxes beside moof and mdat, such as styp, emsg and prft; they are listed and draw no complaint.
- `chunks`: each moof that an mdat follows, with its mfhd `sequence_number` and, per traf, the tfhd `track_id`, the tfdt `base_media_decode_time` and the `sample_count`.
- `first_sample`: where the first sample's flags come from (the trun's `first_sample_flags` or per-sample flags, the tfhd default, the header's trex default), its `is_leading`, `depends_on` and `sync`, and `sap_type` as candidates. A trun carrying both `first_sample_flags` and per-sample flags makes the flags, `sync` and `sap_type` `"ambiguous"`. A `'sap '` sample group states the type. Otherwise, by ISO/IEC 14496-12: a sync sample is type 1 or 2; a later sample of the Object presented before it rules out 1, and the type is 2 only when every such sample has `is_leading` 3 (decodable), else 2 or 3.
- `earliest_presentation_time`, in the track's timescale, and `ept_ms`, the value a SAP Type timeline record carries (3.6.1): rounded to the nearest millisecond, with both candidates when it lies exactly halfway.

`"not_signalled"` marks a value the payload and header do not state, and `"ambiguous"` one they state in ways no draft or ISO/IEC 14496-12 ranks. A reader reports either as such and does not fill it in. A first Object of a Group whose SAP type is not signalled draws no complaint; one whose signalled type is 3 does.

CMSF 3.3 asks the moof for a 'Track Box (trak) with a Track ID (track_ID) matching a Track Box in the initialization fragment'. A moof carries Track Fragment Boxes, so the vectors match each traf's tfhd track_ID against the tkhd track_IDs of the header. Box layouts are those of ISO/IEC 14496-12. The error categories are defined in [`schema/object-vector.schema.json`](schema/object-vector.schema.json).

### Timeline vectors

A timeline vector holds one `input` as `{"text": ...}`: the payload of one timeline Object, uncompressed, or the value of a track's `template` field. The file's `format` says which: `mediatimeline`, `eventtimeline` or `template`. An event timeline file names the track's `event_type` when the vectors apply its definition. Then exactly one of `decoded`, every record in payload order, or `error` with an optional `error_detail`. Records are not merged: two records for one Location both appear.

- A media timeline record (MSF 7.1) reads as `media_time_ms`, the `group_id` and `object_id` of its Location, and `wallclock_ms`. Media time is an integer: MSF-00 rounds it to the nearest millisecond, MSF-01 7.1.1 takes the floor.
- An event timeline record (MSF 8.1) reads as its `index` key (`t`, `l` or `m`), that reference's value (`wallclock_ms`; `group_id` and `object_id`; or `media_time_ms`) and `data`. Without an `event_type`, `data` is the JSON value the payload has.
- A SAP Type timeline (`org.ietf.moq.cmsf.sap`) record reads as the `group_id` and `object_id` of its Location and the `sap_type` and `ept_ms` of its data.
- A template (MSF-01 7.4.1) reads as its six values in `decoded.template` and, in `decoded.records`, its first `entries` entries as media timeline records: entry n is the start value plus n times the delta, for each of media time, Location and wallclock.

Cases the drafts leave open have no vector, among them records with extra items or keys, a fractional or negative wallclock time, a fractional template delta, and a template inside a timeline document.

```json
{
  "id": "first-object-sap-3",
  "description": "SAP type 3 for Object 0 of Group 2. ...",
  "input": { "text": "[{\"l\": [2, 0], \"data\": [3, 8000]}]" },
  "error": "invalid_value",
  "error_detail": "records[0].data[0]"
}
```

The first Object of a Group must carry SAP type 1 or 2 (3.6.1), and that Object has Object ID 0: through MSF-01 6.2 in CMSF-01, and through draft-ietf-moq-transport-10 9.1.1, the transport draft CMSF-00 cites, in CMSF-00. The error categories are defined in [`schema/timeline-vector.schema.json`](schema/timeline-vector.schema.json).

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
import marking from '@moqtap/test-vectors/loc/draft04/properties/video-frame-marking.json';
import sap from '@moqtap/test-vectors/cmsf/draft01/objects/sap.json';
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

MSF carries catalogs and timelines. CMSF adds the payload of a CMAF Object and its SAP Type timeline. MSF-00 writes `version` as a Number and a delta as `deltaUpdate: true` with `addTracks`, `removeTracks` and `cloneTracks`; MSF-01 writes `version` as a String and `deltaUpdate` as an ordered array of `{op, tracks}`. CMSF-00 puts each CMAF header in the track's `initData`; CMSF-01 moves it to a root `initDataList` that tracks point into with `initRef`, and adds `contentProtections`. CMSF-00 extends the WARP Streaming Format draft that preceded MSF, which is not included; its vectors cover only what CMSF-00 itself defines. Where a draft contradicts itself — `mimeType` in its field table and `mimetype` in its examples; `"draft-XX"` as the version convention and `"1"` in every example; examples whose Base64 is elided with `...` — the vector's description says so.

LOC carries property values only. Draft-00 and draft-01 are wire-identical. Draft-02 gives type 0x06 to both Timestamp and Audio Level. That type is `ambiguous` and sits in draft-02's `conflicts.json`. Draft-03 gives Timestamp two types, 0x06 (Table 1) and 0x0A (2.3.1.1), and its `timestamp.json` covers both. Draft-mzanaty-moq-loc-05 frames an even type's value as Length and bytes, the reverse of every transport draft's framing. All four of its types are even, so each of its vectors is `uninterpreted`. A type does not mean the same thing across these drafts: 0x10 is Video Config in mzanaty-05 and Timestamp in draft-04. A consumer therefore runs the vectors of the draft a track uses.

The two type columns count files — one per control message type, one per data stream or datagram type; a catalog or property spec has neither, and its row counts its vectors. A **negative** vector is one carrying an `error` category instead of a `decoded` block: input a conforming consumer must refuse.

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
| MOQT Streaming Format | draft-00 | — | — | 79 | 49 |
| MOQT Streaming Format | draft-01 | — | — | 110 | 67 |
| CMAF MOQT Streaming Format | draft-00 | — | — | 76 | 36 |
| CMAF MOQT Streaming Format | draft-01 | — | — | 91 | 48 |
| Low Overhead Media Container | draft-00 | — | — | 20 | 2 |
| Low Overhead Media Container | draft-01 | — | — | 20 | 2 |
| Low Overhead Media Container | draft-02 | — | — | 17 | 1 |
| Low Overhead Media Container | draft-03 | — | — | 31 | 3 |
| Low Overhead Media Container | draft-04 | — | — | 29 | 3 |
| Low Overhead Media Container (draft-mzanaty) | draft-05 | — | — | 5 | 0 |
| | **all** | | | **4639** | **1047** |

## Scope

This repo tests **codec correctness** — wire encoding and decoding of individual messages — **catalog correctness**: parsing MSF and CMSF catalogs and applying their deltas; **timeline correctness**: reading MSF media and event timelines and MSF-01 templates; and **object correctness**: reading a CMSF Object against its CMAF header and reading its SAP Type timeline; and **property correctness**: reading LOC property values. It does not test session state machines, transport-layer behavior, or media-layer concerns beyond the boxes CMSF names, such as the codec configuration in a sample entry or a LOC Video Config. Session conformance testing (state transitions, race conditions, interop flows) requires a dynamic test harness.

## License

MIT
