# 開発環境の移行手順書（Mac → 新PC）

作成日: 2026-09-05
対象: `YukinoMac-mini` から quants の開発環境を撤退させ、別PCで引き継ぐ

---

## 1. 前提と方針

- **GitHub が履歴の正本**。移行時点でローカルに未push コミット・stash は 0 件だった
- **NAS (`/Volumes/personal_folder`) は引き続き使用する**。実データ 20GB は元から NAS 上にある
- Mac の削除は **新PCでの稼働確認が終わってから**行う（手順は §9）
- Neo4j は quants 専用ではなく **note / research / creator と共有**する 4 DB 構成。
  Mac 側では **quants データベースのみ**を削除し、コンテナと他 3 DB は残す

### 資産の所在マップ

| 資産 | 所在 | Mac 削除時 |
|---|---|---|
| ソースコード・ドキュメント・ノートブック | GitHub `YH-05/quants` | 失われない |
| 実データ 20GB (`DATA_DIR`) | NAS `Projects/quants/data/` | 失われない |
| `.env` / `.mcp.json` / `.claude/settings.json` | NAS `Projects/quants/` (sync-nas で同期) | 失われない |
| Neo4j quants DB | NAS `neo4j-dumps/quants.dump` | dump 済み（§6） |
| `data/cache/market_data.db` (120MB) | **Mac のみ** → NAS へ退避済み | 退避済み |
| `.venv` (2.0GB) | Mac のみ | `uv sync` で再構築 |
| HuggingFace モデルキャッシュ (6.6GB) | Mac のみ | 初回実行時に再ダウンロード |

---

## 2. 移行用バックアップの内容

退避先: `/Volumes/personal_folder/quants-migration-2026-09-05/`

| パス | 内容 | 検証 |
|---|---|---|
| `repo-untracked/market_data.db` | 120MB。yfinance 等の市場データキャッシュ。**NAS に存在しなかった唯一の実データ** | SHA-256 一致 |
| `repo-untracked/data-sqlite/` | `edinet.db` (sqlite3 `.backup` で整合コピー)、`_sync_state.json`、`_rate_limit.json` | `integrity_check: ok` / 全 6 テーブルの行数一致 |
| `repo-untracked/.env`, `.mcp.json`, `.mcp.json.bak` | 秘密情報 | SHA-256 一致 |
| `repo-untracked/2026-05-11_nse-owner-obsolete/` | `trash/` の内容 16MB。中身未検証のため保険として退避 | SHA-256 一致 |
| `orphan-worktree/feature-prj38.tar.gz` | 2.7MB。§8 参照 | — |
| `launchd/*.plist` | 13 ファイル。定期実行ジョブの定義 | SHA-256 一致 |
| `scripts/start-quants-neo4j.sh` | Neo4j 自動起動スクリプト | SHA-256 一致 |
| `neo4j/quants.dump` | 1.6MB。2026-09-05 15:48 取得 | §6 の基準値で検証 |

`edinet.db` を除く 26 ファイルは SHA-256 で元ファイルとの一致を確認済み。

---

## 3. 落とし穴（先に読むこと）

### 3-1. NAS のデータが二重化している

NAS には quants のデータ置き場が **2 つ**あり、同名ファイルが両方に存在する。

| 場所 | 参照元 | 実態 |
|---|---|---|
| `/Volumes/personal_folder/Projects/quants/data/` | `.env` の `DATA_DIR` | **正本**。20GB、日次ジョブが更新中 |
| `/Volumes/personal_folder/data/` | リポジトリ内 `data/` の symlink 8 本 | 旧構成。23MB、2026-04-02 以降ほぼ停止 |

例えば `market/all_performance_20260129-1437.json` は両方に同一内容で存在するため、
どちらを見ているか気づきにくい。**`DATA_DIR` 側が正しい。**

### 3-2. `data/` 配下の symlink 8 本は新PCで壊れる

`data/{duckdb,investment_theme,macroeconomics,market,news,processed,stock,Transcript}` は
`/Volumes/personal_folder/data/...` を指す symlink で、**Git 管理下**にある。
つまり clone した時点で新PCにも同じ symlink が再現される。

