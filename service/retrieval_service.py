# -*- coding: utf-8 -*-
import json

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
        self.triple_core = SolrAPIHandler(TRIPLE_CORE_NAME)  # solr三元组core

    def _sort_retrieval_docs(self, query, triple_docs, target_field):
        self.debug('>>> start _sort_retrieval_docs <<<')
        filter_triple_docs = []
        query_words, query_tags = seg_doc(query)
        for doc_item in triple_docs:
            target_sentence = doc_item.get('%s_index' % target_field, "")
            target_sentence_words = target_sentence.strip().split()
            score = calculate_wmd(query_words, target_sentence_words)
            if score < DEFAULT_WMD_THRESHOLD:
                doc_item['score'] = score
                filter_triple_docs.append(doc_item)
                filter_triple_docs.sort(key=lambda x: x['score'], reverse=False)
        self.debug('>>> end _sort_retrieval_docs <<<')
        return filter_triple_docs

    def get_triple(self, query, query_fields, target_field):
        self.debug('>>> start get_triple <<<')
        self.debug('query=%s, query_fields=%s, target_field=%s',
                   query, json.dumps(query_fields), target_field)
        triple_doc = {}
        triple_docs = self.triple_core.search_with_seg(query, query_fields=query_fields)
        if triple_docs:
            triple_docs = list(triple_docs)
            self.debug("got triple_docs=%s", len(triple_docs))
            sorted_triple_docs = self._sort_retrieval_docs(query, triple_docs, target_field)
            self.debug("got sorted_triple_docs=%s", len(sorted_triple_docs))
            if sorted_triple_docs:
                triple_doc = sorted_triple_docs[0]
        else:
            self.warn("@@@@@@@@@@@@@@@@@@@@@@@@@@ triple_docs is None")
        self.debug('>>> end get_triple <<<')
        return triple_doc

    def retrieval_answer(self, query):
        self.debug('>>> start retrieval_answer <<<')
        answer = ""
        query_fields = ['triple_object_index', ]
        target_field = 'triple_object'
        triple_doc = self.get_triple(query, query_fields, target_field)
        if triple_doc:
            answer = triple_doc.get(target_field, "")
        else:
            self.debug('unexpected values triple_doc=None')
        self.debug('>>> end retrieval_answer <<<')
        return answer

    def reply(self, query):
        """
        根据query返回答案
        :param query: 用户输入问句
        :return: 答案
        """
        answer = {}
        self.query = normalize_query(query)
        self.debug("[start] query=%s", self.query)
        if self.query:
            answer = self.retrieval_answer(self.query)
        else:
            self.warn("@@@@@@@@@@@@@@@@@@@ unexpected query is None")
        if answer:
            ret = answer
        else:
            ret = ''
        self.debug("[end] query=%s", self.query)
        return ret

if __name__ == '__main__':
    bot = RetrievalBot()
    while 1:
        _query = raw_input('请输入问句：')
        _answer = bot.reply(_query)
        print _answer
