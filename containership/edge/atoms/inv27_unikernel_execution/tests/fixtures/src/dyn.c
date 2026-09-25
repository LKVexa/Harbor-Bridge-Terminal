#include <unistd.h>
#include <dlfcn.h>
int main(void) { if (fork() == 0) execve("/bin/true", 0, 0); void *h = dlopen("x", 0); return h != 0; }