- **Mac / Linux**: NAS を同じパスにマウントすれば動くが、§3-1 のとおり参照先は旧データ。
  **`DATA_DIR` 経由に統一することを推奨**（symlink を削除するか、正本側に張り替える）
- **Windows**: symlink は機能しない。git の `core.symlinks` 設定次第でリンクの中身を書いた
  ただのテキストファイルになる。`DATA_DIR` 経由のコードパスのみを使うこと

### 3-3. `.env` の `CACHE_DIR` だけローカル絶対パス

`DATA_DIR` と `FRED_HISTORICAL_CACHE_DIR` は NAS を指すが、`CACHE_DIR` だけ
`/Users/yuki/Desktop/quants/data` というこの Mac 固有のパスになっている。
新PCでは自分のリポジトリパスに書き換えること。

### 3-4. 旧ユーザー名 `yukihata` / 旧プロジェクト名 `finance` の残骸

過去のマシン移行の残骸が以下に残っている（今回は未修正）。

| ファイル | 箇所 | 内容 |
|---|---|---|
| `.claude/settings.json` | 8 | `/Users/yukihata/Desktop/finance/...` の permissions allowlist |
| `.claude/settings.local.json` | 15 | 同上（マシン固有ファイル・NAS 同期対象外） |
| `.claude/sync-config.yaml` | 1 | `local_path: /Users/yukihata/Desktop/Quants` |

権限許可リストの変更にあたるため意図的に触っていない。新PCで整理すること。

---

## 4. 新PC セットアップ手順

実行環境は Docker コンテナに統一している。ホスト OS が Windows / Linux / macOS の
いずれでも、コンテナ内は同じ Debian になり、パスも同じになる
（リポジトリ = `/app`、NAS = `/nas`）。

### 4-1. 前提ソフトウェア

ホスト側に必要なものは 3 つだけ。

| 必須 | 用途 |
|---|---|
| Docker（Desktop または Engine） | 実行環境そのもの |
| Git | clone のみ |
| NAS (SMB) マウント | 宅内 NAS の `personal_folder` 共有。接続情報は NAS 管理画面で確認する |

Python・`uv`・Ruff・pytest・`gh` CLI はすべてコンテナに入っているため、
ホストへのインストールは不要。

| 任意 | 用途 |
|---|---|
| `gh` CLI（ホスト） | ホストから GitHub 操作をしたい場合。コンテナへは認証を共有する |
| `blpapi` | Bloomberg Terminal / B-PIPE を使う場合。**コンテナでは動かない**ため、ホストのネイティブ環境が必要（§4-4） |

### 4-2. 手順

```bash
# 1. clone
git clone https://github.com/YH-05/quants.git
cd quants

# 2. NAS をマウント（パスは OS に合わせる）
#    macOS  : /Volumes/personal_folder
#    Linux  : /mnt/personal_folder
#    Windows: ネットワークドライブに割り当て

# 3. 秘密情報を配置（§5）
cp .env.example .env
#    NAS から取得する場合:
#    cp <NAS>/Projects/quants/.env .env
#    cp <NAS>/Projects/quants/.mcp.json .mcp.json

# 4. .env にホスト固有の 2 変数を設定する（ここだけが OS で異なる）
#    NAS_ROOT=/Volumes/personal_folder     ← 自分の環境のマウント先
#    NEO4J_DATA_ROOT=/Users/<user>/neo4j-data
#    Windows は追加で HOST_HOME と DOCKER_SOCKET も設定する

# 5. イメージをビルド
docker compose build

# 6. Neo4j 起動と復元（§6）
docker compose up -d neo4j

# 7. 開発シェルに入る
docker compose run --rm dev bash

# 8. コンテナ内で GitHub 認証と動作確認（§7）
gh auth login
make check-all
```

### 4-3. Windows での注意

- **リポジトリは WSL2 のファイルシステム側に置くこと。** Windows のドライブ
  （`/mnt/c/...`）に置くとバインドマウント越しのファイル I/O が大幅に遅くなる
