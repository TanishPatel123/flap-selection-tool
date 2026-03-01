# app.py  –  Head-&-Neck Local-Flap Selector (research prototype)
# Author: Tanish Patel
# -----------------------------------------------------------------
from pathlib import Path
from datetime import datetime, date
import pandas as pd
import streamlit as st
   
# ──────────────────────────────────────────────────────────────
# 1. CONSTANTS & HELPERS
# ──────────────────────────────────────────────────────────────
DATA_PATH = Path(".data/usage_log.csv")      # hidden dot-folder
DATA_PATH.parent.mkdir(exist_ok=True, parents=True)

st.set_page_config("Flap-Selector (Research)", "🩺", layout="wide")  
SUBUNITS = [
    "Scalp", "Forehead – central", "Forehead – lateral", "Temple",
    "Zygomatic-arch (temporal-malar)", "Nasal tip", "Nasal dorsum",
    "Nasal ala / side-wall", "Upper eyelid", "Lower eyelid",
    "Medial canthus", "Lateral canthus", "Upper lip – central",
    "Upper lip – lateral", "Lower lip – central", "Lower lip – lateral",
    "Oral commissure", "Cheek – infra-orbital", "Cheek – buccal",
    "Chin – mentum", "Ear – helical rim", "Ear – conchal bowl",
    "Ear – lobule", "Peri-auricular skin",
]

DEPTH_OPTS = [
    "Superficial (skin only)",
    "Partial thickness (subcut / perichondrium)",
    "Full thickness (cartilage / bone exposed)",
]

THR = {
    "Scalp": (2, 6), "Forehead – central": (1.5, 5), "Forehead – lateral": (1.5, 4),
    "Temple": (1.5, 4), "Zygomatic-arch (temporal-malar)": (2, 4),
    "Nasal tip": (0.5, 1.5), "Nasal dorsum": (1, 1.5), "Nasal ala / side-wall": (1, 1.5),
    "Upper eyelid": (1, 1.5), "Lower eyelid": (1, 1.5),
    "Medial canthus": (1, 1.5), "Lateral canthus": (1, 1.5),
    "Upper lip – central": (0.8, 1.6), "Upper lip – lateral": (0.8, 1.6),
    "Lower lip – central": (1, 2), "Lower lip – lateral": (1, 2),
    "Oral commissure": (1, 1.5),
    "Cheek – infra-orbital": (1.5, 3), "Cheek – buccal": (2, 4), "Chin – mentum": (1.5, 3),
    "Ear – helical rim": (1, 1.5), "Ear – conchal bowl": (1.5, 2.5),
    "Ear – lobule": (1, 1.5), "Peri-auricular skin": (2, 4),
}

def _cat(loc: str, cm: float) -> str:
    lo, mid = THR[loc]
    return "small" if cm <= lo else "medium" if cm <= mid else "large"

pick = lambda size, m: m[size]

