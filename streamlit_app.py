import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import re
import time

# ==================== 🔐 安全登录配置 ====================
USERS = {
    "admin": "123456",
    "li": "888888",
}

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
        .login-box {
            max-width: 400px; margin: 100px auto; padding: 30px;
            background: white; border-radius: 20px; box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        }
    </style>
    """, unsafe_allow_html=True)


local_css()


# ==================== 🕵️‍♂️ 登录逻辑 ====================
def check_login():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.markdown("<br><br><br>", unsafe_allow_html=True)
            st.title("🔐 请先登录")
            with st.form("login_form"):
                username = st.text_input("账号")
                password = st.text_input("密码", type="password")
                if st.form_submit_button("登录", use_container_width=True):
                    if username in USERS and USERS[username] == password:
                        st.session_state.authenticated = True
                        st.session_state.username = username
                        st.success("登录成功！")
                        st.rerun()
                    else:
                        st.error("❌ 账号或密码错误")
        return False
    return True


if not check_login():
    st.stop()

# ==================== ⚙️ 云端连接配置 ====================
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_ELEC = "electronics"
SHEET_SCREW = "screws"
SHEET_PCB = "pcbs"


# ==================== 🔧 核心函数 (修复版) ====================

def load_data(sheet_name):
    """从云端读取数据，并强制修正数据类型"""
    try:
        df = conn.read(worksheet=sheet_name, ttl=0)
        df = df.fillna("")

        # 1. 强制列名为字符串（防止数字表头报错）
        df.columns = df.columns.astype(str)

        # 2. 处理“数量”列：强制转为整数
        if '数量' in df.columns:
            df['数量'] = pd.to_numeric(df['数量'], errors='coerce').fillna(0).astype(int)

        # 3. 处理其他列：强制转为字符串（防止混合类型导致 data_editor 崩溃）
        # 这一点至关重要！解决 TypeError 的关键！
        for col in df.columns:
            if col != '数量':
                df[col] = df[col].astype(str).replace('nan', '')

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
    if selection and "rows" in selection and selection["rows"]:
        idx = selection["rows"][0]
        try:
            row = df.iloc[idx]
            name = row.get("名称", row.get("规格", "未知器件"))
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


# ==================== 📱 电子元器件 ====================
def render_electronics():
    st.markdown("## ☁️ 电子元器件")
    df = load_data(SHEET_ELEC)
    if df.empty:
        st.info("表格为空或初始化中...")
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
            if st.button("🔄 强制刷新", use_container_width=True): st.rerun()
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

            column_cfg = {}
            if "图片" in display_df.columns:
                column_cfg["图片"] = st.column_config.ImageColumn("图片预览")

            event = st.data_editor(
                display_df, use_container_width=True, num_rows="dynamic", height=500, key="elec_editor",
                column_config=column_cfg, selection_mode="single-row"
            )

            if "elec_editor" in st.session_state:
                show_selected_image(display_df, st.session_state["elec_editor"].get("selection", {}))

            if st.button("💾 保存更改到云端", type="primary"):
                if len(event) != len(df) and len(display_df) != len(df):
                    st.warning("⚠️ 筛选模式下请谨慎保存。")
                else:
                    if save_data(event, SHEET_ELEC):
                        st.success("✅ 保存成功！")
                        time.sleep(1)
                        st.rerun()

    with tab2:
        up_file = st.file_uploader("上传 Excel 入库单", type=['xlsx'])
        if up_file:
            new_data = pd.read_excel(up_file)
            if st.button("🚀 确认合并入库"):
                updated_df = pd.concat([df, new_data], ignore_index=True)
                save_data(updated_df, SHEET_ELEC)
                st.success("入库成功！")
                st.rerun()
    with tab3:
        st.info("BOM 功能建议在本地使用。")


# ==================== 🔩 五金螺丝 ====================
def render_screws():
    st.markdown("## 🔩 五金螺丝")
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
        tab_in, tab_out = st.tabs(["📥 入库", "📤 出库"])
        with tab_in:
            with st.form("screw_add"):
                spec = st.text_input("规格", placeholder="M3")
                length = st.text_input("长度", placeholder="10mm")
                stype = st.text_input("类型", placeholder="圆头")
                qty = st.number_input("数量", value=50, step=10, min_value=1)
                if st.form_submit_button("➕ 确认入库"):
                    mask = (df['规格'] == str(spec)) & (df['长度'] == str(length)) & (df['类型'] == str(stype))
                    if mask.any():
                        df.loc[mask, '数量'] += qty
                        st.toast(f"已增加: {spec} +{qty}")
                    else:
                        new_row = pd.DataFrame([{"规格": str(spec), "长度": str(length), "类型": str(stype),
                                                 "材质": "不锈钢", "数量": qty, "备注": ""}])
                        df = pd.concat([df, new_row], ignore_index=True)
                        st.toast(f"新规格: {spec}")
                    save_data(df, SHEET_SCREW)
                    time.sleep(1)
                    st.rerun()

        with tab_out:
            st.caption("选择库存领用：")
            if not df.empty:
                df['display_name'] = df['规格'] + " " + df['长度'] + " " + df['类型'] + " (余:" + df['数量'].astype(
                    str) + ")"
                with st.form("screw_out"):
                    selected_item = st.selectbox("选择螺丝", df['display_name'].tolist())
                    out_qty = st.number_input("领用数量", value=1, min_value=1)
                    if st.form_submit_button("➖ 确认出库"):
                        idx = df[df['display_name'] == selected_item].index[0]
                        if df.at[idx, '数量'] < out_qty:
                            st.error("库存不足！")
                        else:
                            df.at[idx, '数量'] -= out_qty
                            save_data(df.drop(columns=['display_name']), SHEET_SCREW)
                            st.success("出库成功！")
                            time.sleep(1)
                            st.rerun()
        st.divider()
        if st.button("🔄 刷新"): st.rerun()

    with col2:
        column_cfg = {}
        if "图片" in df.columns:
            column_cfg["图片"] = st.column_config.ImageColumn("图片预览")
        display_data = df.drop(columns=['display_name']) if 'display_name' in df.columns else df

        edited_df = st.data_editor(
            display_data, use_container_width=True, num_rows="dynamic", height=500, key="screw_editor",
            column_config=column_cfg, selection_mode="single-row"
        )
        if "screw_editor" in st.session_state:
            show_selected_image(display_data, st.session_state["screw_editor"].get("selection", {}))
        if st.button("💾 保存五金更改", type="primary"):
            save_data(edited_df, SHEET_SCREW)
            st.success("保存成功！")
            st.rerun()


# ==================== 📟 PCB 电路板 (修复版) ====================
def render_pcb():
    st.markdown("## 📟 PCB 电路板")
    df = load_data(SHEET_PCB)
    if df.empty:
        st.info("表格为空，请确保 Google Sheets 'pcbs' 表头包含：名称, 尺寸, 数量, 位置, 备注")
        if '名称' not in df.columns: return

    c1, c2, c3 = st.columns(3)
    c1.metric("📦 板子型号", len(df))
    c2.metric("🔢 库存总数", df['数量'].sum())
    c3.metric("⚠️ 低库存", len(df[df['数量'] < 5]), delta_color="inverse")

    st.markdown("---")
    col1, col2 = st.columns([1, 4])

    with col1:
        tab_in, tab_out = st.tabs(["📥 入库", "📤 出库"])
        with tab_in:
            with st.form("pcb_add"):
                name = st.text_input("名称/版本号", placeholder="V1.0")
                size = st.text_input("尺寸", placeholder="10x10cm")
                loc = st.text_input("位置", placeholder="A-01")
                qty = st.number_input("数量", value=5, min_value=1)

                if st.form_submit_button("➕ 确认入库"):
                    mask = (df['名称'] == str(name)) & (df['尺寸'] == str(size))
                    if mask.any():
                        df.loc[mask, '数量'] += qty
                        st.toast(f"已累加: {name} +{qty}")
                    else:
                        new_row = pd.DataFrame(
                            [{"名称": str(name), "尺寸": str(size), "数量": qty, "位置": str(loc), "备注": ""}])
                        df = pd.concat([df, new_row], ignore_index=True)
                        st.toast(f"新板入库: {name}")
                    save_data(df, SHEET_PCB)
                    time.sleep(1)
                    st.rerun()

        with tab_out:
            st.caption("选择 PCB 领用：")
            if not df.empty:
                df['display_info'] = df['名称'] + " [" + df['尺寸'] + "] (余:" + df['数量'].astype(str) + ")"
                with st.form("pcb_out"):
                    selected_pcb = st.selectbox("选择板子", df['display_info'].tolist())
                    out_qty = st.number_input("领用数量", value=1, min_value=1)
                    if st.form_submit_button("➖ 确认出库"):
                        idx = df[df['display_info'] == selected_pcb].index[0]
                        if df.at[idx, '数量'] < out_qty:
                            st.error("库存不足！")
                        else:
                            df.at[idx, '数量'] -= out_qty
                            save_data(df.drop(columns=['display_info']), SHEET_PCB)
                            st.success("领用成功！")
                            time.sleep(1)
                            st.rerun()
            else:
                st.warning("暂无库存")
        st.divider()
        if st.button("🔄 刷新"): st.rerun()

    with col2:
        column_cfg = {}
        if "图片" in df.columns:
            column_cfg["图片"] = st.column_config.ImageColumn("图片预览")

        # 确保显示的数据不包含辅助列
        display_data = df.drop(columns=['display_info']) if 'display_info' in df.columns else df.copy()

        edited_df = st.data_editor(
            display_data, use_container_width=True, num_rows="dynamic", height=500, key="pcb_editor",
            column_config=column_cfg, selection_mode="single-row"
        )
        if "pcb_editor" in st.session_state:
            show_selected_image(display_data, st.session_state["pcb_editor"].get("selection", {}))

        if st.button("💾 保存PCB更改", type="primary"):
            save_data(edited_df, SHEET_PCB)
            st.success("保存成功！")
            st.rerun()


# ==================== 🚀 主入口 ====================
with st.sidebar:
    st.title("☁️ 云端管家")
    if st.button("🚪 退出登录"):
        st.session_state.authenticated = False
        st.rerun()

    st.markdown("---")
    app_mode = st.radio("切换仓库", ["电子元器件", "五金螺丝", "PCB电路板"], label_visibility="collapsed")
    st.markdown("---")
    st.caption(f"Status: Online 🟢\nUser: {st.session_state.get('username', 'Admin')}")

if app_mode == "电子元器件":
    render_electronics()
elif app_mode == "五金螺丝":
    render_screws()
else:
    render_pcb()