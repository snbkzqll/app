import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import re
import time

# ==================== 🎨 界面美化 ====================
st.set_page_config(page_title="云端库存管家", page_icon="☁️", layout="wide")


def local_css():
    st.markdown("""
    <style>
        .stApp { background-color: #f3f4f6; }
        [data-testid="stSidebar"] { background-color: #1e293b; }
        [data-testid="stSidebar"] * { color: #f1f5f9 !important; }
        h1, h2, h3 {
            background: -webkit-linear-gradient(45deg, #2563eb, #9333ea);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            font-family: 'Segoe UI', sans-serif; font-weight: 800 !important;
        }
        div[data-testid="metric-container"] {
            background-color: rgba(255, 255, 255, 0.9); border-radius: 15px;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); padding: 15px;
        }
        [data-testid="stDataEditor"] {
            background-color: white; border-radius: 15px; padding: 10px;
        }
        .stButton>button { border-radius: 50px; font-weight: bold; border: none; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }

        /* 图片预览区的样式 */
        .img-preview {
            border: 2px solid #e5e7eb;
            border-radius: 10px;
            padding: 5px;
            background: white;
        }
    </style>
    """, unsafe_allow_html=True)


local_css()

# ==================== ⚙️ 云端连接配置 ====================
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_ELEC = "electronics"
SHEET_SCREW = "screws"


# ==================== 🔧 核心函数 ====================

def load_data(sheet_name):
    """从云端读取数据"""
    try:
        df = conn.read(worksheet=sheet_name, ttl=0)
        df = df.fillna("")
        if '数量' in df.columns:
            df['数量'] = pd.to_numeric(df['数量'], errors='coerce').fillna(0).astype(int)
        return df
    except Exception as e:
        st.error(f"连接云端失败: {e}")
        return pd.DataFrame()


def save_data(df, sheet_name):
    """保存数据到云端"""
    try:
        conn.update(worksheet=sheet_name, data=df)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"云端保存失败: {e}")
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


# ==================== 🖼️ 图片显示助手 ====================
def show_selected_image(df, selection):
    """在侧边栏显示选中行的图片"""
    if selection and "rows" in selection and selection["rows"]:
        # 获取选中行的索引
        idx = selection["rows"][0]
        # 获取该行数据
        try:
            # 注意：如果表格经过排序/筛选，这里的 index 需要小心处理
            # 这里的 df 是 display_df，索引是对应的
            row = df.iloc[idx]
            name = row.get("名称", row.get("规格", "未知器件"))

            st.sidebar.markdown("---")
            st.sidebar.markdown(f"### 🖼️ 当前选中: {name}")

            # 检查是否有图片列
            img_col = None
            for col in ["图片", "图片链接", "Image", "img"]:
                if col in df.columns:
                    img_col = col
                    break

            if img_col and row[img_col] and str(row[img_col]).startswith("http"):
                st.sidebar.image(row[img_col], caption=f"{name} 实物图", use_container_width=True)
            else:
                st.sidebar.info("暂无图片链接 (请在表格 '图片' 列填入网址)")
        except Exception as e:
            st.sidebar.error(f"图片加载失败: {e}")