# ──────────────────────────────────────────────────────────────
# 2.  DECISION ENGINE  (full logic preserved)
# ──────────────────────────────────────────────────────────────
def decide(loc, kind, cm, depth, hair, age, dia, smk, rad):
    # FIX: use _cat(), not cat()
    size = _cat(loc, cm)
    flap = rationale = ""

    # ————————————————— SCALP —————————————————
    if loc == "Scalp":
        if depth.startswith("Full"):
            if size=="large":
                flap="Latissimus-dorsi free flap + STSG"
                rationale="Massive bare skull requires vascular muscle then graft."
            else:
                flap="Ortícochea four-flap rotation"
                rationale="≤6 cm full-depth closed with opposing galeal rotations."
        else:
            if size=="small":
                flap="Linear primary closure ± galeal scoring"
                rationale="≤2 cm superficial scalp closed after undermining."
            elif size=="medium":
                flap="O-Z rotation flap"
                rationale="2-6 cm superficial scalp defects via semicircular rotation."
            else:
                flap="Ortícochea four-flap rotation"
                rationale=">6 cm superficial needs four opposing rotations."
        if hair and "graft" in flap.lower():
            rationale+=" Flap preserves hair-bearing skin; graft would alopecise."

    # ————————————————— FOREHEAD CENTRAL / LATERAL / TEMPLE / ZYGOMA —————————————————
    elif loc == "Forehead – central":
        if depth.startswith("Full"):
            flap="Temporalis fascia turnover + frontal skin rotation"
            rationale="Fascia vascularises bone, rotated skin closes."
        else:
            flap = pick(size,{
                "small":"Direct closure in horizontal rhytid",
                "medium":"H-plasty bilateral advancement",
                "large":"Parietal-forehead rotation flap"})
            rationale = pick(size,{
                "small":"Short scar hidden in forehead line.",
                "medium":"Advances both sides (1.5-5 cm).",
                "large":"Large defect recruits parietal scalp."})
    elif loc == "Forehead – lateral":
        if depth.startswith("Full"):
            flap="Temporoparietal fascia flap + STSG"
            rationale="TP fascia on bone then skin graft."
        else:
            flap = pick(size,{
                "small":"Mini A-T advancement flap",
                "medium":"Temporal-scalp rotation flap",
                "large":"Extended cervicofacial rotation"})
            rationale = pick(size,{
                "small":"Triangle-to-T hides scar at hairline.",
                "medium":"Rotated hair-bearing scalp covers 1.5-4 cm.",
                "large":">4 cm needs cheek/neck recruitment."})
    elif loc == "Temple":
        if depth.startswith("Full"):
            flap="Temporalis-fascia flap + STSG"
            rationale="Vascular fascia over bone/joint."
        else:
            flap = pick(size,{
                "small":"Limberg rhomboid flap",
                "medium":"Mustardé cheek rotation flap",
                "large":"Cervicofacial rotation flap"})
            rationale = pick(size,{
                "small":"Rhomboid in crow’s-feet lines ≤1.5 cm.",
                "medium":"2-4 cm uses Mustardé upward rotation.",
                "large":">4 cm full cervicofacial."})
    elif loc == "Zygomatic-arch (temporal-malar)":
        if depth.startswith("Full"):
            flap="Mustardé cheek rotation flap"
            rationale="Robust cheek rotation covers arch."
        else:
            flap = pick(size,{
                "small":"Rhomboid transposition flap",
                "medium":"Mustardé cheek rotation flap",
                "large":"Cervicofacial rotation flap"})
            rationale = pick(size,{
                "small":"≤2 cm rhomboid along RSTL.",
                "medium":"2-4 cm rotated cheek skin.",
                "large":">4 cm needs full cervicofacial flap."})

    # ————————————————— NOSE —————————————————
    elif loc == "Nasal tip":
        if depth.startswith("Full"):
            flap="Paramedian forehead flap + septal cartilage graft"
            rationale="2-stage skin + support for full-depth tip."
        else:
            flap = pick(size,{
                "small":"Secondary intention / tiny FTSG",
                "medium":"Bilobed flap",
                "large":"Paramedian forehead flap"})
            rationale = pick(size,{
                "small":"<5 mm granulates or small graft.",
                "medium":"Bilobed uses upper-dorsum skin.",
                "large":">1.5 cm exceeds nasal reserve."})
    elif loc == "Nasal dorsum":
        if depth.startswith("Full"):
            flap="Paramedian forehead flap"
            rationale="Full-depth dorsal defect needs forehead skin & lining."
        else:
            flap = pick(size,{
                "small":"Rieger dorsal-nasal flap",
                "medium":"Glabellar rotation flap",
                "large":"Paramedian forehead flap"})
            rationale = pick(size,{
                "small":"≤1 cm short transposition.",
                "medium":"1-1.5 cm glabellar rotation.",
                "large":">1.5 cm forehead flap."})
    elif loc == "Nasal ala / side-wall":
        if depth.startswith("Full"):
            flap="Nasolabial interpolation flap + conchal cartilage"
            rationale="Staged cheek skin + cartilage maintain airway."
        else:
            flap = pick(size,{
                "small":"Inferior bilobed flap",
                "medium":"Nasolabial interpolation flap",
                "large":"Paramedian forehead flap"})
            rationale = pick(size,{
                "small":"<1 cm ala gap bilobed.",
                "medium":"1-1.5 cm staged nasolabial.",
                "large":">1.5 cm requires forehead flap."})

    # ————————————————— EYELIDS / CANTHI —————————————————
    elif loc == "Upper eyelid":
        if depth.startswith("Full"):
            flap = "Cutler-Beard bridge flap" if size=="large" else "Tenzel semicircular flap"
            rationale = ("Full-thickness >50 % upper-lid via 2-stage Cutler-Beard."
                         if size=="large"
                         else "25-50 % full-thickness closed by Tenzel lateral rotation.")
        else:
            flap = pick(size,{
                "small":"Direct closure in lid crease",
                "medium":"Blepharoplasty skin-advancement",
                "large":"Tenzel semicircular flap"})
            rationale = pick(size,{
                "small":"<1 cm skin closed in natural crease.",
                "medium":"1-1.5 cm advanced redundant lid skin.",
                "large":">1.5 cm superficial uses Tenzel flap."})
    elif loc == "Lower eyelid":
        if depth.startswith("Full"):
            flap = "Hughes tarsoconjunctival flap + STSG" if size=="large" else "Tenzel semicircular flap"
            rationale = (">50 % full-thickness lower-lid with Hughes posterior lamella + skin graft."
                         if size=="large"
                         else "25-50 % full-thickness uses Tenzel semicircular.")
        else:
            flap = pick(size,{
                "small":"Direct closure",
                "medium":"Full-thickness skin graft",
                "large":"Tenzel semicircular flap"})
            rationale = pick(size,{
                "small":"≤1 cm linear closure.",
                "medium":"1-1.5 cm graft from post-auricular.",
                "large":">1.5 cm superficial uses Tenzel."})
    elif loc == "Medial canthus":
        if depth.startswith("Full") or size=="large":
            flap="Paramedian (glabellar) forehead interpolation flap"
            rationale="Deep/large medial canthus needs staged glabellar skin."
        else:
            flap = "Full-thickness skin graft" if size=="small" else "Glabellar V-Y (Rintala) flap"
            rationale = ("<1 cm grafted with thin skin."
                         if size=="small"
                         else "1-1.5 cm V-Y glabellar transposition.")
    elif loc == "Lateral canthus":
        flap = pick(size,{
            "small":"Direct primary closure",
            "medium":"Tenzel semicircular flap",
            "large":"Mustardé cheek rotation flap"})
        rationale = pick(size,{
            "small":"≤1 cm closed after cantholysis.",
            "medium":"25-50 % lateral defect uses Tenzel.",
            "large":">1.5 cm needs Mustardé cheek rotation."})

    # ————————————————— LIPS / COMMISSURE —————————————————
    elif loc.startswith("Upper lip"):
        zone="central" in loc
        if depth.startswith("Superficial") and size=="small":
            flap="V-Y vermilion advancement"
            rationale="Tiny vermilion excision advanced mucosa."
        else:
            if zone:
                flap = pick(size,{
                    "small":"Full-thickness wedge closure",
                    "medium":"Abbé cross-lip flap",
                    "large":"Karapandzic bilateral rotation"})
                rationale = pick(size,{
                    "small":"≤0.8 cm (<30 %) wedge.",
                    "medium":"30-60 % central: staged Abbé cross-lip.",
                    "large":">60 %: bilateral Karapandzic."})
            else:
                flap = pick(size,{
                    "small":"Full-thickness wedge closure",
                    "medium":"Estlander flap",
                    "large":"Bernard-Burow advancement"})
                rationale = pick(size,{
                    "small":"<30 % lateral wedge.",
                    "medium":"30-50 % lateral/commissure Estlander.",
                    "large":">50 % cheek advancement."})
    elif loc.startswith("Lower lip"):
        zone="central" in loc
        if zone:
            flap = pick(size,{
                "small":"Full-thickness wedge closure",
                "medium":"Karapandzic rotation flap",
                "large":"Bernard-Webster bilateral advancement"})
            rationale = pick(size,{
                "small":"<30 % wedge.",
                "medium":"30-60 % central Karapandzic.",
                "large":">60 % Bernard-Webster."})
        else:
            flap = pick(size,{
                "small":"Full-thickness wedge closure",
                "medium":"Estlander flap",
                "large":"Extended Karapandzic / Burow"})
            rationale = pick(size,{
                "small":"<30 % lateral wedge.",
                "medium":"30-50 % Estlander.",
                "large":">50 % extended circumoral rotation."})
    elif loc == "Oral commissure":
        if depth.startswith("Full") or size=="large":
            flap="Free radial-forearm commissuroplasty flap"
            rationale="Near-total commissure reconstructed microsurgically."
        else:
            flap = "Commissuroplasty triangular flap" if size=="small" else "Estlander cross-lip flap"
            rationale = ("<1 cm triangular mucocutaneous realignment."
                         if size=="small"
                         else "1-1.5 cm lateral loss Estlander flap.")

    # ————————————————— CHEEK / CHIN —————————————————
    elif loc == "Cheek – infra-orbital":
        flap = pick(size,{
            "small":"Malar V-Y advancement",
            "medium":"Mustardé cheek rotation",
            "large":"Cervicofacial rotation"})
        rationale = pick(size,{
            "small":"≤1.5 cm V-Y under eyelid.",
            "medium":"1.5-3 cm Mustardé malar rotation.",
            "large":">3 cm cervicofacial flap."})
    elif loc == "Cheek – buccal":
        if depth.startswith("Full"):
            flap="Cervicofacial rotation flap"
            rationale="Deep buccal loss best with large rotation."
        else:
            flap = pick(size,{
                "small":"Limberg rhomboid flap",
                "medium":"V-Y cheek advancement",
                "large":"Cervicofacial rotation"})
            rationale = pick(size,{
                "small":"≤2 cm rhomboid along smile lines.",
                "medium":"2-4 cm V-Y advancement.",
                "large":">4 cm cervicofacial flap."})
    elif loc == "Chin – mentum":
        if depth.startswith("Full"):
            flap="Submental island flap"
            rationale="Full-thickness chin needs pedicled submental."
        else:
            flap = pick(size,{
                "small":"H-plasty bilateral advancement",
                "medium":"Submental advancement flap",
                "large":"Extended cervicofacial rotation"})
            rationale = pick(size,{
                "small":"≤1.5 cm bilateral advancement under chin.",
                "medium":"1.5-3 cm submental laxity advanced.",
                "large":">3 cm cheek-neck rotation."})

    # ————————————————— EAR / PERI-AURICULAR —————————————————
    elif loc == "Ear – helical rim":
        flap = pick(size,{
            "small":"V-wedge chondro-cutaneous closure",
            "medium":"Antia-Buch advancement flap",
            "large":"Posterior-auricular tubed flap"})
        rationale = pick(size,{
            "small":"Short segment closed wedge.",
            "medium":"1-1.5 cm rim advanced.",
            "large":">1.5 cm staged tubed flap."})
        if depth.startswith("Full") and size!="small":
            rationale += "  Conchal cartilage graft supports rim."
    elif loc == "Ear – conchal bowl":
        flap = pick(size,{
            "small":"Post-auricular full-thickness skin graft",
            "medium":"Revolving-door island flap",
            "large":"Two-stage posterior-auricular flap"})
        rationale = pick(size,{
            "small":"Thin FTSG matches concavity.",
            "medium":"Island flap swings into bowl.",
            "large":">2.5 cm requires staged flap."})
    elif loc == "Ear – lobule":
        flap = pick(size,{
            "small":"Direct wedge closure",
            "medium":"Gavello V-Y advancement",
            "large":"Bilobed lobule rotation + composite graft"})
        rationale = pick(size,{
            "small":"Tiny gap approximated.",
            "medium":"V-Y slides inferior lobule.",
            "large":">1.5 cm rotation + graft restore bulk."})
    elif loc == "Peri-auricular skin":
        flap = pick(size,{
            "small":"Direct sulcus closure",
            "medium":"Retro-auricular rotation flap",
            "large":"Cervicofacial rotation flap"})
        rationale = pick(size,{
            "small":"≤2 cm scar hides behind ear.",
            "medium":"2-4 cm mastoid rotation.",
            "large":">4 cm extended cervicofacial."})
        if depth.startswith("Full"):
            rationale += "  Parotid fascia exposed – SMAS turned in."

    # ————————————————— NOTES / RISK FLAGS —————————————————
    notes = []
    if smk: notes.append("Smoking jeopardises flap – cessation essential.")
    if dia: notes.append("Optimise glycaemia pre-op.")
    if rad: notes.append("Radiated skin – consider delay/wider pedicle.")
    if hair and "graft" in flap.lower():
        notes.append("A graft on hair-bearing skin causes alopecia; flap chosen.")
    if age < 18:
        notes.append("Paediatric skin tight – staged expansion may help.")
    elif age > 70:
        notes.append("Elderly laxity aids rotation; rhytids hide scars.")
    if kind == "Oncologic":
        notes.append("Confirm clear margins before reconstruction.")
    elif kind == "Traumatic":
        notes.append("Debride & align with laceration lines.")
    elif kind == "Congenital":
        notes.append("Consider staged expansion for symmetry.")

    return (
        f"**Recommended flap:** {flap}\n\n"
        f"**Rationale:** {rationale}\n\n"
        f"**Notes:** {' '.join(notes) if notes else 'None.'}"
    )

