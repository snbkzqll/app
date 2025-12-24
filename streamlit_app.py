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
    </style>
    """, unsafe_allow_html=True)


local_css()

# ==================== ⚙️ 云端连接配置 ====================
conn = st.connection("gsheets", type=GSheetsConnection)

# 定义工作表名称 (必须与 Google Sheets 底部标签页名字一致)
SHEET_ELEC = "electronics"
SHEET_SCREW = "screws"
SHEET_PCB = "pcbs"  # 🟢 新增：PCB 表名


# ==================== 🔧 核心函数 ====================

def load_data(sheet_name):
    """从云端读取数据 (不缓存)"""
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


# ==================== 📱 电子元器件 ====================
def render_electronics():
    st.markdown("## ☁️ 电子元器件 (Google Sheets)")
    df = load_data(SHEET_ELEC)
    if df.empty:
        st.info("初始化中或表格为空...")
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("📦 种类", len(df))
    c2.metric("🔢 总数", df['数量'].sum())
    low_stock = df[df['数量'] < 10]
    c3.metric("⚠️ 缺货", len(low_stock), delta_color="inverse")

    if not low_stock.empty:
        with st.expander(f"🔴 查看 {len(low_stock)} 个缺货器件"):
            st.dataframe(low_stock, use_container_width=True)

    st.markdown("---")
    tab1, tab2, tab3 = st.tabs(["📊 总览与管理", "📥 批量入库", "📤 BOM出库"])

    with tab1:
        col1, col2 = st.columns([1, 4])
        with col1:
            st.markdown("##### 🛠 操作")
            if st.button("🔄 强制刷新", use_container_width=True): st.rerun()
            st.divider()
            st.markdown("##### 🔍 筛选")
            sort_mode = st.selectbox("排序", ["智能排序", "库存倒序", "库存正序"])
            filter_type = st.multiselect("类型", df['类型'].unique() if '类型' in df.columns else [])
            search = st.text_input("搜索...", placeholder="输入型号或参数")

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

            edited_df = st.data_editor(
                display_df, use_container_width=True, num_rows="dynamic", height=500, key="elec_editor"
            )

            if len(edited_df) != len(df):
                st.warning("⚠️ 筛选或搜索模式下 **禁止保存**。请清空筛选条件，显示全表后再保存。")
            else:
                if st.button("💾 保存更改到云端", type="primary", use_container_width=True):
                    if save_data(edited_df, SHEET_ELEC):
                        st.success("✅ 云端保存成功！")
                        time.sleep(1)
                        st.rerun()

    with tab2:
        st.write("批量上传 Excel 追加库存")
        up_file = st.file_uploader("上传 Excel 入库单", type=['xlsx'])
        if up_file:
            new_data = pd.read_excel(up_file)
            st.write("预览:", new_data.head())
            if st.button("🚀 确认追加到云端"):
                updated_df = pd.concat([df, new_data], ignore_index=True)
                if save_data(updated_df, SHEET_ELEC):
                    st.success("入库成功！")
                    time.sleep(1)
                    st.rerun()
    with tab3:
        st.info("💡 提示：云端版建议直接在 [总览] 页面搜索型号，然后手动修改库存数量。")


# ==================== 🔩 五金螺丝 ====================
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
                mask = (df['规格'] == spec) & (df['长度'] == length) & (df['类型'] == stype)
                if mask.any():
                    df.loc[mask, '数量'] += qty
                    st.toast(f"库存已累加: {spec} {length} +{qty}")
                else:
                    new_row = pd.DataFrame(
                        [{"规格": spec, "长度": length, "类型": stype, "材质": "不锈钢", "数量": qty, "备注": ""}])
                    df = pd.concat([df, new_row], ignore_index=True)
                    st.toast(f"新规格入库: {spec} {length}")
                save_data(df, SHEET_SCREW)
                time.sleep(1)
                st.rerun()
        st.divider()
        if st.button("🔄 刷新数据", use_container_width=True): st.rerun()

    with col2:
        edited_df = st.data_editor(
            df, use_container_width=True, num_rows="dynamic", height=500, key="screw_editor"
        )
        if st.button("💾 保存五金更改", type="primary"):
            if save_data(edited_df, SHEET_SCREW):
                st.success("✅ 保存成功！")
                time.sleep(1)
                st.rerun()


# ==================== 📟 PCB 电路板 (新增) ====================
def render_pcb():
    st.markdown("## 📟 PCB 电路板 (Google Sheets)")
    # 1. 加载数据
    df = load_data(SHEET_PCB)

    # 初始化检查
    if df.empty:
        st.info("表格为空，请确保 Google Sheets 'pcbs' 表头包含：名称, 尺寸, 数量, 位置, 备注")
        # 即使为空也允许手动添加，所以不直接 return，除非连列名都没有
        if '名称' not in df.columns:
            return

    # 2. 仪表盘
    c1, c2, c3 = st.columns(3)
    c1.metric("📦 板子型号", len(df))
    c2.metric("🔢 库存总数", df['数量'].sum())
    c3.metric("⚠️ 低库存", len(df[df['数量'] < 5]), delta_color="inverse")  # PCB通常少于5片就该打样了

    st.markdown("---")

    col1, col2 = st.columns([1, 4])

    # 左侧：快速添加表单
    with col1:
        st.write("### ⚡ 新板入库")
        with st.form("pcb_add"):
            name = st.text_input("名称/版本号", placeholder="V1.0 主控板")
            size = st.text_input("尺寸", placeholder="10x10cm")
            loc = st.text_input("位置", placeholder="A-01")
            qty = st.number_input("数量", value=5, step=1, min_value=1)

            if st.form_submit_button("➕ 添加 / 补货"):
                # 逻辑：名称和尺寸一致视为同一种板子
                mask = (df['名称'] == name) & (df['尺寸'] == size)

                if mask.any():
                    df.loc[mask, '数量'] += qty
                    st.toast(f"已累加: {name} +{qty}")
                else:
                    new_row = pd.DataFrame([{
                        "名称": name, "尺寸": size, "数量": qty,
                        "位置": loc, "备注": ""
                    }])
                    df = pd.concat([df, new_row], ignore_index=True)
                    st.toast(f"新板入库: {name}")

                # 自动保存
                save_data(df, SHEET_PCB)
                time.sleep(1)
                st.rerun()

        st.divider()
        if st.button("🔄 刷新数据", use_container_width=True):
            st.rerun()

    # 右侧：全功能编辑器
    with col2:
        edited_df = st.data_editor(
            df,
            use_container_width=True,
            num_rows="dynamic",
            height=500,
            key="pcb_editor",
            column_config={
                "数量": st.column_config.NumberColumn(
                    "数量",
                    help="库存数量",
                    min_value=0,
                    step=1,
                ),
                "尺寸": st.column_config.TextColumn("尺寸 (长x宽)"),
            }
        )

        if st.button("💾 保存PCB更改", type="primary"):
            if save_data(edited_df, SHEET_PCB):
                st.success("✅ 保存成功！")
                time.sleep(1)
                st.rerun()


# ==================== 🚀 主入口 ====================
with st.sidebar:
    st.title("☁️ 云端管家")
    st.markdown("---")
    # 🟢 修改：增加了 PCB 电路板 选项
    app_mode = st.radio("切换仓库", ["电子元器件", "五金螺丝", "PCB电路板"], label_visibility="collapsed")
    st.markdown("---")
    st.caption(f"Status: Online 🟢\nDatabase: Google Sheets")

if app_mode == "电子元器件":
    render_electronics()
elif app_mode == "五金螺丝":
    render_screws()
else:
    render_pcb()  # 🟢 新增：调用 PCB 渲染函数