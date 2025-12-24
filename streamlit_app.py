import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import re
import time

# ==================== 🎨 界面美化配置 ====================
st.set_page_config(page_title="云端库存管家", page_icon="☁️", layout="wide")


def local_css():
    st.markdown("""
    <style>
        /* 全局背景色 */
        .stApp { background-color: #f3f4f6; }

        /* 侧边栏深色风格 */
        [data-testid="stSidebar"] { background-color: #1e293b; }
        [data-testid="stSidebar"] * { color: #f1f5f9 !important; }

        /* 标题渐变色 */
        h1, h2, h3 {
            background: -webkit-linear-gradient(45deg, #2563eb, #9333ea);
            -webkit-background-clip: text; 
            -webkit-text-fill-color: transparent;
            font-family: 'Segoe UI', sans-serif; 
            font-weight: 800 !important;
        }

        /* 卡片容器样式 */
        div[data-testid="metric-container"] {
            background-color: rgba(255, 255, 255, 0.9); 
            border-radius: 15px;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); 
            padding: 15px;
            border: 1px solid #e5e7eb;
        }

        /* 表格容器样式 */
        [data-testid="stDataEditor"] {
            background-color: white; 
            border-radius: 15px; 
            padding: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }

        /* 按钮圆角样式 */
        .stButton>button { 
            border-radius: 50px; 
            font-weight: bold; 
            border: none; 
            box-shadow: 0 2px 4px rgba(0,0,0,0.1); 
            transition: all 0.2s;
        }
        .stButton>button:hover { transform: scale(1.02); }
    </style>
    """, unsafe_allow_html=True)


local_css()

# ==================== ⚙️ 云端连接配置 ====================
# 建立连接
conn = st.connection("gsheets", type=GSheetsConnection)

# 定义工作表名称 (必须与 Google Sheets 底部标签页名字一致)
SHEET_ELEC = "electronics"
SHEET_SCREW = "screws"


# ==================== 🔧 核心函数 ====================

def load_data(sheet_name):
    """从云端读取数据 (不缓存)"""
    try:
        # ttl=0 表示每次都强制从 Google 拉取最新数据，不使用缓存
        df = conn.read(worksheet=sheet_name, ttl=0)
        df = df.fillna("")
        # 确保数量是整数
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
        st.cache_data.clear()  # 清除 Streamlit 缓存
        return True
    except Exception as e:
        st.error(f"云端保存失败: {e}")
        return False


def get_sort_value(name):
    """智能排序权重计算"""
    name = str(name).upper().strip()
    match = re.search(r'(\d+\.?\d*)\s*([KMGUNPμR]?)', name)
    if match:
        val = float(match.group(1))
        unit = match.group(2)
        multipliers = {
            'K': 1e3, 'M': 1e6, 'G': 1e9, 'R': 1, '': 1,
            'M': 1e-3, 'U': 1e-6, 'μ': 1e-6, 'N': 1e-9, 'P': 1e-12
        }
        if 'F' in name: pass
        return val * multipliers.get(unit, 1)
    return float('inf')


def get_default_index(options, keywords):
    for idx, opt in enumerate(options):
        for kw in keywords:
            if kw in str(opt): return idx
    return 0


