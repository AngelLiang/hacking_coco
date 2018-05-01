#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#

import os
import socket
import threading
import paramiko

# SSHServer依赖Client类、Request类、SSHInterface类
from .utils import ssh_key_gen, get_logger
from .interface import SSHInterface
from .interactive import InteractiveServer
from .models import Client, Request
from .sftp import SFTPServer

logger = get_logger(__file__)
BACKLOG = 5


class SSHServer:

    def __init__(self, app):
        self.app = app
        self.stop_evt = threading.Event()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.host_key_path = os.path.join(
            self.app.root_path, 'keys', 'host_rsa_key')

    @property
    def host_key(self):
        if not os.path.isfile(self.host_key_path):
            self.gen_host_key()
        return paramiko.RSAKey(filename=self.host_key_path)

    ##########################################################################

    def gen_host_key(self):
        ssh_key, _ = ssh_key_gen()
        with open(self.host_key_path, 'w') as f:
            f.write(ssh_key)

    def run(self):
        """启动 sshd"""
        host = self.app.config["BIND_HOST"]
        port = self.app.config["SSHD_PORT"]
        print('Starting ssh server at {}:{}'.format(host, port))
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((host, port))    # 绑定端口
        self.sock.listen(BACKLOG)       # 监听

        # 循环运行
        while not self.stop_evt.is_set():
            try:
                sock, addr = self.sock.accept()  # accept
                logger.info(
                    "Get ssh request from {}: {}".format(addr[0], addr[1]))
                # 使用线程处理连接
                thread = threading.Thread(
                    target=self.handle_connection, args=(sock, addr))
                thread.daemon = True
                thread.start()
            except Exception as e:
                logger.error("Start SSH server error: {}".format(e))

    def handle_connection(self, sock, addr):
        """处理连接"""

        # ssh transport 绑定一个 socket
        transport = paramiko.Transport(sock, gss_kex=False)
        try:
            transport.load_server_moduli()
        except IOError:
            logger.warning("Failed load moduli -- gex will be unsupported")

        transport.add_server_key(self.host_key)
        transport.set_subsystem_handler(
            'sftp', paramiko.SFTPServer, SFTPServer
        )

        request = Request(addr)  # 包装一下 addr 为 request
        # 构建 SSHInterface 作为 ssh server ， SSHInterface 在 interface.py 文件里
        server = SSHInterface(self.app, request)

        try:
            transport.start_server(server=server)   # 启动 ssh server
        except paramiko.SSHException:
            logger.warning("SSH negotiation failed")    # ssh 协商失败
            return
        except EOFError:
            logger.warning("Handle EOF Error")
            return

        # 进入循环
        while True:
            # 如果没有活动的连接，则关闭并break
            if not transport.is_active():
                transport.close()
                sock.close()
                break
            # accept
            chan = transport.accept()
            server.event.wait(5)

            if chan is None:
                continue

            if not server.event.is_set():
                logger.warning("Client not request a valid request, exiting")
                return

            # 线程方式处理 chan，chan和request作为参数
            t = threading.Thread(target=self.handle_chan, args=(chan, request))
            t.daemon = True
            t.start()

    def handle_chan(self, chan, request):
        """处理 chan"""
        client = Client(chan, request)  # 构建一个 client
        self.app.add_client(client)  # 添加 client
        self.dispatch(client)       # 调度

    def dispatch(self, client):
        """调度"""
        request_type = client.request.type
        if 'pty' in request_type:   # 一般会进入这里
            logger.info("Request type `pty`, dispatch to interactive mode")
            # 调用 InteractiveServer 的 interact() 方法
            InteractiveServer(self.app, client).interact()
        elif 'subsystem' in request_type:
            pass
        else:
            logger.info("Request type `{}`".format(request_type))
            client.send("Not support request type: %s" % request_type)

    def shutdown(self):
        self.stop_evt.set()
