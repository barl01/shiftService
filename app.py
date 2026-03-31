import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date, timedelta

# --- פונקציות בסיס נתונים ---
def init_db():
    conn = sqlite3.connect('justice_table.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, password TEXT, role TEXT, section TEXT, kadar_points INTEGER, is_active BOOLEAN)''')
    c.execute('''CREATE TABLE IF NOT EXISTS exemptions 
                 (user_id INTEGER, type TEXT, end_date DATE, status TEXT)''')
    # עדכון טבלת rotations להכלת תאריך סיום
    c.execute('''CREATE TABLE IF NOT EXISTS rotations 
                 (start_date DATE, end_date DATE, user_id INTEGER, task_name TEXT, total_days INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS task_types (name TEXT UNIQUE)''')
    
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        users = [
            ("Admin", "1234", "admin", "מפקדה", 0, 1),
            ("Israel", "1234", "user", "מחשוב", 10, 1),
            ("Noa", "1234", "user", "סיסטם", 5, 1)
        ]
        c.executemany("INSERT INTO users (name, password, role, section, kadar_points, is_active) VALUES (?,?,?,?,?,?)", users)
        c.executemany("INSERT OR IGNORE INTO task_types VALUES (?)", [("מטבח",), ("שמירה",), ("סיור",), ("אבטש",)])
    conn.commit()
    return conn

conn = init_db()

# --- לוגיקת מועמדים (בודקת לפי תאריך התחלה) ---
def get_all_candidates(target_date):
    df_users = pd.read_sql_query("SELECT id, name, kadar_points FROM users WHERE is_active = 1 AND role = 'user'", conn)
    df_ex = pd.read_sql_query("SELECT user_id, end_date FROM exemptions WHERE status = 'מאושר'", conn)
    eligible = []
    for _, user in df_users.iterrows():
        user_ex = df_ex[df_ex['user_id'] == user['id']]
        is_exempt = False
        for _, ex in user_ex.iterrows():
            try:
                if datetime.strptime(str(ex['end_date']), '%Y-%m-%d').date() >= target_date:
                    is_exempt = True
                    break
            except: continue
        if not is_exempt:
            eligible.append(user)
    return pd.DataFrame(eligible) if eligible else pd.DataFrame()

# --- ניהול Session ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'user_role': None, 'user_id': None, 'user_name': ""})

st.markdown("""<style> .main { direction: rtl; text-align: right; } </style>""", unsafe_allow_html=True)

# --- דף כניסה ---
if not st.session_state['logged_in']:
    st.title("🔐 מערכת טבלת צדק - ניהול טווחים")
    u_name = st.text_input("שם משתמש")
    u_pass = st.text_input("סיסמה", type="password")
    if st.button("התחבר"):
        res = conn.execute("SELECT id, name, role FROM users WHERE name = ? AND password = ?", (u_name, u_pass)).fetchone()
        if res:
            st.session_state.update({'logged_in':True, 'user_id':res[0], 'user_name':res[1], 'user_role':res[2]})
            st.rerun()
        else: st.error("פרטים שגויים")

