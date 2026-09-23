# 配布・初回起動の検証 — 0.1.0a3

2026-09-23。Linux / Python 3.13.5で実行。

## 結果

- 全体pytest: **233 passed, 3 skipped**（a2から66件追加）。ログはtests.txt / tests.xml。
- 3件は公式MCP SDK、TypeSafe SDK、明示許可が必要な実Jev API。未実行を成功に含めない。
- 配布の版・SHA-256・source/wheel一致・Skillミラー・manifest整合性: 成功。
- 12エージェントの配置先を模したディレクトリへのSkillコピーとランチャープレビュー: 成功。
  **フォルダ構成のテストであり、そのエージェントやnpxを起動した結果ではない。**
- 初回確認のread-only、同意なしdownload拒否、壊れたwheel拒否、競合・リンク拒否、秘密値を
  installer環境へ渡さないこと、再導入・移動後の再利用・任意文字列引数をshell評価しないことを確認。
- 実venv/pipで別環境へCLIを導入し、help/init/doctor/tasksを実行: 成功。
  依存wheelはこの環境の既存パッケージから組み直した**テスト専用fixture**。公式配布wheelを
  ネット取得した試験ではなく、fixture自体は配布物に含めていない。Jev SDKは未試験。
- CoreデモをSIMULATED_DEMO_ONLYとして実行。本人の承認・独立レビュー・AI性能を実証しない。
- compileall、配布validator、publishスクリプトのbash構文検査: 成功。ruffは未導入で未実行。

## 実npxの試行

`skills@1.7.0`を一時HOME・一時プロジェクトへ取得する実コマンドを試行したが、
registry.npmjs.orgの名前解決でEAI_AGAIN。**インストール成功とは表示しない。**
生の制限付き出力はnpx-attempt.json。`scripts/smoke_skills_install.py`と手動CI
`.github/workflows/distribution-smoke.yml`で接続できる環境から再試験する。

上流のREADME/ソースでnpx書式、agent ID、Skillフォルダの再帰コピーは確認した。
このことは配布物の実npxテストやホストアプリの実機試験の代わりではない。

## 未検証・未公開

オンラインPyPI依存取得、新しいPythonのuv取得、各ホストによるSkill発見・実行、
macOS、ネイティブWindows（Core非対応）、実Jev、速度・精度・トークン削減。
GitHub公開、default branchへの反映、npm/PyPI公開、公式マーケットプレイス登録・掲載も未実施。
CIファイルを用意したことと、GitHub上でCIが通ったことは区別する。

## ファイル

summary.json / distribution.json / tests.txt / tests.xml / offline-runtime-smoke.json /
npx-attempt.json / core-demo.json。元v1.0仕様とCoreの完了条件は維持。
