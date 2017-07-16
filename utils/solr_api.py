# -*- coding: utf-8 -*-
import json

import pysolr

from const import SOLR_ESCAPE_PATTERN
from logger import BaseLogger
from utils import seg_doc_with_search, unicode2str
from config import SOLR_CORE_MAP, SOLR_DEFAULT_ROWS, SOLR_DEFAULT_RETURN_FIELDS


class SolrAPIHandler(BaseLogger):
    def __init__(self, core_name):
        super(SolrAPIHandler, self).__init__()
        self.core_name = core_name
        self.debug('init solr_client core_name=%s', core_name)
        self.core = SOLR_CORE_MAP.get(core_name, "")
        self.escape_pattern = SOLR_ESCAPE_PATTERN
        if self.core:
            self.solr_client = pysolr.Solr(self.core)
        else:
            self.solr_client = None
            self.warn('@@@@@@@@@@@@@@@@@@@@@@@@@ core_name=%s not in SOLR_COREMAP', core_name)

    def search_index(self, query_str, **kwargs):
        self.debug('>>> start search_index <<<')
        docs = None
        if self.solr_client:
            normal_query_str = self._escape_str(unicode2str(query_str))
            self.debug("need_query_seg=False, query_str=%s, kwargs=%s",
                       normal_query_str, json.dumps(kwargs, ensure_ascii=False))

            docs = self.solr_client.search(normal_query_str, **kwargs)
        else:
            self.warn('@@@@@@@@@@@@@@@@@@@@@@ solr_client is None')
        self.debug('>>> end search_index <<<')
        return docs

    def _escape_str(self, query_str):
        self.debug('>>> start _escape_str <<<')
        escape_query = query_str
        for escape_key in self.escape_pattern.keys():
            if escape_key in escape_query:
                escape_query.replace(escape_key, self.escape_pattern[escape_key])
        self.debug('query_str=%s', query_str)
        self.debug('escape_result=%s', escape_query)
        self.debug('>>> end _escape_str <<<')
        return escape_query

    def _escape_words(self, words):
        self.debug('>>> start _escape_words <<<')
        escape_words = words
        if escape_words:
            for escape_key in self.escape_pattern.keys():
                for idx, word in enumerate(escape_words):
                    if escape_key in escape_words:
                        escape_words[idx] = escape_key.replace(escape_key, self.escape_pattern[escape_key])
            self.debug('words=%s, escape_words=%s',
                       json.dumps(words, ensure_ascii=False), json.dumps(escape_words, ensure_ascii=False))
        else:
            self.warn('@@@@@@@@@@@@@@@@@@@@@ unexpected values words=[]')
        self.debug('>>> end _escape_words <<<')
        return escape_words

    def search_with_seg(self, query, **kwargs):
        self.debug(">>> start search_with_seg <<<")
        docs = None
        if self.solr_client:
            words = seg_doc_with_search(query)
            normal_words = [w.strip() for w in self._escape_words(words) if w.strip()]
            query_fields = kwargs.get("query_fields", [])
            search_fields = kwargs.get("search_fields", SOLR_DEFAULT_RETURN_FIELDS)
            rows = kwargs.get("rows", SOLR_DEFAULT_ROWS)
            extend_condition = kwargs.get("extend_condition", "")
            if normal_words:
                if query_fields:
                    query_list = list()
                    for field in query_fields:
                        field += ':'
                        query_str = "(" + " ".join([field + word for word in normal_words]) + ")"
                        query_list.append(query_str)
                else:
                    query_list = ["(" + " ".join(["*:" + word for word in normal_words]) + ")"]
                q = "+(%s)" % (" ".join(query_list))
                if extend_condition:
                    q += extend_condition
                self.debug("core=%s query_str='%s'", self.core_name, q)
                docs = self.solr_client.search(q, rows=rows, fl=','.join(search_fields))
            else:
                self.warn('@@@@@@@@@@@@@@@@@@@@@@@@@@@ unexpected value words_list=%s',
                          json.dumps(words))
        else:
            self.warn('@@@@@@@@@@@@@@@@@@@@@@ solr_client is None')
        self.debug(">>> end search_with_seg <<<")
        return docs

if __name__ == "__main__":
    _core_name = "biology-triple"
    _query_fields = ['attribute_date_index']
    solr_api = SolrAPIHandler(_core_name)
    _docs = solr_api.search_with_seg(u"胚胎是如何形成的", query_fields=_query_fields, extend_condition="+(attribute_name: name)")
    for doc in _docs:
        print '#' * 100
        for key in doc.keys():
            print key, doc[key]

    _docs = solr_api.search_index(query_str=u"*:*")
    for doc in _docs:
        print doc