# ==================== 📱 电子元器件 (云端版) ====================
def render_electronics():
    st.markdown("## ☁️ 电子元器件 (Google Sheets)")

    # 1. 加载数据
    df = load_data(SHEET_ELEC)
    if df.empty:
        st.info("正在初始化数据表，或表格为空...")
        return

    # 2. 仪表盘
    c1, c2, c3 = st.columns(3)
    c1.metric("📦 种类", len(df))
    c2.metric("🔢 总数", df['数量'].sum())
    low_stock = df[df['数量'] < 10]
    c3.metric("⚠️ 缺货", len(low_stock), delta_color="inverse")

    if not low_stock.empty:
        with st.expander(f"🔴 查看 {len(low_stock)} 个缺货器件"):
            st.dataframe(low_stock, use_container_width=True)

    st.markdown("---")

    # 3. 功能区
    tab1, tab2, tab3 = st.tabs(["📊 总览与管理", "📥 批量入库", "📤 BOM出库"])

    # --- Tab 1: 总览与编辑 ---
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
            search = st.text_input("搜索...", placeholder="输入型号或参数")

        with col2:
            display_df = df.copy()

            # 筛选逻辑
            if filter_type:
                display_df = display_df[display_df['类型'].isin(filter_type)]
            if search:
                mask = display_df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)
                display_df = display_df[mask]

            # 排序逻辑
            if sort_mode == "智能排序":
                display_df['sort_val'] = display_df['参数'].apply(get_sort_value)
                display_df = display_df.sort_values(by=['类型', '名称', 'sort_val'])
                display_df = display_df.drop(columns=['sort_val'])
            elif sort_mode == "库存倒序":
                display_df = display_df.sort_values(by='数量', ascending=False)
            elif sort_mode == "库存正序":
                display_df = display_df.sort_values(by='数量')

            # ⚡ 数据编辑器
            edited_df = st.data_editor(
                display_df,
                use_container_width=True,
                num_rows="dynamic",
                height=500,
                key="elec_editor"
            )

            # 🛡️ 安全锁：防止筛选后保存导致数据丢失
            # 逻辑：如果编辑后的表格行数 != 原始表格行数，说明有数据被隐藏了，此时禁止覆盖保存
            if len(edited_df) != len(df):
                st.warning("⚠️ 筛选或搜索模式下 **禁止保存**，以防丢失隐藏的数据。请清空筛选条件，显示全表后再保存。")
            else:
                if st.button("💾 保存更改到云端", type="primary", use_container_width=True):
                    if save_data(edited_df, SHEET_ELEC):
                        st.success("✅ 云端保存成功！")
                        time.sleep(1)
                        st.rerun()

    # --- Tab 2: 入库 ---
    with tab2:
        st.write("批量上传 Excel 追加库存")
        up_file = st.file_uploader("上传 Excel 入库单", type=['xlsx'])
        if up_file:
            new_data = pd.read_excel(up_file)
            st.write("预览:", new_data.head())
            if st.button("🚀 确认追加到云端"):
                # 简单追加模式
                updated_df = pd.concat([df, new_data], ignore_index=True)
                if save_data(updated_df, SHEET_ELEC):
                    st.success("入库成功！")
                    time.sleep(1)
                    st.rerun()

    # --- Tab 3: 出库 ---
    with tab3:
        st.info("💡 提示：云端版建议直接在 [总览] 页面搜索型号，然后手动修改库存数量，记得清空搜索后再保存。")


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
            qty = st.number_input("数量", value=50, step=10)

            if st.form_submit_button("➕ 添加 / 补货"):
                # 逻辑：检查是否存在，存在则累加，不存在则新建
                mask = (df['规格'] == spec) & (df['长度'] == length) & (df['类型'] == stype)

                if mask.any():
                    df.loc[mask, '数量'] += qty
                    st.toast(f"库存已累加: {spec} {length} +{qty}")
                else:
                    new_row = pd.DataFrame([{
                        "规格": spec, "长度": length, "类型": stype,
                        "材质": "不锈钢", "数量": qty, "备注": ""
                    }])
                    df = pd.concat([df, new_row], ignore_index=True)
                    st.toast(f"新规格入库: {spec} {length}")

                # 自动保存
                save_data(df, SHEET_SCREW)
                time.sleep(1)
                st.rerun()

        st.divider()
        if st.button("🔄 刷新数据", use_container_width=True):
            st.rerun()

    with col2:
        # 五金部分通常不需要复杂的筛选保存，直接显示全表
        edited_df = st.data_editor(
            df,
            use_container_width=True,
            num_rows="dynamic",
            height=500,
            key="screw_editor"
        )

        if st.button("💾 保存五金更改", type="primary"):
            if save_data(edited_df, SHEET_SCREW):
                st.success("✅ 保存成功！")
                time.sleep(1)
                st.rerun()


# ==================== 🚀 主入口 ====================
with st.sidebar:
    st.title("☁️ 云端管家")
    st.markdown("---")
    app_mode = st.radio("切换仓库", ["电子元器件", "五金螺丝"], label_visibility="collapsed")
    st.markdown("---")
    st.caption(f"Status: Online 🟢\nDatabase: Google Sheets")

if app_mode == "电子元器件":
    render_electronics()
else:
    render_screws()