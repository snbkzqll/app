import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import re
import time

# ==================== 🔐 账号密码配置 ====================
USERS = {
    "admin": "123456",
    "user1": "888888",
    "root": "root"
}

# ==================== 🎨 界面美化配置 ====================
st.set_page_config(page_title="云端库存管家", page_icon="☁️", layout="wide")


def local_css():
    st.markdown("""
    <style>
        .stApp { background-color: #f3f4f6; }
        [data-testid="stSidebar"] { background-color: #1e293b; }
        [data-testid="stSidebar"] * { color: #f1f5f9 !important; }
        h1, h2, h3 {
            background: -webkit-linear-gradient(45deg, #2563eb, #9333ea);
            -webkit-background-clip: text; 
            -webkit-text-fill-color: transparent;
            font-family: 'Segoe UI', sans-serif; 
            font-weight: 800 !important;
        }
        div[data-testid="metric-container"] {
            background-color: rgba(255, 255, 255, 0.9); 
            border-radius: 15px;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); 
            padding: 15px;
            border: 1px solid #e5e7eb;
        }
        [data-testid="stDataEditor"] {
            background-color: white; 
            border-radius: 15px; 
            padding: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        .stButton>button { 
            border-radius: 50px; 
            font-weight: bold; 
            border: none; 
            box-shadow: 0 2px 4px rgba(0,0,0,0.1); 
            transition: all 0.2s;
        }
        .stButton>button:hover { transform: scale(1.02); }
        .login-box {
            padding: 2rem; border-radius: 10px; background-color: white;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-top: 10vh;
        }
    </style>
    """, unsafe_allow_html=True)


local_css()


# ==================== 🔐 登录逻辑 ====================
def check_login():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("<br><br>", unsafe_allow_html=True)
            st.title("🔐 请先登录")
            with st.form("login_form"):
                username = st.text_input("账号")
                password = st.text_input("密码", type="password")
                if st.form_submit_button("登录", use_container_width=True):
                    if username in USERS and USERS[username] == password:
                        st.session_state.logged_in = True
                        st.session_state.username = username
                        st.success("登录成功！")
                        st.rerun()
                    else:
                        st.error("❌ 账号或密码错误")
        return False
    return True


if not check_login():
    st.stop()

# ==================== ⚙️ 云端配置 ====================
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_ELEC = "electronics"
SHEET_SCREW = "screws"
SHEET_PCB = "pcbs"


# ==================== 🔧 核心函数 (数据处理升级) ====================
def load_data(sheet_name):
    """读取数据，强制列类型，确保数据安全"""
    try:
        df = conn.read(worksheet=sheet_name, ttl=0)
        df = df.fillna("")
        df.columns = df.columns.astype(str)  # 强制表头为字符

        if '数量' in df.columns:
            df['数量'] = pd.to_numeric(df['数量'], errors='coerce').fillna(0).astype(int)

        # 强制其他列为字符串，防止混合类型报错
        for col in df.columns:
            if col != '数量':
                df[col] = df[col].astype(str).replace('nan', '')
        return df
    except Exception as e:
        st.error(f"连接云端失败: {e}")
        return pd.DataFrame()


def save_data_smart(original_df, edited_subset_df, sheet_name):
    """
    🧠 智能保存函数：
    即使只编辑了筛选后的几行，也能精准更新回总表，不会弄丢隐藏的数据。
    """
    try:
        # 1. 创建原始数据的副本，防止意外修改
        final_df = original_df.copy()

        # 2. 利用索引(Index)进行精准更新
        # Pandas 的 update 会根据行号（Index）自动匹配
        # 只有 edited_subset_df 里存在的行，才会被更新到 final_df 里
        final_df.loc[edited_subset_df.index] = edited_subset_df

        # 3. 推送回 Google Sheets
        conn.update(worksheet=sheet_name, data=final_df)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"保存失败: {e}")
        return False


def get_sort_value(name):
    name = str(name).upper().strip()
    match = re.search(r'(\d+\.?\d*)\s*([KMGUNPμR]?)', name)
    if match:
        val = float(match.group(1))
        unit = match.group(2)
        multipliers = {'K': 1e3, 'M': 1e6, 'G': 1e9, 'R': 1, '': 1, 'M': 1e-3, 'U': 1e-6, 'μ': 1e-6, 'N': 1e-9,
                       'P': 1e-12}
        if 'F' in name: pass
        return val * multipliers.get(unit, 1)
    return float('inf')


# ==================== 🖼️ 图片显示组件 ====================
def show_selected_image(df, selection):
    if selection and "rows" in selection and selection["rows"]:
        idx = selection["rows"][0]
        try:
            # 注意：这里的 idx 是 data_editor 显示数据的相对索引
            # 如果是筛选后的数据，需要确保传入的 df 就是那个筛选后的 df
            row = df.iloc[idx]
            name = row.get("名称", row.get("规格", "器件"))

            st.sidebar.markdown("---")
            st.sidebar.markdown(f"### 🖼️ 当前选中: {name}")

            img_col = None
            for col in ["图片", "图片链接", "Image", "img"]:
                if col in df.columns:
                    img_col = col
                    break

            if img_col and row[img_col] and str(row[img_col]).startswith("http"):
                st.sidebar.image(row[img_col], caption=f"{name} 实物图", use_container_width=True)
            else:
                st.sidebar.info("暂无图片链接")
        except Exception:
            pass


