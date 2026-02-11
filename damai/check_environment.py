#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
环境检查脚本
在运行抢票脚本前，使用此脚本检查环境是否配置正确
"""

import os
import re
import subprocess
import sys


def _get_version_from_output(output):
    """从命令输出中提取主版本号"""
    match = re.search(r'(\d+)\.', output)
    return match.group(1) if match else None


def _run_command_get_version(command):
    """运行命令并获取版本信息"""
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def check_python_version():
    """检查 Python 版本"""
    print("Python 版本检查...")
    version = sys.version_info
    print(f"  当前版本: {version.major}.{version.minor}.{version.micro}")

    if version.major < 3 or (version.major == 3 and version.minor < 7):
        print("  ✗ 需要 Python 3.7 或更高版本")
        return False
    print("  ✓ Python 版本符合要求\n")
    return True


def check_dependencies():
    """检查依赖包"""
    print("依赖包检查...")
    dependencies = {
        'selenium': 'Selenium WebDriver',
        'webdriver_manager': 'WebDriver Manager',
    }

    missing = []
    for package, description in dependencies.items():
        try:
            __import__(package)
            print(f"  ✓ {description} ({package})")
        except ImportError:
            print(f"  ✗ {description} ({package}) 未安装")
            missing.append(package)

    if missing:
        print(f"\n  安装命令: pip install {' '.join(missing)}\n")
        return False
    print()
    return True


def check_chrome():
    """检查 Chrome 浏览器"""
    print("Chrome 浏览器检查...")
    chrome_paths = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary",
        "/usr/bin/google-chrome",
        "/usr/bin/chromium-browser",
    ]

    for chrome_path in chrome_paths:
        if os.path.exists(chrome_path):
            version_str = _run_command_get_version([chrome_path, "--version"])
            if version_str:
                chrome_version = _get_version_from_output(version_str)
                if chrome_version:
                    print(f"  ✓ Chrome 浏览器: {version_str}")
                    print(f"  ✓ 主版本号: {chrome_version}")
                    print()
                    return True

    print("  ✗ 未找到 Chrome 浏览器")
    print("  请安装 Chrome: https://www.google.com/chrome/")
    print()
    return False


def check_chromedriver():
    """检查 ChromeDriver"""
    print("ChromeDriver 检查...")
    chromedriver_paths = [
        "/opt/homebrew/bin/chromedriver",
        "/usr/local/bin/chromedriver",
        "/opt/homebrew/Caskroom/chromedriver",
    ]

    for driver_path in chromedriver_paths:
        if os.path.exists(driver_path) or os.path.islink(driver_path):
            version_str = _run_command_get_version([driver_path, "--version"])
            if version_str:
                driver_version = _get_version_from_output(version_str)
                if driver_version:
                    print(f"  ✓ ChromeDriver: {version_str}")
                    print(f"  ✓ 主版本号: {driver_version}")
                    print(f"  ✓ 路径: {driver_path}")
                    print()
                    return True

    print("  ⚠ 未找到 ChromeDriver")
    print("  安装方法:")
    print("    - macOS: brew install --cask chromedriver")
    print("    - 或使用脚本自动安装: chromedriver-autoinstaller")
    print()
    return False


def check_version_match():
    """检查 Chrome 和 ChromeDriver 版本是否匹配"""
    print("版本匹配检查...")

    chrome_version = None
    chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    if os.path.exists(chrome_path):
        version_str = _run_command_get_version([chrome_path, "--version"])
        if version_str:
            chrome_version = _get_version_from_output(version_str)

    driver_version = None
    driver_path = "/opt/homebrew/bin/chromedriver"
    if os.path.exists(driver_path) or os.path.islink(driver_path):
        version_str = _run_command_get_version([driver_path, "--version"])
        if version_str:
            driver_version = _get_version_from_output(version_str)

    if not chrome_version or not driver_version:
        print("  ⚠ 无法获取版本信息")
        print()
        return False

    print(f"  Chrome 版本: {chrome_version}")
    print(f"  ChromeDriver 版本: {driver_version}")

    if chrome_version == driver_version:
        print("  ✓ 版本匹配")
        print()
        return True
    else:
        print(f"  ✗ 版本不匹配！(差距: {abs(int(chrome_version) - int(driver_version))} 个主版本)")
        print("\n  解决方案:")
        print("  方案1: 更新 Chrome 浏览器到最新版本（推荐）")
        print("    打开 Chrome → 设置 → 关于 Chrome → 等待更新")
        print()
        print("  方案2: 安装匹配的 ChromeDriver")
        print("    卸载当前版本: brew uninstall --cask chromedriver")
        print("    手动下载: https://googlechromelabs.github.io/chrome-for-testing/")
        print()
        return False


def get_chromedriver_path():
    """
    获取 ChromeDriver 路径，如果不存在则自动安装
    供其他脚本导入使用
    :return: ChromeDriver 可执行文件路径
    """
    chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

    if not os.path.exists(chrome_path):
        raise RuntimeError("未找到 Chrome 浏览器，请先安装 Chrome")

    # 获取 Chrome 版本
    chrome_version_str = _run_command_get_version([chrome_path, "--version"])
    chrome_version = _get_version_from_output(chrome_version_str) if chrome_version_str else None

    if not chrome_version:
        raise RuntimeError("无法获取 Chrome 版本")

    # 检查已安装的 ChromeDriver 是否匹配
    chromedriver_paths = [
        "/opt/homebrew/bin/chromedriver",
        "/usr/local/bin/chromedriver",
    ]

    for driver_path in chromedriver_paths:
        if os.path.exists(driver_path) or os.path.islink(driver_path):
            driver_version_str = _run_command_get_version([driver_path, "--version"])
            if driver_version_str:
                driver_version = _get_version_from_output(driver_version_str)
                if driver_version == chrome_version:
                    # 版本匹配，直接使用
                    return driver_path

    # 版本不匹配或不存在，使用自动安装器
    print(f"  Chrome 版本: {chrome_version}")
    print("  正在自动安装匹配的 ChromeDriver...")
    try:
        import chromedriver_autoinstaller
        chromedriver_path = chromedriver_autoinstaller.install()

        # 验证安装的版本
        result = _run_command_get_version([chromedriver_path, "--version"])
        if not result:
            raise RuntimeError("ChromeDriver 无法执行")

        print(f"  ✓ ChromeDriver 安装成功: {result}")
        return chromedriver_path
    except ImportError:
        raise RuntimeError("未安装 chromedriver-autoinstaller，请运行: pip install chromedriver-autoinstaller")
    except Exception as e:
        raise RuntimeError(f"ChromeDriver 安装失败: {e}")


def check_config_file():
    """检查配置文件"""
    print("配置文件检查...")
    config_file = 'config.json'

    if not os.path.exists(config_file):
        print(f"  ✗ 未找到配置文件: {config_file}")
        print(f"  请先创建配置文件")
        print()
        return False

    try:
        import json
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        print(f"  ✓ 配置文件存在: {config_file}")

        required_fields = ['index_url', 'login_url', 'target_url', 'users']
        missing_fields = [field for field in required_fields if field not in config]

        if missing_fields:
            print(f"  ✗ 缺少必需字段: {', '.join(missing_fields)}")
            print()
            return False

        print(f"  ✓ 必需字段完整")
        print(f"  ✓ 观众人数: {len(config['users'])} 人")
        print()
        return True
    except Exception as e:
        print(f"  ✗ 配置文件错误: {e}")
        print()
        return False


def main():
    print("\n" + "=" * 60)
    print("大麦抢票脚本 - 环境检查工具")
    print("=" * 60)
    print()

    checks = [
        ("Python 版本", check_python_version),
        ("依赖包", check_dependencies),
        ("Chrome 浏览器", check_chrome),
        ("ChromeDriver", check_chromedriver),
        ("版本匹配", check_version_match),
        ("配置文件", check_config_file),
    ]

    results = []
    for name, check_func in checks:
        try:
            results.append((name, check_func()))
        except Exception as e:
            print(f"  ✗ 检查出错: {e}\n")
            results.append((name, False))

    print("=" * 60)
    print("检查结果汇总")
    print("=" * 60)

    all_passed = all(result for _, result in results)
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"  {name}: {status}")

    print("=" * 60)

    if all_passed:
        print("\n✓ 所有检查通过！可以运行抢票脚本了。")
        print("  运行命令: python damai.py\n")
        return 0
    else:
        print("\n✗ 部分检查未通过，请根据上述提示修复问题。\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
