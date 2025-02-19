#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <string.h>
#include <unistd.h>
#include <math.h>

#if      defined(__linux__)
char	*strdup(const char *string);
#endif

//  written by Chris.McDonald@uwa.edu.au
//  compile with:
//      cc -std=c11 -Wall -Werror -o buildrandomroutes buildrandomroutes.c

#define AUTHOR_EMAIL        "Chris.McDonald@uwa.edu.au"

#define TT_PREFIX           "tt-"
#define FILENM_ADJACENCY    "adjacency"

#define	MIN_NODES	    2
#define	MAX_NODES	    (26*26)

#define RANDOM_LAT          (-31.9 + (rand() % 40) / 100.0)
#define RANDOM_LON          (115.8 + (rand() % 40) / 100.0)

//  JUST A VERY HELPFUL MACRO
#define CHECKALLOC(p)	do { if((p) == NULL) { \
    fprintf(stderr, "allocation failed - %s:%s(), line %d\n",__FILE__,__func__,__LINE__); \
    exit(2); } \
} while(false)

//  ---------------------------------------------------------------------

static  char    *argv0;
static  int     N;

#define FOREACH_i           for(int i=0 ; i<N ; ++i)
#define FOREACH_j           for(int j=0 ; j<N ; ++j)

static	bool	**w	    = NULL;
static	bool	**adj	    = NULL;


// "A Theorem on Boolean Matrices"
// Stephen Warshall, Journal of the ACM, January 1962.
// c.f.  https://dl.acm.org/doi/pdf/10.1145/321105.321107

static bool Warshall(bool **adj, int N)
{
    FOREACH_i {
        FOREACH_j {
            w[i][j] = adj[i][j];
        }
    }
    for(int k=0 ; k<N ; ++k) {
        FOREACH_i {
            FOREACH_j {
                if(!w[i][j]) {
                    w[i][j] = w[i][k] && w[k][j];
                }
            }
        }
    }
    FOREACH_i {
        FOREACH_j {
            if(!w[i][j]) {
                return false;
            }
        }
    }
    return true;
}

//  ---------------------------------------------------------------------

static void build_routes(void)
{
    do {
        int i   = rand() % N;
        int j   = rand() % N;

        if((i == j) || adj[i][j]) {
            continue;
        }

        adj[i][j] = adj[j][i] = true;
    } while( !Warshall(adj, N) );
}

static  int type0   = 0;

static char *nodetype(int i)
{
    char *types[] = { "Station", "Terminal", "Junction", "Busport" };
#define NTYPES      (sizeof(types) / sizeof(types[0]))

    return types[ (i+type0) % NTYPES ];
#undef  NTYPES
}

static char *nodename(int i)
{
    static char name[4];

    if(N < 26) {
        name[0] = 'A' + i%26;
        name[1] = '\0';
    }
    else {
        name[0] = 'A' + i%26;
        name[1] = 'A' + (i/26)%26;
        name[2] = '\0';
    }
    return name;
}

static double *x, *y;

static double distance(int i, int j)
{
    return (fabs(x[i] - x[j]) + fabs(y[i] - y[j])) * 100.0;
}

static FILE *create_file(const char *filenm)
{
    FILE *fp    = fopen(filenm, "w");

    if(fp == NULL) {
        fprintf(stderr, "%s: cannot open '%s'\n", argv0, filenm);
        exit(1);
    }
    printf("creating file %s\n", filenm);
    return fp;
}

static void build_timetables(const char *tt_prefix)
{
    x   = calloc(N, sizeof(x[0]));
    CHECKALLOC(x);
    y   = calloc(N, sizeof(y[0]));
    CHECKALLOC(y);

    FOREACH_i {
        x[i]    = RANDOM_LON;
        y[i]    = RANDOM_LAT;
    }

    char    filenm[256];

    FOREACH_i {
        int nn = 0;

        FOREACH_j {
            if(adj[i][j]) {
                ++nn;
            }
        }
        
        sprintf(filenm, "%s%s%s", tt_prefix, nodetype(i), nodename(i));

        FILE *fp    = create_file(filenm);

//  Subiaco_Stn,-31.9446,115.8241
        fprintf(fp, "# station-name,longitude,latitude\n");
        fprintf(fp, "%s%s,%.4f,%.4f\n",
                    nodetype(i), nodename(i), x[i], y[i]);

        int departs = 6*60 + nn;    // 6am +
        int tlast   = 21*60;        // 9pm
        int tdelta  = 60 / nn;
        char *nni   = strdup(nodename(i));

        fprintf(fp, "# departure-time,route-name,departing-from,arrival-time,arrival-station\n");
        while(departs < tlast) {
            int j   = rand() % N;

            if(adj[i][j]) {
                int skew    = rand()%3;
                int arrives = departs + distance(i, j) + skew;
                char *nnj   = strdup(nodename(j));

#define hour(m)     (m/60)
#define mins(m)     (m%60)
//  07:52,Fremantle_Line,Subiaco_Stn_Platform_1,07:53,West_Leederville_Stn
                fprintf(fp, "%02i:%02i,bus%s_%s,stop%s,%02i:%02i,%s%s\n",
                            hour(departs), mins(departs),
                            nni, nnj,
                            nni,
                            hour(arrives), mins(arrives),
                            nodetype(j), nnj );
#undef  hour
#undef  mins
                free(nnj);
                departs += tdelta + skew + rand() % 5 + 2;
            }
        }
        free(nni);
        fclose(fp);
    }
    free(x);
    free(y);
}

static void print_adjacency(const char *filenm)
{
    FILE *fp    = create_file(filenm);

    FOREACH_i {
        fprintf(fp, "%s%s", nodetype(i), nodename(i));
        FOREACH_j {
            if(adj[i][j]) {
                fprintf(fp, " %s%s", nodetype(j), nodename(j));
            }
        }
        fprintf(fp, "\n");
    }
    fclose(fp);
}

static bool **new2D(int N)
{
    bool **a	= malloc(N * sizeof(bool *));
    CHECKALLOC(a);

    FOREACH_i {
	a[i]	= calloc(N, sizeof(bool));
        CHECKALLOC(a[i]);
    }
    return a;
}

//  ---------------------------------------------------------------------

static void usage(int status)
{
    fprintf(stderr, "Usage: %s N  (%i..%i)\n", argv0, MIN_NODES, MAX_NODES);
    fprintf(stderr, "\nPlease report any bugs to %s\n", AUTHOR_EMAIL);
    exit(status);
}

int main(int argc, char *argv[])
{
    argv0	= (argv0 = strrchr(argv[0],'/')) ? argv0+1 : argv[0];

    if(argc != 2) {
        usage(EXIT_FAILURE);
    }

    N   = atoi(argv[1]);
    if(N < MIN_NODES || N > MAX_NODES) {
        usage(EXIT_FAILURE);
    }

    w       = new2D(N);
    adj     = new2D(N);

    srand(getpid());
    type0   = rand() % 10;

    build_routes();
    build_timetables(TT_PREFIX);
    print_adjacency(FILENM_ADJACENCY);

    return EXIT_SUCCESS;
}

//  vim: ts=8 sw=4