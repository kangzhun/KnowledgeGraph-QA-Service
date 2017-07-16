# -*- coding: utf-8 -*-
import codecs

from const import DEFAULT_SUBJECT_SYNONYM
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
    normal_query = unicode2str(query).strip()  # 转换为unicode编码，并去掉句子开头和结尾的空格和回车
    return normal_query


def load_entity_synonym(path):
    synonyms = dict()
    with codecs.open(path, mode='r', encoding='utf-8') as fr:
        lines = fr.readlines()
        for line in lines:
            line_list = line.strip().split(',')
            if len(line_list) == 2:
                key = line_list[0]
                value = line_list[1]
                if key in synonyms.keys():
                    synonyms[key].append(value)
                else:
                    synonyms[key] = [value, ]
    return synonyms


if __name__ == '__main__':
    print load_entity_synonym(DEFAULT_SUBJECT_SYNONYM)
