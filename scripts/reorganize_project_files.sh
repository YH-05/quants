#!/bin/bash
# プロジェクトファイルを project-[番号].md 形式にリネームし、
# 調査レポートを research/ サブディレクトリに移動するスクリプト

set -e

cd "$(dirname "$0")/.."

echo "=== プロジェクトファイルの整理を開始 ==="

# research/ ディレクトリを作成（既に作成済みの場合はスキップ）
if [ ! -d "docs/project/research" ]; then
    echo "Creating docs/project/research/ directory..."
    mkdir -p docs/project/research
fi

# プロジェクトファイルをリネーム
echo ""
echo "=== プロジェクトファイルのリネーム ==="

if [ -f "docs/project/financial-news-rss-collector.md" ]; then
    echo "Renaming financial-news-rss-collector.md → project-14.md"
    git mv docs/project/financial-news-rss-collector.md docs/project/project-14.md
fi

if [ -f "docs/project/note-content-enhancement.md" ]; then
    echo "Renaming note-content-enhancement.md → project-11.md"
    git mv docs/project/note-content-enhancement.md docs/project/project-11.md
fi

if [ -f "docs/project/research-agent.md" ]; then
    echo "Renaming research-agent.md → project-7.md"
    git mv docs/project/research-agent.md docs/project/project-7.md
fi

# 調査レポートを research/ に移動
echo ""
echo "=== 調査レポートの移動 ==="

if [ -f "docs/project/image-collection-requirements.md" ]; then
    echo "Moving image-collection-requirements.md → research/"
    git mv docs/project/image-collection-requirements.md docs/project/research/
fi

if [ -f "docs/project/research-agent-survey.md" ]; then
    echo "Moving research-agent-survey.md → research/"
    git mv docs/project/research-agent-survey.md docs/project/research/
fi

if [ -f "docs/project/rss-package-investigation.md" ]; then
    echo "Moving rss-package-investigation.md → research/"
    git mv docs/project/rss-package-investigation.md docs/project/research/
fi

echo ""
echo "=== 完了 ==="
echo ""
echo "リネーム結果:"
echo "  - docs/project/project-14.md (Finance News Tracker)"
echo "  - docs/project/project-11.md (note金融コンテンツ発信強化)"
echo "  - docs/project/project-7.md (リサーチエージェントの追加)"
echo ""
echo "調査レポート移動先:"
echo "  - docs/project/research/image-collection-requirements.md"
echo "  - docs/project/research/research-agent-survey.md"
echo "  - docs/project/research/rss-package-investigation.md"
echo ""
echo "次のステップ:"
echo "  1. git status で変更を確認"
echo "  2. 各ファイルの GitHub Project 記述を統一フォーマットに更新"
