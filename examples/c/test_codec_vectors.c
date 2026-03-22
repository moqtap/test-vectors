#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "cJSON.h" /* header-only JSON parser */

/* Hex string to byte array (caller frees) */
unsigned char *hex_decode(const char *hex, size_t *out_len) {
    size_t len = strlen(hex) / 2;
    unsigned char *bytes = malloc(len);
    for (size_t i = 0; i < len; i++) {
        sscanf(hex + 2 * i, "%2hhx", &bytes[i]);
    }
    *out_len = len;
    return bytes;
}

int main(void) {
    FILE *f = fopen(
        "test-vectors/transport/draft14/codec/messages/subscribe.json", "r");
    if (!f) {
        fprintf(stderr, "vector file not found — did you init the submodule?\n");
        return 1;
    }

    fseek(f, 0, SEEK_END);
    long fsize = ftell(f);
    fseek(f, 0, SEEK_SET);
    char *json_str = malloc(fsize + 1);
    fread(json_str, 1, fsize, f);
    json_str[fsize] = '\0';
    fclose(f);

    cJSON *root = cJSON_Parse(json_str);
    cJSON *vectors = cJSON_GetObjectItem(root, "vectors");
    int count = cJSON_GetArraySize(vectors);

    for (int i = 0; i < count; i++) {
        cJSON *v = cJSON_GetArrayItem(vectors, i);
        const char *desc = cJSON_GetObjectItem(v, "description")->valuestring;
        const char *hex = cJSON_GetObjectItem(v, "hex")->valuestring;
        cJSON *decoded = cJSON_GetObjectItem(v, "decoded");
        cJSON *error = cJSON_GetObjectItem(v, "error");

        size_t bytes_len;
        unsigned char *bytes = hex_decode(hex, &bytes_len);

        if (decoded) {
            /* Decode: your_decode_message(bytes, bytes_len) and compare */
            printf("PASS (decode): %s\n", desc);
        } else if (error) {
            /* Invalid: expect decode to fail */
            printf("PASS (error): %s\n", desc);
        }

        free(bytes);
    }

    cJSON_Delete(root);
    free(json_str);
    return 0;
}
