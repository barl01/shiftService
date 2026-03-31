import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date, timedelta

# --- הגדרות תצוגה ---
st.set_page_config(layout="wide", page_title="מערכת טבלת צדק יחידתית")
st.markdown("""<style> .main { direction: rtl; text-align: right; } div.stButton > button { width: 100%; } </style>""", unsafe_allow_html=True)

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
        c.execute("INSERT INTO users (personal_id, name, password, role, section, kadar_points, is_active) VALUES (?,?,?,?,?,?,?)",
                  ("100", "Admin", "1234", "admin", "מפקדה", 0, 1))
        c.execute("INSERT INTO users (personal_id, name, password, role, section, kadar_points, is_active) VALUES (?,?,?,?,?,?,?)",
                  ("200", "ישראל ישראלי", "1234", "user", "מחשוב", 0, 1))
        c.execute("INSERT INTO users (personal_id, name, password, role, section, kadar_points, is_active) VALUES (?,?,?,?,?,?,?)",
                  ("300", "נועה לוי", "1234", "user", "סיסטם", 0, 1))
        c.executemany("INSERT OR IGNORE INTO task_types VALUES (?)", [("מטבח",), ("שמירה",), ("סיור",), ("אבטש",)])
    
    conn.commit()
    return conn

conn = init_db()

# --- לוגיקת זכאות ---
def get_eligible_candidates(target_date):
    df_users = pd.read_sql_query("SELECT id, name, kadar_points FROM users WHERE is_active = 1 AND role = 'user'", conn)
    df_ex = pd.read_sql_query("SELECT user_id, end_date FROM exemptions WHERE status = 'מאושר'", conn)
    
    eligible = []
    for _, user in df_users.iterrows():
        user_ex = df_ex[df_ex['user_id'] == user['id']]
        is_exempt = False
        for _, ex in user_ex.iterrows():
            if str(ex['end_date']) >= str(target_date):
                is_exempt = True
                break
        if not is_exempt:
            eligible.append(user)
    return pd.DataFrame(eligible) if eligible else pd.DataFrame()

# --- ניהול Session ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'user_role': None, 'user_id': None, 'user_name': ""})

# --- דף כניסה ---
if not st.session_state['logged_in']:
    st.title("🔐 מערכת טבלת צדק - כניסה")
    u_name = st.text_input("שם משתמש")
    u_pass = st.text_input("סיסמה", type="password")
    if st.button("התחבר"):
        res = conn.execute("SELECT id, name, role FROM users WHERE name = ? AND password = ?", (u_name, u_pass)).fetchone()
        if res:
            st.session_state.update({'logged_in': True, 'user_id': res[0], 'user_name': res[1], 'user_role': res[2]})
            st.rerun()
        else: st.error("פרטים שגויים")

