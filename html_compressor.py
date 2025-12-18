import streamlit as st
import re
from io import BytesIO

# ==========================================
# 1. ページ設定とUI
# ==========================================
st.set_page_config(page_title="HTML圧縮ツール", layout="wide", page_icon="🗜️")

st.title("🗜️ HTML圧縮ツール")
st.markdown("HTMLファイルを最適化します。MAツール制限（1行800バイト）にも対応。")

# --- サイドバー設定 ---
st.sidebar.header("⚙️ 設定")

compression_level = st.sidebar.radio(
    "圧縮レベルを選択",
    [
        "1️⃣ ヘッダーのみ圧縮",
        "2️⃣ Smart版（推奨）",
        "3️⃣ Aggressive版",
        "4️⃣ 完全圧縮",
        "5️⃣ 整形モード（インデント最適化）"
    ]
)

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

st.sidebar.markdown("---")
st.sidebar.subheader("📖 圧縮レベルの違い")
st.sidebar.markdown("""
**ヘッダーのみ圧縮**
- `<head>`内のみ圧縮、他はそのまま

**Smart版（推奨）**
- 適度に圧縮、可読性を維持

**Aggressive版**
- コメント削除、改行削除

**完全圧縮**
- 全ての不要な空白削除、最小サイズ

**整形モード**
- 余分なインデントを削除して軽量化
- 階層構造（＞の形）を維持
""")


# ==========================================
# 2. ロジック関数群（インデントエラー対策済み）
# ==========================================

def split_line_safely(line: str, max_bytes: int) -> list:
    """1行が長い場合に、タグの区切り目（>）で安全に分割する"""
    if len(line.encode('utf-8')) <= max_bytes:
        return [line]

    result_lines = []
    current_start = 0
    line_len = len(line)
    
    in_quote = False
    quote_char = ''
    last_safe_split_index = -1
    
    i = 0
    while i < line_len:
        char = line[i]
        # クォート管理
        if char in ('"', "'"):
            if not in_quote:
                in_quote = True
                quote_char = char
            elif char == quote_char:
                in_quote = False
        
        # 安全な改行ポイント（>）を探す
        if char == '>' and not in_quote:
            last_safe_split_index = i + 1
        
        current_chunk = line[current_start:i+1]
        chunk_bytes = len(current_chunk.encode('utf-8'))
        
        if chunk_bytes > max_bytes:
            if last_safe_split_index > current_start:
                result_lines.append(line[current_start:last_safe_split_index])
                current_start = last_safe_split_index
                i = current_start - 1
            else:
                # 安全な場所がない場合は強制分割
                split_pos = i
                result_lines.append(line[current_start:split_pos])
                current_start = split_pos
                i -= 1
            last_safe_split_index = -1
        i += 1
    
    if current_start < line_len:
        result_lines.append(line[current_start:])
        
    return result_lines


def insert_line_breaks_for_activecore(html: str, max_bytes: int = 800) -> str:
    """アクティブコア対応：800バイトを超える行だけを処理する"""
    original_lines = html.split('\n')
    processed_lines = []
    
    for line in original_lines:
        line_clean = line.rstrip() 
        if not line_clean:
            continue
            
        if len(line_clean.encode('utf-8')) <= max_bytes:
            processed_lines.append(line_clean)
        else:
            splitted = split_line_safely(line_clean, max_bytes)
            processed_lines.extend(splitted)
            
    return '\n'.join(processed_lines)


def format_html_structure(html: str) -> str:
    """HTMLの構造を解析し、インデントを再構築する（整形モード）"""
    # 構造を単純化してインデントエラーを防ぐ
    tokens = re.split(r'(<[^>]+>)', html)
    tokens = [t.strip() for t in tokens if t.strip()]
    
    formatted_lines = []
    indent_level = 0
    indent_unit = "  " # スペース2個
    
    # インデントを下げないタグ一覧
    void_tags = [
        'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 
        'link', 'meta', 'param', 'source', 'track', 'wbr', '!doctype', '?xml'
    ]
    
    for token in tokens:
        # 1. 終了タグの場合
        if token.startswith('</'):
            indent_level = max(0, indent_level - 1)
            formatted_lines.append((indent_unit * indent_level) + token)
            continue

        # 2. コメントタグの場合
        if token.startswith('', '', result, flags=re.DOTALL)
    # 空白圧縮
    result = re.sub(r'[ \t]+', ' ', result)
    # 行整形
    lines = [line.strip() for line in result.split('\n')]
    result = '\n'.join(lines)
    # 空行削除
    result = re.sub(r'\n\s*\n', '\n', result)
    return result.strip()