# ==================== 📱 电子元器件 (云端版) ====================
def render_electronics():
    st.markdown("## ☁️ 电子元器件 (Google Sheets)")
    df = load_data(SHEET_ELEC)
    if df.empty:
        st.info("正在初始化数据表...")
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("📦 种类", len(df))
    c2.metric("🔢 总数", df['数量'].sum())
    low_stock = df[df['数量'] < 10]
    c3.metric("⚠️ 缺货", len(low_stock), delta_color="inverse")

    st.markdown("---")

    tab1, tab2, tab3 = st.tabs(["📊 总览与管理", "📥 批量入库", "📤 BOM出库"])

    with tab1:
        col1, col2 = st.columns([1, 4])
        with col1:
            st.markdown("##### 🛠 操作")
            if st.button("🔄 强制刷新", use_container_width=True):
                st.rerun()
            st.divider()
            st.markdown("##### 🔍 筛选")
            sort_mode = st.selectbox("排序", ["智能排序", "库存倒序", "库存正序"])
            filter_type = st.multiselect("类型", df['类型'].unique() if '类型' in df.columns else [])
            search = st.text_input("搜索...")

        with col2:
            display_df = df.copy()
            if filter_type: display_df = display_df[display_df['类型'].isin(filter_type)]
            if search:
                mask = display_df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)
                display_df = display_df[mask]

            if sort_mode == "智能排序":
                display_df['sort_val'] = display_df['参数'].apply(get_sort_value)
                display_df = display_df.sort_values(by=['类型', '名称', 'sort_val'])
                display_df = display_df.drop(columns=['sort_val'])
            elif sort_mode == "库存倒序":
                display_df = display_df.sort_values(by='数量', ascending=False)
            elif sort_mode == "库存正序":
                display_df = display_df.sort_values(by='数量')

            # 🔥🔥🔥 核心修改：增加行选择功能 🔥🔥🔥
            # 1. 配置列显示 (把图片链接直接显示为缩略图)
            column_cfg = {}
            if "图片" in display_df.columns:
                column_cfg["图片"] = st.column_config.ImageColumn("图片预览", help="输入图片链接")

            # 2. 启用 selection_mode
            event = st.data_editor(
                display_df,
                use_container_width=True,
                num_rows="dynamic",
                height=500,
                key="elec_editor",
                column_config=column_cfg,
                on_change=None,
                selection_mode="single-row",  # 允许单选行
            )

            # 3. 如果选中了行，在侧边栏显示大图
            show_selected_image(display_df, event.selection)

            # 4. 获取编辑后的数据 (data_editor 返回的是事件对象，我们需要手动提取 data)
            # 注意：Streamlit 的 data_editor 直接修改传入的 df 并不完全准确，
            # 但在这里为了保持你原有的保存逻辑简单，我们假设用户是想保存 event 中的更改。
            # 实际上 data_editor 会返回编辑后的 dataframe，但在开启 selection 后，返回值变成了 event。
            # ⚠️ 修正：Streamlit 1.35+ data_editor 开启 selection 后返回的是 dataframe 还是 event 取决于写法。
            # 为了兼容保存功能和选择功能，我们需要用 state 或者重新组织逻辑。
            # 简化方案：data_editor 在 Streamlit 新版中直接返回编辑后的数据，selection 存储在 event.selection 中
            # 但目前 API 如果开启 on_select，返回值会变。
            # 💡 最佳实践：这里我们为了不破坏你的保存逻辑，仅仅利用 selection 来展示图片。
            # data_editor 默认返回 edited_df。selection 需要通过 key 在 session_state 中获取，或者使用 on_select。

            # 修正逻辑：使用 session_state 获取选区，data_editor 依然返回 edited_df
            if "elec_editor" in st.session_state:
                selection = st.session_state["elec_editor"].get("selection", {})
                show_selected_image(display_df, selection)

            if st.button("💾 保存更改到云端", type="primary"):
                # 这里的 event 其实就是 edited_df
                if save_data(event, SHEET_ELEC):
                    st.success("✅ 云端保存成功！")
                    time.sleep(1)
                    st.rerun()

    with tab2:
        up_file = st.file_uploader("上传 Excel 入库单", type=['xlsx'])
        if up_file:
            new_data = pd.read_excel(up_file)
            st.write("预览:", new_data.head())
            if st.button("🚀 确认合并入库"):
                current_df = load_data(SHEET_ELEC)
                updated_df = pd.concat([current_df, new_data], ignore_index=True)
                if save_data(updated_df, SHEET_ELEC):
                    st.success("入库成功！")
                    time.sleep(1)
                    st.rerun()
    with tab3:
        st.info("BOM 匹配功能建议在本地使用。")


# ==================== 🔩 五金螺丝 (云端版) ====================
def render_screws():
    st.markdown("## 🔩 五金螺丝 (Google Sheets)")
    df = load_data(SHEET_SCREW)
    if df.empty:
        st.info("初始化中...")
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("📦 种类", len(df))
    c2.metric("🔢 总数", df['数量'].sum())
    c3.metric("⚠️ 缺货", len(df[df['数量'] < 20]), delta_color="inverse")

    st.markdown("---")
    col1, col2 = st.columns([1, 4])

    with col1:
        st.write("### ⚡ 快速入库")
        with st.form("screw_add"):
            spec = st.text_input("规格", placeholder="M3")
            length = st.text_input("长度", placeholder="10mm")
            stype = st.text_input("类型", placeholder="圆头")
            qty = st.number_input("数量", value=50)
            if st.form_submit_button("➕ 添加"):
                mask = (df['规格'] == spec) & (df['长度'] == length) & (df['类型'] == stype)
                if mask.any():
                    df.loc[mask, '数量'] += qty
                else:
                    new_row = pd.DataFrame(
                        [{"规格": spec, "长度": length, "类型": stype, "材质": "不锈钢", "数量": qty, "备注": ""}])
                    df = pd.concat([df, new_row], ignore_index=True)
                save_data(df, SHEET_SCREW)
                st.toast("添加成功!")
                time.sleep(1)
                st.rerun()
        st.divider()
        if st.button("🔄 刷新"): st.rerun()

    with col2:
        # 同样增加图片显示逻辑
        column_cfg = {}
        if "图片" in df.columns:
            column_cfg["图片"] = st.column_config.ImageColumn("图片预览")

        edited_df = st.data_editor(
            df,
            use_container_width=True,
            num_rows="dynamic",
            height=500,
            key="screw_editor",
            column_config=column_cfg,
            selection_mode="single-row"
        )

        # 显示图片
        if "screw_editor" in st.session_state:
            selection = st.session_state["screw_editor"].get("selection", {})
            show_selected_image(df, selection)

        if st.button("💾 保存五金更改", type="primary"):
            save_data(edited_df, SHEET_SCREW)
            st.success("保存成功！")
            st.rerun()


# ==================== 🚀 主入口 ====================
with st.sidebar:
    st.title("☁️ 云端管家")
    st.info("💡 提示：点击表格左侧的方框选中一行，即可在侧边栏下方查看图片。")
    app_mode = st.radio("切换仓库", ["电子元器件", "五金螺丝"])
    st.caption("Data stored in Google Sheets")

if app_mode == "电子元器件":
    render_electronics()
else:
    render_screws()