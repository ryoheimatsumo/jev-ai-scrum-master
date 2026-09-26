# ドキュメント一覧

[English](README.md)

利用者・メンテナー向けのガイドを日英で用意しています。各ページ上部から言語を切り替えられます。
英語の案内は英語ガイドへ、日本語の案内は日本語ガイドへリンクします。

| 内容 | English | 日本語 |
|---|---|---|
| 概要 | [Read](../README.md) | [読む](../README.ja.md) |
| クイックスタート | [Read](QUICKSTART.md) | [読む](QUICKSTART.ja.md) |
| 導入・更新 | [Read](DISTRIBUTION.md) | [読む](DISTRIBUTION.ja.md) |
| Jev設定 | [Read](JEV.md) | [読む](JEV.ja.md) |
| 構成 | [Read](ARCHITECTURE.md) | [読む](ARCHITECTURE.ja.md) |
| 実装状況 | [Read](IMPLEMENTATION_STATUS.md) | [読む](IMPLEMENTATION_STATUS.ja.md) |
| 残作業 | [Read](BACKLOG.md) | [読む](BACKLOG.ja.md) |
| 安全性 | [Read](../SECURITY.md) | [読む](../SECURITY.ja.md) |
| 開発への参加 | [Read](../CONTRIBUTING.md) | [読む](../CONTRIBUTING.ja.md) |
| リリース手順 | [Read](PUBLISHING.md) | [読む](PUBLISHING.ja.md) |
| ホスト連携 | [Read](../integrations/README.md) | [読む](../integrations/README.ja.md) |
| 変更履歴 | [Read](../CHANGELOG.md) | [読む](../CHANGELOG.ja.md) |
| 検証記録の案内 | [Read](validation/INDEX.md) | [読む](validation/INDEX.ja.md) |
| 公開内容の確認 | [Read](PUBLICATION_REVIEW.md) | [読む](PUBLICATION_REVIEW.ja.md) |
| PRの案内 | [Read](PULL_REQUEST.md) | [読む](PULL_REQUEST.ja.md) |

## 意図的に原本を維持する記録

[確定仕様v1.0](spec/v1.0.ja.md)は日本語の固定した設計原本で、現在使える全機能の宣言ではありません。
翻訳済みの利用者ガイドではなく、英語読者には上の構成・現状・残作業を案内します。
[ADR-001](adr/001-initial-slice-and-jev-efficiency.md)、[ADR-002](adr/002-skill-first-cli.md)、
[ADR-003](adr/003-marketplace-and-npx.md)も、当時の判断を残した英語原本です。
現在の利用に関係する内容は、両言語の構成ガイドに反映しています。

実行用の[Skill](../skills/jev-scrum-master/SKILL.md)、[CLI契約](../skills/jev-scrum-master/references/cli.md)、
ソースの識別子、生のJSON・XML・テキストは、元の英語・機械形式を維持します。
言語によって別実装を作るものではありません。過去の検証証拠を、新しい試験のように翻訳・改変しません。
[LICENSE](../LICENSE)はApache-2.0の正式な原文を維持します。

## 日英を揃える方針

英語は`.md`、日本語は`.ja.md`を使い、対を`languages.json`に登録します。
手順、安全性、既定値、成熟度の変更では、両方を更新します。
ルートから`python scripts/check_public_docs.py`を実行してください。
自動のリンク・言語チェックは意味の一致を保証しないため、翻訳の内容もレビューします。
