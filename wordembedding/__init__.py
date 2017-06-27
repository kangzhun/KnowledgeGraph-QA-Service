# -*- coding: utf-8 -*-
import chardet
import codecs
import os

from tqdm import tqdm

from config import HERE
from utils import seg_doc


def generate_training_data(path):
    file_names = os.listdir(path)

    for name in file_names:
        if os.path.isdir(os.path.join(path, name)):
            print '%s is directory' % name
            continue
        if name.startswith('seg_'):
            if os.path.exists(os.path.join(path, 'seg_corpus/%s' % name)):
                print "%s seg corpus exists, don't need generate seg_%s" % (name, name)
                continue
            with codecs.open(os.path.join(path, name), mode='r', encoding='utf-8') as fr:
                lines = fr.readlines()

            with codecs.open(os.path.join(path, 'seg_corpus/%s' % name), mode='w', encoding='utf-8') as fw:
                print 'start generate seg_corpus/%s' % name
                for line in tqdm(lines):
                    if line.strip():
                        words = line.strip().split()
                        fw.write(' '.join([w.strip() for w in words if w.strip()]))
                        fw.write('\n')
        else:
            if os.path.exists(os.path.join(path, 'seg_corpus/seg_%s' % name)):
                print "%s seg corpus exists, don't need generate seg_%s" % (name, name)
                continue
            with codecs.open(os.path.join(path, name), mode='r', encoding='utf-8') as fr:
                lines = fr.readlines()

            with codecs.open(os.path.join(path, 'seg_corpus/seg_%s' % name), mode='w', encoding='utf-8') as fw:
                print 'start generate seg_corpus/seg_%s' % name
                for line in tqdm(lines):
                    if line.strip():
                        words, tags = seg_doc(line.strip())
                        fw.write(' '.join([w.strip() for w in words if w.strip()]))
                        fw.write('\n')

if __name__ == '__main__':
    generate_training_data(os.path.join(HERE, 'data/embedding_training_corpus'))
