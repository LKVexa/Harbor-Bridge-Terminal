/* brrun -- the PA21 Language Studio's host for the BOTTLE ROCKET VM.
 *
 * The VM is only half a machine. The other half is the device and I/O service
 * architecture the package defines -- console, persistent block, monotonic
 * state, entropy, clock, mailbox, diagnostics -- and a VM created without a
 * host abstraction layer has none of it. A program that touches any service
 * on such a VM does not misbehave subtly: it traps BR_TRAP_HOST at the first
 * service call and stops, which is the whole distributed fabric refusing to
 * start.
 *
 * So this host stands that fabric up on the package's own memory adapter,
 * which backs every one of those devices in RAM: four guest storage objects,
 * a bounded console in and out, a monotonic counter with anti-rollback, a
 * seeded entropy source, a clock, and the device-call path. Nothing is
 * written to disk and no socket is opened -- the fabric lives entirely in
 * this process's memory, which is what lets it run anywhere the C core
 * compiles, with no filesystem and no OpenSSL.
 *
 * Two adapter kinds, and the difference is the point:
 *   memory         the RAM fabric, entropy seeded per run
 *   deterministic  the same fabric with the replay substitutes, so two runs
 *                  of one image produce identical bytes
 *
 * The state of the fabric after the run is reported with the result: what the
 * guest wrote to the console, what sits in each storage object, where the
 * monotonic counter stands. A run whose effects nobody can see is a run
 * nobody can check.
 *
 * Raw image loading is the runtime's DEVELOPMENT path and requires
 * -DBR_DEVELOPMENT=1, exactly as the package's own test binaries do. The
 * studio records that in every result rather than implying a production trust
 * chain it has not provisioned.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "brvm.h"
#include "br_adapters.h"
#ifdef BR_STUDIO_SIGNING
#include <openssl/evp.h>
#endif

#ifdef BR_STUDIO_SIGNING
/* ---- verifying a signed image on the RAM fabric ---------------------------
 *
 * The memory adapter answers BR_EUNSUPPORTED for signature verification, so a
 * signed image cannot be loaded on it: the VM refuses, correctly, rather than
 * pretending to have checked. The package's own signing path uses the POSIX
 * adapter, which keeps its state in files -- so the choice looked like signed
 * images OR the RAM fabric.
 *
 * It is not, because the HAL is a table of function pointers. This is the
 * memory HAL with exactly one entry replaced: an Ed25519 verify. Everything
 * else -- storage, console, entropy, clock, mailbox -- is still the package's
 * own RAM implementation, byte for byte. The image is verified by the VM,
 * through the HAL, before a single instruction executes.
 */
static int studio_verify(void *x, const uint8_t *key, size_t kn,
                         const uint8_t *msg, size_t mn,
                         const uint8_t *sig, size_t sn) {
    EVP_PKEY *k = NULL;
    EVP_MD_CTX *c = NULL;
    int ok = 0;
    (void)x;
    if (!key || kn != 32u || !msg || !sig || sn != 64u) return BR_EINVAL;
    k = EVP_PKEY_new_raw_public_key(EVP_PKEY_ED25519, NULL, key, 32);
    c = EVP_MD_CTX_new();
    if (k && c && EVP_DigestVerifyInit(c, NULL, NULL, NULL, k) == 1)
        ok = (EVP_DigestVerify(c, sig, sn, msg, mn) == 1);
    EVP_MD_CTX_free(c);
    EVP_PKEY_free(k);
    return ok ? 0 : BR_ESIGNATURE;
}
#endif

static int load_file(const char *p, uint8_t **out, size_t *n) {
    FILE *f = fopen(p, "rb");
    if (!f) return -1;
    if (fseek(f, 0, SEEK_END)) { fclose(f); return -1; }
    long z = ftell(f);
    if (z < 0 || z > (1 << 20)) { fclose(f); return -1; }
    rewind(f);
    uint8_t *b = (uint8_t *)malloc((size_t)z ? (size_t)z : 1);
    if (!b) { fclose(f); return -1; }
    if (fread(b, 1, (size_t)z, f) != (size_t)z) { free(b); fclose(f); return -1; }
    fclose(f);
    *out = b; *n = (size_t)z;
    return 0;
}