# ───────────────────────────────────────────────────────────────
# 1️⃣  CONSTANTS & UTILITY
# ───────────────────────────────────────────────────────────────
DATA_PATH = Path(".data/usage_log.csv")
DATA_PATH.parent.mkdir(exist_ok=True, parents=True)   # hidden folder

SUBUNITS = [
    "Scalp", "Forehead – central", "Forehead – lateral", "Temple",
    "Zygomatic-arch (temporal-malar)", "Nasal tip", "Nasal dorsum",
    "Nasal ala / side-wall", "Upper eyelid", "Lower eyelid",
    "Medial canthus", "Lateral canthus", "Upper lip – central",
    "Upper lip – lateral", "Lower lip – central", "Lower lip – lateral",
    "Oral commissure", "Cheek – infra-orbital", "Cheek – buccal",
    "Chin – mentum", "Ear – helical rim", "Ear – conchal bowl",
    "Ear – lobule", "Peri-auricular skin",
]

DEPTH_OPTS = [
    "Superficial (skin only)",
    "Partial thickness (subcut / perichondrium)",
    "Full thickness (cartilage / bone exposed)",
]

def log_row(row: dict) -> None:
    """Append one anonymised row to .data/usage_log.csv."""
    first = not DATA_PATH.exists()
    pd.DataFrame([row]).to_csv(DATA_PATH, mode="a", header=first, index=False)

