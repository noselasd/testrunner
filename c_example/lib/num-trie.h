#ifndef NUMTRIE_H_
#define NUMTRIE_H_

typedef struct TrieNode TrieNode;
struct TrieNode {
	TrieNode *child[10];
	void *data;
};

typedef struct NumTrie NumTrie;
struct NumTrie {
	size_t allocatedNodes;
	size_t numElements;
	struct TrieNode *root;
};
/**
 * Inserts the current key into the tree, associating it with the given data-
 * Keys should only be digits, that is the character '0' through '9'
 *
 * @param trie The trie to insert into
 * @param key The key to insert
 * @param data The data to associate with the key
 */
void *num_trie_insert(NumTrie *trie, const char *key, void *data);

/**
 * Looks up the data associated with the longes prefix of the key.
 * Traversing the key will stop if it encounters characters outside '0' through '9'
 * e.g. if a key exists for "123" and "12345", and a lookup is performed on "1234567",
 * the data associated with "12345" is returned. If a lookup on "1239999" is performed,
 * data associated with "123" would be returned.
 *
 * @param trie The trie to perform the lookup in.
 * @param key The key perform a prefix lookup on.
 * @return data The data associated with the longest prefix matched in key, 
 *         or NULL if no match are found
 */
void* num_trie_prefix_lookup(NumTrie *trie, const char *key);

/**
 * Similar to num_trie_insert, but allows you to concatenate serveal keys, the last argument must be NULL.
 * e.g. num_trie_prefix_lookup_keys(trie,"47","370431",NULL);
 * is exactly identical to num_trie_prefix_lookup(trie,"47370431");
 *
 * @param trie The trie to perform the lookup in.
 * @param ... The keys perform a incremental prefix lookup on. The 
 *            last argument must be NULL.
 * @return data The data associated with the longest prefix matched in key, 
 *              or NULL if no match are found
 */
void* num_trie_prefix_lookup_keys(NumTrie *trie, ...);

#endif /* NUMTRIE_H_ */
