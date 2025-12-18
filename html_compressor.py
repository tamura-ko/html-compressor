import streamlit as st
import re

# ==========================================
# 1. 初期設定とUIレイアウト
# ==========================================
st.set_page_config(page_title="HTML圧縮ツール", layout="wide", page_icon="🗜️")

st.title("🗜️ HTML圧縮ツール")
st.markdown("HTMLファイルを最適化します。MAツール制限（1行800バイト）にも対応。")

# --- サイドバー ---
st.sidebar.header("⚙️ 設定")

# 圧縮モード選択
compression_mode = st.sidebar.radio(
    "処理モードを選択",
    [
        "1️⃣ ヘッダーのみ圧縮",
        "2️⃣ Smart版（推奨）",
        "3️⃣ Aggressive版",
        "4️⃣ 完全圧縮",
        "5️⃣ 整形モード（インデント最適化）"
    ]
)

st.sidebar.markdown("---")

# アクティブコア制限設定
use_activecore_limit = st.sidebar.checkbox(
    "📤 アクティブコアモード",
    value=False,
    help="1行あたりのバイト数を制限します（MAツール用）"
)

if use_activecore_limit:
    byte_limit = st.sidebar.number_input(
        "1行の最大バイト数",
        min_value=100,
        max_value=2000,
        value=800,
        step=50
    )
else:
    byte_limit = 800

st.sidebar.markdown("---")
st.sidebar.info("""
**モード解説:**
- **Smart版**: 読みやすさを残しつつ圧縮
- **完全圧縮**: 極限までサイズ削減
- **整形モード**: インデントを整理して軽量化（構造維持）
""")


# ==========================================
# 2. ロジック関数群
# ==========================================

def get_byte_len(text):
    """文字列のUTF-8バイト数を取得"""
    return len(text.encode('utf-8'))


def split_long_line(line, limit):
    """制限バイト数を超える行を安全に分割する"""
    if get_byte_len(line) <= limit:
        return [line]

    result = []
    current_start = 0
    line_len = len(line)
    in_quote = False
    quote_char = ''
    last_split_point = -1
    
    i = 0
    while i < line_len:
        char = line[i]
        
        # クォート内かどうかの判定
        if char == '"' or char == "'":
            if not in_quote:
                in_quote = True
                quote_char = char
            elif char == quote_char:
                in_quote = False
        
        # タグの終わり（>）を分割候補とする（クォート外のみ）
        if char == '>' and not in_quote:
            last_split_point = i + 1
            
        # 現在のチャンクサイズをチェック
        chunk = line[current_start:i+1]
        
        if get_byte_len(chunk) > limit:
            # 分割実行
            if last_split_point > current_start:
                # 安全な場所（タグ区切り）でカット
                result.append(line[current_start:last_split_point])
                current_start = last_split_point
                i = current_start - 1
            else:
                # 分割場所がない場合は強制カット（文字単位）
                result.append(line[current_start:i])
                current_start = i
                i -= 1 # 同じ文字から再開
            
            last_split_point = -1
            
        i += 1
        
    # 残りを追加
    if current_start < line_len:
        result.append(line[current_start:])
        
    return result


def apply_activecore_limit(html, limit):
    """全行に対してバイト数制限を適用"""
    lines = html.split('\n')
    processed = []
    
    for line in lines:
        line = line.rstrip()
        if not line:
            continue
            
        if get_byte_len(line) <= limit:
            processed.append(line)
        else:
            # 長い行は分割処理へ
            split_parts = split_long_line(line, limit)
            processed.extend(split_parts)
            
    return '\n'.join(processed)


def format_html_indentation(html):
    """HTMLの構造を解析してインデントを再構築（整形モード）"""
    # タグとテキストに分解
    parts = re.split(r'(<[^>]+>)', html)
    # 空白のみの要素を除去
    parts = [p.strip() for p in parts if p.strip()]
    
    formatted_lines = []
    level = 0
    indent_str = "  "  # スペース2個
    
    # インデントを増やさないタグ
    void_tags = [
        'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 
        'link', 'meta', 'param', 'source', 'track', 'wbr', '!doctype', '?xml'
    ]
    
    for part in parts:
        # 終了タグ
        if part.startswith('</'):
            if level > 0:
                level -= 1
            formatted_lines.append((indent_str * level) + part)
            continue
            
        # コメント
        if part.startswith('', '', s, flags=re.DOTALL)
    # 空白・タブをスペース1つに
    s = re.sub(r'[ \t]+', ' ', s)
    # 行ごとの整形
    lines = [line.strip() for line in s.split('\n')]
    s = '\n'.join(lines)
    # 空行削除
    s = re.sub(r'\n\s*\n', '\n', s)
    return s.strip()


