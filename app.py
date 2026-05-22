import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date
import os
import json

# ─── Page config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="GS Document Tracker",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Base */
html, body, [class*="css"] { font-family: 'Segoe UI', sans-serif; }

/* Sidebar */
section[data-testid="stSidebar"] { background: #1a1f2e; }
section[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
section[data-testid="stSidebar"] .stTextInput input {
    background: #2d3748; border: 1px solid #4a5568; border-radius: 8px; color: #e2e8f0 !important;
}

/* Metric cards */
.metric-card {
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
    border: 1px solid #334155; border-radius: 12px;
    padding: 20px 24px; text-align: center; margin: 4px;
}
.metric-card .label { font-size: 12px; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px; }
.metric-card .value { font-size: 36px; font-weight: 700; margin: 4px 0; }
.metric-card .sub   { font-size: 12px; color: #64748b; }

/* Status badges */
.badge {
    display: inline-block; padding: 3px 10px; border-radius: 20px;
    font-size: 12px; font-weight: 600; letter-spacing: 0.3px;
}
.badge-pending   { background: #7c3aed22; color: #a78bfa; border: 1px solid #7c3aed44; }
.badge-progress  { background: #0ea5e922; color: #38bdf8; border: 1px solid #0ea5e944; }
.badge-done      { background: #10b98122; color: #34d399; border: 1px solid #10b98144; }
.badge-blocked   { background: #ef444422; color: #f87171; border: 1px solid #ef444444; }
.badge-verified  { background: #f59e0b22; color: #fbbf24; border: 1px solid #f59e0b44; }

/* Checklist card */
.doc-card {
    background: #1e293b; border: 1px solid #334155; border-radius: 12px;
    padding: 20px 24px; margin-bottom: 14px; position: relative;
    transition: border-color 0.2s;
}
.doc-card:hover { border-color: #475569; }
.doc-card .item-title { font-size: 16px; font-weight: 600; color: #f1f5f9; margin-bottom: 6px; }
.doc-card .item-reqs  { font-size: 13px; color: #94a3b8; white-space: pre-wrap; line-height: 1.6; }
.doc-card .item-meta  { font-size: 12px; color: #64748b; margin-top: 8px; }

/* Note bubble */
.note-bubble {
    background: #0f172a; border-left: 3px solid #3b82f6;
    border-radius: 0 8px 8px 0; padding: 10px 14px; margin: 6px 0;
}
.note-bubble .note-author { font-size: 11px; color: #60a5fa; font-weight: 600; }
.note-bubble .note-text   { font-size: 13px; color: #cbd5e1; margin-top: 2px; }
.note-bubble .note-time   { font-size: 11px; color: #475569; margin-top: 4px; }

/* Progress bar */
.progress-wrap { background: #1e293b; border-radius: 99px; height: 10px; overflow: hidden; margin: 8px 0; }
.progress-fill { height: 100%; border-radius: 99px;
    background: linear-gradient(90deg, #3b82f6, #10b981); transition: width 0.5s; }

/* Activity log */
.log-entry {
    padding: 10px 14px; border-left: 3px solid #334155;
    margin: 4px 0; background: #1e293b; border-radius: 0 8px 8px 0;
}
.log-entry .log-time { font-size: 11px; color: #475569; }
.log-entry .log-text { font-size: 13px; color: #94a3b8; }

/* Section headers */
.section-header {
    font-size: 22px; font-weight: 700; color: #f1f5f9;
    border-bottom: 2px solid #334155; padding-bottom: 10px; margin-bottom: 20px;
}
.sub-header { font-size: 14px; color: #64748b; margin-top: -14px; margin-bottom: 20px; }

/* Advisory box */
.advisory-box {
    background: #1a1a2e; border: 1px solid #f59e0b55;
    border-left: 4px solid #f59e0b; border-radius: 8px; padding: 16px 20px; margin: 16px 0;
}
.advisory-box .adv-title { font-size: 13px; font-weight: 700; color: #fbbf24; margin-bottom: 8px; }
.advisory-box .adv-text  { font-size: 13px; color: #cbd5e1; line-height: 1.7; }

/* Critical box */
.critical-box {
    background: #1a0a0a; border: 1px solid #ef444455;
    border-left: 4px solid #ef4444; border-radius: 8px; padding: 16px 20px; margin: 16px 0;
}
.critical-box .crit-title { font-size: 13px; font-weight: 700; color: #f87171; margin-bottom: 8px; }
.critical-box .crit-text  { font-size: 13px; color: #cbd5e1; line-height: 1.7; }
</style>
""", unsafe_allow_html=True)

# ─── Database ────────────────────────────────────────────────────────────────
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
        # Seed only if empty
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

# ─── DB helpers ─────────────────────────────────────────────────────────────
def get_docs():
    with conn() as c:
        rows = c.execute("SELECT DISTINCT doc_name FROM items ORDER BY doc_name").fetchall()
    return [r["doc_name"] for r in rows]

def get_items(doc_name=None, status_filter=None, assignee_filter=None):
    q = "SELECT * FROM items WHERE 1=1"
    params = []
    if doc_name:
        q += " AND doc_name=?"; params.append(doc_name)
    if status_filter and status_filter != "All":
        q += " AND status=?"; params.append(status_filter)
    if assignee_filter and assignee_filter != "All":
        q += " AND assigned_to LIKE ?"; params.append(f"%{assignee_filter}%")
    q += " ORDER BY id"
    with conn() as c:
        return c.execute(q, params).fetchall()

def get_notes(item_id):
    with conn() as c:
        return c.execute("SELECT * FROM notes WHERE item_id=? ORDER BY created_at DESC", (item_id,)).fetchall()

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

def verify_item(item_id, actor):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with conn() as c:
        row = c.execute("SELECT verified FROM items WHERE id=?", (item_id,)).fetchone()
        new_val = 0 if row["verified"] else 1
        c.execute("UPDATE items SET verified=?, verified_by=?, verified_at=?, updated_at=? WHERE id=?",
                  (new_val, actor if new_val else None, now if new_val else None, now, item_id))
        action = "VERIFIED" if new_val else "UNVERIFIED"
        c.execute("INSERT INTO activity_log (item_id, action, detail, actor) VALUES (?,?,?,?)",
                  (item_id, action, f"{'Marked verified' if new_val else 'Unverified'} by {actor}", actor))

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

# ─── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📋 GS Doc Tracker")
    st.markdown("---")
    user = st.text_input("👤 Your Name", value=st.session_state.get("user", ""), placeholder="Enter your name…")
    if user:
        st.session_state["user"] = user
    else:
        user = st.session_state.get("user", "Anonymous")

    st.markdown("---")
    docs = get_docs()
    selected_doc = st.selectbox("📁 Document", ["All"] + docs)
    st.markdown("---")

    STATUS_OPTIONS = ["Pending", "In Progress", "Done", "Blocked", "Verified"]
    status_filter = st.selectbox("🔍 Filter by Status", ["All"] + STATUS_OPTIONS)
    all_assignees = list(set(
        p.strip()
        for row in get_items()
        for p in (row["assigned_to"] or "").split("/")
        if p.strip()
    ))
    assignee_filter = st.selectbox("👥 Filter by Assignee", ["All"] + sorted(all_assignees))

    st.markdown("---")
    # Quick stats
    all_items = get_items(doc_name=selected_doc if selected_doc != "All" else None)
    total = len(all_items)
    done  = sum(1 for r in all_items if r["status"] == "Done")
    verif = sum(1 for r in all_items if r["verified"])
    pend  = sum(1 for r in all_items if r["status"] == "Pending")
    pct   = int(done / total * 100) if total else 0

    st.markdown(f"**Progress: {pct}%**")
    st.progress(pct / 100)
    st.markdown(f"✅ Done: **{done}** / {total}")
    st.markdown(f"🔍 Verified: **{verif}**")
    st.markdown(f"⏳ Pending: **{pend}**")
    st.markdown(f"👤 Logged in as: **{user}**")

# ─── Main ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div style='margin-bottom:4px'>
  <span style='font-size:28px;font-weight:800;color:#f1f5f9'>📋 GS Document Tracker</span>
</div>
<div style='color:#64748b;font-size:14px;margin-bottom:24px'>
  Visa Compliance — Edith Cowan University &nbsp;|&nbsp; Multi-user checklist & verification system
</div>
""", unsafe_allow_html=True)

# Advisory notices (shown on Dashboard)
ADVISORIES = [
    ("⚠️ CRITICAL: Property Sale Funds",
     "Funds from unexecuted property sales cannot be considered. If the property sale is pending past July 31, 2026, switch immediately to Path B with verified alternative liquid funds."),
    ("📌 CA Net Wealth Certificate",
     "Your mother's or sponsor's CA Net Wealth certificate must include the practicing CA's registration/membership number. Missing identifiers cause immediate rejection."),
    ("🔗 Cross-Reference Evidence",
     "Rental amounts in the father's lease/rental agreements must exactly match values declared in his FBR/Income Tax returns."),
]

tab1, tab2, tab3, tab4 = st.tabs(["🏠 Dashboard", "✅ Checklist", "➕ Add New", "📜 Activity Log"])

# ─── TAB 1: Dashboard ─────────────────────────────────────────────────────────
with tab1:
    items = get_items(doc_name=selected_doc if selected_doc != "All" else None)
    total = len(items)
    done_n    = sum(1 for r in items if r["status"] == "Done")
    inprog_n  = sum(1 for r in items if r["status"] == "In Progress")
    blocked_n = sum(1 for r in items if r["status"] == "Blocked")
    pend_n    = sum(1 for r in items if r["status"] == "Pending")
    verif_n   = sum(1 for r in items if r["verified"])
    pct_done  = int(done_n / total * 100) if total else 0
    pct_verif = int(verif_n / total * 100) if total else 0

    # Metric cards
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(f"""<div class="metric-card">
            <div class="label">Total Items</div>
            <div class="value" style="color:#f1f5f9">{total}</div>
            <div class="sub">across all docs</div></div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="metric-card">
            <div class="label">Completed</div>
            <div class="value" style="color:#34d399">{done_n}</div>
            <div class="sub">{pct_done}% done</div></div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class="metric-card">
            <div class="label">Verified</div>
            <div class="value" style="color:#fbbf24">{verif_n}</div>
            <div class="sub">{pct_verif}% verified</div></div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""<div class="metric-card">
            <div class="label">In Progress</div>
            <div class="value" style="color:#38bdf8">{inprog_n}</div>
            <div class="sub">being worked on</div></div>""", unsafe_allow_html=True)
    with c5:
        st.markdown(f"""<div class="metric-card">
            <div class="label">Blocked</div>
            <div class="value" style="color:#f87171">{blocked_n}</div>
            <div class="sub">needs attention</div></div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Progress bars
    col_prog, col_adv = st.columns([1, 1])
    with col_prog:
        st.markdown("#### 📊 Completion Progress")
        st.markdown(f"""
        <div style="margin:14px 0">
          <div style="display:flex;justify-content:space-between;font-size:13px;color:#94a3b8;margin-bottom:4px">
            <span>Done ({done_n}/{total})</span><span>{pct_done}%</span>
          </div>
          <div class="progress-wrap">
            <div class="progress-fill" style="width:{pct_done}%;background:linear-gradient(90deg,#3b82f6,#10b981)"></div>
          </div>
          <div style="display:flex;justify-content:space-between;font-size:13px;color:#94a3b8;margin-bottom:4px;margin-top:14px">
            <span>Verified ({verif_n}/{total})</span><span>{pct_verif}%</span>
          </div>
          <div class="progress-wrap">
            <div class="progress-fill" style="width:{pct_verif}%;background:linear-gradient(90deg,#f59e0b,#fbbf24)"></div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # Status breakdown table
        st.markdown("#### 📋 Status Breakdown")
        status_counts = {}
        for r in items:
            status_counts[r["status"]] = status_counts.get(r["status"], 0) + 1
        df = pd.DataFrame(list(status_counts.items()), columns=["Status", "Count"])
        if not df.empty:
            df["Percentage"] = (df["Count"] / total * 100).round(1).astype(str) + "%"
            st.dataframe(df, use_container_width=True, hide_index=True)

    with col_adv:
        st.markdown("#### ⚠️ Strategic Advisories")
        for title, text in ADVISORIES:
            st.markdown(f"""<div class="advisory-box">
                <div class="adv-title">{title}</div>
                <div class="adv-text">{text}</div>
            </div>""", unsafe_allow_html=True)

    # Summary table
    st.markdown("#### 📄 All Items Summary")
    BADGE = {
        "Pending":     "badge-pending",
        "In Progress": "badge-progress",
        "Done":        "badge-done",
        "Blocked":     "badge-blocked",
        "Verified":    "badge-verified",
    }
    if items:
        df2 = pd.DataFrame([{
            "ID": r["id"],
            "Document": r["doc_name"],
            "Category": r["category"].replace("\n", " "),
            "Assigned To": r["assigned_to"] or "—",
            "Status": r["status"],
            "Verified": "✅" if r["verified"] else "—",
            "Target Date": r["target_date"] or "Open",
        } for r in items])
        st.dataframe(df2, use_container_width=True, hide_index=True)

# ─── TAB 2: Checklist ─────────────────────────────────────────────────────────
with tab2:
    doc_filter = selected_doc if selected_doc != "All" else None
    items = get_items(doc_name=doc_filter, status_filter=status_filter, assignee_filter=assignee_filter)

    if not items:
        st.info("No items match your current filters.")
    else:
        for row in items:
            iid = row["id"]
            status = row["status"]
            verified = bool(row["verified"])

            BADGE_CLASS = {
                "Pending":     "badge-pending",
                "In Progress": "badge-progress",
                "Done":        "badge-done",
                "Blocked":     "badge-blocked",
                "Verified":    "badge-verified",
            }.get(status, "badge-pending")

            BORDER_COLOR = {
                "Pending":     "#7c3aed",
                "In Progress": "#0ea5e9",
                "Done":        "#10b981",
                "Blocked":     "#ef4444",
                "Verified":    "#f59e0b",
            }.get(status, "#334155")

            verif_badge = ' &nbsp;<span class="badge badge-verified">✓ VERIFIED</span>' if verified else ""

            st.markdown(f"""
            <div class="doc-card" style="border-left:4px solid {BORDER_COLOR}">
              <div style="display:flex;justify-content:space-between;align-items:flex-start">
                <div>
                  <span class="item-title">#{iid} — {row['category'].replace(chr(10), ' ')}</span>
                  <span class="badge {BADGE_CLASS}" style="margin-left:10px">{status}</span>
                  {verif_badge}
                </div>
                <div style="font-size:12px;color:#475569">{row['doc_name']}</div>
              </div>
              <div class="item-reqs" style="margin-top:10px">{row['requirements'] or '—'}</div>
              <div class="item-meta">
                👤 {row['assigned_to'] or '—'} &nbsp;|&nbsp;
                📅 {row['target_date'] or 'Open'} &nbsp;|&nbsp;
                🕐 Updated: {row['updated_at'][:16]}
                {f"&nbsp;|&nbsp; ✅ Verified by <b>{row['verified_by']}</b> on {row['verified_at'][:16]}" if verified and row['verified_by'] else ""}
              </div>
            </div>
            """, unsafe_allow_html=True)

            # Expand/collapse via session state
            key_exp = f"expand_{iid}"
            if key_exp not in st.session_state:
                st.session_state[key_exp] = False

            col_btn1, col_btn2, col_btn3, col_btn4 = st.columns([1, 1, 1, 1])
            with col_btn1:
                if st.button("✏️ Edit", key=f"edit_{iid}", use_container_width=True):
                    st.session_state[key_exp] = not st.session_state[key_exp]
            with col_btn2:
                v_label = "🔒 Unverify" if verified else "✅ Verify"
                if st.button(v_label, key=f"verify_{iid}", use_container_width=True):
                    if not user or user == "Anonymous":
                        st.warning("Please enter your name in the sidebar first.")
                    else:
                        verify_item(iid, user)
                        st.rerun()
            with col_btn3:
                if st.button("📝 Notes", key=f"notes_{iid}", use_container_width=True):
                    st.session_state[f"notes_open_{iid}"] = not st.session_state.get(f"notes_open_{iid}", False)
            with col_btn4:
                if st.button("🗑️ Delete", key=f"del_{iid}", use_container_width=True):
                    st.session_state[f"confirm_del_{iid}"] = True

            # Confirm delete
            if st.session_state.get(f"confirm_del_{iid}"):
                st.warning(f"Delete item #{iid} — **{row['category'][:40]}**? This cannot be undone.")
                cc1, cc2 = st.columns(2)
                with cc1:
                    if st.button("Yes, delete", key=f"yes_del_{iid}", type="primary"):
                        delete_item(iid, user)
                        st.session_state.pop(f"confirm_del_{iid}", None)
                        st.rerun()
                with cc2:
                    if st.button("Cancel", key=f"cancel_del_{iid}"):
                        st.session_state.pop(f"confirm_del_{iid}", None)
                        st.rerun()

            # Edit panel
            if st.session_state.get(key_exp):
                with st.container():
                    st.markdown("**Edit Item**")
                    e1, e2, e3, e4 = st.columns([2, 1, 1, 1])
                    with e1:
                        new_cat = st.text_input("Category", value=row["category"], key=f"cat_{iid}")
                    with e2:
                        new_status = st.selectbox("Status", STATUS_OPTIONS,
                                                   index=STATUS_OPTIONS.index(status) if status in STATUS_OPTIONS else 0,
                                                   key=f"st_{iid}")
                    with e3:
                        new_assign = st.text_input("Assigned To", value=row["assigned_to"] or "", key=f"asgn_{iid}")
                    with e4:
                        cur_date = None
                        if row["target_date"]:
                            try: cur_date = date.fromisoformat(row["target_date"])
                            except: pass
                        new_date = st.date_input("Target Date", value=cur_date, key=f"dt_{iid}")
                    new_reqs = st.text_area("Requirements", value=row["requirements"] or "", key=f"req_{iid}", height=100)
                    if st.button("💾 Save Changes", key=f"save_{iid}", type="primary"):
                        if not user or user == "Anonymous":
                            st.warning("Please enter your name first.")
                        else:
                            if new_cat != row["category"]:       update_item(iid, "category", new_cat, user)
                            if new_status != status:              update_item(iid, "status", new_status, user)
                            if new_assign != (row["assigned_to"] or ""): update_item(iid, "assigned_to", new_assign, user)
                            if new_reqs != (row["requirements"] or ""):  update_item(iid, "requirements", new_reqs, user)
                            nd_str = new_date.isoformat() if new_date else None
                            if nd_str != row["target_date"]:     update_item(iid, "target_date", nd_str, user)
                            st.session_state[key_exp] = False
                            st.success("Saved!")
                            st.rerun()

            # Notes panel
            if st.session_state.get(f"notes_open_{iid}", False):
                st.markdown(f"**Notes for item #{iid}**")
                existing_notes = get_notes(iid)
                if existing_notes:
                    for n in existing_notes:
                        st.markdown(f"""<div class="note-bubble">
                            <div class="note-author">💬 {n['author']}</div>
                            <div class="note-text">{n['note']}</div>
                            <div class="note-time">{n['created_at']}</div>
                        </div>""", unsafe_allow_html=True)
                else:
                    st.caption("No notes yet.")
                with st.form(key=f"note_form_{iid}", clear_on_submit=True):
                    new_note = st.text_area("Add a note…", key=f"note_text_{iid}", height=80)
                    submitted = st.form_submit_button("Post Note")
                    if submitted:
                        if not user or user == "Anonymous":
                            st.warning("Enter your name in the sidebar first.")
                        elif not new_note.strip():
                            st.warning("Note cannot be empty.")
                        else:
                            add_note(iid, new_note.strip(), user)
                            st.success("Note added!")
                            st.rerun()

            st.markdown("<hr style='border:none;border-top:1px solid #1e293b;margin:4px 0'>", unsafe_allow_html=True)

# ─── TAB 3: Add New ───────────────────────────────────────────────────────────
with tab3:
    st.markdown("### ➕ Add New Item")
    st.markdown('<div class="sub-header">Add a new document requirement to any checklist, or create a brand-new checklist.</div>', unsafe_allow_html=True)

    with st.form("add_item_form", clear_on_submit=True):
        a1, a2 = st.columns([2, 1])
        with a1:
            existing_docs = get_docs()
            doc_choice = st.radio("Checklist", ["Existing", "New"], horizontal=True)
            if doc_choice == "Existing":
                new_doc_name = st.selectbox("Select Checklist", existing_docs if existing_docs else ["GS Checklist"])
            else:
                new_doc_name = st.text_input("New Checklist Name", placeholder="e.g. Murdoch University Docs")
        with a2:
            new_status_add = st.selectbox("Initial Status", STATUS_OPTIONS)
            new_assign_add = st.text_input("Assigned To", placeholder="e.g. Father, Applicant")
            new_date_add   = st.date_input("Target Date", value=None)

        new_category = st.text_input("Category / Task Title *", placeholder="e.g. Bank Statement - 6 months")
        new_reqs_add = st.text_area("Requirements / Details",
                                     placeholder="• List specific document requirements\n• File format\n• Who to get it from",
                                     height=120)

        submitted = st.form_submit_button("➕ Add Item", type="primary", use_container_width=True)
        if submitted:
            if not user or user == "Anonymous":
                st.warning("Please enter your name in the sidebar first.")
            elif not new_category.strip():
                st.warning("Category / Task Title is required.")
            elif not new_doc_name or not new_doc_name.strip():
                st.warning("Checklist name is required.")
            else:
                add_item(
                    doc_name=new_doc_name.strip(),
                    category=new_category.strip(),
                    requirements=new_reqs_add.strip(),
                    assigned_to=new_assign_add.strip(),
                    status=new_status_add,
                    target_date=new_date_add.isoformat() if new_date_add else None,
                    actor=user,
                )
                st.success(f"✅ Item added to **{new_doc_name}**!")
                st.rerun()

    st.markdown("---")
    st.markdown("### 📂 Manage Checklists")
    st.markdown("Current checklists in the database:")
    for d in get_docs():
        items_in_doc = get_items(doc_name=d)
        done_in_doc  = sum(1 for r in items_in_doc if r["status"] == "Done")
        st.markdown(f"- **{d}** — {len(items_in_doc)} items, {done_in_doc} done")

# ─── TAB 4: Activity Log ──────────────────────────────────────────────────────
with tab4:
    st.markdown("### 📜 Activity Log")
    st.markdown('<div class="sub-header">Full audit trail of all changes, notes, and verifications.</div>', unsafe_allow_html=True)

    logs = get_logs(200)
    if not logs:
        st.info("No activity yet.")
    else:
        ACTION_ICONS = {
            "INIT":        "🌱",
            "ADD ITEM":    "➕",
            "DELETE":      "🗑️",
            "UPDATE STATUS":   "🔄",
            "UPDATE CATEGORY": "✏️",
            "UPDATE ASSIGNED_TO": "👤",
            "UPDATE TARGET_DATE": "📅",
            "UPDATE REQUIREMENTS": "📋",
            "NOTE":        "💬",
            "VERIFIED":    "✅",
            "UNVERIFIED":  "🔒",
        }
        for log in logs:
            icon = ACTION_ICONS.get(log["action"], "📌")
            item_ref = f"[Item #{log['item_id']}] " if log["item_id"] else ""
            st.markdown(f"""<div class="log-entry">
                <div class="log-time">{log['created_at']} &nbsp;·&nbsp; <b>{log['actor']}</b></div>
                <div class="log-text">{icon} {item_ref}<b>{log['action']}</b>
                  {f"— {log['detail']}" if log['detail'] else ""}</div>
            </div>""", unsafe_allow_html=True)

        if st.button("🔄 Refresh Log"):
            st.rerun()
