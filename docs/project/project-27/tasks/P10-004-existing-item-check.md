# P10-004: 既存Project Item検出

## 概要

IssueがすでにProjectに追加されている場合を検出し、重複追加を回避する。

## 背景

`gh project item-add` でIssueが既にProjectに存在する場合、item_idが空で返される可能性がある。事前に存在チェックを行い、既存のitem_idを取得する。

## 変更内容

### 変更ファイル

| ファイル | 変更内容 |
|----------|----------|
| `src/news/publisher.py` | `_get_existing_project_item` メソッド追加 |

### 実装詳細

```python
# src/news/publisher.py

async def _get_existing_project_item(
    self,
    issue_url: str,
) -> str | None:
    """Project内の既存Itemを検索しitem_idを返す。

    Parameters
    ----------
    issue_url : str
        検索するIssueのURL。

    Returns
    -------
    str | None
        既存のitem_id、存在しない場合はNone。
    """
    owner = self._repo.split("/")[0]

    # gh project item-list でProject内のItemを取得
    result = subprocess.run(
        [
            "gh", "project", "item-list",
            str(self._project_number),
            "--owner", owner,
            "--format", "json",
            "--jq", f'.items[] | select(.content.url == "{issue_url}") | .id',
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0 and result.stdout.strip():
        item_id = result.stdout.strip()
        logger.debug(
            "Found existing project item",
            issue_url=issue_url,
            item_id=item_id,
        )
        return item_id

    return None


async def _add_issue_to_project(
    self,
    issue_number: int,
    article: SummarizedArticle,
) -> None:
    """Issue を Project に追加し、フィールドを設定。"""
    issue_url = f"https://github.com/{self._repo}/issues/{issue_number}"

    # 既存Item検索
    item_id = await self._get_existing_project_item(issue_url)

    if item_id is None:
        # 新規追加
        owner = self._repo.split("/")[0]
        add_result = subprocess.run(
            ["gh", "project", "item-add", ...],
            ...
        )
        item_id = add_result.stdout.strip()

        if not item_id:
            logger.warning("Empty item_id from project item-add", ...)
            return
    else:
        logger.info(
            "Issue already in project, updating fields",
            issue_number=issue_number,
            item_id=item_id,
        )

    # フィールド設定（新規・既存共通）
    ...
```

## 受け入れ条件

- [ ] 既存Issueのitem_idが正しく取得される
- [ ] 新規Issueは通常通り追加される
- [ ] 既存Issueはフィールド更新のみ実行される
- [ ] 単体テストが通る

## テストケース

```python
def test_existing_item_returns_item_id(publisher, mocker):
    """既存Itemがある場合、item_idを返す。"""
    mocker.patch(
        "subprocess.run",
        return_value=Mock(stdout="PVTI_xxx", returncode=0),
    )

    item_id = await publisher._get_existing_project_item(
        "https://github.com/YH-05/quants/issues/123"
    )

    assert item_id == "PVTI_xxx"


def test_no_existing_item_returns_none(publisher, mocker):
    """既存Itemがない場合、Noneを返す。"""
    mocker.patch(
        "subprocess.run",
        return_value=Mock(stdout="", returncode=0),
    )

    item_id = await publisher._get_existing_project_item(
        "https://github.com/YH-05/quants/issues/999"
    )

    assert item_id is None
```

## 依存関係

- 依存先: P10-003
- ブロック: P10-016

## 見積もり

- 作業時間: 30分
- 複雑度: 中
