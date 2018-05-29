# coding=utf-8
"""
改写 httpd ，引出可能需要修改的接口
"""

import os
import socket
import uuid
from flask_socketio import SocketIO, Namespace, join_room, leave_room
from flask import Flask, request, current_app, redirect

from .models import Request, Client, WSProxy

from .httpd_ori import ProxyNamespace_ori, HttpServer_ori, logger, ProxyServer


class ProxyNamespace(ProxyNamespace_ori):
    def on_data(self, message):
        """
        收到数据
        :param message: {"data": "xxx", "room": "xxx"}
        :return:
        """
        room = message.get('room')
        if not room:
            return

        # 如果创建了代理房间则转发
        # room_proxy 类型为 ProxyServer
        room_proxy = self.clients[request.sid]['proxy'].get(room)
        if room_proxy:
            room_proxy.send({"data": message['data']})

    def on_host(self, message):
        """
        核心
        获取主机的信息，并进行代理

        :param message: {"uuid":"","userid":"","secret":""}
        """
        logger.debug("On host event trigger")
        connection = str(uuid.uuid4())  # 生成一个 uuid 作为连接房间
        asset_id = message.get('uuid', None)
        user_id = message.get('userid', None)
        secret = message.get('secret', None)

        self.emit('room', {'room': connection, 'secret': secret})

        # TODO: 这里设置需要 proxy 的设备资产和帐户
        # asset =
        # system_user =

        # 以下是核心代码
        child, parent = socket.socketpair()

        # 设置参数
        # Client
        self.clients[request.sid]["client"][connection] = Client(
            parent, self.clients[request.sid]["request"])
        # WSProxy
        self.clients[request.sid]["proxy"][connection] = WSProxy(
            self, child, self.clients[request.sid]["room"], connection)
        # ProxyServer
        self.clients[request.sid]["forwarder"][connection] = ProxyServer(
            self.app, self.clients[request.sid]["client"][connection])

        # 开始启动
        # 后台执行任务，ProxyServer.proxy，传递asset和system_user
        self.socketio.start_background_task(
            self.clients[request.sid]["forwarder"][connection].proxy, asset,
            system_user)

    def on_token(self, message):
        """
        一个协助处理函数
        处理token
        """
        # 此处获取token含有的主机的信息
        # logger.debug("On token trigger")
        # logger.debug(message)
        token = message.get('token', None)
        secret = message.get('secret', None)

        # 以下两句似乎没有什么用
        # connection = str(uuid.uuid4())
        # self.emit('room', {'room': connection, 'secret': secret})

        # 可模拟emit发送消息，这里参数为空
        self.on_host({})


class HttpServer(HttpServer_ori):
    # 使用其他模式可能会导致卡住
    async_mode = "threading"

    def register_routes(self):
        """注册路由"""
        self.socket_io.on_namespace(ProxyNamespace('/ssh'))
