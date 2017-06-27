# -*- coding: utf-8 -*-
import os
from itertools import izip

import h5py
import numpy as np
import copy
import math

from config import HERE
from utils.logger import BaseLogger


class H5EmbeddingManager(BaseLogger):
    def __init__(self, h5_path, mode='disk', **kwargs):
        super(H5EmbeddingManager, self).__init__(**kwargs)
        self.mode = mode
        f = h5py.File(h5_path, 'r')
        if mode == 'disk':
            self.W = f['embedding']
        elif mode == 'in-memory':
            self.W = f['embedding'][:]
        message = "load mode=%s, embedding data type=%s, shape=%s" % (self.mode, type(self.W), self.W.shape)
        self.info(message)
        words_flatten = f['words_flatten'][0]
        self.id2word = words_flatten.split('\n')
        assert len(self.id2word) == f.attrs['vocab_len'], "%s != %s" % (len(self.id2word), f.attrs['vocab_len'])
        self.word2id = dict(izip(self.id2word, range(len(self.id2word))))
        del words_flatten

    def __getitem__(self, item):
        item_type = type(item)
        if item_type is str:
            index = self.word2id[item]
            embs = self.W[index]
            return embs
        else:
            raise RuntimeError("don't support type: %s" % type(item))

    def init_word_embedding(self, words, dim_size=300, scale=0.1, mode='google'):
        print('loading word embedding.')
        word2id = self.word2id
        W = self.W
        shape = (len(words), dim_size)
        np.random.seed(len(words))
        # W2V = np.random.uniform(low=-scale, high=scale, size=shape).astype('float32')
        W2V = np.zeros(shape, dtype='float32')
        for i, word in enumerate(words[1:], 1):
            if word in word2id:
                _id = word2id[word]
                vec = W[_id]
                vec /= np.linalg.norm(vec)
            elif word.capitalize() in word2id:
                _id = word2id[word.capitalize()]
                vec = W[_id]
                vec /= np.linalg.norm(vec)
            else:
                vec = np.random.normal(0, 1.0, 300)
                vec = (0.01 * vec).astype('float32')
            W2V[i] = vec[:dim_size]
        return W2V

    def init_word_embedding1(self, words, dim_size=300, scale=0.1, mode='google'):
        word2id = self.word2id
        W = self.W
        shape = (len(words), dim_size)
        np.random.seed(len(words))
        # W2V = np.random.uniform(low=-scale, high=scale, size=shape).astype('float32')
        W2V = np.random.normal(0, 1.0, size=shape).astype('float32') * 0.01
        W2V[0, :] = 0
        if mode == 'random':
            return W2V
        in_vocab = np.ones(shape[0], dtype=np.bool)
        oov_set = set()
        word_ids = []
        for i, word in enumerate(words):
            _id = -1
            try:
                _id = word2id[word]
            except KeyError:
                pass
            if _id < 0:
                try:
                    _id = word2id[word.capitalize()]
                except KeyError:
                    pass
            if _id < 0:
                in_vocab[i] = False
                if not word.startswith("$oov-"):
                    oov_set.update([word])
            else:
                word_ids.append(_id)
        if self.mode == 'in-memory':
            W2V[in_vocab][:, :] = W[np.array(word_ids, dtype='int32')][:, :dim_size]
        else:
            nonzero_ids = in_vocab.nonzero()[0]
            for i in nonzero_ids:
                emb = W[word_ids[i]]
                W2V[i][:] = emb[:dim_size]
        # logger.debug("%s words is not in google word2vec, and it is random "
        #              "initialized: %s" % (len(oov_set), oov_set))
        return W2V


