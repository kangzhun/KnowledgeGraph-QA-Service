# -*- coding: utf-8 -*-
import json
import re
from math import exp

from config import TEMPLATE_CORE_NAME, TRIPLE_CORE_NAME
from const import TRIPLE_MATCH_THRESHOLD, DEFAULT_SUBJECT_SYNONYM, DEFAULT_WMD_THRESHOLD, DEFAULT_TEMPLATE_PRIORITY
from service import longest_common_substring, calculate_wmd
from utils import str2unicode, normalize_query, seg_doc, load_entity_synonym, unicode2str
from utils.logger import BaseLogger
from utils.neo4j_api import KnowledgeDBAPI
from utils.solr_api import SolrAPIHandler


class TemplateBot(BaseLogger):
    def __init__(self, **kwargs):
        super(TemplateBot, self).__init__(**kwargs)
        self.debug('>>> init TemplateBot <<<')
        self.query = ''
        self.template_core = SolrAPIHandler(TEMPLATE_CORE_NAME)  # solr问句模板core
        self.triple_core = SolrAPIHandler(TRIPLE_CORE_NAME)      # solr三元组core
        self.knowledge_db = KnowledgeDBAPI()                     # 生物学科知识图谱
        self.entity_synonym = load_entity_synonym(DEFAULT_SUBJECT_SYNONYM)

    def _match_predicate(self):
        """
        基于模板匹配谓语
        :return:返回匹配到的谓语
        """
        self.debug('>>> start _match_predicate <<<')
        template_docs = self.template_core.search_with_seg(self.query, query_fields=['key_index'])
        match_template_docs = []
        if template_docs:
            for tmp_item in template_docs:
                pattern_str = tmp_item.get('pattern', '')                            # 模板的正则表达式
                predicates = tmp_item.get('predicates', [])                          # 模板对应的谓语
                priority = tmp_item.get('priority', DEFAULT_TEMPLATE_PRIORITY)       # 模板优先级，（1为精确匹配）
                missing_tuple = tmp_item.get('missing_tuple', '')  # 缺失的三元祖

                pattern = re.compile(ur'%s' % pattern_str)
                is_match = pattern.match(str2unicode(self.query))
                if is_match:  # 模板匹配，将其添加到match_template_docs中
                    doc = {'pattern': pattern_str, 'predicates': predicates,
                           'priority': priority, 'missing_tuple': missing_tuple}
                    self.debug("got match pattern=%s", pattern_str)
                    doc['title'] = is_match.group('title')
                    if priority != 1:  # 匹配到的模板不是精确模板，加入到match_template_docs
                        match_template_docs.append(doc)
                    else:              # 匹配到的模板是精确模板，仅返回精确匹配模板
                        self.debug('got precise pattern=%s')
                        match_template_docs = [doc, ]
                        break
                else:  # 模板未匹配
                    self.debug("don't match pattern=%s", pattern_str)
        else:
            self.warn('@@@@@@@@@@@@@@@@@@@@@@ unexpected value, templates_docs=None')
        self.debug(">>> end _match_predicate <<<")
        return match_template_docs

    def _sort_docs_by_subject(self, sentence, triple_docs):
        """
        基于最长公共子串进行排序
        :param sentence:
        :param triple_docs:
        :return:
        """
        self.debug('>>> start _sort_docs_by_subject <<<')
        words, tags = seg_doc(sentence)
        _words = [w.strip() for w in words if w.strip()]
        chosen_triple_docs = []
        for doc_item in triple_docs:
            item_str = doc_item.get('attribute_date', "")
            item_index = doc_item.get("attribute_date_index", "")
            item_words = [w.strip() for w in item_index.split()]

            sub_string, length = longest_common_substring(_words, item_words)  # 计算_words与item_words的最长公共子串
            scores = [len(sub_string) / float(len(item_words)), ]
            if item_str in self.entity_synonym:  # 若target_sentence在主语拓展库中，计算扩展主语与sentence的匹配度
                for extend_str in self.entity_synonym[item_str]:
                    _words, _tags = seg_doc(extend_str)
                    extend_str_words = [w.strip() for w in _words if w.strip()]
                    sub_string, length = longest_common_substring(_words, extend_str_words)
                    scores.append(len(sub_string) / float(len(extend_str_words)))
            doc_item['score'] = max(scores)  # 选取target_sentence及扩展主语与sentence的最大匹配分数作为最后分数
            doc_item['length'] = len(item_words)
            if doc_item['score'] >= TRIPLE_MATCH_THRESHOLD:  # 匹配度高于阈值选取该三元组
                self.debug('choose item_str=%s, score=%s, length=%s', item_str, doc_item['score'], doc_item['length'])
                chosen_triple_docs.append(doc_item)
            else:  # 匹配度低于阈值，过滤掉该三元组
                self.debug("filter item_str=%s, score=%s, length=%s", item_str, doc_item['score'], doc_item['length'])
        if chosen_triple_docs:  # 按length降序排序
            chosen_triple_docs.sort(key=lambda x: x['length'], reverse=True)
        self.debug('>>> end _sort_docs_by_subject <<<')
        return chosen_triple_docs

    def _sort_docs_by_object(self, sentence, triple_docs):
        """
        基于文档迁移距离对triple_docs进行重排
        :param sentence:
        :param triple_docs:
        :return:
        """
        self.debug('>>> start _sort_docs_by_object <<<')
        words, tags = seg_doc(sentence)
        _words = [w.strip() for w in words if w.strip()]
        match_triple_docs = list()  # 满足匹配阈值的triple_docs
        for doc_item in triple_docs:
            item_str = doc_item.get("attribute_date", "")
            item_index = doc_item.get("attribute_date_index", "")
            item_words = [w.strip() for w in item_index.split()]
            distance = calculate_wmd(_words, item_words)  # 计算文档迁移距离
            score = exp(-distance / 19.0)
            doc_item['score'] = score
            if doc_item['score'] > DEFAULT_WMD_THRESHOLD:  # 过滤掉距离大于阈值的三元组
                self.debug('choose item_str=%s, score=%s', item_str, doc_item['score'])
                match_triple_docs.append(doc_item)
            else:
                self.debug("filter item_str=%s, score=%s", item_str, doc_item['score'])
        if match_triple_docs:  # 按score降序排序
            match_triple_docs.sort(key=lambda x: x['score'], reverse=True)
        self.debug('>>> end _sort_docs_by_object <<<')
        return match_triple_docs

    def _match_retrieval_docs(self, sentence, triple_docs, missing_triple):
        """
        对检索得到的三元组进行排序和过滤
        :param sentence:
        :param triple_docs:
        :param missing_triple:
        :return:
        """
        self.debug('>>> start _match_retrieval_docs <<<')
        chosen_triple_docs = []
        if missing_triple == 'object':    # 缺失元组为object，则排序方式为_sort_docs_by_subject
            chosen_triple_docs = self._sort_docs_by_subject(sentence, triple_docs)
        elif missing_triple == 'subject':  # 缺失元组为subject，则排序方式为_sort_docs_by_object
            chosen_triple_docs = self._sort_docs_by_object(sentence, triple_docs)
        else:
            self.warn('@@@@@@@@@@@@@@@@@@@@@@ unexpected value, missing_triple=%s', missing_triple)
        self.debug('>>> end _match_retrieval_docs <<<')
        return chosen_triple_docs

    def _match_subject_and_object(self, sentence, missing_triple):
        """
        匹配sentence中包含的主语或宾语
        :param sentence:
        :param missing_triple:
        :return:
        """
        self.debug('>>> start _match_subject_and_object <<<')
        self.debug('sentence=%s, missing_triple=%s', sentence, missing_triple)
        triple_subject = ""
        triple_object = ""
        extend_condition = ""
        if missing_triple == 'object':   # 若缺失元组为object，设置solr附加查询条件
            extend_condition = '+(attribute_name: name)'
        triple_docs = self.triple_core.search_with_seg(sentence, query_fields=["attribute_date_index"],
                                                       rows=50, extend_condition=extend_condition)
        if triple_docs:
            sorted_triple_docs = self._match_retrieval_docs(sentence, triple_docs, missing_triple)
            if sorted_triple_docs:  # 选取sorted_triple_docs的top1作为结果
                ret = sorted_triple_docs[0].get("attribute_date", '')
                if missing_triple == 'object':
                    triple_subject = ret
                elif missing_triple == 'subject':
                    triple_object = ret
                self.debug("got triple_subject=%s, triple_object=%s", triple_subject, triple_object)
            else:
                self.warn('@@@@@@@@@@@@@@@@@@@@@@@@ unexpected value, sorted_triple_docs is None')
        else:
            self.warn("@@@@@@@@@@@@@@@@@@@@@@@@@@ unexpected value, triple_docs is None")
        self.debug(">>> end _match_subject_and_object <<<")
        return triple_subject, triple_object

    def get_triple(self):
        """
        获取与问句相关的三元组
        :return: 三元组(subject, predicate, object)，其中有一个值是缺失的
        """
        self.debug('>>> start get_triple <<<')
        template_docs = self._match_predicate()
        triple_docs = list()
        if template_docs:
            for doc in template_docs:  # 遍历匹配到的template_docs，生成查询三元组
                missing_tuple = doc.get('missing_tuple', '')  # 缺失三元组
                title = doc.get('title', '')  # 模板框定的title部分，用于检索可能的主语或宾语
                predicates = doc.get('predicates', [])  # 匹配模板对应的谓语
                priority = doc.get('priority', DEFAULT_TEMPLATE_PRIORITY)  # 模板优先级

                if missing_tuple in ['subject', 'object']:  # 缺失元组为主语或宾语
                    triple_subject, triple_object = self._match_subject_and_object(title, missing_tuple)
                    triple_doc = {'subject': triple_subject, 'predicate': predicates,
                                  'object': triple_object, 'priority': priority}
                    triple_docs.append(triple_doc)
        else:
            self.warn('@@@@@@@@@@@@@@@@@@@@@@@@@ unexpected value, template_docs=[]')
        self.debug('>>> end get_triple <<<')
        return triple_docs

    def get_answer(self, triple_docs):
        """
        根据匹配到的三元组检索知识库，并返回最终答案
        :param triple_docs: 检索得到的三元组
        :return: 知识库查询结果
        """
        self.debug('>>> start get_answer <<<')
        ret_docs = []
        ret = []
        if triple_docs:
            for triple_doc in triple_docs:
                tmp_ret = self.knowledge_db.search(triple_doc=triple_doc)
                if tmp_ret:
                    ret_docs.append((tmp_ret, triple_doc))
            if ret_docs:  # 按优先级升序排列
                ret_docs.sort(key=lambda x: x[1]['priority'], reverse=False)
        else:
            self.warn('@@@@@@@@@@@@@@@@@@@ unexpected value, triple_docs is None')
        if ret_docs:
            _doc, _doc_info = ret_docs[0]
            for key in _doc.keys():
                _subject = _doc_info.get("subject", "")
                _object = _doc_info.get("object", "")
                if _subject:
                    entity = _subject
                else:
                    entity = _object
                value = u"%s--%s:%s" % (entity, key, ",".join(_doc[key]))
                ret.append(value)
        else:
            self.warn('@@@@@@@@@@@@@@@@@@@ unexpected value, ret_docs is None')
        self.debug('>>> end get_answer <<<')
        return "\n".join(ret)

    def reply(self, query):
        """
        根据query返回答案
        :param query: 用户输入问句
        :return: 答案
        """
        answer = ""
        self.query = normalize_query(query)
        self.debug("[start TemplateBot reply]")
        self.debug('query=%s', self.query)

        if self.query:
            triple_docs = self.get_triple()  # 与问句可能相关的三元组
            answer = self.get_answer(triple_docs)
        else:
            self.warn("@@@@@@@@@@@@@@@@@@@ unexpected value, query is None")

        self.debug('answer=%s', answer)
        self.debug("[end TemplateBot reply]")
        return answer


if __name__ == '__main__':
    bot = TemplateBot()
    while 1:
        _query = raw_input('请输入问句：')
        _answer = bot.reply(_query)
        print _answer
