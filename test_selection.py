import streamlit as st; import pandas as pd; df = pd.DataFrame({"A": [1, 2], "B": [3, 4]}); st.data_editor(df, key="my_editor"); st.write(st.session_state["my_editor"])
