# 大麦抢票自动化系统

一个基于Selenium和Appium的大麦网抢票自动化工具，支持Web端和移动端抢票。

## 🚀 功能特性

- **双端支持**：支持Web端（Selenium）和移动端（Appium）抢票
- **智能抢票**：自动选择城市、票价、观演人员
- **高性能**：优化的点击策略，适合抢票场景
- **可配置**：灵活的配置文件，支持多种演出设置
- **重试机制**：内置重试逻辑，提高成功率

## 📋 系统要求

### 基础环境
- **Python**: 3.9+
- **Node.js**: 20.19.0+ 或 22.12.0+ 或 24.0.0+
- **操作系统**: macOS / Windows / Linux

### Web端抢票
- **Chrome浏览器**: 最新版本
- **ChromeDriver**: 自动下载

### 移动端抢票
- **Android SDK**: 已配置环境变量
- **Appium**: 3.1.0+
- **Android设备**: 真机或模拟器

## 🛠️ 安装指南

### 1. 克隆项目
```bash
git clone <repository-url>
cd ticket-purchase
```

### 2. 安装Python依赖
```bash
# 使用Poetry（推荐）
poetry install

# 或使用pip
pip install -r requirements.txt
```

### 3. 移动端环境配置（仅移动端抢票需要）

#### 3.1 安装Node.js
```bash
# macOS (使用Homebrew)
brew install node

# 验证版本（需要20.19.0+）
node --version
```

#### 3.2 安装Appium
```bash
# 全局安装Appium
npm install -g appium

# 安装UiAutomator2驱动
appium driver install uiautomator2

# 验证安装
appium --version
```

#### 3.3 配置Android环境
```bash
# 设置环境变量（添加到 ~/.zshrc 或 ~/.bashrc）
export ANDROID_HOME=/path/to/your/android/sdk
export ANDROID_SDK_ROOT=/path/to/your/android/sdk

# 验证ADB
adb devices
```

## ⚙️ 配置说明

### 移动端配置 (config.jsonc)

```json
{
  "server_url": "http://127.0.0.1:4723",
  "keyword": "刘若英",
  "users": [
    "观演人1",
    "观演人2"
  ],
  "city": "泉州",
  "date": "10.04",
  "price": "799元",
  "price_index": 1,
  "if_commit_order": true
}
```

#### 配置参数说明

| 参数 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `server_url` | string | Appium服务器地址 | `"http://127.0.0.1:4723"` |
| `keyword` | string | 搜索关键词 | `"刘若英"` |
| `users` | array | 观演人员名单 | `["张三", "李四"]` |
| `city` | string | 演出城市 | `"泉州"` |
| `date` | string | 演出日期 | `"10.04"` |
| `price` | string | 票价描述 | `"799元"` |
| `price_index` | number | 票价索引（从0开始） | `1` |
| `if_commit_order` | boolean | 是否自动提交订单 | `true` |

### Web端配置 (config.json)

```json
{
  "index_url": "https://www.damai.cn/",
  "login_url": "https://passport.damai.cn/login",
  "target_url": "https://detail.damai.cn/item.htm?id=xxx",
  "users": ["张三", "李四"],
  "city": "广州",
  "date": "2023-10-28",
  "price": "1039",
  "if_commit_order": true
}
```

## 🚀 使用方法

### 移动端抢票（推荐）

#### 1. 启动Android设备
```bash
# 启动模拟器
/Users/shengwang/Library/Android/sdk/emulator/emulator -avd YourAVDName

# 或连接真机（需开启USB调试）
adb devices
```

#### 2. 安装大麦APP
在Android设备上安装大麦APP，并登录账号。

#### 3. 启动Appium服务器
```bash
# 设置环境变量
export ANDROID_HOME=/Users/shengwang/Library/Android/sdk
export ANDROID_SDK_ROOT=/Users/shengwang/Library/Android/sdk

# 启动Appium服务器
appium --port 4723
```

#### 4. 配置抢票参数
编辑 `damai_appium/config.jsonc` 文件，设置：
- 搜索关键词
- 观演人员
- 城市、日期、票价
- 其他参数

