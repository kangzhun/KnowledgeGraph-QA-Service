# -*- coding: utf-8 -*-
import os
from time import strftime, localtime

from pymongo import MongoClient
from tqdm import tqdm

from config import MONGODB_HOST, MONGODB_PORT, MONGODB_DBNAME, MONGODB_TEST_CORPUS, HERE
from service.retrieval_service import RetrievalBot
from service.template_service import TemplateBot

client = MongoClient(MONGODB_HOST, MONGODB_PORT)
db = client.get_database(MONGODB_DBNAME)
test_corpus_collection = db.get_collection(MONGODB_TEST_CORPUS)


if __name__ == '__main__':
    template_bot = TemplateBot()
    retrieval_bot = RetrievalBot()
    test_corpus_docs = test_corpus_collection.find()
    start_time = strftime("%Y-%m-%d-%H:%M:%S", localtime())
    model_name = 'template_bot'
    missing_path = os.path.join(HERE, 'data/test_result/missing_%s_%s.csv' % (model_name, start_time))
    answer_path = os.path.join(HERE, 'data/test_result/answer_%s_%s.csv' % (model_name, start_time))
    fw_missing = open(missing_path, 'w')
    fw_answer = open(answer_path, 'w')
    for doc in tqdm(test_corpus_docs):
        query = doc['query']
        answer = doc['answer']
        try:
            reply_answer = template_bot.reply(query).replace('\n', '\t')
            if reply_answer:
                line = '\t'.join([query, answer, reply_answer, 'TEMPLATE'])
                fw_answer.write(line.encode('utf-8'))
                fw_answer.write('\n')
            else:
                reply_answer = retrieval_bot.reply(query).replace('\n', '\t')
                if reply_answer:
                    line = '\t'.join([query, answer, reply_answer, 'RETRIEVAL'])
                    fw_answer.write(line.encode('utf-8'))
                    fw_answer.write('\n')
                else:
                    line = '\t'.join([query, answer])
                    fw_missing.write(line.encode('utf-8'))
                    fw_missing.write('\n')
        except Exception, e:
            print 'got error:', query

    fw_answer.close()
    fw_missing.close()
