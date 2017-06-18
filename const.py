# -*- coding: utf-8 -*-

CYPER_TEMPLATE = {
    "node_property": u"MATCH (node {name: '%s'}) RETURN node.%s",
    "equal_node_property": u"MATCH (node {name: '%s'})-[r: 等同]-(equal_node) RETURN equal_node.%s",
    "all_node": u"MATCH (node) RETURN node",
    "node_data": u"MATCH (node {name: '%s'})-[]-(neighbors) RETURN node, neighbors",
    "neighbors_property": u"MATCH (n {name: '%s'})-[r: %s]-(neighbors) RETURN neighbors.%s",
    "neighbors_data": u"MATCH (n {name: '%s'})-[r: %s]-(neighbors) RETURN neighbors.name",
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
