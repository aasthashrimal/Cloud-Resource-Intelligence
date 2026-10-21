# Results dashboard

This local Streamlit dashboard displays the **saved outputs** of `analysis.ipynb`.
It does not retrain models, download trace shards, or load the 565.8 MB project
data. The included `snapshot.json` comes from the completed notebook run and is
about 18 KB.

From the project folder in Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r dashboard\requirements.txt
.\.venv\Scripts\python -m streamlit run dashboard\app.py
```
(Use 3rd one to run)

Streamlit will print a local address, usually `http://localhost:8501`. Open it
in a browser. The sidebar switches CPU/memory; the allocation tab lets you
compare the saved stress scenarios. The plots are interactive, and the app
needs no cloud account.
Use Streamlit's menu to switch between light and dark themes; the dashboard
follows that choice for its page, metrics, and charts.

The project-local `.venv` has already been created in this workspace. While it
is present, you only need the final `streamlit run` command above.

After a new Colab run, save the updated `analysis.ipynb` back into this project
and refresh the snapshot locally:

```powershell
python dashboard\export_snapshot.py
```

The exporter requires saved, error-free outputs from a full top-to-bottom run
and checks the policy/scenario tables before replacing `snapshot.json`. You can
also upload a newer snapshot through the dashboard sidebar. The source of every
number is the notebook's saved result tables; this dashboard does not invent
new workloads or recompute the simulated allocation.
