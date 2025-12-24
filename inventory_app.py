import streamlit as st
import pandas as pd
import os
import re
import time
import base64

# ==================== 🎨 界面美化配置 ====================
st.set_page_config(page_title="实验室库存管家 Pro", page_icon="🔬", layout="wide")


# --- 核心函数：设置背景图 ---
def set_background(image_file, opacity):
    with open(image_file, "rb") as f:
        img_data = f.read()
    b64_encoded = base64.b64encode(img_data).decode()
    style = f"""
        <style>
        .stApp {{
            background-image: linear-gradient(rgba(243, 244, 246, {opacity}), rgba(243, 244, 246, {opacity})), url(data:image/png;base64,{b64_encoded});
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}
        </style>
    """
    st.markdown(style, unsafe_allow_html=True)


def local_css():
    st.markdown("""
    <style>
        [data-testid="stSidebar"] { background-color: #1e293b; opacity: 0.95; }
        [data-testid="stSidebar"] * { color: #f1f5f9 !important; }
        h1, h2, h3 {
            background: -webkit-linear-gradient(45deg, #2563eb, #9333ea);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            font-family: 'Segoe UI', sans-serif; font-weight: 800 !important;
            text-shadow: 0px 0px 2px rgba(255,255,255,0.5);
        }
        div[data-testid="metric-container"] {
            background-color: rgba(255, 255, 255, 0.85) !important;
            backdrop-filter: blur(5px); border: 1px solid rgba(255, 255, 255, 0.5);
            padding: 20px; border-radius: 15px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            transition: transform 0.2s;
        }
        div[data-testid="metric-container"]:hover {
            transform: translateY(-5px); box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        }
        [data-testid="stDataEditor"] {
            background-color: rgba(255, 255, 255, 0.9) !important;
            backdrop-filter: blur(5px); border-radius: 15px; padding: 15px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); border: 1px solid rgba(255, 255, 255, 0.5);
        }
        .stButton>button { border-radius: 50px; font-weight: bold; border: none; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    </style>
    """, unsafe_allow_html=True)


local_css()

# ==================== ⚙️ 配置区域 ====================
BASE_DIR = r'D:\OneDrive\元器件库'

INVENTORY_FILE = os.path.join(BASE_DIR, 'my_inventory.xlsx')
SCREW_FILE = os.path.join(BASE_DIR, 'my_screws.xlsx')
BG_CACHE_FILE = os.path.join(BASE_DIR, 'bg_image.png')

if not os.path.exists(BASE_DIR):
    os.makedirs(BASE_DIR, exist_ok=True)


# ==================== 🔧 通用核心函数 ====================

def get_sort_value(name):
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
        multiplier = multipliers.get(unit, 1)
        return val * multiplier
    return float('inf')


def load_excel(file_path, columns):
    if not os.path.exists(file_path):
        df = pd.DataFrame(columns=columns)
        df.to_excel(file_path, index=False)
        return df
    else:
        try:
            df = pd.read_excel(file_path)
            df.columns = df.columns.astype(str).str.strip()
            for col in columns:
                if col not in df.columns: df[col] = ''
            for col in columns:
                if col != '数量':
                    df[col] = df[col].astype(str).replace('nan', '').str.strip()
            df['数量'] = pd.to_numeric(df['数量'], errors='coerce').fillna(0).astype(int)
            return df
        except Exception as e:
            st.error(f"读取文件失败: {e}")
            return pd.DataFrame(columns=columns)


def save_excel(df, file_path):
    try:
        save_df = df.copy()
        for hidden in ['sort_key', '数值权重']:
            if hidden in save_df.columns:
                save_df = save_df.drop(columns=[hidden])
        save_df.to_excel(file_path, index=False)
        return True
    except PermissionError:
        st.error(f"⚠️ 保存失败！请关闭 '{os.path.basename(file_path)}'。")
        return False


def get_default_index(options, keywords):
    for idx, opt in enumerate(options):
        for kw in keywords:
            if kw in str(opt): return idx
    return 0