# ==================== 📱 电子元器件 (升级版) ====================
def render_electronics():
    st.markdown("## ☁️ 电子元器件")
    df = load_data(SHEET_ELEC)
    if df.empty:
        st.info("数据加载中...")
        return

    # 顶部数据看板
    c1, c2, c3 = st.columns(3)
    c1.metric("📦 种类", len(df))
    c2.metric("🔢 总数", df['数量'].sum())
    low_stock = df[df['数量'] < 10]
    c3.metric("⚠️ 缺货", len(low_stock), delta_color="inverse")

    st.markdown("---")
    tab1, tab2, tab3 = st.tabs(["📊 总览与管理", "📥 批量入库", "📤 BOM出库"])

    # === Tab 1: 核心管理 (支持筛选保存) ===
    with tab1:
        col1, col2 = st.columns([1, 4])
        with col1:
            st.markdown("##### 🔍 筛选与搜索")
            filter_type = st.multiselect("按类型筛选", df['类型'].unique() if '类型' in df.columns else [])
            search = st.text_input("关键字搜索...", placeholder="输入型号/参数")

            st.divider()
            if st.button("🔄 刷新数据", use_container_width=True): st.rerun()

        with col2:
            # 1. 处理筛选逻辑
            display_df = df.copy()
            if filter_type:
                display_df = display_df[display_df['类型'].isin(filter_type)]
            if search:
                mask = display_df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)
                display_df = display_df[mask]

            # 2. 配置图片列
            column_cfg = {}
            if "图片" in display_df.columns:
                column_cfg["图片"] = st.column_config.ImageColumn("图片预览")

            # 3. 显示编辑器
            edited_df = st.data_editor(
                display_df,
                use_container_width=True,
                num_rows="dynamic",
                height=500,
                key="elec_editor",
                column_config=column_cfg,
                selection_mode="single-row"
            )

            # 显示图片侧边栏
            if "elec_editor" in st.session_state:
                show_selected_image(display_df, st.session_state["elec_editor"].get("selection", {}))

            # 4. 智能保存按钮
            # 只要数据有变化（无论是改了数量，还是加了行），都可以保存
            if st.button("💾 保存更改到云端", type="primary"):
                if save_data_smart(df, edited_df, SHEET_ELEC):
                    st.success("✅ 保存成功！所有更改（包括筛选状态下的修改）已更新。")
                    time.sleep(1)
                    st.rerun()

    # === Tab 2: 入库 ===
    with tab2:
        up_file = st.file_uploader("上传 Excel 入库单", type=['xlsx'])
        if up_file:
            new_data = pd.read_excel(up_file)
            st.dataframe(new_data.head())
            if st.button("🚀 确认合并入库"):
                # 简单追加模式
                final_df = pd.concat([df, new_data], ignore_index=True)
                save_data_smart(final_df, final_df, SHEET_ELEC)
                st.success("入库成功！")
                st.rerun()

    # === Tab 3: 出库 ===
    with tab3:
        st.info("💡 提示：对于大批量BOM匹配，建议下载Excel在本地处理。单品出库请直接在“总览”页面修改数量。")


# ==================== 🔩 五金螺丝 (全面升级) ====================
def render_screws():
    st.markdown("## 🔩 五金螺丝")
    df = load_data(SHEET_SCREW)
    if df.empty:
        st.info("数据加载中...")
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("📦 种类", len(df))
    c2.metric("🔢 总数", df['数量'].sum())
    c3.metric("⚠️ 缺货", len(df[df['数量'] < 20]), delta_color="inverse")

    st.markdown("---")
    # 统一的三栏布局
    tab1, tab2, tab3 = st.tabs(["📊 总览与管理", "📥 快速入库", "📤 快捷领用"])

    # === Tab 1: 管理 (支持搜索保存) ===
    with tab1:
        col1, col2 = st.columns([1, 4])
        with col1:
            st.markdown("##### 🔍 筛选与搜索")
            # 增加类型筛选
            filter_type = st.multiselect("按类型筛选", df['类型'].unique() if '类型' in df.columns else [])
            # 增加规格筛选
            filter_spec = st.multiselect("按规格筛选", df['规格'].unique() if '规格' in df.columns else [])
            search = st.text_input("关键字搜索...", placeholder="输入 M3 / 长度等")

            st.divider()
            if st.button("🔄 刷新数据", use_container_width=True, key="refresh_screw"): st.rerun()

        with col2:
            display_df = df.copy()
            if filter_type: display_df = display_df[display_df['类型'].isin(filter_type)]
            if filter_spec: display_df = display_df[display_df['规格'].isin(filter_spec)]
            if search:
                mask = display_df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)
                display_df = display_df[mask]

            column_cfg = {}
            if "图片" in display_df.columns:
                column_cfg["图片"] = st.column_config.ImageColumn("图片预览")

            edited_df = st.data_editor(
                display_df,
                use_container_width=True,
                num_rows="dynamic",
                height=500,
                key="screw_editor",
                column_config=column_cfg,
                selection_mode="single-row"
            )

            if "screw_editor" in st.session_state:
                show_selected_image(display_df, st.session_state["screw_editor"].get("selection", {}))

            # 智能保存
            if st.button("💾 保存五金更改", type="primary"):
                if save_data_smart(df, edited_df, SHEET_SCREW):
                    st.success("✅ 保存成功！")
                    time.sleep(1)
                    st.rerun()

    # === Tab 2: 入库表单 ===
    with tab2:
        col_a, col_b = st.columns([1, 2])
        with col_a:
            with st.form("screw_add"):
                st.write("### ➕ 新增/补货")
                spec = st.text_input("规格", placeholder="M3")
                length = st.text_input("长度", placeholder="10mm")
                stype = st.text_input("类型", placeholder="圆头")
                qty = st.number_input("数量", value=50, step=10, min_value=1)

                if st.form_submit_button("确认入库"):
                    # 查找是否存在
                    mask = (df['规格'].astype(str) == str(spec)) & (df['长度'].astype(str) == str(length)) & (
                                df['类型'].astype(str) == str(stype))
                    if mask.any():
                        df.loc[mask, '数量'] +=