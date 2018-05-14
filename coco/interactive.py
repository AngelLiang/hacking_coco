# coding=utf-8

from .interactive_ori import InteractiveServer_ori


class InteractiveServer(InteractiveServer_ori):
    def display_banner(self):
        super().display_banner()

    def display_search_result(self):
        super().display_search_result()
