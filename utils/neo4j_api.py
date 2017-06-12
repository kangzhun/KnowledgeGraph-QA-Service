# -*- coding: utf-8 -*-
import json

from py2neo import authenticate, Graph
from pymongo import MongoClient

from config import NEO4J_HOST_PORT, NEO4J_USER, NEO4J_PWD, NEO4J_URL, MONGODB_HOST, MONGODB_PORT, MONGODB_DBNAME, \
    MONGODB_KNOWLEDGE_PROPERTY
from const import CYPER_TEMPLATE
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

    def search(self, subject, predicate):
        answer = {}
        self.debug('>>> start search <<<')
        self.debug('subject=%s, predicate=%s', subject, predicate)
        predicate_doc = self.property_collection.find_one({'uri': predicate})
        if predicate_doc:  # 谓语存在则进行查询
            predicate_type = predicate_doc.get('type', '')
            self.debug('predicate_type=%s', predicate_type)
            if predicate_type == 'data_relationship':  # 谓语属于数据关系
                answer = self.search_node_info(subject, node_property=predicate)
            elif predicate_type == 'object_relationship':  # 谓语属于对象关系
                answer = self.search_neighbors_info(subject, predicate, node_property='name')
            else:
                self.warn('@@@@@@@@@@@@@@@@@@@@@@@@ predicate_type is None')
        else:
            self.warn('@@@@@@@@@@@@@@@@@@@@ predicate=%s, do not match', predicate)
        return answer


if __name__ == '__main__':
    knowledge_db = KnowledgeDBAPI()
    _ret = knowledge_db.search('桃花', 'common_consistedOf')
    print _ret
