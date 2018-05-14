# coding=utf-8

from .interface_ori import SSHInterface_ori


class SSHInterface(SSHInterface_ori):
    def validate_auth(self, username, password="", public_key=""):
        """
        用户验证
        @return: True or False

        如果成功，则给 self.request.user 赋值一个 models.User 的对象并返回 True
        """
        from .models import User
        user = User()
        user.username = username
        user.name = username
        user.password = password
        self.request.user = user
        return True
