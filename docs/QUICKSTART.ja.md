# クイックスタート

[English](QUICKSTART.md)

対象は`0.1.0a5`です。信頼できるローカルGitリポジトリ、Git、Python 3.12以上を用意します。
Linuxはローカルテスト済みですが、macOSと実際のエージェントセッションは未検証です。ネイティブWindowsは対象外です。

## 1. Skillを導入する

開発したいプロジェクトのGitルートで実行します。

```sh
npx skills add ryoheimatsumo/jev-ai-scrum-master --skill jev-scrum-master
```

導入先ホストを選択します。インストーラーにはNode/npmとレジストリへの接続が必要です。
1ホストに複数経路で重複導入しないでください。[導入方法の詳細](DISTRIBUTION.ja.md)。

## 2. セットアップを依頼する

必要に応じてホストを再読み込みし、次のように依頼します。

> jev-scrum-masterを、このリポジトリで使えるようにセットアップして。

Skillが自分のランチャーを見つけ、準備内容を表示し、依存関係のダウンロード前に確認します。
CLI専用の環境はプロジェクト外に作成します。CoreにはPython 3.12以上が必要です。
ランチャーはPython 3.9以上で開始でき、導入済みのuvがある場合は、ダウンロードへの同意後に
新しいPythonを取得する経路も使えます。システムツールの導入やホスト権限の変更は黙って行いません。

Jevは別途設定するまで無効です。APIキーをチャットやGitへ貼らないでください。
セットアップへの同意と、開発タスクの承認は別です。

## 3. 実際の検証コマンドを登録する

`.jev-sm/config.yaml`を確認します。既にpytestを使っているプロジェクトの例です。

```yaml
schema_version: 1
checks:
  unit:
    argv: [python, -m, pytest, -q, --junitxml=.jev-sm-output/unit.xml]
    kind: test
    parser: junit
    report_path: .jev-sm-output/unit.xml
    timeout_seconds: 600
    min_tests: 1
    output_limit_bytes: 262144
dod_check_ids: []
jev_enabled: false
```

すべてのリポジトリに適したコマンドではありません。実際に使うPython実行ファイルと、導入済みの
テスト依存関係を使ってください。Runnerがテスト依存関係をインストールすることはありません。
受け入れ基準にはチェックと正確なケースIDを対応付けます。チェックを定義しただけでは、
全基準の証拠にはなりません。共通の必須チェックは`dod_check_ids`に登録します。

## 4. 依頼全体の成果を伝える

> jev-scrum-masterを使って、項目を変更して保存し、開き直しても保存した値が表示されるようにして。

エージェントが依頼全体のユーザーストーリー、対象範囲、受け入れ基準、チェック、副作用を
読みやすい計画カードにまとめます。現行カードを確認してチャットで明示的に承認すると、
エージェントがプレビューのハッシュを使って計画承認を記録できます。ターミナル承認も選べます。
その後は価値ごとの小さな単位で進め、単位ごとの計画承認は求めません。範囲や基準の重要な変更は
再確認します。

実装後はチェックを実行し、不足する証拠を確認します。このα版のstandardタスクには、
人間による代替レビューも必要です。エージェントの申告だけでなく、assertionと証拠を確認してください。
自動の独立AIレビューは未実装です。

## 5. 完了の確認・再開

以下はCLIの書式であり、そのまま実行する一連の手順ではありません。TASKは実際に返されたIDに置き換え、
セットアップで選んだランチャーまたはCLI実行ファイルを使います。

```sh
jev-sm --repo /ABS/PROJECT status TASK
jev-sm --repo /ABS/PROJECT gate TASK
jev-sm --repo /ABS/PROJECT report TASK
```

`gate`の終了コードは、0＝条件充足、2＝未充足・確認待ち、3＝証拠失効、4＝エラーです。
一般のコマンドの終了コード0は「結果を返した」だけで、テスト合格を意味しません。
DONEは現行タスク契約に対するローカルの検証状態であり、マージ・デプロイ・正しさの保証ではありません。
コード・設定・基準を変更した後は状態を再確認し、必要な再承認・再検証を行います。

過去のIDは`tasks`で調べます。検証中にプロセスが強制終了した場合は記録を保全し、
完了扱いにするためにDBや回数を直接変更しないでください。[既知の制限](IMPLEMENTATION_STATUS.ja.md)。

## 任意：ソースからCLIを導入する

開発者やCLIを手動管理する場合は、ソースを取得して仮想環境へ導入できます。

```sh
git clone https://github.com/ryoheimatsumo/jev-ai-scrum-master.git
cd jev-ai-scrum-master
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
jev-sm --repo /ABS/PROJECT skill install --host codex
jev-sm --repo /ABS/PROJECT skill install --host codex --write
jev-sm --repo /ABS/PROJECT init --write
jev-sm --repo /ABS/PROJECT doctor
```

ローカルインストーラーでClaude Codeを指定する値は`--host claude`です。上流インストーラーの
`-a claude-code`とは異なります。最初のSkillコマンドはプレビュー、`--write`は反映です。
エージェントが環境を引き継げない場合はCLIの絶対パスを使います。skills管理の配置先へ重ねて導入しないでください。
ユーザー単位の配置は`--scope user`、未編集の管理対象の更新は`--update --write`を使います。

[Jevの設定](JEV.ja.md) · [CLI契約・英語原本](../skills/jev-scrum-master/references/cli.md) · [安全性](../SECURITY.ja.md)。
