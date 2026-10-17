"""Interactive view of the saved cloud-resource project results."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


SNAPSHOT_PATH = Path(__file__).with_name("snapshot.json")
POLICY_LABELS = {
    "fixed": "Fixed reference",
    "persistence": "Persistence",
    "forest_plus_margin": "Forest + margin",
}
POLICY_COLORS = {
    "Fixed reference": "#ed9959",
    "Persistence": "#6aa6da",
    "Forest + margin": "#56c9a4",
}
SCENARIO_ORDER = ["original", "+20% demand", "+50% demand", "-20% pool"]


def load_snapshot() -> tuple[dict, str]:
    uploaded = st.sidebar.file_uploader("Load a newer dashboard snapshot", type="json")
    try:
        if uploaded is None:
            data = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
            source = SNAPSHOT_PATH.name
        else:
            if uploaded.size > 2_000_000:
                raise ValueError("Snapshot files must be smaller than 2 MB")
            data = json.loads(uploaded.getvalue())
            source = uploaded.name
        if data.get("schema_version") != 1:
            raise ValueError("Unsupported snapshot version; regenerate it with export_snapshot.py")
        for name in ("run", "forecasting", "risk", "allocation", "clustering"):
            if name not in data:
                raise ValueError(f"Snapshot is missing {name}")
        return data, source
    except (OSError, ValueError, KeyError, TypeError) as exc:
        st.error(f"Cannot load dashboard snapshot: {exc}")
        st.stop()


def chart_layout(fig, *, height=370, ytitle=None):
    fig.update_layout(
        height=height,
        margin=dict(l=12, r=12, t=28, b=12),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(zeroline=False, title=ytitle)
    return fig


def show_chart(fig, key):
    st.plotly_chart(fig, key=key, theme="streamlit",
                    config={"displaylogo": False})


st.set_page_config(page_title="Cloud Resource Intelligence", page_icon="☁️",
                   layout="wide")

st.sidebar.title("Project results")
st.sidebar.caption("Saved Google Cluster Data 2011-2 sample")
data, source = load_snapshot()
st.sidebar.caption(f"Showing: {source}")
resource = st.sidebar.radio("Resource", ["cpu", "memory"],
                            format_func=lambda value: value.upper())
margin = data["allocation"]["margin"]
POLICY_LABELS["forest_plus_margin"] = f"Forest + {margin:.0%} margin"
POLICY_COLORS[POLICY_LABELS["forest_plus_margin"]] = POLICY_COLORS.pop("Forest + margin")

st.title("Cloud Resource Intelligence")
st.caption("Forecasting and simulated allocation on a bounded Google cluster trace sample")
run = data["run"]
kpis = st.columns(4)
kpis[0].metric("Sampled usage rows", f"{run['source_rows']:,}", border=True)
kpis[1].metric("Eligible 5-min pairs", f"{run['eligible_pairs']:,}", border=True)
kpis[2].metric("Held-out test intervals", f"{run['test_intervals']:,}", border=True)
kpis[3].metric("Saved project data", f"{run['project_mb']:.1f} MB", border=True)

overview, forecasting, risk, allocation, method = st.tabs(
    ["Overview", "Forecasting", "Risk classification", "Allocation simulator", "Method & limits"]
)

with overview:
    st.subheader("What the project found")
    base = pd.DataFrame(data["allocation"]["baseline"])
    selected = data["forecasting"]["selected_models"]
    left, right = st.columns(2)
    with left:
        st.markdown("**Next-interval forecasting**")
        st.write(f"Lowest validation MAE: **{selected['cpu']}** for CPU and "
                 f"**{selected['memory']}** for memory.")
        test = pd.DataFrame(data["forecasting"]["test"])
        st.dataframe(test[["resource", "model", "MAE", "RMSE", "R2"]].round(6),
                     hide_index=True)
    with right:
        st.markdown("**Held-out allocation comparison**")
        original = base[base.resource == resource].copy()
        original["Policy"] = original.policy.map(POLICY_LABELS)
        original["Useful utilization"] = original.utilization.map(lambda x: f"{x:.1%}")
        original["Unmet demand"] = original.unmet_fraction.map(lambda x: f"{x:.1%}")
        st.dataframe(original[["Policy", "Useful utilization", "Unmet demand"]],
                     hide_index=True)
        st.caption("Forest reserves more capacity: it reduces unmet CPU demand "
                   "but lowers useful utilization against persistence.")
    st.info("The allocation results are a trace replay with simulated pools. "
            "They are not measured Borg savings, SLA outcomes, or physical capacity.")

with forecasting:
    st.subheader(f"{resource.upper()} demand forecasting")
    validation = pd.DataFrame(data["forecasting"]["validation"])
    forecast_metric = st.radio("Validation metric", ["MAE", "RMSE"], horizontal=True)
    rows = validation[validation.resource == resource].sort_values(forecast_metric)
    fig = px.bar(rows, x="model", y=forecast_metric, text=forecast_metric,
                 color="model", color_discrete_sequence=["#56c9a4", "#6aa6da",
                                                        "#9b91db", "#ed9959"])
    fig.update_traces(texttemplate="%{y:.5f}", textposition="outside")
    fig.update_layout(showlegend=False, xaxis_title="Candidate model")
    chart_layout(fig, ytitle=f"Validation {forecast_metric} (normalized units)")
    fig.update_yaxes(range=[0, rows[forecast_metric].max() * 1.2])
    show_chart(fig, "validation-forecast")
    st.caption("Model selection used validation MAE. The forest was retained as "
               "a separate allocation candidate; persistence won forecasting MAE.")

    st.markdown("**Workload profiles**")
    profiles = pd.DataFrame(data["clustering"]["profiles"])
    clusters = pd.DataFrame(data["clustering"]["scores"])
    chosen = clusters.dropna(subset=["silhouette"]).sort_values("silhouette", ascending=False).iloc[0]
    st.write(f"MiniBatchKMeans chose **{int(chosen.k)} clusters** "
             f"(sampled silhouette **{chosen.silhouette:.3f}**).")
    st.dataframe(profiles.round(6), hide_index=True)
    st.caption("Cluster IDs describe historical normalized usage profiles; "
               "they are not fixed workload types or machine classes.")

with risk:
    st.subheader("Future allocation-risk proxy")
    st.caption("Classes compare next observed usage with a fixed training-only "
               "reference allocation. They are not recorded failures.")
    a, b, c = st.columns(3)
    a.metric("Selected classifier", data["risk"]["selected_model"].replace("_", " ").title(),
             border=True)
    b.metric("Test macro-F1", f"{data['risk']['test_macro_f1']:.3f}", border=True)
    c.metric("Majority baseline", f"{data['risk']['majority_test_macro_f1']:.3f}", border=True)
    counts = pd.DataFrame(data["risk"]["class_counts"])
    long_counts = counts.melt(id_vars="label", value_vars=["train", "validation", "test"],
                              var_name="Split", value_name="Intervals")
    long_counts["Share"] = (long_counts["Intervals"] /
                            long_counts.groupby("Split")["Intervals"].transform("sum"))
    fig = px.bar(long_counts, x="Split", y="Share", color="label", barmode="stack",
                 category_orders={"Split": ["train", "validation", "test"]},
                 custom_data=["Intervals"],
                 color_discrete_sequence=["#6aa6da", "#ed9959", "#56c9a4", "#9b91db"])
    fig.update_traces(hovertemplate="%{fullData.name}: %{customdata[0]:,} intervals "
                                    "(%{y:.1%})<extra></extra>")
    chart_layout(fig, ytitle="Share of task intervals")
    fig.update_yaxes(tickformat=".0%", range=[0, 1])
    show_chart(fig, "risk-counts")
    st.markdown("**Validation model comparison**")
    risk_validation = pd.DataFrame(data["risk"]["validation"])
    st.dataframe(risk_validation[["model", "macro_F1", "recall_balanced",
                                  "recall_CPU risk", "recall_memory risk", "recall_both"]].round(3),
                 hide_index=True)

with allocation:
    st.subheader(f"{resource.upper()} allocation replay")
    base = pd.DataFrame(data["allocation"]["baseline"])
    rows = base[base.resource == resource].copy()
    rows["Policy"] = rows.policy.map(POLICY_LABELS)
    long_base = rows.melt(id_vars="Policy", value_vars=["utilization", "unmet_fraction"],
                          var_name="Measure", value_name="Share")
    long_base["Measure"] = long_base["Measure"].map({
        "utilization": "Served / allocated",
        "unmet_fraction": "Unmet / observed demand",
    })
    fig = px.bar(long_base, x="Policy", y="Share", color="Measure", barmode="group",
                 text="Share", color_discrete_sequence=["#6aa6da", "#ed9959"])
    fig.update_traces(texttemplate="%{y:.1%}", textposition="outside")
    chart_layout(fig, ytitle="Share")
    fig.update_yaxes(tickformat=".0%", range=[0, 1.12])
    show_chart(fig, "allocation-baseline")
    st.caption("The two bars have different denominators. Utilization is served / "
               "allocated; unmet demand is unserved / observed demand.")

    st.markdown("**What-if stress tests**")
    chosen_scenarios = st.multiselect("Show scenarios", SCENARIO_ORDER,
                                      default=SCENARIO_ORDER)
    scenario = pd.DataFrame(data["allocation"]["scenarios"])
    scenario = scenario[(scenario.resource == resource) &
                        (scenario.scenario.isin(chosen_scenarios))].copy()
    if scenario.empty:
        st.info("Select at least one scenario to see its comparison.")
    else:
        scenario["Policy"] = scenario.policy.map(POLICY_LABELS)
        scenario["Scenario"] = pd.Categorical(scenario.scenario,
                                                categories=SCENARIO_ORDER, ordered=True)
        fig = px.bar(scenario, x="Scenario", y="unmet_fraction", color="Policy",
                     barmode="group", category_orders={"Scenario": SCENARIO_ORDER},
                     color_discrete_map=POLICY_COLORS,
                     hover_data={"overloaded_task_fraction": ":.1%",
                                 "pool_saturation_fraction": ":.1%"})
        chart_layout(fig, ytitle="Unmet share of observed demand")
        fig.update_yaxes(tickformat=".0%", range=[0, .75])
        show_chart(fig, "allocation-scenarios")
        st.dataframe(scenario[["scenario", "Policy", "utilization", "unmet_fraction",
                               "overloaded_task_fraction", "pool_saturation_fraction"]]
                     .sort_values(["scenario", "Policy"]).round(4), hide_index=True)
    st.caption("Demand stress changes only scoring demand; policies do not see the "
               "shift in advance. The pool scenario reduces both simulated pools by 20%.")

with method:
    st.subheader("How to interpret this dashboard")
    st.write(f"The analysis used {run['shards']} of 500 task-usage shards, "
             f"covering about {run['hours']:.2f} hours. It predicts the next "
             "contiguous five-minute interval. Time splits prevent future targets "
             "from entering training features.")
    st.markdown("**Data preparation**")
    quality = data["quality"]
    st.write(f"{quality['non_300_second_rows']:,} irregular-duration rows were excluded "
             f"from fixed-horizon modeling; {quality['overlapping_interval_rows']:,} "
             "overlapping rows were detected and handled during cleaning.")
    st.dataframe(pd.DataFrame(data["split_counts"]), hide_index=True)
    st.markdown("**Limits**")
    for item in data["limitations"]:
        st.markdown(f"- {item}")
    st.caption("Snapshot derived from the saved notebook outputs; refresh it after "
               "a new full analysis run with `python dashboard/export_snapshot.py`.")
