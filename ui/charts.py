import plotly.express as px
import pandas as pd

def plot_bus_timeline(df_timeline: pd.DataFrame, plotly_theme: dict):
    """
    Plots the bus schedule Gantt timeline chart.
    """
    if df_timeline.empty:
        return None

    # Sort by Bus ID for clean y-axis layout
    df_timeline = df_timeline.sort_values(by=["Bus ID", "Start"])
    
    fig = px.timeline(
        df_timeline, 
        x_start="Start", 
        x_end="End", 
        y="Bus ID", 
        color="State",
        hover_name="Activity",
        color_discrete_map=plotly_theme["colors"],
        category_orders={"Bus ID": sorted(list(df_timeline["Bus ID"].unique()))},
        template=plotly_theme["template"]
    )
    
    # Adjust layout
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(
        xaxis_title="Time of Day",
        yaxis_title="Bus ID",
        xaxis=dict(
            gridcolor=plotly_theme["grid"],
            linecolor=plotly_theme["grid"],
            tickformat="%H:%M",
            type="date"
        ),
        yaxis=dict(
            gridcolor=plotly_theme["grid"],
            linecolor=plotly_theme["grid"]
        ),
        height=600,
        margin=dict(l=0, r=0, t=30, b=0),
        legend=dict(
            orientation="h", 
            yanchor="bottom", 
            y=1.02, 
            xanchor="right", 
            x=1, 
            font=dict(color=plotly_theme["text"])
        ),
        paper_bgcolor=plotly_theme["bg"],
        plot_bgcolor=plotly_theme["bg"],
        font=dict(color=plotly_theme["text"], family="'Outfit', 'Inter', sans-serif")
    )
    return fig

def plot_station_occupancy(df_st_time: pd.DataFrame, plotly_theme: dict):
    """
    Plots the station occupancy Gantt timeline chart.
    """
    if df_st_time.empty:
        return None

    df_st_time = df_st_time.sort_values(by=["Station", "Start"])
    
    fig = px.timeline(
        df_st_time,
        x_start="Start",
        x_end="End",
        y="Station",
        color="Bus ID",
        hover_name="Label",
        category_orders={"Station": sorted(list(df_st_time["Station"].unique()))},
        template=plotly_theme["template"]
    )
    
    fig.update_layout(
        xaxis_title="Time of Day",
        yaxis_title="Station",
        xaxis=dict(
            gridcolor=plotly_theme["grid"],
            linecolor=plotly_theme["grid"],
            tickformat="%H:%M",
            type="date"
        ),
        yaxis=dict(
            gridcolor=plotly_theme["grid"],
            linecolor=plotly_theme["grid"]
        ),
        height=350,
        margin=dict(l=0, r=0, t=30, b=0),
        legend_title="Bus ID",
        paper_bgcolor=plotly_theme["bg"],
        plot_bgcolor=plotly_theme["bg"],
        font=dict(color=plotly_theme["text"], family="'Outfit', 'Inter', sans-serif")
    )
    return fig
