# -*- coding: UTF-8 -*-
"""
__Author__ = "WECENG"
__Version__ = "1.0.0"
__Description__ = ""
__Created__ = 2023/10/10 17:00
"""

import os.path
import pickle
import time
from time import sleep

from selenium import webdriver
from selenium.webdriver.common.by import By


class Concert:
    def __init__(self, config):
        self.config = config
        self.status = 0  # 状态,表示如今进行到何种程度
        self.login_method = 1  # {0:模拟登录,1:Cookie登录}自行选择登录方式
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_experimental_option("excludeSwitches", ['enable-automation'])
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        self.driver = webdriver.Chrome(options=chrome_options)  # 默认Chrome浏览器

    def set_cookie(self):
        """
        :return: 写入cookie
        """
        self.driver.get(self.config.index_url)
        print("***请点击登录***\n")
        while self.driver.title.find('大麦网-全球演出赛事官方购票平台') != -1:
            sleep(1)
        print("***请扫码登录***\n")
        while self.driver.title != '大麦网-全球演出赛事官方购票平台-100%正品、先付先抢、在线选座！':
            sleep(1)
        print("***扫码成功***\n")

        # 将cookie写入damai_cookies.pkl文件中
        pickle.dump(self.driver.get_cookies(), open("damai_cookies.pkl", "wb"))
        print("***Cookie保存成功***")
        # 读取抢票目标页面
        self.driver.get(self.config.target_url)

    def get_cookie(self):
        """
        :return: 读取cookie
        """
        try:
            cookies = pickle.load(open("damai_cookies.pkl", "rb"))
            for cookie in cookies:
                cookie_dict = {
                    'domain': '.damai.cn',  # 域为大麦网的才为有效cookie
                    'name': cookie.get('name'),
                    'value': cookie.get('value'),
                }
                self.driver.add_cookie(cookie_dict)
            print('***完成cookie加载***\n')
        except Exception as e:
            print(e)

    def login(self):
        """
        :return: 登录
        """
        if self.login_method == 0:
            self.driver.get(self.config.login_url)
            print('***开始登录***\n')
        elif self.login_method == 1:
            if not os.path.exists('damai_cookies.pkl'):
                # 没有cookie就获取
                self.set_cookie()
            else:
                self.driver.get(self.config.target_url)
                self.get_cookie()

    def enter_concert(self):
        """
        :return: 打开浏览器
        """
        print('***打开浏览器，进入大麦网***\n')
        # 先登录
        self.login()
        # 刷新页面
        self.driver.refresh()
        # 标记登录成功
        self.status = 2
        print('***登录成功***')
        if self.is_element_exist('/html/body/div[2]/div[2]/div/div/div[3]/div[2]'):
            self.driver.find_element(value='/html/body/div[2]/div[2]/div/div/div[3]/div[2]', by=By.XPATH).click()

    def is_element_exist(self, element):
        """
        :param element: 判断元素是否存在
        :return:
        """
        flag = True
        browser = self.driver
        try:
            browser.find_element(value=element, by=By.XPATH)
            return flag
        except Exception:
            flag = False
            return flag

    def choose_ticket(self):
        """
        :return: 选票
        """
        # 如果登录成功了
        if self.status == 2:
            print("*******************************\n")
            print("***选定城市***\n")
            if self.driver.find_elements(value='citys', by=By.CLASS_NAME) and self.config.city is not None:
                # 如果可以选择场次
                city_name_element_list = self.driver.find_element(value='citylist', by=By.CLASS_NAME).find_elements(
                    value='cityitem', by=By.CLASS_NAME)
                for city_name_element in city_name_element_list:
                    if self.config.city in city_name_element.text:
                        city_name_element.click()
                        break
            print("***选定场次***\n")
            if self.driver.find_elements(value='perform__order__select__performs',
                                         by=By.CLASS_NAME) and self.config.date is not None:
                # 如果可以选择场次
                order_name_element_list = self.driver.find_element(value='perform__order__select__performs',
                                                                   by=By.CLASS_NAME).find_elements(
                    value='select_right_list_item', by=By.CLASS_NAME)
                for order_name_element in order_name_element_list:
                    if self.config.date in order_name_element.text:
                        order_name_element.click()
                        break
            print("***选定票档***\n")
            if self.driver.find_elements(value='perform__order__select',
                                         by=By.CLASS_NAME) and self.config.price is not None:
                # 如果可以选择票档
                sku_name_element_list = self.driver.find_elements(value='skuname',
                                                                  by=By.CLASS_NAME)
                for sku_name_element in sku_name_element_list:
                    if self.config.price in sku_name_element.text:
                        sku_name_element.click()
                        break
            print("***选定人数***\n")
            if self.driver.find_elements(value='number_right_info', by=By.CLASS_NAME):
                # 如果可以选人数
                for i in range(len(self.config.users) - 1):
                    self.driver.find_element(value='cafe-c-input-number-handler-up',
                                             by=By.CLASS_NAME).click()
            while self.driver.title.find('订单确认页') == -1:
                try:
                    buy_button = self.driver.find_element(value='buybtn',
                                                          by=By.CLASS_NAME).text if self.driver.find_elements(
                        value='buybtn', by=By.CLASS_NAME) else None
                    by_link = self.driver.find_element(value='buy-link',
                                                       by=By.CLASS_NAME).text if self.driver.find_elements(
                        value='buy-link', by=By.CLASS_NAME) else None
                    if buy_button == "提交缺货登记":
                        # 改变现有状态
                        self.status = 2
                        self.driver.get(self.config.target_url)
                        print('***抢票未开始，刷新等待开始***\n')
                        continue
                    elif buy_button == "立即预订":
                        self.driver.find_element(value='buybtn', by=By.CLASS_NAME).click()
                        # 改变现有状态
                        self.status = 3
                    elif buy_button == "立即购买":
                        self.driver.find_element(value='buybtn', by=By.CLASS_NAME).click()
                        # 改变现有状态
                        self.status = 4
                    elif by_link == "不，立即预订" or by_link == "不，立即购买":
                        self.driver.find_element(value='buy-link', by=By.CLASS_NAME).click()
                        # 改变现有状态
                        self.status = 4
                    # 选座购买暂时无法完成自动化
                    elif buy_button == "选座购买":
                        self.driver.find_element(value='buybtn', by=By.CLASS_NAME).click()
                        self.status = 5
                except Exception:
                    print('***未跳转到订单结算界面***\n')
                title = self.driver.title
                if title == '选座购买':
                    # 实现选座购买逻辑
                    self.choice_seat()
                elif title == '订单确认页':
                    while True:
                        # 如果标题为确认订单
                        print('等待...\n')
                        if self.is_element_exist('//*[@id="confirmOrder_1"]'):
                            # 实现确认订单逻辑
                            self.check_order()
                            break

    def choice_seat(self):
        while self.driver.title == '选座购买':
            while self.is_element_exist('//*[@id="app"]/div[2]/div[2]/div[1]/div[2]/img'):
                # 座位手动选择 选中座位之后//*[@id="app"]/div[2]/div[2]/div[1]/div[2]/img 就会消失
                print('请快速选择您的座位！！！')
            # 消失之后就会出现 //*[@id="app"]/div[2]/div[2]/div[2]/div
            while self.is_element_exist('//*[@id="app"]/div[2]/div[2]/div[2]/div'):
                # 找到之后进行点击确认选座
                self.driver.find_element(value='//*[@id="app"]/div[2]/div[2]/div[2]/button', by=By.XPATH).click()

    def check_order(self):
        if self.status in [3, 4, 5]:
            print('***开始确认订单***\n')
            try:
                # 选购票人信息
                for user in self.config.users:
                    xpath_expression = f"//div[text()='{user}']"
                    # 根据购票人定位到勾选按钮
                    user_checked_element = self.driver.find_element(value=xpath_expression, by=By.XPATH).find_element(
                        value='..',
                        by=By.XPATH).find_element(
                        value='..', by=By.XPATH).find_element(value="following-sibling::*[1]",
                                                              by=By.XPATH).find_element(value=".//i",
                                                                                        by=By.XPATH)
                    # 模拟js调用click，防止元素覆盖
                    self.driver.execute_script("arguments[0].click();", user_checked_element)
            except Exception as e:
                print("***购票人信息选中失败，清自行查看元素位置***\n")
                print(e)
            # 最后一步提交订单
            time.sleep(0.2)
            if self.config.if_commit_order:
                self.driver.find_element(
                    value='//*[@id="dmOrderSubmitBlock_DmOrderSubmitBlock"]/div[2]/div/div[2]/div[3]/div[2]/span',
                    by=By.XPATH).click()

    def finish(self):
        self.driver.quit()
