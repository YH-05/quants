# syntax=docker/dockerfile:1
# quants - フル Docker 開発・実行環境
# Python 3.12 + Claude Code + GitHub CLI + uv + supercronic
#
# 開発シェルと定期実行スケジューラの両方がこのイメージを使う。
# ホスト OS（macOS / Linux / Windows）に関わらず中身は同じ Debian になる。

FROM python:3.12-slim

# ===== システムパッケージ =====
# tzdata: 定期実行を JST など任意のタイムゾーンで動かすために必要
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    wget \
    build-essential \
    ca-certificates \
    gnupg \
    openssh-client \
    make \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# ===== GitHub CLI =====
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
      | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
    && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
      | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && apt-get update \
    && apt-get install -y gh \
    && rm -rf /var/lib/apt/lists/*

# ===== Docker CLI（クライアントのみ）=====
# scheduler が Neo4j コンテナへ `docker exec` してダンプを取るために必要。
# デーモンは同梱せず、ホストの Docker API をソケット経由で使う
RUN install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc \
    && chmod a+r /etc/apt/keyrings/docker.asc \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
      > /etc/apt/sources.list.d/docker.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends docker-ce-cli \
    && rm -rf /var/lib/apt/lists/*

# ===== supercronic（コンテナ内 cron）=====
# 通常の cron と違い PID 1 で動かせて、ログを標準出力に流す。
# これによりホスト側は launchd / systemd / タスクスケジューラのいずれも不要になる
ARG SUPERCRONIC_VERSION=v0.2.33
RUN ARCH="$(dpkg --print-architecture)" \
    && curl -fsSL -o /usr/local/bin/supercronic \
      "https://github.com/aptible/supercronic/releases/download/${SUPERCRONIC_VERSION}/supercronic-linux-${ARCH}" \
    && chmod +x /usr/local/bin/supercronic \
    && supercronic -version

# ===== Node.js 20.x（Claude Code に必要）=====
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# ===== Claude Code =====
RUN npm install -g @anthropic-ai/claude-code

# ===== uv（Python パッケージマネージャ）=====
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# ===== 作業ディレクトリ =====
WORKDIR /app

# ===== Python 依存関係のインストール =====
# 2 つの extra を除外する。
#
# bloomberg (blpapi):
#   1. Linux 版 wheel が x86_64 のみで、arm64 ホスト（Apple Silicon 等）では
#      sdist ビルドにフォールバックして失敗する
#   2. Bloomberg Terminal / B-PIPE への接続が前提で、コンテナ内からは実行できない
#   → Bloomberg を使う作業はホスト側のネイティブ環境で行うこと
#
# nlp (torch / transformers / sentence-transformers 等):
#   torch は NVIDIA GPU 用の CUDA ライブラリ約 2.4GB を連れてくる（nvidia-cublas
#   518MB、nvidia-cudnn 424MB 等）。GPU の無い環境では一切使われないのに、
#   マシンごとに 5GB 超のダウンロードと 1〜2 時間のビルドを強いる。
#   src/ は torch を使っておらず、利用箇所は notebook/FILING_NLP のみ。
#   → コンテナで FILING_NLP を動かす場合は uv sync --extra nlp を実行すること
# README.md も必要。pyproject.toml が readme = "README.md" を宣言しており、
# 自プロジェクトを editable install する際に hatchling が実ファイルを要求するため。
# これが無いと uv sync が OSError: Readme file does not exist で失敗する
COPY pyproject.toml uv.lock README.md ./
COPY src/utils_core ./src/utils_core/
# BuildKit のキャッシュマウントで uv のダウンロードキャッシュを永続化する。
# 依存は torch など合計 5GB 超あり、ビルドが中断した場合に最初から
# やり直しになるのを防ぐ。キャッシュはイメージには含まれない。
#
# UV_CONCURRENT_DOWNLOADS: 既定では 50 並列でダウンロードしてメモリを
# 圧迫し、メモリの少ないホストではビルドが OOM で落ちる。
RUN --mount=type=cache,target=/root/.cache/uv \
    UV_CONCURRENT_DOWNLOADS=8 UV_HTTP_TIMEOUT=120 \
    uv sync --frozen --all-extras --no-extra bloomberg --no-extra nlp

# ===== ソースコードコピー =====
COPY . .

# ===== 環境変数 =====
ENV PYTHONPATH="/app/src"
ENV LOG_LEVEL="INFO"
ENV PROJECT_ENV="development"
ENV TERM="xterm-256color"

# ===== デフォルトコマンド =====
CMD ["bash"]
