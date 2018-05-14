# coding=utf-8

from .proxy_ori import ProxyServer_ori


class ProxyServer(ProxyServer_ori):
    def validate_permission(self, asset, system_user):
        """
        验证用户是否有连接改资产的权限
        :return: True or False
        """
        return True
