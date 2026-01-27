import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import re
import time
import inspect

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

# ==================== ✅ Data Editor 兼容组件（解决 selection_mode 报错） ====================
def _st_data_editor_supports_selection_mode() -> bool:
    """检查当前 Streamlit 的 st.data_editor 是否支持 selection_mode 参数"""
    try:
        sig = inspect.signature(st.data_editor)
        return "selection_mode" in sig.parameters
    except Exception:
        return False


def _find_image_col(columns) -> str | None:
    for col in ["图片", "图片链接", "Image", "img"]:
        if col in columns:
            return col
    return None


def show_row_image_in_sidebar(row: pd.Series):
    """给一行数据，在侧边栏显示图片"""
    name = row.get("名称", row.get("规格", "器件"))
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"### 🖼️ 当前选中: {name}")

    img_col = _find_image_col(row.index)
    if img_col and row.get(img_col, "") and str(row[img_col]).startswith("http"):
        st.sidebar.image(row[img_col], caption=f"{name} 实物图", use_container_width=True)
    else:
        st.sidebar.info("暂无图片链接")


def sidebar_row_picker(display_df: pd.DataFrame, key: str):
    """
    旧版 Streamlit 降级方案：用 selectbox 选一行，显示图片
    返回：被选中的 DataFrame index（原 index）；找不到返回 None
    """
    if display_df.empty:
        return None

    # 优先用“名称/规格”做展示
    if "名称" in display_df.columns:
        label_col = "名称"
    elif "规格" in display_df.columns:
        label_col = "规格"
    else:
        label_col = display_df.columns[0]

    options = [f"[{idx}] {str(display_df.at[idx, label_col])}" for idx in display_df.index]
    picked = st.sidebar.selectbox("📌 选择一行查看图片（兼容模式）", options, key=f"{key}_picker")

    if not picked:
        return None

    try:
        idx = int(picked.split("]")[0].replace("[", "").strip())
    except Exception:
        return None

    if idx in display_df.index:
        show_row_image_in_sidebar(display_df.loc[idx])
        return idx
    return None


def data_editor_with_optional_selection(
    display_df: pd.DataFrame,
    key: str,
    column_cfg: dict,
    height: int = 500
) -> pd.DataFrame:
    """
    兼容包装：
    - 新版：启用 selection_mode='single-row'，并从 session_state 读取 selection 显示图片
    - 旧版：不传 selection_mode（避免报错），侧边栏用 selectbox 选择行显示图片
    返回：edited_df
    """
    supports = _st_data_editor_supports_selection_mode()

    if supports:
        edited_df = st.data_editor(
            display_df,
            use_container_width=True,
            num_rows="dynamic",
            height=height,
            key=key,
            column_config=column_cfg,
            selection_mode="single-row",
        )
        sel = st.session_state.get(key, {}).get("selection", {})
        if sel and "rows" in sel and sel["rows"]:
            pos = sel["rows"][0]  # 注意：这是 display_df 的位置索引
            try:
                show_row_image_in_sidebar(display_df.iloc[pos])
            except Exception:
                pass
        return edited_df

    # 旧版 Streamlit：没有 selection_mode，走降级方案
    edited_df = st.data_editor(
        display_df,
        use_container_width=True,
        num_rows="dynamic",
        height=height,
        key=key,
        column_config=column_cfg,
    )
    sidebar_row_picker(display_df, key=key)
    return edited_df


# ==================== 🔧 核心函数 (核弹级修复) ====================
def load_data(sheet_name):
    """
    读取数据，执行“核弹级”类型清洗。
    将所有非数量列强制转为 String，杜绝 TypeError。
    """
    try:
        df = conn.read(worksheet=sheet_name, ttl=0)
        df = df.fillna("")

        df = df.loc[:, ~df.columns.duplicated()]
        df.columns = df.columns.astype(str)

        # 全转字符串，避免 mixed types
        df = df.astype(str)
        df = df.replace('nan', '')

        if '数量' in df.columns:
            df['数量'] = pd.to_numeric(df['数量'], errors='coerce').fillna(0).astype(int)

        return df
    except Exception as e:
        st.error(f"数据读取错误: {e}")
        return pd.DataFrame()


def save_data_smart(original_df, edited_subset_df, sheet_name):
    """
    🧠 智能保存：支持筛选模式下的修改保存
    """
    try:
        final_df = original_df.copy()
        final_df.loc[edited_subset_df.index] = edited_subset_df

        conn.update(worksheet=sheet_name, data=final_df)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"保存失败: {e}")
        return False


