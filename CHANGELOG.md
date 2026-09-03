# Changelog

Breaking changes only. A vector's `id` is its contract — consumers key their
expectations on it — so a vector that changes what it asserts, or stops
existing, is breaking even though the corpus only ever grows. Everything else,
including every vector added, is in the git history.

A version with no entry here broke nothing.

## 0.15.0

Nothing changed what it asserts; this is a version of its own because 0.14.0's
shape change is what made the additions expressible.

Ten vectors added, one per draft from 11 to 20: `with-two-auth-tokens`, a
message carrying AUTHORIZATION_TOKEN twice with different Token Values. The
parameter's own definition permits it — "The AUTHORIZATION TOKEN parameter MAY
be repeated within a message as long as the combination of Token Type and Token
Value are unique after resolving any aliases" — and until now **no vector in the
corpus exercised a repeated parameter type of any kind other than the four Range
Filter cases added in 0.13.x**. A consumer had nothing telling it how a repeat
decodes, which is how two of them arrived at one slot per name.

Drafts 07 through 10 have none, and that is a fact about them: their text has no
carve-out, so every repeat is a duplicate and is refused.

The two encodings are both covered, because they differ: drafts 11 through 15
write Parameter Types absolutely, so a repeat is the type again, and drafts 16
and later delta-encode them, so a repeat is a Type Delta of 0 — the only
encoding a second instance has once the types are required to ascend.

## 0.14.0

Every Key-Value-Pair block in a `decoded` message changed shape. A consumer
reading `decoded.parameters` as a map keyed by parameter name will not find one.

`parameters`, `setup_parameters`, `options`, `track_properties` and
`track_extensions` are now an array of entries in wire order. Each entry carries
a `type` (lowercase hex), an optional `name`, and exactly one of `value` or
`raw_hex`:

```json
"parameters": [
  { "type": "0x20", "name": "subscriber_priority", "value": "128" },
  { "type": "0x25", "name": "subgroup_filter",
    "value": { "set_id": "0", "ranges": [{ "start": "2", "end": "4" }] } }
]
```

The map could not express three things the drafts require. A parameter type may
repeat — AUTHORIZATION_TOKEN says so, and drafts 19 and 20 say it of the five
Range Filters — and a map has one slot per name, so a SUBSCRIBE carrying two
SUBGROUP_FILTERs under different SetIDs was recorded as the second one alone.
Drafts 16 and later require parameters to ascend by Type and close the session
over a pair that does not, and a map has no order for a vector to be wrong
about. And a type the draft names nothing has no key to sit under, which is why
unknown parameters lived in a second, differently-shaped `unknown` array beside
the named ones on some drafts and were dropped outright on others.

Three consequences beyond the shape:

- The `unknown` array is gone. An unnamed type is an ordinary entry, told apart
  by having no `name`.
- An unknown *integer* parameter used to be written `{"id": ..., "length": N}`,
  where `N` was the varint's value under a key naming something else. It is now
  `value`.
- Drafts 00 through 06 changed too. `moqtap-codec` does not implement them, so
  their parameter types were recovered from the bytes and accepted only where
  the parse was forced: it had to consume the block exactly, produce as many
  entries as the vector already named, and every recovered value had to equal
  the value already recorded under one of those names.

The data plane's `extension_headers` and `object_properties` are Key-Value lists
too and are unchanged. Nothing regenerates them, so converting them would mean
editing by hand values that no consumer checks.

`schema/codec-vector.schema.json` describes all of this for the first time —
`decoded` previously had no stated shape at all, which is why each new case fell
to whoever met it first.

## 0.12.0

Six published vectors changed what they assert. Each was wrong about the draft
it belongs to.

- `draft16/messages/subscribe.json [unknown-extension-param]` decoded
  successfully; now expects `invalid_parameter`. Draft-16 Section 9.2 requires
  an endpoint receiving an unknown Message Parameter to close the session.
  Drafts 11 through 15 say the opposite and keep their decode-success vectors.
- `draft17`, `draft18` and `draft19`
  `/messages/fetch-ok.json [with-params-and-properties]` decoded successfully;
  now expect `parameter_out_of_scope`. Each carried EXPIRES, which those drafts
  do not list FETCH_OK among the messages for.
- `draft17/messages/publish-ok.json [with-largest-object]` decoded
  successfully; now expects `parameter_out_of_scope`. It carried
  LARGEST_OBJECT, which draft-17 permits in SUBSCRIBE_OK, PUBLISH or
  REQUEST_OK, and on that draft PUBLISH_OK is a message type of its own.
- `draft12/messages/subscribe-error.json [retry-track-alias]` is removed. It
  asserted a successful decode of SUBSCRIBE_ERROR code `0x6`, which draft-12
  does not assign: its codes run `0x0`–`0x5` and resume at `0x10`.

A consumer comparing against `decoded` for the first five ids will not find
one; one keying on the sixth will not find the vector.
