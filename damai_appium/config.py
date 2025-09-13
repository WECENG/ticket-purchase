# -*- coding: UTF-8 -*-
"""
__Author__ = "WECENG"
__Version__ = "1.0.0"
__Description__ = "配置类"
__Created__ = 2023/10/27 09:54
"""
import json
import re


class Config:
    def __init__(self, server_url, keyword, users, city, date, price, price_index, if_commit_order):
        self.server_url = server_url
        self.keyword = keyword
        self.users = users
        self.city = city
        self.date = date
        self.price = price
        self.price_index = price_index
        self.if_commit_order = if_commit_order

    @staticmethod
    def load_config():
        with open('config.jsonc', 'r', encoding='utf-8') as config_file:
            content = config_file.read()
            # 去掉 // 的注释
            content = re.sub(r'//.*', '', content)
            # content = re.sub(r'/\*[\s\S]*?\*/', '', content)
            print(content)
            config = json.loads(content)
            # config = json.load(config_file)
        return Config(config['server_url'],
                      config['keyword'],
                      config['users'],
                      config['city'],
                      config['date'],
                      config['price'],
                      config['price_index'],
                      config['if_commit_order'])