# ==================== 📱 系统 1: 电子元器件 ====================
def render_electronics_app():
    st.markdown("## 📱 电子元器件控制台")
    E_COLS = ['名称', '参数', '类型', '封装', '数量', '位置', '备注']
    if 'df_elec' not in st.session_state:
        st.session_state.df_elec = load_excel(INVENTORY_FILE, E_COLS)
    df = st.session_state.df_elec

    # --- 仪表盘 ---
    total_items = len(df)
    total_qty = df['数量'].sum()
    low_stock = df[df['数量'] < 10]
    low_stock_count = len(low_stock)

    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("📦 器件种类", f"{total_items}", delta="SKU")
    kpi2.metric("🔢 库存总数", f"{total_qty}", delta="PCS")
    kpi3.metric("⚠️ 低库存 (<10)", f"{low_stock_count}", delta="需补货", delta_color="inverse")

    if low_stock_count > 0:
        with st.expander(f"🔴 查看 {low_stock_count} 个库存紧张的器件", expanded=False):
            # 修复警告：use_container_width -> width='stretch'
            st.dataframe(low_stock[['名称', '参数', '数量', '位置']], width='stretch')

    st.markdown("---")

    tab1, tab2, tab3 = st.tabs(["📊 库存总览", "📥 详细入库", "📤 BOM出库"])

    with tab1:
        c1, c2 = st.columns([1.5, 5])
        with c1:
            st.markdown("##### 🛠 筛选与排序")
            sort_mode = st.selectbox(
                "🔃 排序方式",
                ["智能排序 (类型>名称>参数)", "按库存 (从多到少)", "按库存 (从少到多)", "最近入库 (倒序)"]
            )

            existing_types = list(df['类型'].unique())
            existing_pkgs = list(df['封装'].unique())

            filter_type = st.multiselect("按类型", [x for x in existing_types if x])
            filter_pkg = st.multiselect("按封装", [x for x in existing_pkgs if x])
            search_txt = st.text_input("🔍 搜索", placeholder="输入型号/参数...")

            st.write("")
            # 修复警告：use_container_width -> width='stretch'
            if st.button("🔄 刷新全表", use_container_width=True):
                st.session_state.df_elec = load_excel(INVENTORY_FILE, E_COLS)
                st.rerun()

        with c2:
            display_df = df.copy()
            if filter_type: display_df = display_df[display_df['类型'].isin(filter_type)]
            if filter_pkg: display_df = display_df[display_df['封装'].isin(filter_pkg)]
            if search_txt:
                mask = display_df.astype(str).apply(lambda x: x.str.contains(search_txt, case=False)).any(axis=1)
                display_df = display_df[mask]

            if sort_mode == "智能排序 (类型>名称>参数)":
                display_df['数值权重'] = display_df['参数'].apply(get_sort_value)
                display_df = display_df.sort_values(by=['类型', '名称', '数值权重'], ascending=[True, True, True])
            elif sort_mode == "按库存 (从多到少)":
                display_df = display_df.sort_values(by=['数量'], ascending=False)
            elif sort_mode == "按库存 (从少到多)":
                display_df = display_df.sort_values(by=['数量'], ascending=True)
            elif sort_mode == "最近入库 (倒序)":
                display_df = display_df.sort_index(ascending=False)

            final_df = display_df[E_COLS].copy()
            final_df.index = range(1, len(final_df) + 1)

            # 修复警告：use_container_width -> width='stretch'
            edited_df = st.data_editor(
                final_df,
                column_config={
                    "名称": st.column_config.TextColumn("名称", width="medium", required=True),
                    "参数": st.column_config.TextColumn("参数", width="medium"),
                    "类型": st.column_config.TextColumn("分类", width="small"),
                    "封装": st.column_config.TextColumn("封装", width="small"),
                    "数量": st.column_config.NumberColumn("库存", format="%d"),
                    "位置": st.column_config.TextColumn("📍 位置", width="small"),
                    "备注": st.column_config.TextColumn("备注", width="medium"),
                },
                width='stretch', num_rows="dynamic", hide_index=False, key="elec_editor", height=500
            )

            if not final_df.reset_index(drop=True).equals(edited_df.reset_index(drop=True)):
                if save_excel(edited_df, INVENTORY_FILE):
                    st.session_state.df_elec = edited_df.reset_index(drop=True)
                    st.toast("已保存更改", icon="💾")

    with tab2:
        c_up, c_info = st.columns([1, 1])
        with c_up:
            up_in = st.file_uploader("📂 拖拽上传入库单 (Excel)", type=['xlsx', 'xls'], key="e_in")
        with c_info:
            st.info("💡 提示：Excel 导入支持自定义类型。")
        if up_in:
            df_new = pd.read_excel(up_in)
            cols = list(df_new.columns)
            cc1, cc2, cc3, cc4, cc5 = st.columns(5)
            c_name = cc1.selectbox("名称", cols, index=get_default_index(cols, ['名称', 'Name']))
            c_param = cc2.selectbox("参数", ["(无)"] + cols, index=get_default_index(cols, ['参数', '值', 'Value']))
            c_qty = cc3.selectbox("数量", cols, index=get_default_index(cols, ['数量', 'Qty']))
            c_pkg = cc4.selectbox("封装", ["(无)"] + cols, index=get_default_index(cols, ['封装']))
            c_type = cc5.selectbox("类型", ["(无)"] + cols, index=get_default_index(cols, ['类型']))
            if st.button("🚀 开始入库", type="primary"):
                curr = load_excel(INVENTORY_FILE, E_COLS)
                cnt = 0
                for _, row in df_new.iterrows():
                    name = str(row[c_name]).strip()
                    if not name or name == 'nan': continue
                    try:
                        qty = int(row[c_qty])
                    except:
                        qty = 0
                    param = str(row[c_param]).strip() if c_param != "(无)" and str(row[c_param]) != 'nan' else ""
                    pkg = str(row[c_pkg]).strip() if c_pkg != "(无)" and str(row[c_pkg]) != 'nan' else ""
                    typ = str(row[c_type]).strip() if c_type != "(无)" and str(row[c_type]) != 'nan' else ""
                    mask = (curr['名称'] == name)
                    if param: mask = mask & (curr['参数'] == param)
                    if pkg: mask = mask & (curr['封装'] == pkg)
                    if mask.any():
                        idx = curr[mask].index[0]
                        curr.at[idx, '数量'] += qty
                        if typ and not curr.at[idx, '类型']: curr.at[idx, '类型'] = typ
                    else:
                        new_row = pd.DataFrame(
                            {'名称': [name], '参数': [param], '类型': [typ], '封装': [pkg], '数量': [qty], '位置': [''],
                             '备注': ['']})
                        curr = pd.concat([curr, new_row], ignore_index=True)
                    cnt += 1
                save_excel(curr, INVENTORY_FILE)
                st.session_state.df_elec = curr
                st.balloons()
                st.success(f"成功入库 {cnt} 条数据！")
                time.sleep(1)
                st.rerun()

    with tab3:
        st.markdown("#### 📤 智能 BOM 扣减")
        up_out = st.file_uploader("📂 上传 BOM 清单", type=['xlsx', 'xls'], key="e_out")
        if up_out and st.session_state.get('last_bom_name') != up_out.name:
            st.session_state.last_bom_name = up_out.name
            st.session_state.bom_res = None
        if up_out:
            df_bom = pd.read_excel(up_out)
            cols = list(df_bom.columns)
            c1, c2, c3, c4 = st.columns(4)
            t_name = c1.selectbox("BOM名称", cols, index=get_default_index(cols, ['名称', 'Model']))
            t_param = c2.selectbox("BOM参数", ["(无)"] + cols, index=get_default_index(cols, ['参数', '值', 'Value']))
            t_qty = c3.selectbox("BOM数量", cols, index=get_default_index(cols, ['数量', 'Qty']))
            t_pkg = c4.selectbox("BOM封装", ["(无)"] + cols, index=get_default_index(cols, ['封装']))
            # 修复警告：use_container_width -> width='stretch'
            if st.button("🔍 检查库存匹配", use_container_width=True):
                temp = st.session_state.df_elec.copy()
                valid, missing = [], []
                for _, row in df_bom.iterrows():
                    name = str(row[t_name]).strip()
                    if not name or "无货" in name: continue
                    try:
                        q = int(row[t_qty])
                    except:
                        q = 1
                    bparam = str(row[t_param]).strip() if t_param != "(无)" and str(row[t_param]) != 'nan' else ""
                    bpkg = str(row[t_pkg]).strip() if t_pkg != "(无)" and str(row[t_pkg]) != 'nan' else ""
                    mask = temp['名称'] == name
                    if bparam: mask = mask & (temp['参数'] == bparam)
                    if bpkg: mask = mask & (temp['封装'] == bpkg)
                    if mask.any():
                        idx = temp[mask].index[0]
                        curr_q = temp.at[idx, '数量']
                        if curr_q >= q:
                            valid.append({'index': idx, 'qty': q})
                        else:
                            missing.append(f"❌ 不足: {name} {bparam} (需{q}, 存{curr_q})")
                    else:
                        missing.append(f"❓ 未找到: {name} {bparam}")
                st.session_state.bom_res = {'valid': valid, 'missing': missing}
            if st.session_state.get('bom_res'):
                res = st.session_state.bom_res
                if not res['missing']:
                    st.success("✅ 完美匹配！")
                    if st.button("🚀 立即执行扣减", type="primary"):
                        curr = st.session_state.df_elec.copy()
                        for a in res['valid']: curr.at[a['index'], '数量'] -= a['qty']
                        save_excel(curr, INVENTORY_FILE)
                        st.session_state.df_elec = curr
                        st.session_state.bom_res = None
                        st.balloons()
                        st.rerun()
                else:
                    st.error(f"发现 {len(res['missing'])} 个问题")
                    # 修复警告：use_container_width -> width='stretch'
                    st.dataframe(res['missing'], width='stretch')
                    if res['valid'] and st.button(f"⚠️ 强行扣减匹配的 {len(res['valid'])} 项", type="secondary"):
                        curr = st.session_state.df_elec.copy()
                        for a in res['valid']: curr.at[a['index'], '数量'] -= a['qty']
                        save_excel(curr, INVENTORY_FILE)
                        st.session_state.df_elec = curr
                        st.session_state.bom_res = None
                        st.balloons()
                        st.rerun()


