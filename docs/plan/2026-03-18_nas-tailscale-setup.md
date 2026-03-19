# UGREEN NAS Tailscale セットアップ手順

**目的**: 外部ネットワークから自宅NASに直接アクセスし、PythonスクリプトからNASにデータ書き込みできるようにする

**ステータス**: ✅ Phase 2〜5 + 自動マウント 完了（2026-03-19 実施）

**前提条件**:
- UGREEN NAS（UGOS、Docker非対応）
- NAS管理画面ポート: HTTPS 9443
- Tailscale アカウント: このPCで使用中のもの（YH-05@）
- 自宅LANに接続した状態で作業する

## 実施結果サマリー

| Phase | 内容 | ステータス | 備考 |
|-------|------|-----------|------|
| Phase 1 | Mac mini SSH鍵登録 | ⏭️ スキップ | Mac mini オフライン、後日対応可 |
| Phase 2 | NAS情報収集 | ✅ 完了 | 2026-03-19 |
| Phase 3 | Tailscaleインストール・認証 | ✅ 完了 | 2026-03-19 |
| Phase 4 | 自動起動設定 (cron @reboot) | ✅ 完了 | 2026-03-19 |
| Phase 5 | SMBマウント・Python書き込みテスト | ✅ 完了 | 2026-03-19 |
| Phase 6 | SMB自動マウント (launchd + Keychain) | ✅ 完了 | 2026-03-19 |

## 確定した接続情報

| 項目 | 値 |
|------|-----|
| NASホスト名 | DH2300-48C1 |
| NAS ローカルIP | 192.168.11.14 |
| NAS Tailscale IP | 100.70.5.35 |
| NAS OS | Debian 12 (bookworm) / UGOS 1.13.1 |
| NAS アーキテクチャ | aarch64 (arm64) |
| Tailscale バージョン | v1.80.3 |
| Tailscale バイナリ | /usr/local/bin/tailscale, /usr/local/bin/tailscaled |
| 自動起動 | root cron @reboot |
| SSH ユーザー | Yuki (port 22) |
| SMB 共有名 | personal_folder |
| SMB マウントポイント | /Volumes/personal_folder |
| Quants データパス | /Volumes/personal_folder/Quants |
| データディスク | /volume1 (5.4TB, 5.4TB空き) |

---

## Phase 1: Mac mini SSH鍵登録（2分） ⏭️ スキップ

Mac mini のターミナルを開いて実行：

```bash
mkdir -p ~/.ssh
echo 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFpd0UmpEWRJpyVmtJsVEYDnV+zZPu0BkJIj8rSUK+5p youxitiankaggle@gmail.com' >> ~/.ssh/authorized_keys
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
```

**確認**: このPC（外部Wi-Fi接続時）から実行して接続できるか確認：
```bash
ssh yuki@100.106.41.61 "echo OK"
```

---

## Phase 2: NAS情報の収集（3分）

### 2-1. NASのSSHを有効化

1. ブラウザで NAS管理画面を開く（`https://<NAS_IP>:9443`）
2. **設定 > サービス > SSH** を有効化
3. SSHポート番号をメモ（デフォルト: 22）

### 2-2. NASの情報 ✅

| 項目 | 値 |
|------|-----|
| NASのローカルIP | 192.168.11.14 |
| SSHポート | 22 |
| SSHユーザー名 | Yuki |
| NASホスト名 | DH2300-48C1 |

### 2-3. NASにSSHで接続してアーキテクチャ確認

```bash
ssh <ユーザー名>@<NAS_IP> -p <SSHポート>
```

ログイン後に実行：
```bash
uname -m       # aarch64 or x86_64
uname -a       # OS情報
cat /etc/os-release 2>/dev/null  # ディストリビューション
which curl wget 2>/dev/null       # ダウンロードツール
ls /usr/local/ 2>/dev/null        # 書き込み可能なパス
df -h          # ストレージ空き容量
```

→ **結果をメモしておく**（Phase 3 で必要）

---

## Phase 3: NASにTailscaleインストール（10分）

### 3-1. Tailscale スタティックバイナリのダウンロード

