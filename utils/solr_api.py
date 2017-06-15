# -*- coding: utf-8 -*-
import json

import pysolr

from logger import BaseLogger
from utils import seg_doc_with_search
from config import SOLR_CORE_MAP, SOLR_DEFAULT_ROWS, SOLR_DEFAULT_RETURN_FIELDS


class SolrAPIHandler(BaseLogger):
    def __init__(self, core_name):
        super(SolrAPIHandler, self).__init__()
        self.core_name = core_name
        self.debug('init solr_client core_name=%s', core_name)
        self.core = SOLR_CORE_MAP.get(core_name, "")
        if self.core:
            self.solr_client = pysolr.Solr(self.core)
        else:
            self.solr_client = None
            self.warn('@@@@@@@@@@@@@@@@@@@@@@@@@ core_name=%s not in SOLR_COREMAP', core_name)

    def search_index(self, query_str, **kwargs):
        self.debug('>>> start search_index <<<')
        docs = None
        if self.solr_client:
            self.debug("need_query_seg=False, query_str=%s, kwargs=%s", query_str, json.dumps(kwargs, ensure_ascii=False))
            docs = self.solr_client.search(query_str.encode("utf-8"), **kwargs)
        else:
            self.warn('@@@@@@@@@@@@@@@@@@@@@@ solr_client is None')
        self.debug('>>> end search_index <<<')
        return docs

    def search_with_seg(self, query, **kwargs):
        self.debug(">>> start search_with_seg <<<")
        docs = None
        if self.solr_client:
            words_list = seg_doc_with_search(query)
            query_fields = kwargs.get("query_fields", [])
            search_fields = kwargs.get("search_fields", SOLR_DEFAULT_RETURN_FIELDS)
            rows = kwargs.get("rows", SOLR_DEFAULT_ROWS)
            if query_fields:
                query_list = list()
                for field in query_fields:
                    field += ':'
                    query_str = "(" + " ".join([field + word for word in words_list]) + ")"
                    query_list.append(query_str)
            else:
                query_list = ["(" + " ".join(["*:" + word for word in words_list]) + ")"]
            q = "(%s)" % (" ".join(query_list))
            self.debug("core=%s query_str='%s'", self.core_name, q)
            self.debug("query_fields=%s, search_fields=%s, rows=%s",
                       json.dumps(query_fields, ensure_ascii=False),
                       json.dumps(search_fields, ensure_ascii=False),
                       rows)
            docs = self.solr_client.search(q, rows=rows, fl=','.join(search_fields))
        else:
            self.warn('@@@@@@@@@@@@@@@@@@@@@@ solr_client is None')
        self.debug(">>> end search_with_seg <<<")
        return docs

if __name__ == "__main__":
    _core_name = "biology-triple"
    _query_fields = ['triple_subject_index']
    solr_api = SolrAPIHandler(_core_name)
    _docs = solr_api.search_with_seg(u"胚胎是如何形成的", query_fields=_query_fields)
    for doc in _docs:
        print '#' * 100
        for key in doc.keys():
            print key, doc[key]

    _docs = solr_api.search_index(query_str=u"*:*")
    for doc in _docs:
        print doc
