# -*- coding: utf-8 -*-
import json

from py2neo import authenticate, Graph
from pymongo import MongoClient

from config import NEO4J_HOST_PORT, NEO4J_USER, NEO4J_PWD, NEO4J_URL, MONGODB_HOST, MONGODB_PORT, MONGODB_DBNAME, \
    MONGODB_KNOWLEDGE_PROPERTY
from const import CYPER_SUBJECT_TEMPLATE, CYPER_OBJECT_TEMPLATE
from utils import str2unicode, unicode2str
from utils.logger import BaseLogger


class KnowledgeDBAPI(BaseLogger):
    def __init__(self):
        super(KnowledgeDBAPI, self).__init__()
        self.debug('start init neo4j, host_port=%s, url=%s',
                   NEO4J_HOST_PORT, NEO4J_URL)
        authenticate(NEO4J_HOST_PORT, NEO4J_USER, NEO4J_PWD)
        self.graph = Graph(NEO4J_URL)
        self.debug('start connected mongodb, host=%s, port=%s, db_name=%s, collection_name=%s',
                   MONGODB_HOST, MONGODB_PORT, MONGODB_DBNAME, MONGODB_KNOWLEDGE_PROPERTY)
        client = MongoClient(MONGODB_HOST, MONGODB_PORT)
        db = client.get_database(MONGODB_DBNAME)
        self.property_collection = db.get_collection(MONGODB_KNOWLEDGE_PROPERTY)

    def search_node_info(self, name, **kwargs):
        docs = {}
        self.debug('>>> start search_node_info <<<')
        node_property = kwargs.get('node_property', '')
        triple_object = kwargs.get('triple_object', '')
        self.debug('search node with name=%s, property=%s, object=%s', name, node_property, triple_object)
        if name and node_property:
            condition = CYPER_SUBJECT_TEMPLATE['node_property'] % (str2unicode(name), node_property)
            self.debug('condition=%s', condition)
            try:
                data = self.graph.run(condition).data()
            except Exception, e:
                self.error('illegal query=%s', condition)
                data = {}
            docs = self._extract_answer(data)
            if not docs:
                self.debug('search equal_node name=%s, property=%s', name, node_property)
                condition = CYPER_SUBJECT_TEMPLATE['equal_node_property'] % (str2unicode(name), node_property)
                self.debug('condition=%s', condition)
                try:
                    data = self.graph.run(condition).data()
                except Exception, e:
                    self.error('illegal query=%s', condition)
                    data = {}
                docs = self._extract_answer(data)
        elif triple_object and node_property:
            condition = CYPER_OBJECT_TEMPLATE['node_name'] % (node_property, str2unicode(triple_object))
            self.debug('condition=%s', condition)
            try:
                data = self.graph.run(condition).data()
            except Exception, e:
                self.error('illegal query=%s', condition)
                data = {}
            docs = self._extract_answer(data)
        else:
            self.warn('@@@@@@@@@@@@@@ unexpected name=%s, property=%s, triple_object=%s',
                      name, node_property, triple_object)
        self.debug('>>> end search_node_info <<<')
        return docs

    def search_neighbors_info(self, name, relationship, **kwargs):
        docs = {}
        self.debug('>>> start search_neighbors_info <<<')
        node_property = kwargs.get('node_property', '')
        if node_property:
            self.debug('search node name=%s, relationship=%s, property=%s',
                       name, relationship, node_property)
        else:
            self.debug('search node name=%s, relationship=%s', name, relationship)
        if name:
            if node_property:
                condition = CYPER_SUBJECT_TEMPLATE['neighbors_property'] % \
                            (str2unicode(name), relationship, node_property)
            else:
                condition = CYPER_SUBJECT_TEMPLATE['neighbors_data'] % \
                            (str2unicode(name), relationship)
            self.debug('condition=%s', condition)
            try:
                data = self.graph.run(condition).data()
            except Exception, e:
                self.error('illegal query=%s', condition)
                data = {}
            docs = self._extract_answer(data)
        else:
            self.warn('@@@@@@@@@@@@@@ name is None')
        self.debug('>>> end search_neighbors_info <<<')
        return docs

    def search_with_triple(self, triple_doc):
        self.debug('>>> start search_with_triple <<<')
        self.debug('triple_doc=%s', len(triple_doc))
        answer = {}
        if triple_doc:
            for triple_item in triple_doc:
                tmp_answer = {}
                triple_subject = triple_item.get('subject', "")
                triple_object = triple_item.get('object', "")
                triple_predicates = triple_item.get('predicate', [])
                self.debug('triple_predicates=%s', json.dumps(triple_predicates, ensure_ascii=False))
                predicate_doc = self.property_collection.find({'uri': {'$in': triple_predicates}})
                for predicate_item in predicate_doc:
                    predicate_type = predicate_item.get('type', '')
                    predicate_value = unicode2str(predicate_item.get('uri', ''))
                    self.debug('predicate_type=%s, predicate_value=%s', predicate_type, predicate_value)
                    if predicate_type == 'data_relationship':  # 谓语属于数据关系
                        if triple_subject:
                            tmp_answer = self.search_node_info(triple_subject, node_property=predicate_value)
                        elif triple_object:
                            tmp_answer = self.search_node_info(triple_subject,
                                                               node_property=predicate_value,
                                                               triple_object=triple_object)
                    elif predicate_type == 'object_relationship':  # 谓语属于对象关系
                        if triple_subject:
                            tmp_answer = self.search_neighbors_info(triple_subject, predicate_value,
                                                                    node_property='name')
                        elif triple_object:
                            pass
                    else:
                        self.warn('@@@@@@@@@@@@@@@@@@@@@@@@ predicate_type is None')
                    answer = dict(answer, **tmp_answer)
        else:
            self.warn('@@@@@@@@@@@@@@@@@@@@ unexpected value triple_doc=', json.dumps(triple_doc, ensure_ascii=False))
        self.debug('>>> end search_with_triple <<<')
        return answer

    def search_with_query(self, query_str):
        self.debug('>>> start search_with_query_info <<<')
        self.debug('search node with query_str=%s', query_str)
        try:
            data = self.graph.run(query_str).data()
        except Exception, e:
            self.error('illegal query=%s', query_str)
            data = {}
        docs = self._extract_answer(data)
        self.debug('>>> end search_with_query_info <<<')
        return docs

    def _extract_answer(self, docs):
        ret = {}
        if docs:
            self.debug('docs=%s', json.dumps(docs, ensure_ascii=False))
            for doc in docs:
                for key in doc.keys():
                    value = doc[key]
                    if key not in ret.keys():
                        if value:
                            self.debug('key=%s, value=%s', key, json.dumps(value, ensure_ascii=False))
                            if isinstance(value, list):
                                ret[key] = value
                            else:
                                ret[key] = [value]
                        else:
                            self.warn('@@@@@@@@@@@@@@@@@@@@@@@ key=%s, value=None')
                    else:
                        if value:
                            self.debug('key=%s, value=%s', key, json.dumps(value, ensure_ascii=False))
                            if isinstance(value, list):
                                ret[key].extend(value)
                            else:
                                ret[key].append(value)
                        else:
                            self.warn('@@@@@@@@@@@@@@@@@@@@@@@ key=%s, value=None')
        else:
            self.warn('@@@@@@@@@@@@@@@@@@@@@@@ unexpected values docs=None')
        self.debug('ret=%s', json.dumps(ret, ensure_ascii=False))
        return ret

    def search(self, triple_doc=[], query_str=""):
        self.debug('>>> start search <<<')
        answer = {}
        if triple_doc:
            answer = self.search_with_triple(triple_doc)
        elif query_str:
            answer = self.search_with_query(query_str)
        else:
            self.warn('@@@@@@@@@@@@@@@@@@@@@@@ unexpected values triple_doc=%s, query_str=%s',
                      json.dumps(triple_doc), query_str)
        self.debug('>>> end search <<<')
        return answer


if __name__ == '__main__':
    knowledge_db = KnowledgeDBAPI()
    _triple_doc = [{'subject': '桃花', 'predicate': ['common_consistedOf', ], 'object': ""}]
    _ret = knowledge_db.search(_triple_doc)
    print _ret

    _triple_doc = [{'subject': '细胞凋亡', 'predicate': ['biology_mechanism', 'biology_concept'], 'object': ""}]
    _ret = knowledge_db.search(_triple_doc)
    print _ret

    _triple_doc = [{'subject': '', 'predicate': ['biology_Secretory_fluid'], 'object': "胆汁"}]
    _ret = knowledge_db.search(_triple_doc)
    print _ret

    _query_str = "MATCH (n {name: '桃花'})-[r: common_consistedOf]-(neighbors) RETURN neighbors.name"
    _ret = knowledge_db.search(query_str=_query_str)
    print _ret
