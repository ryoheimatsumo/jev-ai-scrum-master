# インストールと配布

[English](DISTRIBUTION.md)

GitHubリポジトリは公開済みです。ソースとSkillを配布するものであり、独自のnpm・PyPIパッケージ公開や、
公式マーケットプレイスへの掲載ではありません。ローカルの配布テストだけで、すべてのエージェントが
Skillを発見・実行できると確認したことにはなりません。

## Agent Skillsインストーラー

開発対象プロジェクトのGitルートで実行します。

```sh
npx skills add ryoheimatsumo/jev-ai-scrum-master --skill jev-scrum-master
```

第三者の`skills` CLIがホスト選択と配置を担当します。Node/npmとレジストリへの接続が必要です。
導入元と配置内容を確認してください。ユーザー単位は`-g`、省略時はプロジェクト単位です。
一括の`--all`や承認省略フラグを、通常の導入例には使いません。

| ホスト | インストーラーのID |
|---|---|
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

上流で案内される配置先であり、本製品の実機検証済み一覧ではありません。
ホストにはローカルSkillと、Git・Pythonを使うシェル実行機能が必要です。指定例：

```sh
npx skills add ryoheimatsumo/jev-ai-scrum-master --skill jev-scrum-master -a cursor
```

インストーラーには独自のテレメトリーがあります。[上流の説明](https://skills.sh/docs/cli)に従い、
停止する場合は`DISABLE_TELEMETRY=1`を設定します。この設定はコーディングホストやJevの通信を制御しません。

## Claude Codeのリポジトリマーケットプレイス

Claude Code内で実行します。

```text
/plugin marketplace add ryoheimatsumo/jev-ai-scrum-master
/plugin install jev-ai-scrum-master@jev-dev-tools
```

ホストの案内に従って再読み込みしてください。本リポジトリの定義ファイルを利用するもので、
Anthropicによる承認を示すものではありません。MCP、Hook、拡張権限は追加しません。
[上流のマーケットプレイス説明](https://code.claude.com/docs/en/plugin-marketplaces)。

## Codexのマーケットプレイスを使う場合

```sh
codex plugin marketplace add ryoheimatsumo/jev-ai-scrum-master
```

これはカタログの登録です。コマンドの実行だけで、Skillの導入や動作が確認できるわけではありません。
導入済みホストのプラグイン画面で、Jev Development Tools / Jev AI Scrum Masterを選びます。
[上流のプラグイン説明](https://developers.openai.com/plugins/build/plugins)では、カタログの設定と、
対応デスクトップ画面からの導入・テストを案内しています。
利用中の版で使えない場合は`npx skills ... -a codex`を使ってください。本製品の実ホスト連携は未検証です。

## 初回設定・更新・削除

1ホストでは1つの経路を使います。`jev-scrum-master`のセットアップをホストに依頼し、
ダウンロード内容を確認して、実際のチェックを登録します。[クイックスタート](QUICKSTART.ja.md)。

SkillにはCLI wheel、整合性manifest、ランチャー、参照資料を含みます。`SKILL.md`だけをコピーしないでください。
同意後に、プロジェクト外へ専用環境を作ります。CoreはPython 3.12以上が必要です。
ランチャーはPython 3.9以上で起動でき、導入済みのuvとダウンロード同意があれば、新しいPythonを取得できます。
システムツール、APIキー、権限、MCP、Hookを黙って設定しません。

更新では内容・版ごとの実行環境を使い、過去の状態は保持します。上流の更新でローカル編集が
置き換わることがあるため、独自変更はforkやバックアップで管理してください。
同じインストーラーの一覧・確認・更新・削除機能を使い、更新前に現行のhelpで動作を確認します。
Skill削除は、実行環境、証拠、タスク履歴、別に保管した認証情報の削除ではありません。

ローカルcheckoutやforkは、リポジトリ名の代わりにディレクトリを指定できます。

```sh
npx skills add /ABS/PATH/TO/jev-ai-scrum-master --skill jev-scrum-master -a cursor
```

ローカル導入でも、インストーラーが未取得なら取得先への接続が必要です。

## 配布内容の整合性と制限

ランチャーは同梱wheelの版とSHA-256を確認します。不一致を検知するもので、発行者を証明する署名ではありません。
依存関係は範囲指定であり完全固定ではなく、専用Python環境もセキュリティ上のサンドボックスではありません。
Jevには別途SDK、APIキー、送信内容の確認、有効化が必要です。
[安全性](../SECURITY.ja.md) · [実装状況](IMPLEMENTATION_STATUS.ja.md)。

メンテナーは[リリース準備](PUBLISHING.ja.md)を参照してください。版ごとの生の検証記録は、
その時点の試験を記録したもので、現在のリモート導入状況を示すものではありません。
