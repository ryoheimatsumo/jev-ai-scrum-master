# 開発への参加

[English](CONTRIBUTING.md)

信頼性、文書、再現可能なテストの改善を歓迎します。本製品は実験的α版です。
目標仕様を実装済みとして説明しないでください。最初に[現在の実装状況](docs/IMPLEMENTATION_STATUS.ja.md)と
[セキュリティ](SECURITY.ja.md)を確認してください。

## ローカル開発

ソースのcheckoutで、Python 3.12以上と仮想環境を使用します。

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
python -m compileall -q src tests
python -m pytest -q
python scripts/check_public_docs.py
python scripts/sync_skill_assets.py --check
python scripts/validate_distribution.py
```

任意SDKを検証するときだけ`.[dev,mcp,jev]`を導入します。実Jevテストには別途、明示許可と認証情報が必要です。
SDKのインストールは、有料API呼び出しへの同意ではありません。

`python scripts/demo_cli.py --simulate-approvals`は使い捨てデモです。承認はテスト用で、本物の人間レビューではありません。
本番に偽の人間承認オプションを追加しないでください。

## 変更と生成物

別ブランチで作業してPRを作成します。テスト、制限、安全性への影響を含めてください。
必須チェックを弱めたり、モデルからPASS・DONEを直接書かせたり、外部送信や実行権限を黙って広げたりしないでください。
文書整備に合わせてリポジトリ名を勝手に変更しないでください。

実行用Skillは`src/jev_sm/assets/skills/jev-scrum-master`の正本を編集し、`skills/`のミラーだけを編集しません。
ソース・Skill変更でwheelの再生成が必要な場合は[リリース手順](docs/PUBLISHING.ja.md)を使います。
CLIとMCPは同じCoreを利用し、利用者の指示ファイルを保持してください。

## 英語・日本語ドキュメント

両言語を同じPRで更新します。`README.md`と通常の`.md`ガイドは英語、`.ja.md`は日本語とし、
タイトル付近に相互リンクを置きます。動作、注意点、既定値、コマンド、成熟度を一致させ、
計画中の機能を黙って実装済みにしないでください。

人向けの対は`docs/languages.json`に登録します。自動チェックはリンク、言語版の有無、特定の古い表現を確認しますが、
翻訳精度を証明するものではありません。意味もレビューしてください。
実行用Skill契約と生ログは翻訳用に重複させません。原仕様と履歴は[文書一覧](docs/README.ja.md)で明示します。

IssueやPRに秘密情報、個人・顧客情報、未確認の生ログを投稿しないでください。
マスクした最小例だけを共有してください。[脆弱性報告](SECURITY.ja.md)。
