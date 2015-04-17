#include <stdlib.h>
#include <stdarg.h>
#include "num-trie.h"

typedef struct LookupResult LookupResult ;
struct LookupResult{
    TrieNode *lastNode;
    void *lastData;
};


/* "4743" would be represented by
  _____________
  |root        |
  |____________|
       Y
     (NULL)
  ___________________
  |*|*|*|*|4|*|*|*|*|*|
  |___________________|
           |
           V
          (4,path="4")
  ____________________
  |*|*|*|*|*|*|*|7|*|*|
  |___________________|
                 |
                 V
                 (7,path="47")
  __________________)__
  |*|*|*|*|4|*|*|*|*|*|
  |___________________|
           |
           V
          (4,path="474")
  ____________________
  |*|*|*|3|*|*|*|*|*|*|
  |___________________|
         |
         V
        (3,path="4743")
   ____________________
  |*|*|*|*|*|*|*|*|*|*|
  |___________________|
  */

//todo, compress the tree to make a patricia tree.

void *num_trie_insert(NumTrie *trie, const char *key, void *data)
{
    TrieNode **currentNode = &trie->root;

    const char *currenKey = key;
    void *oldData = NULL;

    if (key == NULL || data == NULL) {
        return NULL;
    }

    while (*currenKey && *currenKey >= '0' && *currenKey <= '9') {
        int index = *currenKey - '0';

        if (*currentNode == NULL) {
            *currentNode = (TrieNode*)calloc(1, sizeof **currentNode);
            if (*currentNode == NULL) {
                return NULL;
            }
            trie->allocatedNodes++;
        }

        currentNode = &(*currentNode)->child[index];
        currenKey++;
    }

    if (*currentNode == NULL && *currentNode != trie->root) {
        *currentNode = (TrieNode*)calloc(1, sizeof **currentNode);
        if (*currentNode == NULL) {
            return NULL;
        }
        trie->allocatedNodes++;
    }

    if (*currentNode) {
        oldData = (*currentNode)->data;
        (*currentNode)->data = data;
        if (oldData == NULL) {
            trie->numElements++;
        }
    } else {
        return NULL;
    }

    if (oldData != NULL) {
        return oldData;
    } else {
        return data;
    }
}

static void num_trie_prefix_lookup_internal(LookupResult *result,
                                            TrieNode *currentNode, 
                                            const char *key)
{
    const char *currenKey = key;
    void *found = NULL;

    while (currentNode && *currenKey && *currenKey >= '0' && *currenKey <= '9') {
        int index = *currenKey - '0';

        if (currentNode->data != NULL) {
            found = currentNode->data;
        }

        result->lastNode = currentNode;

        currentNode = currentNode->child[index];
        currenKey++;
    }

    if (currentNode) {
        if(currentNode->data != NULL) {
            found = currentNode->data;
        }
        result->lastNode = currentNode;
    }

    result->lastData = found;
}


void* num_trie_prefix_lookup(NumTrie *trie, const char *key)
{
    LookupResult result = {NULL, NULL};
    num_trie_prefix_lookup_internal(&result, trie->root, key);
    return result.lastData;
}

void* num_trie_prefix_lookup_keys(NumTrie *trie, ...)
{
    va_list args;
    va_start(args,trie);

    LookupResult result = {trie->root, NULL};
    do {
        const char *key = va_arg(args,const char*);
        if(key == NULL) {
            break;
        }
        num_trie_prefix_lookup_internal(&result, result.lastNode, key);
    } while (result.lastNode != NULL);

    va_end(args);

    return result.lastData;
}

