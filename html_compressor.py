import streamlit as st
import re
from io import BytesIO

st.set_page_config(page_title="HTML圧縮ツール", layout="wide", page_icon="🗜️")

st.title("🗜️ HTML圧縮ツール")
st.markdown("HTMLファイルを4段階の圧縮レベルで最適化します。")

# サイドバーで圧縮レベル選択
st.sidebar.header("⚙️ 設定")
compression_level = st.sidebar.radio(
    "圧縮レベルを選択",
    [
        "1️⃣ ヘッダーのみ圧縮",
        "2️⃣ Smart版（推奨）",
        "3️⃣ Aggressive版",
        "4️⃣ 完全圧縮"
    ]
)

# アクティブコアモード追加
st.sidebar.markdown("---")
activecore_mode = st.sidebar.checkbox(
    "📤 アクティブコアモード",
    value=False,
    help="1行800バイト制限に対応（MAツール用）"
)

if activecore_mode:
    max_bytes = st.sidebar.number_input(
        "1行の最大バイト数",
        min_value=100,
        max_value=2000,
        value=800,
        step=50,
        help="アクティブコアは800バイト/行の制限があります"
    )
else:
    max_bytes = 800

# 説明を表示
st.sidebar.markdown("---")
st.sidebar.subheader("📖 圧縮レベルの違い")
st.sidebar.markdown("""
**ヘッダーのみ圧縮**
- `<head>`内のみ圧縮
- `<body>`は元のまま
- デバッグ時に便利

**Smart版（推奨）**
- 適度に圧縮
- 改行・スペースを削減
- ある程度の可読性を維持

**Aggressive版**
- 積極的に圧縮
- コメント削除
- 可読性より容量優先

**完全圧縮**
- 最大限に圧縮
- 全ての不要な空白削除
- 最小サイズを実現
""")


# --- ヘルパー関数群 ---

def split_string_by_bytes(s: str, limit: int) -> list:
    """文字列を指定バイト数以下で強制分割（マルチバイト文字対応）"""
    chunks = []
    current = ""
    for char in s:
        # 次の文字を足すと超えるかチェック
        if len((current + char).encode('utf-8')) > limit:
            chunks.append(current)
            current = char
        else:
            current += char
    if current:
        chunks.append(current)
    return chunks


def split_long_token(text: str, max_bytes: int) -> list:
    """
    制限を超える巨大なトークン（長い属性を持つタグなど）を
    スペース（属性の区切り）などで安全に分割するヘルパー関数
    """
    chunks = []
    current_chunk = ""
    
    # スペースで分割してみる（属性ごと、単語ごとに分けるため）
    words = re.split(r'(\s+)', text)
    
    for word in words:
        word_bytes = len(word.encode('utf-8'))
        current_chunk_bytes = len(current_chunk.encode('utf-8'))
        
        if current_chunk_bytes + word_bytes <= max_bytes:
            current_chunk += word
        else:
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""
            
            # 単語そのものが巨大な場合（長いURLやBase64など）
            if word_bytes > max_bytes:
                # 仕方ないので文字単位で強制分割
                sub_chunks = split_string_by_bytes(word, max_bytes)
                chunks.extend(sub_chunks[:-1])
                current_chunk = sub_chunks[-1]
            else:
                current_chunk = word
                
    if current_chunk:
        chunks.append(current_chunk)
        
    return chunks


def insert_line_breaks_for_activecore(html: str, max_bytes: int = 800) -> str:
    """
    アクティブコア対応（改善版）：
    HTMLのタグ構造を考慮して、可能な限りタグの区切りで改行を入れることで
    ソースコードの可読性を維持しつつバイト数制限をクリアする。
    """
    # HTMLを「タグ」と「それ以外（テキスト）」に分割する正規表現
    # (<[^>]+>) でタグ全体をキャプチャして分割リストに残す
    tokens = re.split(r'(<[^>]+>)', html)
    # 空文字を除去
    tokens = [t for t in tokens if t]
    
    lines = []
    current_line = ""
    
    for token in tokens:
        # このトークン（タグやテキスト）を追加したときのバイト数を計算
        token_bytes = len(token.encode('utf-8'))
        current_bytes = len(current_line.encode('utf-8'))
        
        # 追加しても制限内なら、そのまま連結
        if current_bytes + token_bytes <= max_bytes:
            current_line += token
        else:
            # 制限を超えるなら、今の行を確定して改行（リストに追加）
            if current_line:
                lines.append(current_line)
                current_line = ""
            
            # もしトークン単体で制限を超えている場合（巨大な画像タグや長いテキストなど）
            if token_bytes > max_bytes:
                # 特別な処理で細かく分割する
                chunks = split_long_token(token, max_bytes)
                lines.extend(chunks[:-1])
                current_line = chunks[-1]
            else:
                # 次の行の先頭にする
                current_line = token
                
    # 最後の行を追加
    if current_line:
        lines.append(current_line)
        
    return '\n'.join(lines)


