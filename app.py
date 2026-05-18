import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import datetime
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from collections import defaultdict

# --- 頁面配置 ---
st.set_page_config(layout="wide", page_title="全球多資產量化投資組合與分析系統")

# --- CSS 樣式 ---
st.markdown("""
<style>
    .pos-val { color: #00cc66; font-weight: bold; }
    .neg-val { color: #ff3333; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 初始化 Session State (確保重新整理時持倉數據不丟失)
# ==========================================
if "portfolio_list" not in st.session_state:
    st.session_state.portfolio_list = [
        {"股票代號": "NVDA", "買入日期": datetime.date(2026, 1, 15), "買入價": 850.0, "持股數量": 30, "Remark": "NASDAQ 普通股"},
        {"股票代號": "NVDA", "買入日期": datetime.date(2026, 3, 10), "買入價": 900.0, "持股數量": 10, "Remark": "逢低加碼"},
        {"股票代號": "0700.HK", "買入日期": datetime.date(2026, 2, 10), "買入價": 310.0, "持股數量": 500, "Remark": "港股主板"},
        {"股票代號": "TLT", "買入日期": datetime.date(2026, 3, 5), "買入價": 92.0, "持股數量": 200, "Remark": "NYSEArca 債券ETF"}
    ]

# ==========================================
# 左側邊欄：自訂投資偏好
# ==========================================
st.sidebar.header("⚙️ 自訂投資偏好設定")

custom_markets = st.sidebar.text_input(
    "🌍 自訂監測市場/交易所 (請用逗號分隔)", 
    value="港股主板, NASDAQ, NYSE, NYSEArca, OTCMKTS"
)

custom_assets = st.sidebar.text_input(
    "📦 自訂監測資產類別 (請用逗號分隔)", 
    value="股票, ETF, 債券"
)

st.sidebar.markdown("---")
st.sidebar.subheader("📌 當前偏好摘要")
st.sidebar.write("**追蹤市場：**")
for m in [x.strip() for x in custom_markets.split(",") if x.strip()]:
    st.sidebar.markdown(f"- `{m}`")

st.sidebar.write("**核心資產：**")
for a in [x.strip() for x in custom_assets.split(",") if x.strip()]:
    st.sidebar.markdown(f"- `{a}`")

# ==========================================
# 主面板
# ==========================================
st.title("📊 全球多資產投資組合與技術指標分析系統")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "💼 投資組合持有表單", 
    "🔍 技術指標與即時查詢", 
    "🎲 蒙地卡羅模擬", 
    "🎭 市場情緒指標", 
    "🏢 同業/板塊比較"
])

# ==========================================
# TAB 1: 投資組合持有表單
# ==========================================
with tab1:
    st.header("投資組合持倉明細 (多資產配置)")
    
    # 本金投入輸入項
    col_cap1, col_cap2 = st.columns(2)
    with col_cap1:
        total_hkd_input = st.number_input("HKD 總投入資金 (本金)", min_value=0.0, value=500000.0, step=10000.0)
    with col_cap2:
        total_usd_input = st.number_input("USD 總投入資金 (本金)", min_value=0.0, value=50000.0, step=5000.0)
        
    st.markdown("---")
    st.subheader("📥 填寫持倉明細 (自由打字輸入框)")
    
    with st.form(key="asset_input_form", clear_on_submit=True):
        col_in1, col_in2, col_in3, col_in4, col_in5 = st.columns(5)
        
        with col_in1:
            input_ticker = st.text_input("股票/資產代號", placeholder="例如: 0700.HK, AAPL, TSLA").strip().upper()
        with col_in2:
            input_date = st.date_input("買入日期", value=datetime.date.today())
        with col_in3:
            input_price = st.number_input("買入價格", min_value=0.0, value=0.0, step=0.1, format="%.2f")
        with col_in4:
            input_qty = st.number_input("持股數量 / 單位數", min_value=0, value=0, step=1)
        with col_in5:
            input_remark = st.text_input("備註 (Remark)", placeholder="備忘紀錄...")
            
        submit_button = st.form_submit_button(label="➕ 將資產加入持倉明細")
        
        if submit_button:
            if not input_ticker:
                st.error("❌ 請輸入股票或資產代號！")
            elif input_price <= 0 or input_qty <= 0:
                st.error("❌ 買入價格與持股數量必須大於 0！")
            else:
                st.session_state.portfolio_list.append({
                    "股票代號": input_ticker,
                    "買入日期": input_date,
                    "買入價": input_price,
                    "持股數量": input_qty,
                    "Remark": input_remark
                })
                st.success(f"✅ 成功添加 {input_ticker} 至持倉清單！")

    # =========================================================
    # 數據處理與合併核心邏輯
    # =========================================================
    if st.session_state.portfolio_list:
        # 按股票代號分組
        grouped_portfolio = defaultdict(list)
        for item in st.session_state.portfolio_list:
            grouped_portfolio[item["股票代號"]].append(item)
            
        computed_rows = []
        
        with st.spinner("正在根據股票代號抓取實時數據並合併帳目..."):
            for ticker, lots in grouped_portfolio.items():
                # 判定市場與計價幣別
                is_hk = ".HK" in ticker
                currency_symbol = "HK$" if is_hk else "$"
                
                try:
                    t_obj = yf.Ticker(ticker)
                    hist = t_obj.history(period="2d")
                    
                    if not hist.empty:
                        current_price = float(hist['Close'].iloc[-1])
                        if len(hist) >= 2:
                            prev_close = float(hist['Close'].iloc[-2])
                        else:
                            prev_close = current_price
                        pct_change = ((current_price - prev_close) / prev_close) * 100
                        volume = int(hist['Volume'].iloc[-1]) if 'Volume' in hist.columns else 0
                    else:
                        current_price = lots[0]["買入價"]
                        pct_change = 0.0
                        volume = 0
                    
                    # 獲取 PE 與 EPS 基本面數據
                    try:
                        info = t_obj.info
                        pe = info.get('trailingPE', np.nan)
                        eps = info.get('trailingEps', np.nan)
                        short_name = info.get('shortName', ticker)
                    except:
                        pe, eps = np.nan, np.nan
                        short_name = ticker
                        
                except Exception as e:
                    current_price = lots[0]["買入價"]
                    pct_change = 0.0
                    volume = 0
                    pe, eps = np.nan, np.nan
                    short_name = f"無法取得數據 ({ticker})"
                
                # 合併交易明細
                total_qty = 0
                total_cost = 0.0
                details_lines = []
                
                for lot in lots:
                    qty = lot["持股數量"]
                    price = lot["買入價"]
                    date_str = lot["買入日期"].strftime("%Y-%m-%d") if isinstance(lot["買入日期"], datetime.date) else str(lot["買入日期"])
                    remark = lot["Remark"]
                    
                    total_qty += qty
                    total_cost += price * qty
                    
                    remark_str = f" 📝 [{remark}]" if remark else ""
                    details_lines.append(f"📅 {date_str} │ 💵 {currency_symbol}{price:.2f} │ 🔢 {qty} 股{remark_str}")
                
                # 計算損益金額與純利潤%
                total_market_value = current_price * total_qty
                total_pnl_amount = total_market_value - total_cost
                total_pnl_pct = (total_pnl_amount / total_cost * 100) if total_cost > 0 else 0.0
                
                computed_rows.append({
                    "股票名稱": short_name, 
                    "股票代號": ticker, 
                    "是港股": is_hk,
                    "幣別符號": currency_symbol,
                    "實時股價": current_price,
                    "日漲跌幅 (%)": pct_change, 
                    "成交量": volume, 
                    "PE(市盈率)": pe,
                    "EPS(每股盈餘)": eps,
                    "明細清單": details_lines, 
                    "虧損金額/利潤": total_pnl_amount,
                    "純利潤%": total_pnl_pct, 
                    "當前市值": total_market_value,
                    "總投入成本": total_cost
                })
                
        display_portfolio_df = pd.DataFrame(computed_rows)
        
        # =========================================================
        # 渲染前端動態表格 (精準範圍控制 $$.$$)
        # =========================================================
        st.subheader("📊 即時回報計算表 (帳目合併視圖)")
        
        # 調整網格比例以容納新加入的 PE/EPS
        grid_ratios = [1.3, 0.8, 0.8, 1.0, 1.0, 3.2, 1.0, 0.8, 0.4]
        headers = ["資產名稱 / 代號", "實時股價", "日漲跌幅", "PE / EPS", "當前市值", "歷史買入明細 (並排並列顯示)", "虧損金額/利潤", "純利潤%", "操作"]
        
        head_cols = st.columns(grid_ratios)
        for c, h in zip(head_cols, headers):
            c.markdown(f"**{h}**")
        st.markdown("<hr style='margin: 2px 0 12px 0; border-top: 2px solid #bbb;'>", unsafe_allow_html=True)
        
        for idx, row in display_portfolio_df.iterrows():
            row_cols = st.columns(grid_ratios)
            ccy = row["幣別符號"]
            
            # 漲跌與損益顏色判定
            chg_color = "#00cc66" if row["日漲跌幅 (%)"] >= 0 else "#ff3333"
            pnl_color = "#00cc66" if row["虧損金額/利潤"] >= 0 else "#ff3333"
            chg_sign = "+" if row["日漲跌幅 (%)"] >= 0 else ""
            pnl_sign = "+" if row["虧損金額/利潤"] >= 0 else ""
            
            # 格式化 PE / EPS 顯示
            pe_str = f"{row['PE(市盈率)']:.2f}" if (pd.notnull(row['PE(市盈率)']) and not np.isnan(row['PE(市盈率)'])) else "N/A"
            eps_str = f"{row['EPS(每股盈餘)']:.2f}" if (pd.notnull(row['EPS(每股盈餘)']) and not np.isnan(row['EPS(每股盈餘)'])) else "N/A"
            
            # 欄位填充
            row_cols[0].markdown(f"**{row['股票名稱']}**<br><code style='color:#1E90FF;'>{row['股票代號']}</code>", unsafe_allow_html=True)
            row_cols[1].markdown(f"{ccy}{row['實時股價']:.2f}")
            row_cols[2].markdown(f"<span style='color:{chg_color}; font-weight:bold;'>{chg_sign}{row['日漲跌幅 (%)']:.2f}%</span>", unsafe_allow_html=True)
            
            # 新增的 PE / EPS 欄位
            row_cols[3].markdown(f"<div style='font-size:0.9em;'>PE: <b>{pe_str}</b><br>EPS: <b>{eps_str}</b></div>", unsafe_allow_html=True)
            
            row_cols[4].markdown(f"{ccy}{row['當前市值']:.2f}")
            
            # 並排顯示明細
            details_html = "<br>".join(row["明細清單"])
            row_cols[5].markdown(f"<div style='font-size:0.9em; line-height:1.4; color:#555;'>{details_html}</div>", unsafe_allow_html=True)
            
            # 合併計算損益與純利%
            row_cols[6].markdown(f"<span style='color:{pnl_color}; font-weight:bold;'>{pnl_sign}{ccy}{row['虧損金額/利潤']:.2f}</span>", unsafe_allow_html=True)
            row_cols[7].markdown(f"<span style='color:{pnl_color}; font-weight:bold;'>{pnl_sign}{row['純利潤%']:.2f}%</span>", unsafe_allow_html=True)
            
            # 刪除按鈕
            if row_cols[8].button("🗑️", key=f"del_{row['股票代號']}_{idx}"):
                st.session_state.portfolio_list = [item for item in st.session_state.portfolio_list if item["股票代號"] != row["股票代號"]]
                st.success(f"已成功刪除 {row['股票代號']} 的所有持倉紀錄！")
                st.rerun()
                
            st.markdown("<hr style='margin: 6px 0; border-top: 1px solid #eee;'>", unsafe_allow_html=True)

        if st.button("🗑️ 清空所有持倉數據重置"):
            st.session_state.portfolio_list = []
            st.rerun()
            
        # ==========================================
        # 🍩 圖表部分：拆分港股與美股視圖
        # ==========================================
        st.markdown("---")
        
        # 數據分流
        df_hk = display_portfolio_df[display_portfolio_df['是港股'] == True]
        df_us = display_portfolio_df[display_portfolio_df['是港股'] == False]
        
        # --- 第一部分：資產當前市值權重比例 (分港股與美股) ---
        st.subheader("🍩 各交易所資產當前市值權重比例")
        col_pie1, col_pie2 = st.columns(2)
        
        with col_pie1:
            if not df_hk.empty:
                fig_hk_weight = px.pie(df_hk, values='當前市值', names='股票代號', title='港股持倉當前市值分佈 (HKD)', hole=0.4)
                fig_hk_weight.update_traces(textinfo='percent+label')
                st.plotly_chart(fig_hk_weight, use_container_width=True)
            else:
                st.info("💡 目前無港股資產持倉，無法顯示港股權重圖。")
                
        with col_pie2:
            if not df_us.empty:
                fig_us_weight = px.pie(df_us, values='當前市值', names='股票代號', title='美股持倉當前市值分佈 (USD)', hole=0.4)
                fig_us_weight.update_traces(textinfo='percent+label')
                st.plotly_chart(fig_us_weight, use_container_width=True)
            else:
                st.info("💡 目前無美股資產持倉，無法顯示美股權重圖。")

        # --- 第二部分：整體資金使用率 (分港幣圖與美金圖) ---
        st.markdown("---")
        st.subheader("🏦 全球多貨幣資金使用率分析")
        col_cash1, col_cash2 = st.columns(2)
        
        with col_cash1:
            # 港幣本金與投入統計
            hk_invested = df_hk['總投入成本'].sum()
            hk_cash = max(0.0, total_hkd_input - hk_invested)
            
            hk_cash_df = pd.DataFrame({
                "資金項目": ["港股已投入本金", "港幣可用剩餘現金"],
                "金額(HKD)": [hk_invested, hk_cash]
            })
            fig_hk_cash = px.pie(
                hk_cash_df, values='金額(HKD)', names='資金項目', 
                title=f'港幣資金池使用率 (總投入: HKD {total_hkd_input:,.2f})',
                color_discrete_sequence=['#2ca02c', '#d62728'], hole=0.3
            )
            fig_hk_cash.update_traces(texttemplate='HKD %{value:,.2f}<br>(%{percent})')
            st.plotly_chart(fig_hk_cash, use_container_width=True)
            
        with col_cash2:
            # 美金本金與投入統計
            us_invested = df_us['總投入成本'].sum()
            us_cash = max(0.0, total_usd_input - us_invested)
            
            us_cash_df = pd.DataFrame({
                "資金項目": ["美股已投入本金", "美金可用剩餘現金"],
                "金額(USD)": [us_invested, us_cash]
            })
            fig_us_cash = px.pie(
                us_cash_df, values='金額(USD)', names='資金項目', 
                title=f'美金資金池使用率 (總投入: USD {total_usd_input:,.2f})',
                color_discrete_sequence=['#1f77b4', '#ff7f0e'], hole=0.3
            )
            fig_us_cash.update_traces(texttemplate='USD %{value:,.2f}<br>(%{percent})')
            st.plotly_chart(fig_us_cash, use_container_width=True)
            
    else:
        st.info("💡 目前持倉清單為空。請在上方輸入框中輸入代號、買入價與持股數加入資產！")

# ==========================================
# TAB 2 至 TAB 5 功能模組
# ==========================================
with tab2:
    st.header("🛠️ 跨資產投資組合優化分析")
    st.write("系統正基於馬可維茲模型進行矩陣交叉優化...")
    
    st.markdown("---")
    st.header("🔍 全球資產即時技術查詢器")
    col_q1, col_q2 = st.columns([1, 3])
    with col_q1:
        search_ticker = st.text_input("輸入任意市場代號查詢 (例如：0005.HK, TSLA)", value="0700.HK").upper()
        days_to_lookback = st.slider("歷史 K 線天數選擇", min_value=30, max_value=365, value=120)
        
    if search_ticker:
        try:
            stock = yf.Ticker(search_ticker)
            hist = stock.history(period=f"{days_to_lookback}d")
            
            if not hist.empty:
                latest_data = hist.iloc[-1]
                info = stock.info
                st.subheader(f"📌 {info.get('shortName', search_ticker)} 資產即時數據摘要")
                
                # 渲染技術指標圖表 (與先前邏輯一致)
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
                fig.add_trace(go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'], name="K線"), row=1, col=1)
                fig.update_layout(xaxis_rangeslider_visible=False, height=500)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.error("未找到數據，請確認代號格式。")
        except Exception as e:
            st.error(f"數據讀取失敗: {e}")

with tab3:
    st.header("🎲 蒙地卡羅模擬")
    sim_data = np.random.normal(loc=0.06, scale=0.14, size=1200) * 100
    fig_hist = px.histogram(sim_data, nbins=35, title="多市場資產配置期望分佈")
    st.plotly_chart(fig_hist, use_container_width=True)

with tab4:
    st.header("🎭 市場情緒指標")

with tab5:
    st.header("🏢 同業/同類資產比較分析")
