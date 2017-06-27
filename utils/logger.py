# -*- coding:utf-8 -*-
import os
import logging

from config import LOGGER_PATH, LOGGER_NAME


class BaseLogger(object):
    def __init__(self, **kwargs):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

        fh = logging.FileHandler(os.path.join(LOGGER_PATH, LOGGER_NAME))
        fh.setLevel(logging.DEBUG)

        fm = logging.Formatter('%(asctime)s -  %(levelname)s - %(message)s')
        fh.setFormatter(fm)

        if not self.logger.handlers:
            self.logger.addHandler(fh)

        self.logger.propagate = False

    def log_base(self, level, msg, *args, **kwargs):
        log_handler_map = {
            "debug": self.logger.debug,
            "info": self.logger.info,
            "warn": self.logger.warn,
            "error": self.logger.error,
            "exception": self.exception
        }
        msg_str = msg.decode('utf-8')
        if args:
            msg_str = msg % args
        msg_list = msg_str.split(os.linesep)
        for line in msg_list:
            log_handler_map[level](line, **kwargs)

    def debug(self, msg, *args, **kwargs):
        self.log_base("debug", msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self.log_base("info", msg, *args, **kwargs)

    def warn(self, msg, *args, **kwargs):
        self.log_base("warn", msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self.log_base("error", msg, *args, **kwargs)

    def exception(self, msg, *args, **kwargs):
        self.logger.exception(msg, *args, **kwargs)
