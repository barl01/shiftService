import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date, timedelta
import os

# --- הגדרות תצוגה ועיצוב ---
st.set_page_config(layout="wide", page_title="מערכת טבלת צדק יחידתית", page_icon="⚖️")

# הזרקת CSS משודרג - דגש על תיבות בחירה, טבלאות והתראות
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;700&display=swap');

    /* רקע כללי וגופן */
    .stApp {
        background-color: #f1f4f1; 
        font-family: 'Assistant', sans-serif;
        direction: rtl;
        text-align: right;
    }

    /* עיצוב סרגל הצד */
    [data-testid="stSidebar"] {
        background-color: #2d3e2d !important;
        direction: rtl;
    }
    [data-testid="stSidebar"] * {
        color: white !important;
    }

    /* עיצוב ה"פופים" - תיבות בחירה, קלט ותאריכים */
    .stTextInput input, .stSelectbox div[data-baseweb="select"], .stTextArea textarea, .stDateInput input {
        background-color: #ffffff !important;
        border: 1px solid #c8e6c9 !important;
        border-radius: 12px !important;
        color: #2d3e2d !important;
        padding: 5px 10px !important;
        transition: all 0.3s ease;
    }

    /* עיצוב רשימת הבחירה שנפתחת */
    div[data-baseweb="popover"] { border-radius: 12px !important; }
    div[data-baseweb="menu"] { background-color: #ffffff !important; border-radius: 12px !important; }

    /* עיצוב טבלאות */
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

    /* עיצוב כפתורים */
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

    /* עיצוב התראות */
    .stAlert {
        border-radius: 15px !important;
        border: none !important;
        background-color: rgba(255, 255, 255, 0.7) !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05) !important;
    }

    h1, h2, h3 { color: #1b5e20; text-align: right; margin-bottom: 15px; }
    .stDataFrame { border: none !important; }
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

if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'user_role': None, 'user_id': None, 'user_name': ""})

# --- דף כניסה ---
if not st.session_state['logged_in']:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.title("⚖️ כניסה למערכת")
        with st.container():
            u_name = st.text_input("👤 שם משתמש")
            u_pass = st.text_input("🔑 סיסמה", type="password")
            if st.button("התחבר למערכת"):
                res = conn.execute("SELECT id, name, role FROM users WHERE name = ? AND password = ?",
                                   (u_name, u_pass)).fetchone()
                if res:
                    st.session_state.update(
                        {'logged_in': True, 'user_id': res[0], 'user_name': res[1], 'user_role': res[2]})
                    st.rerun()
                else:
                    st.error("❌ פרטים שגויים, נסה שוב")

