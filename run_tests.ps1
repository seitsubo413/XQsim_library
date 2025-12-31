# XQsim API テストスクリプト
# 複数の量子回路をテストし、結果を保存します

$baseUrl = "http://localhost:8000"
$outputDir = "test_results"

# 出力ディレクトリ作成
if (-not (Test-Path $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir | Out-Null
}

# テストケース定義
$testCases = @(
    @{
        name = "test1_single_h"
        description = "1量子ビット: Hゲートのみ"
        qasm = @"
OPENQASM 2.0;
include "qelib1.inc";
qreg q[1];
creg c[1];
h q[0];
measure q[0] -> c[0];
"@
    },
    @{
        name = "test2_bell_state"
        description = "2量子ビット: Bell状態 (H + CNOT)"
        qasm = @"
OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
h q[0];
cx q[0],q[1];
measure q[0] -> c[0];
measure q[1] -> c[1];
"@
    },
    @{
        name = "test3_ghz_3qubit"
        description = "3量子ビット: GHZ状態"
        qasm = @"
OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
creg c[3];
h q[0];
cx q[0],q[1];
cx q[1],q[2];
measure q[0] -> c[0];
measure q[1] -> c[1];
measure q[2] -> c[2];
"@
    },
    @{
        name = "test4_multiple_h"
        description = "3量子ビット: 複数のHゲート"
        qasm = @"
OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
creg c[3];
h q[0];
h q[1];
h q[2];
measure q[0] -> c[0];
measure q[1] -> c[1];
measure q[2] -> c[2];
"@
    },
    @{
        name = "test5_x_gate"
        description = "2量子ビット: Xゲート (NOT)"
        qasm = @"
OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
x q[0];
x q[1];
measure q[0] -> c[0];
measure q[1] -> c[1];
"@
    },
    @{
        name = "test6_z_gate"
        description = "2量子ビット: Zゲート"
        qasm = @"
OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
h q[0];
z q[0];
h q[0];
measure q[0] -> c[0];
measure q[1] -> c[1];
"@
    }
)

# サマリー用配列
$summary = @()

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "XQsim API テスト開始" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ヘルスチェック
Write-Host "API ヘルスチェック中..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "$baseUrl/health" -Method Get
    Write-Host "API Status: $($health.status)" -ForegroundColor Green
    Write-Host ""
} catch {
    Write-Host "エラー: APIに接続できません。docker-compose up が実行されているか確認してください。" -ForegroundColor Red
    exit 1
}

# 各テストケースを実行
foreach ($test in $testCases) {
    Write-Host "----------------------------------------" -ForegroundColor Gray
    Write-Host "テスト: $($test.name)" -ForegroundColor Yellow
    Write-Host "説明: $($test.description)" -ForegroundColor Gray
    Write-Host ""
    
    $body = @{
        qasm = $test.qasm
        config = "example_cmos_d5"
    } | ConvertTo-Json
    
    $startTime = Get-Date
    
    try {
        Write-Host "実行中... (時間がかかる場合があります)" -ForegroundColor Cyan
        
        $result = Invoke-RestMethod -Uri "$baseUrl/trace" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 3600
        
        $endTime = Get-Date
        $duration = ($endTime - $startTime).TotalSeconds
        
        # 結果をファイルに保存
        $outputFile = "$outputDir/$($test.name).json"
        $result | ConvertTo-Json -Depth 20 | Out-File -FilePath $outputFile -Encoding utf8
        
        # サマリー情報を収集
        $meta = $result.result.meta
        $summaryEntry = @{
            name = $test.name
            description = $test.description
            status = "SUCCESS"
            total_cycles = $meta.total_cycles
            elapsed_seconds = $meta.elapsed_seconds
            num_patches = $meta.num_patches
            num_events = $result.result.patch.events.Count
            termination_reason = $meta.termination_reason
            local_duration = [math]::Round($duration, 2)
        }
        $summary += $summaryEntry
        
        Write-Host "完了!" -ForegroundColor Green
        Write-Host "  サイクル数: $($meta.total_cycles)" -ForegroundColor White
        Write-Host "  実行時間: $($meta.elapsed_seconds) 秒" -ForegroundColor White
        Write-Host "  パッチ数: $($meta.num_patches)" -ForegroundColor White
        Write-Host "  イベント数: $($result.result.patch.events.Count)" -ForegroundColor White
        Write-Host "  保存先: $outputFile" -ForegroundColor Gray
        
    } catch {
        $endTime = Get-Date
        $duration = ($endTime - $startTime).TotalSeconds
        
        $summaryEntry = @{
            name = $test.name
            description = $test.description
            status = "FAILED"
            error = $_.Exception.Message
            local_duration = [math]::Round($duration, 2)
        }
        $summary += $summaryEntry
        
        Write-Host "失敗: $($_.Exception.Message)" -ForegroundColor Red
    }
    
    Write-Host ""
}

# サマリーを保存
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "テスト完了 - サマリー" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$summaryFile = "$outputDir/summary.json"
$summaryOutput = @{
    timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    total_tests = $testCases.Count
    passed = ($summary | Where-Object { $_.status -eq "SUCCESS" }).Count
    failed = ($summary | Where-Object { $_.status -eq "FAILED" }).Count
    results = $summary
}
$summaryOutput | ConvertTo-Json -Depth 10 | Out-File -FilePath $summaryFile -Encoding utf8

Write-Host ""
Write-Host "結果サマリー:" -ForegroundColor Yellow
$summary | ForEach-Object {
    $color = if ($_.status -eq "SUCCESS") { "Green" } else { "Red" }
    Write-Host "  [$($_.status)] $($_.name): $($_.description)" -ForegroundColor $color
    if ($_.status -eq "SUCCESS") {
        Write-Host "         サイクル: $($_.total_cycles), イベント: $($_.num_events)" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "サマリー保存先: $summaryFile" -ForegroundColor Cyan
Write-Host ""
Write-Host "個別の結果ファイル:" -ForegroundColor Yellow
Get-ChildItem $outputDir -Filter "*.json" | ForEach-Object {
    Write-Host "  - $($_.Name)" -ForegroundColor Gray
}

