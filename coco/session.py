# coding=utf-8

import datetime
from .session_ori import Session_ori, logger, selectors, BUF_SIZE


class Session(Session_ori):
    def pre_bridge(self):
        pass

    def post_bridge(self):
        pass
