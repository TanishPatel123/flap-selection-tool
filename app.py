# app.py – Head-&-Neck Local-Flap Selector (research prototype)
# Author: Tanish Patel
# Updated: Added Neck subunits, lateral cheek, pathology-sensitive logic, and margin-guidance notes
# -----------------------------------------------------------------
from pathlib import Path
from datetime import datetime, date
import csv
import re

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
    "Oral commissure", "Cheek – infra-orbital", "Cheek – medial",
    "Cheek – lateral", "Chin – mentum", "Neck – anterior", "Neck – posterior",
    "Ear – helical rim", "Ear – conchal bowl", "Ear – lobule",
    "Peri-auricular skin",
]

DEPTH_OPTS = [
    "Superficial (skin only)",
    "Partial thickness (subcut / perichondrium)",
    "Full thickness (cartilage / bone exposed)",
]

THR = {
    "Scalp": (2, 6),
    "Forehead – central": (1.5, 5),
    "Forehead – lateral": (1.5, 4),
    "Temple": (1.5, 4),
    "Zygomatic-arch (temporal-malar)": (2, 4),
    "Nasal tip": (0.5, 1.5),
    "Nasal dorsum": (1, 1.5),
    "Nasal ala / side-wall": (1, 1.5),
    "Upper eyelid": (1, 1.5),
    "Lower eyelid": (1, 1.5),
    "Medial canthus": (1, 1.5),
    "Lateral canthus": (1, 1.5),
    "Upper lip – central": (0.8, 1.6),
    "Upper lip – lateral": (0.8, 1.6),
    "Lower lip – central": (1, 2),
    "Lower lip – lateral": (1, 2),
    "Oral commissure": (1, 1.5),
    "Cheek – infra-orbital": (1.5, 3),
    "Cheek – medial": (2, 4),
    "Cheek – lateral": (2, 4),
    "Chin – mentum": (1.5, 3),
    "Neck – anterior": (2, 5),
    "Neck – posterior": (2, 5),
    "Ear – helical rim": (1, 1.5),
    "Ear – conchal bowl": (1.5, 2.5),
    "Ear – lobule": (1, 1.5),
    "Peri-auricular skin": (2, 4),
}


def _cat(loc: str, cm: float) -> str:
    lo, mid = THR[loc]
    return "small" if cm <= lo else "medium" if cm <= mid else "large"


def pick(size: str, mapping: dict) -> str:
    return mapping[size]


def normalize_pathology(cancer_type: str) -> str:
    """Map free-text pathology into the core pathology groups used by the algorithm."""
    txt = (cancer_type or "").strip().lower()
    if not txt:
        return ""
    if any(term in txt for term in ["melanoma in situ", "melanoma-in-situ", "melanoma in-situ", "mis", "lentigo maligna"]):
        return "Melanoma in situ"
    if "melanoma" in txt:
        return "Melanoma"
    if "scc" in txt or "squamous" in txt:
        return "SCC"
    if "bcc" in txt or "basal" in txt:
        return "BCC"
    return cancer_type.strip()


def recommended_margin_note(pathology: str, loc: str = "", breslow_mm: float = 0.0, tumour_risk: str = "") -> str:
    """Return literature-based clinical excision margin guidance for common cutaneous malignancies."""
    pathology = normalize_pathology(pathology)
    risk_txt = (tumour_risk or "").lower()
    high_risk = "high" in risk_txt or "complex" in risk_txt or "recurrent" in risk_txt or "ill" in risk_txt

    if pathology == "BCC":
        if high_risk:
            return (
                "Recommended margin guidance for BCC: low-risk primary BCC is commonly excised with ~4 mm clinical margins; "
                "for high-risk, recurrent, ill-defined, aggressive histology, or cosmetically/functionally sensitive head and neck sites, "
                "consider Mohs/margin-controlled excision or wider margins when feasible."
            )
        return (
            "Recommended margin guidance for BCC: low-risk primary BCC is commonly excised with ~4 mm clinical margins; "
            "use Mohs/margin-controlled excision or wider margins for high-risk, recurrent, ill-defined, or aggressive lesions."
        )

    if pathology == "SCC":
        if high_risk:
            return (
                "Recommended margin guidance for cutaneous SCC: low-risk primary cSCC is commonly excised with 4-6 mm clinical margins; "
                "high-risk lesions generally warrant margin-controlled excision/Mohs when available, or wider margins when anatomically feasible."
            )
        return (
            "Recommended margin guidance for cutaneous SCC: low-risk primary cSCC is commonly excised with 4-6 mm clinical margins; "
            "consider margin-controlled excision or wider margins for high-risk features."
        )

    if pathology == "Melanoma in situ":
        head_neck_sensitive = any(term in loc for term in ["Nasal", "eyelid", "canthus", "lip", "Ear", "Peri-auricular"])
        extra = (
            " For head and neck sites near the eyelid, nose, lip, or ear, margin-controlled excision before reconstruction may be useful when tissue sparing is important."
            if head_neck_sensitive else ""
        )
        return (
            "Recommended margin guidance for melanoma in situ: 5 mm-1 cm clinical radial margin when feasible." + extra
        )

    if pathology == "Melanoma":
        if breslow_mm and breslow_mm > 0:
            if breslow_mm <= 1.0:
                margin = "1 cm"
            elif breslow_mm <= 2.0:
                margin = "1-2 cm"
            else:
                margin = "2 cm"
            return (
                f"Recommended margin guidance for invasive melanoma: Breslow thickness {breslow_mm:g} mm → {margin} clinical radial margin when anatomically feasible. "
                "On the head and neck, margins may need modification for function/cosmesis; consider staged or margin-controlled excision before complex reconstruction."
            )
        return (
            "Recommended margin guidance for invasive melanoma depends on Breslow thickness: ≤1.0 mm → 1 cm; 1.01-2.0 mm → 1-2 cm; >2.0 mm → 2 cm, when anatomically feasible. "
            "Add Breslow thickness to generate a specific margin note."
        )

    return ""


