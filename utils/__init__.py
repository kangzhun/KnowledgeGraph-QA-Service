# -*- coding: utf-8 -*-
from utils.nlu_api import JiebaClient

seg_client = JiebaClient()


def seg_doc(doc):
    words, tags = seg_client.seg(doc)
    return words, tags


def seg_doc_with_search(doc):
    words = seg_client.seg_for_search(doc)
    return words


def unicode2str(unicode_str):
    if isinstance(unicode_str, unicode):
        return unicode_str.encode('utf-8')
    else:
        return unicode_str


def str2unicode(utf_str):
    if isinstance(utf_str, str):
        return utf_str.decode('utf-8')
    else:
        return utf_str


def normalize_query(query):
    normal_query = unicode2str(query).strip()
    return normal_query
