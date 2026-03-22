import { describe, it, expect } from 'vitest';
import vectors from '@moqtap/test-vectors/transport/draft14/codec/messages/subscribe.json';
import { decodeMessage, encodeMessage } from '@moqtap/codec';

function hexToBytes(hex: string): Uint8Array {
  const bytes = new Uint8Array(hex.length / 2);
  for (let i = 0; i < hex.length; i += 2) {
    bytes[i / 2] = parseInt(hex.substring(i, i + 2), 16);
  }
  return bytes;
}

function bytesToHex(bytes: Uint8Array): string {
  return Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('');
}

describe(`codec: ${vectors.message_type}`, () => {
  for (const v of vectors.vectors) {
    it(v.description, () => {
      const bytes = hexToBytes(v.hex);
      const isCanonical = v.canonical ?? true;

      if (v.decoded) {
        // Decode direction: always test
        const result = decodeMessage(bytes);
        expect(result).toEqual(v.decoded);

        // Encode direction: only for canonical vectors
        if (isCanonical) {
          const reEncoded = encodeMessage(result);
          expect(bytesToHex(reEncoded)).toBe(v.hex);
        }
      } else if (v.error) {
        expect(() => decodeMessage(bytes)).toThrow();
      }
    });
  }
});
