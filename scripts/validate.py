#!/usr/bin/env python3
"""Validate test vector files for structural correctness.

Checks:
1. All JSON files parse correctly
2. Hex fields are valid even-length lowercase hex strings
3. Every codec vector has exactly one of decoded or error
4. Protocol integer fields in decoded objects are strings matching ^[0-9]+$
5. Control message framing: declared length matches actual payload length
   (varint framing for draft00..10, 16-bit BE for draft11+)
6. Every version directory has a meta.json
7. meta.json entries are consistent with manifest.json
8. Vector fields, error categories and conformance profiles are ones the
   schema names
9. Catalog vectors: every payload is exact text or hex; payloads that must
   parse do, an invalid_json payload does not; a single independent object
   resolves to itself parsed
10. Every JSON file under a version directory sits in a category its meta.json
    lists, and every listed category exists
11. Property vectors: an even type carries `value`, an odd type `value_hex`;
    exactly one of decoded and error; decoded has one of its four shapes
12. Object vectors: header and object are lowercase hex; exactly one of
    decoded and error; a header's top-level boxes tile it and include moov;
    a decoded object's top-level boxes tile it and are the ones it lists
13. Timeline vectors: exactly one of decoded and error; invalid_json exactly
    when the text does not parse; decoded is what the input reads as under the
    file's format: its records in payload order, or a template's entries

Every spec in manifest.json is walked.

Check 8 repeats part of validate-schema.mjs so that it runs without npm install.
"""

import json
import glob
import os
import re
import struct
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
errors = []

def err(msg):
    errors.append(msg)
    print(f"  FAIL: {msg}", file=sys.stderr)

# Known protocol integer field names (must be strings matching ^[0-9]+$)
# Union of all field names across all drafts.
PROTOCOL_INT_FIELDS = {
    # common
    "value", "track_alias", "group_id", "object_id", "subgroup_id",
    "error_code", "status_code", "subscriber_priority", "publisher_priority",
    "group_order", "content_exists", "filter_type", "expires",
    "start_group", "start_object", "end_group", "end_of_track",
    "payload_length", "length",
    # draft-07
    "subscribe_id", "end_object", "object_status",
    "largest_group_id", "largest_object_id",
    "final_group", "final_object",
    "last_group_id", "last_object_id",
    "role", "max_subscribe_id", "delivery_timeout", "max_cache_duration",
    # draft-14
    "request_id", "forward", "largest_group",
    "subscribe_request_id", "max_request_id", "max_auth_token_cache_size",
    # draft-15: subscription_request_id, stream_count, joining fields
    "subscription_request_id", "stream_count",
    "joining_request_id", "joining_start", "maximum_request_id",
    "fetch_type", "status", "joining_subscribe_id",
    "extension_headers_length", "preceding_group_offset",
    "extension_count", "maximum_subscribe_id",
    # Location fields (used inside largest_object parameter)
    "group", "object",
    # draft-16: existing_request_id, retry_interval, subscribe_options
    "existing_request_id", "retry_interval", "subscribe_options",
    "timeout",
    "object_id_delta",
    "required_request_id_delta",
    # draft-00/01
    "track_id", "group_sequence", "object_sequence", "object_send_order",
    "mode",
}

# Fields that are string integers inside version arrays
VERSION_INT_FIELDS = set()  # versions are already strings in our format

INT_PATTERN = re.compile(r"^[0-9]+$")
HEX_PATTERN = re.compile(r"^([0-9a-f]{2})+$")

# Fields that are Location objects ({mode, value}) in early drafts but plain int strings in draft07+
_LOCATION_FIELDS = {"start_group", "start_object", "end_group", "end_object"}
# Drafts where Location fields are objects rather than plain int strings
_LOCATION_OBJECT_DRAFTS = {"draft01", "draft02", "draft03"}

# Every Key-Value-Pair block renders as a list of entries in wire order, so
# these keys hold a list and not a map. See `check_kvp_block`.
_KVP_BLOCK_KEYS = {
    "parameters",
    "setup_parameters",
    "options",
    "track_properties",
    "track_extensions",
    "extension_headers",
    "object_properties",
}
_KVP_TYPE_PATTERN = re.compile(r"^0x[0-9a-f]+$")


def _looks_like_kvp_block(value):
    return (
        isinstance(value, list)
        and value
        and all(
            isinstance(e, dict)
            and isinstance(e.get("type"), str)
            and _KVP_TYPE_PATTERN.match(e["type"])
            for e in value
        )
    )


