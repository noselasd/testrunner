#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "num-trie.h"

static void read_nums(const char *fileName, NumTrie *trie)
{
	char buf[512];
	FILE *f = fopen(fileName,"r");

	if (f == NULL) {
		perror("Can't open file:");
        exit(1);
	}

	while (fgets(buf, sizeof buf, f) != NULL) {
		size_t len = strlen(buf);
		if (len > 0) {
            char *s;
            char *old;

			buf[len-1] = 0;
			s = strdup(buf);
			old = (char*)num_trie_insert(trie, buf, s);
			if (s != old) {
				printf("Duplicate found for %s\n", s);
			}
		}
	}
}

static void usage(void)
{
    puts("Usage: numtrie lookupfile number");
    exit(1);

}

int main(int argc,char *argv[])
{
	NumTrie trie = {0};
    const char *data;
    int rc = 1;

    if (argc != 3) {
        usage();
    }

	read_nums(argv[1], &trie);

    data = (const char*)num_trie_prefix_lookup(&trie, argv[2]);
    if (data) {
        printf("Data for %s : %s\n", argv[2], data);
        rc = 0;
    } else {
        printf("Nothing found for %s\n", argv[2]);
    }

	return rc;
}

