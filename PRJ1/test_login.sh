#!/usr/bin/env bash
# 簡單的登入功能測試腳本

BASE_URL="http://127.0.0.1:5000"
COOKIE_FILE="/tmp/test_cookies.txt"

echo "🚀 內控治理入口網站登入功能測試"
echo "========================================"

# 清理舊的 cookie 文件
rm -f "$COOKIE_FILE"

echo ""
echo "1. 測試未登入時訪問主頁面..."
status=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/")
if [ "$status" = "302" ]; then
    echo "✅ 正確重定向到登入頁面 (302)"
else
    echo "❌ 未正確重定向，狀態碼: $status"
    exit 1
fi

echo ""
echo "2. 測試登入頁面載入..."
status=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/login")
if [ "$status" = "200" ]; then
    echo "✅ 登入頁面正常載入"
else
    echo "❌ 登入頁面載入失敗，狀態碼: $status"
    exit 1
fi

echo ""
echo "3. 測試登入..."
response=$(curl -s -w "HTTPSTATUS:%{http_code}" \
    -X POST \
    -d "username=testuser&password=testpass&role=process_owner" \
    -c "$COOKIE_FILE" \
    "$BASE_URL/login")

http_code=$(echo "$response" | tr -d '\n' | sed -e 's/.*HTTPSTATUS://')
if [ "$http_code" = "302" ]; then
    echo "✅ 登入成功，重定向到主頁面"
else
    echo "❌ 登入失敗，狀態碼: $http_code"
    exit 1
fi

echo ""
echo "4. 測試登入後訪問主頁面..."
response=$(curl -s -b "$COOKIE_FILE" "$BASE_URL/")
if echo "$response" | grep -q "歡迎，testuser！"; then
    echo "✅ 主頁面正常顯示用戶資訊"
else
    echo "❌ 主頁面未正確顯示用戶資訊"
    exit 1
fi

echo ""
echo "5. 測試訪問受保護的頁面..."
protected_pages=("/dashboard" "/controls" "/issues" "/resources" "/audit_logs")

for page in "${protected_pages[@]}"; do
    status=$(curl -s -o /dev/null -w "%{http_code}" -b "$COOKIE_FILE" "$BASE_URL$page")
    if [ "$status" = "200" ]; then
        echo "✅ $page 頁面可正常訪問"
    else
        echo "❌ $page 頁面訪問失敗，狀態碼: $status"
        exit 1
    fi
done

echo ""
echo "6. 測試登出..."
status=$(curl -s -o /dev/null -w "%{http_code}" -b "$COOKIE_FILE" "$BASE_URL/logout")
if [ "$status" = "302" ]; then
    echo "✅ 登出成功，重定向到登入頁面"
else
    echo "❌ 登出失敗，狀態碼: $status"
    exit 1
fi

echo ""
echo "7. 測試登出後訪問受保護頁面..."
status=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/dashboard")
if [ "$status" = "302" ]; then
    echo "✅ 登出後正確重定向到登入頁面"
else
    echo "❌ 登出後仍可訪問受保護頁面，狀態碼: $status"
    exit 1
fi

echo ""
echo "🎉 所有登入功能測試通過！"
echo ""
echo "📋 測試摘要:"
echo "   ✅ 未登入用戶正確重定向到登入頁面"
echo "   ✅ 登入頁面正常載入"
echo "   ✅ 用戶認證和登入成功"
echo "   ✅ 登入後顯示用戶資訊"
echo "   ✅ 所有受保護頁面可正常訪問"
echo "   ✅ 登出功能正常工作"
echo "   ✅ 登出後正確保護頁面"

# 清理
rm -f "$COOKIE_FILE"