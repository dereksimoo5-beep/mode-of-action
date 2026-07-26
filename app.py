"""
Modes d'action phyto - explorateur et outil de revision
Base : familles chimiques des matieres actives phytosanitaires (FRAC / IRAC / HRAC)
"""

import random
import unicodedata
from pathlib import Path

import pandas as pd
import streamlit as st

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------

st.set_page_config(
    page_title="Modes d'action phyto",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATA_PATH = Path(__file__).parent / "data" / "modes_action.csv"
if not DATA_PATH.exists():
    DATA_PATH = Path(__file__).parent / "modes_action.csv"
RISK_ORDER = [
    "Très faible", "Faible", "Faible à modéré", "Modéré",
    "Modéré à élevé", "Élevé", "Très élevé",
]

RISK_COLORS = {
    "Très faible": "#2e7d32",
    "Faible": "#558b2f",
    "Faible à modéré": "#9e7b00",
    "Modéré": "#b26a00",
    "Modéré à élevé": "#c0392b",
    "Élevé": "#b71c1c",
    "Très élevé": "#7b0000",
}

CAT_ICONS = {
    "Fongicides": "🍄",
    "Insecticides & acaricides": "🐛",
    "Herbicides": "🌾",
    "Nématicides": "🪱",
}

st.markdown(
    """
    <style>
    /* Claude-inspired Global Theme */
    .stApp {
        background-color: #fdfcf9;
        color: #2d2b2a;
    }
    h1, h2, h3, h4, h5, h6 {
        font-family: "Georgia", "Times New Roman", serif !important;
        color: #1a1918 !important;
        font-weight: 500 !important;
    }
    .block-container {
        padding-top: 2rem; 
        max-width: 1000px; 
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* Components */
    .badge {display:inline-block; padding:2px 10px; border-radius:12px;
            color:#fff; font-size:0.75rem; font-weight:600; white-space:nowrap;}
    .code-chip {display:inline-block; padding:3px 12px; border-radius:6px;
            background:#f0eee9; color:#2d2b2a; font-weight:600; font-size:0.9rem; border: 1px solid #e0ded9;}
            
    .card {border:1px solid #e8e6e1; border-radius:12px; padding:20px 24px;
           margin-bottom:16px; background:#ffffff; box-shadow: 0 1px 2px rgba(0,0,0,0.02);}
    .card h4 {margin:0 0 6px 0; font-size:1.1rem; color:#1a1918; font-family: "Georgia", serif;}
    .lbl {font-size:0.75rem; text-transform:uppercase; letter-spacing:0.5px;
          color:#8a8885; font-weight:600; margin-top:12px;}
    .val {font-size:0.95rem; color:#2d2b2a; line-height:1.5;}
    
    .flash {border:1px solid #e8e6e1; border-radius:16px; padding:36px 30px;
            text-align:center; background:#ffffff; min-height:160px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.03);}
    .flash .big {font-size:1.6rem; font-weight:500; color:#1a1918; line-height:1.4; font-family: "Georgia", serif;}
    .flash .sub {font-size:0.8rem; color:#8a8885; text-transform:uppercase;
                 letter-spacing:1px; margin-bottom:12px;}
    </style>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------------------------------
# Donnees
# --------------------------------------------------------------------------

@st.cache_data
def load_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH, encoding="utf-8-sig")
    df["risque"] = pd.Categorical(df["risque"], categories=RISK_ORDER, ordered=True)
    df["ma_list"] = df["matieres_actives"].apply(
        lambda s: [x.strip() for x in str(s).replace(" ; ", ", ").split(",") if x.strip()]
    )
    df["_search"] = (
        df["code"] + " | " + df["famille"] + " | " + df["mode_action"]
        + " | " + df["matieres_actives"] + " | " + df["groupe"] + " | " + df["categorie"]
    ).apply(lambda s: strip_accents(s.lower()))
    return df


def strip_accents(txt: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", txt)
        if unicodedata.category(c) != "Mn"
    )


def risk_badge(risque: str, estime: str = "non") -> str:
    color = RISK_COLORS.get(risque, "#666")
    star = " *" if estime == "oui" else ""
    return f'<span class="badge" style="background:{color}">{risque}{star}</span>'


df = load_data()


# --------------------------------------------------------------------------
# Etat de session
# --------------------------------------------------------------------------

DEFAULTS = {
    "q_current": None,
    "q_index": 0,
    "q_answered": False,
    "q_choice": None,
    "score_ok": 0,
    "score_total": 0,
    "streak": 0,
    "best_streak": 0,
    "errors": [],
    "flash_row": None,
    "flash_revealed": False,
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v


# --------------------------------------------------------------------------
# Barre laterale : filtres
# --------------------------------------------------------------------------

st.sidebar.markdown("## 🔎 Filtres")

cats = st.sidebar.multiselect(
    "Catégorie",
    options=sorted(df["categorie"].unique()),
    default=[],
    placeholder="Toutes",
)

orgs = st.sidebar.multiselect(
    "Classification",
    options=sorted(df["organisme"].unique()),
    default=[],
    placeholder="Toutes",
)

risks = st.sidebar.multiselect(
    "Risque de résistance",
    options=RISK_ORDER,
    default=[],
    placeholder="Tous",
)

hide_est = st.sidebar.checkbox("Masquer les risques estimés (*)", value=False)

st.sidebar.markdown("---")
st.sidebar.caption(
    "Les valeurs de risque suivies d'un astérisque sont des estimations par "
    "analogie, en l'absence de classement officiel publié.\n\n"
    "L'homologation réelle dépend de l'index ONSSA, pas de la présence "
    "d'une famille dans cette base."
)


def apply_filters(data: pd.DataFrame) -> pd.DataFrame:
    out = data
    if cats:
        out = out[out["categorie"].isin(cats)]
    if orgs:
        out = out[out["organisme"].isin(orgs)]
    if risks:
        out = out[out["risque"].isin(risks)]
    if hide_est:
        out = out[out["estime"] == "non"]
    return out


pool = apply_filters(df)


# --------------------------------------------------------------------------
# En-tete
# --------------------------------------------------------------------------

st.markdown("# 🧪 Modes d'action phytosanitaires")
st.caption(
    "Familles chimiques, cibles biochimiques et risque de résistance — "
    "classification FRAC / IRAC / HRAC-WSSA"
)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Entrées affichées", len(pool))
c2.metric("Codes distincts", pool["code"].nunique())
c3.metric("Matières actives", sum(len(x) for x in pool["ma_list"]))
c4.metric("Catégories", pool["categorie"].nunique())

tab_explore, tab_flash, tab_quiz, tab_stats = st.tabs(
    ["📚 Explorer", "🃏 Révision", "🎯 Quiz", "📊 Vue d'ensemble"]
)


# --------------------------------------------------------------------------
# Onglet 1 : explorer
# --------------------------------------------------------------------------

with tab_explore:
    query = st.text_input(
        "Recherche libre",
        placeholder="ex. azoxystrobine, SDHI, complexe III, FRAC 11, tébuconazole…",
        label_visibility="collapsed",
    )

    res = pool
    if query.strip():
        needle = strip_accents(query.lower().strip())
        terms = [t for t in needle.split() if t]
        mask = res["_search"].apply(lambda s: all(t in s for t in terms))
        res = res[mask]

    left, right = st.columns([3, 1])
    with right:
        view = st.radio("Affichage", ["Fiches", "Tableau"], horizontal=False)
    with left:
        st.markdown(f"**{len(res)} résultat(s)**")

    if res.empty:
        st.info("Aucun résultat. Élargis la recherche ou retire des filtres.")
    elif view == "Tableau":
        show = res[["categorie", "code", "famille", "mode_action",
                    "matieres_actives", "risque"]].copy()
        show.columns = ["Catégorie", "Code", "Famille chimique",
                        "Mode d'action", "Matières actives", "Risque"]
        st.dataframe(show, width="stretch", hide_index=True, height=560)
        st.download_button(
            "⬇️ Exporter ces résultats (CSV)",
            data=show.to_csv(index=False).encode("utf-8-sig"),
            file_name="modes_action_export.csv",
            mime="text/csv",
        )
    else:
        for cat, grp in res.groupby("categorie", sort=False):
            st.markdown(f"### {CAT_ICONS.get(cat, '•')} {cat}")
            for _, r in grp.iterrows():
                st.markdown(
                    f"""
                    <div class="card">
                      <span class="code-chip">{r['code']}</span>
                      &nbsp;{risk_badge(r['risque'], r['estime'])}
                      <div class="lbl">Famille chimique</div>
                      <div class="val"><b>{r['famille']}</b></div>
                      <div class="lbl">Mode d'action</div>
                      <div class="val">{r['mode_action']}</div>
                      <div class="lbl">Matières actives (exemples)</div>
                      <div class="val">{r['matieres_actives']}</div>
                      <div class="lbl">Groupe</div>
                      <div class="val" style="color:#7a828c">{r['groupe']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


# --------------------------------------------------------------------------
# Onglet 2 : revision (flashcards)
# --------------------------------------------------------------------------

with tab_flash:
    st.markdown("### 🃏 Fiches de révision")
    st.caption(
        "Une matière active s'affiche : retrouve son code et son mode d'action "
        "avant de retourner la carte."
    )

    if pool.empty:
        st.warning("Aucune entrée avec les filtres actuels.")
    else:
        cA, cB = st.columns([1, 1])
        if cA.button("🔀 Nouvelle carte", width="stretch") or st.session_state.flash_row is None:
            st.session_state.flash_row = int(pool.sample(1).index[0])
            st.session_state.flash_revealed = False

        row = df.loc[st.session_state.flash_row]
        ma = random.Random(st.session_state.flash_row).choice(row["ma_list"])

        st.markdown(
            f"""
            <div class="flash">
              <div class="sub">Matière active</div>
              <div class="big">{ma}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if cB.button("👁️ Retourner la carte", width="stretch"):
            st.session_state.flash_revealed = True

        if st.session_state.flash_revealed:
            st.markdown("")
            k1, k2 = st.columns([1, 2])
            with k1:
                st.markdown(f'<span class="code-chip">{row["code"]}</span>', unsafe_allow_html=True)
                st.markdown(risk_badge(row["risque"], row["estime"]), unsafe_allow_html=True)
            with k2:
                st.markdown(f"**Famille :** {row['famille']}")
                st.markdown(f"**Mode d'action :** {row['mode_action']}")
                st.markdown(f"**Catégorie :** {row['categorie']}")
            with st.expander("Autres matières actives du même code"):
                st.write(row["matieres_actives"])


# --------------------------------------------------------------------------
# Onglet 3 : quiz
# --------------------------------------------------------------------------

QUESTION_TYPES = {
    "code_from_ma": "Code à partir d'une matière active",
    "moa_from_code": "Mode d'action à partir d'un code",
    "famille_from_ma": "Famille chimique à partir d'une matière active",
    "risk_from_code": "Risque de résistance d'un code",
    "same_code": "Deux matières actives, même code ou non",
}


def same_family_pool(data: pd.DataFrame, row) -> pd.DataFrame:
    """Distracteurs tires de la meme categorie, pour des questions non triviales."""
    subset = data[data["categorie"] == row["categorie"]]
    return subset if len(subset) >= 5 else data


def build_question(data: pd.DataFrame, qtype: str):
    """Construit une question QCM depuis le jeu de donnees filtre."""
    if qtype == "same_code":
        r1 = data.sample(1).iloc[0]
        same = random.random() < 0.5
        if same and len(r1["ma_list"]) >= 2:
            a, b = random.sample(r1["ma_list"], 2)
            answer, expl = "Oui", f"Les deux relèvent du code {r1['code']} ({r1['famille']})."
        else:
            others = same_family_pool(data, r1)
            others = others[others["code"] != r1["code"]]
            if others.empty:
                return None
            r2 = others.sample(1).iloc[0]
            a = random.choice(r1["ma_list"])
            b = random.choice(r2["ma_list"])
            answer = "Non"
            expl = f"{a} = {r1['code']} · {b} = {r2['code']}. Alternance valable."
        return {
            "prompt": f"**{a}** et **{b}** partagent-elles le même code de mode d'action ?",
            "options": ["Oui", "Non"],
            "answer": answer,
            "explain": expl,
        }

    row = data.sample(1).iloc[0]
    ma = random.choice(row["ma_list"])
    near = same_family_pool(data, row)

    if qtype == "code_from_ma":
        wrong = near[near["code"] != row["code"]]["code"].drop_duplicates()
        opts = random.sample(list(wrong), min(3, len(wrong))) + [row["code"]]
        prompt = f"À quel code de mode d'action appartient **{ma}** ?"
        answer = row["code"]
        explain = f"{row['code']} — {row['famille']} : {row['mode_action']}."

    elif qtype == "moa_from_code":
        wrong = near[near["mode_action"] != row["mode_action"]]["mode_action"].drop_duplicates()
        opts = random.sample(list(wrong), min(3, len(wrong))) + [row["mode_action"]]
        prompt = f"Quel est le mode d'action du code **{row['code']}** ({row['famille'][:60]}) ?"
        answer = row["mode_action"]
        explain = f"Exemples de matières actives : {row['matieres_actives']}."

    elif qtype == "famille_from_ma":
        wrong = near[near["famille"] != row["famille"]]["famille"].drop_duplicates()
        opts = random.sample(list(wrong), min(3, len(wrong))) + [row["famille"]]
        prompt = f"À quelle famille chimique appartient **{ma}** ?"
        answer = row["famille"]
        explain = f"{row['code']} : {row['mode_action']}."

    else:  # risk_from_code
        opts = RISK_ORDER[:]
        prompt = (f"Quel est le niveau de risque de résistance associé au code "
                  f"**{row['code']}** ({row['famille'][:60]}) ?")
        answer = str(row["risque"])
        explain = (f"{row['mode_action']}."
                   + (" Valeur estimée par analogie." if row["estime"] == "oui" else ""))

    opts = list(dict.fromkeys(opts))
    if answer not in opts:
        opts.append(answer)
    random.shuffle(opts)
    return {"prompt": prompt, "options": opts, "answer": answer, "explain": explain}


with tab_quiz:
    st.markdown("### 🎯 Quiz")

    qcols = st.columns([3, 1])
    with qcols[0]:
        chosen_types = st.multiselect(
            "Types de questions",
            options=list(QUESTION_TYPES.keys()),
            default=list(QUESTION_TYPES.keys()),
            format_func=lambda k: QUESTION_TYPES[k],
        )
    with qcols[1]:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        if st.button("♻️ Réinitialiser le score", width="stretch"):
            for k in ("score_ok", "score_total", "streak", "best_streak"):
                st.session_state[k] = 0
            st.session_state.errors = []
            st.session_state.q_current = None
            st.rerun()

    m1, m2, m3 = st.columns(3)
    total = st.session_state.score_total
    pct = (st.session_state.score_ok / total * 100) if total else 0
    m1.metric("Score", f"{st.session_state.score_ok} / {total}", f"{pct:.0f} %")
    m2.metric("Série en cours", st.session_state.streak)
    m3.metric("Meilleure série", st.session_state.best_streak)

    if pool.empty or not chosen_types:
        st.warning("Sélectionne au moins un type de question et élargis les filtres.")
    else:
        if st.session_state.q_current is None:
            st.session_state.q_current = build_question(pool, random.choice(chosen_types))
            st.session_state.q_index += 1
            st.session_state.q_answered = False
            st.session_state.q_choice = None

        q = st.session_state.q_current
        if q is None:
            st.warning("Pas assez de données pour générer une question avec ces filtres.")
        else:
            st.markdown("---")
            st.markdown(f"#### {q['prompt']}")

            choice = st.radio(
                "Réponse",
                q["options"],
                index=None,
                key=f"radio_{st.session_state.q_index}",
                disabled=st.session_state.q_answered,
                label_visibility="collapsed",
            )

            b1, b2 = st.columns([1, 1])
            if not st.session_state.q_answered:
                if b1.button("✅ Valider", width="stretch", disabled=choice is None):
                    st.session_state.q_answered = True
                    st.session_state.q_choice = choice
                    st.session_state.score_total += 1
                    if choice == q["answer"]:
                        st.session_state.score_ok += 1
                        st.session_state.streak += 1
                        st.session_state.best_streak = max(
                            st.session_state.best_streak, st.session_state.streak
                        )
                    else:
                        st.session_state.streak = 0
                        st.session_state.errors.append(
                            {"Question": q["prompt"].replace("**", ""),
                             "Ta réponse": choice,
                             "Bonne réponse": q["answer"]}
                        )
                    st.rerun()
            else:
                if q["answer"] == st.session_state.q_choice:
                    st.success(f"Correct — {q['explain']}")
                else:
                    st.error(f"Faux. Réponse attendue : **{q['answer']}**")
                    st.info(q["explain"])
                if b2.button("➡️ Question suivante", width="stretch"):
                    st.session_state.q_current = build_question(pool, random.choice(chosen_types))
                    st.session_state.q_index += 1
                    st.session_state.q_answered = False
                    st.session_state.q_choice = None
                    st.rerun()

    if st.session_state.errors:
        with st.expander(f"❌ Revoir mes erreurs ({len(st.session_state.errors)})"):
            st.dataframe(pd.DataFrame(st.session_state.errors),
                         width="stretch", hide_index=True)


# --------------------------------------------------------------------------
# Onglet 4 : vue d'ensemble
# --------------------------------------------------------------------------

with tab_stats:
    st.markdown("### 📊 Répartition de la base")

    s1, s2 = st.columns(2)
    with s1:
        st.markdown("**Entrées par catégorie**")
        st.bar_chart(pool["categorie"].value_counts())
    with s2:
        st.markdown("**Entrées par niveau de risque**")
        counts = pool["risque"].value_counts().reindex(RISK_ORDER).fillna(0)
        st.bar_chart(counts)

    st.markdown("**Codes à surveiller en priorité** (risque élevé ou très élevé)")
    hot = pool[pool["risque"].isin(["Élevé", "Très élevé"])][
        ["categorie", "code", "famille", "matieres_actives", "risque"]
    ]
    hot.columns = ["Catégorie", "Code", "Famille chimique", "Matières actives", "Risque"]
    st.dataframe(hot, width="stretch", hide_index=True)

    st.markdown("---")
    st.caption(
        "Rappel : l'alternance antirésistance porte sur le **code**, pas sur la "
        "spécialité commerciale ni sur la famille chimique. Deux familles "
        "chimiques distinctes peuvent partager le même code et ne constituent "
        "alors aucune alternance."
    )
