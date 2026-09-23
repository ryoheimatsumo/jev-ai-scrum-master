# 実装状態 — 0.1.0a3

更新日: 2026-09-23

## 現在地

- GitHubリポジトリ: **Publicで公開済み**
- 標準入口: **Skill + CLI**
- MCP: 任意アダプター
- Jev: 任意・既定無効
- 製品ラベル: **experimental alpha / quality improvement unverified**

公開済みであることと、各ホストでのend-to-end互換性や品質改善が実証済みであることは別です。

## 実装済みの主要フロー

```text
計画
→ 契約/設定/参照版の固定
→ 人間の承認
→ 実装開始
→ 登録済みcheckの隔離実行
→ AC別の証拠評価
→ 必要なレビュー
→ completion gate
→ 改善提案
```

ホストLLMが計画・分割・実装・自由文の説明を担当します。Coreはコード生成エージェントではなく、状態、承認、Runner、証拠、完了条件を管理します。

## Jevを使う経路

現在のJev経路：

- **readiness**: 計画不足や観測可能性の補助判定
- **playbook**: 継続 / 最小再現 / 環境確認 / 保存確認 / 契約確認 / 人間判断などの次手候補
- **context selection**: 必須・不明情報を残し、強く無関係な候補を退避
- **evidence relation**: ACとRunner証拠の関係候補を評価

Jevの判断だけでPASSやDONEにはしません。低confidence、UNKNOWN、API障害は必要なレビューへフォールバックします。

判定キャッシュは補助判断専用で、承認、テスト結果、完了資格を再利用するものではありません。

## 完了条件の主要ガード

ローカルCoreでは、少なくとも次を扱います。

- 未承認計画から開始しない
- agent claimだけでACをPASSにしない
- 必須AC未検証ならDONEにしない
- zero tests / 必須skip / レポート欠損を行動ACの成功にしない
- relevant input変更後は古い証拠をSTALEにする
- 契約変更後は古い承認を再利用しない
- 未承認checkを実行しない
- 同一失敗・無進捗や修正ラウンドに上限を持つ
- strictタスクでは追加の人間確認を要求
- 改善案は承認されるまで次タスクの必須ルールにしない

詳細な受け入れ条件は [v1.0 specification](spec/v1.0.ja.md) を参照してください。

## 配布状態

公開リポジトリからAgent Skillsとして導入できる構成です。

```sh
npx skills add ryoheimatsumo/jev-ai-scrum-master --skill jev-scrum-master
```

Claude Code / Codex向けのmarketplace metadataも含みます。

ただし、上流インストーラーが対応するホストIDと、本製品が実機end-to-end検証済みであることは区別しています。

詳細: [DISTRIBUTION.ja.md](DISTRIBUTION.ja.md)

## 現在の明確な制限

未実装または未実証：

- 自動の独立AIレビュー
- hard crash中jobの完全自動復旧
- 強制Hook / CI enforcementの完成版
- 完全な外部環境fingerprint
- mutation testing
- Jev質問の自動最適化
- 実Jev APIを使った精度改善ベンチマーク
- end-to-endの速度 / 総コスト / トークン削減効果
- 全対応候補ホストでの実機smoke test
- macOS実機検証
- ネイティブWindows Core対応

ローカルRunnerは信頼済みコードを前提としており、OS / network sandboxではありません。

## 検証記録

実際に行ったローカル検証は `docs/validation/` に保存しています。

テストfixtureによる承認は`SIMULATED_DEMO_ONLY`であり、実人間レビューやAI品質の実証として扱いません。

Jev provider fixtureでのテストは、API課金・実精度・実レイテンシを証明しません。

## 履歴

変更履歴は [CHANGELOG.md](../CHANGELOG.md)、主要な設計判断は `docs/adr/` を参照してください。

過去版で「GitHub未公開」と記録されていた文言は、その時点の履歴であり、現在の状態ではありません。
