/* Solo5-convention reference guest (built locally; modelled on public Solo5 API names). */
void solo5_console_write(const char *b, unsigned long n) { (void)b; (void)n; }
unsigned long solo5_clock_monotonic(void) { return 0; }
int solo5_app_main(const void *si) { (void)si; solo5_console_write("INV27-READY\n", 12); return 0; }
void _start(void) { solo5_app_main(0); for (;;) __asm__ volatile("hlt"); }
