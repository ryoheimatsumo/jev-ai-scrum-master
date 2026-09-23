# ホスト連携

[English](README.md)

通常は[Skill導入](../docs/DISTRIBUTION.ja.md)と[クイックスタート](../docs/QUICKSTART.ja.md)を使います。
1ホストでは1つの経路から導入します。ホスト別のディレクトリへ配置できても、実行できる保証にはなりません。
ローカルシェル、Git、CLIの実行環境が必要です。

## 任意のMCP

ソースcheckoutの環境で実行します。

```sh
python -m pip install -e '.[mcp]'
jev-sm --repo /ABS/PROJECT serve
```

[Codexの設定例](codex/config.example.toml)または[Claude Codeの設定例](claude-code/mcp.example.json)を確認し、
絶対パスのプレースホルダーを実際の値に置き換えます。Gitに保存する設定へ秘密値を入れないでください。
1サーバーが対象にするのは1つのローカルGit作業ツリーであり、遠隔チーム向けサービスではありません。

CLIとMCPはCore、SQLite、助言キャッシュを共有します。CLIの検証は終了まで待機し、MCPは
サーバーが処理を所有したままジョブIDを返します。状態変更を新しいキーで再送したり、同じタスクの状態保存先を
切り替えたりしないでください。MCPには人間承認のツールを公開していません。

SkillもMCPも、ホストやGitの全行動を捕捉しません。自動Hook、権限拡張、独立AIレビューは導入しません。
[構成](../docs/ARCHITECTURE.ja.md) · [安全性](../SECURITY.ja.md)。
