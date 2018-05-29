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
    def on_host(self, message):
        print("on_host")
        # 此处获取主机的信息
        logger.debug("On host event trigger")
        connection = str(uuid.uuid4())
        asset_id = message.get('uuid', None)
        user_id = message.get('userid', None)
        secret = message.get('secret', None)

        self.emit('room', {'room': connection, 'secret': secret})

        # if not asset_id or not user_id:
        #     self.on_connect()
        #     return

        # 获取asset和system_user
        # asset = self.app.service.get_asset(asset_id)
        # system_user = self.app.service.get_system_user(user_id)
        # TODO:
        # asset =
        # system_user =

        # if not asset or not system_user:
        #     self.on_connect()
        #     return

        child, parent = socket.socketpair()
        # Client
        self.clients[request.sid]["client"][connection] = Client(
            parent, self.clients[request.sid]["request"])
        # WSProxy
        self.clients[request.sid]["proxy"][connection] = WSProxy(
            self, child, self.clients[request.sid]["room"], connection)
        # ProxyServer
        self.clients[request.sid]["forwarder"][connection] = ProxyServer(
            self.app, self.clients[request.sid]["client"][connection])
        # 后台执行任务，ProxyServer.proxy
        self.socketio.start_background_task(
            self.clients[request.sid]["forwarder"][connection].proxy, asset,
            system_user)

    def on_token(self, message):
        print("on_token")
        # 此处获取token含有的主机的信息
        # logger.debug("On token trigger")
        # logger.debug(message)
        token = message.get('token', None)
        secret = message.get('secret', None)

        connection = str(uuid.uuid4())

        self.emit('room', {'room': connection, 'secret': secret})

        # if not (token or secret):
        #     logger.debug("token or secret is None")
        #     self.emit('data', {
        #         'data': "\nOperation not permitted!",
        #         'room': connection
        #     })
        #     self.emit('disconnect')
        #     return None

        # 从token中获取asset
        # host = self.app.service.get_token_asset(token)
        # TODO:
        # host = {"asset":asset,"system_user":system_user}

        logger.debug(host)
        if not host:
            logger.debug("host is None")
            self.emit('data', {
                'data': "\nOperation not permitted!",
                'room': connection
            })
            self.emit('disconnect')
            return None

        user_id = host.get('user', None)
        logger.debug("self.current_user")

        # 获取用户profile
        # self.current_user = self.app.service.get_user_profile(user_id)
        # self.current_user = self.get_current_user()

        logger.debug(self.current_user)
        # {
        #     "user": {UUID},
        #     "asset": {UUID},
        #     "system_user": {UUID}
        # }

        self.on_host({
            'secret': secret,
            'uuid': host['asset'],
            'userid': host['system_user']
        })


class HttpServer(HttpServer_ori):
    def register_routes(self):
        self.socket_io.on_namespace(ProxyNamespace('/ssh'))