def get_sort_value(name):
    name = str(name).strip()
    # 不强制 upper，保留 m/u 等可能性；单位统一用 upper 处理
    name_u = name.upper()

    match = re.search(r'(\d+\.?\d*)\s*([KMGUNPμRmunp]?)', name)
    if match:
        val = float(match.group(1))
        unit_raw = match.group(2)
        unit = unit_raw.upper()

        # 注意：m（毫）和 M（兆）区别
        multipliers = {
            '': 1,
            'R': 1,
            'K': 1e3,
            'M': 1e6,
            'G': 1e9,
            'U': 1e-6,
            'μ': 1e-6,
            'N': 1e-9,
            'P': 1e-12,
        }
        if unit_raw == 'm':  # milli
            return val * 1e-3

        if 'F' in name_u:
            pass
        return val * multipliers.get(unit, 1)

    return float('inf')


# ==================== 📱 电子元器件 ====================
def render_electronics():
    st.markdown("## ☁️ 电子元器件")
    df = load_data(SHEET_ELEC)
    if df.empty:
        st.info("数据加载中...")
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("📦 种类", len(df))
    c2.metric("🔢 总数", int(df['数量'].sum()) if '数量' in df.columns else 0)
    low_stock = df[df['数量'] < 10] if '数量' in df.columns else df.iloc[0:0]
    c3.metric("⚠️ 缺货", len(low_stock), delta_color="inverse")

    st.markdown("---")
    tab1, tab2, tab3 = st.tabs(["📊 总览与管理", "📥 批量入库", "📤 BOM出库"])

    # === Tab 1: 管理 ===
    with tab1:
        col1, col2 = st.columns([1, 4])
        with col1:
            st.markdown("##### 🔍 筛选与搜索")
            filter_type = st.multiselect("按类型筛选", df['类型'].unique() if '类型' in df.columns else [])
            search = st.text_input("关键字搜索...", placeholder="输入型号/参数")
            st.divider()
            if st.button("🔄 刷新数据", use_container_width=True):
                st.rerun()

        with col2:
            display_df = df.copy()
            if filter_type and '类型' in display_df.columns:
                display_df = display_df[display_df['类型'].isin(filter_type)]
            if search:
                mask = display_df.astype(str).apply(lambda x: x.str.contains(search, case=False, na=False)).any(axis=1)
                display_df = display_df[mask]

            column_cfg = {}
            if "图片" in display_df.columns:
                column_cfg["图片"] = st.column_config.ImageColumn("图片预览")

            edited_df = data_editor_with_optional_selection(
                display_df=display_df,
                key="elec_editor_fix_v3",
                column_cfg=column_cfg,
                height=500
            )

            if st.button("💾 保存更改到云端", type="primary"):
                if save_data_smart(df, edited_df, SHEET_ELEC):
                    st.success("✅ 保存成功！所有更改已同步。")
                    time.sleep(1)
                    st.rerun()

    with tab2:
        up_file = st.file_uploader("上传 Excel 入库单", type=['xlsx'])
        if up_file:
            new_data = pd.read_excel(up_file)
            st.dataframe(new_data.head())
            if st.button("🚀 确认合并入库"):
                final_df = pd.concat([df, new_data], ignore_index=True)
                save_data_smart(final_df, final_df, SHEET_ELEC)
                st.success("入库成功！")
                st.rerun()

    with tab3:
        st.info("💡 提示：对于大批量BOM匹配，建议下载Excel在本地处理。")


