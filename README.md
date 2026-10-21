# ☁️ Cloud Resource Intelligence

**An interactive dashboard for cloud resource analysis, cost forecasting, risk classification, and resource allocation.**

Cloud Resource Intelligence is a data-driven analytics project that transforms cloud resource data into actionable insights through interactive visualizations, predictive analysis, and resource allocation simulation.

🔗 **Live Demo:** [View on Streamlit](https://share.streamlit.io/](https://cloud-resource-intelligence.streamlit.app/)

## 🚀 Features

- **Resource Overview:** Explore key metrics and summaries of cloud resources.
- **Cost Forecasting:** Analyze historical trends and forecast future resource costs.
- **Risk Classification:** Identify and categorize resources based on their risk levels.
- **Allocation Simulator:** Experiment with resource allocation scenarios and evaluate potential outcomes.
- **Interactive Visualizations:** Explore analytical results through charts and visual summaries.
- **Methodology & Limitations:** Review the analytical approach, assumptions, and limitations of the results.

## 🛠️ Tech Stack

- **Python** — Data processing and analysis
- **Streamlit** — Interactive web dashboard
- **Pandas & NumPy** — Data manipulation and numerical computing
- **Matplotlib / Plotly** — Data visualization
- **Jupyter Notebook** — Exploratory data analysis and experimentation

## 📂 Project Structure

```text
Cloud-Resource-Intelligence/
├── dashboard/
│   ├── app.py
│   ├── requirements.txt
│   ├── snapshot.json
│   └── export_snapshot.py
├── analysis.ipynb
├── notebook.ipynb
├── .gitignore
└── README.md
```

## ⚙️ Run Locally

### 1. Clone the repository

```bash
git clone https://github.com/aasthashrimal/Cloud-Resource-Intelligence.git
cd Cloud-Resource-Intelligence
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate it:

**Windows**
```powershell
.venv\Scripts\activate
```

**macOS / Linux**
```bash
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r dashboard/requirements.txt
```

### 4. Launch the dashboard

```bash
streamlit run dashboard/app.py
```

The dashboard will open in your browser, usually at `http://localhost:8501`.

## 📊 How It Works

1. **Data Analysis:** Explore and analyze cloud resource data using Jupyter notebooks.
2. **Analytical Processing:** Generate resource metrics, forecasts, and risk-related results.
3. **Snapshot Export:** Store prepared analytical results in `dashboard/snapshot.json`.
4. **Dashboard Visualization:** Load the saved results into an interactive Streamlit dashboard.
5. **Scenario Exploration:** Use the allocation simulator to explore potential resource allocation decisions.

The dashboard uses precomputed analytical results from the snapshot file, allowing it to display insights without rerunning the full analysis on every visit.

## 🌐 Deployment

The application is deployed using **Streamlit Community Cloud** and can be accessed through its public URL.

To deploy your own instance:

1. Fork or clone this repository.
2. Sign in to [Streamlit Community Cloud](https://share.streamlit.io/).
3. Connect your GitHub repository.
4. Set the main file path to `dashboard/app.py`.
5. Deploy the application.

## ⚠️ Limitations

- Forecasts and classifications depend on the quality and coverage of the underlying data.
- Displayed results may reflect a previously generated snapshot rather than live cloud infrastructure.
- Allocation simulations are analytical experiments and do not directly provision, modify, or delete cloud resources.
- Predictions should be interpreted alongside the assumptions and limitations documented in the dashboard.

## 🔮 Future Enhancements

- Integration with live AWS and Azure resource data.
- Real-time cloud cost monitoring and budget alerts.
- Automated detection of underutilized resources.
- Advanced forecasting and anomaly detection.
- Cloud resource optimization recommendations.

## 👩‍💻 Author

**Aastha Shrimal**

GitHub: [@aasthashrimal](https://github.com/aasthashrimal)

---

⭐ If you find this project useful, consider giving the repository a star.
