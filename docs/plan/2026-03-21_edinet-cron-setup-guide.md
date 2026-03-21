# EDINET DB 自動同期セットアップガイド（Mac Mini）

**作成日**: 2026-03-21
**対象マシン**: Mac Mini (yukimac-mini / 100.106.41.61)
**前提**: MacBook での全コード変更がコミット・プッシュ済みであること

## 前提条件（確認済み）

- [x] Mac Mini に quants リポジトリが存在 (`~/Desktop/quants/`)
- [x] uv 0.9.18 インストール済み
- [x] Python 3.12.12 インストール済み
- [ ] NAS マウント
- [ ] EDINET_DB_API_KEY 設定
- [ ] git pull（最新コード反映）
- [ ] 手動テスト実行
- [ ] launchd 登録

---

## 手順

### Step 1: MacBook でコミット&プッシュ

MacBook の Claude Code で `/commit-and-pr` を実行し、全変更をプッシュ。

### Step 2: Mac Mini で NAS をマウント

```bash
# SMB マウント
mkdir -p /Volumes/personal_folder
mount -t smbfs //Yuki@100.70.5.35/personal_folder /Volumes/personal_folder

# 確認
ls /Volumes/personal_folder/Quants/data/sqlite/edinet.db && echo "OK"
```

#### 起動時の自動マウント設定

`System Settings > General > Login Items` に以下のスクリプトを追加、
または `/etc/auto_master` に設定:

```bash
# /etc/auto_smb を作成
echo '/Volumes/personal_folder -fstype=smbfs ://Yuki:PASSWORD@100.70.5.35/personal_folder' | sudo tee /etc/auto_smb

# auto_master に登録
echo '/- auto_smb' | sudo tee -a /etc/auto_master

# automount を再読み込み
sudo automount -vc
```

### Step 3: EDINET_DB_API_KEY を設定

```bash
cd ~/Desktop/quants

# MacBook の .env から EDINET_DB_API_KEY の値を確認してコピー
echo 'EDINET_DB_API_KEY=ここにAPIキーを入力' >> .env

# 確認
grep EDINET .env
```

### Step 4: 最新コードを取得

```bash
cd ~/Desktop/quants
git pull origin main
uv sync --all-extras
```

### Step 5: 手動テスト実行

```bash
cd ~/Desktop/quants

# ステータス確認
uv run python -m market.edinet.scripts.sync --status

# 手動で同期実行（数社分取得して正常動作を確認）
uv run python -m market.edinet.scripts.sync --resume
```

期待する出力:
```
Resume sync completed: X/Y phases successful
  [OK] financials_ratios: N processed
```

### Step 6: launchd plist を作成

```bash
cat > ~/Library/LaunchAgents/com.quants.edinet-sync.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.quants.edinet-sync</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/yuki/.local/bin/uv</string>
        <string>run</string>
        <string>python</string>
        <string>-m</string>
        <string>market.edinet.scripts.sync</string>
        <string>--resume</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/yuki/Desktop/quants</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/Users/yuki/.local/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>3</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/Users/yuki/Desktop/quants/logs/edinet_sync.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/yuki/Desktop/quants/logs/edinet_sync_error.log</string>
</dict>
</plist>
EOF
```

### Step 7: launchd に登録

```bash
# ログディレクトリ作成
mkdir -p ~/Desktop/quants/logs

# 登録
launchctl load ~/Library/LaunchAgents/com.quants.edinet-sync.plist

# 確認
launchctl list | grep edinet

# 即時実行テスト（3時まで待たずに確認）
launchctl start com.quants.edinet-sync

# ログ確認
tail -20 ~/Desktop/quants/logs/edinet_sync.log
```

---

## 運用

### ログ確認
```bash
tail -50 ~/Desktop/quants/logs/edinet_sync.log
tail -50 ~/Desktop/quants/logs/edinet_sync_error.log
```

### 手動実行
```bash
cd ~/Desktop/quants && uv run python -m market.edinet.scripts.sync --resume
```

### ステータス確認
```bash
cd ~/Desktop/quants && uv run python -m market.edinet.scripts.sync --status
```

### 停止
```bash
launchctl unload ~/Library/LaunchAgents/com.quants.edinet-sync.plist
```

---

## 完了までの見込み

| 項目 | 値 |
|------|-----|
| 全社数 | 3,839 |
| 取得済み | 51社 |
| 残り | 3,788社 |
| 1日あたり | 約31社 (95コール/日 ÷ 3コール/社) |
| 完了予定 | 約122日後（2026年7月下旬） |