# --- 圧縮ロジック関数群 ---

def compress_header_only(html: str) -> str:
    """ヘッダーのみ圧縮"""
    # headタグ内を抽出
    head_match = re.search(r'<head>(.*?)</head>', html, re.DOTALL | re.IGNORECASE)
    if not head_match:
        return html
    
    head_content = head_match.group(1)
    
    # head内を圧縮
    compressed_head = re.sub(r'\s+', ' ', head_content)
    compressed_head = re.sub(r'>\s+<', '><', compressed_head)
    compressed_head = compressed_head.strip()
    
    # 元のHTMLのheadを置き換え
    result = html.replace(head_match.group(0), f'<head>{compressed_head}</head>')
    return result


def compress_smart(html: str) -> str:
    """Smart版圧縮 - 適度な圧縮"""
    result = html
    
    # コメント削除（条件付きコメントは残す）
    result = re.sub(r'', '', result, flags=re.DOTALL)
    
    # 複数の空白を1つに
    result = re.sub(r'[ \t]+', ' ', result)
    
    # タグ間の改行を削除（ただし、preタグ内は除く）
    result = re.sub(r'>\s+<', '><', result)
    
    # 行頭・行末の空白削除
    result = '\n'.join(line.strip() for line in result.split('\n'))
    
    # 空行を削除
    result = re.sub(r'\n\s*\n', '\n', result)
    
    return result.strip()


def compress_aggressive(html: str) -> str:
    """Aggressive版 - 積極的な圧縮"""
    result = html
    
    # 全てのコメント削除
    result = re.sub(r'', '', result, flags=re.DOTALL)
    
    # 改行をすべて削除
    result = result.replace('\n', '')
    result = result.replace('\r', '')
    
    # タブを削除
    result = result.replace('\t', '')
    
    # 複数のスペースを1つに
    result = re.sub(r' +', ' ', result)
    
    # タグ間のスペース削除
    result = re.sub(r'>\s+<', '><', result)
    
    # 属性値前後の不要なスペース削除
    result = re.sub(r'\s*=\s*', '=', result)
    
    return result.strip()


def compress_complete(html: str) -> str:
    """完全圧縮 - 最大限の圧縮"""
    result = html
    
    # 全てのコメント削除
    result = re.sub(r'', '', result, flags=re.DOTALL)
    
    # 全ての改行・タブ・複数スペースを削除
    result = re.sub(r'\s+', ' ', result)
    
    # タグ間の全てのスペース削除
    result = re.sub(r'>\s+<', '><', result)
    
    # 属性の前後のスペース削除
    result = re.sub(r'\s*=\s*', '=', result)
    result = re.sub(r'\s+>', '>', result)
    result = re.sub(r'<\s+', '<', result)
    
    # セミコロンの後のスペース削除（CSS/JS用）
    result = re.sub(r';\s+', ';', result)
    
    # カンマの後のスペース削除
    result = re.sub(r',\s+', ',', result)
    
    return result.strip()


def calculate_compression_ratio(original: str, compressed: str) -> tuple:
    """圧縮率を計算"""
    original_size = len(original.encode('utf-8'))
    compressed_size = len(compressed.encode('utf-8'))
    reduction = original_size - compressed_size
    ratio = (reduction / original_size * 100) if original_size > 0 else 0
    return original_size, compressed_size, reduction, ratio


def check_line_byte_limits(html: str, max_bytes: int = 800) -> tuple:
    """
    各行のバイト数をチェックし、制限を超えている行を検出
    """
    lines = html.split('\n')
    violations = []
    
    for i, line in enumerate(lines, 1):
        line_bytes = len(line.encode('utf-8'))
        if line_bytes > max_bytes:
            violations.append((i, line_bytes, line[:100] + '...' if len(line) > 100 else line))
    
    return violations, lines


