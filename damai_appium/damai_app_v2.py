# -*- coding: UTF-8 -*-
"""
__Author__ = "BlueCestbon"
__Version__ = "2.0.0"
__Description__ = "大麦app抢票自动化 - 优化版"
__Created__ = 2025/09/13 19:27
"""

import time, re, os, logging, sys, urllib.request, urllib.error
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
        self._check_appium_server()
        self._setup_driver()


    def _check_appium_server(self, max_wait=30):
        """Check if Appium server is reachable, exit with guidance if not"""
        server_url = self.config.server_url
        status_url = f"{server_url}/status"
        logging.info(f"Checking Appium server: {server_url} ...")
        start = time.time()
        while time.time() - start < max_wait:
            try:
                req = urllib.request.Request(status_url)
                with urllib.request.urlopen(req, timeout=3) as resp:
                    if resp.status == 200:
                        logging.info("[OK] Appium server ready")
                        return
            except (urllib.error.URLError, ConnectionRefusedError, OSError, Exception):
                pass
            elapsed = int(time.time() - start)
            suffix = f"({elapsed}s/{max_wait}s)"
            logging.info("  Waiting for Appium... " + suffix)
            time.sleep(2)
        logging.error("=" * 60)
        logging.error("[FAIL] Cannot connect to Appium server!")
        logging.error("  Target: " + server_url)
        logging.error("")
        logging.error("Start Appium first:")
        logging.error("  1. Install Node.js 20.19+")
        logging.error("  2. npm install -g appium")
        logging.error("  3. appium driver install uiautomator2")
        logging.error("  4. appium --port 4723")
        logging.error("  Or run: python start.py")
        logging.error("")
        logging.error("Also ensure Android device has USB debugging enabled")
        logging.error("  adb devices   # should show your device")
        logging.error("=" * 60)
        sys.exit(2)

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
        max_conn_retries = 3
        for attempt in range(1, max_conn_retries + 1):
            try:
                self.driver = webdriver.Remote(self.config.server_url, options=device_app_info)
                break
            except Exception as e:
                if attempt < max_conn_retries:
                    msg = "Appium connect failed (%d/%d), retrying..." % (attempt, max_conn_retries)
                    logging.warning(msg)
                    time.sleep(2)
                else:
                    logging.error("[FAIL] Appium connect final failure: " + str(e))
                    raise

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

    def select_users_robust(self, timeout=3):
        """多策略选择观演人 - text/textContains/description/CheckBox遍历"""
        users = self.config.users
        found = 0

        # Strategy 1: Try CheckBox + text sibling pattern (common in Damai)
        # On Damai confirm page, each user is typically a LinearLayout containing:
        # CheckBox (clickable) + TextView (name)
        try:
            # Find all CheckBox elements that are clickable
            checkboxes = self.driver.find_elements(
                AppiumBy.ANDROID_UIAUTOMATOR,
                'new UiSelector().className("android.widget.CheckBox").clickable(true)'
            )
            logging.info(f"  找到 {len(checkboxes)} 个勾选框")
            if checkboxes and len(checkboxes) >= len(users):
                for i, user in enumerate(users):
                    try:
                        self.driver.execute_script("mobile: clickGesture", {
                            "elementId": checkboxes[i].id,
                            "duration": 30
                        })
                        logging.info(f"  点击勾选框 #{i+1}: {user}")
                        found += 1
                        time.sleep(0.1)
                    except Exception as e:
                        logging.warning(f"  勾选框 #{i+1} 点击失败: {e}")
                if found > 0:
                    logging.info(f"  [Strategy 1] 选中 {found} 个用户")
                    return True
        except Exception as e:
            logging.info(f"  Strategy 1 失败: {e}")

        # Strategy 2: textContains + click parent LinearLayout
        for user in users:
            try:
                el = WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((
                        AppiumBy.ANDROID_UIAUTOMATOR,
                        f'new UiSelector().textContains("{user}")'
                    ))
                )
                # Click the element itself (might be the name text, tap it to toggle)
                self.driver.execute_script("mobile: clickGesture", {
                    "elementId": el.id, "duration": 30
                })
                logging.info(f"  [Strategy 2] 点击: {user}")
                found += 1
                time.sleep(0.1)
            except TimeoutException:
                logging.warning(f"  [Strategy 2] 未找到: {user}")
            except Exception as e:
                logging.warning(f"  [Strategy 2] 失败 {user}: {e}")

        if found > 0:
            logging.info(f"  [Strategy 2] 选中 {found} 个用户")
            return True

        # Strategy 3: Dump and scan all text elements
        logging.info("  Strategy 3: 扫描页面所有文本元素...")
        try:
            all_texts = self.driver.find_elements(
                AppiumBy.ANDROID_UIAUTOMATOR,
                'new UiSelector().className("android.widget.TextView")'
            )
            for el in all_texts:
                txt = (el.text or el.get_attribute("text") or "").strip()
                if txt:
                    logging.info(f"    TextView: '{txt}'")
            # Try clicking by index if we found matching texts
            for user in users:
                for i, el in enumerate(all_texts):
                    txt = (el.text or el.get_attribute("text") or "").strip()
                    if user in txt or txt in user:
                        self.driver.execute_script("mobile: clickGesture", {
                            "elementId": el.id, "duration": 30
                        })
                        logging.info(f"  [Strategy 3] 点击: '{txt}' for {user}")
                        found += 1
                        time.sleep(0.1)
                        break
        except Exception as e:
            logging.warning(f"  Strategy 3 失败: {e}")

        logging.info(f"  最终选中 {found}/{len(users)} 个用户")
        return found > 0

    def ultra_batch_click_fuzzy(self, elements_info, user_names, timeout=2):
        """模糊批量点击 - 每个用户尝试多种选择器，找到1个即停止"""
        found = 0
        for user in user_names:
            clicked = False
            # Try all selectors for this user
            for by, value in elements_info:
                if value.find(user) == -1:  # skip selectors not for this user
                    continue
                try:
                    el = WebDriverWait(self.driver, timeout).until(
                        EC.presence_of_element_located((by, value))
                    )
                    rect = el.rect
                    x = rect["x"] + rect["width"] // 2
                    y = rect["y"] + rect["height"] // 2
                    self.driver.execute_script("mobile: clickGesture", {
                        "x": x, "y": y, "duration": 30
                    })
                    logging.info(f"点击用户: {user}")
                    found += 1
                    clicked = True
                    time.sleep(0.1)
                    break  # found this user, stop trying other selectors
                except TimeoutException:
                    continue
                except Exception as e:
                    continue
            if not clicked:
                logging.warning(f"超时未找到用户: {user}")
        logging.info(f"成功找到 {found} 个用户")
        return found > 0

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


    def wait_for_user_login(self):
        """Wait for the user to manually log into the Damai app"""
        skip = os.environ.get('DAMAI_SKIP_LOGIN', '').lower() in ('1', 'true', 'yes')
        if skip:
            logging.info('DAMAI_SKIP_LOGIN=1 - skipping manual login prompt')
            logging.info('Assuming user is already logged in on the phone.')
            logging.info('=' * 60)
            return

        logging.info("=" * 60)
        logging.info("[USER ACTION REQUIRED]")
        logging.info("=" * 60)
        logging.info("Please manually complete these steps on your phone:")
        logging.info("  1. Open the Damai app")
        logging.info("  2. Log in with your account (scan/password/SMS)")
        logging.info("  3. Make sure you are on the main/home page")
        logging.info("")
        logging.info("The script will NOT proceed until you press Enter.")
        logging.info("=" * 60)
        try:
            input("Press Enter after you have logged in...")
        except (EOFError, KeyboardInterrupt):
            logging.info("Aborted by user.")
            sys.exit(0)
        logging.info("Proceeding with ticket automation...")

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
    def _run_reserved_mode(self):
        """预约模式：已预约演出，直接等待开抢→购买→提交"""
        try:
            logging.info("=== 预约模式：已预约演出，等待开抢 ===")
            
            # 0. 如果有 auto_buy_time，先等到开售时间
            if self.config.auto_buy_time:
                from datetime import datetime
                bt = self.config.auto_buy_time
                parts = bt.split(":")
                target = datetime.now().replace(
                    hour=int(parts[0]), minute=int(parts[1]),
                    second=int(parts[2]) if len(parts) > 2 else 0, microsecond=0
                )
                wait_sec = (target - datetime.now()).total_seconds()
                if wait_sec > 0:
                    logging.info(f"等待开售时间 {bt}（剩余 {wait_sec:.0f} 秒）...")
                    # 每5秒刷新一次，保持活跃
                    while wait_sec > 0:
                        sleep = min(wait_sec, 5)
                        time.sleep(sleep)
                        wait_sec = (target - datetime.now()).total_seconds()
                        if wait_sec <= 0:
                            break
                        logging.info(f"  距开售还有 {wait_sec:.0f} 秒，保持等待...")
                logging.info(f"开售时间 {bt} 已到，开始抢票！")
            
            # 1. 导航到演出详情页（搜索 + 点击）
            if not self.navigate_to_concert():
                logging.warning("导航到演出详情页失败")
                return False
            
            # 1.5 尝试从页面自动检测开售时间
            detected_time = self.extract_sale_time()
            if detected_time and not self.config.auto_buy_time:
                from datetime import datetime
                self.config.auto_buy_time = detected_time
                parts = detected_time.split(":")
                target = datetime.now().replace(
                    hour=int(parts[0]), minute=int(parts[1]),
                    second=int(parts[2]) if len(parts) > 2 else 0, microsecond=0
                )
                wait_sec = (target - datetime.now()).total_seconds()
                if wait_sec > 0:
                    logging.info(f"等待开售时间 {detected_time}（剩余 {wait_sec:.0f} 秒）...")
                    while wait_sec > 0:
                        sleep = min(wait_sec, 1)
                        time.sleep(sleep)
                        wait_sec = (target - datetime.now()).total_seconds()
                    logging.info(f"开售时间到！")

            # 2. 已预约模式：不需要选城市/日期/票价，直接等「立即购买」按钮出现
            logging.info("已预约模式：等待「立即购买」按钮...")
            purchase_button_found = False
            start_wait = time.time()
            
            # 按钮选择器（覆盖各种状态）
            purchase_selectors = [
                (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().text("立即购买")'),
                (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().text("去抢票")'),
                (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textContains("立即")'),
                (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textContains("购买")'),
                (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textContains("开抢")'),
                (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textContains("抢票")'),
                (By.ID, "cn.damai:id/trade_project_detail_purchase_status_bar_container_fl"),
            ]
            
            max_wait = 120  # 最多等 120 秒
            while time.time() - start_wait < max_wait:
                for by, val in purchase_selectors:
                    try:
                        el = self.driver.find_element(by, val)
                        txt = el.text or el.get_attribute("text") or ""
                        if txt and any(w in txt for w in ["购买", "抢票", "开抢", "立即", "选座"]):
                            logging.info(f"找到按钮: '{txt}'，点击！")
                            self.driver.execute_script("mobile: clickGesture", {
                                "elementId": el.id, "duration": 30
                            })
                            purchase_button_found = True
                            break
                    except:
                        continue
                
                if purchase_button_found:
                    break
                
                # 检查是否有倒计时
                try:
                    xml = self.driver.page_source
                    import re as _re3
                    countdowns = _re3.findall(r'text="(\d{2}:\d{2}:\d{2})"', xml)
                    if countdowns:
                        logging.info(f"  倒计时: {countdowns[0]}，继续等待...")
                except:
                    pass
                
                time.sleep(1)
            
            if not purchase_button_found:
                logging.warning("超时未找到购买按钮")
                # 列出页面上的可点击元素帮助调试
                try:
                    clickables = self.driver.find_elements(
                        AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().clickable(true)'
                    )
                    for el in clickables[:5]:
                        txt = (el.text or el.get_attribute("text") or "").strip()
                        if txt:
                            logging.info(f"  可点击: '{txt}'")
                except:
                    pass
                return False
            
            time.sleep(0.5)
            
            # 3. 确认订单页：用户和票价已由预约预选，只需提交
            logging.info("确认订单页...")
            time.sleep(1)
            
            # 3a. 选择数量（如果需要）
            logging.info("选择数量...")
            try:
                # 尝试找数量选择器
                qty_btns = self.driver.find_elements(
                    AppiumBy.ANDROID_UIAUTOMATOR, 
                    'new UiSelector().text("+")'
                )
                if qty_btns:
                    # 点击+号到需要的数量（用户数）
                    for _ in range(len(self.config.users) - 1):
                        self.driver.execute_script("mobile: clickGesture", {
                            "elementId": qty_btns[0].id, "duration": 30
                        })
                        time.sleep(0.2)
                    logging.info(f"  数量设为 {len(self.config.users)}")
            except:
                logging.info("  数量选择跳过（可能已预选）")
            
            # 3b. 提交订单
            logging.info("提交订单...")
            submit_selectors = [
                (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().text("提交订单")'),
                (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().text("立即支付")'),
                (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textMatches(".*提交.*|.*支付.*|.*确认.*")'),
                (By.ID, "cn.damai:id/trade_submit_order_button"),
                (By.ID, "bottom_button"),
            ]
            
            submitted = False
            for by, val in submit_selectors:
                try:
                    el = WebDriverWait(self.driver, 3).until(
                        EC.presence_of_element_located((by, val))
                    )
                    if self.config.if_commit_order:
                        self.driver.execute_script("mobile: clickGesture", {
                            "elementId": el.id, "duration": 30
                        })
                        logging.info(f"  ✅ 订单已提交！")
                        submitted = True
                        break
                    else:
                        logging.info(f"  [模拟模式] 找到提交按钮，但 if_commit_order=false")
                        submitted = True
                        break
                except TimeoutException:
                    continue
            
            if not submitted:
                logging.warning("未找到提交按钮")
                return False
            
            elapsed = time.time() - start_wait if 'start_wait' in dir() else 0
            logging.info(f"抢票流程完成！耗时 {elapsed:.1f} 秒")
            return submitted
            
        except Exception as e:
            logging.error(f"抢票流程异常: {e}")
            import traceback
            traceback.print_exc()
            return False
    def _run_full_mode(self):
        """完整模式：从头搜索→选城市→选票价→选用户→提交（未预约场景）"""
        try:
            logging.info("=== 完整模式：搜索 + 选择 ===")
            start_time = time.time()

            # 0.5 自动检测开售时间
            self.extract_sale_time()
            if self.config.auto_buy_time:
                from datetime import datetime
                bt = self.config.auto_buy_time
                parts = bt.split(":")
                target = datetime.now().replace(
                    hour=int(parts[0]), minute=int(parts[1]),
                    second=int(parts[2]) if len(parts) > 2 else 0, microsecond=0
                )
                wait_sec = (target - datetime.now()).total_seconds()
                if wait_sec > 0:
                    logging.info(f"等待开售时间 {bt}（剩余 {wait_sec:.0f} 秒）...")
                    while wait_sec > 0:
                        sleep = min(wait_sec, 1)
                        time.sleep(sleep)
                        wait_sec = (target - datetime.now()).total_seconds()
                    logging.info(f"开售时间到！")

            # 0.6 搜索并进入演出详情页
            if not self.navigate_to_concert():
                logging.warning("导航到演出详情页失败")
                return False

            # 1. 城市选择
            logging.info("选择城市...")
            if not self.two_stage_click(self.config.city, timeout=3):
                logging.warning("城市选择失败")
                return False

            # 2. 点击购买按钮
            logging.info("点击购买按钮...")
            book_selectors = [
                (By.ID, "cn.damai:id/trade_project_detail_purchase_status_bar_container_fl"),
                (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textMatches(".*预约.*|.*购买.*|.*立即.*|.*开抢.*|.*抢票.*|.*选座.*|.*已预约.*")'),
                (By.XPATH, '//*[contains(@text,"预约") or contains(@text,"购买") or contains(@text,"开抢") or contains(@text,"抢票")]'),
                (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().className("android.widget.Button").clickable(true)'),
            ]
            if not self.smart_wait_and_click(*book_selectors[0], book_selectors[1:]):
                logging.warning("购买按钮点击失败")
                return False

            # 3. 票价选择
            logging.info("选择票价...")
            try:
                price_container = self.driver.find_element(By.ID, 'cn.damai:id/project_detail_perform_price_flowlayout')
                target_price = price_container.find_element(
                    AppiumBy.ANDROID_UIAUTOMATOR,
                    f'new UiSelector().className("android.widget.FrameLayout").index({self.config.price_index}).clickable(true)'
                )
                self.driver.execute_script('mobile: clickGesture', {'elementId': target_price.id})
            except Exception as e:
                print(f"票价选择失败，启动备用方案: {e}")
                price_container = self.wait.until(
                    EC.presence_of_element_located((By.ID, 'cn.damai:id/project_detail_perform_price_flowlayout')))
                target_price = price_container.find_element(
                    AppiumBy.ANDROID_UIAUTOMATOR,
                    f'new UiSelector().className("android.widget.FrameLayout").index({self.config.price_index}).clickable(true)'
                )
                self.driver.execute_script('mobile: clickGesture', {'elementId': target_price.id})

            # 4. 选择数量
            logging.info("选择数量...")
            try:
                qty_btns = self.driver.find_elements(
                    AppiumBy.ANDROID_UIAUTOMATOR,
                    'new UiSelector().text("+")'
                )
                if qty_btns:
                    for _ in range(len(self.config.users) - 1):
                        self.driver.execute_script("mobile: clickGesture", {
                            "elementId": qty_btns[0].id, "duration": 30
                        })
                        time.sleep(0.15)
            except:
                pass

            # 5. 确定购买
            logging.info("确定购买...")
            if not self.ultra_fast_click(By.ID, "btn_buy_view"):
                self.ultra_fast_click(AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textMatches(".*确定.*|.*购买.*")')

            # 6. 选择用户 - 多策略
            logging.info("选择用户...")
            if not self.select_users_robust():
                return False

            # 7. 提交订单
            logging.info("提交订单...")
            submit_selectors = [
                (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().text("提交订单")'),
                (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().text("立即支付")'),
                (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textMatches(".*提交.*|.*支付.*|.*确认.*")'),
                (By.ID, "cn.damai:id/trade_submit_order_button"),
                (By.ID, "bottom_button"),
            ]
            submitted = False
            for by, val in submit_selectors:
                try:
                    el = WebDriverWait(self.driver, 3).until(
                        EC.presence_of_element_located((by, val))
                    )
                    if self.config.if_commit_order:
                        self.driver.execute_script("mobile: clickGesture", {
                            "elementId": el.id, "duration": 30
                        })
                        logging.info(f"  ====== 订单已提交！======")
                    else:
                        logging.info(f"  [模拟模式] 找到提交按钮，但 if_commit_order=false")
                    submitted = True
                    break
                except TimeoutException:
                    continue

            if not submitted:
                logging.warning("未找到提交按钮")
                return False

            elapsed = time.time() - start_time
            logging.info(f"完整模式完成！耗时 {elapsed:.1f} 秒")
            return True

        except Exception as e:
            logging.error(f"完整模式异常: {e}")
            import traceback
            traceback.print_exc()
            return False

    def run_ticket_grabbing(self):
        """统一入口：根据 config.mode 选择模式（reserved=预约 / full=完整）"""
        mode = getattr(self.config, 'mode', 'reserved')
        logging.info(f"抢票模式: {mode}")
        if mode == 'full':
            return self._run_full_mode()
        else:
            return self._run_reserved_mode()


    def run_with_retry(self, max_retries=3):
        """带重试机制的抢票 - 高频率持续重试"""
        retry_delay = 0.5  # 0.5秒重试间隔
        max_duration = 300  # 最多持续5分钟
        
        start_time = time.time()
        attempt = 0
        
        while time.time() - start_time < max_duration:
            attempt += 1
            logging.info(f"第 {attempt} 次尝试 (已运行 {(time.time()-start_time):.0f}s)...")
            
            if self.run_ticket_grabbing():
                logging.info(f"抢票成功！共尝试 {attempt} 次")
                return True
            
            elapsed = time.time() - start_time
            if elapsed >= max_duration:
                logging.warning(f"超过最大持续时间 {max_duration}s，停止重试")
                break
            
            logging.info(f"第 {attempt} 次失败，{retry_delay}s 后重试...")
            time.sleep(retry_delay)
        
        logging.error(f"所有 {attempt} 次尝试均失败")
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
