# Skill・プラグインの導入と更新

公開元は `ryoheimatsumo/jev-ai-scrum-master` です。追加 → セットアップ確認 →
テスト設定 → 利用の順に進めます。**配置できることと、実ホストでの動作検証済みは別です。**
初めて使う場合は[クイックスタート](QUICKSTART.ja.md)を参照してください。

## npxによる導入

開発対象プロジェクトのGitルートで実行します。

```sh
npx skills add ryoheimatsumo/jev-ai-scrum-master --skill jev-scrum-master
# 例: Cursorを指定
npx skills add ryoheimatsumo/jev-ai-scrum-master --skill jev-scrum-master -a cursor
```

上流インストーラーの対象IDとして案内しているもの：

| ホスト | ID |
| --- | --- |
| Codex | `codex` |
| Claude Code | `claude-code` |
| Cursor | `cursor` |
| Windsurf | `windsurf` |
| GitHub Copilot | `github-copilot` |
| Gemini CLI | `gemini-cli` |
| OpenCode | `opencode` |
| Cline | `cline` |
| Roo Code | `roo` |
| Antigravity | `antigravity` |
| Kilo Code | `kilo` |
| Grok Build | `grok` |

ホストはローカルSkillを読み、Python/Gitコマンドを実行できる必要があります。
一覧は本製品の実機テスト結果ではありません。使用中の `skills --help` とホストの対応状況を確認してください。
ユーザー単位なら `-g`、コピー配置なら `--copy` を指定できます。不要なホストへの
導入や確認省略を避けるため、`--all` と `--yes` は通常の導入例には使いません。

`skills`は第三者のCLIです。更新・配置・テレメトリーはその仕様に従います。
上流の匿名統計を無効にする設定は `DISABLE_TELEMETRY=1` です。
本プロジェクトがこの第三者CLIを配布・運営しているわけではありません。

## Claude Codeのマーケットプレイス

```text
/plugin marketplace add ryoheimatsumo/jev-ai-scrum-master
/plugin install jev-ai-scrum-master@jev-dev-tools
```

このリポジトリを追加する方式で、公式ディレクトリへの掲載や推薦ではありません。
Codexも対応版ではリポジトリのマーケットプレイス定義を利用できますが、利用中の版で
使えない場合は `npx skills ... -a codex` を利用してください。MCP・Hook・権限の自動追加はありません。

## ローカルcheckout / fork

```sh
npx skills add /ABS/PATH/TO/jev-ai-scrum-master --skill jev-scrum-master -a cursor
```

`SKILL.md` 単体ではなく、`runtime/`・`scripts/`・`references/` を含むSkill全体が必要です。
配置後、ホストへセットアップを依頼します。Python環境やプロジェクト依存関係を準備する
許可と、タスク計画の承認は別です。Jevの有効化・APIキーも別途確認します。

## 初回起動と更新

同梱wheelは整合性manifestと照合します。不一致なら検査を迂回せず、信頼する導入元を確認してください。
ハッシュは破損・取り違えの検出であり、発行者署名や完全な供給経路の保証ではありません。
専用Python環境はプロジェクト外に作られ、版・wheel内容・SDK有無ごとに区別されます。
依存パッケージは範囲指定で、完全な再現環境ではありません。

更新・削除には導入時と同じ経路を使い、実行前に対象と上流CLIのヘルプを確認してください。

```sh
npx skills list
npx skills update --help
npx skills remove --help
```

1ホストへマーケットプレイス版とnpx版を重ねないでください。上流インストーラーの更新は
Skillを置き換える場合があります。独自編集はfork等で管理し、更新前に退避します。
本製品の旧 `jev-sm skill install` の上書き防止を、第三者インストーラーの保証と混同しないでください。
Skillの削除は、履歴・証拠・Python環境・外部資格情報の削除ではありません。

## 制限とデータ送信

CoreはGit/Python 3.12以上が必要です。LinuxのCore/SDK CIと、実ホスト・実Jevの検証は別です。
macOSの実機動作は未確認、ネイティブWindowsは非対応です。
Jevは既定無効ですが、ホストAIやインストーラーは独自の外部通信を行い得ます。
[SECURITY.md](../SECURITY.md)と[実装状態](IMPLEMENTATION_STATUS.ja.md)を確認してください。

配布物の生成・整合性確認は[maintainerガイド](PUBLISHING.ja.md)へ分離しています。
