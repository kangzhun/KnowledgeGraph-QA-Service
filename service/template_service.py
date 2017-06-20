# -*- coding: utf-8 -*-
import json
import re

from config import TEMPLATE_CORE_NAME, TRIPLE_CORE_NAME
from const import TRIPLE_MATCH_THRESHOLD
from service import longest_common_substring
from utils import str2unicode, normalize_query, seg_doc
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

    def _sort_retrieval_docs(self, sentence, triple_docs, target_field):
        self.debug('>>> start _sort_retrieval_docs <<<')
        words, tags = seg_doc(sentence)
        sentence_words = [w.strip() for w in words if w.strip()]
        target_field_map = {"triple_object": "triple_subject_index",
                            "triple_subject": "triple_subject_index"}
        doc_sentence_dict = dict()
        match_triple_docs = list()
        for doc_item in triple_docs:
            doc_sentence = doc_item.get(target_field_map[target_field], "")
            if doc_sentence not in doc_sentence_dict.keys():
                doc_words = [w.strip() for w in doc_sentence.split()]
                self.debug('sentence_words=%s, doc_words=%s',
                           json.dumps(sentence_words, ensure_ascii=False), json.dumps(doc_words, ensure_ascii=False))
                sub_string, length = longest_common_substring(sentence_words, doc_words)
                score = len(sub_string)/float(len(doc_words))
                doc_item['score'] = score
                doc_item['length'] = len(doc_words)
                self.debug('score=%s, length=%s', doc_item['score'], doc_item['length'])
                doc_sentence_dict[doc_sentence] = (score, len(doc_words))
            else:
                doc_item['score'], doc_item['length'] = doc_sentence_dict[doc_sentence]
            if doc_item['score'] >= TRIPLE_MATCH_THRESHOLD:
                match_triple_docs.append(doc_item)
        if match_triple_docs:
            match_triple_docs.sort(key=lambda x: x['length'], reverse=True)
        else:
            self.warn("@@@@@@@@@@@@@@@@@@@@@@@@@ don't match any triple_docs, there is no such instance!!!!")
        self.debug('>>> end _sort_retrieval_docs <<<')
        return match_triple_docs

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
        triple_docs = self.triple_core.search_with_seg(sentence, query_fields=query_fields)
        if triple_docs:
            triple_docs = list(triple_docs)
            self.debug("got triple_docs=%s", len(triple_docs))
            sorted_triple_docs = self._sort_retrieval_docs(sentence, triple_docs, target_field)
            self.debug("got sorted_triple_docs=%s", len(sorted_triple_docs))
            if sorted_triple_docs:
                ret = sorted_triple_docs[0].get(target_field, '')
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