# ───────────────────────────────────────────────────────────────
# 2️⃣  STREAMLIT PAGE CONFIG & SIDEBAR
# ───────────────────────────────────────────────────────────────
st.set_page_config("Flap-Selector (Research)", "🩺", layout="wide")

with st.sidebar:
    st.header("Flap Selection Tool")
    st.markdown(
        "**Prototype** tool for determining optimal local flap for excision closure.\n\n"
        "No personal identifiers are saved.\n"
        "Only anonymous input parameters & your feedback are stored "
        "in a private file visible *only* to the Research team.\n\n"
        "Made by referencing Baker — 3rd edition, Neligan Volume 1 & 3 — 5th edition.\n" 
    )
    if DATA_PATH.exists():
        st.caption(f"Logged cases: {len(pd.read_csv(DATA_PATH))}")
    st.caption(f"Build: {date.today()}")
# -- INSIDE the "with st.sidebar:" block --
if DATA_PATH.exists():
    # OPTIONAL one-line password gate ─ remove if not needed
    pw_ok = st.text_input("Admin password", type="password") == st.secrets["ADMIN_PASS"]

    if pw_ok:
        st.download_button(
            "⬇️  Download usage CSV",
            data=DATA_PATH.read_bytes(),
            file_name="usage_log.csv",
            mime="text/csv",
        )

