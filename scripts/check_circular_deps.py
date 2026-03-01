#!/usr/bin/env python3
"""パッケージ間の循環依存を検出するスクリプト.

4層アーキテクチャに基づき、パッケージ間のインポート依存関係を分析して
循環依存や層違反を検出します。

Usage
-----
python scripts/check_circular_deps.py [--graph] [--mermaid] [--json]

Options
-------
--graph
    依存関係グラフをテキスト形式で表示
--mermaid
    Mermaid形式の依存関係図を出力
--json
    結果をJSON形式で出力

Notes
-----
このスクリプトは以下のチェックを実行します:
- パッケージ間の循環依存の検出
- 4層アーキテクチャの層違反検出
- 依存関係グラフの生成

Exit codes:
- 0: 循環依存なし
- 1: 循環依存を検出
"""

from __future__ import annotations

import ast
import json as json_module
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

# ANSI colors
RED = "\033[91m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"

# 対象パッケージ
PACKAGES = ["database", "market", "analyze", "factor", "strategy", "rss"]

# 4層アーキテクチャの層定義（数字が大きいほど上位）
LAYER_MAP = {
    "database": 0,  # Base Infrastructure
    "rss": 0,  # Base Infrastructure
    "market": 1,  # Layer 1: Data Acquisition
    "analyze": 2,  # Layer 2: Analysis
    "factor": 3,  # Layer 3: Factor
    "strategy": 4,  # Layer 4: Strategy
}


def get_src_dir() -> Path:
    """ソースディレクトリのパスを取得.

    Returns
    -------
    Path
        ソースディレクトリのパス
    """
    return Path(__file__).parent.parent / "src"


def get_imports_from_file(filepath: Path) -> Iterator[str]:
    """ファイルからインポート文を抽出し、パッケージ名を返す.

    Parameters
    ----------
    filepath : Path
        解析対象のPythonファイルパス

    Yields
    ------
    str
        インポートされているパッケージ名
    """
    try:
        with open(filepath, encoding="utf-8") as f:
            content = f.read()
        tree = ast.parse(content)
    except (SyntaxError, UnicodeDecodeError):
        return

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name.split(".")[0]
        elif isinstance(node, ast.ImportFrom) and node.module:
            yield node.module.split(".")[0]


def build_dependency_graph() -> dict[str, set[str]]:
    """パッケージ間の依存関係グラフを構築.

    Returns
    -------
    dict[str, set[str]]
        パッケージ名をキー、依存先パッケージ名のセットを値とする辞書
    """
    src_dir = get_src_dir()
    graph: dict[str, set[str]] = {pkg: set() for pkg in PACKAGES}

    for pkg in PACKAGES:
        pkg_dir = src_dir / pkg
        if not pkg_dir.exists():
            continue

        for py_file in pkg_dir.rglob("*.py"):
            for imported in get_imports_from_file(py_file):
                # 自パッケージへの依存は除外、対象パッケージのみ記録
                if imported in PACKAGES and imported != pkg:
                    graph[pkg].add(imported)

    return graph


def find_cycles(graph: dict[str, set[str]]) -> list[list[str]]:
    """深さ優先探索で循環を検出.

    Parameters
    ----------
    graph : dict[str, set[str]]
        依存関係グラフ

    Returns
    -------
    list[list[str]]
        検出された循環のリスト（各循環はパッケージ名のリスト）
    """
    cycles: list[list[str]] = []
    visited: set[str] = set()
    reported_cycles: set[frozenset[str]] = set()

    def dfs(node: str, rec_stack: set[str], path: list[str]) -> None:
        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                dfs(neighbor, rec_stack, path)
            elif neighbor in rec_stack:
                # 循環を検出
                cycle_start = path.index(neighbor)
                cycle = [*path[cycle_start:], neighbor]
                cycle_set = frozenset(cycle)
                if cycle_set not in reported_cycles:
                    cycles.append(cycle)
                    reported_cycles.add(cycle_set)

        path.pop()
        rec_stack.remove(node)

    for node in graph:
        if node not in visited:
            dfs(node, set(), [])

    return cycles


def check_layer_violations(graph: dict[str, set[str]]) -> list[str]:
    """4層アーキテクチャの依存関係違反を検出.

    Parameters
    ----------
    graph : dict[str, set[str]]
        依存関係グラフ

    Returns
    -------
    list[str]
        検出された層違反のメッセージリスト
    """
    violations = []
    for pkg, deps in graph.items():
        pkg_layer = LAYER_MAP[pkg]
        for dep in deps:
            dep_layer = LAYER_MAP[dep]
            # 下位層が上位層に依存している場合は違反
            if pkg_layer < dep_layer:
                violations.append(
                    f"Layer violation: {pkg} (L{pkg_layer}) -> {dep} (L{dep_layer})"
                )
            # 同一層間の依存も確認（database/rss間は許容）
            elif pkg_layer == dep_layer and pkg_layer != 0:
                violations.append(
                    f"Same-layer dependency: {pkg} -> {dep} (both at L{pkg_layer})"
                )

    return violations


