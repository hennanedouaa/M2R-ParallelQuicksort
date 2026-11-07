/* Benchmark the ORIGINAL three algorithms without editing their sorting code.
 * Include the original source, renaming its own main so that we can supply
 * controlled inputs, measurement, and an independent correctness oracle.
 * Original parallel random-pivot implementation uses libc rand() concurrently;
 * this may cause scheduling-dependent performance and is itself under study.
 */
#define _POSIX_C_SOURCE 200809L
#define main original_main_unmodified
#include "../src/parallelQuicksort.c"
#undef main
#include <errno.h>
#include <inttypes.h>
#include <stdint.h>
#include <sys/resource.h>
#include <unistd.h>

static uint64_t rng_state;
static uint64_t next_random(void) {
  uint64_t x = rng_state;
  x ^= x >> 12; x ^= x << 25; x ^= x >> 27;
  rng_state = x;
  return x * UINT64_C(2685821657736338717);
}
static double seconds(struct timespec t) { return (double)t.tv_sec + 1e-9 * (double)t.tv_nsec; }
static double timeval_seconds(struct timeval t) { return (double)t.tv_sec + 1e-6 * (double)t.tv_usec; }
static void help(const char *name) {
  fprintf(stderr,"Usage: %s ALGO SIZE DISTRIBUTION SEED LEVEL\\nALGO: seq|par|libc  DISTRIBUTION: random|sorted|reverse|equal|few_unique|nearly_sorted|organ_pipe\\nLEVEL: parallel recursion depth (recommend 0..4 for production)\\n",name);
}
int main(int argc, char **argv) {
  if (argc != 6) {help(argv[0]); return 2;}
  const char *algo=argv[1], *distribution=argv[3];
  char *end=NULL;
  errno=0; unsigned long n_arg=strtoul(argv[2],&end,10);
  if (errno||!end||*end||n_arg>INT32_MAX) {fprintf(stderr,"invalid n\n");return 2;}
  int n=(int)n_arg;
  errno=0;end=NULL;unsigned long long seed=strtoull(argv[4],&end,10);
  if(errno||!end||*end){fprintf(stderr,"invalid seed\n");return 2;}
  errno=0;end=NULL;long lvl=strtol(argv[5],&end,10);
  if(errno||!end||*end||lvl<0||lvl>6){fprintf(stderr,"invalid level (0..6)\n");return 2;}
  if(strcmp(algo,"seq")&&strcmp(algo,"par")&&strcmp(algo,"libc")){help(argv[0]);return 2;}
  if(strcmp(distribution,"random")&&strcmp(distribution,"sorted")&&strcmp(distribution,"reverse")&&strcmp(distribution,"equal")&&strcmp(distribution,"few_unique")&&strcmp(distribution,"nearly_sorted")&&strcmp(distribution,"organ_pipe")){help(argv[0]);return 2;}
  rng_state=(uint64_t)seed+UINT64_C(0x9e3779b97f4a7c15);
  if(rng_state==0)rng_state=1;
  size_t count=(size_t)n, bytes=count*sizeof(double);
  double *data=malloc(bytes?bytes:sizeof(double)), *oracle=malloc(bytes?bytes:sizeof(double));
  if(!data||!oracle){perror("malloc");free(data);free(oracle);return 3;}
  for(int i=0;i<n;i++){
    uint64_t r=next_random();
    if(!strcmp(distribution,"random"))data[i]=(double)(r>>11)/(double)(UINT64_C(1)<<53);
    else if(!strcmp(distribution,"sorted")||!strcmp(distribution,"nearly_sorted")) data[i]=(double)i;
    else if(!strcmp(distribution,"reverse"))data[i]=(double)(n-i);
    else if(!strcmp(distribution,"equal"))data[i]=1.0;
    else if(!strcmp(distribution,"few_unique"))data[i]=(double)(r%8);
    else data[i]=(double)(i<=n/2?i:n-i);
  }
  if(!strcmp(distribution,"nearly_sorted")&&n>1)for(int j=0;j<n/100+1;j++){
    int a=(int)(next_random()%count), b=(int)(next_random()%count);
    double tmp=data[a];data[a]=data[b];data[b]=tmp;
  }
  memcpy(oracle,data,bytes);
  /* The correctness oracle is OUTSIDE the timed interval. */
  qsort(oracle,count,sizeof(double),compare_doubles);
  /* Control the original source's rand() used for pivot selection. */
  srand((unsigned)(seed ^ (seed>>32)));
  struct rusage before,after; struct timespec start,stop;
  if(getrusage(RUSAGE_SELF,&before)||clock_gettime(CLOCK_MONOTONIC,&start)){perror("clock/getrusage");return 3;}
  if(!strcmp(algo,"seq")) quicksort(data,n);
  else if(!strcmp(algo,"par")) parallelQuicksort(data,n,(int)lvl);
  else qsort(data,count,sizeof(double),compare_doubles);
  if(clock_gettime(CLOCK_MONOTONIC,&stop)||getrusage(RUSAGE_SELF,&after)){perror("clock/getrusage");return 3;}
  int correct=(memcmp(data,oracle,bytes)==0); /* exact match: finite numeric data */
  double wall=1000.0*(seconds(stop)-seconds(start));
  double cpu=1000.0*(timeval_seconds(after.ru_utime)-timeval_seconds(before.ru_utime));
  double sys=1000.0*(timeval_seconds(after.ru_stime)-timeval_seconds(before.ru_stime));
  printf("%s,%d,%s,%llu,%ld,%.6f,%d,%.6f,%.6f,%ld,%ld,%ld\n",
         algo,n,distribution,seed,lvl,wall,correct,cpu,sys,
         after.ru_maxrss,after.ru_nvcsw-before.ru_nvcsw,
         after.ru_nivcsw-before.ru_nivcsw);
  free(data);free(oracle);
  return correct?0:4;
}
