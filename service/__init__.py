# -*- coding: utf-8 -*-
from const import DEFAULT_WORDING_EMBEDDING_PATH
from wordembedding.wordvector import load_embedding

wording_embedding = load_embedding(DEFAULT_WORDING_EMBEDDING_PATH)


def longest_common_substring(query, retrieval_str):
    """
    计算问句与检索结果的最长公共子串
    :param query: 问句
    :param retrieval_str:检索结果
    :return: 最长公共子串长度
    """
    # 生成0矩阵，为方便后续计算，比字符串长度多了一列
    m = [[0 for i in range(len(retrieval_str) + 1)] for j in range(len(query) + 1)]
    mmax = 0  # 最长匹配的长度
    p = 0  # 最长匹配对应在query中的最后一位
    for i in range(len(query)):
        for j in range(len(retrieval_str)):
            if query[i] == retrieval_str[j]:
                m[i + 1][j + 1] = m[i][j] + 1
                if m[i + 1][j + 1] > mmax:
                    mmax = m[i + 1][j + 1]
                    p = i + 1
    return query[p - mmax:p], mmax  # 返回最长子串及其长度


def calculate_wmd(words_1, words_2):
    """
    计算句子1与句子2的文档迁移距离
    :param words_1:
    :param words_2:
    :return:
    """
    score = wording_embedding.wmdistance(words_1, words_2)
    return score


if __name__ == '__main__':
    qa = [u'你', u'是', u'谁']
    qb = [u'你', u'谁', u'啊']
    sub_string, length = longest_common_substring(qb, qa)
    print sub_string, length
