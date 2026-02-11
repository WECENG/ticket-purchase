# 🚀 大麦抢票快速开始指南

## 📋 一键检查环境

```bash
./check_environment.sh
```

## 🎯 三步开始抢票

### 第1步：启动Appium服务器
```bash
./start_appium.sh
```

### 第2步：准备抢票环境
1. 在Android设备上打开大麦APP
2. 搜索目标演出（如"刘若英"）
3. 进入演出详情页面

### 第3步：开始抢票
```bash
./start_ticket_grabbing.sh
```

## ⚙️ 配置抢票参数

编辑 `damai_appium/config.jsonc` 文件：

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

## 🔧 常见问题解决

### 问题1：Node.js版本不兼容
```bash
# 升级Node.js
brew upgrade node
```

### 问题2：Android设备未连接
```bash
# 启动模拟器
/Users/shengwang/Library/Android/sdk/emulator/emulator -avd Medium_Phone_API_36.0

# 检查设备
/Users/shengwang/Library/Android/sdk/platform-tools/adb devices
```

### 问题3：Appium服务器未启动
```bash
# 设置环境变量并启动
export ANDROID_HOME=/Users/shengwang/Library/Android/sdk
export ANDROID_SDK_ROOT=/Users/shengwang/Library/Android/sdk
appium --port 4723
```

## 📱 移动端抢票完整流程

1. **环境检查**：`./check_environment.sh`
2. **启动服务**：`./start_appium.sh`
3. **准备设备**：在模拟器上打开大麦APP
4. **配置参数**：编辑 `config.jsonc`
5. **开始抢票**：`./start_ticket_grabbing.sh`

## ⚠️ 重要提醒

- 确保在开售时间前准备好所有环境
- 提前测试脚本运行是否正常
- 建议使用专门的测试账号
- 遵守大麦网使用条款

## 🆘 获取帮助

如果遇到问题，请：
1. 运行 `./check_environment.sh` 检查环境
2. 查看 `README.md` 详细文档
3. 检查控制台错误信息
4. 确认所有依赖已正确安装

---

**祝您抢票成功！** 🎫✨
