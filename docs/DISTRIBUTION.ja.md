# マーケットプレイス／npx導入 — 0.1.0a3

このリポジトリは **GitHubで公開済み** です。標準の導入方法は、既存のAgent Skillsインストーラーまたは各ホストのマーケットプレイス機能を使う方法です。

基本体験は次の通りです。

> Skillを追加 → ホストでセットアップを依頼 → 初回の準備内容を確認 → プロジェクトの検証設定を登録 → 利用開始

Skillの追加だけで、Python、プロジェクト依存関係、APIキー、テスト環境まで自動的に準備されるわけではありません。

## 1. Agent Skills / npx（標準）

独自npmパッケージではなく、Vercelの`skills` CLIを利用します。Node.js/npmが必要です。

対象プロジェクトのルートで実行します。

```sh
npx skills add ryoheimatsumo/jev-ai-scrum-master --skill jev-scrum-master
```

特定のエージェントを指定する例：

```sh
# Cursor
npx skills add ryoheimatsumo/jev-ai-scrum-master --skill jev-scrum-master -a cursor

# Windsurf
npx skills add ryoheimatsumo/jev-ai-scrum-master --skill jev-scrum-master -a windsurf

# GitHub Copilot
npx skills add ryoheimatsumo/jev-ai-scrum-master --skill jev-scrum-master -a github-copilot

# Gemini CLI
npx skills add ryoheimatsumo/jev-ai-scrum-master --skill jev-scrum-master -a gemini-cli

# OpenCode + Cline
npx skills add ryoheimatsumo/jev-ai-scrum-master --skill jev-scrum-master -a opencode -a cline
```

確認済みの上流インストーラー識別子：

| 対象 | `--agent` |
|---|---|
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
| Codex | `codex` |
| Claude Code | `claude-code` |

これは **上流インストーラーの配置対象一覧** であり、本製品をすべてのホストでend-to-end検証済みという意味ではありません。

既定はプロジェクト単位です。ユーザー単位に配置する場合は`-g`を追加します。不要なホストまで対象にする`--all`は既定例にしません。

上流CLIの匿名テレメトリーを停止する場合は、上流仕様に従って`DISABLE_TELEMETRY=1`を指定します。

## 2. ローカルcheckout / forkからの導入

開発中のforkやローカル変更を試す場合は、GitHubリポジトリ名の代わりにローカルパスを指定できます。

```sh
npx skills add /ABS/PATH/TO/jev-ai-scrum-master --skill jev-scrum-master -a cursor
```

`SKILL.md`だけを単独コピーするのではなく、Skillディレクトリ全体を扱ってください。`runtime/`、`scripts/`、`references/`も実行に必要です。

## 3. Claude Code marketplace

Claude Code内で：

```text
/plugin marketplace add ryoheimatsumo/jev-ai-scrum-master
/plugin install jev-ai-scrum-master@jev-dev-tools
```

`.claude-plugin/marketplace.json`が一覧、`.claude-plugin/plugin.json`が製品定義です。

これはこのGitHubリポジトリを導入元として使う方法です。Anthropic公式ディレクトリへの掲載を意味しません。

Hook、MCP、追加権限は自動設定しません。

## 4. Codex marketplace

```sh
codex plugin marketplace add ryoheimatsumo/jev-ai-scrum-master
```

対応するプラグイン画面から **Jev Development Tools → Jev AI Scrum Master** を選択します。

利用しているCodex版でマーケットプレイス機能が利用できない場合は、`npx skills ... -a codex`を使ってください。

## 5. 追加後の初回セットアップ

ホストを必要に応じて再読み込みし、次のように依頼します。

> jev-scrum-masterを使いたい。このプロジェクトで使えるようにセットアップして。

Skillは自身の配置先を基準に、同梱CLIのセットアップ方法を案内します。利用者が確認した後、専用Python環境にCLIと必要な依存関係を導入します。

標準導線では、手動clone・venvのactivate・MCP登録は必須ではありません。

### Coreの前提

- Git
- Python 3.12以上
- `npx skills`経由の場合はNode.js/npm

ランチャー自体はPython 3.9以上で動くようにしており、既に`uv`がある環境では、利用者の同意後に適切なPythonを用意できる経路があります。

OSのパッケージマネージャを無断で実行しません。

### Jevを使う場合

Jevは任意機能で、初期状態は無効です。

有効化する場合：

1. 送信対象を確認する
2. 任意のJev SDKを導入する
3. 本人が`TYPESAFE_API_KEY`を環境変数へ設定する
4. `.jev-sm/config.yaml`で`jev_enabled: true`へ変更する

APIキーをチャット、Skill、Git、プロジェクト設定へ直接書かないでください。

設定変更はタスクの契約ハッシュに影響するため、作業中タスクは再確認が必要です。

## 6. 初回起動の内部処理

SkillにはCLI wheel、整合性確認用manifest、bootstrap launcherを含みます。

- wheelの内容と版がmanifestと一致しなければ停止
- 専用ランタイムはプロジェクト外に作成
- Skillの版・wheel内容・SDK有無ごとに環境を分離
- 更新時に既存タスク状態や古いランタイムを勝手に削除しない
- APIキー、MCP、Hook、ホスト権限を自動設定しない

ハッシュは破損・取り違え検出用であり、発行者署名や完全なサプライチェーン保証ではありません。

## 7. 更新・削除

Agent Skills経由の場合は、上流CLIの更新・削除機能を使います。

```sh
npx skills list
npx skills update jev-scrum-master
npx skills remove jev-scrum-master
```

1つのホストにmarketplace版とAgent Skills版を重複して導入しないでください。

Skillの削除は、タスク履歴、証拠、Pythonランタイム、外部資格情報まで自動削除する操作ではありません。

## 8. 配布検証

maintainer向け：

```sh
python scripts/build_marketplace.py
python scripts/validate_distribution.py
```

実`npx`導入確認用の補助：

```sh
python scripts/smoke_skills_install.py --skills-version 1.7.0 --agent cursor --write --allow-downloads
```

この試験はSkill配置とbootstrapの確認を目的としており、実ホスト上の開発品質、Jevの精度、速度、トークン削減まで検証するものではありません。

## 現在の制限

- リポジトリは公開済みだが、すべてのホストで実機end-to-end検証済みではない
- 実Jev APIを使った品質・速度・コスト・トークン削減効果は未実証
- macOS実機は未検証
- ネイティブWindows版Coreはalphaの対応対象外
- 自動の独立AIレビューは未実装

詳細は [実装状態](IMPLEMENTATION_STATUS.ja.md) と [検証記録](validation/marketplace/README.md) を参照してください。

## 参考

- https://skills.sh/docs/cli
- https://github.com/vercel-labs/skills
- https://code.claude.com/docs/en/plugin-marketplaces
- https://developers.openai.com/plugins/build/plugins
