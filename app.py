import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date, timedelta
import os

# --- הגדרות תצוגה ועיצוב ---
st.set_page_config(layout="wide", page_title="מערכת טבלת צדק יחידתית", page_icon="⚖️")

# הזרקת CSS מתקדם לעיצוב יוקרתי ועדין
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;700&display=swap');

    /* הגדרות גוף הדף */
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Assistant', sans-serif;
        background-color: #f8faf8; /* לבן-ירקרק עדין מאוד */
        direction: rtl;
        text-align: right;
    }

    /* עיצוב סרגל הצד */
    [data-testid="stSidebar"] {
        background-color: #2d3e2d !important; /* ירוק כהה עמוק */
        color: white;
    }
    [data-testid="stSidebar"] * {
        color: white !important;
    }

    /* כרטיסיות לבנות לתוכן */
    div.stBlock {
        background-color: white;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }

    /* עיצוב כותרות */
    h1, h2, h3 {
        color: #3e5c3e;
        font-weight: 700;
    }

    /* עיצוב כפתורים */
    div.stButton > button {
        background-color: #557c55;
        color: white !important;
        border-radius: 8px;
        border: none;
        padding: 0.6rem 1rem;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }

    div.stButton > button:hover {
        background-color: #3e5c3e;
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }

    /* עיצוב שדות קלט */
    .stTextInput input, .stSelectbox select, .stTextArea textarea {
        border-radius: 10px !important;
        border: 1px solid #e0e0e0 !important;
        background-color: #ffffff !important;
    }

    /* טבלאות ודאטה פריימים */
    .stDataFrame {
        border-radius: 10px;
        overflow: hidden;
    }

    /* מחוונים (Metrics) */
    [data-testid="stMetricValue"] {
        color: #557c55 !important;
        font-size: 2rem;
    }
    </style>
    """, unsafe_allow_html=True)


# --- פונקציות בסיס נתונים ---
def init_db():
    conn = sqlite3.connect('justice_table.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, personal_id TEXT, name TEXT, 
                  password TEXT, role TEXT, section TEXT, kadar_points INTEGER DEFAULT 0, is_active BOOLEAN)''')
    c.execute('''CREATE TABLE IF NOT EXISTS exemptions 
                 (user_id INTEGER, type TEXT, details TEXT, end_date DATE, status TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS rotations 
                 (start_date DATE, end_date DATE, user_id INTEGER, task_name TEXT, total_days INTEGER, location TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS task_types (name TEXT UNIQUE)''')

    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        c.execute(
            "INSERT INTO users (personal_id, name, password, role, section, kadar_points, is_active) VALUES (?,?,?,?,?,?,?)",
            ("100", "מפקד", "1234", "admin", "מפקדה", 0, 1))
        c.execute(
            "INSERT INTO users (personal_id, name, password, role, section, kadar_points, is_active) VALUES (?,?,?,?,?,?,?)",
            ("200", "לינור ז", "1234", "user", "מחשוב", 0, 1))
        c.execute(
            "INSERT INTO users (personal_id, name, password, role, section, kadar_points, is_active) VALUES (?,?,?,?,?,?,?)",
            ("300", "בר", "1234", "user", "סיסטם", 0, 1))
        c.executemany("INSERT OR IGNORE INTO task_types VALUES (?)", [("מטבח",), ("שמירה",), ("סיור",), ("אבטש",)])
    conn.commit()
    return conn


conn = init_db()

# --- ניהול Session ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'user_role': None, 'user_id': None, 'user_name': ""})

# --- תפריט צד (Sidebar) ---
if st.session_state['logged_in']:
    with st.sidebar:
        if os.path.exists("logo.png"):
            st.image("logo.png", use_container_width=True)
        else:
            st.markdown("<h2 style='text-align:center; color:white;'>⚖️ טבלת צדק</h2>", unsafe_allow_html=True)

        st.write("---")
        st.markdown(f"### שלום, **{st.session_state['user_name']}**")

        admin_menu = ["📅 ניהול שיבוצים", "👥 ניהול חיילים", "🛡️ פטורים", "⚙️ הגדרות", "🔐 שינוי סיסמה"]
        user_menu = ["📌 התורנויות שלי", "📝 בקשת פטור", "🔐 שינוי סיסמה"]

        menu = st.radio("ניווט במערכת:", admin_menu if st.session_state['user_role'] == "admin" else user_menu)

        st.write("---")
        if st.button("🚪 התנתק"):
            st.session_state.update({'logged_in': False})
            st.rerun()

# --- דף כניסה ---
if not st.session_state['logged_in']:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        with st.container():
            st.title("🔐 כניסה למערכת")
            u_name = st.text_input("👤 שם משתמש")
            u_pass = st.text_input("🔑 סיסמה", type="password")
            if st.button("התחבר"):
                res = conn.execute("SELECT id, name, role FROM users WHERE name = ? AND password = ?",
                                   (u_name, u_pass)).fetchone()
                if res:
                    st.session_state.update(
                        {'logged_in': True, 'user_id': res[0], 'user_name': res[1], 'user_role': res[2]})
                    st.rerun()
                else:
                    st.error("❌ פרטים שגויים")

# --- ממשק לאחר התחברות ---
else:
    # שינוי סיסמה
    if menu == "🔐 שינוי סיסמה":
        st.header("🔐 שינוי סיסמה")
        with st.form("change_pass"):
            old_p = st.text_input("סיסמה נוכחית", type="password")
            new_p = st.text_input("סיסמה חדשה", type="password")
            if st.form_submit_button("עדכן סיסמה"):
                curr = conn.execute("SELECT password FROM users WHERE id=?", (st.session_state['user_id'],)).fetchone()
                if old_p == curr[0]:
                    conn.execute("UPDATE users SET password=? WHERE id=?", (new_p, st.session_state['user_id']))
                    conn.commit()
                    st.success("הסיסמה עודכנה!")
                else:
                    st.error("סיסמה שגויה")

    # מנהל: ניהול שיבוצים
    elif menu == "📅 ניהול שיבוצים":
        st.header("📅 ניהול שיבוצים")
        c1, c2 = st.columns([1, 1.5])
        with c1:
            st.subheader("שיבוץ חדש")
            d_range = st.date_input("תאריכים", [date.today(), date.today() + timedelta(days=2)])
            loc = st.text_input("📍 מיקום")
            all_u = pd.read_sql_query("SELECT id, name, kadar_points FROM users WHERE role='user'", conn)
            if not all_u.empty:
                all_u = all_u.sort_values("kadar_points")
                choice = st.selectbox("בחר חייל (לפי נקודות):",
                                      [f"{r['name']} ({r['kadar_points']})" for _, r in all_u.iterrows()])
                sel_id = int(all_u[all_u['name'] == choice.split(" (")[0]].iloc[0]['id'])

                tasks = [t[0] for t in conn.execute("SELECT name FROM task_types").fetchall()]
                task = st.selectbox("משימה", tasks)

                if st.button("בצע שיבוץ"):
                    days = (d_range[1] - d_range[0]).days + 1
                    conn.execute("INSERT INTO rotations VALUES (?,?,?,?,?,?)",
                                 (d_range[0], d_range[1], sel_id, task, days, loc))
                    conn.execute("UPDATE users SET kadar_points = kadar_points + ? WHERE id=?", (days * 5, sel_id))
                    conn.commit()
                    st.success("בוצע!")
        with c2:
            st.subheader("לו\"ז עתידי")
            df = pd.read_sql_query(
                "SELECT r.start_date, r.end_date, u.name, r.task_name FROM rotations r JOIN users u ON r.user_id=u.id",
                conn)
            st.dataframe(df, use_container_width=True)

    # מנהל: ניהול חיילים
    elif menu == "👥 ניהול חיילים":
        st.header("👥 ניהול סגל")
        df = pd.read_sql_query("SELECT personal_id, name, section, kadar_points FROM users WHERE role='user'", conn)
        st.dataframe(df, use_container_width=True)
        with st.expander("הוספת חייל"):
            with st.form("add"):
                p_id = st.text_input("מספר אישי")
                p_name = st.text_input("שם")
                if st.form_submit_button("שמור"):
                    conn.execute(
                        "INSERT INTO users (personal_id, name, password, role, section) VALUES (?,?,'1234','user','כללי')",
                        (p_id, p_name))
                    conn.commit()
                    st.rerun()

    # מנהל: פטורים
    elif menu == "🛡️ פטורים":
        st.header("🛡️ ניהול פטורים")
        pend = pd.read_sql_query(
            "SELECT e.rowid as ID, u.name, e.type, e.end_date FROM exemptions e JOIN users u ON e.user_id=u.id WHERE e.status='ממתין'",
            conn)
        st.table(pend)
        id_to_app = st.number_input("ID לאישור", step=1, min_value=1)
        if st.button("אשר פטור"):
            conn.execute("UPDATE exemptions SET status='מאושר' WHERE rowid=?", (id_to_app,))
            conn.commit()
            st.rerun()

    # חייל: התורנויות שלי
    elif menu == "📌 התורנויות שלי":
        st.header("📌 המשימות שלי")
        pts = conn.execute("SELECT kadar_points FROM users WHERE id=?", (st.session_state['user_id'],)).fetchone()[0]
        st.metric("נקודות צדק שנצברו", pts)
        df = pd.read_sql_query(
            f"SELECT start_date, end_date, task_name, location FROM rotations WHERE user_id={st.session_state['user_id']}",
            conn)
        st.table(df)

    # חייל: בקשת פטור
    elif menu == "📝 בקשת פטור":
        st.header("📝 הגשת בקשה")
        with st.form("ex"):
            t = st.selectbox("סוג", ["רפואי", "אישי"])
            d = st.date_input("עד תאריך")
            if st.form_submit_button("שלח"):
                conn.execute("INSERT INTO exemptions VALUES (?,?,?,?,'ממתין')",
                             (st.session_state['user_id'], t, "בקשה", d))
                conn.commit()
                st.success("נשלח למפקד")

    # הגדרות
    elif menu == "⚙️ הגדרות":
        st.header("⚙️ הגדרות")
        new_t = st.text_input("סוג תורנות חדש")
        if st.button("הוסף"):
            conn.execute("INSERT OR IGNORE INTO task_types VALUES (?)", (new_t,))
            conn.commit()
            st.rerun()