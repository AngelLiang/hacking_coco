# coding=utf-8
#

from .connection_ori import SSHConnection_ori


class SSHConnection(SSHConnection_ori):
    """
    继承 SSHConnection ，重新实现 SSHConnection 认证相关的接口
    """

    def get_system_user_auth(self, system_user):
        """
        获取系统用户的认证信息，密码或秘钥，依赖于self.app
        :return: system user have full info

        可能需要自定义
        主要给 system_user.password 和 system_user.private_key 赋值
        """
        # system_user.password, system_user.private_key = \
        #     self.app.service.get_system_user_auth_info(system_user)
