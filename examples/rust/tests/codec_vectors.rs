use serde::Deserialize;
use std::fs;

#[derive(Deserialize)]
struct VectorFile {
    message_type: String,
    vectors: Vec<Vector>,
}

#[derive(Deserialize)]
struct Vector {
    description: String,
    hex: String,
    decoded: Option<serde_json::Value>,
    error: Option<String>,
    canonical: Option<bool>,
}

#[test]
fn test_subscribe_vectors() {
    let data = fs::read_to_string(
        "test-vectors/transport/draft14/codec/messages/subscribe.json",
    )
    .expect("vector file not found — did you init the submodule?");
    let file: VectorFile = serde_json::from_str(&data).unwrap();

    for v in &file.vectors {
        let bytes = hex::decode(&v.hex).unwrap();
        let is_canonical = v.canonical.unwrap_or(true);

        if let Some(ref decoded) = v.decoded {
            // Decode direction: always test
            let result = moqtap_codec::decode_message(&bytes).unwrap();
            assert_eq!(
                serde_json::to_value(&result).unwrap(),
                *decoded,
                "decode failed: {}",
                v.description
            );

            // Encode direction: only for canonical vectors
            if is_canonical {
                let re_encoded = moqtap_codec::encode_message(&result);
                assert_eq!(
                    hex::encode(&re_encoded),
                    v.hex,
                    "encode failed: {}",
                    v.description
                );
            }
        } else if let Some(ref _error) = v.error {
            assert!(
                moqtap_codec::decode_message(&bytes).is_err(),
                "expected error for: {}",
                v.description
            );
        }
    }
}
