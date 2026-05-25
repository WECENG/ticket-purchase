# -*- coding: UTF-8 -*-
"""
__Author__ = "BlueCestbon"
__Version__ = "2.0.0"
__Description__ = "大麦app抢票自动化 - 优化版"
__Created__ = 2025/09/13 19:27
"""

import time, re, os, logging
from appium import webdriver
from appium.options.common.base import AppiumOptions
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from config import Config

logging.basicConfig(level=logging.INFO, format="%(message)s")


class DamaiBot:
    def __init__(self):
        self.config = Config.load_config()
        self.driver = None
        self.wait = None
        self._setup_driver()

    def _setup_driver(self):
        """初始化驱动配置"""
        capabilities = {
            "platformName": "Android",  # 操作系统
            "platformVersion": self.config.platform_version or "12",  # 系统版本
            "deviceName": self.config.device_name or "57e97d81",  # 设备名称
            "appPackage": "cn.damai",  # app 包名
            "appActivity": ".launcher.splash.SplashActivity",  # app 启动 Activity
            "unicodeKeyboard": True,  # 支持 Unicode 输入
            "resetKeyboard": True,  # 隐藏键盘
            "noReset": True,  # 不重置 app
            "newCommandTimeout": 6000,  # 超时时间
            "automationName": "UiAutomator2",  # 使用 uiautomator2
            "skipServerInstallation": False,  # 跳过服务器安装
            "ignoreHiddenApiPolicyError": True,  # 忽略隐藏 API 策略错误
            "disableWindowAnimation": True,  # 禁用窗口动画
            # 优化性能配置
            "mjpegServerFramerate": 1,  # 降低截图帧率
            "shouldTerminateApp": False,
            "adbExecTimeout": 20000,
        }

        device_app_info = AppiumOptions()
        device_app_info.load_capabilities(capabilities)
        self.driver = webdriver.Remote(self.config.server_url, options=device_app_info)

        # 更激进的性能优化设置
        self.driver.update_settings({
            "waitForIdleTimeout": 0,  # 空闲时间，0 表示不等待，让 UIAutomator2 不等页面“空闲”再返回
            "actionAcknowledgmentTimeout": 0,  # 禁止等待动作确认
            "keyInjectionDelay": 0,  # 禁止输入延迟
            "waitForSelectorTimeout": 300,  # 从500减少到300ms
            "ignoreUnimportantViews": False,  # 保持false避免元素丢失
            "allowInvisibleElements": True,
            "enableNotificationListener": False,  # 禁用通知监听
        })

        # 极短的显式等待，抢票场景下速度优先
        self.wait = WebDriverWait(self.driver, 2)  # 从5秒减少到2秒

    def ultra_fast_click(self, by, value, timeout=1.5):
        """超快速点击 - 适合抢票场景"""
        try:
            # 直接查找并点击，不等待可点击状态
            el = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            # 使用坐标点击更快
            rect = el.rect
            x = rect['x'] + rect['width'] // 2
            y = rect['y'] + rect['height'] // 2
            self.driver.execute_script("mobile: clickGesture", {
                "x": x,
                "y": y,
                "duration": 50  # 极短点击时间
            })
            return True
        except TimeoutException:
            return False

    def batch_click(self, elements_info, delay=0.1):
        """批量点击操作"""
        for by, value in elements_info:
            if self.ultra_fast_click(by, value):
                if delay > 0:
                    time.sleep(delay)
            else:
                logging.warning(f"点击失败: {value}")

    def ultra_batch_click(self, elements_info, timeout=2):
        """超快批量点击 - 带等待机制"""
        coordinates = []
        # 批量收集坐标，带超时等待
        for by, value in elements_info:
            try:
                # 等待元素出现
                el = WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((by, value))
                )
                rect = el.rect
                x = rect['x'] + rect['width'] // 2
                y = rect['y'] + rect['height'] // 2
                coordinates.append((x, y, value))
            except TimeoutException:
                logging.warning(f"超时未找到用户: {value}")
            except Exception as e:
                logging.warning(f"查找用户失败 {value}: {e}")
        logging.info(f"成功找到 {len(coordinates)} 个用户")
        # 快速连续点击
        for i, (x, y, value) in enumerate(coordinates):
            self.driver.execute_script("mobile: clickGesture", {
                "x": x,
                "y": y,
                "duration": 30
            })
            if i < len(coordinates) - 1:
                time.sleep(0.01)
            logging.info(f"点击用户: {value}")
        return len(coordinates) > 0


    def smart_wait_and_click(self, by, value, backup_selectors=None, timeout=1.5):
        """智能等待和点击 - 支持备用选择器"""
        selectors = [(by, value)]
        if backup_selectors:
            selectors.extend(backup_selectors)

        for selector_by, selector_value in selectors:
            try:
                el = WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((selector_by, selector_value))
                )
                rect = el.rect
                x = rect['x'] + rect['width'] // 2
                y = rect['y'] + rect['height'] // 2
                self.driver.execute_script("mobile: clickGesture", {"x": x, "y": y, "duration": 50})
                return True
            except TimeoutException:
                continue
        return False

    def two_stage_click(self, text_value, timeout=3):
        """两级匹配点击：先精确 text()，失败后用 textContains()，仍失败 dump 页面文本"""
        # Stage 1: 精确匹配
        logging.info("  尝试精确匹配: " + repr(text_value))
        try:
            el = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located(
                    (AppiumBy.ANDROID_UIAUTOMATOR, f'new UiSelector().text("{text_value}")')
                )
            )
            rect = el.rect
            self.driver.execute_script("mobile: clickGesture", {
                "x": rect["x"] + rect["width"] // 2,
                "y": rect["y"] + rect["height"] // 2,
                "duration": 50,
            })
            logging.info("  >>> 精确匹配成功: " + repr(text_value))
            return True
        except TimeoutException:
            pass

        # Stage 2: 模糊匹配
        logging.info("  尝试模糊匹配: 包含 " + repr(text_value))
        try:
            el = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located(
                    (AppiumBy.ANDROID_UIAUTOMATOR, f'new UiSelector().textContains("{text_value}")')
                )
            )
            actual_text = el.text or el.get_attribute("text") or "(hidden)"
            rect = el.rect
            self.driver.execute_script("mobile: clickGesture", {
                "x": rect["x"] + rect["width"] // 2,
                "y": rect["y"] + rect["height"] // 2,
                "duration": 50,
            })
            logging.info("  >>> 模糊匹配成功: " + repr(actual_text))
            return True
        except TimeoutException:
            pass

        # Stage 3: Dump visible text for debugging
        logging.warning("  >>> 两级匹配均失败，dump 页面文本用于排查...")
        try:
            xml = self.driver.page_source
            import re as _re_dump
            texts = _re_dump.findall(r'text="([^"]*)"', xml)
            visible = [t for t in texts if t.strip() and len(t.strip()) > 1]
            logging.warning("  页面上可见文本 ({} 条):".format(len(visible)))
            for t in visible[:30]:
                logging.warning("    - " + repr(t))
            if len(visible) > 30:
                logging.warning("    ... 还有 {} 条".format(len(visible) - 30))
        except Exception:
            pass
        return False


    def navigate_to_concert(self):
        """搜索并进入目标演出详情页"""
        keyword = self.config.keyword
        logging.info(f"搜索演出: {keyword}")

        # Step 1: 检查是否已经在搜索结果页或演出列表页
        # 尝试直接点击包含关键词的元素
        try:
            el = WebDriverWait(self.driver, 3).until(
                EC.presence_of_element_located(
                    (AppiumBy.ANDROID_UIAUTOMATOR, f'new UiSelector().textContains("{keyword}")')
                )
            )
            rect = el.rect
            self.driver.execute_script("mobile: clickGesture", {
                "x": rect["x"] + rect["width"] // 2,
                "y": rect["y"] + rect["height"] // 2,
                "duration": 50,
            })
            logging.info(f"  直接点击成功: {el.text or keyword}")
            time.sleep(2)
            return True
        except TimeoutException:
            pass

        # Step 2: 尝试点击搜索框并输入关键词
        try:
            # 尝试多种搜索框选择器
            search_selectors = [
                (By.ID, "cn.damai:id/search_bg_click"),
                (By.ID, "cn.damai:id/search_box"),
                (By.ID, "cn.damai:id/header_search_view"),
                (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().descriptionContains("搜索")'),
                (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textContains("搜索")'),
                (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().className("android.widget.EditText")'),
            ]
            clicked_search = False
            for by, val in search_selectors:
                try:
                    el = WebDriverWait(self.driver, 2).until(
                        EC.element_to_be_clickable((by, val))
                    )
                    el.click()
                    clicked_search = True
                    break
                except:
                    continue

            if clicked_search:
                time.sleep(0.5)
                # 输入关键词
                try:
                    search_input = WebDriverWait(self.driver, 2).until(
                        EC.presence_of_element_located(
                            (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().className("android.widget.EditText").focused(true)')
                        )
                    )
                except:
                    search_input = WebDriverWait(self.driver, 2).until(
                        EC.presence_of_element_located(
                            (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().className("android.widget.EditText")')
                        )
                    )
                search_input.clear()
                search_input.send_keys(keyword)
                time.sleep(1)

                # 按搜索键
                self.driver.press_keycode(66)  # ENTER key
                time.sleep(2)

                # 点击第一个结果
                try:
                    el = WebDriverWait(self.driver, 3).until(
                        EC.presence_of_element_located(
                            (AppiumBy.ANDROID_UIAUTOMATOR, f'new UiSelector().textContains("{keyword}")')
                        )
                    )
                    rect = el.rect
                    self.driver.execute_script("mobile: clickGesture", {
                        "x": rect["x"] + rect["width"] // 2,
                        "y": rect["y"] + rect["height"] // 2,
                        "duration": 50,
                    })
                    logging.info(f"  搜索后点击成功: {el.text or keyword}")
                    time.sleep(2)
                    return True
                except TimeoutException:
                    logging.warning("  搜索结果中未找到匹配项")
        except Exception as e:
            logging.warning(f"  搜索导航失败: {e}")

        # 失败时 dump
        logging.warning("  >>> 导航失败，dump 页面文本...")
        try:
            xml = self.driver.page_source
            import re as _re_nav
            texts = _re_nav.findall(r'text="([^"]*)"', xml)
            visible = [t for t in texts if t.strip() and len(t.strip()) > 1]
            logging.warning("  页面上可见文本 ({} 条):".format(len(visible)))
            for t in visible[:20]:
                logging.warning("    - " + repr(t))
        except Exception:
            pass
        return False

    def extract_sale_time(self):
        try:
            time.sleep(1)
            xml = self.driver.page_source
            import re as _re2
            texts = _re2.findall(r"text=\"([^\"]+)\"", xml)
            all_t = " ".join(texts)
            p1 = re.compile(r"\\d{1,2}\\u6708\\d{1,2}\\u65e5\\s*\\d{1,2}:\\d{2}")
            p2 = re.compile(r"\\d{1,2}:\\d{2}")
            for pat in [p1, p2]:
                m2 = pat.search(all_t)
                if m2:
                    g = m2.groups()
                    st = g[-2].zfill(2) + ":" + g[-1].zfill(2) + ":00", 
                    print(f"  >>> Auto-detected sale time: {st} <<<")
                    cp = os.path.join(os.path.dirname(__file__), "config.jsonc")
                    with open(cp, "r", encoding="utf-8") as f2:
                        ct = f2.read()
                    old_at = re.search(r"\"auto_buy_time\":\\s*\"[^\"]*\"", ct)
                    if old_at:
                        ct = ct[:old_at.start()] + "\"auto_buy_time\": \"" + st + "\"" + ct[old_at.end():]
                    with open(cp, "w", encoding="utf-8") as f2:
                        f2.write(ct)
                    self.config.auto_buy_time = st
                    return st
            return None
        except Exception as e:
            print(f"  extract_sale_time err: {e}")
            return None
    def run_ticket_grabbing(self):
        """执行抢票主流程"""
        try:
            logging.info("开始抢票流程...")
            start_time = time.time()

            # 0.5 Auto-extract sale time
            self.extract_sale_time()

            # 0.6 搜索并进入演出详情页
            if not self.navigate_to_concert():
                logging.warning("导航到演出详情页失败")
                return False

            # 1. 城市选择 - 两级匹配（先精确后模糊，失败时 dump 页面文本）
            logging.info("选择城市...")
            if not self.two_stage_click(self.config.city, timeout=3):
                logging.warning("城市选择失败")
                return False

            # 2. 点击预约按钮 - 多种可能的按钮文本
            logging.info("点击预约按钮...")
            book_selectors = [
                (By.ID, "cn.damai:id/trade_project_detail_purchase_status_bar_container_fl"),
                (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textMatches(".*预约.*|.*购买.*|.*立即.*")'),
                (By.XPATH, '//*[contains(@text,"预约") or contains(@text,"购买")]')
            ]
            if not self.smart_wait_and_click(*book_selectors[0], book_selectors[1:]):
                logging.warning("预约按钮点击失败")
                return False

            # 3. 票价选择 - 优化查找逻辑
            logging.info("选择票价...")
            try:
                # 直接尝试点击，不等待容器，实际每次都失败，只能等待
                price_container = self.driver.find_element(By.ID, 'cn.damai:id/project_detail_perform_price_flowlayout')
                # price_container = self.wait.until(  # 等待找到容器
                #     EC.presence_of_element_located((By.ID, 'cn.damai:id/project_detail_perform_price_flowlayout')))
                # 在容器内找 index=1 且 clickable="true" 的 FrameLayout【因为799元的票价是排在第二的，但是page里text是空的被隐藏了】
                target_price = price_container.find_element(
                    AppiumBy.ANDROID_UIAUTOMATOR,
                    f'new UiSelector().className("android.widget.FrameLayout").index({self.config.price_index}).clickable(true)'
                )
                self.driver.execute_script('mobile: clickGesture', {'elementId': target_price.id})
            except Exception as e:
                print(f"票价选择失败，启动备用方案: {e}")
                # 备用方案
                # 先找到大容器
                price_container = self.wait.until(
                    EC.presence_of_element_located((By.ID, 'cn.damai:id/project_detail_perform_price_flowlayout')))
                # 在容器内找 index=1 且 clickable="true" 的 FrameLayout【因为799元的票价是排在第二的，但是page里text是空的被隐藏了】
                target_price = price_container.find_element(
                    AppiumBy.ANDROID_UIAUTOMATOR,
                    f'new UiSelector().className("android.widget.FrameLayout").index({self.config.price_index}).clickable(true)'
                )
                self.driver.execute_script('mobile: clickGesture', {'elementId': target_price.id})


            # 4. 数量选择
            logging.info("选择数量...")
            if self.driver.find_elements(by=By.ID, value='layout_num'):
                clicks_needed = len(self.config.users) - 1
                if clicks_needed > 0:
                    try:
                        plus_button = self.driver.find_element(By.ID, 'img_jia')
                        for i in range(clicks_needed):
                            rect = plus_button.rect
                            x = rect['x'] + rect['width'] // 2
                            y = rect['y'] + rect['height'] // 2
                            self.driver.execute_script("mobile: clickGesture", {
                                "x": x,
                                "y": y,
                                "duration": 50
                            })
                            time.sleep(0.02)
                    except Exception as e:
                        logging.warning(f"快速点击加号失败: {e}")


            # 5. 确定购买
            logging.info("确定购买...")
            if not self.ultra_fast_click(By.ID, "btn_buy_view"):
                # 备用按钮文本
                self.ultra_fast_click(AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textMatches(".*确定.*|.*购买.*")')

            # 6. 批量选择用户
            logging.info("选择用户...")
            user_clicks = [(AppiumBy.ANDROID_UIAUTOMATOR, f'new UiSelector().text("{user}")') for user in
                           self.config.users]
            if not self.ultra_batch_click(user_clicks):
                return False

            # 7. 提交订单
            logging.info("提交订单...")
            submit_selectors = [
                (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().text("立即提交")'),
                (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textMatches(".*提交.*|.*确认.*")'),
                (By.XPATH, '//*[contains(@text,"提交")]')
            ]
            self.smart_wait_and_click(*submit_selectors[0], submit_selectors[1:])

            end_time = time.time()
            logging.info(f"抢票流程完成，耗时: {end_time - start_time:.2f}秒")
            return True

        except Exception as e:
            logging.error(f"抢票过程发生错误: {e}")
            return False
        finally:
            time.sleep(1)  # 给最后的操作一点时间
            self.driver.quit()

    def run_with_retry(self, max_retries=3):
        """带重试机制的抢票"""
        for attempt in range(max_retries):
            logging.info(f"第 {attempt + 1} 次尝试...")
            if self.run_ticket_grabbing():
                logging.info("抢票成功！")
                return True
            else:
                logging.warning(f"第 {attempt + 1} 次尝试失败")
                if attempt < max_retries - 1:
                    logging.info("2秒后重试...")
                    time.sleep(2)
                    # 重新初始化驱动
                    try:
                        self.driver.quit()
                    except:
                        pass
                    self._setup_driver()

        logging.error("所有尝试均失败")
        return False


# 使用示例
if __name__ == "__main__":
    bot = DamaiBot()
    auto_bt = bot.config.auto_buy_time
    if auto_bt:
        from datetime import datetime
        parts = auto_bt.split(":")
        target = datetime.now().replace(hour=int(parts[0]), minute=int(parts[1]), second=int(parts[2]) if len(parts) > 2 else 0, microsecond=0)
        wait = (target - datetime.now()).total_seconds()
        if wait > 0:
            print(f"Waiting {wait:.0f}s until {auto_bt}...")
            time.sleep(wait)
        else:
            print(f"{auto_bt} passed, starting now")
    bot.run_with_retry(max_retries=3)