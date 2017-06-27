# -*- coding: utf-8 -*-
import os
from time import strftime, localtime

from gensim.models import word2vec, KeyedVectors

from config import HERE
from utils import seg_doc


def load_embedding(embedding_file_path):
    try:
        model = KeyedVectors.load(embedding_file_path)
    except Exception, e:
        model = KeyedVectors.load_word2vec_format(embedding_file_path)
    return model


def train_embedding(model_path, corpus_path, dimension, window, min_count):
    """
    训练词向量
    :param model_path:
    :param corpus_path:
    :param dimension:
    :param window:
    :param min_count:
    :return:
    """
    sentences = word2vec.Text8Corpus(corpus_path)
    model = word2vec.Word2Vec(sentences, size=dimension, window=window, min_count=min_count)
    model.save(model_path)


def get_similarity(model, word):
    """

    :param model:
    :param word: 编码为unicode
    :return:
    """
    similar_list = model.similar_by_word(word, topn=50)
    for (word, simi) in similar_list:
        print word, repr(word)
        print simi


def get_wmd(model, s1, s2):
    """
    使用gensim词向量模型计算文档迁移距离
    :param model: 模型
    :param s1: 句子1
    :param s2: 句子2
    :return:
    """
    words_s1, tag_s1 = seg_doc(s1)
    words_s2, tag_s2 = seg_doc(s2)

    wmd = model.wmdistance(words_s1, words_s2)
    return wmd

if __name__ == '__main__':
    # 训练词向量
    start_time = strftime("%Y-%m-%d-%H:%M:%S", localtime())
    _model_path = os.path.join(HERE, 'data/word_embedding', 'word_embedding_%s.vec' % start_time)
    _corpus_path = os.path.join(HERE, 'data/embedding_training_corpus/seg_corpus/seg_corpus.txt')
    _dimension = 100
    _window = 8
    _min_count = 0
    # train_embedding(_model_path, _corpus_path, _dimension, _window, _min_count)

    # 加载词向量并测试
    _model_path = os.path.join(HERE, 'data/word_embedding', 'word_embedding_2017-06-25-23:36:57.vec')
    _model = load_embedding(_model_path)
    get_similarity(_model, u'自然')

