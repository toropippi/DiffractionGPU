# HSP With Codex

このリポジトリで HSP を Codex と一緒に安全に編集するための運用メモ。
今後ルールが増える前提で、まずは「壊しやすい場所」と「分割の境界」を固定する。

## 目的

- `Step1_StarBurst.hsp` は GPU 計算本体に寄せる
- CLI、パラメータ解決、スペクトル生成、入出力補助は別ファイルへ逃がす
- HSP の include 順・実行順・未初期化変数まわりで事故らないようにする
- Codex が編集しても崩れにくい構造にする

## 現在の役割分担

- `Step1_StarBurst.hsp`
  GPU 計算本体、OpenCL JIT コンパイル、回折計算、加算、bin 保存、Python 起動
- `Step1_ParamsAndSpectrum.as`
  CLI 引数解析、デフォルト解決、出力名生成、`spec`/`specvals`/`specfile`、`lint` 生成
- `postprocess.py`
  bin 読み込み、可視化用露出、`png`/`exr` 保存、bin 削除
- `StarBurst.cl`
  OpenCL カーネル本体
- `col390to830.hsp`
  等色関数テーブル

## 最重要ルール

1. `#const` は、それを使う include より前に置く。
2. include ファイルの先頭には実行飛ばし用 `goto` を置く。
3. `Step1_StarBurst.hsp` に長い補助ロジックを書かない。
4. CLI 追加時は、デフォルト値を本体側で先に初期化する。
5. OpenCL の `-D` に渡す値は、HSP 側 `#const` でなく通常変数でもよい。

## HSP 固有の注意

### include は「結合」

HSP の `#include` はモジュール import ではなく、実質的にソース結合に近い。
そのため、以下が起こる。

- include 順に依存する
- `#const` 定義順に依存する
- include 先頭が通常文だとそのまま実行される

### include ファイルの定型

`.as` 側は必ずこの形にする。

```hsp
goto *file_end

*someHelper
    return

*file_end
```

これを崩すと、include 後に helper 本体へ処理が落ちる。

### 未初期化警告は軽視しすぎない

HSP は未初期化でも 0 扱いで進むことが多い。
その結果、

- 本当は定数が見えていない
- 配列サイズが壊れている
- `dir_cmdline` まわりが文字列として成立していない

のようなバグが「別の場所のエラー」として出る。

## ファイル分割ルール

### 本体に残してよいもの

- GPU 実行フロー
- OpenCL カーネル引数設定
- `view`
- `saveRawFloat`
- `runPostprocess`
- 色変換バッファ生成

### helper 側へ出すもの

- CLI 引数解析
- パス解決
- 出力名生成
- スペクトル定義
- `lint` 生成
- 将来の `specfile` / 数値入力処理

### 今後さらに分ける候補

- `Step1_CLI.as`
- `Step1_Spectrum.as`
- `Step1_OutputNaming.as`

`Step1_ParamsAndSpectrum.as` が大きくなったらこの3分割を優先する。

## パラメータ設計ルール

### HSP 本体に置くべきもの

- 本当に計算本体のデフォルト
- OpenCL JIT に必要な値
- 実行時に必須なバッファサイズ関連

### CLI で受けるべきもの

- `input`
- `distance`
- `gxy`
- `z0`
- `ox`
- `oy`
- `splitn`
- `spec`
- `specvals`
- `specfile`
- `tag`

### 追加時の原則

- まず本体でデフォルト値を代入する
- helper 側は「未指定なら何もしない」
- OpenCL に渡す値は最終解決後に 1 回だけ文字列化する

## スペクトル設計ルール

### 現在のモード

- `spec=<preset>`
- `specvals=v1,v2,...`
- `specfile=path.csv`

### `split_n` と `lint`

- `split_n` は「1 オクターブの波長帯を何分割するか」
- `lint` は固定配列ではなく、現在の `split_n` に応じて生成する
- `preset` と `specfile` は補間して `lint` を作る
- `specvals` は `split_n` 個をそのまま使う

### `specfile` 仕様

CSV 1 行につき:

```text
wavelength_nm,intensity
```

例:

```text
390,0.1
430,0.8
470,1.2
510,0.6
550,0.2
650,0.0
800,0.0
```

## 出力設計ルール

- HSP は raw float32 RGB を `bin` で保存
- Python は `bin` から `png` と `exr` を両方出す
- 最終出力名には Python 側の 10 桁乱数サフィックスを付ける
- HSP 側の `runStem` には条件をなるべく含める

## Codex 編集ルール

### 変更前に確認すること

- include 順
- `#const` の位置
- helper 先頭 `goto` の有無
- デフォルト値の初期化位置
- `split_n` を使う配列サイズ

### HSP を直すときの優先手順

1. まず本体か helper かを決める
2. 依存する `#const` が include より前か確認する
3. デフォルト値を先に置く
4. CLI で上書きする
5. OpenCL `-D` 文字列は最後に組む

### 触らないほうがよいもの

- 本体に helper ロジックを戻すこと
- `lint` を 다시固定長直打ちに戻すこと
- include の先頭 `goto` を消すこと
- Python 側の出力名乱数を HSP 側へ戻すこと

## 新しい helper を増やすときのテンプレート

```hsp
// helper summary
goto *my_helper_end

*someRoutine
    return

*my_helper_end
```

## 今後追加したいもの

- `Step1_CLI.as` / `Step1_Spectrum.as` / `Step1_OutputNaming.as` への再分割
- `specfile` のバリデーション強化
- `specvals` の短縮記法
- 複数条件バッチ実行用の Python ランナー
- 実行ログ保存

## 変更履歴メモ

- 2026-04-09
  `Step1_StarBurst.hsp` から CLI/スペクトル処理を分離
- 2026-04-09
  `spec` を preset + `specvals` + `specfile` の3方式に拡張
- 2026-04-09
  Python 後段を `png` + `exr` 同時出力、10桁乱数サフィックスに変更
