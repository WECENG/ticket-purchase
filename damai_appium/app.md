# Android V2 使用说明

Android V2 是推荐的移动端入口，支持自动搜索目标演出、匹配城市与日期、
选择票档和观演人，并根据配置停在提交前或提交后验证支付界面。

## Windows

在项目根目录打开两个 PowerShell 窗口：

```powershell
.\start_appium.ps1
```

```powershell
.\start_ticket_grabbing.ps1
```

## macOS / Linux

```bash
./start_appium.sh
./start_ticket_grabbing.sh
```

正式运行前编辑 `config.jsonc`：

- `start_at`：开售时间，格式为 `YYYY-MM-DD HH:MM:SS`；`null` 表示立即开始。
- `if_commit_order`：`false` 会安全停在提交按钮前；`true` 才会创建订单。
- `price_index`：仅在 APP 隐藏票档文字、无法按价格匹配时作为备用索引。

脚本不会自动完成支付。只有检测到支付界面后才会报告下单成功。