- `.env` に `HOST_HOME=C:/Users/<user>` と `DOCKER_SOCKET=//./pipe/docker_engine`
  を設定する
- `.venv` は名前付きボリュームに隔離しているため、この経路の遅さは回避済み

### 4-4. イメージに含めていないもの

| 対象 | 理由 | 対処 |
|---|---|---|
| Bloomberg (`blpapi`) | Terminal / B-PIPE への接続が前提。加えて Linux 版 wheel が x86_64 のみで arm64 ホストではビルドできない | ホストのネイティブ環境で実行する |
| `nlp` extra（`torch` 等） | `torch` が NVIDIA GPU 用の CUDA ライブラリ約 2.4GB を連れてくる。GPU の無い環境では一切使われないのに、マシンごとに 5GB 超のダウンロードと 1〜2 時間のビルドを強いる | 下記参照 |

`nlp` extra には `torch` / `transformers` / `sentence-transformers` / `gliner` /
`accelerate` / `fastopic` / `topmost` が入っている。`src/` はこれらを使っておらず、
利用箇所は `notebook/FILING_NLP/`（10-K/10-Q の FinBERT 感情分析・埋め込み生成）のみ。
`tests/notebook/FILING_NLP/test_embed_indices.py` は `pytest.importorskip("torch")` で
torch 不在時に自動スキップされるため、テストは影響を受けない。

FILING_NLP の解析を動かすときだけ、以下で追加する。

```bash
# コンテナ内
uv sync --extra nlp

# ホストで直接動かす場合
uv sync --all-extras
```

HuggingFace のモデル（`gte-Qwen2-1.5B-instruct`、約 6.6GB）は初回実行時に
`notebook/FILING_NLP/data/hf_cache/` へ自動ダウンロードされる。

---

## 5. 秘密情報の再設定

`.env` は 19 変数。値は以下のいずれかから取得する。

1. NAS `Projects/quants/.env`（sync-nas で同期済み。2026-09-05 15:27 時点）
2. 移行バックアップ `quants-migration-2026-09-05/repo-untracked/.env`

変数の一覧と役割は `.env.example` を参照。

**keyring 方式のため物理コピーできないもの**:

- `gh` CLI 認証 → 新PCで `gh auth login`（scopes: `gist`, `project`, `read:org`, `repo`, `workflow`）
- NotebookLM のブラウザセッション → 新PCで再ログイン
- alphaxiv MCP の OAuth → 初回接続時にブラウザ認証

---

## 6. Neo4j の復元

### 6-1. 復元

```bash
# コンテナ起動
docker compose up -d neo4j

# NAS の dump から quants DB を復元（コンテナ内で実行）
docker compose run --rm dev bash -c 'NEO4J_DBS=quants bash scripts/neo4j_sync.sh load'
```

`scripts/neo4j_sync.sh` の macOS 既定値（`/Volumes/...`、`~/Library/Logs`）は、
compose が `NAS_DUMP_DIR=/nas/neo4j-dumps` と `NEO4J_SYNC_LOG=/app/logs/neo4j-sync.log`
に上書きするため、コンテナ内では OS に依らず同じ場所を見る。
ホストから直接実行する場合のみ、これらを環境変数で指定すること。

### 6-2. 復元の検証（基準値）

Mac 側で dump した時点の quants DB の内容。新PCで一致すれば復元成功。

| 項目 | 値 |
|---|---|
| ノード総数 | 3,809 |
| リレーション総数 | 8,366 |

ラベル別ノード数:

| ラベル | 件数 | | ラベル | 件数 |
|---|---:|---|---|---:|
| Author | 935 | | DataRequirement | 43 |
| Claim | 885 | | Project | 11 |
| Source | 788 | | Insight | 11 |
| Decision | 272 | | Anomaly | 10 |
| ActionItem | 261 | | Fact | 7 |
| Method | 145 | | MarketRegime | 6 |
| Topic | 141 | | | |
| Entity | 108 | | | |
| Discussion | 105 | | | |
| PerformanceEvidence | 81 | | | |