# ==================== 🔩 系统 2: 螺丝/五金 ====================
def render_screws_app():
    st.markdown("## 🔩 五金件控制台")
    S_COLS = ['规格', '类型', '长度', '材质', '数量', '备注']

    if 'df_screw' not in st.session_state:
        st.session_state.df_screw = load_excel(SCREW_FILE, S_COLS)
    df = st.session_state.df_screw

    total_items = len(df)
    total_qty = df['数量'].sum()
    low_stock = df[df['数量'] < 20]
    low_stock_count = len(low_stock)

    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("📦 五金种类", f"{total_items}", delta="SKU")
    kpi2.metric("🔢 库存总数", f"{total_qty}", delta="PCS")
    kpi3.metric("⚠️ 低库存 (<20)", f"{low_stock_count}", delta="需补货", delta_color="inverse")

    if low_stock_count > 0:
        with st.expander(f"🔴 查看 {low_stock_count} 个库存紧张的五金件"):
            # 修复警告：use_container_width -> width='stretch'
            st.dataframe(low_stock[['规格', '长度', '类型', '数量']], width='stretch')

    st.markdown("---")

    c1, c2 = st.columns([2, 5])

    with c1:
        st.markdown("### ⚡ 快速操作")
        # 修复警告：use_container_width -> width='stretch'
        if st.button("🔄 刷新数据", use_container_width=True):
            st.session_state.df_screw = load_excel(SCREW_FILE, S_COLS)
            st.rerun()

        st.write("")

        op_tab1, op_tab2 = st.tabs(["🟢 入库 (加)", "🔴 出库 (拿)"])
        with op_tab1:
            with st.container(border=True):
                q_spec = st.text_input("规格", placeholder="如 M3", key="qs1")
                col_l, col_t = st.columns(2)
                q_len = col_l.text_input("长度", placeholder="10mm", key="qs2")
                q_type = col_t.text_input("头型/种类", placeholder="如: 圆头", key="qs3")
                q_qty = st.number_input("数量", min_value=1, value=50, step=10, key="qs4")
                # 修复警告：use_container_width -> width='stretch'
                if st.button("➕ 确认入库", use_container_width=True, type="primary"):
                    if q_spec:
                        mask = (df['规格'] == q_spec) & (df['长度'] == q_len) & (df['类型'] == q_type)
                        if mask.any():
                            df.loc[mask, '数量'] += q_qty
                            st.toast(f"库存已累加: {q_spec} +{q_qty}", icon="✅")
                        else:
                            new_row = pd.DataFrame({
                                '规格': [q_spec], '类型': [q_type], '长度': [q_len],
                                '材质': ['不锈钢'], '数量': [q_qty], '备注': ['']
                            })
                            df = pd.concat([df, new_row], ignore_index=True)
                            st.toast(f"新规格入库: {q_spec}", icon="✨")
                        save_excel(df, SCREW_FILE)
                        st.session_state.df_screw = df
                        time.sleep(0.5)
                        st.rerun()

        with op_tab2:
            with st.container(border=True):
                if df.empty:
                    st.warning("暂无库存，无法出库")
                else:
                    item_map = {
                        f"{row['规格']} - {row['长度']} - {row['类型']} (余:{row['数量']})": i
                        for i, row in df.iterrows() if row['数量'] > 0
                    }
                    if not item_map:
                        st.info("库存全部为 0，无法出库")
                    else:
                        selected_label = st.selectbox("选择物料", list(item_map.keys()), key="out_sel")
                        take_qty = st.number_input("拿取数量", min_value=1, value=1, key="out_qty")
                        # 修复警告：use_container_width -> width='stretch'
                        if st.button("➖ 确认出库", use_container_width=True):
                            idx = item_map[selected_label]
                            current_qty = df.at[idx, '数量']
                            if current_qty >= take_qty:
                                df.at[idx, '数量'] -= take_qty
                                save_excel(df, SCREW_FILE)
                                st.session_state.df_screw = df
                                st.toast(f"已出库 {take_qty} 个", icon="📉")
                                time.sleep(0.5)
                                st.rerun()
                            else:
                                st.error(f"库存不足！当前只有 {current_qty} 个")

    with c2:
        st.markdown("### 📋 五金清单")
        c_sort_s, c_ph_s = st.columns([1, 2])
        with c_sort_s:
            sort_mode_s = st.selectbox(
                "🔃 排序方式",
                ["智能排序 (规格>长度)", "按库存 (从多到少)", "按库存 (从少到多)"],
                key="sort_screw"
            )

        display_df = df.copy()
        if sort_mode_s == "智能排序 (规格>长度)":
            display_df = display_df.sort_values(by=['规格', '长度'])
        elif sort_mode_s == "按库存 (从多到少)":
            display_df = display_df.sort_values(by=['数量'], ascending=False)
        elif sort_mode_s == "按库存 (从少到多)":
            display_df = display_df.sort_values(by=['数量'], ascending=True)

        display_df.index = range(1, len(display_df) + 1)

        # 修复警告：use_container_width -> width='stretch'
        edited_df = st.data_editor(
            display_df,
            column_config={
                "规格": st.column_config.TextColumn("规格", required=True),
                "类型": st.column_config.TextColumn("头型/种类", width="small"),
                "长度": st.column_config.TextColumn("长度"),
                "材质": st.column_config.TextColumn("材质"),
                "数量": st.column_config.NumberColumn("库存", format="%d"),
            },
            width='stretch', num_rows="dynamic", hide_index=False, height=500, key="screw_editor"
        )

        if not display_df.reset_index(drop=True).equals(edited_df.reset_index(drop=True)):
            if save_excel(edited_df, SCREW_FILE):
                st.session_state.df_screw = edited_df.reset_index(drop=True)
                st.toast("五金库存已保存", icon="💾")


