# 🗜️ HTML圧縮ツール

社内用のHTML圧縮ツールです。メルマガHTML等の容量を削減します。

## 🚀 使い方

https://html-compressor-xxxxx.streamlit.app にアクセス

1. HTMLコードを貼り付け（またはファイルアップロード）
2. 圧縮レベルを選択（**Smart版推奨**）
3. 「🚀 圧縮を実行」をクリック
4. ダウンロード

## 📊 圧縮率

| レベル | 削減率 | 用途 |
|--------|--------|------|
| ヘッダーのみ | 18% | デバッグ用 |
| **Smart版** | **37%** | **メルマガ・推奨** |
| Aggressive | 37% | 本番環境 |
| 完全圧縮 | 38% | 最小化 |

## 💡 推奨設定

メルマガHTML → **Smart版**（37%削減、可読性も維持）

## ⚙️ ローカル起動

```bash
pip install streamlit
streamlit run html_compressor.py
```

## 📄 ライセンス

社内利用のみ
