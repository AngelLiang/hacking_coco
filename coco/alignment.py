#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#

import queue


class MultiQueueMixin:
    """
    混合类，增加批量get和批量put方法
    """
    def mget(self, size=1, block=True, timeout=5):
        """
        批量get
        """
        items = []
        for i in range(size):
            try:
                items.append(self.get(block=block, timeout=timeout))
            except queue.Empty:
                break
        return items

    def mput(self, data_set):
        """
        批量put
        """
        for i in data_set:
            self.put(i)


class MemoryQueue(MultiQueueMixin, queue.Queue):
    """
    队列，用于保存命令记录
    """
    pass


def get_queue(config):
    """获取队列"""
    queue_engine = config['QUEUE_ENGINE']
    queue_size = config['QUEUE_MAX_SIZE']

    if queue_engine == "server":
        replay_queue = MemoryQueue(queue_size)
        command_queue = MemoryQueue(queue_size)
    else:
        replay_queue = MemoryQueue(queue_size)
        command_queue = MemoryQueue(queue_size)

    return replay_queue, command_queue

