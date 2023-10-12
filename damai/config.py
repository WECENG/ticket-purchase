# -*- coding: UTF-8 -*-
"""
__Author__ = "WECENG"
__Version__ = "1.0.0"
__Description__ = "配置类"
__Created__ = 2023/10/11 18:01
"""


class Config:

    def __init__(self, index_url, login_url, target_url, users, city, date, price, if_commit_order):
        self.index_url = index_url
        self.login_url = login_url
        self.target_url = target_url
        self.users = users
        self.city = city
        self.date = date
        self.price = price
        self.if_commit_order = if_commit_order
