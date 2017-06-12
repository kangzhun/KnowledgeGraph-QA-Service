# -*- coding: utf-8 -*-
# 自然语言处理工具包
import jieba
import jieba.posseg as pseg

from config import CUSTOM_DICTIONARY_PATH
from utils.logger import BaseLogger


class JiebaClient(BaseLogger):
    def __init__(self, custom_dict_path=CUSTOM_DICTIONARY_PATH):
        super(JiebaClient, self).__init__()
        try:
            jieba.load_userdict(custom_dict_path)
            self.debug("init JiebaClient, with custom_dict_path=%s", custom_dict_path)
        except Exception, e:
            self.exception(e)
            self.error('@@@@@@@@@@@@@@@@@@@@@@@@@@@ loading custom_dictionary failed')

    def seg(self, sentence):
        words = list()
        tags = list()
        self.debug("sentence=%s", sentence)
        for item in pseg.cut(sentence):
            words.append(item.word)
            tags.append(item.flag)
        self.debug("words=%s, tags=%s", " ".join(words), " ".join(tags))
        return words, tags

    def seg_for_search(self, sentence):
        words = list()
        self.debug("sentence=%s", sentence)
        for item in jieba.cut_for_search(sentence):
            words.append(item)
        self.debug("words=%s", " ".join(words))
        return words


if __name__ == '__main__':
    jieba_client = JiebaClient()
    while 1:
        query = raw_input('请输入句子:\n')
        _words = jieba_client.seg_for_search(query)
        print " ".join(_words)
