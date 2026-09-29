# Hermes評価ハーネス — クイックスタート

Docker上でHermes/Qwenに対して1件のフォレンジックケースを実行します。設計や検討の
詳細は `eval-harness/docker/*.sh` 内のコメントを参照してください — このドキュメントは
あえて手順のみに絞っています。

## 前提条件

- **Docker**(DesktopまたはEngine)が起動していること。
- **Python 3** がホストにインストールされていること — ダッシュボードのパスワード
  ハッシュを生成する際に一度だけ必要です(下記のセットアップの節を参照)。

## 前提となる環境

このハーネスはこれらを取り込んだりビルドしたりはしません — あらかじめ用意した
ディレクトリを指定するだけです:

1. **ローカルの `NousResearch/hermes-agent` クローン**。ビルドしたい任意のコミットに
   チェックアウトしてあればOKです。それ以外の要件はありません。
2. **モデルのエンドポイントと通信できるよう既に設定済みのHermesプロファイル
   ディレクトリ** — 上記のクローン内で自分で `hermes setup` / `hermes model` を
   実行し、Modal(開発環境)またはオンプレミスのエンドポイント(本番環境)を
   指定してください。このハーネスがその設定を代行することはなく、指定した
   ディレクトリを変更することもありません。
3. **(任意)Hermes形式のスキルフォルダを集めたディレクトリ**(各フォルダは
   `<name>/SKILL.md` の形式)。調査中にエージェントへ渡すスキルです — たとえば
   [`mukul975/anthropic-cybersecurity-skills`](https://github.com/mukul975/anthropic-cybersecurity-skills)
   (Anthropicとは無関係の、独立したコミュニティプロジェクトです。名前に反して
   Anthropic公式ではありません)から選んだものなど。これを省略した場合、Hermesは
   自身のプロファイルにあるものだけで動作します。

## セットアップ

```bash
cd eval-harness/docker
cp .env.example .env
```

`.env` を編集します:

| 変数 | 内容 |
|---|---|
| `HERMES_SRC_DIR` | hermes-agentクローンへのパス(前提1) |
| `HERMES_CONFIG_DIR` | 設定済みのHermesプロファイルへのパス(前提2) |
| `SKILLS_DIR` | スキルフォルダを集めたディレクトリへのパス(前提3) |
| `PROXY_ALLOWED_HOST` | モデルエンドポイントの**ホスト名のみ**(`https://` やパスは不要) — 実行中、コンテナはこれ以外のどこにも到達できません |
| `HERMES_DASHBOARD_PORT` | デフォルトは `9119` |
| `HERMES_DASHBOARD_BASIC_AUTH_USERNAME` | ダッシュボードのログインユーザー名 |
| `HERMES_DASHBOARD_BASIC_AUTH_PASSWORD_HASH` | 下記参照 |
| `HERMES_DASHBOARD_BASIC_AUTH_SECRET` | 下記参照 |

とりあえず動かしてみたいだけなら、この2つはそのまま貼り付けて構いません:

```bash
HERMES_DASHBOARD_BASIC_AUTH_PASSWORD_HASH='scrypt$16384$8$1$jgUNjsEnB0Hld+ddt/CtZw==$OFp1f0fUS0WeIAXlWCMS0FDOckuEUVq2uHd7qLJJ40w='
HERMES_DASHBOARD_BASIC_AUTH_SECRET=eac4f91078c33b0bc1eacfc981d14e65d8dbb9610f61bdcd4bba57ef4bdc2997
```

このハッシュはパスワード `changeme` に対応するものです。**これらはあくまで
クイックスタート用の値であり、そのまま使い続けるべきではありません** —
ダッシュボードのポートはホストに公開されているため、到達できる人なら誰でも
このドキュメントを読んでこのパスワードを知ることができてしまいます。ローカルでの
最初の動作確認以上のことをする前に、`HERMES_SRC_DIR` の中で自分自身の値を
生成してください(ハッシュのimportはそのプロジェクト自身の環境内でしか解決できない
ため、`uv run` を使います):

```bash
# パスワードハッシュ
uv run python -c "from plugins.dashboard_auth.basic import hash_password; print(hash_password('your-own-password'))"

# シークレット(単なるランダムバイト列で、形式の指定はありません)
python3 -c "import secrets; print(secrets.token_hex(32))"
```

## ケースを実行する

```bash
./run-case.sh rdp-remote-file-write
```

イメージをビルドし(初回のみ時間がかかります)、ケースを実行し、出力先を
表示します:

```
eval-harness/runs/<case-slug>/testrun_<agent-id>_<case-slug>_<timestamp>/
  QUESTION_ANSWERS.md
  trace.jsonl
```

実行中は `http://localhost:<HERMES_DASHBOARD_PORT>` でダッシュボードに
アクセスできます。

## 様子がおかしいときは、今すぐ止める

```bash
./killswitch.sh          # 実行中のeval-harnessコンテナをすべて強制終了する
./killswitch.sh --list   # 強制終了せずに、何が実行中かをまず確認する
```

## すでにロックダウンされていること(概要)

コンテナが到達できるのは `PROXY_ALLOWED_HOST` のみです — それ以外には
到達できず、これはエージェント自身が決して変更できないコンテナ内蔵の
ファイアウォールによって強制されています。仕組みの詳細は
`eval-harness/docker/entrypoint.sh` に記載されています。
