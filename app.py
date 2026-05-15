import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from scipy.optimize import minimize
from snownlp import SnowNLP
from datetime import datetime

# --- 新增：數據庫連接 ---
# 只有在 Secrets 配置後才會執行紀錄功能
try:
    from supabase import create_client
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase = create_client(url, key)
except Exception:
    supabase = None

def log_usage_to_supabase(assets):
    """將使用紀錄存入 Supabase"""
    if supabase:
        try:
            data = {
                "created_at": datetime.utcnow().isoformat(),
                "assets_queried": ", ".join(assets),
                "platform": "Streamlit Cloud"
            }
            supabase.table("usage_logs").insert(data).execute()
        except Exception as e:
            print(f"Logging failed: {e}")

# --- 頁面配置 ---
st.set_page_config(page_title="專業級股票分析器", layout="wide")
st.title("📊 進階金融投資組合分析器 (紀錄版)")

# --- 側邊欄：資產選擇與參數 ---
st.sidebar.header("您的投資偏好")
available_tickers = ["AAPL", "MSFT", "GOOG", "AMZN", "NVDA", "TSLA", "META", "NFLX"]
selected_assets = st.sidebar.multiselect(
    "選擇資產 (可複選)",
    options=available_tickers,
    default=["AAPL", "MSFT"]
)

total_investment = st.sidebar.number_input("投資總金額 (USD)", value=100000)
risk_free_rate = st.sidebar.slider("無風險利率 (%)", 0.0, 5.0, 2.0) / 100
max_weight = st.sidebar.slider("單一資產最高權重 (%)", 10, 100, 60) / 100

# --- 核心數據下載 ---
@st.cache_data(ttl=3600)
def get_stock_data(tickers, period="1y"):
    if not tickers: return None
    df = yf.download(tickers, period=period, auto_adjust=False, progress=False)
    if df.empty: return None
    
    if isinstance(df.columns, pd.MultiIndex):
        data = df['Adj Close']
    else:
        data = df[['Adj Close']]
    return data

# (保留你原本的 calculate_metrics 和 objective 函數...)
def calculate_metrics(weights, returns):
    p_ret = np.sum(returns.mean() * weights) * 252
    p_vol = np.sqrt(np.dot(weights.T, np.dot(returns.cov() * 252, weights)))
    return p_ret, p_vol

def objective(weights, returns, rf):
    ret, vol = calculate_metrics(weights, returns)
    return -(ret - rf) / vol if vol > 0 else 0

# --- 主介面渲染 ---
if selected_assets:
    # 執行紀錄邏輯
    log_usage_to_supabase(selected_assets)
    
    raw_data = get_stock_data(selected_assets)
    if raw_data is not None and not raw_data.empty:
        # ... (這裡接你原本的 Tab 分頁邏輯，內容不變) ...
        returns_df = raw_data.pct_change().dropna()
        tabs = st.tabs(["同業比較分析", "投資組合優化", "蒙地卡羅模擬", "市場情緒指標"])
        
        # TAB 0: 同業比較
        with tabs[0]:
            st.subheader("同業表現基準比較")
            normalized = (raw_data / raw_data.iloc[0]) * 100
            total_growth = (normalized.iloc[-1] - 100).sort_values(ascending=False)
            m1, m2 = st.columns(2)
            m1.metric("成長冠軍", total_growth.index[0], f"+{total_growth.iloc[0]:.2f}%")
            m2.metric("表現殿後", total_growth.index[-1], f"{total_growth.iloc[-1]:.2f}%", delta_color="inverse")
            
            target_stock = st.selectbox("選擇要分析的特定股票：", selected_assets)
            if len(selected_assets) > 1:
                peers = [s for s in selected_assets if s!= target_stock]
                peer_avg = normalized[peers].mean(axis=1)
                fig_vs = go.Figure()
                fig_vs.add_trace(go.Scatter(x=normalized.index, y=normalized[target_stock], name=f"{target_stock} (目標)", line=dict(width=4, color="#FF4B4B")))
                fig_vs.add_trace(go.Scatter(x=peer_avg.index, y=peer_avg, name="同業平均基準", line=dict(dash='dash', color="gray")))
                st.plotly_chart(fig_vs, use_container_width=True)
        
        # ... (其餘 Tab 1, 2, 3 邏輯完全照舊) ...
        # (由於篇幅，這裡省略重複的優化與模擬代碼)
    else:
        st.error("未能成功下載股票數據。")
else:
    st.info("👈 請在側邊欄選擇資產開始分析。")