NASのアーキテクチャに応じたURLを使用：

| アーキテクチャ (uname -m) | 値 |
|-----------|------|
| `aarch64` | `arm64` |
| `x86_64` | `amd64` |

NASのSSHセッションで実行：

```bash
# アーキテクチャに応じて ARCH を設定
ARCH="arm64"  # or "amd64"

# 最新バージョンのスタティックバイナリをダウンロード
TSVERSION="1.80.3"  # https://pkgs.tailscale.com/stable/ で最新版を確認
cd /tmp
wget "https://pkgs.tailscale.com/stable/tailscale_${TSVERSION}_${ARCH}.tgz" -O tailscale.tgz

# wgetがない場合はcurlで
# curl -Lo tailscale.tgz "https://pkgs.tailscale.com/stable/tailscale_${TSVERSION}_${ARCH}.tgz"
```

### 3-2. 展開・配置

```bash
tar xzf tailscale.tgz
cd tailscale_${TSVERSION}_${ARCH}

# バイナリを配置（書き込み可能な場所）
cp tailscale tailscaled /usr/local/bin/ 2>/dev/null || \
cp tailscale tailscaled /opt/ 2>/dev/null || \
mkdir -p ~/bin && cp tailscale tailscaled ~/bin/

# 配置先を確認
which tailscale tailscaled 2>/dev/null || ls ~/bin/tailscale*
```

### 3-3. Tailscale デーモン起動

```bash
# state ディレクトリ作成
mkdir -p /var/lib/tailscale

# tailscaled をバックグラウンドで起動
# /usr/local/bin に配置した場合：
nohup tailscaled --state=/var/lib/tailscale/tailscaled.state &

# ~/bin に配置した場合：
# nohup ~/bin/tailscaled --state=/var/lib/tailscale/tailscaled.state &
```

### 3-4. Tailscale 認証

```bash
tailscale up
```

→ **認証URLが表示される** → ブラウザで開いてログイン

### 3-5. 接続確認

```bash
tailscale status
tailscale ip -4   # NASのTailscale IPをメモ
```

---

## Phase 4: 自動起動設定（5分）

NAS再起動時にTailscaleが自動起動するよう設定。

### 方法A: cron @reboot

```bash
crontab -e
```

以下を追加：
```
@reboot /usr/local/bin/tailscaled --state=/var/lib/tailscale/tailscaled.state &
```

### 方法B: init.d スクリプト（UGOSが対応している場合）

```bash
cat > /etc/init.d/tailscale << 'INITEOF'
#!/bin/sh
case "$1" in
  start)
    /usr/local/bin/tailscaled --state=/var/lib/tailscale/tailscaled.state &
    sleep 2
    /usr/local/bin/tailscale up
    ;;
  stop)
    killall tailscaled
    ;;
esac
INITEOF
chmod +x /etc/init.d/tailscale
```

**注意**: UGOSのファームウェア更新時にカスタムバイナリが消える可能性がある。更新後は再インストールが必要かもしれない。

---

## Phase 5: このPCからNASに接続（3分）

### 5-1. SMBマウント

```bash
# NASのTailscale IPを使用（Phase 3-5 でメモした値）
NAS_TAILSCALE_IP="100.x.x.x"

# Finderからマウント
open "smb://${NAS_TAILSCALE_IP}"

# またはコマンドラインでマウント
mkdir -p /Volumes/nas
mount_smbfs "//ユーザー名:パスワード@${NAS_TAILSCALE_IP}/共有フォルダ名" /Volumes/nas
```

### 5-2. Pythonからの接続テスト

```python
from pathlib import Path

nas_path = Path("/Volumes/nas/data")
test_file = nas_path / "test.txt"
test_file.write_text("Hello from Python!")
print(f"Written: {test_file}")
print(f"Read back: {test_file.read_text()}")
```

---

## トラブルシューティング

### tailscaled が起動しない
```bash
# TUN デバイスの確認
ls -la /dev/net/tun 2>/dev/null
# なければ作成
mkdir -p /dev/net
mknod /dev/net/tun c 10 200
chmod 600 /dev/net/tun
```

