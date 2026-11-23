import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
from database import init_db, seed_data, get_data, save_roster, clear_roster
from scheduler import generate_roster, validate_roster

st.set_page_config(page_title="Smart Roster", page_icon="📅", layout="wide")
init_db()
seed_data()

# Simple clean styling
st.markdown("""
<style>
.block-container {padding-top: 1.4rem; padding-bottom: 2rem;}
[data-testid="stSidebar"] {background-color: #12233f;}
[data-testid="stSidebar"] * {color: white;}
div[data-testid="stMetric"] {background: #f3f7ff; padding: 14px; border-radius: 12px; border: 1px solid #e3ebfa;}
.roster-work {background:#dff3e5;color:#176534;padding:5px 8px;border-radius:6px;font-weight:600;text-align:center}
.roster-off {background:#fff0d5;color:#8a5800;padding:5px 8px;border-radius:6px;font-weight:600;text-align:center}
.roster-leave {background:#ffe1e1;color:#a12626;padding:5px 8px;border-radius:6px;font-weight:600;text-align:center}
</style>
""", unsafe_allow_html=True)

st.sidebar.title("📅 Smart Roster")
st.sidebar.caption("Simple workforce scheduling")
page = st.sidebar.radio("Navigate", ["Dashboard", "Employees", "Brands & Rules", "Leaves", "Monthly Roster", "Issues & Reports"])

employees, brands, processes, pods, allocations, leaves, roster = get_data()

if page == "Dashboard":
    st.title("📊 Dashboard")
    st.caption("Your team's monthly scheduling overview")
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Employees", len(employees))
    c2.metric("Brands", len(brands))
    c3.metric("Pods", len(pods))
    c4.metric("Roster entries", len(roster))
    st.subheader("Quick actions")
    q1,q2,q3 = st.columns(3)
    with q1:
        if st.button("➕ Manage employees", use_container_width=True):
            st.session_state["page_jump"] = "Employees"
    with q2:
        if st.button("🏷️ View brands", use_container_width=True):
            st.session_state["page_jump"] = "Brands & Rules"
    with q3:
        if st.button("🗓️ Generate roster", use_container_width=True):
            st.session_state["page_jump"] = "Monthly Roster"
    st.subheader("Roster status")
    if roster.empty:
        st.info("No roster generated yet. Choose **Monthly Roster** to create one.")
    else:
        issues = validate_roster(roster, employees, brands, allocations, leaves)
        st.progress(max(0, 1-len(issues)/max(1,len(roster))))
        st.write(f"Generated schedule has **{len(roster)} assignments** and **{len(issues)} issue(s)**.")
        if issues:
            st.warning("Some coverage or availability issues need attention.")
        else:
            st.success("No validation issues found in this sample roster.")
    st.subheader("Sample team")
    st.dataframe(employees.head(8), use_container_width=True, hide_index=True)

elif page == "Employees":
    st.title("👥 Employees")
    st.caption("Add and edit team members. Sample data includes 30 employees.")
    st.dataframe(employees, use_container_width=True, hide_index=True)
    with st.expander("Add an employee"):
        with st.form("add_employee"):
            name = st.text_input("Employee name")
            pod = st.selectbox("Pod", pods["pod_name"].tolist() if not pods.empty else ["Pod Alpha"])
            weekly_off = st.selectbox("Weekly off", ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"])
            submitted = st.form_submit_button("Add employee")
            if submitted and name.strip():
                from database import add_employee
                add_employee(name.strip(), pod, weekly_off)
                st.success("Employee added. Refresh the page to see the update.")
                st.rerun()

elif page == "Brands & Rules":
    st.title("🏷️ Brands & Processes")
    st.caption("Brand operating rules and minimum coverage")
    st.dataframe(brands, use_container_width=True, hide_index=True)
    st.subheader("Processes")
    st.dataframe(processes, use_container_width=True, hide_index=True)
    st.info("Rule types: 365 days, Sundays off, or public holidays off. Sample rules are configurable in the database.")

elif page == "Leaves":
    st.title("🌴 Leaves & Availability")
    st.caption("Record planned leaves and approved comp-offs")
    st.dataframe(leaves, use_container_width=True, hide_index=True)
    with st.expander("Add leave"):
        with st.form("leave_form"):
            employee = st.selectbox("Employee", employees["name"].tolist())
            leave_date = st.date_input("Date")
            leave_type = st.selectbox("Type", ["Planned Leave", "Comp-off"])
            submit = st.form_submit_button("Save leave")
            if submit:
                from database import add_leave
                emp_id = int(employees.loc[employees["name"] == employee, "employee_id"].iloc[0])
                add_leave(emp_id, leave_date, leave_type)
                st.success("Leave saved.")
                st.rerun()

elif page == "Monthly Roster":
    st.title("🗓️ Monthly Roster")
    st.caption("Generate a monthly schedule, review it, and export it.")
    col1,col2 = st.columns([2,1])
    with col1:
        selected_month = st.date_input("Choose any date in the month", value=date.today())
    with col2:
        st.write("")
        st.write("")
        if st.button("✨ Generate roster", type="primary", use_container_width=True):
            result = generate_roster(selected_month.year, selected_month.month, employees, brands, allocations, leaves)
            save_roster(result)
            st.success("Roster generated!")
            st.rerun()
    roster = get_data()[-1]
    if not roster.empty:
        issues = validate_roster(roster, employees, brands, allocations, leaves)
        st.metric("Validation issues", len(issues))
        if issues:
            st.warning("Roster generated, but some issues require review.")
        else:
            st.success("Roster validation passed.")
        st.dataframe(roster, use_container_width=True, hide_index=True)
        csv = roster.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download roster CSV", csv, "monthly_roster.csv", "text/csv")
        st.subheader("Employee calendar")
        emp_name = st.selectbox("View employee", employees["name"].tolist())
        view = roster[roster["employee_name"] == emp_name].copy()
        if not view.empty:
            view["day"] = pd.to_datetime(view["date"]).dt.strftime("%d")
            pivot = view.pivot_table(index="brand", columns="day", values="status", aggfunc="first", fill_value="")
            st.dataframe(pivot, use_container_width=True)

elif page == "Issues & Reports":
    st.title("🚦 Issues & Reports")
    st.caption("Check coverage gaps and download roster summaries.")
    if roster.empty:
        st.info("Generate a roster first.")
    else:
        issues = validate_roster(roster, employees, brands, allocations, leaves)
        if issues:
            st.warning(f"{len(issues)} issue(s) found")
            st.dataframe(pd.DataFrame(issues), use_container_width=True, hide_index=True)
        else:
            st.success("No issues found.")
        st.download_button("⬇️ Download roster CSV", roster.to_csv(index=False).encode(), "roster_report.csv", "text/csv")
