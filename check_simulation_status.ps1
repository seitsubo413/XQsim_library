# XQsimシミュレーションの状態を定期的に確認するスクリプト

Write-Host "XQsimシミュレーション状態確認スクリプト" -ForegroundColor Cyan
Write-Host "Ctrl+Cで停止できます" -ForegroundColor Yellow
Write-Host ""

$checkCount = 0
while ($true) {
    $checkCount++
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "`n[$timestamp] 確認 #$checkCount" -ForegroundColor Green
    Write-Host "=" * 60
    
    # 最新のサイクル数を取得
    $cycle = docker-compose logs xqsim-backend 2>&1 | Select-String -Pattern "Cycle:" | Select-Object -Last 1
    if ($cycle) {
        Write-Host "サイクル数: $($cycle.Line)" -ForegroundColor White
    }
    
    # sim_doneの状態を確認
    $simDone = docker-compose logs xqsim-backend 2>&1 | Select-String -Pattern "sim_done:" | Select-Object -Last 1
    if ($simDone) {
        if ($simDone.Line -match "sim_done: True") {
            Write-Host "✓ シミュレーション完了！" -ForegroundColor Green
            break
        } else {
            Write-Host "シミュレーション進行中..." -ForegroundColor Yellow
        }
    }
    
    # 各ユニットのdone状態を確認
    $units = docker-compose logs xqsim-backend 2>&1 | Select-String -Pattern "qif.done:|qid.done:|pdu.done:|piu.done:|psu.done:|tcu.done:|qxu.done:|pfu.done:|lmu.done:" | Select-Object -Last 9
    if ($units) {
        Write-Host "`nユニット状態:" -ForegroundColor Cyan
        foreach ($unit in $units) {
            if ($unit.Line -match "True") {
                Write-Host "  ✓ $($unit.Line)" -ForegroundColor Green
            } else {
                Write-Host "  ✗ $($unit.Line)" -ForegroundColor Red
            }
        }
    }
    
    # エラーを確認
    $errors = docker-compose logs xqsim-backend 2>&1 | Select-String -Pattern "ERROR|Exception|Traceback|invalid pchpp" | Select-Object -Last 3
    if ($errors) {
        Write-Host "`n警告/エラー:" -ForegroundColor Yellow
        foreach ($error in $errors) {
            Write-Host "  $($error.Line)" -ForegroundColor Yellow
        }
    }
    
    # 30秒待機
    Start-Sleep -Seconds 30
}

Write-Host "`n確認を終了しました。" -ForegroundColor Cyan