# --- ממשק לאחר התחברות ---
else:
    if os.path.exists("logo.png"):
        st.sidebar.image("logo.png", use_container_width=True)
    else:
        st.sidebar.markdown("<h1 style='text-align:center; color:white;'>⚖️</h1>", unsafe_allow_html=True)

    st.sidebar.title(f"שלום, {st.session_state['user_name']} 👋")
    admin_menu = ["📅 ניהול שיבוצים", "👥 ניהול חיילים", "🛡️ אישור וצפייה בפטורים", "⚙️ הגדרות תורנויות", "🔐 שינוי סיסמה"]
    user_menu = ["📌 התורנויות שלי", "📝 בקשת פטור", "🔐 שינוי סיסמה"]
    menu = st.sidebar.radio("תפריט ניווט", admin_menu if st.session_state['user_role'] == "admin" else user_menu)

    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 התנתק"):
        st.session_state.update({'logged_in': False})
        st.rerun()

    # --- שינוי סיסמה ---
    if "שינוי סיסמה" in menu:
        st.header("🔐 שינוי סיסמת כניסה")
        with st.form("change_pass_form"):
            old_p = st.text_input("סיסמה נוכחית", type="password")
            new_p = st.text_input("סיסמה חדשה", type="password")
            confirm_p = st.text_input("אימות סיסמה חדשה", type="password")
            if st.form_submit_button("עדכן סיסמה"):
                current_data = conn.execute("SELECT password FROM users WHERE id = ?",
                                            (st.session_state['user_id'],)).fetchone()
                if old_p != current_data[0]:
                    st.error("❌ הסיסמה הנוכחית אינה נכונה")
                elif new_p != confirm_p:
                    st.error("❌ הסיסמאות החדשות אינן תואמות")
                elif len(new_p) < 4:
                    st.error("❌ הסיסמה החדשה קצרה מדי")
                else:
                    conn.execute("UPDATE users SET password = ? WHERE id = ?", (new_p, st.session_state['user_id']))
                    conn.commit()
                    st.success("✅ הסיסמה עודכנה!")

    # --- מנהל: ניהול שיבוצים ---
    elif "ניהול שיבוצים" in menu:
        st.header("📅 ניהול ושיבוץ תורנויות")
        col1, col2 = st.columns([1, 1.2])
        with col1:
            st.subheader("🛠️ יצירת שיבוץ חדש")
            d_range = st.date_input("טווח תאריכים", [date.today(), date.today() + timedelta(days=1)])
            loc_input = st.text_input("📍 מיקום")
            all_users_df = pd.read_sql_query(
                "SELECT id, name, kadar_points FROM users WHERE role = 'user' AND is_active = 1", conn)
            if not all_users_df.empty:
                sorted_users = all_users_df.sort_values(by='kadar_points')
                recommended = sorted_users.iloc[0]
                st.info(f"✨ מומלץ: **{recommended['name']}** ({recommended['kadar_points']} נק')")
                user_options = [f"{r['name']} ({r['kadar_points']} נק')" for _, r in sorted_users.iterrows()]
                choice = st.selectbox("בחר חייל מהרשימה:", user_options)
                sel_name = choice.split(" (")[0]
                sel_id = int(all_users_df[all_users_df['name'] == sel_name].iloc[0]['id'])

                today_str = date.today().isoformat()
                user_ex = pd.read_sql_query(
                    f"SELECT type as 'סוג', details as 'פירוט', end_date as 'תאריך סיום' FROM exemptions WHERE user_id = {sel_id} AND status = 'מאושר' AND end_date >= '{today_str}'",
                    conn)
                if not user_ex.empty:
                    st.warning(f"⚠️ פטורים פעילים ל{sel_name}:")
                    st.table(user_ex)
                else:
                    st.success(f"✅ ל{sel_name} אין פטורים פעילים.")

                if len(d_range) == 2:
                    start_d, end_d = d_range
                    tasks = [t[0] for t in conn.execute("SELECT name FROM task_types").fetchall()]
                    task = st.selectbox("סוג משימה", tasks if tasks else ["כללי"])
                    if st.button("🚀 אשר שיבוץ"):
                        num_days = (end_d - start_d).days + 1
                        conn.execute("INSERT INTO rotations VALUES (?, ?, ?, ?, ?, ?)",
                                     (start_d, end_d, sel_id, task, num_days, loc_input))
                        conn.execute("UPDATE users SET kadar_points = kadar_points + ? WHERE id = ?",
                                     (num_days * 5, sel_id))
                        conn.commit()
                        st.success("✅ השיבוץ בוצע בהצלחה!")
                        st.rerun()
        with col2:
            st.subheader("📋 לו\"ז תורנויות עתידי")
            # כאן הוספתי את r.location לשאילתה
            active_rots = pd.read_sql_query(
                f"SELECT r.start_date as 'התחלה', r.end_date as 'סיום', u.name as 'חייל', r.task_name as 'משימה', r.location as 'מיקום' FROM rotations r JOIN users u ON r.user_id = u.id WHERE r.end_date >= '{date.today().isoformat()}' ORDER BY r.start_date ASC",
                conn)
            st.dataframe(active_rots, use_container_width=True)

    # --- מנהל: ניהול חיילים ---
    elif "ניהול חיילים" in menu:
        st.header("👥 ניהול סגל וחיילים")
        df_u = pd.read_sql_query(
            "SELECT personal_id as 'מזהה', name as 'שם', section as 'מדור', kadar_points as 'נקודות' FROM users WHERE role='user'",
            conn)
        st.dataframe(df_u, use_container_width=True)
        with st.expander("➕ הוספת חייל חדש"):
            with st.form("add_user"):
                p_id = st.text_input("🔢 מספר אישי")
                p_name = st.text_input("📝 שם מלא")
                p_sec = st.text_input("🏢 מדור")
                if st.form_submit_button("שמור במערכת"):
                    conn.execute(
                        "INSERT INTO users (personal_id, name, password, role, section, kadar_points, is_active) VALUES (?, ?, '1234', 'user', ?, 0, 1)",
                        (p_id, p_name, p_sec))
                    conn.commit()
                    st.rerun()

    # --- מנהל: אישור וצפייה בפטורים ---
    elif "פטורים" in menu:
        st.header("🛡️ ניהול פטורים יחידתי")
        tab1, tab2 = st.tabs(["⏳ בקשות ממתינות", "✅ פטורים מאושרים"])
        with tab1:
            # הוספת e.details (פירוט) לשאילתה
            pend = pd.read_sql_query(
                "SELECT e.rowid as 'ID', u.name as 'חייל', e.type as 'סוג', e.details as 'סיבה/פירוט', e.end_date as 'סיום' FROM exemptions e JOIN users u ON e.user_id = u.id WHERE e.status = 'ממתין'",
                conn)
            if not pend.empty:
                st.table(pend)
                req_id = st.number_input("הכנס ID לאישור", step=1, min_value=1)
                if st.button("✅ אשר פטור"):
                    conn.execute("UPDATE exemptions SET status = 'מאושר' WHERE rowid = ?", (req_id,))
                    conn.commit()
                    st.rerun()
            else:
                st.info("אין בקשות ממתינות כרגע.")
        with tab2:
            # הוספת e.details (פירוט) לשאילתה
            active_ex = pd.read_sql_query(
                f"SELECT u.name as 'חייל', e.type as 'סוג', e.details as 'סיבה/פירוט', e.end_date as 'סיום' FROM exemptions e JOIN users u ON e.user_id = u.id WHERE e.status = 'מאושר' AND e.end_date >= '{date.today().isoformat()}'",
                conn)
            st.table(active_ex)

    # --- חייל: התורנויות שלי ---
    elif "התורנויות שלי" in menu:
        st.header(f"📌 התורנויות שלי - {st.session_state['user_name']}")
        pts = conn.execute("SELECT kadar_points FROM users WHERE id = ?", (st.session_state['user_id'],)).fetchone()[0]
        st.metric("מאזן נקודות צדק", pts)
        my_df = pd.read_sql_query(
            f"SELECT start_date as 'התחלה', end_date as 'סיום', task_name as 'משימה', location as 'מיקום' FROM rotations WHERE user_id = {st.session_state['user_id']} AND end_date >= '{date.today().isoformat()}'",
            conn)
        st.table(my_df)

    # --- חייל: בקשת פטור ---
    elif "בקשת פטור" in menu:
        st.header("📝 הגשת בקשה לפטור")
        with st.form("ex_req"):
            e_t = st.selectbox("סוג הפטור", ["רפואי", "אישי", "אחר"])
            e_d = st.text_area("פירוט וסיבה")
            e_v = st.date_input("תאריך סיום פטור")
            if st.form_submit_button("שלח למפקד"):
                conn.execute(
                    "INSERT INTO exemptions (user_id, type, details, end_date, status) VALUES (?, ?, ?, ?, 'ממתין')",
                    (st.session_state['user_id'], e_t, e_d, e_v))
                conn.commit()
                st.success("✅ הבקשה נשלחה לאישור המפקד.")

    # --- הגדרות ---
    elif "הגדרות" in menu:
        st.header("⚙️ הגדרות מערכת")
        nt = st.text_input("הוסף סוג תורנות חדש")
        if st.button("הוסף"):
            conn.execute("INSERT OR IGNORE INTO task_types VALUES (?)", (nt,))
            conn.commit()
            st.rerun()
        st.table(pd.read_sql_query("SELECT name as 'סוגי תורנויות' FROM task_types", conn))