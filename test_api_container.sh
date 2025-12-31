#!/bin/bash
# XQsim Patch Trace API テストスクリプト (コンテナ内実行用)

API_BASE_URL="http://localhost:8000"

echo "============================================================"
echo "XQsim Patch Trace API テスト開始"
echo "API URL: $API_BASE_URL"
echo "============================================================"

# テスト1: ヘルスチェック
echo ""
echo "テスト1: /health エンドポイント"
echo "------------------------------------------------------------"
HEALTH_RESPONSE=$(curl -s -w "\n%{http_code}" "$API_BASE_URL/health")
HTTP_CODE=$(echo "$HEALTH_RESPONSE" | tail -n1)
BODY=$(echo "$HEALTH_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    echo "✓ ステータスコード: $HTTP_CODE"
    echo "✓ レスポンス: $BODY"
    HEALTH_OK=true
else
    echo "✗ エラー: HTTP $HTTP_CODE"
    echo "  レスポンス: $BODY"
    HEALTH_OK=false
fi

# テスト2: 簡単なQASM
echo ""
echo "テスト2: /trace エンドポイント (簡単なQASM)"
echo "------------------------------------------------------------"

SIMPLE_QASM='OPENQASM 2.0;
include "qelib1.inc";
qreg q[1];
creg meas[1];
h q[0];
measure q[0] -> meas[0];
'

PAYLOAD=$(cat <<EOF
{
  "qasm": "OPENQASM 2.0;\ninclude \"qelib1.inc\";\nqreg q[1];\ncreg meas[1];\nh q[0];\nmeasure q[0] -> meas[1];",
  "config": "example_cmos_d5"
}
EOF
)

echo "送信するQASM:"
echo "$SIMPLE_QASM"
echo ""
echo "リクエスト送信中（最大5分待機）..."

TRACE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE_URL/trace" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD" \
    --max-time 300)

HTTP_CODE=$(echo "$TRACE_RESPONSE" | tail -n1)
BODY=$(echo "$TRACE_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    echo "✓ ステータスコード: $HTTP_CODE"
    echo "$BODY" | python3 -m json.tool > test_result_simple.json 2>/dev/null || echo "$BODY" > test_result_simple.json
    echo "✓ 結果を test_result_simple.json に保存しました"
    
    # パッチ情報を確認
    if command -v python3 &> /dev/null; then
        PATCH_COUNT=$(echo "$BODY" | python3 -c "import sys, json; d=json.load(sys.stdin); print(len(d.get('result', {}).get('patch', {}).get('initial', [])))" 2>/dev/null || echo "N/A")
        EVENT_COUNT=$(echo "$BODY" | python3 -c "import sys, json; d=json.load(sys.stdin); print(len(d.get('result', {}).get('patch', {}).get('events', [])))" 2>/dev/null || echo "N/A")
        echo "✓ 初期パッチ数: $PATCH_COUNT"
        echo "✓ パッチイベント数: $EVENT_COUNT"
    fi
    TRACE_SIMPLE_OK=true
else
    echo "✗ エラー: HTTP $HTTP_CODE"
    echo "  レスポンス: ${BODY:0:500}"
    TRACE_SIMPLE_OK=false
fi

# テスト3: 既存のQASMファイル
echo ""
echo "テスト3: /trace エンドポイント (既存のQASMファイル)"
echo "------------------------------------------------------------"

QASM_FILE="src/quantum_circuits/open_qasm/qft_n2.qasm"
if [ ! -f "$QASM_FILE" ]; then
    echo "✗ ファイルが見つかりません: $QASM_FILE"
    TRACE_FILE_OK=false
else
    QASM_CONTENT=$(cat "$QASM_FILE")
    ESCAPED_QASM=$(echo "$QASM_CONTENT" | python3 -c "import sys, json; print(json.dumps(sys.stdin.read()))" 2>/dev/null || echo "\"$QASM_CONTENT\"")
    
    PAYLOAD=$(cat <<EOF
{
  "qasm": $ESCAPED_QASM,
  "config": "example_cmos_d5"
}
EOF
)
    
    echo "送信するQASMファイル: $QASM_FILE"
    echo "リクエスト送信中（最大5分待機）..."
    
    TRACE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE_URL/trace" \
        -H "Content-Type: application/json" \
        -d "$PAYLOAD" \
        --max-time 300)
    
    HTTP_CODE=$(echo "$TRACE_RESPONSE" | tail -n1)
    BODY=$(echo "$TRACE_RESPONSE" | sed '$d')
    
    if [ "$HTTP_CODE" = "200" ]; then
        echo "✓ ステータスコード: $HTTP_CODE"
        echo "$BODY" | python3 -m json.tool > test_result_qft.json 2>/dev/null || echo "$BODY" > test_result_qft.json
        echo "✓ 結果を test_result_qft.json に保存しました"
        
        # パッチ情報を確認
        if command -v python3 &> /dev/null; then
            PATCH_COUNT=$(echo "$BODY" | python3 -c "import sys, json; d=json.load(sys.stdin); print(len(d.get('result', {}).get('patch', {}).get('initial', [])))" 2>/dev/null || echo "N/A")
            EVENT_COUNT=$(echo "$BODY" | python3 -c "import sys, json; d=json.load(sys.stdin); print(len(d.get('result', {}).get('patch', {}).get('events', [])))" 2>/dev/null || echo "N/A")
            echo "✓ 初期パッチ数: $PATCH_COUNT"
            echo "✓ パッチイベント数: $EVENT_COUNT"
        fi
        TRACE_FILE_OK=true
    else
        echo "✗ エラー: HTTP $HTTP_CODE"
        echo "  レスポンス: ${BODY:0:500}"
        TRACE_FILE_OK=false
    fi
fi

# 結果サマリー
echo ""
echo "============================================================"
echo "テスト結果サマリー"
echo "============================================================"
echo "ヘルスチェック: $([ "$HEALTH_OK" = true ] && echo '✓ 成功' || echo '✗ 失敗')"
echo "簡単なQASM: $([ "$TRACE_SIMPLE_OK" = true ] && echo '✓ 成功' || echo '✗ 失敗')"
echo "既存のQASMファイル: $([ "$TRACE_FILE_OK" = true ] && echo '✓ 成功' || echo '✗ 失敗')"

PASSED=0
[ "$HEALTH_OK" = true ] && PASSED=$((PASSED+1))
[ "$TRACE_SIMPLE_OK" = true ] && PASSED=$((PASSED+1))
[ "$TRACE_FILE_OK" = true ] && PASSED=$((PASSED+1))

echo ""
echo "合計: $PASSED/3 テストが成功しました"

