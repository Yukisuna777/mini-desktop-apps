# mini-tools

Python + PyQt6 製の小さなデスクトップ常駐ツール集。OBSのウィンドウキャプチャで配信オーバーレイとして使うものが中心。

## 構成

```
mini-tools/
├── requirements.txt      # 共通依存パッケージ
├── common/               # 共通ユーティリティ
└── apps/
    └── cockpit-overlay/  # キー・マウス入力可視化オーバーレイ
```

## セットアップ

```bash
pip install -r requirements.txt
```

## アプリ一覧

### cockpit-overlay

画面下部に透過表示されるコックピット風UI。
- 左：キー入力に反応するボタンパネル（Q/W/E/R, A/S/D/F, Z/X/C/V, Space）
- 右：マウス移動に連動する操縦レバー

```bash
python apps/cockpit-overlay/main.py
```
