import sqlite3
import pandas as pd
from pathlib import Path

DB_PATH = Path(__file__).parent / "roster.db"

def connect():
    return sqlite3.connect(DB_PATH)

def init_db():
    with connect() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS employees(employee_id INTEGER PRIMARY KEY, name TEXT, pod_name TEXT, weekly_off TEXT);
        CREATE TABLE IF NOT EXISTS brands(brand_id INTEGER PRIMARY KEY, brand_name TEXT, operating_rule TEXT);
        CREATE TABLE IF NOT EXISTS processes(process_id INTEGER PRIMARY KEY, process_name TEXT);
        CREATE TABLE IF NOT EXISTS allocations(employee_id INTEGER, brand_id INTEGER, process_id INTEGER);
        CREATE TABLE IF NOT EXISTS leaves(employee_id INTEGER, leave_date TEXT, leave_type TEXT);
        CREATE TABLE IF NOT EXISTS roster(date TEXT, employee_id INTEGER, employee_name TEXT, brand TEXT, process TEXT, status TEXT, pod TEXT);
        """)

def seed_data():
    with connect() as con:
        if con.execute("SELECT COUNT(*) FROM employees").fetchone()[0]: return
        pods = ["Pod Alpha","Pod Beta","Pod Gamma"]
        names = ["Aarav","Vivaan","Aditya","Vihaan","Arjun","Sai","Reyansh","Krishna","Ishaan","Shaurya",
                 "Ananya","Diya","Aadhya","Saanvi","Pari","Myra","Riya","Ira","Avni","Kavya",
                 "Rahul","Amit","Priya","Sneha","Neha","Karan","Pooja","Rohan","Meera","Dev"]
        offs = ["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"]
        for i,n in enumerate(names):
            con.execute("INSERT INTO employees VALUES(?,?,?,?)",(i+1,n,pods[i//10],offs[i%7]))
        brand_names = [f"Brand {chr(65+i)}" for i in range(20)]
        rules = ["365 days","Sundays off","Public holidays off","365 days"]
        for i,b in enumerate(brand_names):
            con.execute("INSERT INTO brands VALUES(?,?,?)",(i+1,b,rules[i%4]))
        proc = ["Customer Support","Abandoned Cart","NDR","Retention"]
        for i,p in enumerate(proc): con.execute("INSERT INTO processes VALUES(?,?)",(i+1,p))
        # 16 single-resource brands; 4 multi-resource brands.
        for b in range(1,17):
            emp = b
            process_ids = [1,2,3,4]
            for p in process_ids:
                con.execute("INSERT INTO allocations VALUES(?,?,?)",(emp,b,p))
        for b in range(17,21):
            team = [b, b+4, b+8]
            for j,emp in enumerate(team):
                con.execute("INSERT INTO allocations VALUES(?,?,?)",(emp,b,j+1))
        # Example leaves
        con.execute("INSERT INTO leaves VALUES(?,?,?)",(3,"2026-11-25","Planned Leave"))
        con.execute("INSERT INTO leaves VALUES(?,?,?)",(12,"2026-11-28","Comp-off"))

def get_data():
    with connect() as con:
        employees = pd.read_sql_query("SELECT * FROM employees",con)
        brands = pd.read_sql_query("SELECT * FROM brands",con)
        processes = pd.read_sql_query("SELECT * FROM processes",con)
        pods = pd.read_sql_query("SELECT DISTINCT pod_name FROM employees ORDER BY pod_name",con)
        allocations = pd.read_sql_query("""SELECT a.employee_id,b.brand_name,p.process_name
          FROM allocations a JOIN brands b ON b.brand_id=a.brand_id
          JOIN processes p ON p.process_id=a.process_id""",con)
        leaves = pd.read_sql_query("""SELECT e.name,l.leave_date,l.leave_type FROM leaves l
          JOIN employees e ON e.employee_id=l.employee_id""",con)
        roster = pd.read_sql_query("""SELECT r.date,r.employee_id,r.employee_name,r.brand,r.process,r.status,r.pod
          FROM roster r ORDER BY r.date,r.pod,r.employee_name""",con)
    return employees,brands,processes,pods,allocations,leaves,roster

def add_employee(name,pod,weekly_off):
    with connect() as con:
        con.execute("INSERT INTO employees(name,pod_name,weekly_off) VALUES(?,?,?)",(name,pod,weekly_off))

def add_leave(employee_id,leave_date,leave_type):
    with connect() as con:
        con.execute("INSERT INTO leaves VALUES(?,?,?)",(employee_id,str(leave_date),leave_type))

def save_roster(df):
    with connect() as con:
        con.execute("DELETE FROM roster")
        df.to_sql("roster",con,if_exists="append",index=False)

def clear_roster():
    with connect() as con:
        con.execute("DELETE FROM roster")
