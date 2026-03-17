#!/usr/bin/env python3
"""Neo4j スキーマ検証スクリプト。

knowledge-graph-schema.yaml の namespaces セクションと Neo4j DB 上の
実際のラベルを照合し、逸脱を検出・レポートする。

Usage
-----
::

    # 検証のみ（デフォルト）
    python scripts/validate_neo4j_schema.py

    # JSON レポート出力
    python scripts/validate_neo4j_schema.py --output data/processed/schema_validation.json

    # 接続先を指定
    python scripts/validate_neo4j_schema.py --neo4j-uri bolt://localhost:7690
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml

try:
    from neo4j import Driver, GraphDatabase
except ImportError:
    print("neo4j driver not installed. Run: uv add neo4j")
    sys.exit(1)

try:
    from utils_core.logging import get_logger

    logger = get_logger(__name__)
except ImportError:
    import logging

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    logger = logging.getLogger(__name__)

ALLOWED_URI_SCHEMES = {"bolt", "bolt+s", "bolt+ssc", "neo4j", "neo4j+s", "neo4j+ssc"}


# ---------------------------------------------------------------------------
# Schema loading
# ---------------------------------------------------------------------------


def load_namespaces(schema_path: Path) -> dict[str, Any]:
    """knowledge-graph-schema.yaml から namespaces セクションを読み込む。

    Parameters
    ----------
    schema_path : Path
        YAML スキーマファイルのパス。

    Returns
    -------
    dict[str, Any]
        名前空間定義。

    Raises
    ------
    ValueError
        namespaces セクションが存在しない場合。
    """
    with open(schema_path, encoding="utf-8") as f:
        schema = yaml.safe_load(f)

    namespaces = schema.get("namespaces")
    if namespaces is None:
        msg = f"namespaces section not found in schema: {schema_path}"
        raise ValueError(msg)

    return namespaces


def build_allowed_labels(namespaces: dict[str, Any]) -> dict[str, str]:
    """名前空間定義から許可ラベル → 名前空間のマッピングを構築する。

    Parameters
    ----------
    namespaces : dict[str, Any]
        YAML の namespaces セクション。

    Returns
    -------
    dict[str, str]
        ラベル名 → 名前空間名のマッピング。
    """
    label_to_ns: dict[str, str] = {}

    for ns_name, ns_def in namespaces.items():
        if "labels" in ns_def:
            for label in ns_def["labels"]:
                label_to_ns[label] = ns_name
        if "root_label" in ns_def:
            label_to_ns[ns_def["root_label"]] = ns_name
        if "sub_labels" in ns_def:
            for label in ns_def["sub_labels"]:
                label_to_ns[label] = ns_name

    return label_to_ns


# ---------------------------------------------------------------------------
# Validation checks
# ---------------------------------------------------------------------------


def check_pascal_case_violations(db_labels: list[str]) -> list[dict[str, str]]:
    """小文字で始まるラベル（PascalCase 違反）を検出する。

    Parameters
    ----------
    db_labels : list[str]
        DB 上の全ラベル。

    Returns
    -------
    list[dict[str, str]]
        違反ラベルのリスト。
    """
    return [
        {"label": label, "issue": "starts with lowercase"}
        for label in db_labels
        if label and label[0].islower()
    ]


def check_cross_contamination(
    session: Any,
    allowed: dict[str, str],
) -> list[dict[str, Any]]:
    """Memory ノードが KG v1 ラベルを持つケースを検出する。

    Parameters
    ----------
    session
        Neo4j セッション。
    allowed : dict[str, str]
        許可ラベルマッピング（kg_v1 ラベルを動的に取得するため）。

    Returns
    -------
    list[dict[str, Any]]
        クロスコンタミネーションの一覧。
    """
    kg_v1_labels = [label for label, ns in allowed.items() if ns == "kg_v1"]
    query = """
    MATCH (n:Memory)
    WHERE any(l IN labels(n) WHERE l IN $kg_labels)
    RETURN labels(n) AS labels, n.name AS name
    """
    result = session.run(query, kg_labels=kg_v1_labels)
    return [dict(r) for r in result]


def classify_db_labels(
    db_labels: list[str],
    allowed: dict[str, str],
) -> dict[str, list[str]]:
    """DB ラベルを名前空間ごとに分類する。

    Parameters
    ----------
    db_labels : list[str]
        DB 上の全ラベル。
    allowed : dict[str, str]
        許可ラベルマッピング。

    Returns
    -------
    dict[str, list[str]]
        名前空間名 → ラベルリスト。
    """
    classified: dict[str, list[str]] = {}
    for label in db_labels:
        ns = allowed.get(label, "UNKNOWN")
        classified.setdefault(ns, []).append(label)
    return classified


# ---------------------------------------------------------------------------
# Report building & formatting
# ---------------------------------------------------------------------------


def build_report(
    *,
    schema_path: str,
    db_labels: list[str],
    allowed: dict[str, str],
    unknown_labels: list[dict[str, str]],
    pascal_violations: list[dict[str, str]],
    contamination: list[dict[str, Any]],
    classified: dict[str, list[str]],
    now: datetime | None = None,
) -> dict[str, Any]:
    """検証結果からレポート辞書を構築する。"""
    if now is None:
        now = datetime.now(timezone.utc)
    return {
        "validation_date": now.isoformat(),
        "schema_path": schema_path,
        "db_label_count": len(db_labels),
        "allowed_label_count": len(allowed),
        "namespace_classification": classified,
        "checks": {
            "unknown_labels": {
                "count": len(unknown_labels),
                "pass": len(unknown_labels) == 0,
                "details": unknown_labels,
            },
            "pascal_case_violations": {
                "count": len(pascal_violations),
                "pass": len(pascal_violations) == 0,
                "details": pascal_violations,
            },
            "cross_contamination": {
                "count": len(contamination),
                "pass": len(contamination) == 0,
                "details": contamination,
            },
        },
        "overall_pass": (
            len(unknown_labels) == 0
            and len(pascal_violations) == 0
            and len(contamination) == 0
        ),
    }


def format_report(report: dict[str, Any]) -> str:
    """レポートをテキスト形式にフォーマットする。"""
    lines: list[str] = []
    lines.append("\n=== Neo4j Schema Validation Report ===\n")
    lines.append(f"DB Labels: {report['db_label_count']}")
    lines.append(f"Allowed Labels: {report['allowed_label_count']}")
    lines.append("")

    lines.append("Namespace Classification:")
    for ns, labels in sorted(report["namespace_classification"].items()):
        lines.append(f"  {ns}: {', '.join(sorted(labels))}")
    lines.append("")

    unknown = report["checks"]["unknown_labels"]
    if unknown["count"] > 0:
        lines.append(f"UNKNOWN labels ({unknown['count']}):")
        for u in unknown["details"]:
            lines.append(f"  - {u['label']}")
    else:
        lines.append("UNKNOWN labels: 0 (PASS)")

    violations = report["checks"]["pascal_case_violations"]
    if violations["count"] > 0:
        lines.append(f"\nPascalCase violations ({violations['count']}):")
        for v in violations["details"]:
            lines.append(f"  - {v['label']}: {v['issue']}")
    else:
        lines.append("PascalCase violations: 0 (PASS)")

    contamination = report["checks"]["cross_contamination"]
    if contamination["count"] > 0:
        lines.append(f"\nCross-contamination ({contamination['count']}):")
        for c in contamination["details"]:
            lines.append(f"  - {c['name']}: {c['labels']}")
    else:
        lines.append("Cross-contamination: 0 (PASS)")

    lines.append(f"\nOverall: {'PASS' if report['overall_pass'] else 'FAIL'}")
    return "\n".join(lines)


def save_report(report: dict[str, Any], output_path: Path) -> None:
    """レポートを JSON ファイルに保存する。"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    logger.info("Report saved: %s", output_path)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def _validate_uri_scheme(uri: str) -> None:
    """URI スキームが許可されたものか検証する。"""
    parsed = urlparse(uri)
    if parsed.scheme not in ALLOWED_URI_SCHEMES:
        msg = (
            f"Unsupported URI scheme: {parsed.scheme}. "
            f"Allowed: {', '.join(sorted(ALLOWED_URI_SCHEMES))}"
        )
        raise ValueError(msg)