# ───────────────────────────────────────────────────────────────
# 3️⃣  SESSION-STATE INITIALISATION
# ───────────────────────────────────────────────────────────────
for key, default in {
    "case_submitted": False,
    "feedback_done":  False,
    "case_row":       {},
    "recommendation": "",
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ───────────────────────────────────────────────────────────────
# 1️⃣  CASE-ENTRY FORM  (shows until first submit)
# ───────────────────────────────────────────────────────────────
if not st.session_state.case_submitted:
    with st.form("case_form"):
        c1, c2 = st.columns(2)
        loc   = c1.selectbox("Anatomical sub-unit", SUBUNITS)
        kind  = c2.selectbox("Defect type",
                             ["Oncologic", "Traumatic", "Congenital"])
        depth = c1.radio("Depth of defect", DEPTH_OPTS)
        cm    = c2.number_input("Largest diameter (cm)",
                                min_value=0.1, max_value=25.0,
                                value=1.0, step=0.1)
        age   = c1.number_input("Patient age (years)",
                                min_value=0, max_value=120,
                                value=60, step=1)
        hair  = c2.checkbox("Hair-bearing skin?", True)

        st.markdown("##### Risk factors")
        dia = st.checkbox("Diabetes")
        smk = st.checkbox("Active smoker")
        rad = st.checkbox("Previously irradiated site")

        submitted = st.form_submit_button("Recommend flap")

    if submitted:
        # compute recommendation and stash everything
        st.session_state.case_row = {
            "timestamp_utc": datetime.utcnow().isoformat(timespec="seconds"),
            "loc": loc, "kind": kind, "depth": depth.split()[0],
            "cm": cm, "hair": hair, "age": age,
            "dia": dia, "smk": smk, "rad": rad,
        }
        st.session_state.recommendation = decide(
            loc, kind, cm, depth, hair, age, dia, smk, rad
        )
        st.session_state.case_submitted = True

# ───────────────────────────────────────────────────────────────
# 2️⃣  SHOW RECOMMENDATION & FEEDBACK  (single page)
# ───────────────────────────────────────────────────────────────
# ───────── STAGE 2 – recommendation + feedback (single page) ─────────
if st.session_state.case_submitted and not st.session_state.feedback_done:
    st.markdown(st.session_state.recommendation)

    # 1️⃣  Feedback form
    with st.form("feedback_form"):
        used_choice = st.radio(
            "Did you use the recommended flap?",
            ["Yes", "No"],
            key="used_recommended",
            horizontal=True,
        )

        # Textbox is always enabled now
        alt_flap_val = st.text_input(
            "If you used a different flap, which one?",
            key="alt_flap_text",
            placeholder="Type alternative flap here…"
        )

 send = st.form_submit_button("Submit feedback")

    # 2️⃣  On submit, validate and write to CSV
    if send:
        # Require textbox entry if user chose “No”
        if used_choice == "No" and not alt_flap_val.strip():
            st.warning("Please tell us which flap you used.")
            st.stop()

        import re, csv

        # Extract recommended flap from markdown
        m = re.search(r"\*\*Recommended flap:\*\*\s*(.+)", st.session_state.recommendation)
        rec_flap = m.group(1).strip() if m else "(parse failed)"

        # Build row
        row = st.session_state.case_row.copy()
        row.update({
            "recommended_flap":  rec_flap,
            "used_recommended":  (used_choice == "Yes"),
            "alt_flap_if_no":    alt_flap_val.strip(),
        })

        # Append to CSV
        first_write = not DATA_PATH.exists()
        with DATA_PATH.open("a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=row.keys(), quoting=csv.QUOTE_MINIMAL)
            if first_write:
                writer.writeheader()
            writer.writerow(row)

        st.success("Thank you — entry logged.")
        st.session_state.feedback_done = True
    
        # Clear per-case widget state
        for k in ("used_recommended", "alt_flap_text"):
            st.session_state.pop(k, None)


# ───────────────────────────────────────────────────────────────
# 3️⃣  RESET BUTTON AFTER FEEDBACK
# ───────────────────────────────────────────────────────────────
if st.session_state.get("feedback_done"):
    if st.button("Start new case"):
        # Clear the per-case state
        st.session_state["case_submitted"]  = False
        st.session_state["feedback_done"]   = False
        st.session_state["recommendation"]  = ""
        st.session_state["case_row"]        = {}

        # Remove optional widget values if they exist
        for k in ("used_recommended", "alt_flap_text"):
            st.session_state.pop(k, None)

        # Immediately show a fresh form (Streamlit ≥ 1.27)
        try:
            st.rerun()
        except AttributeError:          # fallback for very old versions
            st.experimental_rerun()


# ───────────────────────────────────────────────────────────────
# FOOTER
# ───────────────────────────────────────────────────────────────
st.markdown("---")
st.caption("Research prototype — use best clinical judgement.")
