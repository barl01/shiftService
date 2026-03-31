import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date, timedelta
import os

# --- Configuration & UI Styles ---
st.set_page_config(layout="wide", page_title="Unit Justice System", page_icon="⚖️")

GLOBAL_STYLES = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;700&display=swap');

    .stApp {
        background-color: #f1f4f1; 
        font-family: 'Assistant', sans-serif;
        direction: rtl;
        text-align: right;
    }

    [data-testid="stSidebar"] {
        background-color: #2d3e2d !important;
        direction: rtl;
    }
    [data-testid="stSidebar"] * {
        color: white !important;
    }

    .stTextInput input, .stSelectbox div[data-baseweb="select"], .stTextArea textarea, .stDateInput input {
        background-color: #ffffff !important;
        border: 1px solid #c8e6c9 !important;
        border-radius: 12px !important;
        color: #2d3e2d !important;
        padding: 5px 10px !important;
        transition: all 0.3s ease;
    }

    div[data-baseweb="popover"] { border-radius: 12px !important; }
    div[data-baseweb="menu"] { background-color: #ffffff !important; border-radius: 12px !important; }

    .stTable, [data-testid="stTable"] {
        background-color: white !important;
        border-radius: 15px !important;
        border: 1px solid #e8f5e9 !important;
        overflow: hidden !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03) !important;
    }

    thead tr th {
        background-color: #f9fbf9 !important;
        color: #2e7d32 !important;
        font-weight: 700 !important;
        border-bottom: 2px solid #e8f5e9 !important;
    }

    div.stButton > button {
        width: 100%;
        border-radius: 12px;
        height: 3.5em;
        background-color: #557c55;
        color: white !important;
        border: none;
        font-weight: bold;
        transition: 0.3s;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    div.stButton > button:hover {
        background-color: #3e5c3e;
        transform: translateY(-2px);
    }

    .stAlert {
        border-radius: 15px !important;
        border: none !important;
        background-color: rgba(255, 255, 255, 0.7) !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05) !important;
    }

    h1, h2, h3 { color: #1b5e20; text-align: right; margin-bottom: 15px; }
    .stDataFrame { border: none !important; }
    </style>
"""


# --- Database Core ---
def connect_db():
    return sqlite3.connect('justice_table.db', check_same_thread=False)


def setup_database():
    db = connect_db()
    cursor = db.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, personal_id TEXT, name TEXT, 
                  password TEXT, role TEXT, section TEXT, kadar_points INTEGER DEFAULT 0, is_active BOOLEAN)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS exemptions 
                 (user_id INTEGER, type TEXT, details TEXT, end_date DATE, status TEXT)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS rotations 
                 (start_date DATE, end_date DATE, user_id INTEGER, task_name TEXT, total_days INTEGER, location TEXT)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS task_types (name TEXT UNIQUE)''')

    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO users (personal_id, name, password, role, section, kadar_points, is_active) VALUES (?,?,?,?,?,?,?)",
            ("100", "מפקד", "1234", "admin", "מפקדה", 0, 1))

        tasks = [("מטבח",), ("שמירה",), ("סיור",), ("אבטש",)]
        cursor.executemany("INSERT OR IGNORE INTO task_types VALUES (?)", tasks)

    db.commit()
    return db


# --- App Logic Functions ---
def verify_credentials(user, pwd, db):
    return db.execute("SELECT id, name, role FROM users WHERE name = ? AND password = ?", (user, pwd)).fetchone()


def run_login_screen(db):
    _, container, _ = st.columns([1, 1.5, 1])
    with container:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.title("⚖️ כניסה למערכת")
        user_input = st.text_input("👤 שם משתמש")
        pass_input = st.text_input("🔑 סיסמה", type="password")

        if st.button("התחבר למערכת"):
            record = verify_credentials(user_input, pass_input, db)
            if record:
                st.session_state.update(
                    {'logged_in': True, 'user_id': record[0], 'user_name': record[1], 'user_role': record[2]})
                st.rerun()
            else:
                st.error("❌ פרטים שגויים, נסה שוב")


def main_app():
    st.markdown(GLOBAL_STYLES, unsafe_allow_html=True)
    db_conn = setup_database()

    if 'logged_in' not in st.session_state:
        st.session_state.update({'logged_in': False, 'user_role': None, 'user_id': None, 'user_name': ""})

    if not st.session_state['logged_in']:
        run_login_screen(db_conn)
        return

    # Sidebar Navigation
    if os.path.exists("logo.png"):
        st.sidebar.image("logo.png", use_container_width=True)
    else:
        st.sidebar.markdown("<h1 style='text-align:center; color:white;'>⚖️</h1>", unsafe_allow_html=True)

    st.sidebar.title(f"שלום, {st.session_state['user_name']} 👋")

    admin_nav = ["📅 ניהול שיבוצים", "🔍 היסטוריית תורנויות", "👥 ניהול חיילים", "🛡️ אישור וצפייה בפטורים",
                 "⚙️ הגדרות תורנויות", "🔐 שינוי סיסמה"]
    user_nav = ["📌 התורנויות שלי", "📝 בקשת פטור", "🔐 שינוי סיסמה"]

    view_mode = st.sidebar.radio("תפריט ניווט", admin_nav if st.session_state['user_role'] == "admin" else user_nav)

    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 התנתק"):
        st.session_state.update({'logged_in': False})
        st.rerun()

    # Routing Logic
    if "שינוי סיסמה" in view_mode:
        st.header("🔐 שינוי סיסמת כניסה")
        with st.form("reset_pwd"):
            cur_p = st.text_input("סיסמה נוכחית", type="password")
            new_p = st.text_input("סיסמה חדשה", type="password")
            ver_p = st.text_input("אימות סיסמה חדשה", type="password")
            if st.form_submit_button("עדכן סיסמה"):
                actual = \
                db_conn.execute("SELECT password FROM users WHERE id = ?", (st.session_state['user_id'],)).fetchone()[0]
                if cur_p != actual:
                    st.error("❌ הסיסמה נוכחית אינה נכונה")
                elif new_p != ver_p:
                    st.error("❌ הסיסמאות החדשות אינן תואמות")
                elif len(new_p) < 4:
                    st.error("❌ הסיסמה החדשה קצרה מדי")
                else:
                    db_conn.execute("UPDATE users SET password = ? WHERE id = ?", (new_p, st.session_state['user_id']))
                    db_conn.commit()
                    st.success("✅ הסיסמה עודכנה!")

    elif "ניהול שיבוצים" in view_mode:
        st.header("📅 ניהול ושיבוץ תורנויות")
        left, right = st.columns([1, 1.2])
        with left:
            st.subheader("🛠️ יצירת שיבוץ חדש")
            range_dates = st.date_input("טווח תאריכים", [date.today(), date.today() + timedelta(days=1)])
            site = st.text_input("📍 מיקום")

            # Use original kadar_points column name
            members = pd.read_sql_query(
                "SELECT id, name, kadar_points FROM users WHERE role = 'user' AND is_active = 1", db_conn)
            if not members.empty:
                members_sorted = members.sort_values(by='kadar_points')
                top_candidate = members_sorted.iloc[0]
                st.info(f"✨ מומלץ: **{top_candidate['name']}** ({top_candidate['kadar_points']} נק')")

                options = [f"{r['name']} ({r['kadar_points']} נק')" for _, r in members_sorted.iterrows()]
                selected = st.selectbox("בחר חייל מהרשימה:", options)

                target_name = selected.split(" (")[0]
                target_uid = int(members[members['name'] == target_name].iloc[0]['id'])

                active_ex = pd.read_sql_query(
                    f"SELECT type as 'סוג', details as 'פירוט', end_date as 'תאריך סיום' FROM exemptions WHERE user_id = {target_uid} AND status = 'מאושר' AND end_date >= '{date.today().isoformat()}'",
                    db_conn)
                if not active_ex.empty:
                    st.warning(f"⚠️ פטורים פעילים ל{target_name}:")
                    st.table(active_ex)
                else:
                    st.success(f"✅ ל{target_name} אין פטורים פעילים.")

                if len(range_dates) == 2:
                    s_date, e_date = range_dates
                    tasks = [t[0] for t in db_conn.execute("SELECT name FROM task_types").fetchall()]
                    chosen_task = st.selectbox("סוג משימה", tasks if tasks else ["כללי"])
                    if st.button("🚀 אשר שיבוץ"):
                        days_count = (e_date - s_date).days + 1
                        db_conn.execute("INSERT INTO rotations VALUES (?, ?, ?, ?, ?, ?)",
                                        (s_date, e_date, target_uid, chosen_task, days_count, site))
                        db_conn.execute("UPDATE users SET kadar_points = kadar_points + ? WHERE id = ?",
                                        (days_count * 5, target_uid))
                        db_conn.commit()
                        st.success("✅ השיבוץ בוצע בהצלחה!")
                        st.rerun()
        with right:
            st.subheader("📋 לו\"ז תורנויות עתידי")
            future_q = f"SELECT r.start_date as 'התחלה', r.end_date as 'סיום', u.name as 'חייל', r.task_name as 'משימה', r.location as 'מיקום' FROM rotations r JOIN users u ON r.user_id = u.id WHERE r.end_date >= '{date.today().isoformat()}' ORDER BY r.start_date ASC"
            st.dataframe(pd.read_sql_query(future_q, db_conn), use_container_width=True)

    elif "היסטוריית תורנויות" in view_mode:
        st.header("🔍 היסטוריית תורנויות מלאה")
        all_u = pd.read_sql_query("SELECT id, name FROM users WHERE role = 'user'", db_conn)
        if not all_u.empty:
            pick = st.selectbox("בחר חייל לצפייה בכל ההיסטוריה שלו:", all_u['name'].tolist())
            picked_id = all_u[all_u['name'] == pick].iloc[0]['id']
            logs = pd.read_sql_query(
                f"SELECT start_date as 'התחלה', end_date as 'סיום', task_name as 'משימה', location as 'מיקום', total_days as 'ימים' FROM rotations WHERE user_id = {picked_id} ORDER BY start_date DESC",
                db_conn)
            if not logs.empty:
                st.table(logs)
            else:
                st.info(f"לא נמצאה היסטוריה עבור {pick}")

    elif "ניהול חיילים" in view_mode:
        st.header("👥 ניהול סגל וחיילים")
        summary = pd.read_sql_query(
            "SELECT personal_id as 'מזהה', name as 'שם', section as 'מדור', kadar_points as 'נקודות' FROM users WHERE role='user'",
            db_conn)
        st.dataframe(summary, use_container_width=True)
        with st.expander("➕ הוספת חייל חדש"):
            with st.form("create_user"):
                new_pid = st.text_input("🔢 מספר אישי")
                new_name = st.text_input("📝 שם מלא")
                new_sec = st.text_input("🏢 מדור")
                if st.form_submit_button("שמור במערכת"):
                    db_conn.execute(
                        "INSERT INTO users (personal_id, name, password, role, section, kadar_points, is_active) VALUES (?, ?, '1234', 'user', ?, 0, 1)",
                        (new_pid, new_name, new_sec))
                    db_conn.commit()
                    st.rerun()

    elif "פטורים" in view_mode:
        st.header("🛡️ ניהול פטורים יחידתי")
        t_pend, t_act = st.tabs(["⏳ בקשות ממתינות", "✅ פטורים מאושרים"])
        with t_pend:
            pending_df = pd.read_sql_query(
                "SELECT e.rowid as 'ID', u.name as 'חייל', e.type as 'סוג', e.details as 'סיבה/פירוט', e.end_date as 'סיום' FROM exemptions e JOIN users u ON e.user_id = u.id WHERE e.status = 'ממתין'",
                db_conn)
            if not pending_df.empty:
                st.table(pending_df)
                app_id = st.number_input("הכנס ID לאישור", step=1, min_value=1)
                if st.button("✅ אשר פטור"):
                    db_conn.execute("UPDATE exemptions SET status = 'מאושר' WHERE rowid = ?", (app_id,))
                    db_conn.commit()
                    st.rerun()
            else:
                st.info("אין בקשות ממתינות.")
        with t_act:
            approved_q = f"SELECT u.name as 'חייל', e.type as 'סוג', e.details as 'סיבה/פירוט', e.end_date as 'סיום' FROM exemptions e JOIN users u ON e.user_id = u.id WHERE e.status = 'מאושר' AND e.end_date >= '{date.today().isoformat()}'"
            st.table(pd.read_sql_query(approved_q, db_conn))

    elif "התורנויות שלי" in view_mode:
        st.header(f"📌 התורנויות שלי - {st.session_state['user_name']}")
        score = \
        db_conn.execute("SELECT kadar_points FROM users WHERE id = ?", (st.session_state['user_id'],)).fetchone()[0]
        st.metric("מאזן נקודות צדק", score)

        st.subheader("📅 תורנויות קרובות")
        today_val = date.today().isoformat()
        personal_future = pd.read_sql_query(
            f"SELECT start_date as 'התחלה', end_date as 'סיום', task_name as 'משימה', location as 'מיקום' FROM rotations WHERE user_id = {st.session_state['user_id']} AND end_date >= '{today_val}' ORDER BY start_date ASC",
            db_conn)
        if not personal_future.empty:
            st.table(personal_future)
        else:
            st.info("אין שיבוצים עתידיים.")

        with st.expander("🕒 היסטוריית תורנויות אישית"):
            personal_past = pd.read_sql_query(
                f"SELECT start_date as 'התחלה', end_date as 'סיום', task_name as 'משימה', location as 'מיקום' FROM rotations WHERE user_id = {st.session_state['user_id']} AND end_date < '{today_val}' ORDER BY start_date DESC",
                db_conn)
            if not personal_past.empty:
                st.table(personal_past)
            else:
                st.write("אין היסטוריה קודמת.")

    elif "בקשת פטור" in view_mode:
        st.header("📝 הגשת בקשה לפטור")
        with st.form("req_ex"):
            type_ex = st.selectbox("סוג הפטור", ["רפואי", "אישי", "אחר"])
            desc_ex = st.text_area("פירוט וסיבה")
            end_ex = st.date_input("תאריך סיום פטור")
            if st.form_submit_button("שלח למפקד"):
                db_conn.execute(
                    "INSERT INTO exemptions (user_id, type, details, end_date, status) VALUES (?, ?, ?, ?, 'ממתין')",
                    (st.session_state['user_id'], type_ex, desc_ex, end_ex))
                db_conn.commit()
                st.success("✅ הבקשה נשלחה.")

    elif "הגדרות" in view_mode:
        st.header("⚙️ הגדרות מערכת")
        input_task = st.text_input("הוסף סוג תורנות חדש")
        if st.button("הוסף"):
            db_conn.execute("INSERT OR IGNORE INTO task_types VALUES (?)", (input_task,))
            db_conn.commit()
            st.rerun()
        st.table(pd.read_sql_query("SELECT name as 'סוגי תורנויות' FROM task_types", db_conn))


if __name__ == "__main__":
    main_app()