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
        templates_list = list(templates_docs)
        predicates = []
        self.debug("got templates_docs=%s", len(templates_docs))
        if templates_list:
            for tmp_item in templates_list:
                pattern_str = tmp_item.get('pattern', '')
                predicate_value = tmp_item.get('predicate_value', '')
                if pattern_str and predicate_value:
                    pattern = re.compile(ur'%s' % pattern_str)
                    is_match = pattern.match(str2unicode(self.query))
                    if is_match:
                        self.debug('got match pattern=%s, predicate_value=%s', pattern_str, predicate_value)
                        predicates.append(predicate_value)
                    else:
                        self.debug("don't match pattern%s", pattern_str)
                else:
                    self.warn('@@@@@@@@@@@@@@@@@@@@@@@ unexpected pattern_str=%s, predicate_value=%s',
                              pattern_str, predicate_value)
        else:
            self.debug("retrieved None templates_docs")
        self.warn("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ don't match any templates ")
        self.debug(">>> end _match_predicate <<<")
        return predicates

    def _match_subject(self):
        self.debug('>>> start _match_subject <<<')
        triple_docs = self.triple_core.search_with_seg(self.query, query_fields=['triple_subject_index'], rows=1)
        triple_list = list(triple_docs)
        subject_ret = ''
        self.debug("got triple_docs=%s", json.dumps(triple_list, ensure_ascii=False))
        if triple_list:
            subject_ret = triple_list[0].get('triple_subject', '')
            self.debug("got subject=%s", subject_ret)
        else:
            self.warn("@@@@@@@@@@@@@@@@@@@@@@@@@@ triple_docs is None")
        self.debug(">>> end _match_subject <<<")
        return subject_ret

    def reply(self, query):
        """
        根据query返回答案
        :param query: 用户输入问句
        :return: 答案
        """
        answer = {}
        self.query = normalize_query(query)
        self.debug("[ start ] query=%s", self.query)
        if self.query:
            predicates = self._match_predicate()  # 匹配谓语, 并把主语部分返回，用于后续检索主语
            subject = self._match_subject()
            if not subject:
                self.warn('@@@@@@@@@@@@@@@@@@@ unexpected subject is None')
            elif not predicates:
                self.warn('@@@@@@@@@@@@@@@@@@@ unexpected predicate is None')
            else:
                self.debug('start search knowledge_db with subject=%s, predicate=%s', subject, json.dumps(predicates))
                answer = self.knowledge_db.search(subject=subject, predicates=predicates)
        else:
            self.warn("@@@@@@@@@@@@@@@@@@@ unexpected query is None")
        if answer:
            ret = []
            for key in answer.keys():
                ret.append(' '.join(answer[key]))
            ret = '\n'.join(ret)
        else:
            ret = ''
        return ret