# --- ממשק לאחר התחברות ---
else:
    st.sidebar.title(f"שלום, {st.session_state['user_name']}")
    if st.session_state['user_role'] == "admin":
        menu = st.sidebar.radio("ניווט מנהל", ["ניהול שיבוצים", "ניהול חיילים", "אישור וצפייה בפטורים", "הגדרות תורנויות"])
    else:
        menu = st.sidebar.radio("ניווט חייל", ["התורנויות שלי", "בקשת פטור"])
    
    if st.sidebar.button("התנתק"):
        st.session_state.update({'logged_in': False})
        st.rerun()

    # --- מנהל: ניהול שיבוצים ---
    if menu == "ניהול שיבוצים":
        st.header("📅 שיבוץ תורנות בטווח תאריכים")
        col1, col2 = st.columns([1, 1])
        with col1:
            d_range = st.date_input("טווח תאריכים", [date.today(), date.today() + timedelta(days=1)])
            loc_input = st.text_input("מיקום התורנות")
            
            if len(d_range) == 2:
                start_d, end_d = d_range
                num_days = (end_d - start_d).days + 1
                tasks = [t[0] for t in conn.execute("SELECT name FROM task_types").fetchall()]
                task = st.selectbox("משימה", tasks if tasks else ["כללי"])
                
                cands = get_eligible_candidates(start_d)
                if not cands.empty:
                    cands = cands.sort_values(by='kadar_points')
                    st.info(f"💡 המלצה: {cands.iloc[0]['name']}")
                    choice = st.selectbox("בחר חייל לשיבוץ", [f"{r['name']} ({r['kadar_points']} נק')" for _, r in cands.iterrows()])
                    sel_id = int(cands[cands['name'] == choice.split(" (")[0]].iloc[0]['id'])
                    
                    if st.button("בצע שיבוץ"):
                        pts = num_days * 5
                        conn.execute("INSERT INTO rotations VALUES (?, ?, ?, ?, ?, ?)", (start_d, end_d, sel_id, task, num_days, loc_input))
                        conn.execute("UPDATE users SET kadar_points = kadar_points + ? WHERE id = ?", (pts, sel_id))
                        conn.commit()
                        st.success("השיבוץ בוצע!")
                        st.rerun()

        with col2:
            st.subheader("📋 תורנויות עתידיות ופעילות")
            today_str = date.today().isoformat()
            # סינון: רק תורנויות שתאריך הסיום שלהן הוא היום או בעתיד
            active_rots = pd.read_sql_query(f"""
                SELECT r.start_date as 'התחלה', r.end_date as 'סיום', u.name as 'חייל', u.section as 'מדור',
                r.task_name as 'משימה', r.location as 'מיקום' FROM rotations r 
                JOIN users u ON r.user_id = u.id 
                WHERE r.end_date >= '{today_str}'
                ORDER BY r.start_date ASC
            """, conn)
            if not active_rots.empty:
                st.dataframe(active_rots, use_container_width=True)
            else:
                st.info("אין תורנויות משובצות לעתיד.")

    # --- מנהל: ניהול חיילים ---
    elif menu == "ניהול חיילים":
        st.header("👥 ניהול סגל וחיילים")
        df_u = pd.read_sql_query("SELECT personal_id as 'מזהה', name as 'שם', section as 'מדור', kadar_points as 'נקודות' FROM users WHERE role='user'", conn)
        st.dataframe(df_u, use_container_width=True)
        
        with st.expander("➕ הוספת חייל חדש"):
            with st.form("add_user_form", clear_on_submit=True):
                p_id = st.text_input("מספר אישי / מזהה")
                p_name = st.text_input("שם מלא")
                p_sec = st.text_input("מדור")
                if st.form_submit_button("שמור במערכת"):
                    if p_id and p_name:
                        conn.execute("INSERT INTO users (personal_id, name, password, role, section, kadar_points, is_active) VALUES (?, ?, '1234', 'user', ?, 0, 1)", (p_id, p_name, p_sec))
                        conn.commit()
                        st.rerun()

    # --- מנהל: אישור וצפייה בפטורים ---
    elif menu == "אישור וצפייה בפטורים":
        st.header("📋 ניהול פטורים")
        st.subheader("⏳ בקשות חדשות לאישור")
        pend = pd.read_sql_query("""
            SELECT e.rowid as 'מזהה_בקשה', u.name as 'חייל', u.section as 'מדור', 
            e.type as 'סוג', e.details as 'פירוט', e.end_date as 'עד_תאריך' 
            FROM exemptions e JOIN users u ON e.user_id = u.id WHERE e.status = 'ממתין'
        """, conn)
        
        if not pend.empty:
            st.dataframe(pend, use_container_width=True)
            req_id = st.number_input("מזהה בקשה לטיפול", step=1, min_value=1)
            c1, c2 = st.columns(2)
            if c1.button("✅ אשר פטור"):
                conn.execute("UPDATE exemptions SET status = 'מאושר' WHERE rowid = ?", (req_id,))
                conn.commit()
                st.rerun()
            if c2.button("❌ דחה ומחק"):
                conn.execute("DELETE FROM exemptions WHERE rowid = ?", (req_id,))
                conn.commit()
                st.rerun()
        
        st.divider()
        st.subheader("✅ פטורים פעילים ותקפים")
        today = date.today().isoformat()
        active_ex = pd.read_sql_query(f"""
            SELECT u.name as 'חייל', u.section as 'מדור', e.type as 'סוג', 
            e.details as 'פירוט', e.end_date as 'בתוקף עד' 
            FROM exemptions e JOIN users u ON e.user_id = u.id 
            WHERE e.status = 'מאושר' AND e.end_date >= '{today}'
            ORDER BY e.end_date ASC
        """, conn)
        st.dataframe(active_ex, use_container_width=True)

    # --- חייל: התורנויות שלי ---
    elif menu == "התורנויות שלי":
        uid = st.session_state['user_id']
        pts = conn.execute("SELECT kadar_points FROM users WHERE id = ?", (uid,)).fetchone()[0]
        st.metric("נקודות הקאדר שלך", pts)
        
        st.subheader("השיבוצים העתידיים שלך")
        today_str = date.today().isoformat()
        # גם כאן סיננו שיראה רק מה שרלוונטי מעכשיו והלאה
        my_df = pd.read_sql_query(f"""
            SELECT start_date as 'התחלה', end_date as 'סיום', task_name as 'משימה', location as 'מיקום' 
            FROM rotations WHERE user_id = {uid} AND end_date >= '{today_str}'
            ORDER BY start_date ASC
        """, conn)
        if not my_df.empty:
            st.table(my_df)
        else:
            st.info("אין לך תורנויות קרובות.")

    # --- חייל: בקשת פטור ---
    elif menu == "בקשת פטור":
        st.header("📝 בקשת פטור חדשה")
        with st.form("ex_req"):
            e_t = st.selectbox("סוג פטור", ["רפואי", "אישי", "אחר"])
            e_d = st.text_area("פירוט")
            e_v = st.date_input("בתוקף עד")
            if st.form_submit_button("שלח למפקד"):
                conn.execute("INSERT INTO exemptions VALUES (?, ?, ?, ?, 'ממתין')", (st.session_state['user_id'], e_t, e_d, e_v))
                conn.commit()
                st.success("הבקשה נשלחה!")

    # --- הגדרות תורנויות ---
    elif menu == "הגדרות תורנויות":
        st.header("🛠 הגדרות משימות")
        nt = st.text_input("שם משימה חדשה")
        if st.button("הוסף"):
            conn.execute("INSERT OR IGNORE INTO task_types VALUES (?)", (nt,))
            conn.commit()
            st.rerun()
        st.table(pd.read_sql_query("SELECT name as 'משימות במאגר' FROM task_types", conn))
