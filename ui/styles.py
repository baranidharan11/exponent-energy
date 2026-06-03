import streamlit as st

def inject_custom_css(dark_mode: bool):
    """
    Injects CSS stylesheet and returns theme specific variables for Plotly charts.
    """
    if dark_mode:
        theme_vars = """
        :root {
            --bg-gradient: linear-gradient(135deg, #0A0C16 0%, #151829 100%);
            --text-color: #F1F5F9;
            --sidebar-bg: #0A0C16;
            --card-bg: rgba(22, 28, 48, 0.7);
            --card-border: 1px solid rgba(255, 87, 34, 0.2);
            --card-hover-border: rgba(255, 107, 53, 0.55);
            --card-hover-shadow: 0 10px 30px rgba(255, 107, 53, 0.15);
            --row-even-bg: #141A29;
            --row-odd-bg: #1C2438;
            --border-color: rgba(255, 255, 255, 0.08);
            --title-color: #FF6B35;
            --subtitle-color: #94A3B8;
            --slider-track: #2D334A;
        }
        """
        plotly_theme = {
            "template": "plotly_dark",
            "bg": "rgba(0,0,0,0)",
            "grid": "rgba(255, 255, 255, 0.08)",
            "text": "#F1F5F9",
            "colors": {
                "Traveling": "#3B82F6",
                "Waiting": "#EF4444",
                "Charging": "#10B981"
            }
        }
    else:
        theme_vars = """
        :root {
            --bg-gradient: linear-gradient(135deg, #F8FAFC 0%, #E2E8F0 100%);
            --text-color: #0F172A;
            --sidebar-bg: #FFFFFF;
            --card-bg: rgba(255, 255, 255, 0.85);
            --card-border: 1px solid rgba(255, 87, 34, 0.15);
            --card-hover-border: rgba(255, 87, 34, 0.45);
            --card-hover-shadow: 0 10px 30px rgba(255, 87, 34, 0.1);
            --row-even-bg: #FFFFFF;
            --row-odd-bg: #F1F5F9;
            --border-color: rgba(0, 0, 0, 0.08);
            --title-color: #E64A19;
            --subtitle-color: #475569;
            --slider-track: #E2E8F0;
        }
        """
        plotly_theme = {
            "template": "plotly_white",
            "bg": "rgba(0,0,0,0)",
            "grid": "rgba(0, 0, 0, 0.08)",
            "text": "#0F172A",
            "colors": {
                "Traveling": "#60A5FA",
                "Waiting": "#F87171",
                "Charging": "#34D399"
            }
        }

    st.markdown(f"""
        <style>
        {theme_vars}
        
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Outfit:wght@400;600;800&display=swap');
        
        /* Main Layout and Title Styles */
        .stApp {{
            background: var(--bg-gradient) !important;
            color: var(--text-color) !important;
            font-family: 'Inter', sans-serif !important;
        }}
        
        div[data-testid="stSidebar"] {{
            background-color: var(--sidebar-bg) !important;
            border-right: 1px solid var(--border-color) !important;
        }}
        
        .main-title {{
            font-family: 'Outfit', sans-serif !important;
            color: var(--title-color) !important;
            font-weight: 800;
            font-size: 2.8rem;
            margin-bottom: 0.1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        
        .subtitle {{
            font-family: 'Inter', sans-serif;
            color: var(--subtitle-color);
            font-size: 1.1rem;
            margin-bottom: 2rem;
        }}
        
        /* Metric Card Styling */
        div[data-testid="stMetric"] {{
            background-color: var(--card-bg) !important;
            border: var(--card-border) !important;
            padding: 20px !important;
            border-radius: 12px !important;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05), 0 2px 4px -1px rgba(0,0,0,0.03) !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        }}
        
        div[data-testid="stMetric"]:hover {{
            transform: translateY(-4px) !important;
            border-color: var(--card-hover-border) !important;
            box-shadow: var(--card-hover-shadow) !important;
        }}
        
        div[data-testid="stMetric"] label {{
            color: var(--subtitle-color) !important;
            font-weight: 600;
            font-size: 0.85rem !important;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        div[data-testid="stMetric"] div[data-testid="stMetricValue"] {{
            color: var(--text-color) !important;
            font-size: 2rem !important;
            font-weight: 700 !important;
            font-family: 'Outfit', sans-serif !important;
        }}
        
        /* Tabs custom styling */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 24px;
            background-color: transparent !important;
            border-bottom: 2px solid var(--border-color) !important;
        }}
        
        .stTabs [data-baseweb="tab"] {{
            height: 50px;
            white-space: pre-wrap;
            background-color: transparent !important;
            border-bottom: 2px solid transparent !important;
            color: var(--subtitle-color) !important;
            font-size: 1.05rem;
            font-weight: 600;
            padding: 10px 16px;
            transition: all 0.3s ease !important;
        }}
        
        .stTabs [data-baseweb="tab"]:hover {{
            color: var(--title-color) !important;
        }}
        
        .stTabs [aria-selected="true"] {{
            color: var(--title-color) !important;
            border-bottom-color: var(--title-color) !important;
        }}
        
        /* Header background accent */
        .header-accent {{
            height: 4px;
            background: linear-gradient(90deg, #FF5722 0%, #FFC107 100%);
            border-radius: 2px;
            margin-bottom: 1.5rem;
        }}
        
        /* Table Styling */
        table {{
            border-collapse: collapse !important;
            width: 100% !important;
            margin: 10px 0 !important;
            border-radius: 8px !important;
            overflow: hidden !important;
            border: 1px solid var(--border-color) !important;
        }}
        
        th {{
            background: linear-gradient(90deg, #FF5722 0%, #FF8A65 100%) !important;
            color: white !important;
            font-family: 'Outfit', sans-serif !important;
            text-transform: uppercase !important;
            font-size: 0.85rem !important;
            letter-spacing: 0.5px !important;
            padding: 12px 15px !important;
            border: none !important;
        }}
        
        tbody tr:nth-child(even) {{
            background-color: var(--row-even-bg) !important;
        }}
        
        tbody tr:nth-child(odd) {{
            background-color: var(--row-odd-bg) !important;
        }}
        
        td {{
            color: var(--text-color) !important;
            padding: 10px 15px !important;
            border-bottom: 1px solid var(--border-color) !important;
            font-size: 0.9rem !important;
        }}
        
        /* Button Customization */
        div.stButton > button {{
            background: linear-gradient(90deg, #FF5722 0%, #FF8A65 100%) !important;
            color: white !important;
            border: none !important;
            font-family: 'Outfit', sans-serif !important;
            font-weight: 600 !important;
            padding: 10px 24px !important;
            border-radius: 8px !important;
            transition: all 0.3s ease !important;
            box-shadow: 0 4px 15px rgba(255, 87, 34, 0.3) !important;
        }}
        
        div.stButton > button:hover {{
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 20px rgba(255, 87, 34, 0.5) !important;
            color: white !important;
        }}
        
        div.stButton > button:active {{
            transform: translateY(0) !important;
        }}
        
        /* Text inputs, select boxes, expanders */
        div[data-testid="stExpander"] {{
            background-color: var(--card-bg) !important;
            border: var(--card-border) !important;
            border-radius: 8px !important;
        }}
        
        div[data-testid="stWidgetLabel"] p {{
            color: var(--text-color) !important;
            font-weight: 500 !important;
        }}
        </style>
        """, unsafe_allow_html=True)

    return plotly_theme
