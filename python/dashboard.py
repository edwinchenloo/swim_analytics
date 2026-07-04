import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import os
import plotly.io as pio
import streamlit.components.v1 as components
from swim_parser import SwimParser

st.set_page_config(page_title="Swim Analytics Dashboard", layout="wide")

# Extreme space optimization: Hide header, dynamic chart height
st.markdown("""
    <style>
    header {visibility: hidden; display: none !important;}
    footer {visibility: hidden;}
    .block-container {
        padding-top: 0rem !important;
        padding-bottom: 0rem !important;
    }
    /* Dynamic height for the chart component - 50vh to leave room for controls */
    iframe[title="streamlit.components.v1.html"] {
        height: 50vh !important;
    }
    div[data-testid="stVerticalBlock"] > div:first-child {
        margin-top: -2rem;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.4rem !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.8rem !important;
    }
    /* Hide the deploy and settings icons by targeting the toolbar */
    .stAppDeployButton {display: none !important;}
    #MainMenu {visibility: hidden;}
    /* Extreme tight margins for all elements */
    h3 {
        margin-top: 0rem !important;
        margin-bottom: 0rem !important;
        font-size: 1.1rem !important;
    }
    .stCheckbox {
        margin-bottom: -1rem !important;
    }
    div[data-testid="stMetric"] {
        padding: 0px !important;
    }
    </style>
""", unsafe_allow_html=True)

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "csv"))
parser = SwimParser(pool_length_yd=25)

def load_all_swims():
    swims = []
    if not os.path.exists(DATA_DIR): return swims
    for f in os.listdir(DATA_DIR):
        if f.endswith(".csv"):
            data = parser.parse_file(os.path.join(DATA_DIR, f))
            if data:
                summary = parser.get_summary(data)
                swims.append({"date": summary['date'], "display_name": f"{summary['date']} - {summary['total_distance_yd']}yd", "data": data, "summary": summary})
    return sorted(swims, key=lambda x: x['date'], reverse=True)

all_swims = load_all_swims()
if not all_swims:
    st.info("No swim data found.")
else:
    if 'selected_swim_idx' not in st.session_state: st.session_state.selected_swim_idx = 0
    
    selected_swim_info = all_swims[st.session_state.selected_swim_idx]
    df = pd.DataFrame(selected_swim_info['data'])
    summary = selected_swim_info['summary']

    # GRAPH AT THE TOP - Fixed width for horizontal scrolling, dynamic vh for height
    px_per_length = 15
    chart_width = len(df) * px_per_length
    x_data = df['message_index'] + 1

    fig = go.Figure()
    min_pace, max_pace = df['pace_100yd_sec'].min(), df['pace_100yd_sec'].max()
    
    fig.add_trace(go.Bar(
        x=x_data, y=df['pace_100yd_sec'], name="Pace", 
        marker_color=['#1f77b4' if i % 2 == 0 else '#4682b4' for i in range(len(df))], 
        opacity=0.4, hovertemplate='Length %{x}<br>Pace: %{text}', text=df['pace_str']
    ))

    show_strokes = st.session_state.get('show_strokes', True)
    show_cadence = st.session_state.get('show_cadence', True)
    show_hr = st.session_state.get('show_hr', True)

    m_size, m_width = 12, 3
    if show_strokes: fig.add_trace(go.Scatter(x=x_data, y=df['total_strokes'], name="Strokes", mode='markers', marker=dict(symbol='line-ew', size=m_size, line=dict(width=m_width, color='#FF9900')), yaxis="y2"))
    if show_cadence: fig.add_trace(go.Scatter(x=x_data, y=df['avg_swimming_cadence'], name="Cadence", mode='markers', marker=dict(symbol='line-ew', size=m_size, line=dict(width=m_width, color='#00FF00')), yaxis="y3"))
    if show_hr:
        hr_df = df[df['avg_heart_rate'] > 0]
        fig.add_trace(go.Scatter(x=hr_df['message_index']+1, y=hr_df['avg_heart_rate'], name="HR", mode='markers', marker=dict(symbol='line-ew', size=m_size, line=dict(width=m_width, color='#FF0000')), yaxis="y4"))

    fig.update_layout(
        width=chart_width, height=None, # Height will be controlled by iframe CSS
        autosize=True, template="plotly_dark", bargap=0.05,
        xaxis=dict(title="Length #", tickmode='linear', dtick=10, fixedrange=True, domain=[0, 0.88]),
        yaxis=dict(title=dict(text="Pace"), side="left", range=[min_pace*0.95, max_pace*1.05]),
        yaxis2=dict(title=dict(text="Strokes", font=dict(color='#FF9900')), tickfont=dict(color='#FF9900'), overlaying="y", side="right", showgrid=False),
        yaxis3=dict(title=dict(text="Cadence", font=dict(color='#00FF00')), tickfont=dict(color='#00FF00'), overlaying="y", side="right", anchor="free", position=0.93, showgrid=False),
        yaxis4=dict(title=dict(text="HR", font=dict(color='#FF0000')), tickfont=dict(color='#FF0000'), overlaying="y", side="right", anchor="free", position=0.98, showgrid=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=50, r=20, t=10, b=40), paper_bgcolor='#0e1117', plot_bgcolor='#0e1117'
    )

    html_content = pio.to_html(fig, config={'responsive': True, 'displayModeBar': True}, full_html=False)
    components.html(f'<div style="width: {chart_width}px; height: 100%; background-color: #0e1117; padding: 10px;">{html_content}</div>', width=chart_width + 200, height=500, scrolling=True)

    # CONTROLS AND TITLE AT THE BOTTOM
    st.markdown("<hr style='margin: 0rem 0;'>", unsafe_allow_html=True)
    b1, b2, b3, b4, b5 = st.columns([1.5, 2.5, 1, 1, 1])
    with b1:
        st.markdown("### 🏊 Swim Analytics")
    with b2:
        new_sel = st.selectbox("Session", options=range(len(all_swims)), index=st.session_state.selected_swim_idx, format_func=lambda x: all_swims[x]['display_name'], label_visibility="collapsed")
        if new_sel != st.session_state.selected_swim_idx:
            st.session_state.selected_swim_idx = new_sel
            st.rerun()
    with b3:
        st.checkbox("Strokes", value=True, key='show_strokes')
    with b4:
        st.checkbox("Cadence", value=True, key='show_cadence')
    with b5:
        st.checkbox("HR", value=True, key='show_hr')

    st.markdown("<div style='margin-bottom: 0.6rem;'></div>", unsafe_allow_html=True)

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Distance", f"{summary['total_distance_yd']} yd")
    m2.metric("Avg Pace", f"{summary['avg_pace_100yd']}")
    m3.metric("Time", summary['total_time'])
    m4.metric("Strokes", summary['avg_strokes'])
    m5.metric("HR", f"{summary.get('avg_hr', 0)} bpm")
