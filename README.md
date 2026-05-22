# 📋 GS Document Tracker

A multi-user Streamlit app for tracking visa document requirements for **Edith Cowan University** (and any other institution). Supports real-time status updates, verification, per-item notes, audit logging, and adding new checklists.

## Features

- **Multi-user** — each user enters their name; all actions are attributed
- **Persistent state** — SQLite database, survives restarts
- **Status tracking** — Pending / In Progress / Done / Blocked / Verified
- **Verification** — separate from completion; records who verified and when
- **Notes** — threaded notes per item with author + timestamp
- **Activity log** — full audit trail of every change
- **Add new items** — add to existing checklists or create brand-new ones
- **Dashboard** — metrics, progress bars, advisory notices
- **Filters** — filter checklist by status and assignee

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

The SQLite database (`gs_tracker.db`) is created automatically on first run and pre-loaded with the GS checklist items.

## Deploy on Streamlit Cloud

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repo and deploy `app.py`

> Note: Streamlit Cloud has an ephemeral filesystem — the database resets on each restart. For persistent cloud storage, swap the SQLite backend for a hosted database (e.g. Supabase, PlanetScale).
