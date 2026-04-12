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

def check_protocol_ints(obj, path, filename, draft_id=None):
    """Recursively check that protocol integer fields are strings."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in PROTOCOL_INT_FIELDS:
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

        # Check protocol integers in decoded
        if has_decoded:
            check_protocol_ints(v["decoded"], f"[{i}].decoded", filepath, draft_id)

def _dvi(data, off):
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
        t, tl = _dvi(raw, 0)
        if t is None:
            continue

        use_varint = draft_id in _VARINT_FRAMED_DRAFTS

        if use_varint:
            length, ll = _dvi(raw, tl)
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

# ---- Main ----

print("Validating test vectors...")
print()

# 1. Parse and validate all JSON vector files
print("Checking vector files and message framing...")
for filepath in glob.glob(os.path.join(REPO_ROOT, "transport/**/codec/**/*.json"), recursive=True):
    relpath = os.path.relpath(filepath, REPO_ROOT)
    try:
        with open(filepath) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        err(f"{relpath}: JSON parse error: {e}")
        continue

    draft_id = _extract_draft_id(relpath)
    validate_codec_vectors(relpath, data, draft_id)

    # Check message framing (only for control messages, not data streams or varint)
    if os.sep + "messages" + os.sep in filepath or "/messages/" in filepath:
        if draft_id:
            validate_message_framing(relpath, data, draft_id)

# 2. Validate meta.json files
print("Checking meta.json files...")
for filepath in glob.glob(os.path.join(REPO_ROOT, "transport/*/meta.json"), recursive=True):
    if ".git" in filepath:
        continue
    relpath = os.path.relpath(filepath, REPO_ROOT)
    try:
        with open(filepath) as f:
            json.load(f)
    except json.JSONDecodeError as e:
        err(f"{relpath}: JSON parse error: {e}")

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