def check_kvp_block(entries, path, filename, draft_id=None):
    """Check one parameter or setup-option block.

    Every entry carries a `type`, may carry a `name`, and carries exactly one of
    `value` and `raw_hex`. An entry's `value` is whatever that parameter type
    defines, so the integer rule does not apply to the key itself — but it does
    apply inside, which is why this recurses into the value.
    """
    if not isinstance(entries, list):
        err(f"{filename}: {path} must be a list of entries, in wire order")
        return
    for i, entry in enumerate(entries):
        at = f"{path}[{i}]"
        if not isinstance(entry, dict):
            err(f"{filename}: {at} must be an entry object")
            continue
        extra = set(entry) - {"type", "name", "value", "raw_hex"}
        if extra:
            err(f"{filename}: {at} has unknown keys {sorted(extra)}")
        ptype = entry.get("type")
        if not isinstance(ptype, str) or not _KVP_TYPE_PATTERN.match(ptype):
            err(f"{filename}: {at}.type = {ptype!r} must be lowercase hex, like '0x21'")
        if "name" in entry and not isinstance(entry["name"], str):
            err(f"{filename}: {at}.name = {entry['name']!r} must be a string")
        if ("value" in entry) == ("raw_hex" in entry):
            err(f"{filename}: {at} must carry exactly one of `value` and `raw_hex`")
        if "raw_hex" in entry:
            raw = entry["raw_hex"]
            if not isinstance(raw, str) or (raw and not HEX_PATTERN.match(raw)):
                err(f"{filename}: {at}.raw_hex = {raw!r} must be lowercase hex")
        if "value" in entry:
            # A parameter whose value is itself a Key-Value-Pair block — a
            # draft-20 FILL_PARAMETERS — is the same shape one level down.
            if _looks_like_kvp_block(entry["value"]):
                check_kvp_block(entry["value"], f"{at}.value", filename, draft_id)
            else:
                check_protocol_ints(entry["value"], f"{at}.value", filename, draft_id)