def melanoma_preferred_repair(loc: str, size: str, depth: str) -> tuple[str, str]:
    """
    For melanoma / melanoma in situ, avoid rotation-heavy tissue rearrangement when feasible
    so the excision bed and margins remain easier to identify if re-excision is required.
    """
    full = depth.startswith("Full")

    if loc == "Scalp":
        if size == "small":
            return (
                "Linear primary closure ± galeal scoring",
                "For melanoma/MIS, direct linear closure keeps the excision bed easier to re-identify if margin revision is needed.",
            )
        if size == "medium":
            return (
                "Bilateral scalp advancement flap ± galeal scoring",
                "Advancement-based scalp closure preserves local anatomy better than broad rotation when margin revision may be required.",
            )
        return (
            "Staged margin clearance, then delayed advancement/graft-based reconstruction",
            "Large melanoma/MIS scalp defects should prioritize margin control before complex tissue rearrangement.",
        )

    if loc.startswith("Forehead") or loc in ["Temple", "Zygomatic-arch (temporal-malar)"]:
        if size == "small":
            return (
                "Linear primary closure in relaxed skin tension line",
                "Primary closure limits tissue displacement and facilitates margin localization if revision is required.",
            )
        if size == "medium":
            return (
                "A-T / O-T advancement flap",
                "Advancement is preferred over rotation for melanoma/MIS when feasible to reduce margin-bed distortion.",
            )
        return (
            "Staged margin clearance, then delayed advancement-based reconstruction",
            "For large melanoma/MIS defects, confirm margins before broad regional rotation or cervicofacial recruitment.",
        )

    if loc.startswith("Nasal"):
        if size == "small":
            return (
                "Primary closure if low-tension; otherwise delayed full-thickness skin graft after margin clearance",
                "Melanoma/MIS nasal defects should prioritize clear margin assessment and avoid local rotation if feasible.",
            )
        if size == "medium":
            return (
                "Staged excision/margin clearance, then advancement-based closure or FTSG",
                "Avoiding bilobed/rotation flaps can keep the original margin bed easier to identify for re-excision.",
            )
        return (
            "Staged margin clearance, then delayed reconstruction such as FTSG or forehead flap only if required",
            "Large melanoma/MIS nasal defects should not undergo complex tissue rearrangement until margins are secure.",
        )

    if loc in ["Upper eyelid", "Lower eyelid", "Medial canthus", "Lateral canthus"]:
        if size == "small":
            return (
                "Direct closure / local skin advancement",
                "For melanoma/MIS near the eyelids, direct or advancement repair limits tissue movement while preserving margin localization.",
            )
        if size == "medium":
            return (
                "Staged margin clearance, then eyelid skin advancement or graft-based repair",
                "Margin control should precede larger eyelid/canthal rearrangement for melanoma/MIS.",
            )
        return (
            "Staged margin clearance, then delayed oculoplastic reconstruction",
            "Large melanoma/MIS periocular defects require margin certainty before complex reconstruction.",
        )

    if loc.startswith("Upper lip") or loc.startswith("Lower lip") or loc == "Oral commissure":
        if size == "small":
            return (
                "Full-thickness wedge / primary closure",
                "Primary closure is preferred for small melanoma/MIS lip defects to preserve orientation for possible margin revision.",
            )
        if size == "medium":
            return (
                "Advancement-based lip repair after margin clearance",
                "For melanoma/MIS, advancement-based closure is preferred when feasible over rotation-type rearrangement.",
            )
        return (
            "Staged margin clearance, then delayed functional lip reconstruction",
            "Large melanoma/MIS lip defects should prioritize margin control before complex flap transfer.",
        )

    if loc.startswith("Cheek") or loc == "Chin – mentum":
        if full:
            return (
                "Staged margin clearance, then local advancement flap or graft-based reconstruction",
                "Full-depth melanoma/MIS defects should prioritize oncologic margin control before complex tissue movement.",
            )
        if size == "small":
            return (
                "Linear primary closure along relaxed skin tension line",
                "Primary closure keeps the defect and margins easiest to identify if re-excision is required.",
            )
        if size == "medium":
            return (
                "V-Y / A-T / O-T advancement flap",
                "Advancement is preferred over rotation for melanoma/MIS when feasible to reduce margin-bed distortion.",
            )
        return (
            "Staged margin clearance, then delayed cheek advancement flap or FTSG",
            "Large melanoma/MIS cheek defects should avoid broad rotation until margins are secure.",
        )

    if loc == "Neck – anterior":
        if size == "small":
            return (
                "Horizontal primary closure in relaxed neck crease",
                "Primary closure keeps the anterior-neck margin bed easy to identify for possible revision.",
            )
        return (
            "Bilateral cervical advancement flap after margin clearance",
            "Advancement along neck creases is preferred over rotation for melanoma/MIS when feasible.",
        )

    if loc == "Neck – posterior":
        if size == "small":
            return (
                "Horizontal primary closure along posterior neck crease",
                "Primary closure minimizes tissue displacement and supports margin-bed localization.",
            )
        if size == "medium":
            return (
                "Bilateral posterior cervical advancement flap after margin clearance",
                "For melanoma/MIS, advancement-based posterior-neck closure is preferred when feasible over rotation/transposition.",
            )
        return (
            "Staged margin clearance, then delayed advancement/graft-based posterior-neck reconstruction",
            "Large melanoma/MIS posterior-neck defects should prioritize margin control before broad tissue rearrangement.",
        )

    if loc.startswith("Ear") or loc == "Peri-auricular skin":
        if size == "small":
            return (
                "Primary wedge/direct closure after margin clearance",
                "Direct repair helps preserve the original margin bed for melanoma/MIS surveillance or revision.",
            )
        return (
            "Staged margin clearance, then advancement/graft-based auricular reconstruction",
            "For melanoma/MIS of the ear/peri-auricular region, avoid rotation-heavy rearrangement until margins are clear.",
        )

    return (
        "Primary closure or local advancement flap after margin clearance",
        "Melanoma/MIS pathology favors closure that minimizes tissue displacement so margins remain easier to identify.",
    )


