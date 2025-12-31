# XQsim Library インターフェース開発 引き継ぎ資料

**作成日**: 2024年12月31日  
**目的**: Windows環境からMac環境への開発移行のための引き継ぎ

---

## 1. プロジェクト概要

### 目的
XQsimをライブラリとして使用し、QASMを入力として受け取り、パッチ情報をJSONで返すインターフェースを構築する。

### 構成ファイル
- `src/patch_trace_backend.py` - メインのインターフェースロジック
- `src/api_server.py` - FastAPI サーバー
- `Dockerfile` / `docker-compose.yml` - Docker環境
- `test_api.py` - APIテストスクリプト
- `test_xqsim_standalone.py` - XQsim単体テストスクリプト

---

## 2. 現在の状態

### 動作するもの
- ✅ Dockerコンテナのビルドと起動
- ✅ FastAPI サーバー (`/health`, `/trace` エンドポイント)
- ✅ QASMのコンパイル（transpile → qisa_compile → assemble）
- ✅ シミュレーションの開始

### 動作しないもの / 問題点
- ❌ シミュレーションが終了しない（非常に多くのサイクルが必要）
- ❌ `qid.done`, `pdu.done`, `piu.done`, `lmu.done` が `False` のまま

---

## 3. 調査結果

### 重要な発見
**インターフェース層の問題ではない。XQsim単体でも同じ問題が発生する。**

```
XQsim単体テスト結果（pprIIZZZ_n5サンプル回路）:
Cycle 17000:
  PSU.srmem.double_buffer: [0].state=filling, [1].state=reading
  psu.pchinfo_full=False
  → 正常に進行している

Cycle 31000+:
  qif.done=True, psu.done=True, tcu.done=True, qxu.done=True, pfu.done=True
  qid.done=False, pdu.done=False, piu.done=False, lmu.done=False
  → 一部のユニットが完了しない
```

### シミュレーション終了条件 (xq_simulator.py:376-384)
```python
done_cond = self.qif.done
done_cond = done_cond and self.qid.done
done_cond = done_cond and (self.pdu.state == "empty")
done_cond = done_cond and (self.piu.state == "ready")
done_cond = done_cond and (self.psu.state == "ready" and not self.psu.pchinfo_srmem.output_notempty)
done_cond = done_cond and self.tcu.output_timebuf_empty
done_cond = done_cond and not (bool(self.qxu.dq_meas_mem) or bool(self.qxu.aq_meas_mem))
done_cond = done_cond and (self.pfu.state == "ready")
done_cond = done_cond and self.lmu.done
```

### スタールの連鎖
```
PSU.pchinfo_full=True（バッファフル）
    ↓
physched_pchwr_stall = True
    ↓
PIU.input_stall = True
    ↓
PDU.input_stall = True
    ↓
QID.to_pchdec_buf が空にならない
    ↓
qid.done = False, pdu.state != empty, piu.state != ready
```

---

## 4. 修正済みの内容

### patch_trace_backend.py

1. **QIFパッチ条件の修正** (301-312行目)
   - 元のXQsimと同じ条件に修正
   - `output_instbuf_empty = False` の時に `done = True`

2. **10Mサイクルチェックをループ内に移動** (443-445行目)
   - 無限ループを実際に防止できるように

3. **デバッグログの追加** (416-442行目)
   - QID, PDU, PIU, PSU の詳細状態を1000サイクルごとに出力

### Dockerfile

1. **プラットフォーム変更**
   - `linux/arm64` → `linux/amd64`（Windows Docker用）

2. **libffi.so.6 依存関係の解決**
   - `libffi7` をインストールしシンボリックリンクを作成

---

## 5. Mac環境での実行手順

### 1) Dockerプラットフォームの変更（Mac Apple Silicon の場合）

`Dockerfile` と `docker-compose.yml` を `linux/arm64` に戻す：

```dockerfile
# Dockerfile 1行目
FROM --platform=linux/arm64 ubuntu:22.04
```

```yaml
# docker-compose.yml
platform: linux/arm64
```

### 2) ビルドと起動

```bash
docker-compose build --no-cache xqsim-backend
docker-compose up -d xqsim-backend
```

### 3) テスト実行

```bash
# APIテスト
docker-compose exec xqsim-backend python /app/test_api.py

# XQsim単体テスト（インターフェースなし）
docker-compose exec xqsim-backend python /app/test_xqsim_standalone.py
```

### 4) ログ確認

```bash
# リアルタイムログ
docker-compose logs -f xqsim-backend

# 最新のサイクル数確認
docker-compose logs xqsim-backend 2>&1 | grep "Cycle:" | tail -5

# デバッグ情報確認
docker-compose logs xqsim-backend 2>&1 | grep -E "=== Cycle|QID:|PDU:|PIU:|PSU:" | tail -30
```

---

## 6. 次のステップ（推奨）

### 優先度高
1. **XQsimの作者/ドキュメントに確認**
   - サンプル回路（pprIIZZZ_n5）が正常終了するのに必要なサイクル数
   - `lmu.done` が `False` のまま終わらない問題の既知の解決策

2. **別の設定を試す**
   - `example_cmos_d5` 以外の設定（`current_300K_CMOS`, `nearfuture_4K_CMOS` など）

### 優先度中
3. **より単純な回路を試す**
   - 1量子ビットのHゲートのみなど

4. **XQsimのREADMEに記載されている実行例を試す**
   - 公式の実行方法で動作確認

---

## 7. 重要なファイルの場所

```
XQsim_library/
├── src/
│   ├── patch_trace_backend.py  # ★ インターフェースロジック
│   ├── api_server.py           # ★ FastAPI サーバー
│   ├── XQ-simulator/           # XQsim本体（変更しない）
│   │   ├── xq_simulator.py
│   │   ├── patch_information_unit.py
│   │   ├── physical_schedule_unit.py
│   │   └── ...
│   └── compiler/               # コンパイラ（変更しない）
├── Dockerfile                  # ★ Docker設定
├── docker-compose.yml          # ★ Docker Compose設定
├── test_api.py                 # ★ APIテスト
├── test_xqsim_standalone.py    # ★ XQsim単体テスト
└── requirements.txt
```

---

## 8. 既知の制限事項

### XQsimの制約
- `num_lq` は奇数または2である必要がある
- 偶数量子ビットのQASMは奇数にパディングして使用

### テスト2（簡単なQASM）の失敗
- 1量子ビットのHゲート+測定は `invalid pchpp in PIU.dyndec` エラーで失敗
- これはXQsim本体の仕様/制限であり、インターフェースの問題ではない

---

## 9. 連絡先 / 参考資料

- XQsim GitHub: （元のリポジトリURL）
- XQsim README: `README.md`

---

**最終更新**: 2024年12月31日


