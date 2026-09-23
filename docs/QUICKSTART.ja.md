# マーケットプレイス／npx導入 — 0.1.0a3

## 現在地

配布用のファイルと初回起動処理を実装した段階です。**GitHub公開、公式ストア掲載、公開URLからの
npx導入成功を意味しません。** 自前のマーケットプレイス追加と公式ディレクトリ掲載も別です。
`OWNER`は公開先アカウントに置き換えます。配布物を含むPRが未マージでdefault branchにない場合、
リポジトリ短縮URLでは導入できません。

基本体験は **追加 → ホストでセットアップを依頼 → 初回の準備を確認 → 利用**。
追加コマンドだけでPython・APIキー・プロジェクトのテスト環境が自動的にそろうわけではありません。

## 1. 他のコーディングエージェント: npx（標準）

独自npmパッケージではなく、Vercelの既存の`skills` CLIを使います。こちらのnpm/PyPI公開は不要。
Node.js/npmが必要です。ホストの選択、配置先、更新・削除は上流CLIが担当します。

**公開後、対象プロジェクトのルートで実行するコマンド：**

```sh
npx skills add OWNER/jev-ai-scrum-master --skill jev-scrum-master
```

対象エージェントを対話的に選びます。指定して追加する場合：

```sh
# Cursor
npx skills add OWNER/jev-ai-scrum-master --skill jev-scrum-master -a cursor
# Windsurf
npx skills add OWNER/jev-ai-scrum-master --skill jev-scrum-master -a windsurf
# GitHub Copilot
npx skills add OWNER/jev-ai-scrum-master --skill jev-scrum-master -a github-copilot
# Gemini CLI
npx skills add OWNER/jev-ai-scrum-master --skill jev-scrum-master -a gemini-cli
# 複数へ追加
npx skills add OWNER/jev-ai-scrum-master --skill jev-scrum-master -a opencode -a cline
```

| 対象 | `--agent`の値 |
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

上流CLIの配置対象として確認した識別子です。**本製品を各ホストで実行検証した一覧ではありません。**
ホストがローカルのSkillを読み、シェルからPython/Gitを実行できることが必要です。
既定はプロジェクト単位。全プロジェクトで使うユーザー単位の配置には`-g`を追加します。
コピーを選ぶ場合は`--copy`。`--all`や`--yes`は既定例にしません。
上流の匿名インストール統計を停止する場合は先頭に`DISABLE_TELEMETRY=1`を指定します。

## 2. GitHub公開前のローカル導入

ZIPを展開し、**利用したいプロジェクトのルート**で次を実行します。
初回の`skills` CLI取得にnpm接続が必要ですが、GitHub公開は不要です。

```sh
npx skills add /ABS/EXTRACTED/jev-ai-scrum-master --skill jev-scrum-master -a cursor
```

SkillだけのZIPは、展開した`skills/`を含むディレクトリを指定できます。
`SKILL.md`単体のコピーは不可。`runtime/`、`scripts/`、`references/`も必要です。

## 3. Claude Codeマーケットプレイス

公開後はClaude Code内で：

```text
/plugin marketplace add OWNER/jev-ai-scrum-master
/plugin install jev-ai-scrum-master@jev-dev-tools
```

公開前の1行目は`/plugin marketplace add /ABS/EXTRACTED/jev-ai-scrum-master`。
`.claude-plugin/marketplace.json`が一覧、`.claude-plugin/plugin.json`が製品定義です。
ホストの案内に従って再読み込み。Hook・MCP・権限設定は同梱しません。
公式Anthropic一覧への審査掲載はしていません。

## 4. Codexのローカル／リポジトリマーケットプレイス

```sh
codex plugin marketplace add /ABS/EXTRACTED/jev-ai-scrum-master
# 公開後: codex plugin marketplace add OWNER/jev-ai-scrum-master
```

