# 安卓端V2版本介绍
## 执行命令
### 开启appium服务端
```bash
appium --address 0.0.0.0 --port 4723 --relaxed-security
```
如果确定某些按钮点击后不会马上有新页面加载，可以加 `--relaxed-security` 启动 Appium，然后用 `mobile: clickGesture` 直接原生点击：
```python
# 这里的target是一个可以执行click()的对象
driver.execute_script('mobile: clickGesture', {'elementId': target.id})
```
### 执行抢票任务
```bash
cd damai_appium
python damai_app_v2.py
```


## 只处理了抢票的，预约的暂未考虑

## 功能
- 大麦的大部分票**只能在APP端购买**，所以只运行了安卓侧的实现并进行修改
- APP更新，**界面信息的票价的Text是空串""**，无法再使用之前的方案去找按钮click，V2是通过分析页面信息，使用索引的方式获取，缺点是需要预先手动写进去，不知道后续有没有什么新的方法获取
- 增加重试机制

## 优化：
- 考虑到界面可以先点到搜索列表，移除了键入搜索和点击搜索按钮的步骤
- 增加了一些加速的配置capabilities，以及一些性能优化的配置
- 优化了多人勾选的逻辑，收集坐标信息，几乎一次性全部点击
- 使用`WebDriverWait`替代`driver.implicitly_wait(5)`，大大提升效率
- 优化了`click()`的方式，使用
```python
driver.execute_script("mobile: clickGesture", {
                "x": x,
                "y": y,
                "duration": 50  # 极短点击时间
            })
```
- 优化显示逻辑，展示执行的进度

## 展望
- 实现预约功能