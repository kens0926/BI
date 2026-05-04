#!/usr/bin/env python3
"""
登入功能測試腳本
測試完整的登入、訪問受保護頁面、登出流程
"""

import requests
import sys

BASE_URL = "http://127.0.0.1:5000"

def test_login_flow():
    """測試登入流程"""
    print("🔐 測試登入功能...")

    # 建立 session 來保持 cookies
    session = requests.Session()

    # 1. 測試未登入時訪問主頁面
    print("1. 測試未登入時訪問主頁面...")
    response = session.get(f"{BASE_URL}/")
    if response.status_code == 302 and 'login' in response.headers.get('Location', ''):
        print("✅ 正確重定向到登入頁面")
    else:
        print("❌ 未正確重定向")
        return False

    # 2. 測試登入頁面載入
    print("2. 測試登入頁面載入...")
    response = session.get(f"{BASE_URL}/login")
    if response.status_code == 200:
        print("✅ 登入頁面正常載入")
    else:
        print("❌ 登入頁面載入失敗")
        return False

    # 3. 測試登入
    print("3. 測試登入...")
    login_data = {
        'username': 'testuser',
        'password': 'testpass',
        'role': 'process_owner'
    }
    response = session.post(f"{BASE_URL}/login", data=login_data, allow_redirects=False)

    if response.status_code == 302 and response.headers.get('Location') == '/':
        print("✅ 登入成功，重定向到主頁面")
    else:
        print("❌ 登入失敗")
        return False

    # 4. 測試登入後訪問主頁面
    print("4. 測試登入後訪問主頁面...")
    response = session.get(f"{BASE_URL}/")
    if response.status_code == 200 and '歡迎，testuser！' in response.text:
        print("✅ 主頁面正常顯示用戶資訊")
    else:
        print("❌ 主頁面未正確顯示")
        return False

    # 5. 測試訪問受保護的頁面
    print("5. 測試訪問受保護的頁面...")
    protected_pages = ['/dashboard', '/controls', '/issues', '/resources', '/audit_logs']

    for page in protected_pages:
        response = session.get(f"{BASE_URL}{page}")
        if response.status_code == 200:
            print(f"✅ {page} 頁面可正常訪問")
        else:
            print(f"❌ {page} 頁面訪問失敗")
            return False

    # 6. 測試登出
    print("6. 測試登出...")
    response = session.get(f"{BASE_URL}/logout", allow_redirects=False)
    if response.status_code == 302 and response.headers.get('Location') == '/login':
        print("✅ 登出成功，重定向到登入頁面")
    else:
        print("❌ 登出失敗")
        return False

    # 7. 測試登出後訪問受保護頁面
    print("7. 測試登出後訪問受保護頁面...")
    response = session.get(f"{BASE_URL}/dashboard")
    if response.status_code == 302 and 'login' in response.headers.get('Location', ''):
        print("✅ 登出後正確重定向到登入頁面")
    else:
        print("❌ 登出後仍可訪問受保護頁面")
        return False

    print("\n🎉 所有登入功能測試通過！")
    return True

def test_role_based_access():
    """測試基於角色的權限訪問"""
    print("\n👥 測試基於角色的權限訪問...")

    roles_to_test = [
        ('system_admin', '系統管理員'),
        ('audit_manager', '稽核主管'),
        ('control_owner', '控制點負責人'),
        ('tester', '測試人員'),
        ('process_owner', '改善負責人'),
        ('approver', '核准者'),
        ('reviewer', '審閱者')
    ]

    for role_code, role_name in roles_to_test:
        print(f"\n測試角色: {role_name} ({role_code})")

        session = requests.Session()

        # 登入
        login_data = {
            'username': f'test_{role_code}',
            'password': 'testpass',
            'role': role_code
        }
        response = session.post(f"{BASE_URL}/login", data=login_data)
        if response.status_code != 200 and '歡迎' not in response.text:
            print(f"❌ {role_name} 登入失敗")
            continue

        # 檢查角色顯示
        if role_name in response.text:
            print(f"✅ {role_name} 角色正確顯示")
        else:
            print(f"❌ {role_name} 角色顯示錯誤")

        # 測試儀表板訪問權限
        dashboard_response = session.get(f"{BASE_URL}/dashboard")
        if role_code in ['system_admin', 'audit_manager', 'control_owner', 'tester', 'process_owner', 'approver', 'reviewer']:
            if dashboard_response.status_code == 200:
                print(f"✅ {role_name} 可訪問儀表板")
            else:
                print(f"❌ {role_name} 無法訪問儀表板")
        else:
            print(f"ℹ️ {role_name} 角色權限檢查")

    print("\n🎉 角色權限測試完成！")

if __name__ == "__main__":
    print("🚀 內控治理入口網站登入功能測試")
    print("=" * 50)

    try:
        # 測試基本登入流程
        if test_login_flow():
            # 測試角色權限
            test_role_based_access()
        else:
            print("❌ 基本登入測試失敗")
            sys.exit(1)

    except requests.exceptions.ConnectionError:
        print("❌ 無法連接到伺服器，請確保 Flask 應用程式正在運行")
        print("   執行: cd /Users/chienyuancheng/Project/PRJ1 && source .venv/bin/activate && python app.py")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 測試過程中發生錯誤: {e}")
        sys.exit(1)

    print("\n✅ 所有測試完成！登入系統運行正常。")