対応するプラグイン画面で「Jev Development Tools」→「Jev AI Scrum Master」を追加。
`.agents/plugins/marketplace.json`とportable `plugin.json`を同梱しています。
利用中の版でこの機能が使えなければ、`npx skills ... -a codex`を利用します。
公式のuniversal public directoryへの掲載は別の公開手続きです。

## 5. 追加後の初回セットアップ

ホストを再読み込みし、次のように依頼します。

> jev-scrum-masterを使いたい。このプロジェクトで使えるようにセットアップして。

Skillは自分のインストール先を見つけ、ランチャーで準備内容を確認します。本人の了承後に
専用Python環境へ同梱CLIと依存関係を導入。手動clone・venv有効化・pip入力・MCP設定は標準導線では不要です。

**前提**：GitとPython 3.12以上。ランチャーはPython 3.9以上で動く構文です。
適したPythonがない場合、導入済みのuvと明示的な同意で新しいPythonを用意できます。
Python/uv/Nodeがなければ別途導入が必要。OSのパッケージマネージャを無断実行しません。
Linuxローカルで確認。macOS実機未確認、ネイティブWindows/Coreは非対応のalphaです。

初回に確認するのは、依存関係取得、プロジェクト設定の初期化、実際のテストコマンド、Jevの利用有無です。
Jev APIキーは`TYPESAFE_API_KEY`へ本人が設定し、チャット・Skill・Gitへ貼りません。
コード／ログの送信範囲を説明し、SDK導入だけでは外部送信を有効にしません。初期状態は無効。
セットアップ同意はタスクの計画承認とは別です。自動の独立AIレビューは引き続き未実装です。

## 6. 初回起動の内部処理

Skill内部にCLI wheelを入れ、SHA-256と版をmanifestに記録。不一致なら停止します。
ハッシュは不一致検出であり発行者署名ではありません。信頼する配布元から導入してください。
`status`、`setup`（`--write`なし）は読み取り専用。`exec`は導入・更新をしません。
ネットワーク導入は`setup --write --allow-downloads`、オフライン導入は`--wheelhouse`を使います。
依存パッケージは範囲指定であり、完全固定・署名済みの供給経路ではありません。
実行環境はプロジェクト外で、版・wheel内容・SDK有無ごとに分離します。
更新で配布物が変われば新環境の準備確認を行います。古い環境・タスク状態は自動削除しません。

## 7. 更新・削除

導入と同じ経路を使います。1ホストにmarketplace版とskills.sh版を二重導入しないでください。

```sh
npx skills list
npx skills update jev-scrum-master
npx skills remove jev-scrum-master
```

上流更新はSkillファイルを置き換えることがあります。個別編集は事前に退避し、独自変更はforkで管理します。
旧`jev-sm skill install`をskills.sh管理の配置先へ重ねません。Skill削除はタスク履歴・証拠・
Python環境・資格情報の削除ではありません。

## 8. 公開・検証

`python scripts/build_marketplace.py`でwheelを同梱、`python scripts/validate_distribution.py`で整合性を確認。
`python scripts/smoke_skills_install.py`は実npx試験のプレビュー。npm取得は明示実行します。

```sh
python scripts/smoke_skills_install.py --skills-version 1.7.0 --agent cursor --write --allow-downloads
```

`1.7.0`は調査時の上流ソースの版。今回npm取得は未確認のため実試験前に公開状況を確認します。
試験は一時プロジェクト・一時HOMEを使い、配置・wheel保持・ランチャープレビューを確認します。
実ホスト・Jev・品質改善までは測りません。手動起動のCIにも同じ試験を用意しています。
GitHub公開用スクリプトはリポジトリ作成と未マージPRまでです。配布前にPRを確認・反映し、
別環境で公開URLの導入を確認します。skills.shの検索掲載を保証・偽装しません。

## 一次資料（2026-09-23確認）

- https://skills.sh/docs/cli
- https://github.com/vercel-labs/skills
- https://github.com/vercel-labs/skills/blob/main/src/installer.ts
- https://code.claude.com/docs/en/plugin-marketplaces
- https://developers.openai.com/plugins/build/plugins
