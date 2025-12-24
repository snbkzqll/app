import os
import sys
import streamlit.web.cli as stcli

def resolve_path(path):
    # 这个函数是为了让 exe 找到打包在内部的文件
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, path)
    return os.path.join(os.path.abspath("."), path)

if __name__ == "__main__":
    # 模拟命令行启动 streamlit run inventory_app.py
    sys.argv = [
        "streamlit",
        "run",
        resolve_path("inventory_app.py"), # 这里必须是你主程序的名字
        "--global.developmentMode=false",
    ]
    sys.exit(stcli.main())