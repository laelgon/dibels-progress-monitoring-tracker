# Fake data into the dashboard, then to Tableau Public

Menu names can differ slightly by Tableau version.

## 1. Make a safe copy
1. Open the **local** workbook (not a copy downloaded from a Tableau Server: a downloaded packaged workbook can carry a real extract).
2. **File > Save As** a new name, for example `DIBELS Progress Monitoring Drill-Down (FAKE DEMO).twb`, in a separate `demo` folder.
   Everything below happens in this copy.

## 2. Point the two data sources at the fake files
For **DIBELS PM** and **DIBELS PM PROBES**:
1. **Data > (the data source) > Edit Data Source**, or the Data Source tab.
2. In **Connections** (top left), click the small dropdown arrow on the connection, or right-click it, and choose **Edit Connection**.
3. Pick the fake file: `dibels_student_window.csv` for DIBELS PM and `dibels_probes.csv` for DIBELS PM PROBES, from `output/fake_demo/` (made by `python demo/make_fake_data.py`).
4. The fake files have the same columns, so every field and calculation keeps working.

If Edit Connection is missing: **Data > New Data Source > Text file**, then **Data > Replace Data Source**, then close the old source.
Only the two fake data sources should remain.

## 3. Clean the copy
1. Close the workbook in Tableau, then `python demo/clean_workbook_copy.py "<copy>.twb"` (adds a backup, removes the server address, the
   publish record and saved drill-down), and reopen it.
2. Titles and text: replace any school name; add a text object on each dashboard: **ALL DATA ON THIS DASHBOARD IS FAKE**.
3. Set the **Window** parameter back to **Current (0)** so switching Level never goes blank.
4. Check the dashboards: names like `Alpha FAKE062`, teachers like `FakeTeacher-1A, Demo`.

## 4. Package and scan
1. **File > Save As > Tableau Packaged Workbook (.twbx)**.
2. `python demo/scan_workbook_for_real_data.py "<file>.twbx"` must say **PASS**. Add `--also-search "Your Organization"` to look for a name.

## 5. Publish
1. **Server > Tableau Public > Save to Tableau Public As** (it may be under **File**). Do **not** use Server > Publish Workbook:
   that goes to your own Tableau Server.
2. Sign in to your own Tableau Public account yourself. Name it, for example, **DIBELS Progress Monitoring Drill-Down (Fake Data Demo)**.
3. In the public page settings you can turn off "Allow users to download the workbook and its data".
4. Open the public link in a private window and click through every dashboard and drill-down. Look for red exclamation marks.

## 6. Add the guide with a Show/Hide button
`APM_KPI_Demo_Guide.html` explains the dashboard. Three ways to show it:

**A. Web page panel (best looking).** Put the HTML on a free HTTPS host (for example GitHub Pages or Netlify Drop; it is public, and it
contains only fake data). In the workbook copy: drag a **Floating** vertical container onto the dashboard (for example X 60, Y 80,
W 1000, H 640), drag a **Web Page** object into it and paste the address, then open the container's dropdown and choose
**Add Show/Hide Button**. Edit the button to read "Show guide" / "Hide guide" and place it top right. Test after publishing: if the
panel is blank, the host may not allow embedding.

**B. Image (no hosting).** Screenshot the guide's Quick guide section, put an **Image** object in the floating container, set it to
fit, and add the Show/Hide button.

**C. Plain Tableau text.** Type a short summary into a text object inside the floating container and add the Show/Hide button.
