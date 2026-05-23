# Entry point for Streamlit Cloud — runs admin_app.py
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "admin_app.py"), encoding="utf-8") as _f:
    exec(compile(_f.read(), "admin_app.py", "exec"))
