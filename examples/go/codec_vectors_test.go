package vectors_test

import (
	"encoding/hex"
	"encoding/json"
	"os"
	"testing"
)

type VectorFile struct {
	MessageType string   `json:"message_type"`
	Vectors     []Vector `json:"vectors"`
}

type Vector struct {
	Description string           `json:"description"`
	Hex         string           `json:"hex"`
	Decoded     *json.RawMessage `json:"decoded,omitempty"`
	Error       *string          `json:"error,omitempty"`
	Canonical   *bool            `json:"canonical,omitempty"`
}

func TestSubscribeVectors(t *testing.T) {
	data, err := os.ReadFile(
		"test-vectors/transport/draft14/codec/messages/subscribe.json",
	)
	if err != nil {
		t.Fatal("vector file not found — did you init the submodule?")
	}
	var file VectorFile
	json.Unmarshal(data, &file)

	for _, v := range file.Vectors {
		t.Run(v.Description, func(t *testing.T) {
			bytes, _ := hex.DecodeString(v.Hex)
			isCanonical := v.Canonical == nil || *v.Canonical

			if v.Decoded != nil {
				// Decode direction: always test
				_ = bytes // result := yourlib.DecodeMessage(bytes)
				if isCanonical {
					// Encode direction: only for canonical vectors
					// reEncoded := yourlib.EncodeMessage(result)
				}
			} else if v.Error != nil {
				// Invalid case: expect error
				_ = bytes // _, err := yourlib.DecodeMessage(bytes)
			}
		})
	}
}
