#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import threading
import uuid
import datetime
import selectors
import time

from .utils import get_logger

BUF_SIZE = 1024
logger = get_logger(__file__)


class Session_ori:
    """
    Session类
    实现 client 和 server 之间的数据转发功能
    使用 selectors 模块实现
    """

    def __init__(self, client, server, command_recorder=None, replay_recorder=None):
        self.id = str(uuid.uuid4())
        self.client = client  # Master of the session, it's a client sock
        self.server = server  # Server channel
        self._watchers = []  # Only watch session ， 监视者
        self._sharers = []  # Join to the session, read and write ， 共享者
        self.replaying = True
        self.date_created = datetime.datetime.utcnow()
        self.date_end = None
        self.stop_evt = threading.Event()
        self.sel = selectors.DefaultSelector()
        self._command_recorder = command_recorder
        self._replay_recorder = replay_recorder
        self.server.set_session(self)
        self.date_last_active = datetime.datetime.utcnow()

    def add_watcher(self, watcher, silent=False):
        """
        Add a watcher, and will be transport server side msg to it.

        添加一个 watcher，并将传输 server 端的消息给它

        :param watcher: A client socket
        :param silent: If true not send welcome message
        :return:
        """
        logger.info("Session add watcher: {} -> {} ".format(self.id, watcher))
        if not silent:
            watcher.send("Welcome to watch session {}\r\n".format(self.id).encode("utf-8"))
        self.sel.register(watcher, selectors.EVENT_READ)
        self._watchers.append(watcher)

    def remove_watcher(self, watcher):
        logger.info("Session %s remove watcher %s" % (self.id, watcher))
        self.sel.unregister(watcher)
        self._watchers.remove(watcher)

    def add_sharer(self, sharer, silent=False):
        """
        Add a sharer, it can read and write to server
        
        添加一个 sharer，可以读写 server

        :param sharer:  A client socket
        :param silent: If true not send welcome message
        :return:
        """
        logger.info("Session %s add share %s" % (self.id, sharer))
        if not silent:
            sharer.send("Welcome to join session: {}\r\n"
                        .format(self.id).encode("utf-8"))
        self.sel.register(sharer, selectors.EVENT_READ)
        self._sharers.append(sharer)

    def remove_sharer(self, sharer):
        """移除 sharer"""
        logger.info("Session %s remove sharer %s" % (self.id, sharer))
        sharer.send("Leave session {} at {}"
                    .format(self.id, datetime.datetime.now())
                    .encode("utf-8"))
        self.sel.unregister(sharer)
        self._sharers.remove(sharer)

    def set_command_recorder(self, recorder):
        self._command_recorder = recorder

    def set_replay_recorder(self, recorder):
        self._replay_recorder = recorder

    def put_command(self, _input, _output):
        """
        存放命令记录
        """
        if not _input:
            return
        self._command_recorder.record({
            "session": self.id,
            "input": _input,
            "output": _output,
            "user": self.client.user.username,
            "asset": self.server.asset.hostname,
            "system_user": self.server.system_user.username,
            "timestamp": time.time(),
        })

    def put_replay(self, data):
        """
        存放命令回复记录
        """
        self._replay_recorder.record({
            "session": self.id,
            "data": data,
            "timestamp": time.time(),
        })

    def pre_bridge(self):
        """桥接准备工作
        即准备命令回复记录
        """
        self._replay_recorder.session_start(self.id)
        self._command_recorder.session_start(self.id)

    def post_bridge(self):
        """桥接收尾工作
        """
        self._replay_recorder.session_end(self.id)
        self._command_recorder.session_end(self.id)

    def terminate(self):
        msg = b"Terminate by administrator\r\n"
        try:
            self.client.send(msg)
        except OSError:
            pass
        self.close()

    def bridge(self):
        """
        Bridge clients with server

        桥接 clients 到 server
        """
        logger.info("Start bridge session: {}".format(self.id))
        self.pre_bridge()   # 做一些命令记录的准备工作

        # client 和 server 都注册到 selectors
        self.sel.register(self.client, selectors.EVENT_READ)
        self.sel.register(self.server, selectors.EVENT_READ)

        # 循环检查是否有停止事件
        while not self.stop_evt.is_set():
            events = self.sel.select()
            for sock in [key.fileobj for key, _ in events]:
                data = sock.recv(BUF_SIZE)
                # self.put_replay(data)
                # server
                if sock == self.server:     
                    if len(data) == 0:  # 如果收到的 data 为0， server 关闭连接
                        msg = "Server close the connection"
                        logger.info(msg)
                        self.close()
                        break

                    self.date_last_active = datetime.datetime.utcnow()
                    # 否则向 client 、watcher 和 sharer 发送数据
                    for watcher in [self.client] + self._watchers + self._sharers:
                        watcher.send(data)
                # client
                elif sock == self.client:
                    if len(data) == 0:  # 如果收到的 data 为0， client 关闭连接
                        msg = "Client close the connection: {}".format(self.client)
                        logger.info(msg)
                        for watcher in self._watchers + self._sharers:
                            watcher.send(msg.encode("utf-8"))
                        self.close()
                        break
                    self.server.send(data)  # 否则向 server 发送数据
                # sharer
                elif sock in self._sharers:
                    if len(data) == 0:
                        logger.info("Sharer {} leave the session {}".format(sock, self.id))
                        self.remove_sharer(sock)
                    self.server.send(data)  # sharer 向 server 发送数据
                # watcher
                elif sock in self._watchers:
                    if len(data) == 0:
                        self._watchers.remove(sock)
                        logger.info("Watcher {} leave the session {}".format(sock, self.id))
        logger.info("Session stop event set: {}".format(self.id))   # stop日志

    def set_size(self, width, height):
        """设置 pty 大小"""
        logger.debug("Resize server chan size {}*{}".format(width, height))
        self.server.resize_pty(width=width, height=height)

    def close(self):
        logger.info("Close the session: {} ".format(self.id))
        self.stop_evt.set()
        self.post_bridge()  # 命令记录的收尾工作
        self.date_end = datetime.datetime.utcnow()  # 设置断开时间
        self.server.close()

    def to_json(self):
        """转换为 json 格式"""
        return {
            "id": self.id,
            "user": self.client.user.username,
            "asset": self.server.asset.hostname,
            "system_user": self.server.system_user.username,
            "login_from": "ST",
            "remote_addr": self.client.addr[0],
            "is_finished": True if self.stop_evt.is_set() else False,
            "date_last_active": self.date_last_active.strftime("%Y-%m-%d %H:%M:%S") + " +0000",
            "date_start": self.date_created.strftime("%Y-%m-%d %H:%M:%S") + " +0000",
            "date_end": self.date_end.strftime("%Y-%m-%d %H:%M:%S") + " +0000" if self.date_end else None
        }

    def __str__(self):
        return self.id

    def __repr__(self):
        return self.id

    # def __del__(self):
    #     print("GC: Session object has been GC")