class EmbeddingInitEnhancer(BaseLogger):
    '''
    For more details, read "Counter-fitting Word Vectors to Linguistic Constraints"
    '''
    def __init__(self, init_word_vectors, vocab, repel_path_list, attract_path_list, **kwargs):
        super(EmbeddingInitEnhancer, self).__init__(**kwargs)
        self.build_word_vector_map(init_word_vectors, vocab)
        self.init_vocab = vocab
        self.repel_path_list = repel_path_list
        self.attract_path_list = attract_path_list

        self.repel = set()
        self.attract = set()

        # and we then have true the information to collect true the linguistic constraints:
        for syn_filepath in self.attract_path_list:
            self.attract = self.attract | self.load_constraints(syn_filepath, self.vocab)

        for ant_filepath in self.repel_path_list:
            self.repel = self.repel | self.load_constraints(ant_filepath, self.vocab)

        # finally, set the experiment hyperparameters:
        self.set_hyperparameters()

    def build_word_vector_map(self, init_word_vectors, vocab):
        self.word_vectors = {}
        for i in xrange(len(vocab)):
            self.word_vectors[vocab[i]] = init_word_vectors[i]
        self.vocab = set(vocab)

    def vector_map_to_vectors(self, word_vectors):
        vector_list = [word_vectors[v] for v in self.init_vocab]
        return np.vstack(vector_list)

    def load_constraints(self, constraints_filepath, vocab):
        """
        This methods reads a collection of constraints from the specified file, and returns a set with
        true constraints for which both of their constituent words are in the specified vocabulary.
        """
        constraints_filepath.strip()
        constraints = set()
        with open(constraints_filepath, "r+") as f:
            for line in f:
                word_pair = line.split()
                if word_pair[0] in vocab and word_pair[1] in vocab and word_pair[0] != word_pair[1]:
                    constraints |= {(word_pair[0], word_pair[1])}
                    constraints |= {(word_pair[1], word_pair[0])}

        self.info("%s yielded %s constraints." % (constraints_filepath, len(constraints)))
        return constraints

    def set_hyperparameters(self):
        """
        This method sets the hyperparameters of the procedure as specified in the paper.
        """
        self.hyper_k1 = 0.1
        self.hyper_k2 = 0.1
        self.hyper_k3 = 0.1
        self.delta = 1.0
        self.gamma = 0.0
        self.rho = 0.2
        self.info("embedding init enhancer hyperparameters --- k_1: %s, k_2: %s, k_3: %s, delta: %s, gamma: %s, rho: %s" %
                    (self.hyper_k1, self.hyper_k2, self.hyper_k3, self.delta, self.gamma, self.rho))

    def get_enhanced_embedding(self, from_pretrained_vector=False):
        """
        This method repeatedly applies SGD steps to counter-fit word vectors to linguistic constraints.
        """
        word_vectors = self.word_vectors
        repel = self.repel
        attract = self.attract
        current_iteration = 0

        if from_pretrained_vector:
            vsp_pairs = {}
            if self.hyper_k3 > 0.0:  # if we need to compute the VSP terms.
                vsp_pairs = self.compute_vsp_pairs(word_vectors, self.vocab, rho=self.rho)

        # Post-processing: remove synonym pairs which are deemed to be both synonyms and antonyms:
        for repel_pair in repel:
            if repel_pair in attract:
                attract.remove(repel_pair)
            if from_pretrained_vector and repel_pair in vsp_pairs:
                del vsp_pairs[repel_pair]

        max_iter = 20
        self.info("repel pairs: %s, attract pairs: %s" % (len(repel), len(attract)))
        self.info("Running the optimisation procedure for %s SGD steps..." % max_iter)

        while current_iteration < max_iter:
            current_iteration += 1
            vsp_pairs = vsp_pairs if from_pretrained_vector else None
            word_vectors = self.one_step_SGD(word_vectors, attract, repel, vsp_pairs)

        return self.vector_map_to_vectors(word_vectors)

    def one_step_SGD(self, word_vectors, attract_pairs, repel_pairs, vsp_pairs=None):
        """
        This method performs a step of SGD to optimise the counterfitting cost function.
        """
        new_word_vectors = copy.deepcopy(word_vectors)

        gradient_updates = {}
        update_count = {}

        # AR term:
        for (word_i, word_j) in repel_pairs:
            current_distance = self.distance(new_word_vectors[word_i], new_word_vectors[word_j])
            if current_distance < self.delta:
                gradient = self.vector_partial_gradient(new_word_vectors[word_i], new_word_vectors[word_j])
                gradient = gradient * self.hyper_k1
                if word_i in gradient_updates:
                    gradient_updates[word_i] += gradient
                    update_count[word_i] += 1
                else:
                    gradient_updates[word_i] = gradient
                    update_count[word_i] = 1

        # SA term:
        for (word_i, word_j) in attract_pairs:
            current_distance = self.distance(new_word_vectors[word_i], new_word_vectors[word_j])
            if current_distance > self.gamma:
                gradient = self.vector_partial_gradient(new_word_vectors[word_j], new_word_vectors[word_i])
                gradient = gradient * self.hyper_k2
                if word_j in gradient_updates:
                    gradient_updates[word_j] -= gradient
                    update_count[word_j] += 1
                else:
                    gradient_updates[word_j] = -gradient
                    update_count[word_j] = 1

        # VSP term:
        if vsp_pairs:
            for (word_i, word_j) in vsp_pairs:
                original_distance = vsp_pairs[(word_i, word_j)]
                new_distance = self.distance(new_word_vectors[word_i], new_word_vectors[word_j])
                if original_distance <= new_distance:
                    gradient = self.vector_partial_gradient(new_word_vectors[word_i], new_word_vectors[word_j])
                    gradient = gradient * self.hyper_k3
                    if word_i in gradient_updates:
                        gradient_updates[word_i] -= gradient
                        update_count[word_i] += 1
                    else:
                        gradient_updates[word_i] = -gradient
                        update_count[word_i] = 1

        for word in gradient_updates:
            # we've found that scaling the update term for each word helps with convergence speed.
            update_term = gradient_updates[word] / (update_count[word])
            new_word_vectors[word] += update_term
        return self.normalise_word_vectors(new_word_vectors)

    def distance(self, v1, v2, normalised_vectors=True):
        """
        Returns the cosine distance between two vectors.
        If the vectors are normalised, there is no need for the denominator, which is always one.
        """
        if normalised_vectors:
            return 1 - np.dot(v1, v2)
        else:
            return 1 - np.dot(v1, v2) / (np.norm(v1) * np.norm(v2))

    def vector_partial_gradient(self, u, v, normalised_vectors=True):
        """
        This function returns the gradient of cosine distance: \frac{ \partial dist(u,v)}{ \partial u}
        If they are both of norm 1 (we do full batch and we renormalise at every step), we can save some time.
        """
        if normalised_vectors:
            gradient = u * np.dot(u, v) - v
        else:
            norm_u = np.norm(u)
            norm_v = np.norm(v)
            nominator = u * np.dot(u, v) - v * np.power(norm_u, 2)
            denominator = norm_v * np.power(norm_u, 3)
            gradient = nominator / denominator
        return gradient

    def normalise_word_vectors(self, word_vectors, norm=1.0):
        """
        This method normalises the collection of word vectors provided in the word_vectors dictionary.
        """
        for word in word_vectors:
            word_vectors[word] /= math.sqrt((word_vectors[word]**2).sum() + 1e-6)
            word_vectors[word] = word_vectors[word] * norm
        return word_vectors

    def compute_vsp_pairs(self, word_vectors, vocabulary, rho=0.2):
        """
        This method returns a dictionary with true word pairs which are closer together than rho.
        Each pair maps to the original distance in the vector space.

        In order to manage memory, this method computes dot-products of different subsets of word
        vectors and then reconstructs the indices of the word vectors that are deemed to be similar.
        """
        self.info("Pre-computing word pairs relevant for Vector Space Preservation (VSP). Rho =%s" % rho)
        vsp_pairs = {}
        threshold = 1 - rho
        vocabulary = list(vocabulary)
        num_words = len(vocabulary)
        step_size = 1000  # Number of word vectors to consider at each iteration.
        import random
        vector_size = random.choice(word_vectors.values()).shape[0]
        # ranges of word vector indices to consider:
        list_of_ranges = []
        left_range_limit = 0
        while left_range_limit < num_words:
            curr_range = (left_range_limit, min(num_words, left_range_limit + step_size))
            list_of_ranges.append(curr_range)
            left_range_limit += step_size
        range_count = len(list_of_ranges)

        # now compute similarities between words in each word range:
        for left_range in range(range_count):
            for right_range in range(left_range, range_count):
                # offsets of the current word ranges:
                left_translation = list_of_ranges[left_range][0]
                right_translation = list_of_ranges[right_range][0]
                # copy the word vectors of the current word ranges:
                vectors_left = np.zeros((step_size, vector_size), dtype="float32")
                vectors_right = np.zeros((step_size, vector_size), dtype="float32")
                # two iterations as the two ranges need not be same length (implicit zero-padding):
                full_left_range = range(list_of_ranges[left_range][0], list_of_ranges[left_range][1])
                full_right_range = range(list_of_ranges[right_range][0], list_of_ranges[right_range][1])
                for iter_idx in full_left_range:
                    vectors_left[iter_idx - left_translation, :] = word_vectors[vocabulary[iter_idx]]
                for iter_idx in full_right_range:
                    vectors_right[iter_idx - right_translation, :] = word_vectors[vocabulary[iter_idx]]
                # now compute the correlations between the two sets of word vectors:
                dot_product = vectors_left.dot(vectors_right.T)
                # find the indices of those word pairs whose dot product is above the threshold:
                indices = np.where(dot_product >= threshold)
                num_pairs = indices[0].shape[0]
                left_indices = indices[0]
                right_indices = indices[1]
                for iter_idx in range(0, num_pairs):
                    left_word = vocabulary[left_translation + left_indices[iter_idx]]
                    right_word = vocabulary[right_translation + right_indices[iter_idx]]
                    if left_word != right_word:
                        # reconstruct the cosine distance and add word pair (both permutations):
                        score = 1 - dot_product[left_indices[iter_idx], right_indices[iter_idx]]
                        vsp_pairs[(left_word, right_word)] = score
                        vsp_pairs[(right_word, left_word)] = score
        self.info("There are %s VSP relations to enforce for rho =%s" % (len(vsp_pairs), rho))
        return vsp_pairs


if __name__ == '__main__':
    path = os.path.join(HERE, 'data/word_embedding/')
    emb = H5EmbeddingManager(path, mode='in-memory')
    while True:
        word = raw_input('input a word:')
        try:
            print repr(word), emb[word]
        except KeyError:
            print '%s is not in vocabulary' % word