def safe_logged_case_count() -> int:
    """Avoid crashing if usage_log.csv exists but is empty/corrupted."""
    if not DATA_PATH.exists() or DATA_PATH.stat().st_size == 0:
        return 0
    try:
        return len(pd.read_csv(DATA_PATH))
    except pd.errors.EmptyDataError:
        return 0


# ──────────────────────────────────────────────────────────────
# 2. DECISION ENGINE
# ──────────────────────────────────────────────────────────────
def decide(loc, kind, cm, depth, hair, age, dia, smk, rad, cancer_type="", margin_size_mm=0.0, breslow_mm=0.0, tumour_risk=""):
    size = _cat(loc, cm)
    flap = rationale = ""

    # ————————————————— SCALP —————————————————
    if loc == "Scalp":
        if depth.startswith("Full"):
            if size == "large":
                flap = "Latissimus-dorsi free flap + STSG"
                rationale = "Massive bare skull requires vascular muscle then graft."
            else:
                flap = "Ortícochea four-flap rotation"
                rationale = "≤6 cm full-depth closed with opposing galeal rotations."
        else:
            if size == "small":
                flap = "Linear primary closure ± galeal scoring"
                rationale = "≤2 cm superficial scalp closed after undermining."
            elif size == "medium":
                flap = "O-Z rotation flap"
                rationale = "2-6 cm superficial scalp defects via semicircular rotation."
            else:
                flap = "Ortícochea four-flap rotation"
                rationale = ">6 cm superficial needs four opposing rotations."
        if hair and "graft" in flap.lower():
            rationale += " Flap preserves hair-bearing skin; graft would alopecise."

    # ————————————————— FOREHEAD CENTRAL / LATERAL / TEMPLE / ZYGOMA —————————————————
    elif loc == "Forehead – central":
        if depth.startswith("Full"):
            flap = "Temporalis fascia turnover + frontal skin rotation"
            rationale = "Fascia vascularises bone, rotated skin closes."
        else:
            flap = pick(size, {
                "small": "Direct closure in horizontal rhytid",
                "medium": "H-plasty bilateral advancement",
                "large": "Parietal-forehead rotation flap",
            })
            rationale = pick(size, {
                "small": "Short scar hidden in forehead line.",
                "medium": "Advances both sides (1.5-5 cm).",
                "large": "Large defect recruits parietal scalp.",
            })
    elif loc == "Forehead – lateral":
        if depth.startswith("Full"):
            flap = "Temporoparietal fascia flap + STSG"
            rationale = "TP fascia on bone then skin graft."
        else:
            flap = pick(size, {
                "small": "Mini A-T advancement flap",
                "medium": "Temporal-scalp rotation flap",
                "large": "Extended cervicofacial rotation",
            })
            rationale = pick(size, {
                "small": "Triangle-to-T hides scar at hairline.",
                "medium": "Rotated hair-bearing scalp covers 1.5-4 cm.",
                "large": ">4 cm needs cheek/neck recruitment.",
            })
    elif loc == "Temple":
        if depth.startswith("Full"):
            flap = "Temporalis-fascia flap + STSG"
            rationale = "Vascular fascia over bone/joint."
        else:
            flap = pick(size, {
                "small": "Limberg rhomboid flap",
                "medium": "Mustardé cheek rotation flap",
                "large": "Cervicofacial rotation flap",
            })
            rationale = pick(size, {
                "small": "Rhomboid in crow’s-feet lines ≤1.5 cm.",
                "medium": "2-4 cm uses Mustardé upward rotation.",
                "large": ">4 cm full cervicofacial.",
            })
    elif loc == "Zygomatic-arch (temporal-malar)":
        if depth.startswith("Full"):
            flap = "Mustardé cheek rotation flap"
            rationale = "Robust cheek rotation covers arch."
        else:
            flap = pick(size, {
                "small": "Rhomboid transposition flap",
                "medium": "Mustardé cheek rotation flap",
                "large": "Cervicofacial rotation flap",
            })
            rationale = pick(size, {
                "small": "≤2 cm rhomboid along RSTL.",
                "medium": "2-4 cm rotated cheek skin.",
                "large": ">4 cm needs full cervicofacial flap.",
            })

    # ————————————————— NOSE —————————————————
    elif loc == "Nasal tip":
        if depth.startswith("Full"):
            flap = "Paramedian forehead flap + septal cartilage graft"
            rationale = "2-stage skin + support for full-depth tip."
        else:
            flap = pick(size, {
                "small": "Secondary intention / tiny FTSG",
                "medium": "Bilobed flap",
                "large": "Paramedian forehead flap",
            })
            rationale = pick(size, {
                "small": "<5 mm granulates or small graft.",
                "medium": "Bilobed uses upper-dorsum skin.",
                "large": ">1.5 cm exceeds nasal reserve.",
            })
    elif loc == "Nasal dorsum":
        if depth.startswith("Full"):
            flap = "Paramedian forehead flap"
            rationale = "Full-depth dorsal defect needs forehead skin & lining."
        else:
            flap = pick(size, {
                "small": "Rieger dorsal-nasal flap",
                "medium": "Glabellar rotation flap",
                "large": "Paramedian forehead flap",
            })
            rationale = pick(size, {
                "small": "≤1 cm short transposition.",
                "medium": "1-1.5 cm glabellar rotation.",
                "large": ">1.5 cm forehead flap.",
            })
    elif loc == "Nasal ala / side-wall":
        if depth.startswith("Full"):
            flap = "Nasolabial interpolation flap + conchal cartilage"
            rationale = "Staged cheek skin + cartilage maintain airway."
        else:
            flap = pick(size, {
                "small": "Inferior bilobed flap",
                "medium": "Nasolabial interpolation flap",
                "large": "Paramedian forehead flap",
            })
            rationale = pick(size, {
                "small": "<1 cm ala gap bilobed.",
                "medium": "1-1.5 cm staged nasolabial.",
                "large": ">1.5 cm requires forehead flap.",
            })

    # ————————————————— EYELIDS / CANTHI —————————————————
    elif loc == "Upper eyelid":
        if depth.startswith("Full"):
            flap = "Cutler-Beard bridge flap" if size == "large" else "Tenzel semicircular flap"
            rationale = (
                "Full-thickness >50 % upper-lid via 2-stage Cutler-Beard."
                if size == "large" else
                "25-50 % full-thickness closed by Tenzel lateral rotation."
            )
        else:
            flap = pick(size, {
                "small": "Direct closure in lid crease",
                "medium": "Blepharoplasty skin-advancement",
                "large": "Tenzel semicircular flap",
            })
            rationale = pick(size, {
                "small": "<1 cm skin closed in natural crease.",
                "medium": "1-1.5 cm advanced redundant lid skin.",
                "large": ">1.5 cm superficial uses Tenzel flap.",
            })
    elif loc == "Lower eyelid":
        if depth.startswith("Full"):
            flap = "Hughes tarsoconjunctival flap + STSG" if size == "large" else "Tenzel semicircular flap"
            rationale = (
                ">50 % full-thickness lower-lid with Hughes posterior lamella + skin graft."
                if size == "large" else
                "25-50 % full-thickness uses Tenzel semicircular."
            )
        else:
            flap = pick(size, {
                "small": "Direct closure",
                "medium": "Full-thickness skin graft",
                "large": "Tenzel semicircular flap",
            })
            rationale = pick(size, {
                "small": "≤1 cm linear closure.",
                "medium": "1-1.5 cm graft from post-auricular.",
                "large": ">1.5 cm superficial uses Tenzel.",
            })
    elif loc == "Medial canthus":
        if depth.startswith("Full") or size == "large":
            flap = "Paramedian (glabellar) forehead interpolation flap"
            rationale = "Deep/large medial canthus needs staged glabellar skin."
        else:
            flap = "Full-thickness skin graft" if size == "small" else "Glabellar V-Y (Rintala) flap"
            rationale = (
                "<1 cm grafted with thin skin."
                if size == "small" else
                "1-1.5 cm V-Y glabellar transposition."
            )
    elif loc == "Lateral canthus":
        flap = pick(size, {
            "small": "Direct primary closure",
            "medium": "Tenzel semicircular flap",
            "large": "Mustardé cheek rotation flap",
        })
        rationale = pick(size, {
            "small": "≤1 cm closed after cantholysis.",
            "medium": "25-50 % lateral defect uses Tenzel.",
            "large": ">1.5 cm needs Mustardé cheek rotation.",
        })

    # ————————————————— LIPS / COMMISSURE —————————————————
    elif loc.startswith("Upper lip"):
        zone = "central" in loc
        if depth.startswith("Superficial") and size == "small":
            flap = "V-Y vermilion advancement"
            rationale = "Tiny vermilion excision advanced mucosa."
        else:
            if zone:
                flap = pick(size, {
                    "small": "Full-thickness wedge closure",
                    "medium": "Abbé cross-lip flap",
                    "large": "Karapandzic bilateral rotation",
                })
                rationale = pick(size, {
                    "small": "≤0.8 cm (<30 %) wedge.",
                    "medium": "30-60 % central: staged Abbé cross-lip.",
                    "large": ">60 %: bilateral Karapandzic.",
                })
            else:
                flap = pick(size, {
                    "small": "Full-thickness wedge closure",
                    "medium": "Estlander flap",
                    "large": "Bernard-Burow advancement",
                })
                rationale = pick(size, {
                    "small": "<30 % lateral wedge.",
                    "medium": "30-50 % lateral/commissure Estlander.",
                    "large": ">50 % cheek advancement.",
                })
    elif loc.startswith("Lower lip"):
        zone = "central" in loc
        if zone:
            flap = pick(size, {
                "small": "Full-thickness wedge closure",
                "medium": "Karapandzic rotation flap",
                "large": "Bernard-Webster bilateral advancement",
            })
            rationale = pick(size, {
                "small": "<30 % wedge.",
                "medium": "30-60 % central Karapandzic.",
                "large": ">60 % Bernard-Webster.",
            })
        else:
            flap = pick(size, {
                "small": "Full-thickness wedge closure",
                "medium": "Estlander flap",
                "large": "Extended Karapandzic / Burow",
            })
            rationale = pick(size, {
                "small": "<30 % lateral wedge.",
                "medium": "30-50 % Estlander.",
                "large": ">50 % extended circumoral rotation.",
            })
    elif loc == "Oral commissure":
        if depth.startswith("Full") or size == "large":
            flap = "Free radial-forearm commissuroplasty flap"
            rationale = "Near-total commissure reconstructed microsurgically."
        else:
            flap = "Commissuroplasty triangular flap" if size == "small" else "Estlander cross-lip flap"
            rationale = (
                "<1 cm triangular mucocutaneous realignment."
                if size == "small" else
                "1-1.5 cm lateral loss Estlander flap."
            )

    # ————————————————— CHEEK / CHIN —————————————————
    elif loc == "Cheek – infra-orbital":
        flap = pick(size, {
            "small": "Malar V-Y advancement",
            "medium": "Mustardé cheek rotation",
            "large": "Cervicofacial rotation",
        })
        rationale = pick(size, {
            "small": "≤1.5 cm V-Y under eyelid.",
            "medium": "1.5-3 cm Mustardé malar rotation.",
            "large": ">3 cm cervicofacial flap.",
        })
    elif loc == "Cheek – medial":
        if depth.startswith("Full"):
            flap = "Cervicofacial rotation flap"
            rationale = "Deep buccal loss best with large rotation."
        else:
            flap = pick(size, {
                "small": "Limberg rhomboid flap",
                "medium": "V-Y cheek advancement",
                "large": "Cervicofacial rotation",
            })
            rationale = pick(size, {
                "small": "≤2 cm rhomboid along smile lines.",
                "medium": "2-4 cm V-Y advancement.",
                "large": ">4 cm cervicofacial flap.",
            })
    elif loc == "Cheek – lateral":
        if depth.startswith("Full"):
            flap = pick(size, {
                "small": "Limberg rhomboid transposition flap",
                "medium": "Cervicofacial rotation-advancement flap",
                "large": "Extended cervicofacial rotation flap",
            })
            rationale = pick(size, {
                "small": "Small deeper lateral-cheek defects can be closed with adjacent transposition while respecting relaxed skin tension lines.",
                "medium": "Lateral cheek and preauricular laxity can be recruited with cervicofacial rotation-advancement for deeper defects.",
                "large": "Large lateral-cheek defects usually need broad cervicofacial recruitment to maintain contour and avoid distortion of nearby units.",
            })
        else:
            flap = pick(size, {
                "small": "Limberg rhomboid flap",
                "medium": "V-Y lateral cheek advancement flap",
                "large": "Cervicofacial rotation flap",
            })
            rationale = pick(size, {
                "small": "≤2 cm lateral-cheek defects can use a rhomboid flap designed along relaxed skin tension lines.",
                "medium": "2-4 cm lateral-cheek defects can be advanced from adjacent cheek/preauricular laxity.",
                "large": ">4 cm lateral-cheek defects are best served by cervicofacial rotation to recruit broader cheek-neck skin.",
            })
    elif loc == "Chin – mentum":
        if depth.startswith("Full"):
            flap = "Submental island flap"
            rationale = "Full-thickness chin needs pedicled submental."
        else:
            flap = pick(size, {
                "small": "H-plasty bilateral advancement",
                "medium": "Submental advancement flap",
                "large": "Extended cervicofacial rotation",
            })
            rationale = pick(size, {
                "small": "≤1.5 cm bilateral advancement under chin.",
                "medium": "1.5-3 cm submental laxity advanced.",
                "large": ">3 cm cheek-neck rotation.",
            })

    # ————————————————— NECK —————————————————
    elif loc == "Neck – anterior":
        if depth.startswith("Full"):
            flap = pick(size, {
                "small": "Platysma-supported bilateral cervical advancement flap",
                "medium": "Cervical rotation-advancement flap",
                "large": "Cervicothoracic advancement / rotation flap",
            })
            rationale = pick(size, {
                "small": "Deep anterior-neck defect benefits from vascularized platysma support and layered closure.",
                "medium": "Anterior cervical skin laxity can be recruited with rotation-advancement while keeping scars in neck creases.",
                "large": "Large anterior-neck defects usually require recruitment from lower cervical or upper chest skin.",
            })
        else:
            flap = pick(size, {
                "small": "Horizontal primary closure in relaxed neck crease",
                "medium": "Bilateral cervical advancement flap / O-T advancement",
                "large": "Cervicothoracic advancement flap",
            })
            rationale = pick(size, {
                "small": "≤2 cm anterior-neck defects often close well along transverse cervical rhytids.",
                "medium": "2-5 cm defects can use lax anterior cervical skin with bilateral advancement and Burow management.",
                "large": ">5 cm defects generally need broader cervical or cervicothoracic tissue recruitment.",
            })
    elif loc == "Neck – posterior":
        if depth.startswith("Full"):
            flap = pick(size, {
                "small": "Posterior cervical rotation flap",
                "medium": "Trapezius myocutaneous advancement/rotation flap",
                "large": "Trapezius myocutaneous flap ± STSG",
            })
            rationale = pick(size, {
                "small": "Deep posterior-neck defects need vascularized local tissue over exposed fascia or muscle.",
                "medium": "The trapezius region provides robust regional tissue for deeper posterior cervical defects.",
                "large": "Large posterior-neck defects may require muscle/myocutaneous coverage, especially if critical structures are exposed.",
            })
        else:
            flap = pick(size, {
                "small": "Horizontal primary closure along posterior neck crease",
                "medium": "Limberg rhomboid transposition flap",
                "large": "Posterior cervical rotation flap / trapezius advancement flap",
            })
            rationale = pick(size, {
                "small": "≤2 cm posterior-neck defects can usually close directly with the scar placed transversely.",
                "medium": "2-5 cm defects are suited to rhomboid transposition using adjacent posterior cervical laxity.",
                "large": ">5 cm defects require broader posterior cervical or trapezius-region advancement/rotation.",
            })

    # ————————————————— EAR / PERI-AURICULAR —————————————————
    elif loc == "Ear – helical rim":
        flap = pick(size, {
            "small": "V-wedge chondro-cutaneous closure",
            "medium": "Antia-Buch advancement flap",
            "large": "Posterior-auricular tubed flap",
        })
        rationale = pick(size, {
            "small": "Short segment closed wedge.",
            "medium": "1-1.5 cm rim advanced.",
            "large": ">1.5 cm staged tubed flap.",
        })
        if depth.startswith("Full") and size != "small":
            rationale += " Conchal cartilage graft supports rim."
    elif loc == "Ear – conchal bowl":
        flap = pick(size, {
            "small": "Post-auricular full-thickness skin graft",
            "medium": "Revolving-door island flap",
            "large": "Two-stage posterior-auricular flap",
        })
        rationale = pick(size, {
            "small": "Thin FTSG matches concavity.",
            "medium": "Island flap swings into bowl.",
            "large": ">2.5 cm requires staged flap.",
        })
    elif loc == "Ear – lobule":
        flap = pick(size, {
            "small": "Direct wedge closure",
            "medium": "Gavello V-Y advancement",
            "large": "Bilobed lobule rotation + composite graft",
        })
        rationale = pick(size, {
            "small": "Tiny gap approximated.",
            "medium": "V-Y slides inferior lobule.",
            "large": ">1.5 cm rotation + graft restore bulk.",
        })
    elif loc == "Peri-auricular skin":
        flap = pick(size, {
            "small": "Direct sulcus closure",
            "medium": "Retro-auricular rotation flap",
            "large": "Cervicofacial rotation flap",
        })
        rationale = pick(size, {
            "small": "≤2 cm scar hides behind ear.",
            "medium": "2-4 cm mastoid rotation.",
            "large": ">4 cm extended cervicofacial.",
        })
        if depth.startswith("Full"):
            rationale += " Parotid fascia exposed – SMAS turned in."

    # ————————————————— PATHOLOGY-SENSITIVE MODIFIER —————————————————
    pathology = normalize_pathology(cancer_type)
    melanoma_like = pathology in ["Melanoma", "Melanoma in situ"]
    margin_guidance = recommended_margin_note(pathology, loc, breslow_mm, tumour_risk)

    if kind == "Oncologic" and melanoma_like:
        flap, rationale = melanoma_preferred_repair(loc, size, depth)

    # ————————————————— NOTES / RISK FLAGS —————————————————
    notes = []
    if smk:
        notes.append("Smoking jeopardises flap – cessation essential.")
    if dia:
        notes.append("Optimise glycaemia pre-op.")
    if rad:
        notes.append("Radiated skin – consider delay/wider pedicle.")
    if hair and "graft" in flap.lower():
        notes.append("A graft on hair-bearing skin causes alopecia; flap chosen.")
    if age < 18:
        notes.append("Paediatric skin tight – staged expansion may help.")
    elif age > 70:
        notes.append("Elderly laxity aids rotation; rhytids hide scars.")
    if kind == "Oncologic":
        if pathology in ["Melanoma", "Melanoma in situ"]:
            notes.append(
                f"Pathology: {pathology}. Prefer primary closure or advancement-based repair when feasible; avoid rotation-heavy flap design until margins are clear because tissue rearrangement can obscure the original margin bed."
            )
            if margin_guidance:
                notes.append(margin_guidance)
            if margin_size_mm:
                notes.append(f"Recorded clinical margin: {margin_size_mm:g} mm.")
        elif pathology in ["BCC", "SCC"]:
            notes.append(f"Pathology: {pathology}. Local flap selection may proceed based on subunit, size, depth, laxity, and margin status.")
            if margin_guidance:
                notes.append(margin_guidance)
            if margin_size_mm:
                notes.append(f"Recorded clinical margin: {margin_size_mm:g} mm.")
        else:
            notes.append("Confirm clear margins before reconstruction.")
    elif kind == "Traumatic":
        notes.append("Debride & align with laceration lines.")
    elif kind == "Congenital":
        notes.append("Consider staged expansion for symmetry.")

    if loc.startswith("Neck"):
        notes.append("Orient scars within relaxed transverse neck lines when feasible; protect marginal mandibular/spinal accessory anatomy depending on subsite.")

    return (
        f"**Recommended flap:** {flap}\n\n"
        f"**Rationale:** {rationale}\n\n"
        f"**Notes:** {' '.join(notes) if notes else 'None.'}"
    )