def check_protocol_ints(obj, path, filename, draft_id=None):
    """Recursively check that protocol integer fields are strings."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in _KVP_BLOCK_KEYS:
                check_kvp_block(v, f"{path}.{k}", filename, draft_id)
            elif k in PROTOCOL_INT_FIELDS:
                if isinstance(v, dict) and k in _LOCATION_FIELDS and draft_id in _LOCATION_OBJECT_DRAFTS:
                    check_protocol_ints(v, f"{path}.{k}", filename, draft_id)
                elif not isinstance(v, str) or not INT_PATTERN.match(v):
                    err(f"{filename}: {path}.{k} = {v!r} must be a string of digits")
            elif k == "supported_versions":
                if isinstance(v, list):
                    for i, item in enumerate(v):
                        if not isinstance(item, str) or not INT_PATTERN.match(item):
                            err(f"{filename}: {path}.supported_versions[{i}] = {item!r} must be a string of digits")
            elif k == "selected_version":
                if not isinstance(v, str) or not INT_PATTERN.match(v):
                    err(f"{filename}: {path}.selected_version = {v!r} must be a string of digits")
            else:
                check_protocol_ints(v, f"{path}.{k}", filename, draft_id)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            check_protocol_ints(item, f"{path}[{i}]", filename, draft_id)

# The schema is the authority on field names, error categories and profiles;
# read it rather than restating it, so a change upstream cannot be contradicted
# here in silence.
def _load_vector_schema():
    path = os.path.join(REPO_ROOT, "schema", "codec-vector.schema.json")
    with open(path) as f:
        vector = json.load(f)["$defs"]["vector"]
    return (
        set(vector["properties"]),
        set(vector["properties"]["error"]["enum"]),
        set(vector["properties"]["profiles"]["items"]["enum"]),
    )


VECTOR_FIELDS, ERROR_CATEGORIES, PROFILES = _load_vector_schema()


def _load_catalog_schema():
    path = os.path.join(REPO_ROOT, "schema", "catalog-vector.schema.json")
    with open(path) as f:
        schema = json.load(f)
    vector = schema["$defs"]["vector"]
    return (
        set(schema["properties"]),
        set(vector["properties"]),
        set(vector["properties"]["error"]["enum"]),
        set(vector["properties"]["profiles"]["items"]["enum"]),
    )


(CATALOG_FILE_FIELDS, CATALOG_VECTOR_FIELDS, CATALOG_ERROR_CATEGORIES,
 CATALOG_PROFILES) = _load_catalog_schema()

ID_PATTERN = re.compile(r"^[a-z0-9-]+$")

def validate_vector_ids(filepath, vectors):
    """Check that all vectors have unique, valid id fields."""
    seen_ids = set()
    for i, v in enumerate(vectors):
        vid = v.get("id")
        if vid is None:
            err(f"{filepath}: [{i}] missing required 'id' field")
            continue
        if not ID_PATTERN.match(vid):
            err(f"{filepath}: [{i}] id '{vid}' must be lowercase kebab-case")
        if vid in seen_ids:
            err(f"{filepath}: [{i}] duplicate id '{vid}'")
        seen_ids.add(vid)

def validate_codec_vectors(filepath, data, draft_id=None):
    """Validate a codec vector file."""
    if "vectors" not in data:
        err(f"{filepath}: missing 'vectors' array")
        return

    validate_vector_ids(filepath, data["vectors"])

    for i, v in enumerate(data["vectors"]):
        desc = v.get("description", f"vector {i}")

        # Check hex field
        if "hex" in v:
            h = v["hex"]
            if not HEX_PATTERN.match(h):
                err(f"{filepath}: [{i}] '{desc}' hex is invalid: {h[:40]}")

        # Check mutual exclusivity
        has_decoded = "decoded" in v
        has_error = "error" in v
        if has_decoded and has_error:
            err(f"{filepath}: [{i}] '{desc}' has both decoded and error")
        elif not has_decoded and not has_error:
            err(f"{filepath}: [{i}] '{desc}' has neither decoded nor error")

        # Check the vector against the shape the schema declares
        extra = set(v) - VECTOR_FIELDS
        if extra:
            err(f"{filepath}: [{i}] '{desc}' carries {sorted(extra)}, which the schema does not declare")
        if has_error and v["error"] not in ERROR_CATEGORIES:
            err(f"{filepath}: [{i}] '{desc}' claims error category {v['error']!r}, which the schema does not name")

        profiles = v.get("profiles")
        if profiles is not None:
            if not isinstance(profiles, list) or not profiles:
                err(f"{filepath}: [{i}] '{desc}' profiles must be a non-empty list")
            else:
                if len(set(profiles)) != len(profiles):
                    err(f"{filepath}: [{i}] '{desc}' names a profile twice")
                for name in profiles:
                    if name not in PROFILES:
                        err(f"{filepath}: [{i}] '{desc}' names profile {name!r}, which the schema does not admit")
            if has_decoded:
                err(f"{filepath}: [{i}] '{desc}' names profiles and decodes; bytes decode the same for every reader")
            if v.get("error") == "incomplete":
                err(f"{filepath}: [{i}] '{desc}' restricts a truncation to some readers; a frame that ended early ended early for everyone")

        # Check protocol integers in decoded
        if has_decoded:
            check_protocol_ints(v["decoded"], f"[{i}].decoded", filepath, draft_id)

def _reject_constant(name):
    raise ValueError(f"{name} is not JSON")


def _parse_payload(payload):
    """The payload as a JSON value, or raise.

    `hex` must be UTF-8 (RFC 8259 §8.1). NaN and Infinity are rejected.
    """
    if "hex" in payload:
        raw = bytes.fromhex(payload["hex"]).decode("utf-8")
    else:
        raw = payload["text"]
    return json.loads(raw, parse_constant=_reject_constant)


def _check_payload(filepath, at, payload):
    """A payload is exactly one of `text` and `hex`; False when it is not."""
    if not isinstance(payload, dict) or len(payload) != 1 or not (
        "text" in payload or "hex" in payload
    ):
        err(f"{filepath}: {at} must be {{text}} or {{hex}}, and exactly one")
        return False
    if "text" in payload and not isinstance(payload["text"], str):
        err(f"{filepath}: {at}.text must be a string, the exact payload")
        return False
    if "hex" in payload and not (
        isinstance(payload["hex"], str) and HEX_PATTERN.match(payload["hex"])
    ):
        err(f"{filepath}: {at}.hex is not lowercase hex")
        return False
    return True


def validate_catalog_vectors(filepath, data):
    """Validate a catalog vector file: its shape, that payloads parse (an
    invalid_json one does not), and that a lone object resolves to itself.
    """
    extra = set(data) - CATALOG_FILE_FIELDS
    if extra:
        err(f"{filepath}: carries {sorted(extra)}, which the catalog schema does not declare")
    stem = os.path.splitext(os.path.basename(filepath))[0]
    if data.get("topic") != stem:
        err(f"{filepath}: topic {data.get('topic')!r} is not the file name {stem!r}")
    if "vectors" not in data:
        err(f"{filepath}: missing 'vectors' array")
        return

    validate_vector_ids(filepath, data["vectors"])

    for i, v in enumerate(data["vectors"]):
        desc = v.get("id", f"vector {i}")
        where = f"[{i}] '{desc}'"

        extra = set(v) - CATALOG_VECTOR_FIELDS
        if extra:
            err(f"{filepath}: {where} carries {sorted(extra)}, which the schema does not declare")
        if not isinstance(v.get("description"), str) or not v.get("description"):
            err(f"{filepath}: {where} needs a description citing the draft")

        has_resolved = "resolved" in v
        has_error = "error" in v
        if has_resolved == has_error:
            err(f"{filepath}: {where} must carry exactly one of resolved and error")
            continue
        if has_error and v["error"] not in CATALOG_ERROR_CATEGORIES:
            err(f"{filepath}: {where} claims error category {v['error']!r}, which the schema does not name")
        if has_resolved and ("error_detail" in v or "error_at" in v):
            err(f"{filepath}: {where} resolves and still says where it fails")

        payloads = [v.get("input")]
        if "steps" in v:
            if not isinstance(v["steps"], list) or not v["steps"]:
                err(f"{filepath}: {where} steps must be a non-empty list")
                continue
            payloads += v["steps"]
        names = ["input"] + [f"steps[{n}]" for n in range(len(payloads) - 1)]
        if not all(_check_payload(filepath, f"{where}.{n}", p) for n, p in zip(names, payloads)):
            continue

        error_at = v.get("error_at", 0)
        if has_error:
            if "steps" in v and "error_at" not in v:
                err(f"{filepath}: {where} has steps and an error but no error_at")
            if not isinstance(error_at, int) or not 0 <= error_at < len(payloads):
                err(f"{filepath}: {where} error_at {error_at!r} names no payload")
                continue
            if error_at < len(payloads) - 1:
                err(f"{filepath}: {where} has steps after error_at")

        # Every payload a reader gets to must be JSON, except the one an
        # invalid_json vector says is not.
        last = error_at if has_error else len(payloads) - 1
        parsed = []
        for n in range(last + 1):
            try:
                parsed.append(_parse_payload(payloads[n]))
                if has_error and n == error_at and v["error"] == "invalid_json":
                    err(f"{filepath}: {where} says {names[n]} is not JSON, and it parses")
            except (ValueError, UnicodeDecodeError) as e:
                if not (has_error and n == error_at and v["error"] == "invalid_json"):
                    err(f"{filepath}: {where} {names[n]} does not parse: {e}")

        if has_resolved:
            if not isinstance(v["resolved"], dict):
                err(f"{filepath}: {where} resolved must be a JSON object, the catalog")
            elif "steps" not in v and parsed and parsed[0] != v["resolved"]:
                err(f"{filepath}: {where} resolves a single object to something other than its parse")

        profiles = v.get("profiles")
        if profiles is not None:
            if not isinstance(profiles, list) or not profiles:
                err(f"{filepath}: {where} profiles must be a non-empty list")
            else:
                if len(set(profiles)) != len(profiles):
                    err(f"{filepath}: {where} names a profile twice")
                for name in profiles:
                    if name not in CATALOG_PROFILES:
                        err(f"{filepath}: {where} names profile {name!r}, which the schema does not admit")
            if has_resolved and not v.get("tolerant"):
                err(f"{filepath}: {where} restricts a resolution to some consumers without marking it tolerant")
        if "tolerant" in v:
            if v["tolerant"] is not True:
                err(f"{filepath}: {where} tolerant is true or absent")
            if not has_resolved or profiles != ["reader"]:
                err(f"{filepath}: {where} is tolerant, so it resolves and binds the reader profile alone")


def _load_property_schema():
    path = os.path.join(REPO_ROOT, "schema", "property-vector.schema.json")
    with open(path) as f:
        schema = json.load(f)
    vector = schema["$defs"]["vector"]
    return (
        set(schema["properties"]),
        set(vector["properties"]),
        set(vector["properties"]["error"]["enum"]),
        set(schema["$defs"]["fields"]["properties"]),
    )


(PROPERTY_FILE_FIELDS, PROPERTY_VECTOR_FIELDS, PROPERTY_ERROR_CATEGORIES,
 PROPERTY_FIELDS) = _load_property_schema()
_PROPERTY_BOOL_FIELDS = {"S", "E", "I", "D", "B", "voice_activity"}


def _check_reading(filepath, where, reading):
    extra = set(reading) - PROPERTY_FIELDS
    if extra:
        err(f"{filepath}: {where} carries {sorted(extra)}, which the schema does not declare")
    for k, v in reading.items():
        if k in _PROPERTY_BOOL_FIELDS:
            if not isinstance(v, bool):
                err(f"{filepath}: {where}.{k} must be a boolean")
        elif k in PROPERTY_FIELDS and not (isinstance(v, str) and INT_PATTERN.match(v)):
            err(f"{filepath}: {where}.{k} = {v!r} must be a string of digits")


def validate_property_vectors(filepath, data):
    """Validate a property vector file: value form by parity, and the shape of decoded."""
    extra = set(data) - PROPERTY_FILE_FIELDS
    if extra:
        err(f"{filepath}: carries {sorted(extra)}, which the property schema does not declare")
    stem = os.path.splitext(os.path.basename(filepath))[0]
    if data.get("topic") != stem:
        err(f"{filepath}: topic {data.get('topic')!r} is not the file name {stem!r}")
    if "vectors" not in data:
        err(f"{filepath}: missing 'vectors' array")
        return

    validate_vector_ids(filepath, data["vectors"])

    for i, v in enumerate(data["vectors"]):
        where = f"[{i}] '{v.get('id', i)}'"
        extra = set(v) - PROPERTY_VECTOR_FIELDS
        if extra:
            err(f"{filepath}: {where} carries {sorted(extra)}, which the schema does not declare")
        if not isinstance(v.get("description"), str) or not v.get("description"):
            err(f"{filepath}: {where} needs a description citing the draft")

        ptype = v.get("property_type")
        if not isinstance(ptype, str) or not _KVP_TYPE_PATTERN.match(ptype):
            err(f"{filepath}: {where} property_type {ptype!r} must be lowercase hex, like '0x0d'")
            continue
        if int(ptype, 16) % 2 == 0:
            if "value_hex" in v or not (isinstance(v.get("value"), str) and INT_PATTERN.match(v["value"])):
                err(f"{filepath}: {where} has an even type, so it carries `value` in decimal digits and no `value_hex`")
        else:
            raw = v.get("value_hex")
            if "value" in v or not (isinstance(raw, str) and (raw == "" or HEX_PATTERN.match(raw))):
                err(f"{filepath}: {where} has an odd type, so it carries `value_hex` in lowercase hex and no `value`")

        has_decoded = "decoded" in v
        has_error = "error" in v
        if has_decoded == has_error:
            err(f"{filepath}: {where} must carry exactly one of decoded and error")
            continue
        if has_error:
            if v["error"] not in PROPERTY_ERROR_CATEGORIES:
                err(f"{filepath}: {where} claims error category {v['error']!r}, which the schema does not name")
            continue
        if "error_detail" in v:
            err(f"{filepath}: {where} decodes and still carries error_detail")

        d = v["decoded"]
        if not isinstance(d, dict):
            err(f"{filepath}: {where} decoded must be an object")
            continue
        if "ambiguous" in d:
            names = d["ambiguous"]
            if (set(d) != {"ambiguous"} or not isinstance(names, list) or len(names) < 2
                    or len(set(names)) != len(names) or not all(isinstance(n, str) for n in names)):
                err(f"{filepath}: {where} ambiguous stands alone and lists two or more distinct names")
            continue
        if not isinstance(d.get("name"), str):
            err(f"{filepath}: {where} decoded needs a name unless it is ambiguous")
        if "uninterpreted" in d:
            if d["uninterpreted"] is not True or set(d) != {"name", "uninterpreted"}:
                err(f"{filepath}: {where} uninterpreted is true and sits beside name alone")
        elif "candidates" in d:
            cands = d["candidates"]
            if set(d) != {"name", "candidates"} or not isinstance(cands, list) or len(cands) < 2:
                err(f"{filepath}: {where} candidates sits beside name alone and lists two or more readings")
                continue
            for n, c in enumerate(cands):
                if not isinstance(c, dict) or not c:
                    err(f"{filepath}: {where} candidates[{n}] must be a non-empty reading")
                else:
                    _check_reading(filepath, f"{where}.candidates[{n}]", c)
            if len({json.dumps(c, sort_keys=True) for c in cands}) != len(cands):
                err(f"{filepath}: {where} lists the same reading twice")
        else:
            _check_reading(filepath, f"{where}.decoded", {k: x for k, x in d.items() if k != "name"})


def _load_object_schema():
    path = os.path.join(REPO_ROOT, "schema", "object-vector.schema.json")
    with open(path) as f:
        schema = json.load(f)
    vector = schema["$defs"]["vector"]
    return (
        set(schema["properties"]),
        set(vector["properties"]),
        set(vector["properties"]["error"]["enum"]),
    )


OBJECT_FILE_FIELDS, OBJECT_VECTOR_FIELDS, OBJECT_ERROR_CATEGORIES = _load_object_schema()


def _top_level_boxes(raw):
    """Box types if the 32-bit sizes tile `raw` exactly, else None."""
    types, pos = [], 0
    while pos < len(raw):
        if len(raw) - pos < 8:
            return None
        size = struct.unpack(">I", raw[pos:pos + 4])[0]
        if size < 8 or pos + size > len(raw):
            return None
        types.append(raw[pos + 4:pos + 8].decode("latin-1"))
        pos += size
    return types


def _hex_bytes(filepath, where, holder, name):
    h = holder.get("hex") if isinstance(holder, dict) else None
    if not isinstance(holder, dict) or set(holder) != {"hex"} or not isinstance(h, str) \
            or not (h == "" or HEX_PATTERN.match(h)):
        err(f"{filepath}: {where} {name} must be {{\"hex\": ...}} in lowercase hex")
        return None
    return bytes.fromhex(h)


def validate_object_vectors(filepath, data):
    """Validate a CMSF object vector file: hex, exactly one of decoded and error, exact box sizes."""
    extra = set(data) - OBJECT_FILE_FIELDS
    if extra:
        err(f"{filepath}: carries {sorted(extra)}, which the object schema does not declare")
    stem = os.path.splitext(os.path.basename(filepath))[0]
    if data.get("topic") != stem:
        err(f"{filepath}: topic {data.get('topic')!r} is not the file name {stem!r}")
    if "vectors" not in data:
        err(f"{filepath}: missing 'vectors' array")
        return
    validate_vector_ids(filepath, data["vectors"])
    for i, v in enumerate(data["vectors"]):
        where = f"[{i}] '{v.get('id', i)}'"
        extra = set(v) - OBJECT_VECTOR_FIELDS
        if extra:
            err(f"{filepath}: {where} carries {sorted(extra)}, which the schema does not declare")
        if not isinstance(v.get("description"), str) or not v.get("description"):
            err(f"{filepath}: {where} needs a description citing the draft")
        if "first_in_group" in v and v["first_in_group"] is not True:
            err(f"{filepath}: {where} first_in_group is true or absent")
        obj = _hex_bytes(filepath, where, v.get("object"), "object")
        if "header" in v:
            hdr = _hex_bytes(filepath, where, v["header"], "header")
            if hdr is not None:
                types = _top_level_boxes(hdr)
                if types is None or "moov" not in types:
                    err(f"{filepath}: {where} header's boxes must tile it and include moov")
        has_decoded, has_error = "decoded" in v, "error" in v
        if has_decoded == has_error:
            err(f"{filepath}: {where} must carry exactly one of decoded and error")
            continue
        if has_error:
            if v["error"] not in OBJECT_ERROR_CATEGORIES:
                err(f"{filepath}: {where} claims error category {v['error']!r}, which the schema does not name")
            continue
        if "error_detail" in v:
            err(f"{filepath}: {where} decodes and still carries error_detail")
        d = v["decoded"]
        if not isinstance(d, dict):
            err(f"{filepath}: {where} decoded must be an object")
            continue
        if obj is not None and _top_level_boxes(obj) != d.get("boxes"):
            err(f"{filepath}: {where} object's boxes must tile it and be the ones decoded.boxes lists")
        if ("header" in v) != (d.get("track_id_in_header") is True):
            err(f"{filepath}: {where} track_id_in_header is true exactly when a header is given")


def _load_timeline_schema():
    path = os.path.join(REPO_ROOT, "schema", "timeline-vector.schema.json")
    with open(path) as f:
        schema = json.load(f)
    vector = schema["$defs"]["vector"]
    return (
        set(schema["properties"]),
        set(schema["properties"]["format"]["enum"]),
        set(vector["properties"]),
        set(vector["properties"]["error"]["enum"]),
    )


(TIMELINE_FILE_FIELDS, TIMELINE_FORMATS, TIMELINE_VECTOR_FIELDS,
 TIMELINE_ERROR_CATEGORIES) = _load_timeline_schema()
SAP_EVENT_TYPE = "org.ietf.moq.cmsf.sap"


def _is_int(x):
    return isinstance(x, int) and not isinstance(x, bool)


def _is_location(x):
    return isinstance(x, list) and len(x) == 2 and all(_is_int(n) and n >= 0 for n in x)


def _media_record(item):
    """A well-formed media timeline record as decoded lists it, or None."""
    if not (isinstance(item, list) and len(item) == 3 and _is_int(item[0])
            and _is_location(item[1]) and _is_int(item[2]) and item[2] >= 0):
        return None
    return {"media_time_ms": str(item[0]), "group_id": str(item[1][0]),
            "object_id": str(item[1][1]), "wallclock_ms": str(item[2])}


def _event_record(item):
    """A well-formed event timeline record, data as it is, or None."""
    if not isinstance(item, dict) or "data" not in item:
        return None
    keys = [k for k in ("t", "l", "m") if k in item]
    if len(keys) != 1:
        return None
    key, x = keys[0], item[keys[0]]
    out = {"index": key}
    if key == "l":
        if not _is_location(x):
            return None
        out["group_id"], out["object_id"] = str(x[0]), str(x[1])
    elif not _is_int(x) or (key == "t" and x < 0):
        return None
    else:
        out["wallclock_ms" if key == "t" else "media_time_ms"] = str(x)
    out["data"] = item["data"]
    return out


def _sap_record(item):
    """A well-formed SAP Type timeline record as decoded lists it, or None."""
    if not isinstance(item, dict) or set(item) != {"l", "data"} or not _is_location(item["l"]):
        return None
    d = item["data"]
    if not (isinstance(d, list) and len(d) == 2 and all(_is_int(n) for n in d) and 0 <= d[0] <= 3):
        return None
    return {"group_id": str(item["l"][0]), "object_id": str(item["l"][1]),
            "sap_type": str(d[0]), "ept_ms": str(d[1])}


def _expected_decoded(fmt, event_type, doc, entries):
    """What decoded must be for a parsed input, or None when it does not read."""
    if fmt == "template":
        if not (isinstance(doc, list) and len(doc) == 6 and _is_int(doc[0]) and _is_int(doc[1])
                and _is_location(doc[2]) and isinstance(doc[3], list) and len(doc[3]) == 2
                and all(_is_int(n) for n in doc[3]) and _is_int(doc[4]) and doc[4] >= 0
                and _is_int(doc[5]) and entries is not None):
            return None
        sm, dm, (sg, so), (dg, do), sw, dw = doc
        template = {
            "start_media_time_ms": sm, "delta_media_time_ms": dm,
            "start_group_id": sg, "start_object_id": so,
            "delta_group_id": dg, "delta_object_id": do,
            "start_wallclock_ms": sw, "delta_wallclock_ms": dw,
        }
        # MSF-01 7.4.1: mediaTime[n] = startMediaTime + (n * deltaMediaTime), and alike.
        records = [_media_record([sm + n * dm, [sg + n * dg, so + n * do], sw + n * dw])
                   for n in range(entries)]
        if None in records:
            return None
        return {"template": {k: str(x) for k, x in template.items()}, "records": records}
    if fmt == "mediatimeline":
        read = _media_record
    elif event_type is None:
        read = _event_record
    elif event_type == SAP_EVENT_TYPE:
        read = _sap_record
    else:
        return None
    if not isinstance(doc, list):
        return None
    records = [read(item) for item in doc]
    return None if None in records else {"records": records}


def validate_timeline_vectors(filepath, data):
    """Validate a timeline vector file: inputs that parse, and read, as their expectation says."""
    extra = set(data) - TIMELINE_FILE_FIELDS
    if extra:
        err(f"{filepath}: carries {sorted(extra)}, which the timeline schema does not declare")
    stem = os.path.splitext(os.path.basename(filepath))[0]
    if data.get("topic") != stem:
        err(f"{filepath}: topic {data.get('topic')!r} is not the file name {stem!r}")
    fmt = data.get("format")
    if fmt not in TIMELINE_FORMATS:
        err(f"{filepath}: format {fmt!r} is not one the schema names")
    event_type = data.get("event_type")
    if event_type is not None and (fmt != "eventtimeline" or not isinstance(event_type, str)):
        err(f"{filepath}: event_type belongs to an eventtimeline file only, as a string")
    if "vectors" not in data:
        err(f"{filepath}: missing 'vectors' array")
        return
    validate_vector_ids(filepath, data["vectors"])
    for i, v in enumerate(data["vectors"]):
        where = f"[{i}] '{v.get('id', i)}'"
        extra = set(v) - TIMELINE_VECTOR_FIELDS
        if extra:
            err(f"{filepath}: {where} carries {sorted(extra)}, which the schema does not declare")
        if not isinstance(v.get("description"), str) or not v.get("description"):
            err(f"{filepath}: {where} needs a description citing the draft")
        payload = v.get("input")
        if not isinstance(payload, dict) or set(payload) != {"text"} or not isinstance(payload["text"], str):
            err(f"{filepath}: {where} input must be {{\"text\": ...}}")
            continue
        try:
            doc, parses = json.loads(payload["text"]), True
        except json.JSONDecodeError:
            doc, parses = None, False
        has_decoded, has_error = "decoded" in v, "error" in v
        if has_decoded == has_error:
            err(f"{filepath}: {where} must carry exactly one of decoded and error")
            continue
        if ("entries" in v) != (fmt == "template" and has_decoded):
            err(f"{filepath}: {where} carries entries exactly when it is a template that decodes")
        if has_error:
            if v["error"] not in TIMELINE_ERROR_CATEGORIES:
                err(f"{filepath}: {where} claims error category {v['error']!r}, which the schema does not name")
            if parses == (v["error"] == "invalid_json"):
                err(f"{filepath}: {where} is invalid_json exactly when its text does not parse")
            continue
        if "error_detail" in v:
            err(f"{filepath}: {where} decodes and still carries error_detail")
        entries = v.get("entries")
        entries = int(entries) if isinstance(entries, str) and INT_PATTERN.match(entries) else None
        expected = _expected_decoded(fmt, event_type, doc, entries) if parses else None
        if expected is None:
            err(f"{filepath}: {where} decodes, but its input does not read as a {fmt} input")
        elif v["decoded"] != expected:
            err(f"{filepath}: {where} decoded is not what its input reads as: {json.dumps(expected)}")


def _dvi_quic(data, off):
    """Decode a QUIC varint at offset. Returns (value, bytes_consumed) or (None, 0)."""
    if off >= len(data):
        return None, 0
    b = data[off]
    p = b >> 6
    if p == 0:
        return b, 1
    elif p == 1:
        if off + 2 > len(data): return None, 0
        return ((b & 0x3f) << 8) | data[off + 1], 2
    elif p == 2:
        if off + 4 > len(data): return None, 0
        return struct.unpack('>I', bytes([b & 0x3f]) + data[off + 1:off + 4])[0], 4
    else:
        if off + 8 > len(data): return None, 0
        return struct.unpack('>Q', bytes([b & 0x3f]) + data[off + 1:off + 8])[0], 8

def _dvi_moqt(data, off):
    """Decode a MoQT varint (draft-17+ §1.4.1) at offset.

    The number of leading 1 bits in the first byte gives the length; the bits
    after the terminating 0 and any following bytes carry the value. 0xff is
    the 9-byte form, whose first byte is prefix only.
    """
    if off >= len(data):
        return None, 0
    b = data[off]
    if b == 0xff:
        if off + 9 > len(data): return None, 0
        return struct.unpack('>Q', data[off + 1:off + 9])[0], 9
    ones = 0
    while ones < 8 and b & (0x80 >> ones):
        ones += 1
    n = ones + 1
    if off + n > len(data): return None, 0
    value = b & ((1 << (8 - n)) - 1)
    for i in range(1, n):
        value = (value << 8) | data[off + i]
    return value, n

# Draft-17 replaced the RFC 9000 varint with its own encoding (§1.4.1).
_MOQT_VARINT_FIRST_DRAFT = 17

def _dvi_for(draft_id):
    """The varint decoder this draft uses."""
    try:
        n = int((draft_id or '')[len('draft'):])
    except ValueError:
        return _dvi_quic
    return _dvi_moqt if n >= _MOQT_VARINT_FIRST_DRAFT else _dvi_quic

# Drafts where control messages use varint length framing (draft00..draft10).
# From draft11 onward, all control messages use 16-bit BE length framing.
_VARINT_FRAMED_DRAFTS = {
    'draft00', 'draft01', 'draft02', 'draft03', 'draft04', 'draft05',
    'draft06', 'draft07', 'draft08', 'draft09', 'draft10',
}

def _extract_draft_id(filepath):
    """Extract draft id (e.g. 'draft12') from a file path."""
    parts = filepath.replace('\\', '/').split('/')
    for p in parts:
        if p.startswith('draft'):
            return p
    return None

def validate_message_framing(filepath, data, draft_id):
    """Validate that control message hex has correct type + length framing."""
    for i, v in enumerate(data['vectors']):
        if 'hex' not in v:
            continue
        if v.get('error') == 'incomplete':
            continue

        raw = bytes.fromhex(v['hex'])
        dvi = _dvi_for(draft_id)
        t, tl = dvi(raw, 0)
        if t is None:
            continue

        use_varint = draft_id in _VARINT_FRAMED_DRAFTS

        if use_varint:
            length, ll = dvi(raw, tl)
            if length is None:
                continue
            payload = raw[tl + ll:]
        else:
            if tl + 2 > len(raw):
                continue
            length = struct.unpack('>H', raw[tl:tl + 2])[0]
            payload = raw[tl + 2:]

        if len(payload) != length:
            desc = v.get('description', f'vector {i}')
            err(f"{filepath}: [{i}] '{desc}' declared length {length} but payload is {len(payload)} bytes")

def validate_manifest_consistency():
    """Check that manifest.json and meta.json files are consistent."""
    manifest_path = os.path.join(REPO_ROOT, "manifest.json")
    if not os.path.exists(manifest_path):
        err("manifest.json not found")
        return

    with open(manifest_path) as f:
        manifest = json.load(f)

    for spec_name, spec in manifest.get("specs", {}).items():
        for version in spec.get("versions", []):
            vid = version["id"]
            vpath = version["path"]
            meta_path = os.path.join(REPO_ROOT, vpath, "meta.json")

            if not os.path.exists(meta_path):
                err(f"manifest references {vpath}meta.json but file not found")
                continue

            with open(meta_path) as f:
                meta = json.load(f)

            if meta.get("id") != vid:
                err(f"{meta_path}: id '{meta.get('id')}' != manifest id '{vid}'")
            if meta.get("spec") != version.get("spec"):
                err(f"{meta_path}: spec '{meta.get('spec')}' != manifest spec '{version.get('spec')}'")

            req = meta.get("requires")
            if req is not None:
                specs = manifest.get("specs", {})
                ids = {v["id"] for v in specs.get(req.get("spec"), {}).get("versions", [])}
                if req.get("id") not in ids:
                    err(f"{meta_path}: requires {req!r}, which manifest.json does not list")

            # Categories and directories must match one to one.
            vdir = os.path.join(REPO_ROOT, vpath)
            listed = set(meta.get("categories", []))
            present = {
                e for e in os.listdir(vdir) if os.path.isdir(os.path.join(vdir, e))
            }
            for missing in sorted(listed - present):
                err(f"{meta_path}: lists category '{missing}', which has no directory")
            for unlisted in sorted(present - listed):
                err(f"{meta_path}: {vpath}{unlisted}/ is not a category it lists")
            for e in os.listdir(vdir):
                if os.path.isfile(os.path.join(vdir, e)) and e != "meta.json":
                    err(f"{vpath}{e}: sits outside every category directory")


def manifest_versions():
    """(spec key, version id, path) for every version manifest.json lists."""
    with open(os.path.join(REPO_ROOT, "manifest.json"), encoding="utf-8") as f:
        manifest = json.load(f)
    for spec_name, spec in manifest.get("specs", {}).items():
        for version in spec.get("versions", []):
            yield spec_name, version["id"], version["path"]


def load(filepath):
    relpath = os.path.relpath(filepath, REPO_ROOT)
    try:
        with open(filepath, encoding="utf-8") as f:
            return relpath, json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        err(f"{relpath}: JSON parse error: {e}")
        return relpath, None

# ---- Main ----

print("Validating test vectors...")
print()

# 1. Parse and validate all JSON vector files, spec by spec
print("Checking vector files and message framing...")
for spec_name, draft_id, vpath in manifest_versions():
    base = os.path.join(REPO_ROOT, vpath)

    for filepath in sorted(glob.glob(os.path.join(base, "codec", "**", "*.json"), recursive=True)):
        relpath, data = load(filepath)
        if data is None:
            continue
        validate_codec_vectors(relpath, data, draft_id)

        # Message framing: transport control messages only.
        if spec_name == "transport" and (
            os.sep + "messages" + os.sep in filepath or "/messages/" in filepath
        ):
            validate_message_framing(relpath, data, draft_id)

    for filepath in sorted(glob.glob(os.path.join(base, "catalog", "**", "*.json"), recursive=True)):
        relpath, data = load(filepath)
        if data is not None:
            validate_catalog_vectors(relpath, data)

    for filepath in sorted(glob.glob(os.path.join(base, "properties", "**", "*.json"), recursive=True)):
        relpath, data = load(filepath)
        if data is not None:
            validate_property_vectors(relpath, data)

    for filepath in sorted(glob.glob(os.path.join(base, "objects", "**", "*.json"), recursive=True)):
        relpath, data = load(filepath)
        if data is not None:
            validate_object_vectors(relpath, data)

    for filepath in sorted(glob.glob(os.path.join(base, "timeline", "**", "*.json"), recursive=True)):
        relpath, data = load(filepath)
        if data is not None:
            validate_timeline_vectors(relpath, data)

# 2. Validate meta.json files
print("Checking meta.json files...")
for spec_name, draft_id, vpath in manifest_versions():
    filepath = os.path.join(REPO_ROOT, vpath, "meta.json")
    if os.path.exists(filepath):
        load(filepath)

# 3. Check manifest consistency
print("Checking manifest consistency...")
validate_manifest_consistency()

# Summary
print()
if errors:
    print(f"FAILED: {len(errors)} error(s) found", file=sys.stderr)
    sys.exit(1)
else:
    print("PASSED: All checks passed")
