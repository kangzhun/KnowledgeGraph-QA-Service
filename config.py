# -*- coding: utf-8 -*-
import os

HERE = os.path.abspath(os.path.dirname(__file__))

# logger config
LOGGER_PATH = HERE
LOGGER_NAME = "knowledge_graph_qa_service.log"

# solr config
SOLR_HOST = "127.0.0.1"
SOLR_PORT = 8983
SOLR_SERVER = "http://%s:%s/solr" % (SOLR_HOST, SOLR_PORT)

TRIPLE_CORE_NAME = "biology-triple"
TRIPLE_CORE = "/".join([SOLR_SERVER, TRIPLE_CORE_NAME])

QUERY_CORE_NAME = "biology-qa"
QUERY_CORE = "/".join([SOLR_SERVER, QUERY_CORE_NAME])

TEMPLATE_CORE_NAME = "biology-template"
TEMPLATE_CORE = "/".join([SOLR_SERVER, TEMPLATE_CORE_NAME])

SOLR_CORE_MAP = {
    TRIPLE_CORE_NAME: TRIPLE_CORE,
    QUERY_CORE_NAME: QUERY_CORE,
    TEMPLATE_CORE_NAME: TEMPLATE_CORE,
}

SOLR_DEFAULT_ROWS = 50
SOLR_DEFAULT_RETURN_FIELDS = ['*', 'score']

# jieba_config
CUSTOM_DICTIONARY_PATH = os.path.join(HERE, "data/dictionary", "custom_dictionary.txt")

# neo4j config
NEO4J_HOST_PORT = "localhost:7474"
NEO4J_USER = "kangzhun"
NEO4J_PWD = "741953"
NEO4J_URL = "http://localhost:7474/db/data/"

# mongodb config
MONGODB_HOST = "127.0.0.1"
MONGODB_PORT = 27017
MONGODB_DBNAME = "biology-db"
MONGODB_KNOWLEDGE_TRIPLE = "biology-triple"
MONGODB_KNOWLEDGE_QUERY = "biology-query"
MONGODB_KNOWLEDGE_TEMPLATE = "biology-template"
MONGODB_KNOWLEDGE_PROPERTY = 'biology-property'
MONGODB_KNOWLEDGE_TEST_CORPUS = 'biology-test_corpus'
