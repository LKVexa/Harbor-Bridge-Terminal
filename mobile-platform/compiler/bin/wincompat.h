/* Harbor Windows/MinGW shim for Bottle Rocket brctl (injected via -include). */
#ifdef _WIN32
#include <io.h>
#ifndef fsync
#define fsync _commit
#endif
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#ifndef HAVE_GETLINE
static ssize_t harbor_getline(char **lineptr, size_t *n, FILE *stream) {
  if (!lineptr || !n || !stream) { errno = EINVAL; return -1; }
  if (!*lineptr || !*n) { *n = 256; *lineptr = (char*)malloc(*n); if (!*lineptr) return -1; }
  size_t len = 0; int c;
  while ((c = fgetc(stream)) != EOF) {
    if (len + 1 >= *n) {
      size_t nn = (*n) * 2;
      char *p = (char*)realloc(*lineptr, nn);
      if (!p) return -1;
      *lineptr = p; *n = nn;
    }
    (*lineptr)[len++] = (char)c;
    if (c == '\n') break;
  }
  if (len == 0 && c == EOF) return -1;
  (*lineptr)[len] = '\0';
  return (ssize_t)len;
}
#define getline harbor_getline
#endif
#endif
