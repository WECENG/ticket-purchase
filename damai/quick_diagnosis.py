#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
快速诊断脚本
用于快速检查 ChromeDriver 状态
"""

import os
import re
import subprocess
import sys


def get_version(output):
    """从输出中提取版本号"""
    match = re.search(r'(\d+)\.', output)
    return match.group(1) if match else None


def run_command(cmd):
    """运行命令并获取输出"""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def check_chrome():
    """检查 Chrome 浏览器"""
    print("检查 Chrome 浏览器...")
    chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

    if not os.path.exists(chrome_path):
        print("  ✗ 未找到 Chrome 浏览器")
        print("  请安装: https://www.google.com/chrome/")
        return None

    version = run_command([chrome_path, "--version"])
    if version:
        print(f"  ✓ {version}")
        return get_version(version)
    else:
        print("  ✗ 无法获取版本")
        return None


def check_chromedriver(chrome_version):
    """检查 ChromeDriver"""
    print("\n检查 ChromeDriver...")

    # 检查系统路径中的 chromedriver
    paths = [
        "/opt/homebrew/bin/chromedriver",
        "/usr/local/bin/chromedriver",
    ]

    found = False
    driver_version = None

    for path in paths:
        if os.path.exists(path) or os.path.islink(path):
            version = run_command([path, "--version"])
            if version:
                driver_version = get_version(version)
                print(f"  ✓ 找到: {path}")
                print(f"  ✓ 版本: {version}")
                found = True
                break

    if not found:
        print("  ✗ 未找到 ChromeDriver")
        print("\n安装方法:")
        print("  方案1 (推荐): brew install --cask chromedriver")
        print("  方案2: 手动下载 https://googlechromelabs.github.io/chrome-for-testing/")
        return None

    # 检查版本匹配
    if chrome_version and driver_version:
        if chrome_version == driver_version:
            print(f"  ✓ 版本匹配 (Chrome {chrome_version} = ChromeDriver {driver_version})")
            return True
        else:
            print(f"  ✗ 版本不匹配!")
            print(f"    Chrome: {chrome_version}")
            print(f"    ChromeDriver: {driver_version}")
            print("\n解决方案:")
            print("  方案1: 更新 Chrome 到最新版本")
            print("  方案2: 卸载并重新安装 ChromeDriver")
            print("    brew uninstall --cask chromedriver")
            print("    brew install --cask chromedriver")
            return False

    return None


def check_autoinstaller():
    """检查自动安装器"""
    print("\n检查 chromedriver-autoinstaller...")
    try:
        import chromedriver_autoinstaller
        print("  ✓ chromedriver-autoinstaller 已安装")
        return True
    except ImportError:
        print("  ✗ chromedriver-autoinstaller 未安装")
        print("\n安装命令: pip install chromedriver-autoinstaller")
        return False


def main():
    print("=" * 50)
    print("ChromeDriver 快速诊断")
    print("=" * 50)
    print()

    chrome_version = check_chrome()
    driver_match = check_chromedriver(chrome_version)
    has_autoinstaller = check_autoinstaller()

    print("\n" + "=" * 50)
    if driver_match is True:
        print("✓ 所有检查通过！")
        print("\n可以运行抢票脚本:")
        print("  python damai/damai.py")
        return 0
    else:
        print("✗ 部分检查未通过")
        print("\n建议操作:")
        if driver_match is False:
            print("  1. 版本不匹配，选择:")
            print("     - 更新 Chrome: 在 Chrome 中打开 设置 → 关于 Chrome")
            print("     - 或重装 ChromeDriver: brew reinstall --cask chromedriver")
        else:
            print("  1. 安装 ChromeDriver: brew install --cask chromedriver")

        if not has_autoinstaller:
            print("  2. 安装自动安装器: pip install chromedriver-autoinstaller")

        print("\n或运行完整环境检查:")
        print("  python damai/check_environment.py")
        return 1


if __name__ == "__main__":
    sys.exit(main())
