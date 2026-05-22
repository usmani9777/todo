import streamlit as st
import sqlite3
from datetime import datetime, date
import os

st.set_page_config(
    page_title="GS Document Tracker",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
html, body, [class*="css"] { font-family: 'Segoe UI', sans-serif; }
section[data-testid="stSidebar"] { background: #1a1f2e; }
section[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
section[data-testid="stSidebar"] .stTextInput input {
    background: #2d3748; border: 1px solid #4a5568; border-radius: 8px; color: #e2e8f0 !important;
}
</style>
""", unsafe_allow_html=True)

# ─── Database ─────────────────────────────────────────────────────────────────
DB = os.path.join(os.path.dirname(__file__), "gs_tracker.db")

def conn():
    c = sqlite3.connect(DB, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    with conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS items (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_name     TEXT    NOT NULL DEFAULT 'GS Checklist',
            category     TEXT    NOT NULL,
            requirements TEXT,
            assigned_to  TEXT,
            status       TEXT    NOT NULL DEFAULT 'Pending',
            target_date  TEXT,
            verified     INTEGER NOT NULL DEFAULT 0,
            verified_by  TEXT,
            verified_at  TEXT,
            created_by   TEXT    DEFAULT 'System',
            created_at   TEXT    DEFAULT (datetime('now','localtime')),
            updated_at   TEXT    DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS notes (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id    INTEGER NOT NULL,
            note       TEXT    NOT NULL,
            author     TEXT    NOT NULL,
            created_at TEXT    DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (item_id) REFERENCES items(id)
        );

        CREATE TABLE IF NOT EXISTS activity_log (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id    INTEGER,
            action     TEXT NOT NULL,
            detail     TEXT,
            actor      TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );
        """)
        if c.execute("SELECT COUNT(*) FROM items").fetchone()[0] == 0:
            seed = [
                ("GS Checklist", "Property Sale: Path A (If Transaction Executed)",
                 "• Full officially registered Sale Deed\n• Withholding Tax Receipt\n• Bank statements showing full transfer of proceeds",
                 "Father", "Pending", "2026-07-31"),
                ("GS Checklist", "Property Sale: Path B (If Transaction Unexecuted)",
                 "• Official bank statements showing alternative or additional liquid funds covering tuition & living costs",
                 "Father / Applicant", "Pending", "2026-07-31"),
                ("GS Checklist", "Brother's Income Capacity",
                 "• Income Tax Return documents for the past 1 single year",
                 "Brother", "Done", None),
                ("GS Checklist", "Father's Rental Income Evidence",
                 "• Official property ownership documents\n• Valid lease/rental agreements verifying tax declaration",
                 "Father", "Done", None),
                ("GS Checklist", "Mother's / Sponsor's CA Net Wealth Certificate",
                 "• Issued by practicing Chartered Accountant\n• Formal CA letterhead with stamp & signature\n• Explicit membership & firm registration details",
                 "Mother / CA", "Pending", None),
                ("GS Checklist", "Genuine Student (GS) Assessment Form",
                 "• Completed GS form with the 150-word targeted statement responses finalized",
                 "Applicant", "Done", None),
            ]
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for row in seed:
                c.execute(
                    "INSERT INTO items (doc_name, category, requirements, assigned_to, status, target_date, created_by, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
                    (*row, "System", now, now)
                )
            c.execute("INSERT INTO activity_log (action, detail, actor) VALUES (?,?,?)",
                      ("INIT", "Database seeded with GS Checklist", "System"))

init_db()

# ─── DB helpers ───────────────────────────────────────────────────────────────
STATUS_OPTIONS = ["Pending", "In Progress", "Done", "Blocked", "Verified"]

def get_docs():
    with conn() as c:
        rows = c.execute("SELECT DISTINCT doc_name FROM items ORDER BY doc_name").fetchall()
    return [r["doc_name"] for r in rows]

def get_items(doc_name=None):
    q = "SELECT * FROM items WHERE 1=1"
    params = []
    if doc_name:
        q += " AND doc_name=?"; params.append(doc_name)
    q += " ORDER BY id"
    with conn() as c:
        return c.execute(q, params).fetchall()

def get_notes(item_id):
    with conn() as c:
        return c.execute("SELECT * FROM notes WHERE item_id=? ORDER BY created_at", (item_id,)).fetchall()

def get_logs(limit=100):
    with conn() as c:
        return c.execute("SELECT * FROM activity_log ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()

def update_item(item_id, field, value, actor):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with conn() as c:
        old = c.execute(f"SELECT {field} FROM items WHERE id=?", (item_id,)).fetchone()[0]
        c.execute(f"UPDATE items SET {field}=?, updated_at=? WHERE id=?", (value, now, item_id))
        c.execute("INSERT INTO activity_log (item_id, action, detail, actor) VALUES (?,?,?,?)",
                  (item_id, f"UPDATE {field.upper()}", f"{old} → {value}", actor))

def add_note(item_id, note, author):
    with conn() as c:
        c.execute("INSERT INTO notes (item_id, note, author) VALUES (?,?,?)", (item_id, note, author))
        c.execute("INSERT INTO activity_log (item_id, action, detail, actor) VALUES (?,?,?,?)",
                  (item_id, "NOTE", note[:80], author))

def add_item(doc_name, category, requirements, assigned_to, status, target_date, actor):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with conn() as c:
        c.execute(
            "INSERT INTO items (doc_name, category, requirements, assigned_to, status, target_date, created_by, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (doc_name, category, requirements, assigned_to, status, target_date or None, actor, now, now)
        )
        c.execute("INSERT INTO activity_log (action, detail, actor) VALUES (?,?,?)",
                  ("ADD ITEM", f"[{doc_name}] {category}", actor))

def delete_item(item_id, actor):
    with conn() as c:
        row = c.execute("SELECT category FROM items WHERE id=?", (item_id,)).fetchone()
        c.execute("DELETE FROM items WHERE id=?", (item_id,))
        c.execute("DELETE FROM notes WHERE item_id=?", (item_id,))
        c.execute("INSERT INTO activity_log (action, detail, actor) VALUES (?,?,?)",
                  ("DELETE", row["category"] if row else str(item_id), actor))

# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📋 GS Tracker")
    st.markdown("---")

    user = st.text_input("👤 Your name", value=st.session_state.get("user", ""), placeholder="Enter your name…")
    if user:
        st.session_state["user"] = user
    else:
        user = st.session_state.get("user", "Anonymous")

    st.markdown("---")
    docs = get_docs()
    selected_doc = st.selectbox("📁 Checklist", ["All"] + docs)
    st.markdown("---")

    sidebar_items = get_items(doc_name=selected_doc if selected_doc != "All" else None)
    total_s   = len(sidebar_items)
    done_s    = sum(1 for r in sidebar_items if r["status"] == "Done")
    blocked_s = sum(1 for r in sidebar_items if r["status"] == "Blocked")
    pct_s     = int(done_s / total_s * 100) if total_s else 0

    st.progress(pct_s / 100)
    st.markdown(f"**{done_s} / {total_s}** tasks done")
    if blocked_s:
        st.error(f"🚫 {blocked_s} task(s) blocked")
    st.markdown(f"Logged in as **{user}**")

# ─── Header ───────────────────────────────────────────────────────────────────
st.markdown("# 📋 GS Document Tracker")
st.caption("ECU Visa Compliance — Genuine Student Assessment")

if user == "Anonymous":
    st.info("👈 Enter your name in the sidebar so your changes are tracked.")

# ─── Tabs ─────────────────────────────────────────────────────────────────────
tab_list, tab_add, tab_history = st.tabs(["📋 Checklist", "➕ Add Task", "📜 History"])

# ─── CHECKLIST ────────────────────────────────────────────────────────────────
with tab_list:
    doc_filter = selected_doc if selected_doc != "All" else None
    all_items  = get_items(doc_name=doc_filter)
    total      = len(all_items)
    done_n     = sum(1 for r in all_items if r["status"] == "Done")
    blocked_n  = sum(1 for r in all_items if r["status"] == "Blocked")
    pct        = int(done_n / total * 100) if total else 0

    st.progress(pct / 100, text=f"**{pct}% complete** — {done_n} of {total} tasks done")
    if blocked_n:
        st.warning(f"🚫 {blocked_n} task(s) blocked — need attention")

    with st.expander("⚠️ Important Advisories"):
        st.markdown("""
**🚨 Property Sale Funds**
Funds from an *unexecuted* sale cannot be used. If the sale is not done by **July 31 2026**, switch to Path B (alternative liquid funds).

**📌 CA Net Wealth Certificate**
Must include the CA's registration/membership number. Missing identifiers cause immediate rejection.

**🔗 Cross-Reference**
Rental amounts in lease agreements must exactly match values declared in the FBR / Income Tax returns.
        """)

    st.markdown("---")

    # Filter
    show = st.radio(
        "Show:",
        ["All tasks", "⬜ To Do", "✅ Done", "🚫 Blocked"],
        horizontal=True,
        label_visibility="collapsed",
    )
    STATUS_GROUPS = {
        "All tasks":  None,
        "⬜ To Do":   ["Pending", "In Progress"],
        "✅ Done":    ["Done", "Verified"],
        "🚫 Blocked": ["Blocked"],
    }
    allowed = STATUS_GROUPS[show]
    items = all_items if not allowed else [r for r in all_items if r["status"] in allowed]

    if not items:
        st.info("No tasks match this filter.")

    ICON = {"Done": "✅", "Verified": "⭐", "In Progress": "🔵", "Blocked": "🚫", "Pending": "⬜"}

    for row in items:
        iid     = row["id"]
        status  = row["status"]
        is_done = status in ("Done", "Verified")
        icon    = ICON.get(status, "⬜")

        label_parts = [f"{icon}  {row['category']}"]
        if row["assigned_to"]:
            label_parts.append(f"👤 {row['assigned_to']}")
        if row["target_date"]:
            label_parts.append(f"📅 {row['target_date']}")
        exp_label = "   ·   ".join(label_parts)

        with st.expander(exp_label):

            # Requirements
            if row["requirements"]:
                st.markdown(row["requirements"])
            else:
                st.caption("No requirements listed.")

            st.divider()

            # ── Primary action ──────────────────────────────────────────────
            act_col, status_col = st.columns([1, 2])

            with act_col:
                if is_done:
                    if st.button("🔄 Reopen", key=f"reopen_{iid}", use_container_width=True):
                        if user == "Anonymous":
                            st.error("Enter your name in the sidebar first.")
                        else:
                            update_item(iid, "status", "Pending", user)
                            st.session_state[f"st_{iid}"] = "Pending"
                            st.rerun()
                else:
                    if st.button("✅ Mark as Done", key=f"done_{iid}", type="primary", use_container_width=True):
                        if user == "Anonymous":
                            st.error("Enter your name in the sidebar first.")
                        else:
                            update_item(iid, "status", "Done", user)
                            st.session_state[f"st_{iid}"] = "Done"
                            st.session_state[f"show_note_{iid}"] = True
                            st.rerun()

            with status_col:
                cur_idx   = STATUS_OPTIONS.index(status) if status in STATUS_OPTIONS else 0
                new_status = st.selectbox(
                    "Set status",
                    STATUS_OPTIONS,
                    index=cur_idx,
                    key=f"st_{iid}",
                    label_visibility="visible",
                )
                if new_status != status:
                    if st.button("Update →", key=f"upd_st_{iid}", use_container_width=True):
                        if user == "Anonymous":
                            st.error("Enter your name in the sidebar first.")
                        else:
                            update_item(iid, "status", new_status, user)
                            st.rerun()

            # ── Completion note (shown right after marking Done) ────────────
            if st.session_state.get(f"show_note_{iid}"):
                st.success("Marked as done! Record what was completed (optional):")
                comp_note = st.text_area(
                    "comp_note_label",
                    key=f"comp_note_{iid}",
                    height=70,
                    label_visibility="collapsed",
                    placeholder="e.g. Receipt #123 uploaded — received from Father on 2026-05-22…",
                )
                cn1, cn2 = st.columns(2)
                with cn1:
                    if st.button("💾 Save Note", key=f"save_cn_{iid}", type="primary", use_container_width=True):
                        if comp_note.strip():
                            add_note(iid, comp_note.strip(), user)
                        st.session_state[f"show_note_{iid}"] = False
                        st.rerun()
                with cn2:
                    if st.button("Skip", key=f"skip_cn_{iid}", use_container_width=True):
                        st.session_state[f"show_note_{iid}"] = False
                        st.rerun()

            st.divider()

            # ── Notes ───────────────────────────────────────────────────────
            notes = get_notes(iid)
            if notes:
                st.markdown(f"**Notes ({len(notes)})**")
                for n in notes:
                    st.markdown(f"**{n['author']}** · *{n['created_at'][:10]}*")
                    st.markdown(f"> {n['note']}")
            else:
                st.caption("No notes yet.")

            with st.form(key=f"note_form_{iid}", clear_on_submit=True):
                new_note = st.text_area(
                    "note_label",
                    height=70,
                    label_visibility="collapsed",
                    placeholder="Add a note about this task…",
                )
                if st.form_submit_button("📝 Post Note", use_container_width=True):
                    if new_note.strip():
                        add_note(iid, new_note.strip(), user if user != "Anonymous" else "Anonymous")
                        st.rerun()

            st.divider()

            # ── Edit details ────────────────────────────────────────────────
            if st.button("✏️ Edit details", key=f"edit_toggle_{iid}"):
                st.session_state[f"edit_open_{iid}"] = not st.session_state.get(f"edit_open_{iid}", False)

            if st.session_state.get(f"edit_open_{iid}"):
                with st.form(key=f"edit_form_{iid}"):
                    new_cat  = st.text_input("Task name", value=row["category"])
                    new_reqs = st.text_area("Requirements", value=row["requirements"] or "", height=120)
                    ef1, ef2 = st.columns(2)
                    with ef1:
                        new_assign = st.text_input("Assigned to", value=row["assigned_to"] or "")
                    with ef2:
                        cur_date = date.fromisoformat(row["target_date"]) if row["target_date"] else None
                        new_date = st.date_input("Target date", value=cur_date)

                    if st.form_submit_button("💾 Save Changes", type="primary", use_container_width=True):
                        if user == "Anonymous":
                            st.error("Enter your name in the sidebar first.")
                        else:
                            if new_cat   != row["category"]:              update_item(iid, "category",    new_cat,   user)
                            if new_reqs  != (row["requirements"] or ""):  update_item(iid, "requirements", new_reqs,  user)
                            if new_assign != (row["assigned_to"] or ""):  update_item(iid, "assigned_to",  new_assign, user)
                            nd = new_date.isoformat() if new_date else None
                            if nd != row["target_date"]:                  update_item(iid, "target_date",  nd,        user)
                            st.session_state[f"edit_open_{iid}"] = False
                            st.rerun()

            # ── Delete ──────────────────────────────────────────────────────
            if st.button("🗑️ Delete task", key=f"del_{iid}"):
                st.session_state[f"confirm_del_{iid}"] = True

            if st.session_state.get(f"confirm_del_{iid}"):
                st.error(f"Delete **{row['category'][:60]}**? This cannot be undone.")
                dc1, dc2 = st.columns(2)
                with dc1:
                    if st.button("Yes, delete", key=f"yes_del_{iid}", type="primary"):
                        delete_item(iid, user)
                        st.session_state.pop(f"confirm_del_{iid}", None)
                        st.rerun()
                with dc2:
                    if st.button("Cancel", key=f"cancel_del_{iid}"):
                        st.session_state.pop(f"confirm_del_{iid}", None)
                        st.rerun()

# ─── ADD TASK ─────────────────────────────────────────────────────────────────
with tab_add:
    st.markdown("### ➕ Add a New Task")

    with st.form("add_form", clear_on_submit=True):
        docs_list  = get_docs()
        doc_choice = st.radio("Add to:", ["Existing checklist", "New checklist"], horizontal=True)
        if doc_choice == "Existing checklist":
            doc_name = st.selectbox("Checklist", docs_list or ["GS Checklist"])
        else:
            doc_name = st.text_input("New checklist name", placeholder="e.g. Murdoch University")

        cat  = st.text_input("Task name *", placeholder="e.g. Bank Statement — 6 months")
        reqs = st.text_area(
            "Requirements / details",
            placeholder="• Document requirements\n• File format\n• Who to get it from",
            height=120,
        )

        af1, af2, af3 = st.columns(3)
        with af1:
            assign  = st.text_input("Assigned to", placeholder="e.g. Father")
        with af2:
            init_st = st.selectbox("Initial status", STATUS_OPTIONS)
        with af3:
            tdate   = st.date_input("Target date", value=None)

        if st.form_submit_button("➕ Add Task", type="primary", use_container_width=True):
            if not cat.strip():
                st.warning("Task name is required.")
            elif not doc_name or not doc_name.strip():
                st.warning("Checklist name is required.")
            else:
                add_item(
                    doc_name=doc_name.strip(),
                    category=cat.strip(),
                    requirements=reqs.strip(),
                    assigned_to=assign.strip(),
                    status=init_st,
                    target_date=tdate.isoformat() if tdate else None,
                    actor=user,
                )
                st.success(f"Task added to **{doc_name}**!")
                st.rerun()

# ─── HISTORY ──────────────────────────────────────────────────────────────────
with tab_history:
    st.markdown("### 📜 Activity History")
    st.caption("Audit trail of all changes, notes, and updates.")

    logs = get_logs(150)
    if not logs:
        st.info("No activity yet.")
    else:
        ACTION_ICONS = {
            "INIT": "🌱", "ADD ITEM": "➕", "DELETE": "🗑️",
            "UPDATE STATUS": "🔄", "UPDATE CATEGORY": "✏️",
            "UPDATE ASSIGNED_TO": "👤", "UPDATE TARGET_DATE": "📅",
            "UPDATE REQUIREMENTS": "📋", "NOTE": "💬",
            "VERIFIED": "✅", "UNVERIFIED": "🔒",
        }
        for log in logs:
            icon     = ACTION_ICONS.get(log["action"], "📌")
            item_ref = f"Task #{log['item_id']} — " if log["item_id"] else ""
            detail   = f"  \n> {log['detail']}" if log["detail"] else ""
            st.markdown(
                f"**{log['created_at'][:16]}** · {log['actor']}  \n"
                f"{icon} {item_ref}**{log['action']}**{detail}"
            )
            st.markdown("---")

        if st.button("🔄 Refresh"):
            st.rerun()