def process_aggressive(html):
    """Aggressive版圧縮"""
    s = html
    s = re.sub(r'', '', s, flags=re.DOTALL)
    s = s.replace('\n', '').replace('\r', '').replace('\t', '')
    s = re.sub(r' +', ' ', s)
    s = re.sub(r'>\s+<', '><', s)
    return s.strip()


def process_complete(html):
    """完全圧縮"""
    s = html
    s = re.sub(r'', '', s, flags=re.DOTALL)
    s = re.sub(r'\s+', ' ', s)
    s = re.sub(r'>\s+<', '><', s)
    s = re.sub(r'\s*=\s*', '=', s)
    s = re.sub(r'\s+>', '>', s)
    s = re.sub(r'<\s+', '<', s)
    return s.strip()


# ==========================================
# 3. メイン処理フロー
# ==========================================

col_input, col_output = st.columns(2)

# --- 入力エリア ---
with col_input:
    st.subheader("📥 入力")
    input_type = st.radio("入力方法", ["テキスト貼り付け", "ファイルアップロード"], horizontal=True)
    
    html_data = ""
    
    if input_type == "テキスト貼り付け":
        html_data = st.text_area("HTMLコード", height=400)
    else:
        uploaded = st.file_uploader("HTMLファイル", type=['html', 'htm'])
        if uploaded:
            html_data = uploaded.read().decode('utf-8')
            st.success(f"読み込み完了: {uploaded.name}")

# --- 出力エリア ---
with col_output:
    st.subheader("📤 出力")
    
    if html_data:
        if st.button("🚀 処理実行", type="primary", use_container_width=True):
            with st.spinner("処理中..."):
                # 1. 指定モードで圧縮/整形
                result_html = ""
                
                if "ヘッダーのみ" in compression_mode:
                    result_html = process_header_only(html_data)
                elif "Smart版" in compression_mode:
                    result_html = process_smart(html_data)
                elif "Aggressive版" in compression_mode:
                    result_html = process_aggressive(html_data)
                elif "整形モード" in compression_mode:
                    result_html = format_html_indentation(html_data)
                else:
                    result_html = process_complete(html_data)
                
                # 2. アクティブコア制限適用（オプション）
                if use_activecore_limit:
                    result_html = apply_activecore_limit(result_html, int(byte_limit))
                
                # 結果を保存
                st.session_state['result'] = result_html
                st.session_state['original_len'] = get_byte_len(html_data)
                
        # 結果表示
        if 'result' in st.session_state:
            res = st.session_state['result']
            orig_len = st.session_state['original_len']
            res_len = get_byte_len(res)
            diff = orig_len - res_len
            ratio = (diff / orig_len * 100) if orig_len > 0 else 0
            
            st.success("完了しました")
            
            # 数値データ表示
            m1, m2, m3 = st.columns(3)
            with m1: st.metric("元サイズ", f"{orig_len:,} B")
            with m2: st.metric("処理後", f"{res_len:,} B", delta=f"-{diff:,} B")
            with m3: st.metric("削減率", f"{ratio:.1f} %")
            
            # バイト数チェック
            if use_activecore_limit:
                lines = res.split('\n')
                errors = []
                for idx, line in enumerate(lines, 1):
                    if get_byte_len(line) > byte_limit:
                        errors.append(f"{idx}行目: {get_byte_len(line)} B")
                
                if errors:
                    st.error(f"{len(errors)}行が制限を超えています")
                    with st.expander("エラー詳細"):
                        st.text('\n'.join(errors))
                else:
                    st.success("✅ 全行が制限バイト数以内です")

            # コードプレビュー
            with st.expander("コードを確認", expanded=True):
                st.code(res[:1000] + "...", language="html")
                
            # ダウンロード
            suffix = "_ac" if use_activecore_limit else ""
            st.download_button(
                "💾 HTMLをダウンロード",
                data=res.encode('utf-8'),
                file_name=f"processed{suffix}.html",
                mime="text/html",
                use_container_width=True
            )
            
            # コピー用
            st.text_area("コピー用", res, height=150)
            
    else:
        st.info("左側に入力してください")