# ==================== 🔩 五金螺丝 ====================
def render_screws():
    st.markdown("## 🔩 五金螺丝")
    df = load_data(SHEET_SCREW)
    if df.empty:
        st.info("数据加载中...")
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("📦 种类", len(df))
    c2.metric("🔢 总数", int(df['数量'].sum()) if '数量' in df.columns else 0)
    c3.metric("⚠️ 缺货", len(df[df['数量'] < 20]) if '数量' in df.columns else 0, delta_color="inverse")

    st.markdown("---")
    tab1, tab2, tab3 = st.tabs(["📊 总览与管理", "📥 快速入库", "📤 快捷领用"])

    with tab1:
        col1, col2 = st.columns([1, 4])
        with col1:
            st.markdown("##### 🔍 筛选与搜索")
            filter_type = st.multiselect("按类型筛选", df['类型'].unique() if '类型' in df.columns else [])
            filter_spec = st.multiselect("按规格筛选", df['规格'].unique() if '规格' in df.columns else [])
            search = st.text_input("关键字搜索...", placeholder="输入 M3 / 长度等")
            st.divider()
            if st.button("🔄 刷新数据", use_container_width=True, key="refresh_screw"):
                st.rerun()

        with col2:
            display_df = df.copy()
            if filter_type and '类型' in display_df.columns:
                display_df = display_df[display_df['类型'].isin(filter_type)]
            if filter_spec and '规格' in display_df.columns:
                display_df = display_df[display_df['规格'].isin(filter_spec)]
            if search:
                mask = display_df.astype(str).apply(lambda x: x.str.contains(search, case=False, na=False)).any(axis=1)
                display_df = display_df[mask]

            column_cfg = {}
            if "图片" in display_df.columns:
                column_cfg["图片"] = st.column_config.ImageColumn("图片预览")

            edited_df = data_editor_with_optional_selection(
                display_df=display_df,
                key="screw_editor_fix_v3",
                column_cfg=column_cfg,
                height=500
            )

            if st.button("💾 保存五金更改", type="primary"):
                if save_data_smart(df, edited_df, SHEET_SCREW):
                    st.success("✅ 保存成功！")
                    time.sleep(1)
                    st.rerun()

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
                    mask = (
                        (df['规格'].astype(str) == str(spec)) &
                        (df['长度'].astype(str) == str(length)) &
                        (df['类型'].astype(str) == str(stype))
                    )
                    if mask.any():
                        df.loc[mask, '数量'] = pd.to_numeric(df.loc[mask, '数量'], errors='coerce').fillna(0).astype(int) + int(qty)
                        st.toast(f"库存已累加: {spec}")
                    else:
                        new_row = pd.DataFrame([{
                            "规格": str(spec),
                            "长度": str(length),
                            "类型": str(stype),
                            "材质": "不锈钢",
                            "数量": int(qty),
                            "备注": ""
                        }])
                        df = pd.concat([df, new_row], ignore_index=True)
                        st.toast(f"新规格入库: {spec}")

                    save_data_smart(df, df, SHEET_SCREW)
                    time.sleep(1)
                    st.rerun()

    with tab3:
        st.write("### ➖ 快捷领用")
        if not df.empty:
            df2 = df.copy()
            df2['display_name'] = (
                df2.get('规格', '').astype(str) + " " +
                df2.get('长度', '').astype(str) + " " +
                df2.get('类型', '').astype(str) +
                " (余:" + df2.get('数量', 0).astype(str) + ")"
            )

            col_out_1, col_out_2 = st.columns([1, 2])
            with col_out_1:
                with st.form("screw_out"):
                    selected_item = st.selectbox("选择螺丝", df2['display_name'].tolist())
                    out_qty = st.number_input("领用数量", value=1, min_value=1)

                    if st.form_submit_button("确认出库"):
                        idx = df2[df2['display_name'] == selected_item].index[0]
                        current = int(df.at[idx, '数量'])
                        if current < out_qty:
                            st.error(f"库存不足！当前仅剩 {current}")
                        else:
                            df.at[idx, '数量'] = current - int(out_qty)
                            save_data_smart(df, df, SHEET_SCREW)
                            st.success("领用成功！")
                            time.sleep(1)
                            st.rerun()
        else:
            st.warning("暂无库存")