#### 5. 运行抢票脚本
```bash
cd damai_appium
ANDROID_HOME=/Users/shengwang/Library/Android/sdk ANDROID_SDK_ROOT=/Users/shengwang/Library/Android/sdk python damai_app_v2.py
```

### Web端抢票

#### 1. 配置参数
编辑 `damai/config.json` 文件，设置目标演出URL和其他参数。

#### 2. 运行抢票脚本
```bash
cd damai
python damai.py
```

## 🔧 故障排除

### 常见问题

#### 1. Node.js版本不兼容
```
Error: Node version must be at least ^20.19.0 || ^22.12.0 || >=24.0.0
```
**解决方案**：升级Node.js到兼容版本
```bash
# macOS
brew upgrade node
```

#### 2. Android环境变量未设置
```
Error: Neither ANDROID_HOME nor ANDROID_SDK_ROOT environment variable was exported
```
**解决方案**：设置环境变量
```bash
export ANDROID_HOME=/path/to/android/sdk
export ANDROID_SDK_ROOT=/path/to/android/sdk
```

#### 3. 设备连接问题
```
Error: Unable to find an active device or emulator
```
**解决方案**：
- 检查设备连接：`adb devices`
- 确保设备已开启USB调试
- 检查Android版本是否匹配

#### 4. Appium连接失败
```
Error: Connection refused
```
**解决方案**：
- 确保Appium服务器正在运行
- 检查端口4723是否被占用
- 验证服务器地址配置

### 调试技巧

#### 1. 检查设备状态
```bash
# 检查连接的设备
adb devices

# 检查设备Android版本
adb shell getprop ro.build.version.release

# 检查设备是否完全启动
adb shell getprop sys.boot_completed
```

#### 2. 验证Appium连接
```bash
# 检查Appium服务器状态
curl http://127.0.0.1:4723/status
```

#### 3. 查看应用包名
```bash
# 查看已安装的应用
adb shell pm list packages | grep damai
```

## 📁 项目结构

```
ticket-purchase/
├── damai/                    # Web端抢票
│   ├── damai.py             # 主程序
│   ├── config.py            # 配置类
│   ├── config.json          # 配置文件
│   └── requirements.txt      # 依赖文件
├── damai_appium/             # 移动端抢票
│   ├── damai_app_v2.py      # 优化版主程序
│   ├── damai_app.py         # 原版主程序
│   ├── config.py            # 配置类
│   ├── config.jsonc         # 配置文件
│   └── app.md               # 应用说明
├── tests/                    # 测试文件
├── doc/                      # 文档
├── img/                      # 图片资源
└── README.md                 # 说明文档
```

## 🎯 使用流程

### 移动端抢票完整流程

1. **环境准备**
   - 安装Node.js (20.19.0+)
   - 安装Appium和驱动
   - 配置Android SDK环境变量

2. **设备准备**
   - 启动Android模拟器或连接真机
   - 安装大麦APP并登录

3. **配置参数**
   - 编辑 `config.jsonc` 文件
   - 设置演出信息、观演人员等

4. **启动服务**
   - 启动Appium服务器
   - 验证设备连接

5. **执行抢票**
   - 在模拟器上打开大麦APP
   - 搜索目标演出
   - 运行抢票脚本

6. **监控结果**
   - 脚本自动执行抢票流程
   - 查看控制台输出
   - 检查订单状态

## ⚠️ 注意事项

1. **合法使用**：请遵守大麦网的使用条款，合理使用自动化工具
2. **账号安全**：建议使用专门的测试账号
3. **网络环境**：确保网络连接稳定
4. **设备性能**：建议使用性能较好的设备进行抢票
5. **时间设置**：提前设置好抢票时间，确保脚本在开售时间运行

## 🤝 贡献指南

欢迎提交Issue和Pull Request来改进项目。

## 📄 许可证

本项目仅供学习和研究使用，请勿用于商业用途。

---

**最后更新**: 2024年10月
**版本**: 2.0.0