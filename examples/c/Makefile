CC = gcc
CFLAGS = -Wall -Wextra -std=c99

test_codec_vectors: test_codec_vectors.c
	$(CC) $(CFLAGS) -o $@ $< -lcjson

.PHONY: test
test: test_codec_vectors
	./test_codec_vectors

.PHONY: clean
clean:
	rm -f test_codec_vectors
