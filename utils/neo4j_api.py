# -*- coding: utf-8 -*-
import json

from py2neo import authenticate, Graph
from pymongo import MongoClient

from config import NEO4J_HOST_PORT, NEO4J_USER, NEO4J_PWD, NEO4J_URL, MONGODB_HOST, MONGODB_PORT, MONGODB_DBNAME, \
    MONGODB_KNOWLEDGE_PROPERTY
from const import CYPER_TEMPLATE
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
        self.debug('search node with name=%s, property=%s', name, node_property)
        if name and node_property:
            condition = CYPER_TEMPLATE['node_property'] % (str2unicode(name), node_property)
            self.debug('condition=%s', condition)
            data = self.graph.run(condition).data()
            docs = self._extract_answer(data)
            if docs:
                self.debug('got node=%s, answer=%s', name, json.dumps(docs))
            else:
                self.debug('search equal_node name=%s, property=%s', name, node_property)
                condition = CYPER_TEMPLATE['equal_node_property'] % (str2unicode(name), node_property)
                self.debug('condition=%s', condition)
                data = self.graph.run(condition).data()
                docs = self._extract_answer(data)
                self.debug('got equal_node=%s, answer=%s', name, json.dumps(docs))
        else:
            self.warn('@@@@@@@@@@@@@@ unexpected name=%s, property=%s', name, node_property)
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
                condition = CYPER_TEMPLATE['neighbors_property'] % \
                            (str2unicode(name), relationship, node_property)
            else:
                condition = CYPER_TEMPLATE['neighbors_data'] % \
                            (str2unicode(name), relationship)
            self.debug('condition=%s', condition)
            data = self.graph.run(condition).data()
            docs = self._extract_answer(data)
            self.debug('got name=%s, answer=%s', name, json.dumps(docs))
        else:
            self.warn('@@@@@@@@@@@@@@ name is None')
        self.debug('>>> end search_neighbors_info <<<')
        return docs

    def search_with_triple(self, subject, predicates):
        pass

    def search_with_query(self, query_str):
        self.debug('>>> start search_with_query_info <<<')
        self.debug('search node with query_str%s', query_str)
        data = self.graph.run(query_str).data()
        docs = self._extract_answer(data)
        if docs:
            self.debug('answer=%s', json.dumps(docs))
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
                            self.debug('key=%s, value=%s', key, json.dumps(value))
                            if isinstance(value, list):
                                ret[key] = value
                            else:
                                ret[key] = [value]
                        else:
                            self.warn('@@@@@@@@@@@@@@@@@@@@@@@ key=%s, value=None')
                    else:
                        if value:
                            self.debug('key=%s, value=%s', key, json.dumps(value))
                            if isinstance(value, list):
                                ret[key].extend(value)
                            else:
                                ret[key].append(value)
                        else:
                            self.warn('@@@@@@@@@@@@@@@@@@@@@@@ key=%s, value=None')
        else:
            self.warn('@@@@@@@@@@@@@@@@@@@@@@@ docs=None')
        return ret

    def search(self, subject="", predicates=[], query_str=""):
        answer = {}
        self.debug('>>> start search <<<')
        if not query_str:
            self.debug('subject=%s, predicate=%s', subject, json.dumps(predicates))
            predicate_docs = self.property_collection.find({'uri': {'$in': predicates}})
            if predicate_docs:
                for doc_item in predicate_docs:
                    tmp_answer = {}
                    if doc_item:  # 谓语存在则进行查询
                        predicate_type = doc_item.get('type', '')
                        predicate_value = unicode2str(doc_item.get('uri', ''))
                        self.debug('predicate_type=%s, predicate_value=%s',
                                   predicate_type, predicate_value)
                        if predicate_type == 'data_relationship':  # 谓语属于数据关系
                            tmp_answer = self.search_node_info(subject, node_property=predicate_value)
                        elif predicate_type == 'object_relationship':  # 谓语属于对象关系
                            tmp_answer = self.search_neighbors_info(subject, predicate_value,
                                                                    node_property='name')
                        else:
                            self.warn('@@@@@@@@@@@@@@@@@@@@@@@@ predicate_type is None')
                    answer = dict(answer, **tmp_answer)
            else:
                self.warn('@@@@@@@@@@@@@@@@@@@@ predicates=%s, do not match', json.dumps(predicates))
        else:
            answer = self.search_with_query(query_str)
        return answer


if __name__ == '__main__':
    knowledge_db = KnowledgeDBAPI()
    _ret = knowledge_db.search('桃花', ['common_consistedOf', ])
    print _ret

    _ret = knowledge_db.search('细胞凋亡', ['biology_mechanism', 'biology_concept'])
    print _ret

    _query_str = "MATCH (n {name: '桃花'})-[r: common_consistedOf]-(neighbors) RETURN neighbors.name"
    _ret = knowledge_db.search(query_str=_query_str)
    print _ret
