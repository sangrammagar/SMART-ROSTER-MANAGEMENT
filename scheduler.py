import pandas as pd
import calendar
from datetime import date

def generate_roster(year,month,employees,brands,allocations,leaves):
    _,days=calendar.monthrange(year,month)
    leave_lookup=set()
    if not leaves.empty:
        # resolve names to employee ids
        for _,row in leaves.iterrows():
            matches=employees[employees["name"]==row["name"]]
            if not matches.empty: leave_lookup.add((int(matches.iloc[0]["employee_id"]),str(row["leave_date"])))
    records=[]
    day_names=["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    for day in range(1,days+1):
        dt=date(year,month,day)
        dstr=dt.isoformat()
        for _,emp in employees.iterrows():
            eid=int(emp["employee_id"])
            if (eid,dstr) in leave_lookup:
                status="Leave"
            elif emp["weekly_off"]==day_names[dt.weekday()]:
                status="Off"
            else:
                status="Work"
            if status=="Work":
                alloc=allocations[allocations["employee_id"]==eid]
                if alloc.empty:
                    records.append({"date":dstr,"employee_id":eid,"employee_name":emp["name"],"brand":"Unallocated","process":"—","status":status,"pod":emp["pod_name"]})
                else:
                    for _,a in alloc.iterrows():
                        records.append({"date":dstr,"employee_id":eid,"employee_name":emp["name"],"brand":a["brand_name"],"process":a["process_name"],"status":status,"pod":emp["pod_name"]})
            else:
                records.append({"date":dstr,"employee_id":eid,"employee_name":emp["name"],"brand":"—","process":"—","status":status,"pod":emp["pod_name"]})
    return pd.DataFrame(records)

def validate_roster(roster,employees,brands,allocations,leaves):
    issues=[]
    if roster.empty: return issues
    # Employee leave/weekly-off violations: schedule should show Off/Leave on unavailable days.
    # Check for work records on days status is not Work (data consistency).
    dupes=roster[roster.duplicated(subset=["date","employee_id","brand","process"],keep=False)]
    for _,r in dupes.iterrows():
        issues.append({"date":r["date"],"brand":r["brand"],"process":r["process"],"issue":"Duplicate assignment","employee":r["employee_name"]})
    # Coverage gaps for processes assigned to a brand. Simple baseline: each active brand-process
    # needs at least one working employee on operating days.
    for _,b in brands.iterrows():
        for process in allocations[allocations["brand_name"]==b["brand_name"]]["process_name"].unique():
            for d in roster["date"].unique():
                work=roster[(roster["date"]==d)&(roster["brand"]==b["brand_name"])&(roster["process"]==process)&(roster["status"]=="Work")]
                if work.empty:
                    issues.append({"date":d,"brand":b["brand_name"],"process":process,"issue":"No coverage","employee":"—"})
    return issues
