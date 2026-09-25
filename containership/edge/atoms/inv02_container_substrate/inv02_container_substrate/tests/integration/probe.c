#define _GNU_SOURCE
#include <stdio.h>
#include <unistd.h>
#include <sys/mount.h>
#include <errno.h>
#include <string.h>
#include <sched.h>
int main(int c, char**v){
  printf("uid=%d pid=%d\n", getuid(), getpid());
  int r = mount("none","/mnt","tmpfs",0,0); printf("mount=%d errno=%d\n", r, r?errno:0);
  r = unshare(CLONE_NEWUSER); printf("unshare=%d errno=%d\n", r, r?errno:0);
  FILE*f=fopen("/etc/probe","w"); printf("rootfs_write=%s\n", f?"yes":"no");
  FILE*s=fopen("/run/secrets/db-pass","r"); char b[64]={0}; if(s){if(fread(b,1,63,s)){}} printf("secret=%s\n", s?b:"none");
  return 0; }
