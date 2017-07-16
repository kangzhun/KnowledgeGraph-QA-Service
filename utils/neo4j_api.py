# -*- coding: utf-8 -*-
import json

from py2neo import authenticate, Graph
from pymongo import MongoClient

from config import NEO4J_HOST_PORT, NEO4J_USER, NEO4J_PWD, NEO4J_URL, MONGODB_HOST, MONGODB_PORT, MONGODB_DBNAME, \
    MONGODB_BIOLOGY_PROPERTY
from const import CYPER_SUBJECT_TEMPLATE, CYPER_OBJECT_TEMPLATE
from utils import str2unicode
from utils.logger import BaseLogger


class KnowledgeDBAPI(BaseLogger):
    def __init__(self):
        super(KnowledgeDBAPI, self).__init__()
        self.debug('start init neo4j, host_port=%s, url=%s',
                   NEO4J_HOST_PORT, NEO4J_URL)
        authenticate(NEO4J_HOST_PORT, NEO4J_USER, NEO4J_PWD)
        self.graph = Graph(NEO4J_URL)
        self.debug('start connected mongodb, host=%s, port=%s, db_name=%s, collection_name=%s',
                   MONGODB_HOST, MONGODB_PORT, MONGODB_DBNAME, MONGODB_BIOLOGY_PROPERTY)
        client = MongoClient(MONGODB_HOST, MONGODB_PORT)
        db = client.get_database(MONGODB_DBNAME)
        self.property_collection = db.get_collection(MONGODB_BIOLOGY_PROPERTY)

    def query_node_property(self, triple_subject, triple_predicate, triple_object):
        """
        根据三元组查询节点的属性
        :param triple_subject: 三元组--主语
        :param triple_predicate: 三元组--谓语
        :param triple_object: 三元组--宾语
        :return:
        """
        self.debug('>>> start search_node_info <<<')
        ret = {}
        self.debug('search node with triple_subject=%s, triple_predicate=%s, triple_object=%s',
                   triple_subject, triple_predicate, triple_object)
        if triple_subject and triple_predicate:  # 缺失宾语的情况
            condition_template = CYPER_SUBJECT_TEMPLATE['node_property']
            condition = condition_template % (triple_subject, triple_predicate, triple_predicate)
            self.debug('condition=%s', condition)
            try:
                knowledge_search_result = self.graph.run(condition).data()
                ret = self._normalize_knowledge_doc(knowledge_search_result)
            except Exception, e:
                self.error('knowledge db query failed, query=%s', condition)
            if not ret:  # 若检索triple_subject未得到答案，检索与triple_subject节点的同等关系节点
                self.debug("start search %s's equal nodes", triple_subject)
                condition_template = CYPER_SUBJECT_TEMPLATE['equal_node_property']
                condition = condition_template % (triple_subject, triple_predicate, triple_predicate)
                self.debug('condition=%s', condition)
                try:
                    knowledge_search_result = self.graph.run(condition).data()
                    ret = self._normalize_knowledge_doc(knowledge_search_result)
                except Exception, e:
                    self.error('knowledge db query failed, query=%s', condition)
        elif triple_object and triple_predicate:  # 缺失主语的情况(根据节点属性查询节点名，是否全文检索更合适)
            condition_template = CYPER_OBJECT_TEMPLATE['node_name']
            condition = condition_template % (triple_predicate, triple_object, triple_predicate)
            self.debug('condition=%s', condition)
            try:
                knowledge_search_result = self.graph.run(condition).data()
                ret = self._normalize_knowledge_doc(knowledge_search_result)
            except Exception, e:
                self.error('knowledge db query failed, query=%s', condition)
        else:
            self.warn("@@@@@@@@@@@@@@ can't handle (triple_subject=%s, triple_predicate=%s, triple_object=%s)",
                      triple_subject, triple_predicate, triple_object)
        self.debug('>>> end search_node_info <<<')
        return ret

    def query_node_relation(self, triple_subject, triple_predicate, triple_object, query_property):
        """
        根据三元组查询节点的链接节点（或节点的某个属性值）
        :param triple_subject: 三元组--主语
        :param triple_predicate: 三元组--谓语
        :param triple_object: 三元组--宾语
        :param query_property:主语或宾语属性值（name或其他属性值）
        :return:
        """
        self.debug('>>> start search_neighbors_info <<<')
        knowledge_search_result = {}
        self.debug('search node with triple_subject=%s, triple_predicate=%s, triple_object=%s',
                   triple_subject, triple_predicate, triple_object)
        if triple_subject and triple_predicate:  # 缺失宾语的情况
            condition_template = CYPER_SUBJECT_TEMPLATE['node_relation_property']
            condition = condition_template % (triple_subject, triple_predicate, query_property, triple_predicate)
            self.debug('condition=%s', condition)
            try:
                knowledge_search_result = self.graph.run(condition).data()
            except Exception, e:
                self.error('knowledge db query failed, query=%s', condition)

        elif triple_object and triple_predicate:  # 缺失宾语的情况
            condition_template = CYPER_OBJECT_TEMPLATE['node_relation_property']
            condition = condition_template % (triple_predicate, triple_object, query_property, triple_predicate)
            self.debug('condition=%s', condition)
            try:
                knowledge_search_result = self.graph.run(condition).data()
            except Exception, e:
                self.error('knowledge db query failed, query=%s', condition)

        ret = self._normalize_knowledge_doc(knowledge_search_result)
        self.debug('>>> end search_neighbors_info <<<')
        return ret

    def search_with_triple(self, triple_doc, **kwargs):
        """
        根据三元组查询节点
        :param triple_doc: 三元组信息
        :param kwargs: 扩展信息（关联节点属性描述）
        :return:
        """
        self.debug('>>> start search_with_triple <<<')
        ret = {}
        if triple_doc:
            triple_subject = str2unicode(triple_doc.get('subject', ""))       # 主语
            triple_object = str2unicode(triple_doc.get('object', ""))         # 宾语
            triple_predicates = triple_doc.get('predicate', [])               # 谓语（关系属性）
            query_property = kwargs.get("query_property", 'name')             # 用于查询关联节点的属性值，默认为name
            self.debug('triple_subject=%s, triple_predicates=%s, triple_object=%s, query_property=%s',
                       triple_subject, json.dumps(triple_predicates, ensure_ascii=False), triple_object, query_property)

            # 查询关系属性库确定关系属性的类型（数据关系还是对象关系）
            predicate_docs = self.property_collection.find({'uri': {'$in': triple_predicates}})
            for predicate_item in predicate_docs:  # 遍历谓语关系并检索neo4j
                predicate_type = predicate_item.get('type', '')
                predicate_value = str(predicate_item.get('uri', ''))
                self.debug('predicate_type=%s, predicate_value=%s', predicate_type, predicate_value)

                tmp_ret = {}
                if predicate_type == 'data':  # 谓语为数据关系
                    tmp_ret = self.query_node_property(triple_subject, predicate_value, triple_object)
                elif predicate_type == 'object':  # 谓语为对象关系
                    tmp_ret = self.query_node_relation(triple_subject, predicate_value, triple_object, query_property)
                else:
                    self.warn('@@@@@@@@@@@@@@@@@@@@@@@@ unexpected value, predicate_type is None')
                ret = dict(ret, **tmp_ret)
        else:
            self.warn('@@@@@@@@@@@@@@@@@@@@ unexpected value, triple_doc is None')
        self.debug('>>> end search_with_triple <<<')
        return ret

    def search_with_query(self, query_str):
        """
        根据查询问句进行查询
        :param query_str:图数据库查询问句
        :return:查询结果
        """
        self.debug('>>> start search_with_query <<<')
        knowledge_search_result = []
        try:
            self.debug('condition=%s', query_str)
            knowledge_search_result = self.graph.run(query_str).data()
        except Exception, e:
            self.error('knowledge db query failed, query=%s', query_str)
        ret = self._normalize_knowledge_doc(knowledge_search_result)
        self.debug('>>> end search_with_query <<<')
        return ret

    def _normalize_knowledge_doc(self, knowledge_doc):
        """
        格式化neo4j检索的答案
        :param knowledge_doc: 知识库查询结果
        :return: 格式化后的结果
        """
        self.debug('>>> start _normalize_knowledge_doc <<<')
        ret = {}
        if knowledge_doc:
            self.debug('knowledge_doc=%s', json.dumps(knowledge_doc, ensure_ascii=False))
            for doc in knowledge_doc:
                for key in doc.keys():
                    value = doc[key]
                    if value:
                        if key not in ret.keys():
                            if isinstance(value, list):
                                ret[key] = value
                            else:
                                ret[key] = [value]
                        else:
                            if isinstance(value, list):
                                ret[key].extend(value)
                            else:
                                ret[key].append(value)
        else:
            self.warn('@@@@@@@@@@@@@@@@@@@@@@@ unexpected value, docs=None')
        self.debug('>>> end _normalize_knowledge_doc <<<')
        return ret

    def search(self, triple_doc={}, query_str=""):
        """
        知识图谱查询接口
        :param triple_doc: 查询三元组
        :param query_str: 查询问句
        :return: 查询结果（字典形式）
        """
        self.debug('>>> start search <<<')
        answer = {}
        if triple_doc:
            answer = self.search_with_triple(triple_doc)
        elif query_str:
            answer = self.search_with_query(query_str)
        else:
            self.warn('@@@@@@@@@@@@@@@@@@@@@@@ unexpected value， triple_doc=%s, query_str=%s',
                      json.dumps(triple_doc), query_str)
        self.debug('>>> end search <<<')
        return answer


if __name__ == '__main__':
    knowledge_db = KnowledgeDBAPI()
    _triple_doc = {'subject': '桃花', 'predicate': ['COMMON_CONSISTEDOF', ], 'object': ""}
    _ret = knowledge_db.search(_triple_doc)
    print _ret

    _triple_doc = {'subject': '细胞凋亡', 'predicate': ['BIOLOGY_MECHANISM', 'BIOLOGY_CONCEPT'], 'object': ""}
    _ret = knowledge_db.search(_triple_doc)
    print _ret

    _triple_doc = {'subject': '', 'predicate': ['BIOLOGY_SECRETORY_FLUID'], 'object': "胆汁"}
    _ret = knowledge_db.search(_triple_doc)
    print _ret

    _query_str = "MATCH (node_a {name: '桃花'})-[r: COMMON_CONSISTEDOF]->(node_b) RETURN node_b.name as name"
    _ret = knowledge_db.search(query_str=_query_str)
    print _ret