# ──────────────────────────────────────────────────────────────
# 3. SIDEBAR
# ──────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Flap Selection Tool")
    st.markdown(
        "**Prototype** tool for determining optimal local flap for excision closure.\n\n"
        "No personal identifiers are saved.\n"
        "Only anonymous input parameters & your feedback are stored "
        "in a private file visible *only* to the Research team.\n\n"
        "Made by referencing Baker — 3rd edition, Neligan Volume 1 & 3 — 5th edition.\n"
    )
    st.caption(f"Logged cases: {safe_logged_case_count()}")
    st.caption(f"Build: {date.today()}")

    if DATA_PATH.exists():
        admin_pass = st.secrets.get("ADMIN_PASS", "")
        pw_ok = st.text_input("Admin password", type="password") == admin_pass
        if pw_ok:
            st.download_button(
                "⬇️ Download usage CSV",
                data=DATA_PATH.read_bytes(),
                file_name="usage_log.csv",
                mime="text/csv",
            )


# ──────────────────────────────────────────────────────────────
# 4. SESSION STATE
# ──────────────────────────────────────────────────────────────
for key, default in {
    "case_submitted": False,
    "feedback_done": False,
    "case_row": {},
    "recommendation": "",
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ──────────────────────────────────────────────────────────────
# 5. CASE ENTRY FORM
# ──────────────────────────────────────────────────────────────
if not st.session_state.case_submitted:
    with st.form("case_form"):
        c1, c2 = st.columns(2)
        loc = c1.selectbox("Anatomical sub-unit", SUBUNITS)
        kind = c2.selectbox("Defect type", ["Oncologic", "Traumatic", "Congenital"])
        depth = c1.radio("Depth of defect", DEPTH_OPTS)
        cm = c2.number_input(
            "Largest diameter (cm)",
            min_value=0.1,
            max_value=25.0,
            value=1.0,
            step=0.1,
        )
        age = c1.number_input(
            "Patient age (years)",
            min_value=0,
            max_value=120,
            value=60,
            step=1,
        )
        hair = c2.checkbox("Hair-bearing skin?", True)

        st.markdown("##### Additional clinical details")
        patient_sex = c1.selectbox("Patient sex", ["", "Male", "Female", "Other"])
        cancer_type = c2.selectbox(
            "Pathology / cancer type",
            ["", "BCC", "SCC", "Melanoma", "Melanoma in situ", "Other"],
            help="Used to modify reconstruction logic for melanoma/MIS when margin-bed preservation is important.",
        )
        tumour_risk = c2.selectbox(
            "Tumour risk level",
            ["", "Low-risk", "High-risk / complex / recurrent / ill-defined"],
            help="Used for BCC/SCC margin note. Leave blank if unknown.",
        )
        breslow_mm = c1.number_input(
            "Breslow thickness (mm) if invasive melanoma",
            min_value=0.0,
            max_value=20.0,
            value=0.0,
            step=0.1,
            help="Only used when pathology is invasive melanoma. Leave 0 if not applicable or unknown.",
        )
        margin_size_mm = c1.number_input(
            "Margin size (mm)",
            min_value=0.0,
            max_value=50.0,
            value=0.0,
            step=1.0,
        )

        st.markdown("##### Risk factors")
        dia = st.checkbox("Diabetes")
        smk = st.checkbox("Active smoker")
        rad = st.checkbox("Previously irradiated site")

        submitted = st.form_submit_button("Recommend flap")

    if submitted:
        st.session_state.case_row = {
            "timestamp_utc": datetime.utcnow().isoformat(timespec="seconds"),
            "loc": loc,
            "kind": kind,
            "depth": depth.split()[0],
            "cm": cm,
            "hair": hair,
            "age": age,
            "patient_sex": patient_sex,
            "cancer_type": cancer_type.strip(),
            "tumour_risk": tumour_risk,
            "breslow_mm": breslow_mm,
            "margin_size_mm": margin_size_mm,
            "dia": dia,
            "smk": smk,
            "rad": rad,
        }
        st.session_state.recommendation = decide(
            loc, kind, cm, depth, hair, age, dia, smk, rad, cancer_type, margin_size_mm, breslow_mm, tumour_risk
        )
        st.session_state.case_submitted = True


# ──────────────────────────────────────────────────────────────
# 6. RECOMMENDATION + FEEDBACK
# ──────────────────────────────────────────────────────────────
if st.session_state.case_submitted and not st.session_state.feedback_done:
    st.markdown(st.session_state.recommendation)

    with st.form("feedback_form"):
        used_choice = st.radio(
            "Did you use the recommended flap?",
            ["Yes", "No"],
            key="used_recommended",
            horizontal=True,
        )
        alt_flap_val = st.text_input(
            "If you used a different flap, which one?",
            key="alt_flap_text",
            placeholder="Type alternative flap here…",
        )

        st.markdown("##### Additional feedback")
        physician_name = st.text_input(
            "Physician name",
            key="physician_name",
            placeholder="Enter physician name",
        )
        pgy_levels = st.multiselect(
            "PGY level",
            ["PGY-1", "PGY-2", "PGY-3", "PGY-4", "PGY-5", "Fellow", "Staff"],
            key="pgy_levels",
        )
        experience_level = st.selectbox(
            "Experience level (only if faculty)",
            ["", "Early Career Faculty <5years", "Faculty 5-10years", "Faculty 10-20 years", "Faculty > 20 years"],
            key="experience_level",
        )
        q2_algorithm_help = st.radio(
            "To what extent did your recon plan match the algorithm suggestion?",
            ["Strongly Agree", "Agree", "Neutral", "Disagree", "Strongly Disagree"],
            key="algorithm_assist_q2",
            horizontal=True,
        )
        q3_algorithm_help = st.radio(
            "To what extent did the algorithm assist you in recon planning?",
            ["Very helpful", "Helpful", "Neutral", "Unhelpful", "Very unhelpful"],
            key="algorithm_assist_q3",
            horizontal=True,
        )
        final_comments_rationale = st.text_area(
            "Final comments / rationale",
            key="final_comments_rationale",
            placeholder="Add any comments, rationale, or context here...",
        )

        send = st.form_submit_button("Submit feedback")

    if send:
        if used_choice == "No" and not alt_flap_val.strip():
            st.warning("Please tell us which flap you used.")
            st.stop()

        m = re.search(r"\*\*Recommended flap:\*\*\s*(.+)", st.session_state.recommendation)
        rec_flap = m.group(1).strip() if m else "(parse failed)"

        row = st.session_state.case_row.copy()
        row.update({
            "recommended_flap": rec_flap,
            "used_recommended": (used_choice == "Yes"),
            "alt_flap_if_no": alt_flap_val.strip(),
            "physician_name": physician_name.strip(),
            "pgy_levels": "|".join(pgy_levels),
            "experience_level": experience_level,
            "algorithm_assist_recon_planning_q2": q2_algorithm_help,
            "algorithm_assist_recon_planning_q3": q3_algorithm_help,
            "final_comments_rationale": final_comments_rationale.strip(),
        })

        first_write = not DATA_PATH.exists() or DATA_PATH.stat().st_size == 0
        with DATA_PATH.open("a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=row.keys(), quoting=csv.QUOTE_MINIMAL)
            if first_write:
                writer.writeheader()
            writer.writerow(row)

        st.success("Thank you — entry logged.")
        st.session_state.feedback_done = True

        for k in (
            "used_recommended",
            "alt_flap_text",
            "physician_name",
            "pgy_levels",
            "experience_level",
            "algorithm_assist_q2",
            "algorithm_assist_q3",
            "final_comments_rationale",
        ):
            st.session_state.pop(k, None)


# ──────────────────────────────────────────────────────────────
# 7. RESET BUTTON AFTER FEEDBACK
# ──────────────────────────────────────────────────────────────
if st.session_state.get("feedback_done"):
    if st.button("Start new case"):
        st.session_state["case_submitted"] = False
        st.session_state["feedback_done"] = False
        st.session_state["recommendation"] = ""
        st.session_state["case_row"] = {}

        for k in ("used_recommended", "alt_flap_text"):
            st.session_state.pop(k, None)

        try:
            st.rerun()
        except AttributeError:
            st.experimental_rerun()


# ──────────────────────────────────────────────────────────────
# FOOTER
# ──────────────────────────────────────────────────────────────
st.markdown("---")
st.caption("Research prototype — use best clinical judgement.")