def _validate_output_path(output: str) -> Path:
    """出力パスがプロジェクト内であることを検証する。"""
    output_path = Path(output).resolve()
    project_root = Path.cwd().resolve()
    if not str(output_path).startswith(str(project_root)):
        msg = f"Output path must be under project root: {project_root}"
        raise ValueError(msg)
    return output_path


def main() -> None:
    """スキーマ検証のエントリーポイント。"""
    parser = argparse.ArgumentParser(
        description="Validate Neo4j schema against knowledge-graph-schema.yaml",
    )
    parser.add_argument(
        "--schema",
        default="data/config/knowledge-graph-schema.yaml",
        help="Path to knowledge-graph-schema.yaml",
    )
    parser.add_argument("--output", help="Output JSON report path")
    parser.add_argument(
        "--neo4j-uri",
        default=os.environ.get("NEO4J_URI", "bolt://localhost:7690"),
        help="Neo4j connection URI (default: bolt://localhost:7690)",
    )
    parser.add_argument(
        "--neo4j-user",
        default=os.environ.get("NEO4J_USER", "neo4j"),
        help="Neo4j username",
    )
    parser.add_argument(
        "--neo4j-password",
        default=os.environ.get("NEO4J_PASSWORD"),
        help="Neo4j password (required: set NEO4J_PASSWORD env var)",
    )
    args = parser.parse_args()

    if not args.neo4j_password:
        parser.error(
            "Neo4j password is required. "
            "Set NEO4J_PASSWORD environment variable or use --neo4j-password."
        )

    try:
        _validate_uri_scheme(args.neo4j_uri)
    except ValueError as e:
        parser.error(str(e))

    logger.info("Loading schema: %s", args.schema)
    try:
        namespaces = load_namespaces(Path(args.schema))
    except ValueError as e:
        logger.error("%s", e)
        sys.exit(1)

    allowed = build_allowed_labels(namespaces)
    logger.info("Allowed labels loaded: %d", len(allowed))

    parsed_uri = urlparse(args.neo4j_uri)
    logger.info("Connecting to Neo4j: %s:%s", parsed_uri.hostname, parsed_uri.port)
    driver: Driver = GraphDatabase.driver(
        args.neo4j_uri,
        auth=(args.neo4j_user, args.neo4j_password),
    )

    try:
        with driver.session() as session:
            result = session.run(
                "CALL db.labels() YIELD label RETURN label ORDER BY label"
            )
            db_labels = [r["label"] for r in result]
            logger.info("DB labels fetched: %d", len(db_labels))

            classified = classify_db_labels(db_labels, allowed)
            unknown_labels = [
                {"label": label, "namespace": "UNKNOWN"}
                for label in classified.get("UNKNOWN", [])
            ]
            pascal_violations = check_pascal_case_violations(db_labels)
            contamination = check_cross_contamination(session, allowed)

        report = build_report(
            schema_path=args.schema,
            db_labels=db_labels,
            allowed=allowed,
            unknown_labels=unknown_labels,
            pascal_violations=pascal_violations,
            contamination=contamination,
            classified=classified,
        )

        print(format_report(report))

        if args.output:
            try:
                validated_path = _validate_output_path(args.output)
            except ValueError as e:
                logger.error("%s", e)
                sys.exit(1)
            save_report(report, validated_path)

        if not report["overall_pass"]:
            sys.exit(1)

    finally:
        driver.close()


if __name__ == "__main__":
    main()
