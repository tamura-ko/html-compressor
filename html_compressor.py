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
        "4️⃣ 完全圧縮",
        "5️⃣ インデント保持版",
        "6️⃣ ハイブリッド版（推奨★）"
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

**インデント保持版**
- 階層構造（>の形）を保持
- 左側の余分なスペースのみ削除
- 可読性重視（圧縮効果は低め）

**ハイブリッド版（推奨★）**
- `<head>`→完全圧縮（CSS等）
- `<body>`→インデント保持
- 圧縮効果と可読性を両立
""")


# --- ヘルパー関数群（安全な改行挿入ロジック） ---

def split_line_safely(line: str, max_bytes: int) -> list:
    """
    1行が長い場合に、タグの区切り目（>）で安全に分割する。
    クォート内の > は無視するロジックを実装。
    """
    if len(line.encode('utf-8')) <= max_bytes:
        return [line]

    result_lines = []
    current_start = 0
    line_len = len(line)
    
    # 状態管理用
    in_quote = False
    quote_char = ''
    
    # 前回の安全な分割ポイント（タグの閉じ括弧 > の直後）
    last_safe_split_index = -1
    
    i = 0
    while i < line_len:
        char = line[i]
        
        # クォートの処理（属性値の中の > で切らないようにする）
        if char in ('"', "'"):
            if not in_quote:
                in_quote = True
                quote_char = char
            elif char == quote_char:
                in_quote = False
        
        # タグの区切り目（>）を探す（クォート外のみ）
        if char == '>' and not in_quote:
            # ここは安全に切れる場所
            last_safe_split_index = i + 1
        
        # 現在のチャンクのバイト数を確認
        current_chunk = line[current_start:i+1]
        chunk_bytes = len(current_chunk.encode('utf-8'))
        
        # 制限を超えそうになったら分割を実行
        if chunk_bytes > max_bytes:
            # 安全な分割ポイントが見つかっている場合
            if last_safe_split_index > current_start:
                result_lines.append(line[current_start:last_safe_split_index])
                current_start = last_safe_split_index
                
                # インデックスを戻す必要はないが、次のループのために調整
                # (last_safe_split_index から再開しているので i はその先へ進める)
                i = current_start - 1 # ループの最後で +1 されるので
            else:
                # 安全な場所がない（巨大な1つのタグやテキスト）
                # 仕方ないので強制的に現在の位置で切る（文字化け回避のため文字単位）
                # ただし、最後の1文字を追加するとオーバーするので、1文字手前で切る
                split_pos = i
                result_lines.append(line[current_start:split_pos])
                current_start = split_pos
                i -= 1 # 同じ文字を次の行で再処理
            
            # 分割ポイントをリセット
            last_safe_split_index = -1
            
        i += 1
    
    # 残りの部分を追加
    if current_start < line_len:
        result_lines.append(line[current_start:])
        
    return result_lines


def insert_line_breaks_for_activecore(html: str, max_bytes: int = 800) -> str:
    """
    アクティブコア対応（最終版）：
    既存の改行構造を維持しつつ、800バイトを超える行だけを処理する。
    """
    # まず既存の行に分ける（Smart版などの整形を壊さないため）
    original_lines = html.split('\n')
    processed_lines = []
    
    for line in original_lines:
        # 行末の空白除去（不具合防止）
        line = line.rstrip()
        if not line:
            continue
            
        # バイト数チェック
        if len(line.encode('utf-8')) <= max_bytes:
            # 制限内ならそのまま（ここが重要！余計な詰め込みをしない）
            processed_lines.append(line)
        else:
            # 制限オーバーの行だけ、安全に分割して追加
            splitted = split_line_safely(line, max_bytes)
            processed_lines.extend(splitted)
            
    return '\n'.join(processed_lines)


# --- 圧縮ロジック関数群 ---

def compress_header_only(html: str) -> str:
    """ヘッダーのみ圧縮"""
    head_match = re.search(r'<head>(.*?)</head>', html, re.DOTALL | re.IGNORECASE)
    if not head_match:
        return html
    head_content = head_match.group(1)
    compressed_head = re.sub(r'\s+', ' ', head_content)
    compressed_head = re.sub(r'>\s+<', '><', compressed_head)
    compressed_head = compressed_head.strip()
    result = html.replace(head_match.group(0), f'<head>{compressed_head}</head>')
    return result

def compress_smart(html: str) -> str:
    """Smart版圧縮 - 適度な圧縮"""
    result = html
    # コメント削除（条件付きコメントは残す）
    result = re.sub(r'', '', result, flags=re.DOTALL)
    # 複数の空白を1つに
    result = re.sub(r'[ \t]+', ' ', result)
    # タグ間の改行を削除（ただし、preタグ内は除く簡易実装）
    # Smart版は可読性を残すため、あえて >\n< をすべて >< にはしない
    # 行頭・行末の空白削除のみ行う
    result = '\n'.join(line.strip() for line in result.split('\n'))
    # 空行を削除
    result = re.sub(r'\n\s*\n', '\n', result)
    return result.strip()

def compress_aggressive(html: str) -> str:
    """Aggressive版 - 積極的な圧縮"""
    result = html
    result = re.sub(r'', '', result, flags=re.DOTALL)
    result = result.replace('\n', '')
    result = result.replace('\r', '')
    result = result.replace('\t', '')
    result = re.sub(r' +', ' ', result)
    result = re.sub(r'>\s+<', '><', result)
    # 属性値前後の不要なスペース削除（破壊的変更に注意）
    result = re.sub(r'\s*=\s*', '=', result)
    return result.strip()

def compress_complete(html: str) -> str:
    """完全圧縮 - 最大限の圧縮"""
    result = html
    result = re.sub(r'', '', result, flags=re.DOTALL)
    result = re.sub(r'\s+', ' ', result)
    result = re.sub(r'>\s+<', '><', result)
    result = re.sub(r'\s*=\s*', '=', result)
    result = re.sub(r'\s+>', '>', result)
    result = re.sub(r'<\s+', '<', result)
    result = re.sub(r';\s+', ';', result)
    result = re.sub(r',\s+', ',', result)
    return result.strip()

def compress_preserve_indent(html: str) -> str:
    """インデント保持版 - 階層構造を保ちつつ左側の余分なスペースを削除"""
    lines = html.split('\n')
    
    # 各行の先頭スペース数を測定
    indent_levels = []
    for line in lines:
        if line.strip():  # 空行でない場合
            leading_spaces = len(line) - len(line.lstrip())
            indent_levels.append(leading_spaces)
    
    # 最小インデントレベルを取得（全体を左寄せするための基準）
    min_indent = min(indent_levels) if indent_levels else 0
    
    # 各行を処理
    result_lines = []
    for line in lines:
        if not line.strip():  # 空行はスキップ
            continue
        
        # 現在の行のインデントレベル
        current_indent = len(line) - len(line.lstrip())
        
        # 最小インデントを引いた相対インデント（ただし2スペース単位に正規化）
        relative_indent = current_indent - min_indent
        normalized_indent = (relative_indent // 2) * 2  # 2スペース単位に正規化
        
        # 新しい行を作成（相対インデント + 内容）
        new_line = ' ' * normalized_indent + line.lstrip()
        result_lines.append(new_line)
    
    return '\n'.join(result_lines)

def compress_hybrid(html: str) -> str:
    """ハイブリッド版 - ヘッダーは完全圧縮、ボディはインデント保持"""
    # <head>と<body>を分離
    head_match = re.search(r'(<head>.*?</head>)', html, re.DOTALL | re.IGNORECASE)
    body_match = re.search(r'(<body.*?>.*?</body>)', html, re.DOTALL | re.IGNORECASE)
    
    if not head_match and not body_match:
        # head/bodyがない場合は全体をインデント保持で処理
        return compress_preserve_indent(html)
    
    # 各パーツを抽出
    before_head = html[:head_match.start()] if head_match else ""
    head_content = head_match.group(1) if head_match else ""
    between = html[head_match.end():body_match.start()] if (head_match and body_match) else ""
    body_content = body_match.group(1) if body_match else ""
    after_body = html[body_match.end():] if body_match else ""
    
    # ヘッダーは完全圧縮（ゴリゴリ削る）
    if head_content:
        compressed_head = re.sub(r'<!--(?!\[if).*?-->', '', head_content, flags=re.DOTALL)
        compressed_head = re.sub(r'\s+', ' ', compressed_head)
        compressed_head = re.sub(r'>\s+<', '><', compressed_head)
        compressed_head = re.sub(r'\s*=\s*', '=', compressed_head)
        head_content = compressed_head.strip()
    
    # ボディはインデント保持
    if body_content:
        body_content = compress_preserve_indent(body_content)
    
    # 結合
    result_parts = []
    if before_head.strip():
        result_parts.append(before_head.strip())
    if head_content:
        result_parts.append(head_content)
    if between.strip():
        result_parts.append(between.strip())
    if body_content:
        result_parts.append(body_content)
    if after_body.strip():
        result_parts.append(after_body.strip())
    
    return '\n'.join(result_parts)

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


# --- メインエリア ---
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📥 入力")
    input_method = st.radio("入力方法を選択", ["テキスト入力", "ファイルアップロード"], horizontal=True)
    html_input = ""
    
    if input_method == "テキスト入力":
        html_input = st.text_area("HTMLコードを貼り付けてください", height=400, placeholder="<!DOCTYPE html>\n<html>...")
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
        if st.button("🚀 圧縮を実行", type="primary", use_container_width=True):
            with st.spinner("圧縮中..."):
                # 1. まず圧縮
                if "ヘッダーのみ" in compression_level:
                    compressed = compress_header_only(html_input)
                elif "Smart版" in compression_level:
                    compressed = compress_smart(html_input)
                elif "Aggressive版" in compression_level:
                    compressed = compress_aggressive(html_input)
                elif "インデント保持版" in compression_level:
                    compressed = compress_preserve_indent(html_input)
                elif "ハイブリッド版" in compression_level:
                    compressed = compress_hybrid(html_input)
                else:
                    compressed = compress_complete(html_input)
                
                # 2. その後、アクティブコア制限を適用（既存の改行は極力維持）
                if activecore_mode:
                    compressed = insert_line_breaks_for_activecore(compressed, max_bytes)
                
                st.session_state['compressed_html'] = compressed
                st.session_state['original_html'] = html_input
        
        if 'compressed_html' in st.session_state:
            compressed = st.session_state['compressed_html']
            original = st.session_state['original_html']
            orig_size, comp_size, reduction, ratio = calculate_compression_ratio(original, compressed)
            
            st.success("✅ 圧縮完了！")
            metric_col1, metric_col2, metric_col3 = st.columns(3)
            with metric_col1: st.metric("元のサイズ", f"{orig_size:,} bytes")
            with metric_col2: st.metric("圧縮後", f"{comp_size:,} bytes", delta=f"-{reduction:,} bytes")
            with metric_col3: st.metric("圧縮率", f"{ratio:.1f}%")
            
            if activecore_mode:
                violations, lines = check_line_byte_limits(compressed, max_bytes)
                if violations:
                    st.warning(f"⚠️ {len(violations)}行が{max_bytes}バイトを超えています")
                    with st.expander("詳細"):
                         for ln, b, t in violations: st.text(f"行{ln}: {b}B - {t}")
                else:
                    st.success(f"✅ 全行 {max_bytes}バイト以内です")
                st.info(f"📊 総行数: {len(lines)}行")
            
            with st.expander("📄 圧縮後のHTML", expanded=True):
                st.code(compressed[:1000] + "...", language="html")
            
            filename_suffix = "_ac" if activecore_mode else ""
            st.download_button(
                label=f"💾 ダウンロード{'（AC対応）' if activecore_mode else ''}",
                data=compressed.encode('utf-8'),
                file_name=f"compressed{filename_suffix}.html",
                mime="text/html",
                use_container_width=True
            )
            st.text_area("コピー用", value=compressed, height=150)
    else:
        st.info("👈 左側にHTMLを入力してください")

st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray; font-size: 0.9em;'>
    <p>💡 <b>Tips:</b> 「Smart版」+「アクティブコアモード」の組み合わせが最もバランスが良くおすすめです。</p>
    <p>📤 <b>アクティブコアモード:</b> 800バイトを超える行のみ、タグの区切り目で安全に改行します。</p>
</div>
""", unsafe_allow_html=True)