/* The machine status is not the error code. A unit that ends by yielding
   returns BR_OK -- nothing went wrong -- while the machine itself is
   SUSPENDED rather than HALTED, and only one of those two facts was being
   reported. Both are, now. */
static const char *machine_status_name(unsigned s) {
    switch (s) {
    case BR_READY:     return "READY";
    case BR_RUNNING:   return "RUNNING";
    case BR_HALTED:    return "HALTED";
    case BR_TRAPPED:   return "TRAPPED";
    case BR_CANCELLED: return "CANCELLED";
    case BR_SUSPENDED: return "SUSPENDED";
    case BR_STOPPED:   return "STOPPED";
    default:           return "UNKNOWN";
    }
}

static void put_hex(const uint8_t *b, size_t n, size_t cap) {
    size_t i, m = n < cap ? n : cap;
    for (i = 0; i < m; i++) printf("%02x", b[i]);
}

/* a JSON string: printable bytes kept, everything else escaped */
static void put_text(const uint8_t *b, size_t n) {
    size_t i;
    for (i = 0; i < n; i++) {
        unsigned c = b[i];
        if (c == '"' || c == '\\') printf("\\%c", (int)c);
        else if (c >= 0x20 && c < 0x7f) putchar((int)c);
        else printf("\\u%04x", c);
    }
}

static int hexval(int c) {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}

static size_t unhex(const char *s, uint8_t *out, size_t cap) {
    size_t k = 0;
    while (s && s[0] && s[1] && k < cap) {
        int hi = hexval(s[0]), lo = hexval(s[1]);
        if (hi < 0 || lo < 0) break;
        out[k++] = (uint8_t)((hi << 4) | lo);
        s += 2;
    }
    return k;
}

/* ---- the fabric's state, between runs -------------------------------------
 *
 * The device fabric lives in RAM, which is what makes it portable -- and it
 * means that without this, a persistent block device is not persistent and a
 * monotonic counter is not monotonic: every run starts from zero, so a program
 * can never read back what an earlier run wrote, and the anti-rollback device
 * has nothing to roll back from.
 *
 * So the host can carry the fabric across runs in one small file: the two
 * control objects, the six storage objects, and the three counters. The image
 * staging area is deliberately not carried -- it is the update path's scratch,
 * not the guest's state. Whether to carry anything at all is the caller's
 * decision, never a default, because a run that silently depends on a previous
 * one is not reproducible.
 */
#define STATE_MAGIC "PA21FAB1"
#define STATE_VERSION 1u

static void put_u64(FILE *f, uint64_t v) {
    int i;
    for (i = 0; i < 8; i++) fputc((int)((v >> (8 * i)) & 0xff), f);
}

static uint64_t get_u64(const uint8_t *p) {
    uint64_t v = 0; int i;
    for (i = 7; i >= 0; i--) v = (v << 8) | p[i];
    return v;
}

static const unsigned STATE_IDS[8] = {
    BR_STORAGE_CONTROL0, BR_STORAGE_CONTROL1,
    BR_STORAGE_OBJECT0 + 0u, BR_STORAGE_OBJECT0 + 1u,
    BR_STORAGE_OBJECT0 + 2u, BR_STORAGE_OBJECT0 + 3u,
    BR_STORAGE_STATE0, BR_STORAGE_STATE1
};

static uint8_t *state_slot(br_memory_ctx *c, unsigned id, size_t *cap) {
    if (id < 2u) { *cap = 512u; return c->control[id]; }
    if (id >= BR_STORAGE_OBJECT0 && id < BR_STORAGE_OBJECTS) {
        *cap = BR_STORAGE_OBJECT_BYTES;
        return c->object[id - BR_STORAGE_OBJECT0];
    }
    return NULL;
}