# --- ממשק לאחר התחברות ---
else:
    st.sidebar.title(f"שלום, {st.session_state['user_name']}")
    if st.session_state['user_role'] == "admin":
        menu = st.sidebar.radio("ניווט מנהל", ["ניהול שיבוצים", "ניהול חיילים", "הגדרות תורנויות", "אישור פטורים"])
    else:
        menu = st.sidebar.radio("ניווט חייל", ["התורנויות שלי", "בקשת פטור"])
    
    if st.sidebar.button("התנתק"):
        st.session_state.update({'logged_in': False})
        st.rerun()

    # --- מנהל: ניהול שיבוצים (טווח תאריכים) ---
    if menu == "ניהול שיבוצים":
        st.header("📅 שיבוץ תורנות בטווח תאריכים")
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("הגדרת טווח")
            d_range = st.date_input("בחר טווח תאריכים (התחלה וסיום)", [date.today(), date.today() + timedelta(days=1)])
            
            if len(d_range) == 2:
                start_d, end_d = d_range
                num_days = (end_d - start_d).days + 1
                st.write(f"🔢 סה\"כ ימים: **{num_days}**")
                st.write(f"📈 נקודות שיינתנו: **{num_days * 5}**")
                
                tasks = pd.read_sql_query("SELECT name FROM task_types", conn)['name'].tolist()
                task = st.selectbox("משימה", tasks if tasks else ["כללי"])
                
                cands = get_all_candidates(start_d)
                if not cands.empty:
                    cands = cands.sort_values(by='kadar_points')
                    choice = st.selectbox("בחר חייל", [f"{r['name']} ({r['kadar_points']})" for _, r in cands.iterrows()])
                    sel_name = choice.split(" (")[0]
                    sel_id = int(cands[cands['name'] == sel_name].iloc[0]['id'])
                    
                    if st.button("בצע שיבוץ לטווח"):
                        points_to_add = num_days * 5
                        conn.execute("INSERT INTO rotations VALUES (?, ?, ?, ?, ?)", (start_d, end_d, sel_id, task, num_days))
                        conn.execute("UPDATE users SET kadar_points = kadar_points + ? WHERE id = ?", (points_to_add, sel_id))
                        conn.commit()
                        st.success(f"שובץ בהצלחה ל-{num_days} ימים! (נוספו {points_to_add} נקודות)")
                        st.rerun()
            else:
                st.info("יש לבחור תאריך התחלה ותאריך סיום בלוח השנה.")

        with col2:
            st.subheader("לוח תורנויות")
            all_rots = pd.read_sql_query("""
                SELECT r.start_date as 'התחלה', r.end_date as 'סיום', u.name as 'חייל', r.task_name as 'משימה', r.total_days as 'ימים' 
                FROM rotations r JOIN users u ON r.user_id = u.id ORDER BY r.start_date DESC
            """, conn)
            st.dataframe(all_rots, use_container_width=True)

    # --- שאר המסכים (ללא שינוי מהותי אך עם התאמה לטווח) ---
    elif menu == "התורנויות שלי":
        st.header(f"התורנויות של {st.session_state['user_name']}")
        curr_id = st.session_state['user_id']
        pts = conn.execute("SELECT kadar_points FROM users WHERE id = ?", (curr_id,)).fetchone()[0]
        st.metric("נקודות הקאדר שלך", pts)
        
        my_df = pd.read_sql_query(f"SELECT start_date as 'התחלה', end_date as 'סיום', task_name as 'משימה', total_days as 'סה\"כ ימים' FROM rotations WHERE user_id = {curr_id} ORDER BY start_date ASC", conn)
        if not my_df.empty:
            st.table(my_df)
        else: st.info("אין לך תורנויות משובצות.")

    elif menu == "ניהול חיילים":
        st.header("👥 ניהול חיילים")
        df_u = pd.read_sql_query("SELECT id, name as 'שם', kadar_points as 'נקודות', is_active FROM users WHERE role='user'", conn)
        st.dataframe(df_u, use_container_width=True)
        with st.expander("➕ הוספת חייל חדש"):
            new_n = st.text_input("שם")
            if st.button("שמור"):
                conn.execute("INSERT INTO users (name, password, role, section, kadar_points, is_active) VALUES (?, '1234', 'user', 'General', 0, 1)", (new_n,))
                conn.commit()
                st.rerun()

    elif menu == "הגדרות תורנויות":
        st.header("🛠 מאגר משימות")
        nt = st.text_input("שם תורנות")
        if st.button("הוסף"):
            conn.execute("INSERT OR IGNORE INTO task_types VALUES (?)", (nt,))
            conn.commit()
            st.rerun()
        st.table(pd.read_sql_query("SELECT name as 'משימות' FROM task_types", conn))

    elif menu == "אישור פטורים":
        st.header("📋 אישור פטורים")
        pend = pd.read_sql_query("SELECT e.rowid as 'ID', u.name, e.type, e.end_date FROM exemptions e JOIN users u ON e.user_id = u.id WHERE e.status = 'ממתין'", conn)
        if not pend.empty:
            st.dataframe(pend)
            pid = st.number_input("ID לאישור", step=1)
            if st.button("אשר"):
                conn.execute("UPDATE exemptions SET status = 'מאושר' WHERE rowid = ?", (pid,))
                conn.commit()
                st.rerun()
        else: st.info("אין פטורים ממתינים.")

    elif menu == "בקשת פטור":
        st.header("📝 בקשת פטור")
        with st.form("ex_form"):
            e_type = st.selectbox("סוג", ["רפואי", "אישי", "אחר"])
            e_date = st.date_input("תוקף עד")
            if st.form_submit_button("שלח"):
                conn.execute("INSERT INTO exemptions VALUES (?, ?, ?, 'ממתין')", (st.session_state['user_id'], e_type, e_date))
                conn.commit()
                st.success("נשלח!")