確認コマンド:

```bash
docker exec neo4j-enterprise cypher-shell -u neo4j -p "$NEO4J_PASSWORD" -d quants \
  "MATCH (n) RETURN count(n); MATCH ()-[r]->() RETURN count(r);"
```

### 6-3. 注意: 他 3 DB のダンプは古い

NAS の `note.dump` / `research.dump` / `creator.dump` / `neo4j.dump` は
**2026-06-05 付**で 3 ヶ月古い。これらは note-finance など他プロジェクトの資産であり、
今回の移行では触っていない。他プロジェクトも移行する場合は別途 dump を取り直すこと。

---

## 7. 動作確認チェックリスト

新PCで以下が全て通れば、Mac を削除してよい。

**ホスト側**

- [ ] NAS がマウントされ、`.env` の `NAS_ROOT` がその場所を指している
- [ ] `docker compose config` がエラーなく通る（必須変数が揃っている）
- [ ] `docker compose build` が成功する

**コンテナ内**（`docker compose run --rm dev bash` で入って実行）

- [ ] `ls /nas/Projects/quants/data` で NAS の実データが見える
- [ ] `make check-all` が成功する（format / lint / typecheck / test）
- [ ] `gh auth status` が `YH-05` として認証済みを返す
- [ ] Neo4j に接続でき、quants DB のノード数が 3,809 と一致する（§6-2）
- [ ] `market_data.db` を NAS から復元した（必要な場合）

**定期実行**（launchd を撤去してから）

- [ ] `docker compose --profile scheduler up -d` でスケジューラが起動する
- [ ] `docker compose logs scheduler` に起動前チェックの成功が出ている
- [ ] ホスト起動時に compose が自動で上がる設定を 1 件登録した（§8-1）

---

## 8. 定期実行ジョブ

### 8-1. 新しい方式（コンテナ内スケジューラ）

13 個の launchd ジョブは `docker/crontab` の 1 ファイルに集約した。
スケジューラ（supercronic）はコンテナ内で動くため、**ホスト側に必要な設定は
「起動時に compose を上げる」だけ**になり、OS ごとのジョブ定義が不要になった。

```bash
# 定期実行を開始
docker compose --profile scheduler up -d

# ログを見る
docker compose logs -f scheduler

# 停止
docker compose --profile scheduler down
```

`scheduler` は **profile を指定しない限り起動しない**。macOS の launchd ジョブが
まだ残っている状態で起動すると同じジョブが二重に走るための安全装置。
launchd 側を撤去してから有効化すること。

ホスト起動時に自動で立ち上げたい場合は、OS ごとに以下を 1 つだけ登録する。

| OS | 方法 |
|---|---|
| macOS | launchd に `docker compose --profile scheduler up -d` を 1 件登録 |
| Linux | systemd unit（`Restart=on-failure`）を 1 件登録 |
| Windows | タスクスケジューラに「ログオン時」トリガーで 1 件登録 |

旧方式では 13 ジョブ × 3 OS = 39 個の定義が必要だったが、この方式では 3 個で済む。

`docker/scheduler-entrypoint.sh` が起動前に NAS の実データを確認し、
未マウント（空ディレクトリ）なら起動を中止する。Docker はバインド元が
存在しないと空ディレクトリを作ってしまい、「NAS があるように見えて中身が空」
という状態でジョブが走り続けるのを防ぐため。

### 8-2. 旧方式（macOS launchd・撤去対象）

Mac の `~/Library/LaunchAgents/` に登録されている 13 個。plist は移行バックアップの
`launchd/` に退避済み。うち `com.quants.edinet-sync` と `com.quants.neo4j` の 2 つは
リポジトリに定義が無く、この Mac にしか存在しなかった（`docker/crontab` に
取り込んだことで初めて版管理下に入った）。

