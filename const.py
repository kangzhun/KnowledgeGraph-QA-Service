# -*- coding: utf-8 -*-
import os

from config import HERE

# 主语的查询模板
CYPER_SUBJECT_TEMPLATE = {
    # 根据name查询节点，返回节点指定的属性
    "node_property": u"MATCH (node {name: '%s'}) RETURN node.%s as %s",
    # 根据name查询节点，再查询与其关系为COMMON_SAMEAS（等同关系）的节点，返回等同节点的指定属性值
    "equal_node_property": u"MATCH (node {name: '%s'})-[r: COMMON_SAMEAS]-(equal_node) RETURN equal_node.%s as %s",
    # 根据name查询节点，再查询特定关系的关联节点，返回关联节点的指定属性值
    "node_relation_property": u"MATCH (node_a {name: '%s'})-[r: %s]->(node_b) RETURN node_b.%s as %s",
    # 根据name查询节点，返回节点的属性和关联节点
    "node_info": u"MATCH (node {name: '%s'})-[relations]->(relation_nodes) RETURN node, relations, relation_nodes",
}

# 宾语查询模板
CYPER_OBJECT_TEMPLATE = {
    "node_name": u"MATCH (node {%s: '%s'}) RETURN node.name as %s",
    # 根据name查询节点，再查询特定关系的关联节点，返回关联节点的指定属性值
    "node_relation_property": u"MATCH (node_a)-[r: %s]->(node_b {name: '%s'}) RETURN node_a.%s as %s",
}


# solr非法字符集转换字典
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

# 模板匹配过滤阈值
TRIPLE_MATCH_THRESHOLD = 1.0

# 词向量路径
DEFAULT_WORDING_EMBEDDING_PATH = os.path.join(HERE, 'data/word_embedding',
                                              'word_embedding_2017-06-25-23:36:57.vec')

# 文档迁移过滤阈值
DEFAULT_WMD_THRESHOLD = 0.5

# 主语同义词词典路径
DEFAULT_SUBJECT_SYNONYM = os.path.join(HERE, 'data/dictionary', 'subject_synonym.txt')

# 模板缺失时的默认优先级
DEFAULT_TEMPLATE_PRIORITY = 4