def compress_aggressive(html: str) -> str:
    result = html
    result = re.sub(r'', '', result, flags=re.DOTALL)
    result = result.replace('\n', '').replace('\r', '').replace('\t', '')
    result = re.sub(r' +', ' ', result)
    result = re.sub(r'>\s+<', '><', result)
    result = re.sub(r'\s*=\s*', '=', result)
    return result.strip()


def compress_complete(html: str) -> str:
    result = html
    result = re.sub(r'', '', result, flags=re.DOTALL)
    result = re.sub(r'\s+', ' ', result)
    result = re.sub(r'>\s+<', '><', result)
    result = re.sub(r'\s*=\s*', '=', result)
    result = re.sub(r'\s+>', '>', result)
    result = re.sub(r'<\s+', '<', result)
    return result.strip()


def calculate_compression_ratio(original: str, compressed: str) -> tuple:
    original_size = len(original.encode('utf-8'))
    compressed_size = len(compressed.encode('utf-8'))
    reduction = original_size - compressed_size
    ratio = (reduction / original_size * 100) if original_size > 0 else 0
    return original_size, compressed_size, reduction, ratio


def check_line_byte_limits(html: str, max_bytes: int = 800) -> tuple:
    lines = html.split('\n')
    violations = []
    for i, line in enumerate(lines, 1):
        line_bytes = len(line.encode('utf-8'))
        if line_bytes > max_bytes:
            violations.append((i, line_bytes, line[:100] + '...' if len(line) > 100 else line))
    return violations, lines


# ==========================================
# 3. メイン処理エリア
# ==========================================

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📥 入力")
    input_method = st.radio("入力方法を選択", ["テキスト入力", "ファイルアップロード"], horizontal=True)
    html_input = ""
    
    if input_method == "テキスト入力":
        html_input = st.text_area("HTMLコードを貼り付けてください", height=400, placeholder="<!DOCTYPE html>...")
    else:
        uploaded_file = st.file_uploader("HTMLファイルをアップロード", type=['html', 'htm'])
        if uploaded_file is not None:
            html_input = uploaded_file.read().decode('utf-8')
            st.success(f"✅ {uploaded_file.name} を読み込みました")
            with st.expander("📄 元のHTMLを表示"):
                st.code(html_input[:1000] + "...", language="html")

with col2:
    st.subheader("📤 出力")
    if html_input:
        if st.button("🚀 処理を実行", type="primary", use_container_width=True):
            with st.spinner("処理中..."):
                # 分岐処理
                if "ヘッダーのみ" in compression_level:
                    compressed = compress_header_only(html_input)
                elif "Smart版" in compression_level:
                    compressed = compress_smart(html_input)
                elif "Aggressive版" in compression_level:
                    compressed = compress_aggressive(html_input)
                elif "整形モード" in compression_level:
                    compressed = format_html_structure(html_input)
                else:
                    compressed = compress_complete(html_input)
                
                # アクティブコア制限
                if activecore_mode:
                    compressed = insert_line_breaks_for_activecore(compressed, max_bytes)
                
                st.session_state['compressed_html'] = compressed
                st.session_state['original_html'] = html_input
        
        # 結果表示
        if 'compressed_html' in st.session_state:
            compressed = st.session_state['compressed_html']
            original = st.session_state['original_html']
            orig_size, comp_size, reduction, ratio = calculate_compression_ratio(original, compressed)
            
            st.success("✅ 完了しました！")
            
            # メトリクス
            m1, m2, m3 = st.columns(3)
            with m1: st.metric("元のサイズ", f"{orig_size:,} bytes")
            with m2: st.metric("処理後", f"{comp_size:,} bytes", delta=f"-{reduction:,} bytes")
            with m3: st.metric("削減率", f"{ratio:.1f}%")
            
            # 制限チェック警告
            if activecore_mode:
                violations, lines = check_line_byte_limits(compressed, max_bytes)
                if violations:
                    st.warning(f"⚠️ {len(violations)}行が{max_bytes}バイトを超えています")
                    with st.expander("詳細"):
                         for ln, b, t in violations: st.text(f"行{ln}: {b}B - {t}")
                else:
                    st.success(f"✅ 全行 {max_bytes}バイト以内です")
            
            with st.expander("📄 結果のHTMLを確認", expanded=True):
                st.code(compressed[:1000] + "...", language="html")
            
            # ダウンロード
            filename_suffix = "_ac" if activecore_mode else ""
            st.download_button(
                label=f"💾 ダウンロード{'（AC対応）' if activecore_mode else ''}",
                data=compressed.encode('utf-8'),
                file_name=f"processed{filename_suffix}.html",
                mime="text/html",
                use_container_width=True
            )
            st.text_area("コピー用", value=compressed, height=150)
    else:
        st.info("👈 左側にHTMLを入力してください")