| ジョブ | スケジュール | 実行内容 |
|---|---|---|
| `com.quants.neo4j` | ログイン時 (RunAtLoad) | `start-quants-neo4j.sh` で Neo4j コンテナ起動 |
| `com.quants.pipeline-nasdaq` | 毎日 1:00 | `market.pipeline --phase 1 --days-back 7` |
| `com.quants.pipeline-alphavantage` | 毎日 2:00 | `market.pipeline --phase 2 --av-budget 25` |
| `com.quants.pipeline-sec-edgar` | 毎日 2:00 | `market.pipeline --phase 3` |
| `com.quants.pipeline-yfinance` | 毎日 2:00 | `market.pipeline --phase 4` |
| `com.quants.etfcom-daily` | 毎日 3:00 | `market.etfcom --frequency daily` |
| `com.quants.neo4j-push` | 毎日 4:00 | `neo4j_sync.sh push`（NAS へ dump） |
| `com.quants.etfcom-weekly` | 日曜 4:00 | `market.etfcom --frequency weekly` |
| `com.quants.etfcom-monthly` | 毎月 1 日 5:00 | `market.etfcom --frequency monthly` |
| `com.quants.fred-sync` | 毎日 6:00 | `market.fred.scripts.sync_historical --auto` |
| `com.quants.edinet-sync` | 毎日 8:00 | `market.edinet.scripts.sync --daily` |
| `com.quants.polymarket-collect` | 0:30 / 6:30 / 12:30 / 18:30 | `market.polymarket` |
| `com.quants.neo4j-push-changed` | 1 時間ごと | `neo4j_sync.sh push --if-changed` |

全ジョブが `/Users/yuki/.local/bin/uv` と `/Users/yuki/Desktop/quants/.env` を
**絶対パスで参照**している。移植時は全て書き換えること。

---

## 9. Mac からの撤退手順

**新PCで §7 のチェックリストが全て通ってから実行すること。**

`scripts/decommission-mac.sh` を使う。既定は dry-run で、何も削除しない。

```bash
# 1. 何が削除されるかを確認（既定・安全）
bash scripts/decommission-mac.sh

# 2. 実際に削除
bash scripts/decommission-mac.sh --execute
```

このスクリプトが行うこと:

1. NAS の移行バックアップが揃っているかを検証（欠けていれば中断）
2. `com.quants.*` の launchd ジョブ 13 個を unload して plist を削除
3. Neo4j の **quants データベースのみ** drop（コンテナと他 3 DB は残す）
4. `~/.local/bin/start-quants-neo4j.sh` を削除
5. リポジトリ `~/Desktop/quants` を削除
6. 孤立 worktree `~/Desktop/.worktrees/Quants` を削除

**このスクリプトが触らないもの**:

- `~/neo4j-data/`（4 DB 共有のため。note-finance が毎日 3:00 に書き込んでいる）
- `com.note-finance.*` の launchd ジョブ 16 個
- `~/Desktop/Quants_data/`（27GB の FNSPID データセット。判断保留）
- NAS 上の一切のデータ

---

## 10. 未決事項

| 項目 | 状況 |
|---|---|
| 移行先 PC の OS | **3 OS どれでも可**。実行環境をコンテナに統一したため、選定を先送りできる |
| `~/Desktop/Quants_data/` 27GB | 判断保留。FNSPID 公開データセットで再取得可能 |
| `data/` の 20GB を NAS 参照のままにするか、新PCにローカルコピーするか | 未定 |
| 13 個の定期ジョブを全て有効化するか、一部に絞るか | 未定（`docker/crontab` の行をコメントアウトすれば絞れる） |
| 旧ユーザー名 `yukihata` パスの整理（§3-4） | `.claude/settings.json` 等は未実施。`scripts/collect_finance_news_*.py` は修正済み |
| `data/` の symlink 8 本の扱い | 未整理。`DATA_DIR` 経由に統一するなら削除できる（§3-2） |
| 孤立 Docker ボリューム `quants_neo4j-data`（516MB） | 2026-03-28 の初期セットアップの残骸。現行 5 DB は含まれず、514MB はトランザクションログ。撤去スクリプトが削除対象に含む |
| Slack MCP / Reddit MCP の接続エラー | 移行前から発生。原因未調査 |
