import json
from pathlib import Path


def test_subscribe_vectors():
    path = Path("test-vectors/transport/draft14/codec/messages/subscribe.json")
    file = json.loads(path.read_text())

    for v in file["vectors"]:
        wire_bytes = bytes.fromhex(v["hex"])
        is_canonical = v.get("canonical", True)

        if "decoded" in v:
            result = decode_message(wire_bytes)  # your library
            assert result == v["decoded"], f"decode failed: {v['description']}"
            if is_canonical:
                re_encoded = encode_message(result)
                assert re_encoded.hex() == v["hex"], f"encode failed: {v['description']}"
        elif "error" in v:
            try:
                decode_message(wire_bytes)
                assert False, f"expected error for: {v['description']}"
            except DecodeError:
                pass