# ==================== 🚀 侧边栏导航与设置 ====================
with st.sidebar:
    st.markdown("### 🧰 实验室管家")
    st.markdown("---")
    app_mode = st.radio("工作区:", ["📱 电子元器件", "🔩 螺丝/五金"], index=0, label_visibility="collapsed")
    st.markdown("---")
    st.info(f"📂 **当前仓库:**\n{os.path.basename(BASE_DIR)}")

    st.markdown("### 🎨 个性化设置")
    bg_img_file = st.file_uploader("上传背景图", type=['png', 'jpg', 'jpeg'], key='bg_uploader')
    saved_bg_path = None
    if os.path.exists(BG_CACHE_FILE): saved_bg_path = BG_CACHE_FILE
    current_bg = None
    if bg_img_file:
        with open(BG_CACHE_FILE, "wb") as f:
            f.write(bg_img_file.getbuffer())
        current_bg = BG_CACHE_FILE
    elif saved_bg_path:
        current_bg = saved_bg_path
    bg_opacity = st.slider("背景遮罩浓度", 0.0, 1.0, 0.85)
    if current_bg: set_background(current_bg, bg_opacity)
    st.caption("v2.6 Pro | 排序修复版")

if app_mode == "📱 电子元器件":
    render_electronics_app()
elif app_mode == "🔩 螺丝/五金":
    render_screws_app()