# Changelog

Breaking changes only. A vector's `id` is its contract — consumers key their
expectations on it — so a vector that changes what it asserts, or stops
existing, is breaking even though the corpus only ever grows. Everything else,
including every vector added, is in the git history.

A version with no entry here broke nothing.

## 0.16.0

Ten draft-17 vectors changed what they assert, so whatever this becomes is a
minor bump and not a patch. They were wrong, and a consumer that agreed with
them was wrong in the same direction.

Every AUTHORIZATION_TOKEN vector on draft-17 encoded the Token Value behind a
varint length of its own, which draft-17 does not define. The Token structure
is `Token { Alias Type (vi64), [Token Alias (vi64)], [Token Type (vi64)],
[Token Value (..)] }` — Figure 5, §9.3.2 — and `(..)` is the rest of the value,
not a length followed by that many bytes. The length that is genuinely there is
the Key-Value-Pair's own, which is what "The AUTHORIZATION TOKEN parameter
(Parameter Type 0x03) uses Length-prefixed encoding" is describing.

What made this survive is that the sentence reads like it means an inner
length, and that the vectors were self-consistent: the spurious byte was
counted in the KVP length and again in the message length, so framing
validation passed and nothing downstream disagreed. It is only wrong against
the draft.

Draft-18 is the proof rather than the analogy. Its Figure 5 is byte-for-byte
draft-17's, the "uses Length-prefixed encoding" sentence appears verbatim in
both (§9.3.2 and §10.2.2), and draft-18's vectors already encode no inner
length. Two drafts saying the same thing cannot encode it two ways.

The ten, all under `transport/draft17/codec/messages/`:

| file | vector id |
| --- | --- |
| `fetch.json` | `standalone-with-auth-token` |
| `publish-namespace.json` | `with-auth-token` |
| `publish.json` | `with-auth-token` |
| `setup.json` | `with-auth-token-register`, `with-path-auth-authority` |
| `subscribe-namespace.json` | `with-auth-token` |
| `subscribe.json` | `with-auth-token-register`, `with-auth-token-use-value`, `with-two-auth-tokens` |
| `track-status.json` | `with-auth-token` |

The two in `setup.json` are Setup Options rather than Message Parameters, a
separate namespace — they are here because §9.4.1.4 makes the AUTHORIZATION
TOKEN Setup Option "functionally equivalent to the AUTHORIZATION TOKEN message
parameter", same structure and so the same defect.

Only draft-17 is affected. Drafts 11 through 16 and 18 through 20 were checked
and encode no inner length.

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