/* returns 0 when a state file was read, 1 when there was none, -1 on damage */
static int state_load(const char *path, br_memory_ctx *c) {
    uint8_t *b = NULL; size_t n = 0, off, i;
    if (load_file(path, &b, &n)) return 1;
    if (n < 32 || memcmp(b, STATE_MAGIC, 8)) { free(b); return -1; }
    c->monotonic = get_u64(b + 12);
    c->clock = get_u64(b + 20);
    off = 28;
    for (i = 0; i < 8; i++) {
        size_t cap = 0, len;
        uint8_t *slot = state_slot(c, STATE_IDS[i], &cap);
        if (off + 8 > n) break;
        len = (size_t)get_u64(b + off);
        off += 8;
        if (off + len > n || !slot || len > cap) { free(b); return -1; }
        memcpy(slot, b + off, len);
        if (len < cap) memset(slot + len, 0, cap - len);
        c->length[STATE_IDS[i]] = len;
        off += len;
    }
    free(b);
    return 0;
}

static int state_save(const char *path, br_memory_ctx *c) {
    FILE *f = fopen(path, "wb");
    size_t i;
    int k;
    if (!f) return -1;
    fwrite(STATE_MAGIC, 1, 8, f);                            /* 0..7   */
    for (k = 0; k < 4; k++)                                  /* 8..11  */
        fputc((int)((STATE_VERSION >> (8 * k)) & 0xffu), f);
    put_u64(f, c->monotonic);                                /* 12..19 */
    put_u64(f, c->clock);                                    /* 20..27 */
    for (i = 0; i < 8; i++) {                                /* 28..   */
        size_t cap = 0;
        const uint8_t *slot = state_slot(c, STATE_IDS[i], &cap);
        size_t len = slot ? c->length[STATE_IDS[i]] : 0;
        if (len > cap) len = cap;
        put_u64(f, (uint64_t)len);
        if (len) fwrite(slot, 1, len, f);
    }
    fclose(f);
    return 0;
}