def print_dependency_graph(graph: dict[str, set[str]]) -> None:
    """依存関係グラフを表示.

    Parameters
    ----------
    graph : dict[str, set[str]]
        依存関係グラフ
    """
    print(f"\n{CYAN}{BOLD}=== パッケージ間依存関係 ==={RESET}\n")
    for pkg in ["strategy", "factor", "analyze", "market", "rss", "database"]:
        deps = sorted(graph.get(pkg, []))
        layer = LAYER_MAP[pkg]
        if deps:
            print(f"  [L{layer}] {pkg} -> {', '.join(deps)}")
        else:
            print(f"  [L{layer}] {pkg} -> (依存なし)")


def generate_mermaid_graph(graph: dict[str, set[str]]) -> str:
    """Mermaid形式の依存関係グラフを生成.

    Parameters
    ----------
    graph : dict[str, set[str]]
        依存関係グラフ

    Returns
    -------
    str
        Mermaid形式のグラフ文字列
    """
    lines = ["```mermaid", "graph TD"]

    # 層ごとにサブグラフを作成
    layer_names = {
        0: "Base Infrastructure",
        1: "Layer 1: Market",
        2: "Layer 2: Analyze",
        3: "Layer 3: Factor",
        4: "Layer 4: Strategy",
    }

    for layer in [4, 3, 2, 1, 0]:
        pkgs = [p for p in PACKAGES if LAYER_MAP[p] == layer]
        if pkgs:
            lines.append(f'    subgraph "{layer_names[layer]}"')
            for pkg in pkgs:
                lines.append(f"        {pkg}[{pkg}]")
            lines.append("    end")

    # エッジ定義
    for pkg, deps in graph.items():
        for dep in sorted(deps):
            lines.append(f"    {pkg} --> {dep}")

    lines.append("```")
    return "\n".join(lines)


def main() -> int:
    """メイン処理.

    Returns
    -------
    int
        終了コード（0: 成功、1: 循環依存を検出）
    """
    show_graph = "--graph" in sys.argv
    show_mermaid = "--mermaid" in sys.argv
    output_json = "--json" in sys.argv

    print(f"{BOLD}🔍 パッケージ間循環依存チェック{RESET}\n")

    # 依存関係グラフを構築
    graph = build_dependency_graph()

    if show_graph:
        print_dependency_graph(graph)

    # 循環依存の検出
    cycles = find_cycles(graph)

    # 層違反チェック
    violations = check_layer_violations(graph)

    if output_json:
        result = {
            "packages": PACKAGES,
            "dependencies": {k: list(v) for k, v in graph.items()},
            "cycles": cycles,
            "layer_violations": violations,
            "success": len(cycles) == 0,
        }
        print(json_module.dumps(result, ensure_ascii=False, indent=2))
        return 0 if len(cycles) == 0 else 1

    # 循環依存の結果表示
    print(f"{CYAN}{BOLD}=== 循環依存チェック ==={RESET}\n")
    if cycles:
        print(f"{RED}❌ 循環依存を検出:{RESET}")
        for cycle in cycles:
            print(f"   {' -> '.join(cycle)}")
    else:
        print(f"{GREEN}✓ 循環依存なし{RESET}")

    # 層違反の結果表示
    print(f"\n{CYAN}{BOLD}=== 4層アーキテクチャ整合性チェック ==={RESET}\n")
    if violations:
        print(f"{YELLOW}⚠ 層違反を検出:{RESET}")
        for v in violations:
            print(f"   {v}")
    else:
        print(f"{GREEN}✓ 4層アーキテクチャに準拠{RESET}")

    # Mermaid グラフ出力
    if show_mermaid:
        print(f"\n{CYAN}{BOLD}=== Mermaid 依存関係図 ==={RESET}\n")
        print(generate_mermaid_graph(graph))

    # サマリー
    print(f"\n{BOLD}=== サマリー ==={RESET}")
    print(f"  パッケージ数: {len(PACKAGES)}")
    print(f"  循環依存: {len(cycles)} 件")
    print(f"  層違反: {len(violations)} 件")

    # 終了コード
    if cycles:
        print(f"\n{RED}{BOLD}❌ 循環依存があります。解消してください。{RESET}")
        return 1

    print(f"\n{GREEN}{BOLD}✓ チェック完了{RESET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
