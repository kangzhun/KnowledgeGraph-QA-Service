# -*- coding: utf-8 -*-
import json
import re

from config import TEMPLATE_CORE_NAME, TRIPLE_CORE_NAME
from utils import str2unicode, normalize_query
from utils.logger import BaseLogger
from utils.neo4j_api import KnowledgeDBAPI
from utils.solr_api import SolrAPIHandler


class TemplateBot(BaseLogger):
    def __init__(self, **kwargs):
        super(TemplateBot, self).__init__(**kwargs)
        self.query = ''
        self.template_core = SolrAPIHandler(TEMPLATE_CORE_NAME)  # solr问句模板core
        self.triple_core = SolrAPIHandler(TRIPLE_CORE_NAME)  # solr三元组core
        self.knowledge_db = KnowledgeDBAPI()  # 生物基础学科知识图谱

    def _match_predicate(self):
        self.debug('>>> start _match_predicate <<<')
        templates_docs = self.template_core.search_with_seg(self.query, query_fields=['key_index'],)
        docs = []
        if templates_docs:
            for tmp_item in templates_docs:
                pattern_str = tmp_item.get('pattern', '')
                predicates = tmp_item.get('predicates', [])
                priority = tmp_item.get('priority', 4)
                missing_tuple = tmp_item.get('missing_tuple', '')
                doc = {'pattern': pattern_str, 'predicates': predicates,
                       'priority': priority, 'missing_tuple': missing_tuple}
                pattern = re.compile(ur'%s' % pattern_str)
                is_match = pattern.match(str2unicode(self.query))
                if is_match:
                    self.debug('got match pattern=%s, predicates=%s, priority=%s, missing_tuple=%s',
                               pattern_str, json.dumps(predicates, ensure_ascii=False), priority, missing_tuple)
                    doc['match_str'] = is_match.group('title')
                    if priority > 1:
                        docs.append(doc)
                    else:
                        docs = [doc, ]
                        self.debug(">>> end _match_predicate <<<")
                        return docs
                else:
                    self.debug("don't match pattern%s", pattern_str)
            else:
                self.warn('@@@@@@@@@@@@@@@@@@@@@@ unexpected values templates_docs=None')
        self.debug(">>> end _match_predicate <<<")
        return docs

    def _match_subject_and_object(self, sentence, missing_triple):
        self.debug('>>> start _match_subject_and_object <<<')
        self.debug('sentence=%s, missing_triple=%s', sentence, missing_triple)
        ret = ''
        if missing_triple == 'object':
            target_field = 'triple_subject'
            query_fields = ['triple_subject_index']
        elif missing_triple == 'subject':
            target_field = 'triple_object'
            query_fields = ['triple_subject_index']
        else:
            self.debug('@@@@@@@@@@@@@@@@@@@@@@@@@@@ unexpected values missing_triple=%s', missing_triple)
            return ret
        self.debug('target_field=%s, query_fields=%s', target_field, json.dumps(query_fields))
        triple_docs = self.triple_core.search_with_seg(sentence, query_fields=query_fields, rows=1)
        if triple_docs:
            triple_docs = list(triple_docs)
            self.debug("got triple_docs=%s", json.dumps(triple_docs, ensure_ascii=False))
            ret = triple_docs[0].get(target_field, '')
            self.debug("got ret=%s", ret)
        else:
            self.warn("@@@@@@@@@@@@@@@@@@@@@@@@@@ triple_docs is None")
        self.debug(">>> end _match_subject_and_object <<<")
        return ret

    def get_triple(self):
        self.debug('>>> start get_triple <<<')
        template_docs = self._match_predicate()
        triple_docs = list()
        for doc in template_docs:
            missing_tuple = doc.get('missing_tuple', '')
            match_str = doc.get('match_str', '')
            predicates = doc.get('predicates', [])
            if missing_tuple == 'subject':
                triple_object = self._match_subject_and_object(match_str, missing_tuple)
                triple_doc = {'subject': "", 'predicate': predicates, 'object': triple_object}
                triple_docs.append(triple_doc)
            elif missing_tuple == 'object':
                triple_subject = self._match_subject_and_object(match_str, missing_tuple)
                triple_doc = {'subject': triple_subject, 'predicate': predicates, 'object': ""}
                triple_docs.append(triple_doc)
            else:
                self.warn('@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ unexpected value missing_tuple=%s', missing_tuple)
        self.debug('triple_docs=%s', json.dumps(triple_docs, ensure_ascii=False))
        self.debug('>>> end get_triple <<<')
        return triple_docs

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
            triple_docs = self.get_triple()
            answer = self.knowledge_db.search(triple_doc=triple_docs)
        else:
            self.warn("@@@@@@@@@@@@@@@@@@@ unexpected query is None")
        if answer:
            ret = []
            for key in answer.keys():
                ret.append(' '.join(answer[key]))
            ret = '\n'.join(ret)
        else:
            ret = ''
        self.debug("[end] query=%s", self.query)
        return ret
