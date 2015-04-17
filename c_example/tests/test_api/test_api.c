#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "num-trie.h"

// These are simple test cases to exercise the num-trie API
// A larger application would preferrably create a few test utilities
// for consiting output/assertions etc.

#define START_TEST(test_func) do {\
    printf("RUNNING %s\n", #test_func);\
    test_func();\
} while (0)

void test_empty_tree(void)
{
    NumTrie trie = {0,0,NULL};
    void *data;
    
    data = num_trie_prefix_lookup(&trie, "1234");
    printf("data: %s\n",  data ? data : "null");
    data = num_trie_prefix_lookup(&trie, "");
    printf("data: %s\n",  data ? data : "null");
}

void test_insert_null(void)
{
    NumTrie trie = {0,0,NULL};
    const char *p;
    
    p = num_trie_insert(&trie, "1234", NULL); 
    if (p != NULL) {
        printf("p: %s\n", p);
    }
    printf("num_elements %zu\n", trie.numElements);

    p = num_trie_insert(&trie, NULL, "5678"); 
    if (p != NULL) {
        printf("p: %s\n", p);
    }
    printf("num_elements %zu\n", trie.numElements);
    if (p != NULL) {
        printf("p: %s\n", p);
    }
}

void test_insert_duplicate(void)
{
    NumTrie trie = {0,0,NULL};
    const char *p;
    
    num_trie_insert(&trie, "1234", "first"); 
    printf("num_elements %zu\n", trie.numElements);
    p = num_trie_insert(&trie, "1234", "second"); 
    printf("p: %s\n", p);
    printf("num_elements %zu\n", trie.numElements);
}

void test_lookup(void)
{
    NumTrie trie = {0,0,NULL};
    const char *p;
    
    p = num_trie_insert(&trie, "1", "first"); 
    if (p == NULL) {
        puts("returned NULL");
    }
    p = num_trie_insert(&trie, "12", "second"); 
    if (p == NULL) {
        puts("returned NULL");
    }

    p = num_trie_insert(&trie, "123456", "third"); 
    if (p == NULL) {
        puts("returned NULL");
    }

    p = num_trie_insert(&trie, "422", "fourth"); 
    if (p == NULL) {
        puts("returned NULL");
    }
    p = num_trie_insert(&trie, "4", "fifth"); 
    if (p == NULL) {
        puts("returned NULL");
    }

    printf("1: %s\n", (const char *)num_trie_prefix_lookup(&trie, "1"));
    printf("2: %s\n", (const char *)num_trie_prefix_lookup(&trie, "12"));
    printf("3: %s\n", (const char *)num_trie_prefix_lookup(&trie, "123"));
    printf("4: %s\n", (const char *)num_trie_prefix_lookup(&trie, "1234"));
    printf("5: %s\n", (const char *)num_trie_prefix_lookup(&trie, "123456"));
    printf("6: %s\n", (const char *)num_trie_prefix_lookup(&trie, "1234567"));
    p = num_trie_prefix_lookup(&trie, "2");
    printf("7: %s\n", p ? p : "null");
    printf("8: %s\n", (const char *)num_trie_prefix_lookup(&trie, "422"));
    printf("9: %s\n", (const char *)num_trie_prefix_lookup(&trie, "4"));
    printf("11: %s\n", (const char *)num_trie_prefix_lookup_keys(&trie, "4","2","2", NULL));
    printf("12: %s\n", (const char *)num_trie_prefix_lookup_keys(&trie, "4","2","2", "3", NULL));
    printf("12: %s\n", (const char *)num_trie_prefix_lookup_keys(&trie, "4","2","2", "3", NULL));
    p = num_trie_prefix_lookup_keys(&trie,  "", NULL);
    printf("13: %s\n", p ? p : "null");
    p = num_trie_prefix_lookup(&trie,  "");
    printf("14: %s\n", p ? p : "null");
}

void test_invalid(void)
{
    NumTrie trie = {0,0,NULL};
    const char *p;
    
    p = num_trie_insert(&trie, "abcd", "first"); 
    if (p != NULL) {
        puts("p != NULL");
    }
    printf("num_elements %zu\n", trie.numElements);

}

int main(int argc,char *argv[])
{
START_TEST(test_insert_null);
    START_TEST(test_empty_tree);
    START_TEST(test_insert_duplicate);
    START_TEST(test_lookup);
    START_TEST(test_invalid);

    return 0;
}

