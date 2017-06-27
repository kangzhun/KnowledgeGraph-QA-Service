# -*- coding: utf-8 -*-
import os

from config import HERE

CYPER_SUBJECT_TEMPLATE = {
    "node_property": u"MATCH (node {name: '%s'}) RETURN node.%s",
    "equal_node_property": u"MATCH (node {name: '%s'})-[r: 等同]-(equal_node) RETURN equal_node.%s",
    "all_node": u"MATCH (node) RETURN node",
    "node_data": u"MATCH (node {name: '%s'})-[]-(neighbors) RETURN node, neighbors",
    "neighbors_property": u"MATCH (n {name: '%s'})-[r: %s]-(neighbors) RETURN neighbors.%s",
    "neighbors_data": u"MATCH (n {name: '%s'})-[r: %s]-(neighbors) RETURN neighbors.name",
}
CYPER_OBJECT_TEMPLATE = {
    "node_name": u"MATCH (node {%s: '%s'}) RETURN node.name",
}


SOLR_ESCAPE_PATTERN = {"+": "\+",
                       "\\": "\\\\",
                       "!": "\!",
                       "/": "\/",
                       "^": "\^",
                       "-": "\-",
                       ":": "",
                       "(": "",
                       ")": "",
                       "~": "\~"}

TRIPLE_MATCH_THRESHOLD = 1.0

DEFAULT_WORDING_EMBEDDING_PATH = os.path.join(HERE, 'data/word_embedding',
                                              'word_embedding_2017-06-25-23:36:57.vec')
DEFAULT_WMD_THRESHOLD = 13.0

DEFAULT_SUBJECT_SYNONYM = os.path.join(HERE, 'data/dictionary', 'subject_synonym.txt')
