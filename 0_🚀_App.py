import streamlit as st
import pandas as pd
import altair as alt
from datetime import date
import gspread
from google.oauth2.service_account import Credentials
import json
import os
import time
import io
import re

# --- 1. SETUP PAGINA ---
# Nota: Rinomina questo file in "0_🚀_App.py" per vedere l'icona nel menu laterale
st.set_page_config(page_title="SISMA MANAGER", layout="wide", initial_sidebar_state="expanded")

# --- 1.1 SISTEMA DI LOGIN ---
def check_password():
    if "PASSWORD_ACCESSO" not in st.secrets:
        return True

    def password_entered():
        if st.session_state["password"] == st.secrets["PASSWORD_ACCESSO"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.markdown("### 🔒 ACCESSO RISERVATO STUDIO")
        st.text_input("Inserisci Password:", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.markdown("### 🔒 ACCESSO RISERVATO STUDIO")
        st.text_input("Inserisci Password:", type="password", on_change=password_entered, key="password")
        st.error("⛔ Password errata")
        return False
    else:
        return True

if not check_password():
    st.stop()

# --- COSTANTI & STILI ---
COL_DEEP = "#0c3a47"
COL_ACCENT = "#427e72"

SOCI_OPZIONI = [
    "ARRIGHETTI ANDREA", "BERTOCCI STEFANO", "LUMINI ANDREA", 
    "MARASCO LORENZO", "MINUTOLI GIOVANNI", "PANCANI GIOVANNI", "REPOLE MARCO"
]

SERVIZI_LIST = [
    "Rilievo Laser Scanner", "Fotogrammetria", "Volo Drone", "Topografia",
    "Restituzione 2D (CAD)", "Modellazione 3D", "Modellazione BIM (H-BIM)",
    "Relazione Storica", "Indagini Diagnostiche", "Archeologia Preventiva",
    "Computi Metrici", "Direzione Lavori", "Sicurezza"
]

st.markdown(f"""
    <style>
    /* STILI GENERALI */
    .stApp {{ background-color: #000000; color: #FFFFFF; font-family: 'Helvetica Neue', sans-serif; }}
    [data-testid="stSidebar"] {{ background-color: #000000; border-right: 1px solid #333333; }}
    
    /* INPUTS */
    .stTextInput input, .stNumberInput input, .stDateInput input, .stTextArea textarea {{
        background-color: #0a0a0a !important; color: #FFF !important; 
        border: 1px solid #333 !important; border-radius: 4px !important; 
    }}
    div[data-baseweb="select"] > div {{
        background-color: #0a0a0a !important; color: #FFF !important; border-color: #333 !important;
    }}
    
    /* EXPANDERS */
    div[data-testid="stExpander"] details {{
        border: 1px solid {COL_DEEP} !important; border-radius: 8px !important;       
        overflow: hidden !important; background-color: transparent !important; margin-bottom: 20px !important;
    }}
    div[data-testid="stExpander"] summary {{
        background-color: {COL_DEEP} !important; border: none !important;             
        color: #FFFFFF !important; font-weight: 600 !important; border-radius: 0 !important;         
    }}
    div[data-testid="stExpanderDetails"] {{
        background-color: transparent !important; border-top: 1px solid rgba(255, 255, 255, 0.1); padding: 20px !important;
    }}
    
    /* BUTTONS STANDARD */
    div.stButton > button {{
        background-color: {COL_DEEP} !important; color: #FFFFFF !important; 
        border: 1px solid {COL_ACCENT} !important; border-radius: 4px; 
    }}

    /* CSS SPECIFICO PER I PULSANTI PICCOLI DELLA DASHBOARD */
    /* Targettiamo i bottoni dentro le colonne piccole */
    div[data-testid="column"] button p {{
        font-size: 12px !important;
    }}
    div[data-testid="column"] button {{
        min-height: 0px !important;
        height: 35px !important;
        padding-top: 0px !important;
        padding-bottom: 0px !important;
    }}

    /* ORGANIGRAMMA STYLES */
    .org-header {{ 
        color: {COL_ACCENT}; font-size: 22px; font-weight: bold; text-transform: uppercase; letter-spacing: 3px; 
        text-align: center; margin-top: 50px; margin-bottom: 30px; border-bottom: 1px solid #333; padding-bottom: 15px; 
    }}
    .org-card {{ 
        background-color: #111111; border: 1px solid #333; border-top: 3px solid {COL_DEEP}; 
        border-radius: 4px; padding: 25px 20px; text-align: center; margin-bottom: 15px;
        display: flex; flex-direction: column; justify-content: center; align-items: center;
    }}
    .card-mid {{
        background-color: #111111; border: 1px solid #333; border-top: 3px solid {COL_DEEP}; 
        border-radius: 4px; padding: 25px 20px; 
        height: 380px; 
        display: flex; flex-direction: column; align-items: center; justify-content: flex-start;
    }}
    .org-row {{
        display: block; width: 100%; margin-bottom: 15px; text-align: center;
        border-bottom: 1px solid #222; padding-bottom: 10px;
    }}
    .org-row:last-child {{ border-bottom: none; margin-bottom: 0; padding-bottom: 0; }}
    .role-label {{ 
        color: {COL_ACCENT}; font-size: 14px; text-transform: uppercase; font-weight: bold; 
        display: block; margin-bottom: 5px; letter-spacing: 0.5px;
    }}
    .card-subtitle {{ 
        font-size: 18px; color: #FFFFFF; font-weight: bold; text-transform: uppercase; 
        margin-bottom: 15px; width: 100%; text-align: center; line-height: 1.2;
    }}
    .name-text {{ font-size: 18px; color: #DDD; font-weight: 500; margin-bottom: 5px; display: block; }}
    
    /* TOTALI BOX */
    .total-box-standard {{
        background-color: {COL_DEEP}; border: 1px solid {COL_ACCENT}; padding: 15px; border-radius: 5px; text-align: center; margin-bottom: 10px;
    }}
    .total-box-desat {{
        background-color: #0f0f0f; border: 1px solid #222; padding: 10px; border-radius: 5px; text-align: center;
    }}
    .total-label {{ font-size: 12px; color: #ccc; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 5px; }}
    .total-value {{ font-size: 24px; font-weight: bold; color: #FFF; }}

    .logo-container {{ display: flex; justify-content: center; padding-bottom: 30px; border-bottom: 1px solid #333333; margin-bottom: 30px; }}
    .logo-container img {{ width: 100%; max-width: 500px; }}
    </style>
""", unsafe_allow_html=True)

LOGO_URL = "https://drive.google.com/thumbnail?id=1xKRvfMtlXd4vRpk_OlFE4MmkC3S7mZ4H&sz=w1000"
st.markdown(f'<div class="logo-container"><img src="{LOGO_URL}"></div>', unsafe_allow_html=True)

# --- 2. GESTIONE DATI (GSPREAD) ---
SHEET_ID = "1vfcB5CJ6J7Vgmw7JcDleR4MDEmw_kJTm4nXak1Lsg8E" 

def get_worksheet(sheet_name="Foglio1"):
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = None
    
    if "GCP_CREDENTIALS" in st.secrets:
        try:
            json_str = st.secrets["GCP_CREDENTIALS"].strip()
            try:
                creds_dict = json.loads(json_str, strict=False)
            except json.JSONDecodeError:
                creds_dict = json.loads(json_str.replace('\n', '\\n'), strict=False)

            if "private_key" in creds_dict:
                creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

            creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        except Exception as e:
            print(f"Errore lettura Secrets: {e}")

    if not creds and os.path.exists("credentials.json"):
        creds = Credentials.from_service_account_file("credentials.json", scopes=scope)
    
    if not creds:
        st.error("⚠️ ERRORE CREDENZIALI: Controlla Secrets o file locale.")
        st.stop()
        
    try:
        client = gspread.authorize(creds)
        sh = client.open_by_key(SHEET_ID)
        return sh.worksheet(sheet_name)
    except Exception as e:
        st.error(f"Errore GSpread: {e}")
        return None

def carica_dati(sheet_name="Foglio1"):
    wks = get_worksheet(sheet_name)
    if not wks: return pd.DataFrame()
    data = wks.get_all_records()
    return pd.DataFrame(data)

def salva_record(record, sheet_name="Foglio1", key_field="Codice", mode="new"):
    wks = get_worksheet(sheet_name)
    df = carica_dati(sheet_name)
    new_row = pd.DataFrame([record])
    if mode == "update" and not df.empty and key_field in df.columns:
        df = df[df[key_field].astype(str) != str(record[key_field])]
    df_final = pd.concat([df, new_row], ignore_index=True)
    wks.clear()
    wks.update([df_final.columns.values.tolist()] + df_final.values.tolist())
    st.toast("SALVATAGGIO RIUSCITO", icon="✅")

def elimina_record(valore_chiave, sheet_name="Foglio1", key_field="Codice"):
    wks = get_worksheet(sheet_name)
    df = carica_dati(sheet_name)
    if not df.empty and key_field in df.columns:
        df_final = df[df[key_field].astype(str) != str(valore_chiave)]
        wks.clear()
        wks.update([df_final.columns.values.tolist()] + df_final.values.tolist())
        st.toast(f"ELEMENTO ELIMINATO", icon="🗑️")
        time.sleep(1)
        st.rerun()

def elimina_record_batch(lista_codici, sheet_name="Foglio1", key_field="Codice"):
    """Elimina una lista di record in una sola operazione."""
    wks = get_worksheet(sheet_name)
    df = carica_dati(sheet_name)
    if not df.empty and key_field in df.columns:
        lista_str = [str(c) for c in lista_codici]
        df_final = df[~df[key_field].astype(str).isin(lista_str)]
        wks.clear()
        wks.update([df_final.columns.values.tolist()] + df_final.values.tolist())
        st.toast(f"ELIMINATI {len(lista_codici)} ELEMENTI", icon="🗑️")
        time.sleep(1)
        st.rerun()

def fmt_euro_it(valore):
    try:
        valore = float(valore)
        s = "{:,.2f}".format(valore)
        s = s.replace(",", "X").replace(".", ",").replace("X", ".")
        return f"€ {s}"
    except: return "€ 0,00"

def fmt_euro(valore):
    try: valore = float(valore)
    except: valore = 0.0
    return f"€ {valore:,.2f}"

def importa_excel_batch(uploaded_file):
    try:
        df_new = pd.read_excel(uploaded_file)
        df_existing = carica_dati("Foglio1")
        existing_codes = []
        if not df_existing.empty and "Codice" in df_existing.columns:
            existing_codes = df_existing["Codice"].astype(str).tolist()
        
        expected_cols = ["Codice", "Anno", "Nome Commessa", "Cliente", "P_IVA", "Sede", 
                         "Referente", "Tel Referente", "PM", "Portatore", "Settore", "Stato", 
                         "Totale Commessa", "Fatturato"]
        records_to_add = []
        count_skipped = 0
        
        for _, row in df_new.iterrows():
            if "Codice" not in row or pd.isna(row["Codice"]): continue
            codice = str(row["Codice"]).strip()
            if codice in existing_codes:
                count_skipped += 1
                continue
            rec = {}
            for col in expected_cols:
                val = row.get(col, "")
                if pd.isna(val): val = ""
                rec[col] = val
            rec["Portatore_Val"] = 0.0
            rec["Costi Società"] = 0.0
            rec["Utile Netto"] = 0.0
            rec["Data Inserimento"] = str(date.today())
            rec["Dati_JSON"] = json.dumps({
                "incassi": [], "soci": [], "collab": [], "spese": [], 
                "servizi": [], "percentages": {"portatore": 10, "societa": 10}
            })
            if "Dati_JSON" in row and pd.notna(row["Dati_JSON"]):
                 rec["Dati_JSON"] = row["Dati_JSON"]
            records_to_add.append(rec)
            
        if records_to_add:
            wks = get_worksheet("Foglio1")
            current_data = wks.get_all_values()
            headers = current_data[0] 
            rows_to_append = []
            for r in records_to_add:
                ordered_row = []
                for h in headers: ordered_row.append(r.get(h, ""))
                rows_to_append.append(ordered_row)
            wks.append_rows(rows_to_append)
            st.success(f"✅ Importati {len(records_to_add)} record. ({count_skipped} duplicati ignorati)")
            time.sleep(2)
            st.rerun()
        else:
            if count_skipped > 0: st.warning(f"⚠️ Nessun nuovo dato. {count_skipped} commesse esistevano già.")
            else: st.error("❌ Nessun dato valido trovato.")
    except Exception as e: st.error(f"Errore Import: {e}")

# --- 3. FORM COMMESSA (LOGICA SAVE-FIRST) ---
def render_commessa_form(data=None):
    is_edit = data is not None
    
    # --- HELPER PER NOMI ---
    def inverti_nome(nome_completo):
        if not nome_completo or " " not in nome_completo: return nome_completo
        parts = nome_completo.split()
        return " ".join(parts[::-1])

    if 'SOCI_OPZIONI' in globals():
        SOCI_OPZIONI_FMT = [inverti_nome(s) for s in SOCI_OPZIONI]

    # Inizializzazione Session State
    keys_to_init = ["form_cliente", "form_piva", "form_sede", "form_ref", "form_tel"]
    for k in keys_to_init:
        if k not in st.session_state: st.session_state[k] = ""
    if "perc_portatore" not in st.session_state: st.session_state["perc_portatore"] = 10
    if "perc_societa" not in st.session_state: st.session_state["perc_societa"] = 10

    # Caricamento Clienti
    df_clienti = carica_dati("Clienti")
    lista_clienti = []
    if not df_clienti.empty and "Denominazione" in df_clienti.columns:
        if "Attivo" in df_clienti.columns:
             clienti_attivi = df_clienti[df_clienti["Attivo"].astype(str).str.upper() == "TRUE"]
             lista_clienti = sorted(clienti_attivi["Denominazione"].unique().tolist())
        else:
             lista_clienti = sorted(df_clienti["Denominazione"].unique().tolist())

    # Gestione dati in modifica vs nuovo
    if is_edit:
        val_codice_originale = data["Codice"] 
        val_anno = int(data.get("Anno", 2024))
        val_oggetto = data.get("Nome Commessa", "") 
        try:
            val_servizi = []
            val_dettagli = ""
            if "Dati_JSON" in data and data["Dati_JSON"]:
                jdata = json.loads(data["Dati_JSON"])
                val_servizi = jdata.get("servizi", [])
                val_dettagli = jdata.get("dettagli_servizi", "") 
                if "percentages" in jdata:
                    st.session_state["perc_portatore"] = int(jdata["percentages"].get("portatore", 10))
                    st.session_state["perc_societa"] = int(jdata["percentages"].get("societa", 10))
        except: 
            val_servizi = []
            val_dettagli = ""

        if st.session_state.get("last_loaded_code") != val_codice_originale:
            st.session_state["form_cliente"] = data.get("Cliente", "") 
            st.session_state["form_piva"] = data.get("P_IVA", "")
            st.session_state["form_sede"] = data.get("Sede", "")
            st.session_state["form_ref"] = data.get("Referente", "")
            st.session_state["form_tel"] = data.get("Tel Referente", "")
            st.session_state["last_loaded_code"] = val_codice_originale
            if "stato_incassi" in st.session_state: del st.session_state["stato_incassi"]
    else:
        val_codice_originale = ""
        val_anno = date.today().year
        val_oggetto = ""
        val_servizi = []
        val_dettagli = ""
        if st.session_state.get("last_loaded_code") != "NEW":
             st.session_state["perc_portatore"] = 10
             st.session_state["perc_societa"] = 10
             st.session_state["last_loaded_code"] = "NEW"
             st.session_state["form_cliente"] = ""
             st.session_state["form_piva"] = ""
             st.session_state["form_sede"] = ""
             st.session_state["form_ref"] = ""
             st.session_state["form_tel"] = ""
    
    titolo = "MODIFICA SCHEDA" if is_edit else "NUOVA COMMESSA"
    st.markdown(f"<h1 style='text-align: center;'>{titolo}</h1>", unsafe_allow_html=True)
    st.markdown("---")

    with st.expander("01 // ANAGRAFICA COMMESSA", expanded=True):
        c1, c2, c3, c4 = st.columns([1.5, 1, 1.5, 1.5], gap="medium")
        
        with c2: anno = st.number_input("Anno", 2020, 2030, val_anno, key="f_anno")
        
        with c3:
            settori = ["RILIEVO", "ARCHEOLOGIA", "INTEGRATI"]
            val_sett_raw = data.get("Settore", "RILIEVO").upper() if is_edit else "RILIEVO"
            val_sett = settori.index(val_sett_raw) if val_sett_raw in settori else 0
            settore = st.selectbox("Settore ▼", settori, index=val_sett, key="f_settore")
        
        # --- FIX CODICE: AUTO-INCREMENTO E FORMATO ---
        with c1:
            mappa_settori = {"RILIEVO": "RIL", "ARCHEOLOGIA": "ARC", "INTEGRATI": "INT"}
            codice_display = val_codice_originale
            
            if is_edit and val_codice_originale:
                # --- LOGICA MODIFICA (Mantiene logica esistente) ---
                parts = re.split(r'[-/]', val_codice_originale)
                
                # Caso standard: PREFISSO / ANNO - NUMERO
                if len(parts) >= 3:
                    nuovo_prefisso = mappa_settori.get(settore, "GEN")
                    # Ricostruisce mantenendo il numero originale ma aggiornando il prefisso se cambia il settore
                    codice_display = f"{nuovo_prefisso}/{parts[1]}-{parts[2]}"
                
                # Caso fallback
                elif len(parts) >= 2:
                    nuovo_prefisso = mappa_settori.get(settore, "GEN")
                    codice_display = f"{nuovo_prefisso}/{parts[-1]}"

            elif not is_edit:
                # --- LOGICA NUOVO: AUTO-INCREMENTO ---
                prefisso = mappa_settori.get(settore, "RIL")
                base_code_search = f"{prefisso}/{anno}-" # Es. RIL/2024-
                
                # 1. Carica i dati per controllare l'ultimo numero
                df_check = carica_dati("Foglio1")
                max_num = 0
                
                if not df_check.empty and "Codice" in df_check.columns:
                    # Filtra solo i codici che non sono nulli e li converte in stringa
                    codici_esistenti = df_check["Codice"].dropna().astype(str)
                    
                    # Cerca i codici che matchano Prefisso e Anno corrente
                    for c in codici_esistenti:
                        if c.startswith(base_code_search):
                            try:
                                # Prende la parte dopo il trattino (es. "001")
                                suffix = c.split("-")[-1]
                                num = int(suffix)
                                if num > max_num:
                                    max_num = num
                            except:
                                pass # Ignora codici malformati
                
                # 2. Calcola il prossimo numero
                next_num = max_num + 1
                
                # 3. Genera il codice (es. RIL/2024-002)
                codice_display = f"{base_code_search}{next_num:03d}"

            st.text_input("Codice (Auto-aggiornato)", value=codice_display, disabled=True)
            codice_finale = codice_display

        with c4:
            idx_stato = ["APERTA", "CHIUSA", "IN ATTESA"].index(data["Stato"]) if is_edit and "Stato" in data else 0
            stato_header = st.selectbox("Stato Commessa ▼", ["APERTA", "CHIUSA", "IN ATTESA"], index=idx_stato)
        
        st.markdown("<br>", unsafe_allow_html=True)
        nome_commessa = st.text_input("Nome Commessa", value=val_oggetto)
        st.markdown("<br>", unsafe_allow_html=True)
        
        # --- MODIFICA LISTA SERVIZI ---
        SERVIZI_LIST = sorted([
            "Archeologia Preventiva",
            "Assistenza Archeologica",
            "Campionamento malte",
            "Drone",
            "Indagine Diagnostica",
            "Inquadramento Archeologico Preliminare",
            "Modellazione 3D",
            "Modellazione BIM",
            "Relazione Archeologica",
            "Relazione Storica",
            "Restituzione CAD",
            "Restituzione Fotopiani",
            "Ricerca Archeologica",
            "Rilievo Fotogrammetrico",
            "Rilievo GPS",
            "Rilievo Laser Scanner",
            "Rilievo Topografico",
            "RTI",
            "Scavo Archeologico",
            "Sorveglianza Archeologica",
            "Stampa 3D",
            "VIARCH",
            "Virtual Tour",
            "VPIA"
        ])

        c_serv, c_dett = st.columns([2, 1])
        with c_serv: servizi_scelti = st.multiselect("Servizi Richiesti", SERVIZI_LIST, default=val_servizi)
        with c_dett: dettagli_servizi = st.text_input("Dettagli", value=val_dettagli)

    with st.expander("02 // COMMITTENZA", expanded=True):
        def on_cliente_change():
            sel = st.session_state["sel_cliente_box"]
            if sel and sel != "➕ NUOVO CLIENTE" and sel in lista_clienti:
                row = df_clienti[df_clienti["Denominazione"] == sel].iloc[0]
                st.session_state["form_piva"] = row["P_IVA"]
                st.session_state["form_sede"] = row["Sede"]
                st.session_state["form_ref"] = row["Referente"]
                st.session_state["form_tel"] = str(row.get("Telefono", ""))
            elif sel == "➕ NUOVO CLIENTE":
                st.session_state["form_piva"] = ""
                st.session_state["form_sede"] = ""
                st.session_state["form_ref"] = ""
                st.session_state["form_tel"] = ""

        try:
            current_cli = st.session_state.get("form_cliente", "")
            display_list = ["➕ NUOVO CLIENTE"] + lista_clienti
            if current_cli and current_cli not in display_list: display_list.append(current_cli)
            idx_cli = display_list.index(current_cli) if current_cli in display_list else 0
        except: idx_cli = 0

        sel_val = st.selectbox("Seleziona Cliente", display_list, index=idx_cli, key="sel_cliente_box", on_change=on_cliente_change)
        if sel_val == "➕ NUOVO CLIENTE":
            nome_cliente_finale = st.text_input("Nome Nuovo Cliente *", value="")
        else: nome_cliente_finale = sel_val

        c1, c2 = st.columns(2)
        p_iva = c1.text_input("P.IVA / CF", value=st.session_state["form_piva"])
        indirizzo = c2.text_input("Sede", value=st.session_state["form_sede"])
        c3, c4 = st.columns(2)
        referente = c3.text_input("Referente", value=st.session_state["form_ref"])
        tel_ref = c4.text_input("Tel", value=st.session_state["form_tel"])

        st.session_state["form_cliente"] = nome_cliente_finale
        st.session_state["form_piva"] = p_iva
        st.session_state["form_sede"] = indirizzo
        st.session_state["form_ref"] = referente
        st.session_state["form_tel"] = tel_ref

    with st.expander("03 // COORDINAMENTO", expanded=True):
        c1, c2 = st.columns(2)
        curr_pm = data.get("PM", SOCI_OPZIONI[0]) if is_edit else SOCI_OPZIONI[0]
        curr_pm_fmt = inverti_nome(curr_pm) 
        idx_pm = SOCI_OPZIONI_FMT.index(curr_pm_fmt) if curr_pm_fmt in SOCI_OPZIONI_FMT else 0
        coordinatore = inverti_nome(c1.selectbox("Project Manager ▼", SOCI_OPZIONI_FMT, index=idx_pm))

        curr_soc = data.get("Portatore", SOCI_OPZIONI[0]) if is_edit else SOCI_OPZIONI[0]
        curr_soc_fmt = inverti_nome(curr_soc)
        idx_soc = SOCI_OPZIONI_FMT.index(curr_soc_fmt) if curr_soc_fmt in SOCI_OPZIONI_FMT else 0
        portatore = inverti_nome(c2.selectbox("Socio Portatore ▼", SOCI_OPZIONI_FMT, index=idx_soc))

    # --- DATAFRAMES ---
    if "stato_incassi" not in st.session_state:
        df_init = pd.DataFrame([{"Voce": "Acconto", "Importo netto €": 0.0, "IVA %": 22, "Importo lordo €": 0.0, "Stato": "Previsto", "Data": date.today(), "Note": ""}])
        if is_edit and "Dati_JSON" in data and data["Dati_JSON"]:
            try:
                jdata = json.loads(data["Dati_JSON"])
                if "incassi" in jdata:
                    df_temp = pd.DataFrame(jdata["incassi"])
                    if not df_temp.empty:
                        if "Data" in df_temp.columns: df_temp["Data"] = pd.to_datetime(df_temp["Data"], errors='coerce').dt.date
                        if "Importo" in df_temp.columns and "Importo netto €" not in df_temp.columns: df_temp = df_temp.rename(columns={"Importo": "Importo netto €"})
                        if "IVA %" not in df_temp.columns: df_temp["IVA %"] = 22
                        df_temp["Importo lordo €"] = df_temp["Importo netto €"] * (1 + df_temp["IVA %"]/100)
                        df_init = df_temp
            except: pass
        st.session_state["stato_incassi"] = df_init
    
    df_soci_def = pd.DataFrame([{"Socio": SOCI_OPZIONI_FMT[0], "Mansione": "Coordinamento", "Importo": 0.0, "Stato": "Da pagare", "Data": None, "Note": ""}])
    df_collab_def = pd.DataFrame([{"Collaboratore": "Esterno", "Mansione": "Rilievo", "Importo": 0.0, "Stato": "Da pagare", "Data": None, "Note": ""}])
    df_spese_def = pd.DataFrame([{"Voce": "Varie", "Importo": 0.0, "Stato": "Da pagare", "Data": None, "Note": ""}])

    if is_edit and "Dati_JSON" in data and data["Dati_JSON"]:
        try:
            jdata = json.loads(data["Dati_JSON"])
            if "soci" in jdata: 
                df_temp = pd.DataFrame(jdata["soci"])
                if "Ruolo" in df_temp.columns: df_temp = df_temp.rename(columns={"Ruolo": "Mansione"})
                if "Socio" in df_temp.columns: df_temp["Socio"] = df_temp["Socio"].apply(inverti_nome)
                expected = ["Socio", "Mansione", "Importo", "Stato", "Data", "Note"]
                for c in expected:
                     if c not in df_temp.columns: df_temp[c] = "" if c != "Importo" else 0.0
                if "Data" in df_temp.columns: df_temp["Data"] = pd.to_datetime(df_temp["Data"], errors='coerce').dt.date
                df_soci_def = df_temp[expected]

            if "collab" in jdata: 
                df_temp = pd.DataFrame(jdata["collab"])
                if "Nome" in df_temp.columns: df_temp = df_temp.rename(columns={"Nome": "Collaboratore"})
                expected = ["Collaboratore", "Mansione", "Importo", "Stato", "Data", "Note"]
                for c in expected:
                     if c not in df_temp.columns: df_temp[c] = "" if c != "Importo" else 0.0
                if "Data" in df_temp.columns: df_temp["Data"] = pd.to_datetime(df_temp["Data"], errors='coerce').dt.date
                df_collab_def = df_temp[expected]

            if "spese" in jdata: 
                df_temp = pd.DataFrame(jdata["spese"])
                expected = ["Voce", "Importo", "Stato", "Data", "Note"]
                for c in expected:
                     if c not in df_temp.columns: df_temp[c] = "" if c != "Importo" else 0.0
                if "Data" in df_temp.columns: df_temp["Data"] = pd.to_datetime(df_temp["Data"], errors='coerce').dt.date
                df_spese_def = df_temp[expected]
        except: pass

    # 04. PIANO ECONOMICO
    with st.expander("04 // PIANO ECONOMICO", expanded=True):
        
        # --- 1. FUNZIONI DI FORMATTAZIONE E PULIZIA ---
        
        # Formattazione VISIVA per i box totali (es. 1000.50 -> "€ 1.000,50")
        fmt_euro = lambda x: f"€ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        
        # Funzione CRITICA: converte qualsiasi stringa "1.234,56" in float 1234.56
        def converti_valuta_italiana(val):
            if pd.isna(val) or str(val).strip() == "": return 0.0
            
            # Se è già un numero (float o int), lo teniamo così com'è
            if isinstance(val, (float, int)):
                return float(val)
            
            s = str(val).replace("€", "").strip()
            
            # Caso specifico: se l'utente scrive "1.628,64"
            # 1. Rimuoviamo i punti delle migliaia (.)
            # 2. Sostituiamo la virgola dei decimali (,) con il punto standard (.)
            if "," in s:
                s = s.replace(".", "")  # Via i separatori migliaia (1.628,64 -> 1628,64)
                s = s.replace(",", ".") # Virgola diventa punto (1628,64 -> 1628.64)
            else:
                # Se non c'è virgola, potrebbe essere "1628" o "1.628" (inglese?)
                # Assumiamo che se ci sono punti senza virgole in un contesto italiano, siano migliaia.
                # Ma per sicurezza, se il numero di decimali dopo il punto è strano, stiamo attenti.
                # Per semplicità in questo contesto: Rimuoviamo il punto se sembra un separatore migliaia.
                if s.count(".") >= 1:
                     s = s.replace(".", "") 

            try:
                return float(s)
            except:
                return 0.0

        # --- 2. PREPARAZIONE DATI PRIMA DELL'EDITOR ---
        # Puliamo preventivamente i dati nel session state per assicurarci che siano float puri
        # Questo evita che l'editor riceva stringhe ambigue.
        if "stato_incassi" in st.session_state:
            st.session_state["stato_incassi"]["Importo netto €"] = st.session_state["stato_incassi"]["Importo netto €"].apply(converti_valuta_italiana)

        col_cfg = {
            "Voce": st.column_config.SelectboxColumn("Voce", options=["Acconto", "Saldo"], required=True),
            # step=0.01 aiuta l'editor a capire che vogliamo i decimali
            "Importo netto €": st.column_config.NumberColumn(format="€ %.2f", required=True, step=0.01),
            "IVA %": st.column_config.SelectboxColumn(options=[0, 22], required=True),
            "Importo lordo €": st.column_config.NumberColumn(format="€ %.2f", disabled=True),
            "Stato": st.column_config.SelectboxColumn(options=["Previsto", "Fatturato"], required=True),
            "Data": st.column_config.DateColumn(format="DD/MM/YYYY"),
            "Note": st.column_config.TextColumn()
        }
        order_cols = ["Voce", "Importo netto €", "Importo lordo €", "IVA %", "Stato", "Data", "Note"]
        
        # --- 3. EDITOR ---
        edited_incassi = st.data_editor(
            st.session_state["stato_incassi"], 
            num_rows="dynamic", 
            column_config=col_cfg, 
            column_order=order_cols, 
            use_container_width=True, 
            key="ed_inc"
        )
        
        # --- 4. CALCOLI E SALVATAGGIO ---
        ricalcolo = edited_incassi.copy()
        
        # Riaplichiamo la conversione in uscita per sicurezza (se l'utente ha incollato testo strano)
        ricalcolo["Importo netto €"] = ricalcolo["Importo netto €"].apply(converti_valuta_italiana)
        
        # Calcolo matematico (ora siamo sicuri che siano float corretti)
        ricalcolo["Importo lordo €"] = ricalcolo["Importo netto €"] * (1 + (ricalcolo["IVA %"] / 100))
        
        # Verifica differenze (con tolleranza float per evitare loop infiniti su 0.0000001)
        # Usiamo .round(2) per confrontare cifre monetarie
        diff_check = False
        try:
            # Confronto manuale sui valori numerici chiave
            netto_old = st.session_state["stato_incassi"]["Importo netto €"].apply(converti_valuta_italiana).round(2)
            netto_new = ricalcolo["Importo netto €"].round(2)
            if not netto_old.equals(netto_new) or len(ricalcolo) != len(st.session_state["stato_incassi"]):
                diff_check = True
            else:
                 # Check altre colonne
                 cols_no_calc = [c for c in ricalcolo.columns if c not in ["Importo netto €", "Importo lordo €"]]
                 if not ricalcolo[cols_no_calc].equals(st.session_state["stato_incassi"][cols_no_calc]):
                     diff_check = True
        except:
            diff_check = True

        if diff_check:
            st.session_state["stato_incassi"] = ricalcolo
            st.rerun()

        # Somme (sicure perché convertite)
        tot_net = ricalcolo["Importo netto €"].sum()
        tot_lordo = ricalcolo["Importo lordo €"].sum()
        
        df_fatt = ricalcolo.copy()
        fatturato_netto = df_fatt[df_fatt['Stato'].astype(str) == 'Fatturato']['Importo netto €'].sum()

        k1, k2 = st.columns(2)
        with k1: st.markdown(f"<div class='total-box-standard'><div class='total-label'>Totale Netto</div><div class='total-value'>{fmt_euro(tot_net)}</div></div>", unsafe_allow_html=True)
        with k2: st.markdown(f"<div class='total-box-standard'><div class='total-label'>Totale Lordo</div><div class='total-value'>{fmt_euro(tot_lordo)}</div></div>", unsafe_allow_html=True)

    # 05. COSTI
    with st.expander("05 // COSTI & RETRIBUZIONI", expanded=True):
        top_metrics = st.container()
        
        # Funzione helper per applicare la config comune
        def get_money_col():
             return st.column_config.NumberColumn(format="€ %.2f", required=True, step=0.01)

        st.markdown("### SOCI")
        soci_cfg = {
            "Socio": st.column_config.SelectboxColumn(options=SOCI_OPZIONI_FMT, required=True),
            "Importo": get_money_col(),
            "Stato": st.column_config.SelectboxColumn(options=["Da pagare", "Conteggiato", "Fatturato"], required=True),
            "Data": st.column_config.DateColumn(format="DD/MM/YYYY")
        }
        # Applichiamo pulizia preventiva anche qui se necessario
        if "Importo" in df_soci_def.columns:
             df_soci_def["Importo"] = df_soci_def["Importo"].apply(converti_valuta_italiana)
             
        edited_soci = st.data_editor(df_soci_def, num_rows="dynamic", column_config=soci_cfg, use_container_width=True, key="ed_soc")

        st.markdown("### COLLABORATORI")
        collab_cfg = {
            "Importo": get_money_col(),
            "Stato": st.column_config.SelectboxColumn(options=["Da pagare", "Fatturato"], required=True),
            "Data": st.column_config.DateColumn(format="DD/MM/YYYY")
        }
        if "Importo" in df_collab_def.columns:
             df_collab_def["Importo"] = df_collab_def["Importo"].apply(converti_valuta_italiana)
             
        edited_collab = st.data_editor(df_collab_def, num_rows="dynamic", column_config=collab_cfg, use_container_width=True, key="ed_col")

        st.markdown("### SPESE VARIE")
        spese_cfg = {
            "Importo": get_money_col(),
            "Stato": st.column_config.SelectboxColumn(options=["Da pagare", "Pagato"], required=True),
            "Data": st.column_config.DateColumn(format="DD/MM/YYYY")
        }
        if "Importo" in df_spese_def.columns:
             df_spese_def["Importo"] = df_spese_def["Importo"].apply(converti_valuta_italiana)
             
        edited_spese = st.data_editor(df_spese_def, num_rows="dynamic", column_config=spese_cfg, use_container_width=True, key="ed_sp")
        
        # Somme con conversione di sicurezza sull'output dell'editor
        sum_soci = edited_soci["Importo"].apply(converti_valuta_italiana).sum()
        sum_collab = edited_collab["Importo"].apply(converti_valuta_italiana).sum()
        sum_spese = edited_spese["Importo"].apply(converti_valuta_italiana).sum()
        
        with top_metrics:
            b1, b2, b3, b4 = st.columns(4)
            with b1:
                val_portatore = tot_net * (st.session_state["perc_portatore"] / 100.0)
                st.markdown(f"<div class='total-box-desat'><div class='total-label'>PORTATORE</div><div class='total-value'>{fmt_euro(val_portatore)}</div></div>", unsafe_allow_html=True)
                new_perc_port = st.number_input("Perc %", 0, 100, int(st.session_state["perc_portatore"]), key="np")
                if new_perc_port != st.session_state["perc_portatore"]:
                    st.session_state["perc_portatore"] = new_perc_port
                    st.rerun()
            with b2:
                val_societa = tot_net * (st.session_state["perc_societa"] / 100.0)
                st.markdown(f"<div class='total-box-desat'><div class='total-label'>SOCIETA'</div><div class='total-value'>{fmt_euro(val_societa)}</div></div>", unsafe_allow_html=True)
                new_perc_soc = st.number_input("Perc %", 0, 100, int(st.session_state["perc_societa"]), key="ns")
                if new_perc_soc != st.session_state["perc_societa"]:
                    st.session_state["perc_societa"] = new_perc_soc
                    st.rerun()
            with b3: 
                val_iva = tot_lordo - tot_net
                st.markdown(f"<div class='total-box-desat'><div class='total-label'>IVA</div><div class='total-value'>{fmt_euro(val_iva)}</div></div>", unsafe_allow_html=True)
            with b4: 
                val_utili = tot_net - (sum_soci + sum_collab + sum_spese)
                color = "#ff4b4b" if val_utili < 0 else "#ffffff"
                st.markdown(f"<div class='total-box-desat'><div class='total-label'>UTILI</div><div class='total-value' style='color:{color};'>{fmt_euro(val_utili)}</div></div>", unsafe_allow_html=True)

    st.markdown("---")
    
    # --- SALVATAGGIO: LOGICA CORRETTA ---
    if st.button("SALVA / AGGIORNA SCHEDA", use_container_width=True):
        if not nome_cliente_finale or not nome_commessa: 
            st.error("Nome Commessa e Nome Cliente sono obbligatori")
        else:
            # Gestione Nuovo Cliente "al volo"
            if nome_cliente_finale not in lista_clienti:
                st.toast(f"Nuovo cliente: aggiungo '{nome_cliente_finale}'...", icon="👤")
                rec_cliente = {"Denominazione": nome_cliente_finale, "P_IVA": p_iva, "Sede": indirizzo, "Referente": referente, "Telefono": tel_ref, "Attivo": "TRUE", "Settore": "ALTRO"}
                salva_record(rec_cliente, "Clienti", "Denominazione", "new")
            
            # Preparazione dati JSON
            soci_to_save = edited_soci.copy()
            soci_to_save["Socio"] = soci_to_save["Socio"].apply(inverti_nome)
            json_data = json.dumps({
                "incassi": st.session_state["stato_incassi"].to_dict('records'), 
                "soci": soci_to_save.to_dict('records'),
                "collab": edited_collab.to_dict('records'), 
                "spese": edited_spese.to_dict('records'),
                "servizi": servizi_scelti, "dettagli_servizi": dettagli_servizi,
                "percentages": { "portatore": st.session_state["perc_portatore"], "societa": st.session_state["perc_societa"] }
            }, default=str)
            
            tot_uscite = val_portatore + val_societa + sum_soci + sum_collab + sum_spese
            utile_netto = tot_net - tot_uscite

            rec = {
                "Codice": codice_finale, "Anno": anno, "Nome Commessa": nome_commessa, "Cliente": nome_cliente_finale,
                "P_IVA": p_iva, "Sede": indirizzo, "Referente": referente, "Tel Referente": tel_ref,
                "PM": coordinatore, "Portatore": portatore, "Settore": settore, "Stato": stato_header, 
                "Totale Commessa": tot_net, "Fatturato": fatturato_netto,
                "Portatore_Val": val_portatore, "Costi Società": val_societa, "Utile Netto": utile_netto,
                "Data Inserimento": str(date.today()), "Dati_JSON": json_data
            }

            # -----------------------------------------------------------
            # LOGICA SALVATAGGIO DIFFERENZIATA
            # -----------------------------------------------------------
            
            # CASO 1: MODIFICA DEL CODICE (es. cambio settore)
            if is_edit and codice_finale != val_codice_originale:
                salva_record(rec, "Foglio1", "Codice", mode="new")
                elimina_record(val_codice_originale, "Foglio1", "Codice")
                st.success(f"Commessa aggiornata da {val_codice_originale} a {codice_finale}")
                time.sleep(1)
                return True # Chiude e torna alla dashboard

            # CASO 2: UPDATE O NUOVO INSERIMENTO
            else:
                mode_save = "update" if is_edit else "new"
                salva_record(rec, "Foglio1", "Codice", mode=mode_save)
                
                if is_edit:
                    # SE STIAMO MODIFICANDO -> Torna alla dashboard
                    st.success("Commessa aggiornata!")
                    time.sleep(1)
                    return True 
                else:
                    # SE E' NUOVA -> Pulisce tutto e rimane sul form
                    st.success("Nuova commessa salvata! Resetto il form...")
                    time.sleep(1)
                    
                    # RESET VARIABILI DI STATO PER NUOVO INSERIMENTO
                    keys_to_clear = ["form_cliente", "form_piva", "form_sede", "form_ref", "form_tel", "stato_incassi", "sel_cliente_box"]
                    for k in keys_to_clear:
                        if k in st.session_state: del st.session_state[k]
                    
                    # Imposta last_loaded_code per forzare il refresh come 'NEW'
                    st.session_state["last_loaded_code"] = "RESET"
                    
                    # Ricarica la pagina (eseguirà render con campi vuoti)
                    st.rerun()

    if is_edit:
        with st.expander("⚠️ ZONA PERICOLO"):
            if st.button("ELIMINA DEFINITIVAMENTE", key="btn_del"): 
                elimina_record(codice_finale, "Foglio1", "Codice")
                st.success("Commessa eliminata.")
                time.sleep(1)
                return True # Chiude anche in caso di eliminazione

    return False

# --- 4. CLIENTI PAGE (DEFINIZIONE FUNZIONE) ---
def render_clienti_page():
    st.markdown("<h2 style='text-align: center;'>ARCHIVIO CLIENTI</h2>", unsafe_allow_html=True)
    st.markdown("---")
    
    # --- GESTIONE STATO SELEZIONE ---
    if "cliente_selezionato" not in st.session_state:
        st.session_state["cliente_selezionato"] = None

    c_form, c_list = st.columns([1, 2], gap="large")

    df = carica_dati("Clienti")
    nomi = sorted(df["Denominazione"].unique().tolist()) if not df.empty else []

    # --- COLONNA SINISTRA: FORM DI INSERIMENTO/MODIFICA ---
    with c_form:
        st.markdown("<h3 style='text-align: center;'>SCHEDA CLIENTE</h3>", unsafe_allow_html=True)
        
        # Gestione indice per sincronizzare Selectbox
        idx_sel = 0
        current_sel = st.session_state["cliente_selezionato"]
        if current_sel in nomi:
            idx_sel = nomi.index(current_sel) + 1 
        
        # Selectbox principale
        sel = st.selectbox("Cerca o Modifica:", [""] + nomi, index=idx_sel, key="sb_cliente_main")
        
        # Aggiornamento stato
        if sel != st.session_state["cliente_selezionato"]:
            st.session_state["cliente_selezionato"] = sel
            
        # Recupero Dati
        d = df[df["Denominazione"] == sel].iloc[0].to_dict() if sel and not df.empty else {}
        
        # Tasto Nuovo
        if sel:
            if st.button("➕ NUOVO CLIENTE (Deseleziona)", use_container_width=True):
                st.session_state["cliente_selezionato"] = None
                st.rerun()

        st.markdown("---")

        with st.form("frm_cli"):
            den = st.text_input("Denominazione *", value=d.get("Denominazione", ""))
            
            c1, c2 = st.columns(2)
            piva = c1.text_input("P.IVA", value=d.get("P_IVA", ""))
            sede = c2.text_input("Sede", value=d.get("Sede", ""))
            
            c3, c4 = st.columns(2)
            ref = c3.text_input("Referente", value=d.get("Referente", ""))
            tel = c4.text_input("Tel", value=d.get("Telefono", ""))
            
            mail = st.text_input("Email", value=d.get("Email", ""))
            
            c5, c6 = st.columns(2)
            lista_soci = SOCI_OPZIONI if 'SOCI_OPZIONI' in globals() else ["Socio A", "Socio B"]
            
            idx_cont = lista_soci.index(d.get("Contatto_SISMA")) + 1 if d.get("Contatto_SISMA") in lista_soci else 0
            cont = c5.selectbox("Contatto SISMA", [""] + lista_soci, index=idx_cont)
            
            sets = ["ARCHEOLOGIA", "RILIEVO", "INTEGRATI", "ALTRO"]
            idx_set = sets.index(d.get("Settore")) if d.get("Settore") in sets else 3
            sett = c6.selectbox("Settore", sets, index=idx_set)
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            c_att, c_dis = st.columns(2)
            curr_active = str(d.get("Attivo", "TRUE")).upper() == "TRUE"
            chk_active = c_att.checkbox("Attivo", value=curr_active)
            chk_inactive = c_dis.checkbox("Non Attivo", value=not curr_active)
            
            note = st.text_area("Note", value=d.get("Note", ""))
            
            if st.form_submit_button("💾 SALVA CLIENTE", type="primary", use_container_width=True):
                if not den: 
                    st.error("Nome obbligatorio")
                else:
                    final_state = "FALSE" if chk_inactive else ("TRUE" if chk_active else "FALSE")
                    rec = {
                        "Denominazione": den, 
                        "P_IVA": piva, 
                        "Sede": sede, 
                        "Referente": ref, 
                        "Telefono": tel, 
                        "Email": mail, 
                        "Contatto_SISMA": cont, 
                        "Settore": sett, 
                        "Attivo": final_state, 
                        "Note": note
                    }
                    salva_record(rec, "Clienti", "Denominazione", "update" if sel else "new")
                    st.success("Cliente salvato!")
                    time.sleep(1)
                    st.rerun()

    # --- COLONNA DESTRA: LISTA E IMPORT/EXPORT ---
    with c_list:
        st.markdown("<h3 style='text-align: center;'>RUBRICA</h3>", unsafe_allow_html=True)
        
        # --- SEZIONE IMPORT / EXPORT ---
        with st.expander("📂 IMPORT / EXPORT MASSIVO (Excel)", expanded=False):
            k1, k2 = st.columns(2)
            colonne_export = ["Denominazione", "P_IVA", "Sede", "Referente", "Telefono", "Email", "Contatto_SISMA", "Settore", "Attivo", "Note"]

            # EXPORT
            with k1:
                st.markdown("**1. Scarica Excel**")
                if not df.empty:
                    df_export = df.copy()
                    for col in colonne_export:
                        if col not in df_export.columns:
                            df_export[col] = ""
                    df_export = df_export[colonne_export]
                else:
                    df_export = pd.DataFrame(columns=colonne_export)

                buffer_cli = io.BytesIO()
                with pd.ExcelWriter(buffer_cli, engine='xlsxwriter') as writer_cli:
                    df_export.to_excel(writer_cli, index=False, sheet_name='Clienti')
                
                st.download_button("📥 SCARICA EXCEL", data=buffer_cli, file_name=f"Clienti_Export_{date.today()}.xlsx", mime="application/vnd.ms-excel", use_container_width=True)

            # IMPORT
            with k2:
                st.markdown("**2. Importa Excel**")
                uploaded_file = st.file_uploader("Carica file .xlsx", type=["xlsx"], label_visibility="collapsed")
                
                if uploaded_file is not None and st.button("🔄 AVVIA IMPORTAZIONE", use_container_width=True):
                    try:
                        df_new = pd.read_excel(uploaded_file, dtype=str).fillna("")
                        if "Denominazione" not in df_new.columns:
                            st.error("Manca colonna 'Denominazione'")
                        else:
                            count = 0
                            progress_bar = st.progress(0)
                            total = len(df_new)
                            for index, row in df_new.iterrows():
                                rec_import = row.to_dict()
                                if rec_import.get("Denominazione") and str(rec_import["Denominazione"]).strip() != "":
                                    if "Attivo" not in rec_import or rec_import["Attivo"] == "":
                                        rec_import["Attivo"] = "TRUE"
                                    salva_record(rec_import, "Clienti", "Denominazione", "update")
                                    count += 1
                                if total > 0:
                                    progress_bar.progress((index + 1) / total)
                            time.sleep(0.5)
                            st.success(f"Importati {count} clienti!")
                            time.sleep(1.5)
                            st.rerun()
                    except Exception as e:
                        st.error(f"Errore: {e}")

        st.divider()

        # --- VISUALIZZAZIONE TABELLA (SOLO CANCELLAZIONE) ---
        if not df.empty:
            df_view = df.copy()
            df_view["Attivo"] = df_view["Attivo"].astype(str).str.upper() == "TRUE"
            
            # Aggiungiamo SOLO la colonna Cancella
            df_view.insert(0, "Cancella", False)

            target_cols = ["Cancella", "Denominazione", "P_IVA", "Referente", "Telefono", "Email", "Settore", "Attivo"]
            final_cols = [c for c in target_cols if c in df_view.columns]
            
            # Data Editor
            edited_df = st.data_editor(
                df_view[final_cols], 
                column_config={
                    "Cancella": st.column_config.CheckboxColumn("🗑️", width="small", default=False),
                    "Attivo": st.column_config.CheckboxColumn(disabled=True),
                    "Denominazione": st.column_config.TextColumn(width="medium"),
                }, 
                # Tutto disabilitato tranne Cancella
                disabled=[c for c in final_cols if c != "Cancella"], 
                use_container_width=True, 
                hide_index=True,
                height=600,
                key="editor_clienti"
            )

            # --- LOGICA CANCELLAZIONE ---
            rows_to_delete = edited_df[edited_df["Cancella"] == True]
            if not rows_to_delete.empty:
                st.warning(f"⚠️ Vuoi eliminare {len(rows_to_delete)} clienti?")
                if st.button("🔴 CONFERMA ELIMINAZIONE", use_container_width=True):
                    for index, row in rows_to_delete.iterrows():
                        nome_da_cancellare = row["Denominazione"]
                        elimina_record(nome_da_cancellare, "Clienti", "Denominazione")
                        
                        # Reset form se eliminiamo il selezionato
                        if st.session_state["cliente_selezionato"] == nome_da_cancellare:
                            st.session_state["cliente_selezionato"] = None
                            
                    st.success("Cancellazione eseguita.")
                    time.sleep(1)
                    st.rerun()

# --- 5. DASHBOARD & IMPORT ---
def render_dashboard():
    # Carica i dati aggiornati
    df = carica_dati("Foglio1")
    
    st.markdown("<h2 style='text-align: center;'>DASHBOARD ANALITICA</h2>", unsafe_allow_html=True)

    # --- 1. FUNZIONE PER I CALCOLI (Restituisce un FLOAT puro) ---
    def pulisci_per_calcoli(val):
        if pd.isna(val) or str(val).strip() == "": 
            return 0.0
        
        # Se è già numero, converti in float e basta
        if isinstance(val, (float, int)):
            return float(val)
            
        s = str(val).strip()
        # Rimuovi simbolo euro e spazi
        s = s.replace("€", "").strip()
        
        try:
            # Rimuovi eventuali spazi interni (es. "1 000")
            s = s.replace(" ", "")
            
            # GESTIONE FORMATI MISTI
            # Caso 1: Formato Italiano (1.234,56) -> Ci sono sia punti che virgole
            if "." in s and "," in s:
                s = s.replace(".", "")   # Via i punti delle migliaia
                s = s.replace(",", ".")  # La virgola diventa il punto decimale Python
            
            # Caso 2: Solo virgola (1234,56) -> Diventa 1234.56
            elif "," in s:
                s = s.replace(",", ".")
            
            # Caso 3: Solo punto (1.234 o 1234.56)
            # Qui si rischia confusione. Assumiamo che se ci sono 3 cifre dopo il punto sia migliaia (1.000), 
            # altrimenti decimale (123.45). Ma per sicurezza, se stiamo parlando di soldi,
            # spesso i punti sono solo separatori visivi in input manuali italiani.
            elif "." in s:
                parts = s.split(".")
                # Se l'ultima parte ha lunghezza diversa da 2, probabilmente era un separatore migliaia (es 1.000)
                # NOTA: Questa è una stima euristica.
                if len(parts) > 1 and len(parts[-1]) != 2: 
                     s = s.replace(".", "")
            
            return float(s)
        except:
            return 0.0

    # --- 2. FUNZIONE VISIVA BLINDATA (Stringa Fissa "€ X.XXX,XX") ---
    def forza_testo_visivo(val):
        # 1. Ottieni il numero puro
        val_float = pulisci_per_calcoli(val)
        
        # 2. Formatta in stile USA forzando ESATTAMENTE 2 decimali (.2f)
        # Es. 1500 -> "1,500.00"
        # Es. 1500.5 -> "1,500.50"
        base = "{:,.2f}".format(val_float)
        
        # 3. Inverti i separatori per lo stile Italiano
        # "1,500.00" -> "1.500,00"
        finale = base.replace(",", "X").replace(".", ",").replace("X", ".")
        
        return f"€ {finale}"

    # --- GESTIONE STATO MODIFICA ---
    if "edit_codice_commessa" not in st.session_state:
        st.session_state["edit_codice_commessa"] = None

    def attiva_modifica():
        selezione = st.session_state.get("trigger_selezione_commessa")
        if selezione:
            st.session_state["edit_codice_commessa"] = selezione.split(" | ")[0]
            st.session_state["trigger_selezione_commessa"] = ""

    # --- MODALITÀ MODIFICA ---
    if st.session_state["edit_codice_commessa"] is not None:
        codice_corrente = st.session_state["edit_codice_commessa"]
        record_corrente = df[df["Codice"].astype(str) == str(codice_corrente)]
        
        if not record_corrente.empty:
            dati_commessa = record_corrente.iloc[0].to_dict()
            esito_salvataggio = render_commessa_form(dati_commessa)
            
            if esito_salvataggio == True:
                st.session_state["edit_codice_commessa"] = None
                st.rerun()
            
            st.markdown("---")
            if st.button("🔙 CHIUDI E TORNA ALLA DASHBOARD", key="btn_close_edit"):
                st.session_state["edit_codice_commessa"] = None
                st.rerun()
        else:
            st.warning("⚠️ Record non trovato.")
            time.sleep(1.5)
            st.session_state["edit_codice_commessa"] = None
            st.rerun()
        return

    # --- VISUALIZZAZIONE NORMALE ---
    if df.empty: 
        st.info("Nessun dato in archivio.")
    else:
        # --- CALCOLI KPI ---
        def calcola_totali_kpi(row):
            t_netto = 0.0
            t_lordo = 0.0
            raw_json = row.get("Dati_JSON", "")
            if pd.isna(raw_json) or str(raw_json).strip() == "": return pd.Series([0.0, 0.0])

            try:
                dati = json.loads(str(raw_json))
                incassi = dati.get("incassi", [])
                for item in incassi:
                    dati_reali = item
                    if isinstance(item, dict) and "Stato" not in item:
                        for k, v in item.items():
                            if isinstance(v, dict) and "Stato" in v:
                                dati_reali = v; break 
                    stato = str(dati_reali.get("Stato", "")).lower().strip()
                    if "fatturato" in stato:
                        t_netto += pulisci_per_calcoli(dati_reali.get("Importo netto €", 0))
                        t_lordo += pulisci_per_calcoli(dati_reali.get("Importo lordo €", 0))
            except: return pd.Series([0.0, 0.0])
            return pd.Series([t_netto, t_lordo])

        df["Anno"] = pd.to_numeric(df["Anno"], errors='coerce').fillna(0).astype(int)
        df[["_Fatt_Netto_Calc", "_Fatt_Lordo_Calc"]] = df.apply(calcola_totali_kpi, axis=1)
        
        # --- FILTRI ---
        anni_disponibili = sorted(df["Anno"].unique().tolist(), reverse=True)
        if 0 in anni_disponibili: anni_disponibili.remove(0)
        anni_opts = ["TOTALE"] + [str(x) for x in anni_disponibili]
        
        c_filt, c_void = st.columns([1, 3])
        sel_anno_str = c_filt.selectbox("Filtra Dashboard e Archivio per Anno:", anni_opts)
        
        if sel_anno_str != "TOTALE":
            df_filtered = df[df["Anno"] == int(sel_anno_str)].copy()
        else:
            df_filtered = df.copy()

        # --- KPI CARDS ---
        palette = ["#14505f", "#1d6677", "#287d8f"]
        cols = st.columns(3)
        settori = ["RILIEVO", "ARCHEOLOGIA", "INTEGRATI"]
        df_filtered["Settore_Norm"] = df_filtered["Settore"].astype(str).str.upper().str.strip()

        for i, (nome, col) in enumerate(zip(settori, cols)):
            d_s = df_filtered[df_filtered["Settore_Norm"] == nome]
            # Usa la funzione blindata per le card
            t_n = forza_testo_visivo(d_s['_Fatt_Netto_Calc'].sum()).replace("€ ", "")
            t_l = forza_testo_visivo(d_s['_Fatt_Lordo_Calc'].sum()).replace("€ ", "")
            
            with col:
                st.markdown(f"""
                <div style="background-color:{palette[i]}; padding:15px; border-radius:6px; text-align:center; color:white;">
                    <div style="font-weight:bold; font-size:16px; border-bottom:1px solid rgba(255,255,255,0.2); padding-bottom:5px;">{nome}</div>
                    <div style="display:flex; justify-content:space-around; margin-top:10px;">
                        <div><div style="font-size:10px;">NETTO</div><div style="font-size:18px; font-weight:bold;">€ {t_n}</div></div>
                        <div><div style="font-size:10px;">LORDO</div><div style="font-size:18px;">€ {t_l}</div></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("<h2 style='text-align: center;'>GESTIONE COMMESSE</h2>", unsafe_allow_html=True)
    
    # --- SELETTORE MODIFICA ---
    if not df.empty:
        opts = []
        for _, row in df.iterrows():
             nome_show = str(row["Nome Commessa"])
             cli_show = str(row["Cliente"]) if row["Cliente"] else "N/D"
             opts.append(f"{row['Codice']} | {cli_show} - {nome_show}")
        
        st.info("✏️ Per **MODIFICARE** una commessa, selezionala dal menu qui sotto.")
        st.selectbox("Seleziona per Modifica:", [""] + opts, key="trigger_selezione_commessa", on_change=attiva_modifica)

    st.markdown("<br>", unsafe_allow_html=True)
    
    # --- GESTIONE ARCHIVIO ---
    if "select_all_state" not in st.session_state: st.session_state["select_all_state"] = False

    c_title, c_actions = st.columns([1, 1], gap="large")
    with c_title: 
        st.markdown("<h3 style='text-align: left; margin-top:0;'>ARCHIVIO</h3>", unsafe_allow_html=True)
        if not df.empty:
            c_btn1, c_btn2, c_rest = st.columns([0.4, 0.4, 0.2])
            with c_btn1:
                if st.button("Seleziona Tutto", use_container_width=True):
                    st.session_state["select_all_state"] = True
                    st.rerun()
            with c_btn2:
                if st.button("Deseleziona", use_container_width=True):
                    st.session_state["select_all_state"] = False
                    st.rerun()

    with c_actions:
        tab_backup, tab_import = st.tabs(["📤 ESPORTA / BACKUP", "📥 IMPORTA DA EXCEL"])
        with tab_backup:
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                cols_to_drop = [c for c in ["_Fatt_Netto_Calc", "_Fatt_Lordo_Calc", "Settore_Norm", "Anno_Int", "Fatturato"] if c in df.columns]
                df.drop(columns=cols_to_drop, errors='ignore').to_excel(writer, index=False, sheet_name='Archivio_SISMA')
            st.download_button("SCARICA EXCEL COMPLETO", data=buffer, file_name=f"Backup_SISMA_{date.today()}.xlsx", mime="application/vnd.ms-excel", use_container_width=True)
        with tab_import:
            st.info("Formato richiesto: Codice, Anno, Nome Commessa, Cliente, Totale Commessa...", icon="ℹ️")
            template_df = pd.DataFrame(columns=["Codice", "Anno", "Nome Commessa", "Cliente", "P_IVA", "Sede", "Referente", "Tel Referente", "PM", "Portatore", "Settore", "Stato", "Totale Commessa"])
            buf_tpl = io.BytesIO()
            with pd.ExcelWriter(buf_tpl, engine='xlsxwriter') as writer: template_df.to_excel(writer, index=False, sheet_name='Template')
            st.download_button("1. Scarica Modello Vuoto", data=buf_tpl, file_name="Template_SISMA.xlsx", use_container_width=True)
            uploaded_file = st.file_uploader("2. Carica Excel compilato", type=["xlsx", "xls"])
            if uploaded_file and st.button("AVVIA IMPORTAZIONE", type="primary", use_container_width=True):
                importa_excel_batch(uploaded_file)

    # --- TABELLA GESTIONALE ---
    if not df.empty:
        df_to_edit = df_filtered.copy()
        
        if "Elimina" not in df_to_edit.columns: df_to_edit.insert(0, "Elimina", st.session_state["select_all_state"])
        else: df_to_edit["Elimina"] = st.session_state["select_all_state"]

        cols_to_hide = ["_Fatt_Netto_Calc", "_Fatt_Lordo_Calc", "Fatturato", "Settore_Norm"] 
        df_to_edit = df_to_edit.drop(columns=[c for c in cols_to_hide if c in df_to_edit.columns], errors='ignore')

        # --- FIX ASSOLUTO: FORZATURA STRINGA ---
        if "Totale Commessa" in df_to_edit.columns:
            # 1. Applico la funzione che genera "€ 1.000,00" (sempre 2 decimali)
            df_to_edit["Totale Commessa"] = df_to_edit["Totale Commessa"].apply(forza_testo_visivo)
            # 2. Converto esplicitamente la colonna in Object/Stringa per Pandas
            df_to_edit["Totale Commessa"] = df_to_edit["Totale Commessa"].astype(str)

        cols_to_show = ["Elimina", "Codice", "Stato", "Anno", "Cliente", "Nome Commessa", "Settore", "Totale Commessa"]
        actual_cols = [c for c in cols_to_show if c in df_to_edit.columns]

        # Configurazione Tabella
        edited_df = st.data_editor(
            df_to_edit[actual_cols],
            column_config={
                "Elimina": st.column_config.CheckboxColumn("❌ Elimina", default=False, width="small"),
                
                # TextColumn: Streamlit mostrerà la stringa ESATTAMENTE come l'abbiamo creata noi
                "Totale Commessa": st.column_config.TextColumn(
                    "Totale Commessa",
                    help="Importo fisso (Visualizzazione Testo)",
                    width="medium"
                ), 
            },
            # Disabilita modifica su Totale Commessa perché ora è testo complesso
            disabled=[c for c in actual_cols if c != "Elimina"], 
            use_container_width=True,
            hide_index=True,
            height=500,
            key="archive_editor"
        )

        rows_to_delete = edited_df[edited_df["Elimina"] == True]
        if not rows_to_delete.empty:
            st.error(f"⚠️ ATTENZIONE: Hai selezionato {len(rows_to_delete)} commesse per l'ELIMINAZIONE.")
            if st.button(f"🗑️ CONFERMA CANCELLAZIONE DI {len(rows_to_delete)} COMMESSE", type="primary"):
                codici_da_eliminare = rows_to_delete["Codice"].tolist()
                elimina_record_batch(codici_da_eliminare, "Foglio1", "Codice")
                
# --- 6. ORGANIGRAMMA ---
def render_organigramma():
    st.markdown("<h2 style='text-align: center;'>ORGANIGRAMMA AZIENDALE</h2>", unsafe_allow_html=True)
    st.markdown("---")
    
    soci = [
        {"Nome": "ARRIGHETTI ANDREA", "Quota": 1540.0, "Perc": "19.25"},
        {"Nome": "BERTOCCI STEFANO", "Quota": 1540.0, "Perc": "19.25"},
        {"Nome": "LUMINI ANDREA", "Quota": 840.0, "Perc": "10.50"},
        {"Nome": "MARASCO LORENZO", "Quota": 840.0, "Perc": "10.50"},
        {"Nome": "MINUTOLI GIOVANNI", "Quota": 860.0, "Perc": "10.75"},
        {"Nome": "PANCANI GIOVANNI", "Quota": 1540.0, "Perc": "19.25"},
        {"Nome": "REPOLE MARCO", "Quota": 840.0, "Perc": "10.50"}
    ]
    df_s = pd.DataFrame(soci)
    
    st.markdown("<div class='org-header'>LIVELLO 1: SOCIETARIO</div>", unsafe_allow_html=True)
    cols_soci = st.columns(7)
    for i, s in enumerate(sorted(soci, key=lambda x: x['Nome'])):
        with cols_soci[i % 7]:
            st.markdown(f"""
            <div class="org-card" style="padding: 15px 5px; min-height: 140px;">
                <div style="font-size: 15px; font-weight: bold; color: #FFF; margin-bottom: 5px;">{s['Nome'].replace(' ', '<br>')}</div>
                <div style="font-size: 22px; color: #427e72; font-weight: bold;">{s['Perc']}%</div>
                <div style="font-size: 13px; color: #888;">€ {s['Quota']:,.0f}</div>
            </div>""", unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # LAYOUT 50% - 50%
    c_table, c_chart = st.columns([1, 1], gap="large")
    
    with c_table:
        st.markdown("""
        <div style="background-color: #111; border: 1px solid #333; border-radius: 4px; padding: 30px; height: 100%; font-family: 'Helvetica Neue', sans-serif; margin-bottom: 50px;">
            <div style="color: #427e72; font-size: 20px; font-weight: bold; margin-bottom: 20px; border-bottom: 1px solid #333; padding-bottom: 15px; text-transform: uppercase;">DATI SOCIETARI</div>
            <table style="width: 100%; border-collapse: collapse; color: #DDD; font-size: 15px;">
                <tr style="border-bottom: 1px solid #222;">
                    <td style="padding: 10px 20px; font-weight: bold; color: #888; width: 25%; border-right: 1px solid #222;">Ragione sociale</td>
                    <td style="padding: 10px 20px;">SISMA - Sistemi Integrati di Monitoraggio Architettonico s.r.l.</td>
                </tr>
                <tr style="border-bottom: 1px solid #222;">
                    <td style="padding: 10px 20px; font-weight: bold; color: #888; border-right: 1px solid #222;">Sede Legale</td>
                    <td style="padding: 10px 20px;">Piazza Togliatti, 40, Scandicci (FI) – 50018</td>
                </tr>
                <tr style="border-bottom: 1px solid #222;">
                    <td style="padding: 10px 20px; font-weight: bold; color: #888; border-right: 1px solid #222;">CF/P.IVA</td>
                    <td style="padding: 10px 20px;">06557660484</td>
                </tr>
                <tr style="border-bottom: 1px solid #222;">
                    <td style="padding: 10px 20px; font-weight: bold; color: #888; border-right: 1px solid #222;">Cod. Destinatario</td>
                    <td style="padding: 10px 20px;">KRRH6B9</td>
                </tr>
                <tr style="border-bottom: 1px solid #222;">
                    <td style="padding: 10px 20px; font-weight: bold; color: #888; border-right: 1px solid #222;">Codice ATECO</td>
                    <td style="padding: 10px 20px;">74.90.99 - altre attività professionali nca</td>
                </tr>
                <tr style="border-bottom: 1px solid #222;">
                    <td style="padding: 10px 20px; font-weight: bold; color: #888; border-right: 1px solid #222;">Capitale Soc.</td>
                    <td style="padding: 10px 20px;">8000,00 €</td>
                </tr>
                <tr style="border-bottom: 1px solid #222;">
                    <td style="padding: 10px 20px; font-weight: bold; color: #888; border-right: 1px solid #222;">Inizio Attività</td>
                    <td style="padding: 10px 20px;">09/06/2015</td>
                </tr>
                <tr style="border-bottom: 1px solid #222;">
                    <td style="padding: 10px 20px; font-weight: bold; color: #888; border-right: 1px solid #222;">N. REA</td>
                    <td style="padding: 10px 20px;">FI – 637912</td>
                </tr>
                <tr style="border-bottom: 1px solid #222;">
                    <td style="padding: 10px 20px; font-weight: bold; color: #888; border-right: 1px solid #222;">PIC</td>
                    <td style="padding: 10px 20px;">919267546</td>
                </tr>
                <tr style="border-bottom: 1px solid #222;">
                    <td style="padding: 10px 20px; font-weight: bold; color: #888; border-right: 1px solid #222;">PEC</td>
                    <td style="padding: 10px 20px;">sisma2015@pec.cgn.it</td>
                </tr>
                <tr style="border-bottom: 1px solid #222;">
                    <td style="padding: 10px 20px; font-weight: bold; color: #888; border-right: 1px solid #222;">E-mail</td>
                    <td style="padding: 10px 20px;">info@sisma-srl.com / archeologia@sisma-srl.com</td>
                </tr>
                <tr>
                    <td style="padding: 10px 20px; font-weight: bold; color: #888; border-right: 1px solid #222;">Sito web</td>
                    <td style="padding: 10px 20px;">www.sisma-srl.com</td>
                </tr>
            </table>
        </div>
        """, unsafe_allow_html=True)

    with c_chart:
        petrol_palette = ['#082a33', '#0c3a47', '#14505f', '#1d6677', '#287d8f', '#3695a7', '#46adbf']
        chart = alt.Chart(df_s).mark_arc(innerRadius=120, outerRadius=190).encode(
            theta=alt.Theta("Quota", stack=True),
            color=alt.Color("Nome", legend=None, scale=alt.Scale(range=petrol_palette)),
            tooltip=["Nome", "Quota", "Perc"]
        ).properties(height=600).configure(background='#000000').configure_view(strokeWidth=0)
        st.altair_chart(chart, use_container_width=True)

    c_cda, c_op, c_cs = st.columns(3, gap="medium")
    with c_cda: 
        st.markdown("""<div class="card-mid"><div class="card-subtitle">CONSIGLIO DI<br>AMMINISTRAZIONE</div>
        <div class="org-row"><span class="role-label">Presidente</span><div class="name-text">LORENZO MARASCO</div></div>
        <div class="org-row"><span class="role-label">Consigliere</span><div class="name-text">ANDREA ARRIGHETTI</div></div>
        <div class="org-row"><span class="role-label">Consigliere</span><div class="name-text">MARCO REPOLE</div></div></div>""", unsafe_allow_html=True)
    with c_op: 
        st.markdown("""<div class="card-mid"><div class="card-subtitle">COMITATO<br>ESECUTIVO</div>
        <div class="org-row">
            <span class="role-label">ARCHEOLOGIA</span>
            <div class="name-text">ANDREA ARRIGHETTI</div>
            <div class="name-text">LORENZO MARASCO</div>
        </div>
        <div class="org-row">
            <span class="role-label">RILIEVO</span>
            <div class="name-text">ANDREA LUMINI</div>
            <div class="name-text">MARCO REPOLE</div>
        </div></div>""", unsafe_allow_html=True)
    with c_cs:
         st.markdown("""<div class="card-mid"><div class="card-subtitle">COMITATO<br>SCIENTIFICO</div>
        <div class="org-row"><span class="role-label">Membro</span><div class="name-text">STEFANO BERTOCCI</div></div>
        <div class="org-row"><span class="role-label">Membro</span><div class="name-text">GIOVANNI MINUTOLI</div></div>
        <div class="org-row"><span class="role-label">Membro</span><div class="name-text">GIOVANNI PANCANI</div></div></div>""", unsafe_allow_html=True)

    st.markdown("<div class='org-header'>LIVELLO 2: GESTIONALE</div>", unsafe_allow_html=True)
    st.markdown("""<div style="display:flex; justify-content:center; margin-bottom:20px; width:100%;">
            <div class="org-card" style="width: 400px; padding: 30px;">
                <span class="role-label">DIREZIONE GENERALE - RELAZIONI ESTERNE</span><div class="name-text" style="font-weight:bold;">LORENZO MARASCO</div>
            </div></div>""", unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3)
    with c1: st.markdown('<div class="org-card"><span class="role-label">CONTABILITA\' - IT - HR</span><div class="name-text">ANDREA LUMINI</div></div>', unsafe_allow_html=True)
    with c2: st.markdown('<div class="org-card"><span class="role-label">BUSINESS - R&D</span><div class="name-text">ANDREA ARRIGHETTI</div></div>', unsafe_allow_html=True)
    with c3: st.markdown('<div class="org-card"><span class="role-label">GARE - MARKETING</span><div class="name-text">MARCO REPOLE</div></div>', unsafe_allow_html=True)

    # --- LIVELLO 3 OPERATIVO ---
    st.markdown("<div class='org-header' style='font-size: 18px;'>LIVELLO 3: OPERATIVO</div>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4, gap="small")
    with c1: 
        st.markdown("""
        <div class="org-card" style="min-height: 200px;">
            <span class="role-label">PROJECT MANAGER</span>
            <div class="card-subtitle" style="margin: 5px 0; font-size: 14px;">ARCHEOLOGIA PREVENTIVA</div>
            <div class="name-text">LORENZO MARASCO</div>
        </div>
        """, unsafe_allow_html=True)
    with c2: 
        st.markdown("""
        <div class="org-card" style="min-height: 200px;">
            <span class="role-label">PROJECT MANAGER</span>
            <div class="card-subtitle" style="margin: 5px 0; font-size: 14px;">ARCHEOLOGIA DELL'ARCHITETTURA</div>
            <div class="name-text">ANDREA ARRIGHETTI</div>
        </div>
        """, unsafe_allow_html=True)
    with c3: 
        st.markdown("""
        <div class="org-card" style="min-height: 200px;">
            <span class="role-label">PROJECT MANAGER</span>
            <div class="card-subtitle" style="margin: 5px 0; font-size: 14px;">RILIEVO DIGITALE & BIM</div>
            <div class="name-text">ANDREA LUMINI</div>
        </div>
        """, unsafe_allow_html=True)
    with c4: 
        st.markdown("""
        <div class="org-card" style="min-height: 200px;">
            <span class="role-label">PROJECT MANAGER</span>
            <div class="card-subtitle" style="margin: 5px 0; font-size: 14px;">RILIEVO DIGITALE & 3D</div>
            <div class="name-text">MARCO REPOLE</div>
        </div>
        """, unsafe_allow_html=True)

# --- 7. ROUTING ---
with st.sidebar:
    st.markdown("### MENU STUDIO")
    st.markdown("---")
    scelta = st.radio("VAI A:", [":: DASHBOARD & ARCHIVIO", ":: NUOVA COMMESSA", ":: CLIENTI", ":: SOCIETA'"], index=0)
    st.markdown("---")

if "DASHBOARD" in scelta: render_dashboard()
elif "NUOVA COMMESSA" in scelta: render_commessa_form(None)
elif "CLIENTI" in scelta: render_clienti_page()
elif "SOCIETA'" in scelta: render_organigramma()





























































