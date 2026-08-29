# Changelog

Notable changes to `@moqtap/test-vectors`.

A vector's `id` is its contract: consumers key their expectations on it, so a
vector that changes what it asserts, or stops existing, is a breaking change
even when the corpus grows. Those are called out under **Breaking** below.

Releases before 0.12.0 are in the git history.

## [0.12.0]

### Breaking

Six published vectors changed what they assert. Each was wrong about the draft
it belongs to.

- **`draft16/messages/subscribe.json [unknown-extension-param]`** decoded
  successfully; it now expects `invalid_parameter`. Draft-16 Section 9.2 added
  "All Message Parameters MUST be defined in the negotiated version of MOQT or
  negotiated via Setup Parameters. An endpoint that receives an unknown Message
  Parameter MUST close the session with PROTOCOL_VIOLATION", and narrowed the
  sentence permitting unknown parameters to *Setup* Parameters in the same
  paragraph. Drafts 11 through 15 say the opposite and keep their
  decode-success vectors.

- **`draft17/messages/fetch-ok.json [with-params-and-properties]`**,
  **`draft18/…`** and **`draft19/…`** decoded successfully; they now expect
  `parameter_out_of_scope`. Each carried EXPIRES, which those drafts do not
  list FETCH_OK among the messages for.

- **`draft17/messages/publish-ok.json [with-largest-object]`** decoded
  successfully; it now expects `parameter_out_of_scope`. It carried
  LARGEST_OBJECT, which draft-17 permits in SUBSCRIBE_OK, PUBLISH or
  REQUEST_OK — and on that draft PUBLISH_OK is a message type of its own.

- **`draft12/messages/subscribe-error.json [retry-track-alias]`** is removed.
  It asserted a successful decode of SUBSCRIBE_ERROR code `0x6`, which draft-12
  does not assign: its codes run `0x0`–`0x5` and resume at `0x10`. The code
  existed in draft-11 only.

A consumer comparing against `decoded` for the first five ids will not find
one, and one keying on the sixth will not find the vector.

### Added

- **`unknown-extension-param` on drafts 17, 18 and 19**, matching draft-16.
  All four drafts state the rule; only draft-16 asserted it.
- Three positive vectors: `draft12 [datagram-end-of-group]`,
  `draft12 [datagram-eog-with-extensions]`,
  `draft15 [datagram-default-priority]`.
- Error categories `invalid_type`, `parameter_out_of_scope` and
  `payload_not_permitted`. Only `parameter_out_of_scope` has vectors so far;
  the other two are reserved for rules the corpus does not yet cover.
- A `profiles` field on vectors, naming which conformance profiles an
  expectation binds. Absent means both, so every existing vector is unchanged.

### Fixed

67 published positive vectors carried bytes that do not decode, or decode to
something other than what their `decoded` object claims. The corrections are
per-draft repetitions of a handful of mistakes: object status codes on drafts
04–12, the SUBSCRIBE_OK no-content flag on 07–14, datagram type codes on
draft-12, delta-coded parameter types on draft-16, and parameter length
prefixes on drafts 18 and 19.

### Changed

- `validate.py` now checks a vector's fields, error category and profiles
  against the schema, reading them from the schema rather than restating them.
- The error categories and the `profiles` field are documented in
  `schema/codec-vector.schema.json` rather than in the README, so the
  definition and the file the validator reads are the same file.
