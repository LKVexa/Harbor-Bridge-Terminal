/* Unikraft-convention reference guest (built locally; not an upstream Unikraft build). */
static const char msg[] = "INV27-READY\n";
long uk_syscall_r_write(long fd, const char *b, long n) { (void)fd; (void)b; return n; }
long uk_syscall_r_read(long fd, char *b, long n) { (void)fd; (void)b; (void)n; return 0; }
long uk_syscall_r_clock_gettime(long c, void *t) { (void)c; (void)t; return 0; }
#ifdef EXTRA
EXTRA
#endif
void ukplat_entry(void) {
    uk_syscall_r_write(1, msg, sizeof msg - 1);
    for (;;) __asm__ volatile("hlt");
}
