/* MC-051 / MC-055 / MC-090 — adversarial escape probes run *inside* the sandbox.
 * Each probe attempts one attack and prints "name=BLOCKED" or "name=ESCAPED".
 * The harness asserts every probe reports BLOCKED.  Build: cc -O2 -o escape_probes escape_probes.c
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/ptrace.h>
#include <sys/resource.h>
#include <sys/socket.h>
#include <sys/syscall.h>
#include <sys/prctl.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>

static void r(const char *n, int escaped) { printf("%s=%s\n", n, escaped ? "ESCAPED" : "BLOCKED"); }

int main(int argc, char **argv) {
    const char *which = argc > 1 ? argv[1] : "all";
    int all = !strcmp(which, "all");
    setvbuf(stdout, NULL, _IONBF, 0);
    if (all || !strcmp(which, "ptrace")) r("ptrace_traceme", ptrace(PTRACE_TRACEME, 0, 0, 0) == 0);
    if (all || !strcmp(which, "socket")) { int s = socket(AF_INET, SOCK_STREAM, 0); r("socket_inet", s >= 0); }
    if (all || !strcmp(which, "mount")) r("mount_tmpfs", mount("x", "/mnt", "tmpfs", 0, 0) == 0);
    if (all || !strcmp(which, "unshare")) r("unshare_user", unshare(CLONE_NEWUSER) == 0);
    if (all || !strcmp(which, "setuid")) r("setuid_0_regain", setuid(0) == 0 && geteuid() == 0 && prctl(PR_CAPBSET_READ, 21) == 1);
    if (all || !strcmp(which, "bpf")) r("bpf", syscall(SYS_bpf, 0, 0, 0) >= 0 || errno != EPERM);
    if (all || !strcmp(which, "keyctl")) r("keyctl", syscall(SYS_keyctl, 0, 0, 0) >= 0 || errno != EPERM);
    if (all || !strcmp(which, "perf")) r("perf_event_open", syscall(SYS_perf_event_open, 0, 0, -1, -1, 0) >= 0 || errno != EPERM);
    if (all || !strcmp(which, "userfaultfd")) r("userfaultfd", syscall(SYS_userfaultfd, 0) >= 0 || errno != EPERM);
#ifdef __x86_64__
    if (!strcmp(which, "x32"))  /* expected outcome: SIGSYS kill */ { long rc = syscall(0x40000000 | 39); r("x32_abi_getpid", rc >= 0); }
#endif
    if (all || !strcmp(which, "fdleak")) {
        int leaked = 0;
        for (int fd = 3; fd < 64; fd++) if (fcntl(fd, F_GETFD) != -1) leaked++;
        r("inherited_fds", leaked != 0);
    }
    if (all || !strcmp(which, "env")) r("ld_preload_env", getenv("LD_PRELOAD") != NULL || getenv("PYTHONPATH") != NULL);
    if (all || !strcmp(which, "rlimit")) { struct rlimit rl = {1 << 20, 1 << 20}; r("raise_nofile", setrlimit(RLIMIT_NOFILE, &rl) == 0); }
    if (all || !strcmp(which, "devmem")) { int fd = open("/dev/mem", O_RDONLY); r("open_dev_mem", fd >= 0); }
    if (all || !strcmp(which, "procview")) {  /* host processes must not be visible */
        int n = 0; char path[64];
        for (int pid = 1; pid < 4194304 && n < 10; pid = pid < 1000 ? pid + 1 : pid * 2) {
            snprintf(path, sizeof path, "/proc/%d", pid);
            if (access(path, F_OK) == 0) n++;
        }
        r("host_proc_visible", n > 1);
    }
    if (!strcmp(which, "whoami")) printf("uid=%d gid=%d\n", getuid(), getgid());
    if (!strcmp(which, "connect")) {  /* for profiles that allow socket: net ns must still isolate */
        int s = socket(AF_INET, SOCK_DGRAM, 0);
        struct sockaddr_in a = {.sin_family = AF_INET, .sin_port = htons(53)};
        inet_pton(AF_INET, "1.1.1.1", &a.sin_addr);
        r("net_egress", s >= 0 && connect(s, (struct sockaddr *)&a, sizeof a) == 0);
    }
    if (!strcmp(which, "landlock")) { int fd = open(argc > 2 ? argv[2] : "/etc/hostname", O_RDONLY); r("landlock_read_outside", fd >= 0); }
    fflush(stdout);
    return 0;
}
