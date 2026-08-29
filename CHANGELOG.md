# Changelog

Breaking changes only. A vector's `id` is its contract — consumers key their
expectations on it — so a vector that changes what it asserts, or stops
existing, is breaking even though the corpus only ever grows. Everything else,
including every vector added, is in the git history.

A version with no entry here broke nothing.

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