int main(int argc, char **argv) {
    const char *image, *adapter = "memory", *console_in = NULL;
    const char *mailbox_in = NULL, *state_path = NULL, *key_path = NULL;
    int state_read = 1, state_written = 0, require_signature = 0;
    int trace = 0;
    uint32_t budget = 4096;
    uint64_t seed = 20260816u;
    int want_devices = 0, i;

    if (argc >= 2 && !strcmp(argv[1], "selftest")) {
        int rc = br_core_selftest();
        printf("{\"selftest\":%s,\"rc\":%d}\n", rc ? "\"FAIL\"" : "\"PASS\"", rc);
        return rc ? 1 : 0;
    }
    if (argc < 3 || strcmp(argv[1], "run")) {
        fprintf(stderr,
            "brrun run IMAGE [--budget N] [--adapter memory|deterministic]\n"
            "                [--seed N] [--console-in HEX] [--devices]\n"
            "                [--mailbox-in HEX] [--state FILE]\n"
            "                [--verify-key PUB] [--require-signature]\n"
            "                [--trace [N]]\n"
            "brrun selftest\n");
        return 2;
    }
    image = argv[2];
    for (i = 3; i < argc; i++) {
        if (!strcmp(argv[i], "--budget") && i + 1 < argc) {
            long b = strtol(argv[++i], NULL, 10);
            if (b > 0 && b <= 100000000L) budget = (uint32_t)b;
        } else if (!strcmp(argv[i], "--adapter") && i + 1 < argc) {
            adapter = argv[++i];
        } else if (!strcmp(argv[i], "--seed") && i + 1 < argc) {
            seed = strtoull(argv[++i], NULL, 10);
        } else if (!strcmp(argv[i], "--console-in") && i + 1 < argc) {
            console_in = argv[++i];
        } else if (!strcmp(argv[i], "--mailbox-in") && i + 1 < argc) {
            mailbox_in = argv[++i];
        } else if (!strcmp(argv[i], "--state") && i + 1 < argc) {
            state_path = argv[++i];
        } else if (!strcmp(argv[i], "--verify-key") && i + 1 < argc) {
            key_path = argv[++i];
        } else if (!strcmp(argv[i], "--require-signature")) {
            require_signature = 1;
        } else if (!strcmp(argv[i], "--trace")) {
            trace = 256;
            if (i + 1 < argc && argv[i + 1][0] != '-') {
                long t = strtol(argv[++i], NULL, 10);
                if (t > 0 && t <= 100000L) trace = (int)t;
            }
        } else if (!strcmp(argv[i], "--devices")) {
            want_devices = 1;
        } else if (argv[i][0] == '-') {
            fprintf(stderr, "{\"error\":\"unknown option %s\"}\n", argv[i]);
            return 2;
        }
    }
    int deterministic = !strcmp(adapter, "deterministic");
    if (!deterministic && strcmp(adapter, "memory")) {
        fprintf(stderr, "{\"error\":\"adapter must be memory or deterministic\"}\n");
        return 2;
    }

    uint8_t *d = NULL; size_t n = 0;
    if (load_file(image, &d, &n)) {
        fprintf(stderr, "{\"error\":\"image not readable\"}\n");
        return 3;
    }

    /* ---- the fabric, in RAM ------------------------------------------ */
    br_vm v;
    br_memory_ctx ctx;
    br_memory_adapter_init(&ctx, deterministic ? BR_ADAPTER_DETERMINISTIC
                                               : BR_ADAPTER_MEMORY, seed);
    if (console_in) {
        uint8_t buf[256];
        size_t k = unhex(console_in, buf, sizeof(buf));
        br_memory_adapter_console(&ctx, buf, k);
    }
    if (state_path) {
        state_read = state_load(state_path, &ctx);
        if (state_read < 0) {
            free(d);
            fprintf(stderr, "{\"error\":\"the state file is not a "
                            "PA21FAB1 fabric state\"}\n");
            return 5;
        }
    }
    br_device devices[2];
    devices[0].id = BR_DEVICE_NETWORK;     devices[0].rc_ = BR_CAP_SERVICE;
    devices[1].id = BR_DEVICE_WALL_CLOCK;  devices[1].rc_ = BR_CAP_SERVICE;

    br_vm_config cfg;
    cfg.ib_ = 256;
    cfg.sb_ = 4096;
    cfg.hb_ = 256;
    cfg.pa_ = BR_CAP_ALL;
    cfg.devices = want_devices ? devices : NULL;
    cfg.dn_ = want_devices ? (size_t)2 : (size_t)0;

    /* the fabric's HAL, with a verifier spliced in when one was asked for */
    br_hal hal = deterministic ? br_hal_deterministic : br_hal_memory;
    uint8_t pubkey[32];
    int have_key = 0;
    if (key_path) {
        uint8_t *kb = NULL; size_t kn = 0;
        if (load_file(key_path, &kb, &kn) || kn != 32u) {
            free(kb); free(d);
            fprintf(stderr, "{\"error\":\"the verification key must be 32 "
                            "raw bytes\",\"path\":\"%s\"}\n", key_path);
            return 7;
        }
        memcpy(pubkey, kb, 32);
        free(kb);
        have_key = 1;
#ifdef BR_STUDIO_SIGNING
        hal.vs_ = studio_verify;
#else
        free(d);
        fprintf(stderr, "{\"error\":\"this runner was built without "
                        "signature support; install a studio on a host with "
                        "OpenSSL headers\"}\n");
        return 7;
#endif
    }

    if (br_vm_create(&v, &hal, &ctx)
        || br_vm_initialize(&v)
        || br_vm_configure(&v, &cfg)) {
        free(d);
        fprintf(stderr, "{\"error\":\"the VM would not stand up on this "
                        "adapter\",\"adapter\":\"%s\"}\n", adapter);
        return 4;
    }
    v.iv_ = 0;
    /* A host-delivered message, before the guest runs: MAILBOX_GET reads
       host-owned messages only, so without this half the mailbox device is
       unreachable from a program and the service can only ever return 0. */
    uint8_t mbin[BR_MAILBOX_BYTES];
    size_t mbin_n = 0;
    if (mailbox_in) {
        mbin_n = unhex(mailbox_in, mbin, sizeof(mbin));
        if (br_vm_mailbox_host_put(&v, mbin, mbin_n)) {
            free(d);
            fprintf(stderr, "{\"error\":\"the mailbox would not take that "
                            "message\",\"bytes\":%zu}\n", mbin_n);
            return 6;
        }
    }
    int rc = br_image_load(&v, d, n, have_key ? pubkey : NULL,
                           have_key ? (size_t)32 : (size_t)0,
                           require_signature);
    int loaded = (rc == 0);
    /* A trace is the run itself, one instruction at a time, recorded. The VM
       exposes a step, so nothing here simulates anything: the same executor
       runs, and the trace is what it did. */
    unsigned *tr_ip = NULL; unsigned char *tr_op = NULL;
    unsigned *tr_st = NULL;
    int tr_n = 0;
    if (loaded && trace) {
        tr_ip = (unsigned *)calloc((size_t)trace, sizeof(unsigned));
        tr_op = (unsigned char *)calloc((size_t)trace, 1);
        tr_st = (unsigned *)calloc((size_t)trace, sizeof(unsigned));
        if (!tr_ip || !tr_op || !tr_st) { trace = 0; }
    }
    if (loaded && trace) {
        rc = br_vm_start(&v);
        while (!rc && tr_n < trace && v.status == BR_RUNNING) {
            unsigned ip = v.ip;
            if (ip < v.cc_) {
                tr_ip[tr_n] = ip;
                tr_op[tr_n] = (unsigned char)v.code[ip].op;
            }
            rc = br_vm_step(&v);
            tr_st[tr_n] = v.status;
            tr_n++;
        }
    } else if (loaded) {
        rc = br_vm_run(&v, budget);
    }

    /* What the host receives afterwards: a guest-owned message is pending
       host receive, and taking it is what a host does. Its length is
       captured first, because receiving it clears the slot. */
    size_t mail_pending = (size_t)v.ml_;
    uint8_t mbout[BR_MAILBOX_BYTES];
    size_t mbout_n = 0;
    br_vm_mailbox_host_get(&v, mbout, sizeof(mbout), &mbout_n);

    printf("{\"loaded\":%s,\"rc\":%d,\"status\":%u,\"status_name\":\"%s\","
           "\"machine_status\":\"%s\",\"trap\":%u,\"registers\":{",
           loaded ? "true" : "false", rc, v.status,
           br_status_name(br_vm_status_code(&v)),
           machine_status_name((unsigned)v.status), v.trap);
    /* Every register, not the first four: a service call writes its result
       into whatever register the row named, and a writer that cannot see
       R7 cannot tell a transfer of zero bytes from one it never made. */
    for (i = 0; i < (int)BR_REGS; i++)
        printf("%s\"R%d\":%llu", i ? "," : "", i,
               (unsigned long long)br_vm_reg(&v, (unsigned)i)[0]);
    printf("},\"bytes\":%zu,\"budget\":%u,"
           "\"execution_mode\":\"%s\",\"adapter\":\"%s\","
           "\"backend\":\"RAM\",\"seed\":%llu,\"extension_devices\":%d,"
           "\"signature\":{\"key\":%s,\"required\":%s,\"image_signed\":%s,"
           "\"verified\":%s},",
           n, budget,
           have_key ? (loaded ? "SIGNED_VERIFIED" : "SIGNATURE_REFUSED")
                    : "DEVELOPMENT_RAW",
           adapter, (unsigned long long)seed, want_devices ? 2 : 0,
           have_key ? "true" : "false",
           require_signature ? "true" : "false",
           (n > 7 && (d[7] & BR_IMAGE_FLAG_SIGNED)) ? "true" : "false",
           (have_key && loaded && n > 7 && (d[7] & BR_IMAGE_FLAG_SIGNED))
               ? "true" : "false");
    /* The first bytes of guest memory, so a buffer service can be seen to
       have landed something rather than merely reported that it did. */
    printf("\"memory_head_hex\":\"");
    put_hex(v.memory, sizeof(v.memory) < 64u ? sizeof(v.memory) : 64u, 64);
    printf("\",");

    /* ---- what the fabric holds afterwards ---------------------------- */
    printf("\"fabric\":{\"console_out_bytes\":%zu,\"console_out_text\":\"",
           ctx.console_out_n);
    put_text(ctx.console_out, ctx.console_out_n);
    printf("\",\"console_out_hex\":\"");
    put_hex(ctx.console_out, ctx.console_out_n, 128);
    printf("\",\"console_in_consumed\":%zu,\"monotonic\":%llu,\"clock\":%llu,"
           "\"device_calls\":%u,\"panic_code\":%d,\"mailbox_bytes\":%zu,"
           "\"mailbox_delivered\":%zu,\"mailbox_received_bytes\":%zu,"
           "\"mailbox_received_hex\":\"",
           ctx.console_in_pos, (unsigned long long)ctx.monotonic,
           (unsigned long long)ctx.clock, ctx.dc_s, ctx.panic_code,
           mail_pending, mbin_n, mbout_n);
    put_hex(mbout, mbout_n, BR_MAILBOX_BYTES);
    printf("\",\"storage\":[");
    for (i = 0; i < (int)BR_STORAGE_GUEST_OBJECTS; i++) {
        unsigned idx = (unsigned)BR_STORAGE_OBJECT0 + (unsigned)i;
        printf("%s{\"object\":%d,\"framed_bytes\":%zu,\"head_hex\":\"",
               i ? "," : "", i, ctx.length[idx]);
        put_hex(ctx.object[i], ctx.length[idx], 32);
        printf("\"}");
    }
    printf("]},");
    /* Why it stopped, from the VM's own records: the trap frame names the
       instruction, and the diagnostics ring holds what the VM logged on the
       way there. A trap code alone tells you the kind of failure and nothing
       about where. */
    {
        br_trap_frame tf;
        int have_tf = (br_vm_trap_frame(&v, &tf) == 0);
        printf("\"fault\":{\"have_frame\":%s", have_tf ? "true" : "false");
        if (have_tf)
            printf(",\"trap\":%u,\"ip\":%u,\"opcode\":%u,\"status\":%u,"
                   "\"flags\":%u",
                   tf.trap, tf.ip, (unsigned)tf.opcode, (unsigned)tf.status,
                   tf.flags);
        printf("},\"diagnostics\":[");
        {
            int k, first = 1;
            for (k = 0; k < (int)BR_DIAG_RECORDS; k++) {
                if (!v.diag[k].seq && !v.diag[k].event) continue;
                printf("%s{\"seq\":%u,\"event\":%u,\"trap\":%u,\"ip\":%u,"
                       "\"opcode\":%u,\"status\":%u}",
                       first ? "" : ",", v.diag[k].seq,
                       (unsigned)v.diag[k].event, (unsigned)v.diag[k].trap,
                       v.diag[k].ip, (unsigned)v.diag[k].opcode,
                       (unsigned)v.diag[k].status);
                first = 0;
            }
        }
        printf("],\"trace\":[");
        {
            int k;
            for (k = 0; k < tr_n; k++)
                printf("%s{\"step\":%d,\"ip\":%u,\"opcode\":%u,"
                       "\"status\":%u}",
                       k ? "," : "", k, tr_ip[k], (unsigned)tr_op[k],
                       tr_st[k]);
        }
        printf("],\"traced\":%s,", trace ? "true" : "false");
    }
    free(tr_ip); free(tr_op); free(tr_st);
    if (state_path && state_save(state_path, &ctx) == 0) state_written = 1;
    printf("\"state\":{\"path\":%s,\"carried_in\":%s,\"written\":%s}}\n",
           state_path ? "\"kept\"" : "null",
           state_path && state_read == 0 ? "true" : "false",
           state_written ? "true" : "false");

    br_vm_destroy(&v);
    free(d);
    return rc ? 1 : 0;
}