### tailscale up で認証できない
```bash
# ログ確認
tailscale status
journalctl -u tailscaled 2>/dev/null || cat /var/log/syslog | grep tailscale
```

### userspace networking モード（TUNが使えない場合）
```bash
tailscaled --tun=userspace-networking --state=/var/lib/tailscale/tailscaled.state &
# この場合、SOCKS5プロキシ経由でアクセスする
tailscale up --socks5-server=localhost:1055
```

### SMBマウントできない
```bash
# NASのSMBサービスが有効か確認
nc -z <NAS_TAILSCALE_IP> 445 && echo "SMB OK" || echo "SMB NG"

# NFS を試す
showmount -e <NAS_TAILSCALE_IP>
```

---

## 完了後の構成図

```
[このPC (yuki)]           [UGREEN NAS (dh2300-48c1)]
  100.121.150.67    ──Tailscale──    100.70.5.35
  (macOS)                            (Debian 12 / UGOS 1.13.1 / aarch64)
                                     LAN: 192.168.11.14
                                     SMB共有: personal_folder
                                     マウント: /Volumes/personal_folder
                                     データ: /volume1 (5.4TB)

Python → Path("/Volumes/personal_folder/Quants/output.csv") → NASに直接書き込み
```

## Phase 6: SMB自動マウント ✅ 完了（2026-03-19 追加実施）

Mac再起動・スリープ復帰・Wi-Fi切替時のSMB切断に対応するため、自動マウントを設定。

### 構成

| ファイル | 役割 |
|---------|------|
| `~/bin/mount-nas.sh` | マウントスクリプト（Tailscale到達確認→osascript SMBマウント） |
| `~/Library/LaunchAgents/com.quants.nas-mount.plist` | launchdエージェント（ログイン時+5分間隔） |
| macOS Keychain | SMB認証情報（Yuki@100.70.5.35） |
| `~/Library/Logs/nas-mount.log` | 動作ログ |

### 動作フロー

```
5分間隔 or ログイン時
  → マウント済み？ → Yes → 何もしない
  → Tailscale起動確認 → NG → スキップ
  → NAS SMBポート到達確認 → NG → スキップ
  → osascript "mount volume smb://Yuki@100.70.5.35/personal_folder"
  → マウント成功ログ記録
```

### 管理コマンド

```bash
# 手動マウント
~/bin/mount-nas.sh

# launchd 状態確認
launchctl list | grep quants

# ログ確認
cat ~/Library/Logs/nas-mount.log

# 一時停止
launchctl unload ~/Library/LaunchAgents/com.quants.nas-mount.plist

# 再開
launchctl load ~/Library/LaunchAgents/com.quants.nas-mount.plist
```

---

## 残タスク

| ID | 内容 | 優先度 | ステータス |
|----|------|--------|-----------|
| act-2026-03-19-001 | Mac mini SSH鍵登録（Phase 1） | low | pending |
| act-2026-03-19-002 | NAS再起動後のTailscale自動起動動作確認 | medium | **completed** (2026-03-19) |
| act-2026-03-19-003 | UGOSファームウェア更新後のTailscaleバイナリ永続化確認 | medium | **completed** (2026-03-19) |

## 検証結果（2026-03-19 追記）

### act-2026-03-19-002: 再起動後の自動起動 ✅

- `sudo reboot` 実行後、**60秒以内**にTailscale復帰確認（ping pong in 5ms）
- SSH/SMB共に正常動作
- crontab `@reboot` エントリ（重複修正済み: 2行→1行）

### act-2026-03-19-003: FW更新対策 ✅

UGOSは**overlay FS**構成:
- rootfs: squashfs (ro) → FW更新で上書きされる
- overlay upper: `/overlay/upper/` (rw) → `/usr/local/bin/` はここに配置
- data volume: `/volume1/` → FW更新で**消えない**

**対策済み**:
- バイナリバックアップ: `/volume1/tailscale-backup/{tailscale,tailscaled}`
- 復元スクリプト: `/volume1/tailscale-backup/restore.sh`
- FW更新後に `/usr/local/bin/` が消えた場合: `sudo sh /volume1/tailscale-backup/restore.sh` で復元
