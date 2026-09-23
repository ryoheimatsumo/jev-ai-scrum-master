# GitHubへ公開する — 0.1.0a3

公開先は `ryoheimatsumo/jev-ai-scrum-master`、可視性は **Public**、初期ブランチは **main**。
この文書・配布ZIPがあるだけでは公開済みではありません。実際の公開操作は利用者の端末で行います。

## 手順

新しい公開用ZIPを展開してください。通常の開発用ZIPとは異なり、過去のhistory.bundleは含めません。
公開用スクリプトはPython 3.9以上とGit、GitHub CLIを使い、Coreや追加Pythonパッケージの導入は不要です。

MacでHomebrewを利用している場合、GitHub CLIがなければ導入します。

```sh
brew install gh
```

GitHub CLIを `ryoheimatsumo` で認証します。ブラウザーの本人確認を使い、トークンをチャットに貼らないでください。
GitHub Actions設定もpushするため、ブラウザー認証の追加スコープにworkflowを指定します。

```sh
gh auth login --hostname github.com --git-protocol https --web --scopes workflow
```

展開した `jev-ai-scrum-master-github-public` フォルダへ移動し、公開します。

```sh
cd /実際の展開先/jev-ai-scrum-master-github-public
bash scripts/publish-github.sh --public
```

対象が一致するか確認したい場合、`--public`の代わりに`--preview`を指定します。
プレビューはネットワークアクセスもアップロードも行いません。

## 実行する内容

宣言済みファイルのハッシュ、Skill本体とCLI wheel、配布設定を照合します。
GitHubのログイン先がryoheimatsumoであること、新規作成先が存在しないことを確認します。
最新のソース・Skill・マーケットプレイス設定・テスト・文書を別の一時フォルダにコピーし、
新しいmainの初期コミットを作成します。過去の開発Git履歴は公開しません。
Publicリポジトリを作成してmainをpushし、公開状態・既定ブランチ・コミットSHAを読み返して確認します。
READMEだけをmainに置いて実装を未マージPRへ残す方式ではありません。

公開対象の一覧は`PUBLICATION_MANIFEST.json`です。リスト外の追加ファイルは送信しません。
記載済みファイルが変わった場合も停止します。.git、.env、秘密鍵、ローカルDBは含めません。
同梱.env.exampleの値はプレースホルダーです。ハッシュは署名ではなく、秘密情報検出も完全な監査ではありません。

認証情報をスクリプトに直書きしません。Gitの認証ヘルパー・コミット設定は新しいコピー内のみで設定します。
元の作業フォルダやグローバルのGit設定は変更しません。
コミットメールはGitHubのnoreply形式です。

## 公開後の導入

公開成功の表示を確認してから、次をユーザーへ案内します。

```sh
npx skills add ryoheimatsumo/jev-ai-scrum-master --skill jev-scrum-master
```

Cursorへの指定例：

```sh
npx skills add ryoheimatsumo/jev-ai-scrum-master --skill jev-scrum-master --agent cursor
```

Claude Codeの会話入力欄では：

```text
/plugin marketplace add ryoheimatsumo/jev-ai-scrum-master
/plugin install jev-ai-scrum-master@jev-dev-tools
```

これはリポジトリを導入元として共有する方法です。公式ストアの審査・掲載ではありません。
同じホストへnpx版とプラグイン版を両方入れないでください。
Skill配置後のPython環境・テストコマンドの設定、任意のJev APIキーと外部送信同意は別です。

## 途中で止まった場合

既存リポジトリの内容・公開設定を自動で上書きすることはありません。
作成後にpushが失敗した場合、空のリポジトリが残ることがあります。スクリプトが表示する
一時フォルダを保存し、GitHub側の状態を確認してください。スクリプトを再実行しても、既存リポジトリは変更しません。

workflowスコープ不足でpushが拒否された場合：

```sh
gh auth refresh --hostname github.com --scopes workflow
# スクリプトが表示した、mainを持つローカルコピーでのみ再試行
git -C /表示された一時フォルダ/jev-ai-scrum-master push --set-upstream origin main
gh repo edit ryoheimatsumo/jev-ai-scrum-master --default-branch main
```

ネットワーク・権限・既存ブランチを確認せず、force-pushや削除を実行しないでください。

## 公開後の確認

GitHub Actionsが成功したかを確認し、失敗を隠さず修正します。
未使用プロジェクトで実際のnpx導入を試し、ホストでSkillが認識されるか確認します。
実Jev API、各ホスト実機、macOS動作、速度・精度・トークン削減は、この公開処理で実証されません。
ラベルはexperimental alphaのままです。公開用処理はnpm/PyPI登録、リリース作成、公式ストア申請を行いません。

## 確認した公式資料

- GitHub CLI repo create: https://cli.github.com/manual/gh_repo_create
- GitHub CLI auth login: https://cli.github.com/manual/gh_auth_login
- Vercel Agent Skills CLI: https://github.com/vercel-labs/skills

この公開補助コードは外部接続を置き換えたローカルテストで確認します。実GitHubへの書き込みは未実施です。