# ==================== 📟 PCB 电路板 ====================
def render_pcb():
    st.markdown("## 📟 PCB 电路板")
    df = load_data(SHEET_PCB)
    if df.empty:
        st.info("数据加载中...")
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("📦 板子型号", len(df))
    c2.metric("🔢 库存总数", int(df['数量'].sum()) if '数量' in df.columns else 0)
    c3.metric("⚠️ 低库存", len(df[df['数量'] < 5]) if '数量' in df.columns else 0, delta_color="inverse")

    st.markdown("---")
    tab1, tab2, tab3 = st.tabs(["📊 总览与管理", "📥 快速入库", "📤 快捷领用"])

    with tab1:
        col1, col2 = st.columns([1, 4])
        with col1:
            st.markdown("##### 🔍 筛选与搜索")
            filter_loc = st.multiselect("按位置筛选", df['位置'].unique() if '位置' in df.columns else [])
            search = st.text_input("搜索 PCB...", placeholder="名称 / 版本号")
            st.divider()
            if st.button("🔄 刷新数据", use_container_width=True, key="refresh_pcb"):
                st.rerun()

        with col2:
            display_df = df.copy()
            if filter_loc and '位置' in display_df.columns:
                display_df = display_df[display_df['位置'].isin(filter_loc)]
            if search:
                mask = display_df.astype(str).apply(lambda x: x.str.contains(search, case=False, na=False)).any(axis=1)
                display_df = display_df[mask]

            column_cfg = {
                "数量": st.column_config.NumberColumn("数量", min_value=0, step=1),
                "名称": st.column_config.TextColumn("名称", required=True),
            }
            if "图片" in display_df.columns:
                column_cfg["图片"] = st.column_config.ImageColumn("图片预览")

            edited_df = data_editor_with_optional_selection(
                display_df=display_df,
                key="pcb_editor_fix_v3",
                column_cfg=column_cfg,
                height=500
            )

            if st.button("💾 保存PCB更改", type="primary"):
                if save_data_smart(df, edited_df, SHEET_PCB):
                    st.success("✅ 保存成功！")
                    time.sleep(1)
                    st.rerun()

    with tab2:
        col_a, col_b = st.columns([1, 2])
        with col_a:
            with st.form("pcb_add"):
                st.write("### ➕ 新板入库")
                name = st.text_input("名称/版本号", placeholder="V1.0")
                size = st.text_input("尺寸", placeholder="10x10cm")
                loc = st.text_input("位置", placeholder="A-01")
                qty = st.number_input("数量", value=5, min_value=1)

                if st.form_submit_button("确认入库"):
                    mask = (df['名称'].astype(str) == str(name)) & (df['尺寸'].astype(str) == str(size)) if \
                        ('名称' in df.columns and '尺寸' in df.columns) else pd.Series([False] * len(df))

                    if mask.any():
                        df.loc[mask, '数量'] = pd.to_numeric(df.loc[mask, '数量'], errors='coerce').fillna(0).astype(int) + int(qty)
                        st.toast(f"库存已累加: {name}")
                    else:
                        new_row = pd.DataFrame([{
                            "名称": str(name),
                            "尺寸": str(size),
                            "数量": int(qty),
                            "位置": str(loc),
                            "备注": ""
                        }])
                        df = pd.concat([df, new_row], ignore_index=True)
                        st.toast(f"新板入库: {name}")

                    save_data_smart(df, df, SHEET_PCB)
                    time.sleep(1)
                    st.rerun()

    with tab3:
        st.write("### ➖ 快捷领用")
        if not df.empty:
            df2 = df.copy()
            df2['display_info'] = (
                df2.get('名称', '').astype(str) +
                " [" + df2.get('尺寸', '').astype(str) + "] " +
                "(余:" + df2.get('数量', 0).astype(str) + ")"
            )
            col_out_1, col_out_2 = st.columns([1, 2])
            with col_out_1:
                with st.form("pcb_out"):
                    selected_pcb = st.selectbox("选择板子", df2['display_info'].tolist())
                    out_qty = st.number_input("领用数量", value=1, min_value=1)

                    if st.form_submit_button("确认出库"):
                        idx = df2[df2['display_info'] == selected_pcb].index[0]
                        current = int(df.at[idx, '数量'])
                        if current < out_qty:
                            st.error("库存不足！")
                        else:
                            df.at[idx, '数量'] = current - int(out_qty)
                            save_data_smart(df, df, SHEET_PCB)
                            st.success("领用成功！")
                            time.sleep(1)
                            st.rerun()
        else:
            st.warning("暂无库存")


# ==================== 🚀 主入口 ====================
with st.sidebar:
    st.title("☁️ 云端管家")
    if 'username' in st.session_state:
        st.write(f"👤 **{st.session_state.username}**")
        if st.button("🚪 退出"):
            st.session_state.logged_in = False
            st.rerun()

    st.markdown("---")
    app_mode = st.radio("切换仓库", ["电子元器件", "五金螺丝", "PCB电路板"], label_visibility="collapsed")
    st.markdown("---")
    st.caption("Status: Online 🟢")

if app_mode == "电子元器件":
    render_electronics()
elif app_mode == "五金螺丝":
    render_screws()
else:
    render_pcb()