# --- メインエリア ---
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📥 入力")
    
    # 入力方法の選択
    input_method = st.radio(
        "入力方法を選択",
        ["テキスト入力", "ファイルアップロード"],
        horizontal=True
    )
    
    html_input = ""
    
    if input_method == "テキスト入力":
        html_input = st.text_area(
            "HTMLコードを貼り付けてください",
            height=400,
            placeholder="<!DOCTYPE html>\n<html>\n<head>\n  <title>Sample</title>\n</head>\n<body>\n  <h1>Hello World</h1>\n</body>\n</html>"
        )
    else:
        uploaded_file = st.file_uploader(
            "HTMLファイルをアップロード",
            type=['html', 'htm'],
            help="HTML/HTMファイルを選択してください"
        )
        
        if uploaded_file is not None:
            html_input = uploaded_file.read().decode('utf-8')
            st.success(f"✅ {uploaded_file.name} を読み込みました")
            with st.expander("📄 元のHTMLを表示"):
                st.code(html_input[:1000] + ("..." if len(html_input) > 1000 else ""), language="html")

with col2:
    st.subheader("📤 出力")
    
    if html_input:
        # 圧縮実行ボタン
        if st.button("🚀 圧縮を実行", type="primary", use_container_width=True):
            with st.spinner("圧縮中..."):
                # 圧縮レベルに応じて処理
                if "ヘッダーのみ" in compression_level:
                    compressed = compress_header_only(html_input)
                elif "Smart版" in compression_level:
                    compressed = compress_smart(html_input)
                elif "Aggressive版" in compression_level:
                    compressed = compress_aggressive(html_input)
                else:  # 完全圧縮
                    compressed = compress_complete(html_input)
                
                # アクティブコアモードの場合、800バイト制限対応
                if activecore_mode:
                    compressed = insert_line_breaks_for_activecore(compressed, max_bytes)
                
                # セッションステートに保存
                st.session_state['compressed_html'] = compressed
                st.session_state['original_html'] = html_input
        
        # 圧縮結果の表示
        if 'compressed_html' in st.session_state:
            compressed = st.session_state['compressed_html']
            original = st.session_state['original_html']
            
            # 統計情報
            orig_size, comp_size, reduction, ratio = calculate_compression_ratio(original, compressed)
            
            st.success("✅ 圧縮完了！")
            
            # メトリクス表示
            metric_col1, metric_col2, metric_col3 = st.columns(3)
            with metric_col1:
                st.metric("元のサイズ", f"{orig_size:,} bytes")
            with metric_col2:
                st.metric("圧縮後", f"{comp_size:,} bytes", delta=f"-{reduction:,} bytes")
            with metric_col3:
                st.metric("圧縮率", f"{ratio:.1f}%")
            
            # アクティブコアモードの場合、行数制限チェック
            if activecore_mode:
                violations, lines = check_line_byte_limits(compressed, max_bytes)
                
                if violations:
                    st.warning(f"⚠️ {len(violations)}行が{max_bytes}バイトを超えています")
                    with st.expander("⚠️ 制限超過の行を表示"):
                        for line_num, byte_count, preview in violations:
                            st.text(f"行{line_num}: {byte_count}バイト - {preview}")
                else:
                    st.success(f"✅ 全ての行が{max_bytes}バイト以内です！")
                
                st.info(f"📊 総行数: {len(lines)}行")
            
            # 圧縮後のHTMLプレビュー
            with st.expander("📄 圧縮後のHTMLを表示", expanded=True):
                st.code(compressed[:1000] + ("..." if len(compressed) > 1000 else ""), language="html")
            
            # ダウンロードボタン
            filename_suffix = "_ac" if activecore_mode else ""
            st.download_button(
                label=f"💾 圧縮HTMLをダウンロード{'（AC対応）' if activecore_mode else ''}",
                data=compressed.encode('utf-8'),
                file_name=f"compressed{filename_suffix}.html",
                mime="text/html",
                use_container_width=True
            )
            
            # コピーボタン用（テキストエリア）
            st.text_area(
                "クリップボードにコピー用",
                value=compressed,
                height=150,
                help="このテキストを選択してコピーできます"
            )
    else:
        st.info("👈 左側にHTMLを入力またはアップロードしてください")

# フッター
st.markdown("---")
st.markdown(f"""
<div style='text-align: center; color: gray; font-size: 0.9em;'>
    <p>💡 <b>Tips:</b> Smart版は可読性とサイズのバランスが良く、通常使用に最適です</p>
    <p>⚠️ 圧縮後は必ず動作確認を行ってください</p>
    {'<p>📤 <b>アクティブコアモード:</b> 1行800バイト制限に対応した改行を自動挿入（タグ優先分割）</p>' if activecore_mode else ''}
</div>
""", unsafe_allow_html=True)
