# 大麦抢票自动化系统

基于 Selenium + Appium 的大麦网自动抢票工具，支持 **Web 端**（Chrome 浏览器）和**移动端**（Android 真机）双模式。

> 移动端（Appium + UIAutomator2）是当前**主推方案**，Web 端 Selenium 可能被大麦风控拦截，作为备用。

---

## 快速开始

```bash
# 1. 安装依赖
pip install selenium appium-python-client

# 2. 移动端模式（推荐）
python start.py

# 3. Web 端模式（备用）
python start.py --web

# 4. 命令行模式
python start.py --cli
```

`start.py` 会自动检测环境（Python / Node.js / Appium / ADB / Chrome），缺失时给出平台专属安装指引。

---

## 运行模式

| 命令 | 模式 | 说明 |
|------|------|------|
| `python start.py` | Web 控制台 | FastAPI 界面（http://127.0.0.1:8765），可视化操作 |
| `python start.py --cli` | 命令行 | 终端交互式选择 Web/Mobile |
| `python start.py --web` | Web 端直达 | 跳过选择，直接启动 Selenium |
| `python start.py --dev` | 开发模式 | Vite HMR 热更新 |
| `python damai/damai.py` | Web 端原生 | 绕过 start.py，直接运行 |

---

## 环境要求

| 组件 | Web 端 | 移动端 | 安装方式 |
|------|:------:|:------:|----------|
| Python 3.8+ | ✅ | ✅ | [python.org](https://python.org) |
| Chrome 浏览器 | ✅ | — | [google.cn/chrome](https://www.google.cn/chrome) |
| ChromeDriver | ✅ | — | 自动安装 |
| Node.js 20+ | — | ✅ | [nodejs.org](https://nodejs.org) |
| Appium 3.x | — | ✅ | `npm install -g appium` |
| UIAutomator2 | — | ✅ | `appium driver install uiautomator2` |
| Android SDK | — | ✅ | Android Studio 或独立 platform-tools |
| Android 真机 | — | ✅ | USB 连接，开启「开发者选项」+「USB 调试」 |

### 移动端一键安装

```bash
# Windows
.\setup_mobile.ps1
```

---

## 配置文件

### Web 端：`damai/config.json`

```json
{
  "index_url": "https://www.damai.cn/",
  "login_url": "https://passport.damai.cn/login?ru=https%3A%2F%2Fwww.damai.cn%2F",
  "target_url": "https://detail.damai.cn/item.htm?id=演出ID",
  "users": ["观演人1", "观演人2"],
  "city": "北京",
  "dates": ["2026-06-15"],
  "prices": ["680"],
  "if_listen": true,
  "if_commit_order": false,
  "max_retries": 10000
}
```

| 字段 | 说明 |
|------|------|
| `target_url` | 演出详情页 URL，从浏览器复制 |
| `users` | 观演人姓名，与 APP 中已添加的一致 |
| `city` | 城市（不需要选城市的演出留空 `""`） |
| `dates` | 场次日期，如 `["2026-06-15", "2026-06-16"]` |
| `prices` | 票面价格，如 `["380", "680"]` |
| `if_listen` | 是否监听开票（`true` = 缺货时自动刷新等待） |
| `if_commit_order` | **`false` = 仅模拟，不下单**（测试用） |
| `max_retries` | 最大重试次数 |

### 移动端：`damai_appium/config.jsonc`

```json
{
  "server_url": "http://127.0.0.1:4723",
  "keyword": "周杰伦",
  "users": ["观演人1", "观演人2"],
  "city": "北京",
  "date": "06.15",
  "price": "内场680元",
  "price_index": 1,
  "if_commit_order": false
}
```

**两种模式**：
- `mode: "reserved"`（默认）— 预约模式：已收藏演出，到点直接抢
- `mode: "full"` — 完整模式：搜索演出 → 选城市/日期/票价 → 选人 → 下单

---

## 抢票流程

### Web 端

```
① 启动 → 加载 Cookie / 扫码登录
② 进入演出详情页
③ 选择 城市 → 日期 → 票价 → 数量
④ 轮询「立即购买」按钮（自动处理缺货/刷新）
⑤ 选座购买 / 直购
⑥ UserSelectorChain 4 策略选观影人（Div→Checkbox→TextClick→JS）
⑦ 提交订单
```

### 移动端

```
① Appium 连接 Android 真机 → 打开大麦 APP
② 搜索演出关键词 → 进入详情页
③ 等待 auto_buy_time 到点
④ 轮询「立即购买」→ 点击
⑤ select_users_robust 多策略选人（CheckBox→textContains→页面扫描）
⑥ 提交订单
⑦ run_with_retry：0.5s 间隔 × 最长 300s 高频重试
```

---

## 常见问题

### Cookie 过期
删除 `damai/damai_cookies.pkl`，重新运行脚本会在浏览器中弹出扫码登录。

### ChromeDriver 不匹配
```bash
pip install chromedriver-autoinstaller
# 或手动下载: https://googlechromelabs.github.io/chrome-for-testing/
```

### 移动端 Appium 连接失败
```bash
# 确认 Appium 运行中
appium --version

# 检查设备
adb devices

# 手动启动
appium --port 4723
```

### 编码乱码
```bash
# 设置 UTF-8
set PYTHONIOENCODING=utf-8    # Windows CMD
$env:PYTHONIOENCODING="utf-8" # PowerShell
```

---

## 项目结构

```
damai/
├── concert.py              # Web 端核心（Concert 类）
├── concert_selectors.py    # 选择器常量（Sel class）
├── concert_user_selector.py # 观影人选择策略链（4 策略）
├── check_environment.py    # 环境检测 + ChromeDriver 自动安装
├── damai.py                # Web 端入口
├── config.json             # Web 端配置
├── config.py               # Config 数据类
├── quick_diagnosis.py      # 快速诊断工具
damai_appium/
├── damai_app_v2.py         # 移动端核心（DamaiBot 类，推荐）
├── damai_app.py            # 移动端 V1（已弃用）
├── config.jsonc            # 移动端配置文件
├── config.py               # Config 加载
console/                    # Web 控制台（FastAPI + React）
tests/
├── test_smoke.py           # 冒烟测试（29 个业务逻辑测试）
├── test_setup_validation.py # 基础设施测试（16 个）
└── unit/                   # 单元测试（4 个）
```

---

## 测试

```bash
# 全部测试（49 个）
pytest tests/ -v

# 仅冒烟测试（业务逻辑）
pytest tests/test_smoke.py -v

# 仅环境检测测试
pytest tests/unit/ -v
```

---

## 免责声明

本项目仅用于学习和研究，请勿用于商业用途。使用本工具产生的一切后果由使用者自行承担。
