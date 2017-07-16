# -*- coding: utf-8 -*-
import json
from math import exp

from config import TRIPLE_CORE_NAME
from const import DEFAULT_WMD_THRESHOLD
from service import calculate_wmd
from utils import normalize_query, seg_doc
from utils.logger import BaseLogger
from utils.solr_api import SolrAPIHandler


class RetrievalBot(BaseLogger):
    def __init__(self, **kwargs):
        super(RetrievalBot, self).__init__(**kwargs)
        self.debug('>>> init RetrievalService <<<')
        self.query = ''
        self.query_fields = ['attribute_date_index', ]  # 检索域
        self.target_field = 'attribute_date'  # 目标域
        self.triple_core = SolrAPIHandler(TRIPLE_CORE_NAME)  # solr三元组core

    def _is_similarity(self, query_words, doc_words):
        """
        计算query_words与doc_words的相似度
        :param query_words:
        :param doc_words:
        :return: 相似度得分
        """
        distance = calculate_wmd(query_words, doc_words)  # 计算问句与属性间的文档迁移距离
        score = exp(-distance/19.0)
        return score

    def _sort_retrieval_docs(self, query, triple_docs):
        """
        对三元组进行重排
        :param query:问句
        :param triple_docs:检索得到的三元组
        :return:
        """
        self.debug('>>> start _sort_retrieval_docs <<<')
        filter_triple_docs = []
        query_words, query_tags = seg_doc(query)
        for doc_item in triple_docs:
            target_field = self.query_fields[0]
            attribute = doc_item.get(target_field, "")
            attribute_words = attribute.strip().split()

            # 需要一个分类器，判断问句与文档是否相关，目前使用word move distance
            score = self._is_similarity(query_words, attribute_words)  # 计算问句与属性间的文档迁移距离
            if score > DEFAULT_WMD_THRESHOLD:  # 过滤掉得分低的三元组
                doc_item['score'] = score
                filter_triple_docs.append(doc_item)
        filter_triple_docs.sort(key=lambda x: x['score'], reverse=False)  # 根据得分进行重排
        self.debug('>>> end _sort_retrieval_docs <<<')
        return filter_triple_docs

    def retrieval_triple(self, query):
        """
        检索三元组，并进行重排
        :param query: 问句
        :return:
        """
        self.debug('>>> start retrieval_triple <<<')
        triple_doc = {}
        self.debug('query=%s, query_fields=%s, target_field=%s',
                   query, json.dumps(self.query_fields), self.target_field)
        triple_docs = self.triple_core.search_with_seg(query, query_fields=self.query_fields)  # 进行solr检索
        if triple_docs:
            sorted_triple_docs = self._sort_retrieval_docs(query, triple_docs)  # 过滤并重排检索得到的三元组
            if sorted_triple_docs:  # 选取top1作为答案三元组
                triple_doc = sorted_triple_docs[0]
        else:
            self.warn("@@@@@@@@@@@@@@@@@@@@@@@@@@ unexpected values, triple_docs is None")
        self.debug('>>> end retrieval_triple <<<')
        return triple_doc

    def get_answer(self, query):
        """
        获取答案
        :param query: 问句
        :return: 答案
        """
        self.debug('>>> start get_answer <<<')
        answer = ""
        triple_doc = self.retrieval_triple(query)
        if triple_doc:  # 若三元组存在选取target_field为最终答案
            answer = triple_doc.get(self.target_field, "")
        else:
            self.debug('unexpected values triple_doc=None')
        self.debug('>>> end get_answer <<<')
        return answer

    def reply(self, query):
        """
        基于检索的方式，返回query的answer
        :param query: 用户输入问句
        :return: 答案
        """
        answer = ""
        self.query = normalize_query(query)  # 问句预处理
        self.debug("[ start RetrievalBot reply ]")
        self.debug("query=%s", self.query)
        if self.query:
            answer = self.get_answer(self.query)
        else:
            self.warn("@@@@@@@@@@@@@@@@@@@ unexpected value, query is None")
        self.debug("answer=%s", answer)
        self.debug("[ end RetrievalBot reply ]")
        return answer

if __name__ == '__main__':
    bot = RetrievalBot()
    while 1:
        _query = raw_input('请输入问句：')
        _answer = bot.reply(_query)
        print _answer
