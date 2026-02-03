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

# --- MODIFICA 1: Aggiunto decoratore Cache ---
@st.cache_data(ttl=10)
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
    
    # --- MODIFICA 2: Pulisci cache dopo salvataggio ---
    carica_dati.clear()
    
    st.toast("SALVATAGGIO RIUSCITO", icon="✅")

def elimina_record(valore_chiave, sheet_name="Foglio1", key_field="Codice"):
    wks = get_worksheet(sheet_name)
    df = carica_dati(sheet_name)
    if not df.empty and key_field in df.columns:
        df_final = df[df[key_field].astype(str) != str(valore_chiave)]
        wks.clear()
        wks.update([df_final.columns.values.tolist()] + df_final.values.tolist())
        
        # --- MODIFICA 3: Pulisci cache dopo eliminazione ---
        carica_dati.clear()
        
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
        
        # --- MODIFICA 4: Pulisci cache dopo eliminazione batch ---
        carica_dati.clear()
        
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

# --- FUNZIONE IMPORTAZIONE SMART (MULTI-FOGLIO) ---
def importa_excel_batch(file_excel):
    try:
        # Legge tutti i fogli del file Excel
        xls = pd.read_excel(file_excel, sheet_name=None)
        
        # Verifica se è il nuovo formato Smart
        if "Commesse" in xls and "Piano_Economico" in xls and "Costi_Operativi" in xls:
            df_main = xls["Commesse"]
            df_piano = xls["Piano_Economico"]
            df_costi = xls["Costi_Operativi"]
            
            # Normalizza colonne Codice per evitare errori di tipo
            df_main["Codice"] = df_main["Codice"].astype(str)
            df_piano["Codice"] = df_piano["Codice"].astype(str)
            df_costi["Codice"] = df_costi["Codice"].astype(str)
            
            count = 0
            prog_bar = st.progress(0)
            
            for idx, row in df_main.iterrows():
                codice = row["Codice"]
                
                # 1. Ricostruisci Piano Economico (Incassi)
                incassi_rows = df_piano[df_piano["Codice"] == codice].to_dict('records')
                # Pulizia: rimuovi la colonna Codice dai dati JSON (è ridondante) e gestisci le date
                clean_incassi = []
                for item in incassi_rows:
                    item.pop("Codice", None)
                    # Converti date in stringa per JSON
                    for d_col in ["Data Saldo", "Data Fattura"]:
                        if d_col in item and pd.notnull(item[d_col]):
                            item[d_col] = str(item[d_col]).split(" ")[0]
                    clean_incassi.append(item)

                # 2. Ricostruisci Costi (Soci, Collab, Spese)
                costi_subset = df_costi[df_costi["Codice"] == codice]
                
                soci_rows = []
                collab_rows = []
                spese_rows = []
                
                for _, c_row in costi_subset.iterrows():
                    c_dict = c_row.to_dict()
                    c_dict.pop("Codice", None)
                    tipo = c_dict.pop("Tipo_Riga", "Spese") # Socio, Collab, Spese
                    
                    # Converti date
                    for d_col in ["Data Saldo", "Data Fattura"]:
                        if d_col in c_dict and pd.notnull(c_dict[d_col]):
                            c_dict[d_col] = str(c_dict[d_col]).split(" ")[0]

                    if tipo == "Socio": soci_rows.append(c_dict)
                    elif tipo == "Collab": collab_rows.append(c_dict)
                    else: spese_rows.append(c_dict)

                # 3. Recupera Metadati JSON (Percentuali, Servizi) dalle colonne Excel se presenti
                perc_port = row.get("Perc_Portatore", 10)
                perc_soc = row.get("Perc_Societa", 10)
                servizi_str = row.get("Lista_Servizi", "")
                dettagli_srv = row.get("Dettagli_Servizi", "")
                
                lista_servizi = [s.strip() for s in str(servizi_str).split(",")] if servizi_str and pd.notnull(servizi_str) else []

                # 4. Assembla il JSON finale
                json_completo = {
                    "incassi": clean_incassi,
                    "soci": soci_rows,
                    "collab": collab_rows,
                    "spese": spese_rows,
                    "servizi": lista_servizi,
                    "dettagli_servizi": str(dettagli_srv),
                    "percentages": {"portatore": int(perc_port) if pd.notnull(perc_port) else 10, "societa": int(perc_soc) if pd.notnull(perc_soc) else 10}
                }
                
                # 5. Prepara il record per GSheets
                record_dict = row.to_dict()
                # Rimuovi colonne helper create per l'export
                cols_to_remove = ["Perc_Portatore", "Perc_Societa", "Lista_Servizi", "Dettagli_Servizi"]
                for c in cols_to_remove:
                    record_dict.pop(c, None)
                
                record_dict["Dati_JSON"] = json.dumps(json_completo, default=str)
                
                # Salva (usa la funzione salva_record esistente)
                salva_record(record_dict, "Foglio1", "Codice", mode="update")
                
                count += 1
                prog_bar.progress(min(count / len(df_main), 1.0))
                
            st.success(f"✅ Importazione completata! Aggiornate {count} commesse.")
            time.sleep(2)
            st.rerun()
            
        else:
            # Fallback: Vecchia importazione (File singolo)
            st.warning("⚠️ File non in formato 'Smart Export'. Tento importazione standard...")
            df_new = pd.read_excel(file_excel)
            count = 0
            for index, row in df_new.iterrows():
                record = row.to_dict()
                # Se c'è un JSON grezzo, usalo, altrimenti lascia vuoto
                if "Dati_JSON" not in record or pd.isna(record["Dati_JSON"]):
                    record["Dati_JSON"] = "{}"
                salva_record(record, "Foglio1", "Codice", mode="update")
                count += 1
            st.success(f"Importazione standard completata ({count} record).")
            
    except Exception as e:
        st.error(f"Errore durante l'importazione: {e}")

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
             if "stato_incassi" in st.session_state: del st.session_state["stato_incassi"]
    
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
        
        # --- BLOCCO CODICE (MODIFICATO: EDITABILE) ---
        with c1:
            mappa_settori = {"RILIEVO": "RIL", "ARCHEOLOGIA": "ARC", "INTEGRATI": "INT"}
            prefisso_target = mappa_settori.get(settore, "GEN")
            
            # --- CALCOLO SUGGERIMENTO AUTOMATICO ---
            # Calcoliamo un suggerimento SOLO se:
            # 1. È una nuova commessa (e non abbiamo ancora scritto nulla)
            # 2. In modifica: se l'utente cambia Settore o Anno rispetto all'originale
            
            suggerimento_codice = ""
            calcola_nuovo = False
            
            if not is_edit:
                calcola_nuovo = True
            elif is_edit and val_codice_originale:
                # Recupera prefisso e anno dal codice originale per vedere se sono cambiati
                parts_old = re.split(r'[-/]', val_codice_originale)
                prefisso_old = parts_old[0] if len(parts_old) > 0 else ""
                
                try: anno_old_code = int(parts_old[1]) if len(parts_old) > 1 else val_anno
                except: anno_old_code = val_anno

                # Se cambia la struttura (Anno o Settore), ricalcolo il suggerimento
                if prefisso_old != prefisso_target or anno_old_code != anno:
                    calcola_nuovo = True
                else:
                    suggerimento_codice = val_codice_originale # Mantengo quello attuale

            if calcola_nuovo:
                # Logica di ricerca prossimo numero libero
                base_code_search = f"{prefisso_target}/{anno}-" 
                
                # OPZIONALE: Se usi st.cache_data su carica_dati, questa riga pulisce la cache
                # per essere sicuri di leggere l'ultimo numero salvato un secondo fa.
                st.cache_data.clear() 
                
                df_check = carica_dati("Foglio1") # Ora ricarica sicuramente da Google Sheets
                
                max_num = 0
                if not df_check.empty and "Codice" in df_check.columns:
                    codici_esistenti = df_check["Codice"].dropna().astype(str)
                    for c in codici_esistenti:
                        if c.startswith(base_code_search):
                            try:
                                suffix = c.split("-")[-1]
                                num = int(suffix)
                                if num > max_num: max_num = num
                            except: pass
                
                next_num = max_num + 1
                suggerimento_codice = f"{base_code_search}{next_num:03d}"

            # --- WIDGET EDITABILE ---
            # Usiamo session_state per gestire il valore che può essere sovrascritto dall'utente
            # Se è la prima volta che entriamo o se cambia il calcolo automatico, aggiorniamo il valore
            
            key_codice = "input_codice_manuale"
            
            # Se stiamo ricalcolando il suggerimento (es. cambio settore), forziamo il valore nel widget
            # Ma solo se l'utente non sta attivamente scrivendo (gestito ricaricando solo agli eventi chiave)
            if "last_suggested_code" not in st.session_state:
                st.session_state["last_suggested_code"] = ""

            # Se il suggerimento calcolato è diverso dall'ultimo mostrato, aggiorniamo il campo
            if suggerimento_codice != st.session_state["last_suggested_code"]:
                 st.session_state[key_codice] = suggerimento_codice
                 st.session_state["last_suggested_code"] = suggerimento_codice

            # Render del campo EDITABILE (disabled=False)
            codice_finale = st.text_input("Codice Commessa (Editabile)", key=key_codice, help="Puoi modificare manualmente questo codice se necessario.")

        with c4:
            idx_stato = ["APERTA", "CHIUSA"].index(data["Stato"]) if is_edit and "Stato" in data else 0
            stato_header = st.selectbox("Stato Commessa ▼", ["APERTA", "CHIUSA"], index=idx_stato)
        
        st.markdown("<br>", unsafe_allow_html=True)
        nome_commessa = st.text_input("Nome Commessa", value=val_oggetto)
        st.markdown("<br>", unsafe_allow_html=True)
        dettagli_servizi = st.text_input("Dettagli Commessa", value=val_dettagli)
        st.markdown("<br>", unsafe_allow_html=True)
        SERVIZI_LIST = sorted([
            "Archeologia dell'Architettura", "Assistenza Archeologica", "Campionamento Malte", "Drone",
            "Indagine Diagnostica", "Inquadramento Archeologico Preliminare", "Modellazione 3D",
            "Modellazione BIM", "Progettazione e Assistenza Archeologica", "Relazione Archeologica", "Relazione Storica", "Restituzione CAD",
            "Restituzione Materico", "Restituzione Fotopiani", "Restituzione Quadro Fessurativo",
            "Ricerca Archeologica", "Rilievo Fotogrammetrico", "Rilievo GPS", "Rilievo Laser Scanner",
            "Rilievo Topografico", "RTI", "Saggi e Trincee", "Scavo Archeologico",
            "Sorveglianza Archeologica", "Stampa 3D", "VIARCH", "Virtual Tour", "VPIA"
        ])
        servizi_scelti = st.multiselect("Servizi Richiesti", SERVIZI_LIST, default=val_servizi)

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

    # --- FUNZIONE NORMALIZZAZIONE COLONNE (AGGIORNATA PER EVITARE CRASH) ---
    def normalizza_colonne_df(df):
        if "Data" in df.columns: df = df.rename(columns={"Data": "Data Saldo"})
        if "Note" in df.columns: df = df.rename(columns={"Note": "Fattura"})
        
        # Assicura che le colonne esistano
        if "Data Fattura" not in df.columns: df["Data Fattura"] = None
        if "Data Saldo" not in df.columns: df["Data Saldo"] = None
        if "Fattura" not in df.columns: df["Fattura"] = ""
        
        # FIX: Conversione sicura a datetime64[ns] senza .dt.date per evitare tipi misti
        for col in ["Data Saldo", "Data Fattura"]:
            df[col] = pd.to_datetime(df[col], errors='coerce')
        return df

    # --- INIZIALIZZAZIONE DATAFRAMES ---
    if "stato_incassi" in st.session_state:
        df_old = st.session_state["stato_incassi"]
        if "Data" in df_old.columns or "Note" in df_old.columns or "Data Fattura" not in df_old.columns:
            st.session_state["stato_incassi"] = normalizza_colonne_df(df_old)

    cols_incassi_std = ["Voce", "Importo netto €", "IVA %", "Importo lordo €", "Stato", "Data Saldo", "Data Fattura", "Fattura"]
    
    if "stato_incassi" not in st.session_state:
        df_init = pd.DataFrame([{"Voce": "Acconto", "Importo netto €": 0.0, "IVA %": 22, "Importo lordo €": 0.0, "Stato": "Previsto", "Data Saldo": None, "Data Fattura": None, "Fattura": ""}])
        if is_edit and "Dati_JSON" in data and data["Dati_JSON"]:
            try:
                jdata = json.loads(data["Dati_JSON"])
                if "incassi" in jdata:
                    df_temp = pd.DataFrame(jdata["incassi"])
                    if not df_temp.empty:
                        if "Importo" in df_temp.columns: df_temp = df_temp.rename(columns={"Importo": "Importo netto €"})
                        if "IVA %" not in df_temp.columns: df_temp["IVA %"] = 22
                        df_temp["Importo lordo €"] = df_temp["Importo netto €"] * (1 + df_temp["IVA %"]/100)
                        df_temp = normalizza_colonne_df(df_temp)
                        for c in cols_incassi_std:
                            if c not in df_temp.columns: df_temp[c] = None
                        df_init = df_temp[cols_incassi_std]
            except: pass
        # Normalizziamo anche l'inizializzazione per garantire i tipi corretti
        st.session_state["stato_incassi"] = normalizza_colonne_df(df_init)

    cols_costi_std = ["Importo", "Stato", "Data Saldo", "Data Fattura", "Fattura"] 
    
    df_soci_def = pd.DataFrame([{"Socio": SOCI_OPZIONI_FMT[0], "Mansione": "Coordinamento", "Importo": 0.0, "Stato": "Da pagare", "Data Saldo": None, "Data Fattura": None, "Fattura": ""}])
    df_collab_def = pd.DataFrame([{"Collaboratore": "Esterno", "Mansione": "Rilievo", "Importo": 0.0, "Stato": "Da pagare", "Data Saldo": None, "Data Fattura": None, "Fattura": ""}])
    df_spese_def = pd.DataFrame([{"Voce": "Varie", "Importo": 0.0, "Stato": "Da pagare", "Data Saldo": None, "Data Fattura": None, "Fattura": ""}])

    if is_edit and "Dati_JSON" in data and data["Dati_JSON"]:
        try:
            jdata = json.loads(data["Dati_JSON"])
            def load_cost_table(key_name, df_default, extra_cols=[]):
                if key_name in jdata:
                    df_t = pd.DataFrame(jdata[key_name])
                    if not df_t.empty:
                        if key_name == "soci":
                            if "Ruolo" in df_t.columns: df_t = df_t.rename(columns={"Ruolo": "Mansione"})
                            if "Socio" in df_t.columns: df_t["Socio"] = df_t["Socio"].apply(inverti_nome)
                        if key_name == "collab" and "Nome" in df_t.columns:
                            df_t = df_t.rename(columns={"Nome": "Collaboratore"})
                        df_t = normalizza_colonne_df(df_t)
                        target_cols = extra_cols + cols_costi_std
                        for c in target_cols:
                            if c not in df_t.columns: df_t[c] = 0.0 if c == "Importo" else (None if "Data" in c else "")
                        return df_t[target_cols]
                return df_default

            df_soci_def = load_cost_table("soci", df_soci_def, ["Socio", "Mansione"])
            df_collab_def = load_cost_table("collab", df_collab_def, ["Collaboratore", "Mansione"])
            df_spese_def = load_cost_table("spese", df_spese_def, ["Voce"])
        except: pass
    
    # Assicuriamo che anche le tabelle di default siano normalizzate come datetime
    df_soci_def = normalizza_colonne_df(df_soci_def)
    df_collab_def = normalizza_colonne_df(df_collab_def)
    df_spese_def = normalizza_colonne_df(df_spese_def)

    # 04. PIANO ECONOMICO (RENDER)
    with st.expander("04 // PIANO ECONOMICO", expanded=True):
        fmt_euro = lambda x: f"€ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        def converti_valuta_italiana(val):
            if pd.isna(val) or str(val).strip() == "": return 0.0
            if isinstance(val, (float, int)): return float(val)
            s = str(val).replace("€", "").strip()
            if "," in s: s = s.replace(".", "").replace(",", ".")
            else: 
                if s.count(".") >= 1: s = s.replace(".", "")
            try: return float(s)
            except: return 0.0

        if "stato_incassi" in st.session_state:
            st.session_state["stato_incassi"]["Importo netto €"] = st.session_state["stato_incassi"]["Importo netto €"].apply(converti_valuta_italiana)

        # --- MODIFICA WIDTH: SETTATO A "MEDIUM" PER TUTTE LE COLONNE ---
        col_cfg = {
            "Voce": st.column_config.SelectboxColumn("Voce", options=["Acconto", "Saldo"], required=True, width="medium"),
            "Importo netto €": st.column_config.NumberColumn(format="€ %.2f", required=True, step=0.01, width="medium"),
            "IVA %": st.column_config.SelectboxColumn(options=[0, 22], required=True, width="medium"),
            "Importo lordo €": st.column_config.NumberColumn(format="€ %.2f", disabled=True, width="medium"),
            "Stato": st.column_config.SelectboxColumn(options=["Previsto", "Fatturato"], required=True, width="medium"),
            "Data Saldo": st.column_config.DateColumn("Data Saldo", format="DD/MM/YYYY", width="medium"),
            "Data Fattura": st.column_config.DateColumn("Data Fattura", format="DD/MM/YYYY", width="medium"),
            "Fattura": st.column_config.TextColumn("N. Fattura", width="medium")
        }
        
        edited_incassi = st.data_editor(
            st.session_state["stato_incassi"], 
            num_rows="dynamic", 
            column_config=col_cfg, 
            column_order=cols_incassi_std,
            use_container_width=True, 
            key="ed_inc"
        )
        
        ricalcolo = edited_incassi.copy()
        # Normalizziamo anche il ritorno dell'editor per sicurezza
        ricalcolo = normalizza_colonne_df(ricalcolo)
        
        ricalcolo["Importo netto €"] = ricalcolo["Importo netto €"].apply(converti_valuta_italiana)
        ricalcolo["Importo lordo €"] = ricalcolo["Importo netto €"] * (1 + (ricalcolo["IVA %"] / 100))
        
        diff_check = False
        try:
            netto_old = st.session_state["stato_incassi"]["Importo netto €"].apply(converti_valuta_italiana).round(2)
            netto_new = ricalcolo["Importo netto €"].round(2)
            if not netto_old.equals(netto_new) or len(ricalcolo) != len(st.session_state["stato_incassi"]):
                diff_check = True
            else:
                 cols_check = [c for c in ricalcolo.columns if c not in ["Importo netto €", "Importo lordo €"]]
                 # Confronto sicuro evitando i problemi di NaN != NaN
                 if not ricalcolo[cols_check].equals(st.session_state["stato_incassi"][cols_check]):
                     diff_check = True
        except: diff_check = True

        if diff_check:
            st.session_state["stato_incassi"] = ricalcolo
            st.rerun()

        tot_commessa_full = ricalcolo["Importo netto €"].sum()
        mask_fatturato = ricalcolo["Stato"] == "Fatturato"
        fatturato_netto = ricalcolo.loc[mask_fatturato, "Importo netto €"].sum()
        fatturato_lordo = ricalcolo.loc[mask_fatturato, "Importo lordo €"].sum()
        tot_net = fatturato_netto
        tot_lordo = fatturato_lordo
        
        k1, k2 = st.columns(2)
        with k1: st.markdown(f"<div class='total-box-standard'><div class='total-label'>Totale Netto (Fatturato)</div><div class='total-value'>{fmt_euro(tot_net)}</div></div>", unsafe_allow_html=True)
        with k2: st.markdown(f"<div class='total-box-standard'><div class='total-label'>Totale Lordo (Fatturato)</div><div class='total-value'>{fmt_euro(tot_lordo)}</div></div>", unsafe_allow_html=True)

    # 05. COSTI
    with st.expander("05 // COSTI & RETRIBUZIONI", expanded=True):
        top_metrics = st.container()
        def get_money_col(): return st.column_config.NumberColumn(format="€ %.2f", required=True, step=0.01, width="medium")

        # --- CONFIGURAZIONE COMUNE CON WIDTH MEDIUM ---
        common_cols_cfg = {
            "Importo": get_money_col(),
            "Data Saldo": st.column_config.DateColumn("Data Saldo", format="DD/MM/YYYY", width="medium"),
            "Data Fattura": st.column_config.DateColumn("Data Fattura", format="DD/MM/YYYY", width="medium"),
            "Fattura": st.column_config.TextColumn("N. Fattura", width="medium")
        }

        st.markdown("### SOCI")
        soci_cfg = {
            "Socio": st.column_config.SelectboxColumn(options=SOCI_OPZIONI_FMT, required=True, width="medium"),
            "Stato": st.column_config.SelectboxColumn(options=["Da pagare", "Conteggiato", "Fatturato"], required=True, width="medium"),
            "Mansione": st.column_config.TextColumn(width="medium"),
            **common_cols_cfg
        }
        if "Importo" in df_soci_def.columns: df_soci_def["Importo"] = df_soci_def["Importo"].apply(converti_valuta_italiana)
        edited_soci = st.data_editor(df_soci_def, num_rows="dynamic", column_config=soci_cfg, use_container_width=True, key="ed_soc")

        st.markdown("### COLLABORATORI")
        collab_cfg = {
            "Collaboratore": st.column_config.TextColumn(width="medium"),
            "Mansione": st.column_config.TextColumn(width="medium"),
            "Stato": st.column_config.SelectboxColumn(options=["Da pagare", "Fatturato"], required=True, width="medium"),
            **common_cols_cfg
        }
        if "Importo" in df_collab_def.columns: df_collab_def["Importo"] = df_collab_def["Importo"].apply(converti_valuta_italiana)
        edited_collab = st.data_editor(df_collab_def, num_rows="dynamic", column_config=collab_cfg, use_container_width=True, key="ed_col")

        st.markdown("### SPESE VARIE")
        spese_cfg = {
            "Voce": st.column_config.TextColumn(width="medium"),
            "Stato": st.column_config.SelectboxColumn(options=["Da pagare", "Pagato"], required=True, width="medium"),
            **common_cols_cfg
        }
        if "Importo" in df_spese_def.columns: df_spese_def["Importo"] = df_spese_def["Importo"].apply(converti_valuta_italiana)
        edited_spese = st.data_editor(df_spese_def, num_rows="dynamic", column_config=spese_cfg, use_container_width=True, key="ed_sp")
        
        sum_soci = edited_soci["Importo"].apply(converti_valuta_italiana).sum()
        sum_collab = edited_collab["Importo"].apply(converti_valuta_italiana).sum()
        sum_spese = edited_spese["Importo"].apply(converti_valuta_italiana).sum()
        
        with top_metrics:
            b1, b2, b3, b4 = st.columns(4)
            with b1:
                box_portatore = st.empty()
                new_perc_port = st.number_input("Perc %", 0, 100, int(st.session_state["perc_portatore"]), key="np")
                st.session_state["perc_portatore"] = new_perc_port
                val_portatore = tot_net * (new_perc_port / 100.0)
                box_portatore.markdown(f"<div class='total-box-desat'><div class='total-label'>PORTATORE</div><div class='total-value'>{fmt_euro(val_portatore)}</div></div>", unsafe_allow_html=True)
            with b2:
                box_societa = st.empty()
                new_perc_soc = st.number_input("Perc %", 0, 100, int(st.session_state["perc_societa"]), key="ns")
                st.session_state["perc_societa"] = new_perc_soc
                val_societa = tot_net * (new_perc_soc / 100.0)
                box_societa.markdown(f"<div class='total-box-desat'><div class='total-label'>SOCIETA'</div><div class='total-value'>{fmt_euro(val_societa)}</div></div>", unsafe_allow_html=True)
            with b3: 
                val_iva = tot_lordo - tot_net
                st.markdown(f"<div class='total-box-desat'><div class='total-label'>IVA</div><div class='total-value'>{fmt_euro(val_iva)}</div></div>", unsafe_allow_html=True)
            with b4: 
                val_utili = tot_net - (sum_soci + sum_collab + sum_spese)
                color = "#ff4b4b" if val_utili < 0 else "#ffffff"
                st.markdown(f"<div class='total-box-desat'><div class='total-label'>UTILI</div><div class='total-value' style='color:{color};'>{fmt_euro(val_utili)}</div></div>", unsafe_allow_html=True)

    st.markdown("---")
    
    # --- SALVATAGGIO ---
    if st.button("SALVA / AGGIORNA SCHEDA", use_container_width=True):
        if not nome_cliente_finale or not nome_commessa: 
            st.error("Nome Commessa e Nome Cliente sono obbligatori")
        elif not codice_finale:
            st.error("Il Codice Commessa è obbligatorio.")
        else:
            # --- CHECK DUPLICATI MANUALE ---
            # Se sto inserendo un NUOVO codice (o in new o in edit cambiando codice), verifico che non esista già
            check_duplicate = False
            if not is_edit: 
                check_duplicate = True
            elif is_edit and codice_finale != val_codice_originale:
                check_duplicate = True
            
            if check_duplicate:
                df_dup = carica_dati("Foglio1")
                if not df_dup.empty and codice_finale in df_dup["Codice"].astype(str).values:
                    st.error(f"⚠️ ERRORE: Il codice '{codice_finale}' esiste già in archivio! Cambialo manualmente.")
                    st.stop() # Ferma l'esecuzione qui    
                    
            if nome_cliente_finale not in lista_clienti:
                st.toast(f"Nuovo cliente: aggiungo '{nome_cliente_finale}'...", icon="👤")
                rec_cliente = {"Denominazione": nome_cliente_finale, "P_IVA": p_iva, "Sede": indirizzo, "Referente": referente, "Telefono": tel_ref, "Attivo": "TRUE", "Settore": "ALTRO"}
                salva_record(rec_cliente, "Clienti", "Denominazione", "new")
            
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
                "Totale Commessa": tot_commessa_full, 
                "Fatturato": fatturato_netto,          
                "Portatore_Val": val_portatore, "Costi Società": val_societa, "Utile Netto": utile_netto,
                "Data Inserimento": str(date.today()), "Dati_JSON": json_data
            }

            if is_edit and codice_finale != val_codice_originale:
                salva_record(rec, "Foglio1", "Codice", mode="new")
                elimina_record(val_codice_originale, "Foglio1", "Codice")
                st.success(f"Commessa aggiornata da {val_codice_originale} a {codice_finale}")
                time.sleep(1)
                return True 
            else:
                mode_save = "update" if is_edit else "new"
                salva_record(rec, "Foglio1", "Codice", mode=mode_save)
                
                if is_edit:
                    st.success("Commessa aggiornata!")
                    time.sleep(1)
                    return True 
                else:
                    st.success("Nuova commessa salvata! Resetto il form...")
                    time.sleep(1)
                    keys_to_clear = ["form_cliente", "form_piva", "form_sede", "form_ref", "form_tel", "stato_incassi", "sel_cliente_box"]
                    for k in keys_to_clear:
                        if k in st.session_state: del st.session_state[k]
                    st.session_state["last_loaded_code"] = "RESET"
                    st.rerun()

    if is_edit:
        with st.expander("⚠️ ZONA PERICOLO"):
            if st.button("ELIMINA DEFINITIVAMENTE", key="btn_del"): 
                elimina_record(codice_finale, "Foglio1", "Codice")
                st.success("Commessa eliminata.")
                time.sleep(1)
                return True 

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
            st.rerun()
            
        # Recupero Dati
        d = df[df["Denominazione"] == sel].iloc[0].to_dict() if sel and not df.empty else {}
        
        # Variabile per sapere se siamo in modifica (True) o nuovo (False)
        is_editing = True if (sel and sel != "") else False

        # Tasto Nuovo
        if is_editing:
            if st.button("➕ NUOVO CLIENTE (Deseleziona)", use_container_width=True):
                st.session_state["cliente_selezionato"] = None
                st.rerun()

        st.markdown("---")

        with st.form("frm_cli"):
            # --- MODIFICA FONDAMENTALE: IL NOME È BLOCCATO SE SIAMO IN EDITING ---
            st.caption("Il nome del cliente non è modificabile in fase di aggiornamento.")
            den = st.text_input("Denominazione *", value=d.get("Denominazione", ""), disabled=is_editing)
            
            c1, c2 = st.columns(2)
            piva = c1.text_input("P.IVA", value=d.get("P_IVA", ""))
            sede = c2.text_input("Sede", value=d.get("Sede", ""))
            
            c3, c4 = st.columns(2)
            ref = c3.text_input("Referente", value=d.get("Referente", ""))
            tel = c4.text_input("Tel", value=d.get("Telefono", ""))
            
            mail = st.text_input("Email", value=d.get("Email", ""))
            
            c5, c6 = st.columns(2)
            lista_soci = SOCI_OPZIONI if 'SOCI_OPZIONI' in globals() else ["Socio A", "Socio B"]
            
            val_contatto = d.get("Contatto_SISMA", "")
            idx_cont = lista_soci.index(val_contatto) + 1 if val_contatto in lista_soci else 0
            cont = c5.selectbox("Contatto SISMA", [""] + lista_soci, index=idx_cont)
            
            sets = ["ARCHEOLOGIA", "RILIEVO", "INTEGRATI", "ALTRO"]
            val_settore = d.get("Settore", "ALTRO")
            idx_set = sets.index(val_settore) if val_settore in sets else 3
            sett = c6.selectbox("Settore", sets, index=idx_set)
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            c_att, c_dis = st.columns(2)
            curr_active = str(d.get("Attivo", "TRUE")).upper() == "TRUE"
            chk_active = c_att.checkbox("Attivo", value=curr_active)
            chk_inactive = c_dis.checkbox("Non Attivo", value=not curr_active)
            
            note = st.text_area("Note", value=d.get("Note", ""))
            
            # Testo dinamico del pulsante
            label_btn = "💾 AGGIORNA DATI CLIENTE" if is_editing else "💾 SALVA NUOVO CLIENTE"

            if st.form_submit_button(label_btn, type="primary", use_container_width=True):
                # Se stiamo creando un NUOVO, usiamo il valore del campo testo.
                # Se stiamo EDITANDO, usiamo la selezione (per sicurezza, anche se il campo è disabilitato).
                nome_finale = sel if is_editing else den

                if not nome_finale: 
                    st.error("Nome obbligatorio")
                else:
                    final_state = "FALSE" if chk_inactive else ("TRUE" if chk_active else "FALSE")
                    rec = {
                        "Denominazione": nome_finale, 
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

                    try:
                        if is_editing:
                            # MODALITÀ UPDATE: Aggiorna il record esistente trovato tramite "Denominazione"
                            salva_record(rec, "Clienti", "Denominazione", "update")
                            st.success("Dati cliente aggiornati correttamente!")
                        else:
                            # MODALITÀ NEW: Crea nuovo
                            # Controllo preventivo duplicati se necessario, ma salva_record di solito gestisce
                            if nome_finale in nomi:
                                st.warning("Esiste già un cliente con questo nome. Aggiorno quello esistente.")
                                salva_record(rec, "Clienti", "Denominazione", "update")
                            else:
                                salva_record(rec, "Clienti", "Denominazione", "new")
                                st.success("Nuovo cliente creato!")
                        
                        time.sleep(1)
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"Errore durante il salvataggio: {e}")

    # --- COLONNA DESTRA: LISTA E IMPORT/EXPORT ---
    with c_list:
        st.markdown("<h3 style='text-align: center;'>RUBRICA</h3>", unsafe_allow_html=True)
        
        # --- SEZIONE IMPORT / EXPORT ---
        with st.expander("📂 IMPORT / EXPORT", expanded=False):
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
                                    # Qui usiamo sempre update/insert logica interna
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
    
    # --- CSS HACK: Allineamento centrato prime due colonne ---
    st.markdown("""
    <style>
    div[data-testid="stDataEditor"] div[role="grid"] div[role="row"] div[role="gridcell"]:nth-child(1),
    div[data-testid="stDataEditor"] div[role="grid"] div[role="row"] div[role="gridcell"]:nth-child(2) {
        justify-content: center !important;
        text-align: center !important;
    }
    div[data-testid="stDataEditor"] div[role="grid"] div[role="row"] div[role="columnheader"]:nth-child(1) div,
    div[data-testid="stDataEditor"] div[role="grid"] div[role="row"] div[role="columnheader"]:nth-child(2) div {
        justify-content: center !important;
        text-align: center !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown("<h2 style='text-align: center;'>DASHBOARD ANALITICA</h2>", unsafe_allow_html=True)

    # --- 1. FUNZIONE PER I CALCOLI (Restituisce un FLOAT) ---
    def pulisci_per_calcoli(val):
        if pd.isna(val) or str(val).strip() == "": 
            return 0.0
        
        if isinstance(val, (float, int)):
            return float(val)
            
        s = str(val).strip()
        s = s.replace("€", "").strip()
        
        try:
            if "." in s and "," in s:
                s = s.replace(".", "").replace(",", ".")
            elif "," in s:
                s = s.replace(",", ".")
            elif "." in s:
                parts = s.split(".")
                if len(parts) > 1 and len(parts[-1]) != 2: 
                     s = s.replace(".", "")
            return float(s)
        except:
            return 0.0

    # --- 2. FUNZIONE PER LA VISUALIZZAZIONE (Stringa Blindata) ---
    def forza_testo_visivo(val):
        val_float = pulisci_per_calcoli(val)
        base = "{:,.2f}".format(val_float)
        finale = base.replace(",", "X").replace(".", ",").replace("X", ".")
        return f"€ {finale}"

    # --- GESTIONE STATO MODIFICA ---
    if "edit_codice_commessa" not in st.session_state:
        st.session_state["edit_codice_commessa"] = None

    # --- MODALITÀ MODIFICA (SCHEDA APERTA) ---
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

    # --- VISUALIZZAZIONE DASHBOARD / TABELLA ---
    if df.empty: 
        st.info("Nessun dato in archivio.")
    else:
        # --- CALCOLO TOTALE PIANO ECONOMICO ---
        def calcola_totale_piano(row):
            t_piano = 0.0
            raw_json = row.get("Dati_JSON", "")
            if pd.isna(raw_json) or str(raw_json).strip() == "": return 0.0
            try:
                dati = json.loads(str(raw_json))
                incassi = dati.get("incassi", [])
                for item in incassi:
                    if isinstance(item, dict):
                        t_piano += pulisci_per_calcoli(item.get("Importo netto €", 0))
            except:
                return 0.0
            return t_piano

        # --- CALCOLO DATI KPI FATTURATO ---
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
                                dati_reali = v
                                break 
                    stato = str(dati_reali.get("Stato", "")).lower().strip()
                    if "fatturato" in stato:
                        t_netto += pulisci_per_calcoli(dati_reali.get("Importo netto €", 0))
                        t_lordo += pulisci_per_calcoli(dati_reali.get("Importo lordo €", 0))
            except: return pd.Series([0.0, 0.0])
            return pd.Series([t_netto, t_lordo])

        # --- PREPARAZIONE DATI ---
        df["Anno"] = pd.to_numeric(df["Anno"], errors='coerce').fillna(0).astype(int)
        df["_Piano_Netto_Calc"] = df.apply(calcola_totale_piano, axis=1)
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

        # --- KPI CARDS (SETTORI) ---
        palette = ["#14505f", "#1d6677", "#287d8f"]
        cols = st.columns(3)
        settori = ["RILIEVO", "ARCHEOLOGIA", "INTEGRATI"]
        df_filtered["Settore_Norm"] = df_filtered["Settore"].astype(str).str.upper().str.strip()

        # Dizionario per accumulare dati per il grafico
        chart_data_dict = {"Settore": [], "Fatturato Netto": [], "Color": []}

        for i, (nome, col) in enumerate(zip(settori, cols)):
            d_s = df_filtered[df_filtered["Settore_Norm"] == nome]
            tot_netto_settore = d_s['_Fatt_Netto_Calc'].sum()
            tot_lordo_settore = d_s['_Fatt_Lordo_Calc'].sum()
            
            # Accumulo dati
            chart_data_dict["Settore"].append(nome)
            chart_data_dict["Fatturato Netto"].append(tot_netto_settore)
            chart_data_dict["Color"].append(palette[i])
            
            fmt_netto = forza_testo_visivo(tot_netto_settore).replace("€ ", "")
            fmt_lordo = forza_testo_visivo(tot_lordo_settore).replace("€ ", "")
            
            card_html = f"""
            <div style="background-color:{palette[i]}; padding:15px; border:1px solid #ddd; border-radius:6px; text-align:center; color:white;">
                <div style="font-weight:bold; font-size:18px; margin-bottom:10px; border-bottom:1px solid rgba(255,255,255,0.2); padding-bottom:5px;">
                    {nome}
                </div>
                <div style="display: flex; justify-content: space-around; align-items: center;">
                    <div style="text-align:center;">
                        <div style="font-size:11px; color:#ccece6; text-transform:uppercase;">NETTO</div>
                        <div style="font-size:20px; font-weight:bold;">€ {fmt_netto}</div>
                    </div>
                    <div style="width:1px; height:30px; background-color:rgba(255,255,255,0.3);"></div>
                    <div style="text-align:center;">
                        <div style="font-size:11px; color:#ffebd6; text-transform:uppercase;">LORDO</div>
                        <div style="font-size:20px; color:#ffebd6; font-weight:bold;">€ {fmt_lordo}</div>
                    </div>
                </div>
                <div style="font-size:11px; color:#ccece6; margin-top:10px;">
                    {len(d_s)} Commesse ({sel_anno_str})
                </div>
            </div>
            """
            with col: st.markdown(card_html, unsafe_allow_html=True)
        
        # --- KPI CARD (TOTALE GENERALE) ---
        tot_netto_gen = df_filtered['_Fatt_Netto_Calc'].sum()
        tot_lordo_gen = df_filtered['_Fatt_Lordo_Calc'].sum()
        fmt_netto_gen = forza_testo_visivo(tot_netto_gen).replace("€ ", "")
        fmt_lordo_gen = forza_testo_visivo(tot_lordo_gen).replace("€ ", "")

        card_total_html = f"""
        <div style="background-color:#092a33; padding:15px; border:1px solid #ddd; border-radius:6px; text-align:center; color:white; margin-top:20px;">
            <div style="font-weight:bold; font-size:18px; margin-bottom:10px; border-bottom:1px solid rgba(255,255,255,0.2); padding-bottom:5px;">
                TOTALE GENERALE
            </div>
            <div style="display: flex; justify-content: space-around; align-items: center;">
                <div style="text-align:center;">
                    <div style="font-size:11px; color:#ccece6; text-transform:uppercase;">NETTO</div>
                    <div style="font-size:24px; font-weight:bold;">€ {fmt_netto_gen}</div>
                </div>
                <div style="width:1px; height:40px; background-color:rgba(255,255,255,0.3);"></div>
                <div style="text-align:center;">
                    <div style="font-size:11px; color:#ffebd6; text-transform:uppercase;">LORDO</div>
                    <div style="font-size:24px; color:#ffebd6; font-weight:bold;">€ {fmt_lordo_gen}</div>
                </div>
            </div>
            <div style="font-size:11px; color:#ccece6; margin-top:10px;">
                {len(df_filtered)} Commesse Totali ({sel_anno_str})
            </div>
        </div>
        """
        st.markdown(card_total_html, unsafe_allow_html=True)

        # --- GRAFICO A CIAMBELLA (DONUT CHART) ---
        st.markdown("<br>", unsafe_allow_html=True)
        
        if tot_netto_gen > 0:
            df_chart = pd.DataFrame(chart_data_dict)
            
            # 1. Calcoli e Mappatura Codici
            map_codici = {"RILIEVO": "RIL", "ARCHEOLOGIA": "ARC", "INTEGRATI": "INT"}
            df_chart["Label_Codice"] = df_chart["Settore"].map(map_codici)
            
            df_chart["Percentuale"] = df_chart["Fatturato Netto"] / tot_netto_gen
            df_chart["Label_Valore"] = df_chart["Fatturato Netto"].apply(lambda x: f"€ {x:,.0f}".replace(",", "X").replace(".", ",").replace("X", "."))
            df_chart["Label_Perc"] = df_chart["Percentuale"].apply(lambda x: f"{x:.1%}")

            base = alt.Chart(df_chart).encode(
                theta=alt.Theta("Fatturato Netto", stack=True)
            )

            # Anello (Donut)
            pie = base.mark_arc(outerRadius=110, innerRadius=95).encode(
                color=alt.Color("Settore", scale=alt.Scale(domain=settori, range=palette), legend=None),
                order=alt.Order("Fatturato Netto", sort="descending"),
                tooltip=["Settore", "Label_Valore", "Label_Perc"]
            )

            # LIVELLO 1: Codice Settore
            text_code = base.mark_text(radius=155, dy=-22, size=14, fontWeight="bold").encode(
                text=alt.Text("Label_Codice"),
                order=alt.Order("Fatturato Netto", sort="descending"),
                color=alt.value("white") 
            )

            # LIVELLO 2: Valore Monetario
            text_val = base.mark_text(radius=155, dy=0, size=16).encode(
                text=alt.Text("Label_Valore"),
                order=alt.Order("Fatturato Netto", sort="descending"),
                color=alt.value("white") 
            )

            # LIVELLO 3: Percentuale
            text_perc = base.mark_text(radius=155, dy=22, size=13).encode(
                text=alt.Text("Label_Perc"),
                order=alt.Order("Fatturato Netto", sort="descending"),
                color=alt.value("#d0d0d0") 
            )
            
            # Etichetta Centrale
            text_center = alt.Chart(pd.DataFrame({'text': [f'€ {fmt_netto_gen}']})).mark_text(
                text=f'€ {fmt_netto_gen}', size=24, font='Arial', color='white', fontWeight='bold'
            ).encode()

            # FIX ERRORE JS: Padding come dizionario esplicito
            final_chart = (pie + text_code + text_val + text_perc + text_center).properties(
                height=400,
                padding={"left": 20, "right": 20, "top": 70, "bottom": 50}
            ).configure_view(
                strokeWidth=0
            )

            c_left, c_chart, c_right = st.columns([1, 6, 1])
            with c_chart:
                st.altair_chart(final_chart, use_container_width=True)
        else:
            st.info("Nessun dato di fatturato disponibile per generare il grafico.")

        st.markdown("---")
        st.markdown("<h2 style='text-align: center;'>GESTIONE COMMESSE</h2>", unsafe_allow_html=True)

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
                st.markdown("Genera un file Excel avanzato con fogli separati per Commesse, Piano Economico e Costi")
                
                if st.button("📥 SCARICA EXCEL", use_container_width=True):
                    rows_commesse = []
                    rows_piano = []
                    rows_costi = []
                    
                    for idx, row in df.iterrows():
                        commessa_dict = row.to_dict()
                        try:
                            dati = json.loads(str(row.get("Dati_JSON", "{}")))
                        except: dati = {}
                        
                        commessa_dict["Perc_Portatore"] = dati.get("percentages", {}).get("portatore", 10)
                        commessa_dict["Perc_Societa"] = dati.get("percentages", {}).get("societa", 10)
                        commessa_dict["Lista_Servizi"] = ", ".join(dati.get("servizi", []))
                        commessa_dict["Dettagli_Servizi"] = dati.get("dettagli_servizi", "")
                        
                        cols_drop = ["_Fatt_Netto_Calc", "_Fatt_Lordo_Calc", "_Piano_Netto_Calc", "Settore_Norm", "Dati_JSON"]
                        for c in cols_drop: commessa_dict.pop(c, None)
                        rows_commesse.append(commessa_dict)
                        
                        codice = str(row["Codice"])
                        incassi = dati.get("incassi", [])
                        for item in incassi:
                            if isinstance(item, dict):
                                item["Codice"] = codice 
                                rows_piano.append(item)
                                
                        for item in dati.get("soci", []):
                            if isinstance(item, dict):
                                item["Codice"] = codice
                                item["Tipo_Riga"] = "Socio"
                                rows_costi.append(item)
                        for item in dati.get("collab", []):
                            if isinstance(item, dict):
                                item["Codice"] = codice
                                item["Tipo_Riga"] = "Collab"
                                rows_costi.append(item)
                        for item in dati.get("spese", []):
                            if isinstance(item, dict):
                                item["Codice"] = codice
                                item["Tipo_Riga"] = "Spese"
                                rows_costi.append(item)

                    df_exp_main = pd.DataFrame(rows_commesse)
                    df_exp_piano = pd.DataFrame(rows_piano)
                    df_exp_costi = pd.DataFrame(rows_costi)
                    
                    if not df_exp_piano.empty:
                        cols_p = ["Codice", "Voce", "Stato", "Importo netto €", "IVA %", "Data Saldo", "Data Fattura", "Fattura"]
                        final_cols_p = [c for c in cols_p if c in df_exp_piano.columns] + [c for c in df_exp_piano.columns if c not in cols_p]
                        df_exp_piano = df_exp_piano[final_cols_p]

                    if not df_exp_costi.empty:
                        cols_c = ["Codice", "Tipo_Riga", "Socio", "Collaboratore", "Voce", "Mansione", "Importo", "Stato", "Data Saldo", "Data Fattura", "Fattura"]
                        final_cols_c = [c for c in cols_c if c in df_exp_costi.columns] + [c for c in df_exp_costi.columns if c not in cols_c]
                        df_exp_costi = df_exp_costi[final_cols_c]

                    buffer = io.BytesIO()
                    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                        df_exp_main.to_excel(writer, index=False, sheet_name='Commesse')
                        df_exp_piano.to_excel(writer, index=False, sheet_name='Piano_Economico')
                        df_exp_costi.to_excel(writer, index=False, sheet_name='Costi_Operativi')
                        
                    st.download_button(
                        label="📥 CLICCA QUI PER SCARICARE IL FILE",
                        data=buffer,
                        file_name=f"Smart_Backup_SISMA_{date.today()}.xlsx",
                        mime="application/vnd.ms-excel"
                    )
            with tab_import:
                st.info("Formato richiesto: Codice, Anno, Nome Commessa...", icon="ℹ️")
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

            def calcola_stato_colore(row):
                try:
                    raw_json = row.get("Dati_JSON", "{}")
                    if not pd.isna(raw_json) and str(raw_json).strip() != "":
                        dati = json.loads(str(raw_json))
                        
                        # PRIORITÀ 1 (ROSSO): Collaboratori o Spese "Da pagare"
                        for cat in ["collab", "spese"]:
                            items = dati.get(cat, [])
                            for it in items:
                                if isinstance(it, dict):
                                    s_pag = str(it.get("Stato", "")).strip()
                                    i_val = pulisci_per_calcoli(it.get("Importo", 0))
                                    if s_pag == "Da pagare" and abs(i_val) > 0.01:
                                        return "🔴"
                        
                        # PRIORITÀ 2 (FUCSIA): Soci "Da pagare"
                        soci_items = dati.get("soci", [])
                        for it in soci_items:
                            if isinstance(it, dict):
                                s_pag = str(it.get("Stato", "")).strip()
                                i_val = pulisci_per_calcoli(it.get("Importo", 0))
                                if s_pag == "Da pagare" and abs(i_val) > 0.01:
                                    return "🟣"

                        # PRIORITÀ 3 (BLU): Soci "Conteggiato"
                        for it in soci_items:
                            if isinstance(it, dict):
                                s_pag = str(it.get("Stato", "")).strip()
                                i_val = pulisci_per_calcoli(it.get("Importo", 0))
                                if s_pag == "Conteggiato" and abs(i_val) > 0.01:
                                    return "🔵"

                except: pass
                
                # PRIORITÀ 4 (GIALLO): Stato Commessa Aperta
                stato_raw = str(row.get("Stato", "")).strip().lower()
                if "aperta" in stato_raw: 
                    return "🟡"
                
                # DEFAULT (VERDE): Tutto chiuso/saldato
                return "🟢"

            df_to_edit["🚦 STATO"] = df_to_edit.apply(calcola_stato_colore, axis=1)
            
            if "Seleziona" not in df_to_edit.columns: df_to_edit.insert(0, "Seleziona", st.session_state["select_all_state"])
            else: df_to_edit["Seleziona"] = st.session_state["select_all_state"]

            cols_to_hide = ["_Fatt_Netto_Calc", "_Fatt_Lordo_Calc", "_Piano_Netto_Calc", "Fatturato", "Settore_Norm"] 
            df_to_edit = df_to_edit.drop(columns=[c for c in cols_to_hide if c in df_to_edit.columns], errors='ignore')

            if "_Piano_Netto_Calc" in df_filtered.columns: df_to_edit["Totale Netto Commessa"] = df_filtered["_Piano_Netto_Calc"]
            if "_Fatt_Netto_Calc" in df_filtered.columns: df_to_edit["Totale Netto Fatturato"] = df_filtered["_Fatt_Netto_Calc"]
            if "_Fatt_Lordo_Calc" in df_filtered.columns: df_to_edit["Totale Lordo Fatturato"] = df_filtered["_Fatt_Lordo_Calc"]

            for col_name in ["Totale Netto Commessa", "Totale Netto Fatturato", "Totale Lordo Fatturato"]:
                if col_name in df_to_edit.columns:
                    df_to_edit[col_name] = df_to_edit[col_name].apply(forza_testo_visivo).astype(str)

            cols_to_show = ["Seleziona", "🚦 STATO", "Codice", "Stato", "Anno", "Cliente", "Nome Commessa", "Settore", "Totale Netto Commessa", "Totale Netto Fatturato", "Totale Lordo Fatturato"]
            actual_cols = [c for c in cols_to_show if c in df_to_edit.columns]

            st.caption("LEGENDA: 🔴 Collaboratori da saldare | 🟣 Soci da saldare o conteggiare | 🔵 Soci conteggiati | 🟡 Commessa Aperta | 🟢 Chiusa e Saldata")

            edited_df = st.data_editor(
                df_to_edit[actual_cols],
                column_config={
                    "Seleziona": st.column_config.CheckboxColumn("☑️", default=False, width="small"),
                    "🚦 STATO": st.column_config.Column("ℹ️", width="small", help="Stato calcolato"),
                    "Totale Netto Commessa": st.column_config.TextColumn("Tot. Commessa (Netto)", help="Totale Netto del Piano Economico (Previsto)", width="medium"),
                    "Totale Netto Fatturato": st.column_config.TextColumn("Fatturato (Netto)", help="Totale Netto effettivamente Fatturato", width="medium"),
                    "Totale Lordo Fatturato": st.column_config.TextColumn("Fatturato (Lordo)", help="Totale Lordo effettivamente Fatturato", width="medium"),
                },
                disabled=[c for c in actual_cols if c != "Seleziona"], 
                use_container_width=True,
                hide_index=True,
                height=500,
                key="archive_editor"
            )

            # --- AZIONI SULLE RIGHE SELEZIONATE ---
            rows_selected = edited_df[edited_df["Seleziona"] == True]
            
            st.markdown("<br>", unsafe_allow_html=True)
            col_mod, col_del = st.columns([0.4, 0.6]) 

            with col_mod:
                if st.button("✏️ MODIFICA COMMESSA SELEZIONATA", use_container_width=True):
                    if len(rows_selected) == 1:
                        codice_target = rows_selected.iloc[0]["Codice"]
                        st.session_state["edit_codice_commessa"] = codice_target
                        st.rerun()
                    elif len(rows_selected) == 0:
                        st.warning("Seleziona una riga per modificarla.")
                    else:
                        st.warning("⚠️ Puoi modificare solo una commessa alla volta.")

            with col_del:
                if not rows_selected.empty:
                    with st.expander(f"⚠️ ZONA PERICOLO ({len(rows_selected)} selez.)"):
                        st.markdown("L'eliminazione è definitiva.")
                        if st.button("🗑️ ELIMINA DEFINITIVAMENTE", type="primary", key="btn_del_dashboard"):
                            codici_da_eliminare = rows_selected["Codice"].tolist()
                            elimina_record_batch(codici_da_eliminare, "Foglio1", "Codice")
                            st.success(f"Eliminati {len(codici_da_eliminare)} record.")
                            time.sleep(1)
                            st.rerun()
                else:
                    st.write("")
                
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
        
# --- 7. GESTIONE PREVENTIVI (LAYOUT FILE WORD SISMA) ---
def render_preventivi_page():
    import textwrap
    import streamlit.components.v1 as components
    import base64
    import requests 
    import json
    import time
    from datetime import date
    import pandas as pd

    st.markdown("<h2 style='text-align: center;'>GESTIONE PREVENTIVI</h2>", unsafe_allow_html=True)
    st.markdown("---")

    # --- HELPER: CONVERSIONE NUMERO IN LETTERE (ITALIANO) ---
    def numero_a_lettere(n):
        if n == 0: return "zero"
        
        numeri = {
            1: "uno", 2: "due", 3: "tre", 4: "quattro", 5: "cinque", 
            6: "sei", 7: "sette", 8: "otto", 9: "nove", 10: "dieci", 
            11: "undici", 12: "dodici", 13: "tredici", 14: "quattordici", 
            15: "quindici", 16: "sedici", 17: "diciassette", 18: "diciotto", 
            19: "diciannove", 20: "venti", 30: "trenta", 40: "quaranta", 
            50: "cinquanta", 60: "sessanta", 70: "settanta", 80: "ottanta", 
            90: "novanta"
        }
        
        def converti_centinaia(num):
            if num < 20: return numeri[num]
            if num < 100:
                decina = (num // 10) * 10
                unita = num % 10
                ris = numeri[decina]
                if unita != 0:
                    if unita == 1 or unita == 8: ris = ris[:-1] # elisione (ventuno, ventotto)
                    ris += numeri[unita]
                return ris
            if num < 1000:
                cent = num // 100
                resto = num % 100
                ris = "cento"
                if cent > 1: ris = numeri[cent] + ris
                if resto != 0: ris += converti_centinaia(resto)
                return ris
            return ""

        def converti_mille(num):
            if num < 1000: return converti_centinaia(num)
            k = num // 1000
            resto = num % 1000
            ris = "mille"
            if k > 1: ris = converti_centinaia(k) + "mila"
            if resto != 0: ris += converti_centinaia(resto)
            return ris
            
        # Supporto semplificato fino a 999.999 per brevità
        # Se servono milioni, la logica è simile estendendo la funzione
        try:
            intero = int(n)
            return converti_mille(intero)
        except:
            return str(n)

    def formatta_prezzo_testuale(valore):
        # Es: 30000.50 -> "trentamila/50"
        intero = int(valore)
        decimali = int(round((valore - intero) * 100))
        testo_intero = numero_a_lettere(intero)
        return f"{testo_intero}/{decimali:02d}"

    # Helper per ID univoco
    def get_next_prev_id(tipo):
        prefix_map = {"RILIEVO": "PR-RIL", "ARCHEOLOGIA": "PR-ARC"}
        prefix_str = f"{prefix_map.get(tipo, 'PR')}-{date.today().year}/"
        df_prev = carica_dati("Preventivi")
        max_n = 0
        if not df_prev.empty and "Codice" in df_prev.columns:
            for c in df_prev["Codice"].astype(str):
                if c.startswith(prefix_str):
                    try:
                        n = int(c.split("/")[-1])
                        if n > max_n: max_n = n
                    except: pass
        return f"{prefix_str}{max_n + 1:03d}"

    # Helper formattazione valuta numerica (30.000,00 €)
    fmt_num = lambda x: f"{x:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")

    # Helper Immagine Default da Google Drive
    @st.cache_data(show_spinner=False) 
    def get_default_logo_base64():
        file_id = "1wboY-ugQSWk2eSN8PCqPTMHCEz6WL1qC"
        url = f"https://drive.google.com/uc?export=download&id={file_id}"
        try:
            response = requests.get(url)
            if response.status_code == 200:
                b64_str = base64.b64encode(response.content).decode()
                return f"data:image/png;base64,{b64_str}"
        except:
            return None
        return None

    tab_new, tab_arch = st.tabs(["NUOVO PREVENTIVO", "ARCHIVIO"])

    # --- TAB 1: CREAZIONE ---
    with tab_new:
        st.info("Compila i dati per generare un preventivo su carta intestata SISMA.")
        
        # Generazione Codice
        c_tipo, c_code = st.columns([1, 1])
        with c_tipo:
            tipo_prev = st.radio("TIPOLOGIA:", ["RILIEVO", "ARCHEOLOGIA"], horizontal=True)
        with c_code:
            new_code = get_next_prev_id(tipo_prev)
            st.metric("Codice Documento", new_code)

        st.markdown("---")
        
        # Caricamento Dati Clienti
        df_cli = carica_dati("Clienti")
        nomi_cli = sorted(df_cli["Denominazione"].unique().tolist()) if not df_cli.empty else []

        # --- SEZIONE 1: DATI DOCUMENTO E FIRMA ---
        st.markdown("### 1. Dati Documento")
        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            data_prev = st.date_input("Data Emissione", value=date.today())
        with c2:
            luogo_data = st.text_input("Luogo", value="Scandicci")
        with c3:
            stato_prev = st.selectbox("Stato", ["BOZZA", "INVIATO", "ACCETTATO", "RIFIUTATO"])
        
        st.markdown("**Firma Socio:**")
        c_soc1, c_soc2 = st.columns([1, 3])
        
        soci_data = {
            "Andrea Arrighetti": "+39 3394298603",
            "Stefano Bertocci": "+39 3357033807",
            "Andrea Lumini": "+39 3381081115",
            "Lorenzo Marasco": "+39 3316458378",
            "Giovanni Minutoli": "+39 3385854417",
            "Marco Repole": "+39 3478835285",
            "Giovanni Pancani": "+39 3355719188"
        }
        
        with c_soc1:
            titolo_socio = st.text_input("Titolo (es. Arch.)", value="Arch.")
        with c_soc2:
            lista_nomi_soci = sorted(list(soci_data.keys()))
            socio_nome = st.selectbox("Socio Firmatario", lista_nomi_soci, index=lista_nomi_soci.index("Andrea Lumini") if "Andrea Lumini" in lista_nomi_soci else 0)
        
        socio_tel = soci_data.get(socio_nome, "")
        socio_firma_completo = f"{titolo_socio} {socio_nome}".strip()

        # --- SEZIONE 2: CLIENTE ---
        st.markdown("### 2. Dati Cliente")
        
        with st.expander("➕ Non trovi il cliente? Aggiungilo qui"):
            with st.form("form_add_cli"):
                new_cli_den = st.text_input("Denominazione (Obbligatorio)")
                new_cli_sede = st.text_area("Indirizzo Sede")
                new_cli_piva = st.text_input("P.IVA / C.F.")
                new_cli_email = st.text_input("Email / PEC")
                if st.form_submit_button("Salva Nuovo Cliente"):
                    if new_cli_den:
                        nuovo_record = {
                            "Denominazione": new_cli_den,
                            "Sede": new_cli_sede,
                            "P.IVA": new_cli_piva,
                            "Email": new_cli_email
                        }
                        salva_record(nuovo_record, "Clienti", "Denominazione", "new")
                        st.success(f"Cliente '{new_cli_den}' aggiunto! La pagina si ricaricherà...")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Inserisci almeno la Denominazione.")

        cli_sel = st.selectbox("Seleziona Cliente", [""] + nomi_cli)
        
        indirizzo_trovato = ""
        if cli_sel and not df_cli.empty:
            row_cli = df_cli[df_cli["Denominazione"] == cli_sel]
            if not row_cli.empty:
                for col_name in ["Sede", "Indirizzo", "Sede Legale"]:
                    if col_name in row_cli.columns:
                        val = str(row_cli.iloc[0][col_name])
                        if val and val != "nan":
                            indirizzo_trovato = val
                            break
        
        indirizzo_cli = st.text_area("Indirizzo Completo (Autocompilato)", value=indirizzo_trovato, height=68)

        # --- SEZIONE 3: OGGETTO ---
        st.markdown("### 3. Oggetto del Preventivo")
        oggetto_prev = st.text_area("Inserisci l'oggetto del preventivo", height=70, label_visibility="collapsed", placeholder="Es. Rilievo architettonico immobile via Roma...")

        # --- SEZIONE 4: VOCI DI COSTO ---
        st.markdown("### 4. Voci di Costo (Attività)")
        st.info("💡 Inserisci qui sotto il titolo dell'attività e usa la colonna 'Descrizione Estesa' per il dettaglio lungo.")
        
        if "prev_lines" not in st.session_state:
            st.session_state["prev_lines"] = pd.DataFrame([{"Titolo Attività": "", "Descrizione Estesa": "", "Prezzo Totale": 0.0}])

        col_config = {
            "Titolo Attività": st.column_config.TextColumn("Titolo (es. Acquisizione dati)", width="medium", required=True),
            "Descrizione Estesa": st.column_config.TextColumn("Descrizione Dettagliata", width="large"),
            "Prezzo Totale": st.column_config.NumberColumn("Prezzo Totale €", min_value=0.0, step=50.0, format="%.2f"),
        }

        edited_df = st.data_editor(
            st.session_state["prev_lines"],
            num_rows="dynamic",
            column_config=col_config,
            use_container_width=True,
            key=f"editor_prev_{tipo_prev}"
        )

        # Calcoli totali
        tot_netto = 0.0
        dettagli_list = []

        for idx, row in edited_df.iterrows():
            try:
                tit = str(row.get("Titolo Attività", ""))
                desc = str(row.get("Descrizione Estesa", ""))
                p = float(row.get("Prezzo Totale", 0))
                
                if tit.strip():
                    tot_netto += p
                    dettagli_list.append({
                        "titolo": tit,
                        "descrizione": desc,
                        "prezzo": p
                    })
            except: pass
        
        # --- SEZIONE 5: CONDIZIONI ---
        st.markdown("### 5. Condizioni Contrattuali")
        col_cond1, col_cond2 = st.columns(2)
        with col_cond1:
            giorni_preavviso = st.number_input("Giorni di Preavviso Minimo", min_value=1, value=10, step=1)
        with col_cond2:
            perc_anticipo = st.number_input("Percentuale Anticipo (%)", min_value=0, max_value=100, value=15, step=5)
        
        # --- PREPARAZIONE HTML ---
        mesi = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]
        data_str = f"{luogo_data}, {data_prev.day} {mesi[data_prev.month-1]} {data_prev.year}"
        nome_cliente_fmt = cli_sel.title() if cli_sel else "...................."

        # COSTRUZIONE ELENCO ATTIVITÀ (NO TABELLA)
        html_elenco = ""
        for i, item in enumerate(dettagli_list, 1):
            prezzo_num = fmt_num(item['prezzo'])
            prezzo_text = formatta_prezzo_testuale(item['prezzo'])
            
            html_elenco += f"""
            <div style="margin-bottom: 25px;">
                <p style="margin: 0; font-size: 11pt;"><b>{i}. {item['titolo']}</b></p>
                <p style="margin-top: 5px; margin-bottom: 5px; text-align: justify; line-height: 1.4;">
                    {item['descrizione']}
                </p>
                <p style="margin: 0; font-weight: bold;">Costo: {prezzo_num} ({prezzo_text} euro)</p>
            </div>
            """

        # Totale Complessivo
        totale_num = fmt_num(tot_netto)
        totale_text = formatta_prezzo_testuale(tot_netto)
        
        # Recupero logo
        img_src = get_default_logo_base64()
        if not img_src: img_src = "https://lh3.googleusercontent.com/d/1yIAVeiPS7dI8wdYkBZ0eyGMvCy6ET2up"

        # HTML COMPLETO
        raw_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: 'Calibri', sans-serif; font-size: 11pt; color: #000; line-height: 1.3; margin: 0; padding: 0; background-color: #f4f4f4; }}
                .page {{ max-width: 800px; margin: 20px auto; background-color: white; padding: 50px; border: 1px solid #ddd; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
            </style>
        </head>
        <body>
        <div class="page">
            
            <div style="text-align: center; margin-bottom: 30px;">
                <img src="{img_src}" alt="Intestazione SISMA" style="max-width: 100%; height: auto; max-height: 120px;" referrerpolicy="no-referrer">
            </div>

            <div style="margin-bottom: 30px;">
                <div style="text-align: right; margin-bottom: 10px;">
                    <p style="font-weight: bold; font-size: 12pt; margin: 0;">Preventivo n. {new_code}</p>
                </div>
                
                <div style="text-align: right; margin-top: 20px;">
                    <p style="margin: 0; font-style: italic;">{nome_cliente_fmt}</p>
                    <p style="margin: 0;">{indirizzo_cli.replace(chr(10), '<br>') if indirizzo_cli else ""}</p>
                </div>
                
                <p style="margin-top: 40px; margin-bottom: 10px; text-align: left;">{data_str}</p>
            </div>

            <div style="margin-bottom: 20px;">
                <p><b>Oggetto: {oggetto_prev if oggetto_prev else "...................."}</b></p>
            </div>

            <p>Spett.le {nome_cliente_fmt},</p>
            <p>come da contatti intercorsi, facendo seguito alla Vostra gentile richiesta, per la realizzazione dei servizi in oggetto, di seguito riportiamo il dettaglio delle attività e delle relative offerte tecnico-economiche:</p>

            <div style="margin-top: 30px; margin-bottom: 30px;">
                {html_elenco}
            </div>

            <div style="margin-bottom: 30px;">
                <p>Per un costo complessivo di: <b>{totale_num} ({totale_text} euro)</b></p>
            </div>

            <div style="font-size: 10pt; text-align: justify; margin-top: 30px;">
                <p><b>Note e Condizioni:</b></p>
                <ul style="padding-left: 20px; margin: 0;">
                    <li style="margin-bottom: 5px;">Il presente preventivo si intende <b>IVA ESCLUSA</b> da contabilizzare secondo l'aliquota prevista dalla legge alla data della fatturazione.</li>
                    <li style="margin-bottom: 5px;">Eventuali indagini aggiuntive che si rendessero necessarie per esigenze di approfondimento riscontrate in corso d’opera dovranno essere preventivamente valutate, prezzate ed approvate dalla Committenza.</li>
                    <li style="margin-bottom: 5px;">Nel presente preventivo non sono altresì conteggiate eventuali opere provvisionali che si rendessero necessarie per la realizzazione del rilievo. Qualora se ne dovesse riscontrare la necessità tali opere dovranno essere contabilizzate a parte o realizzate direttamente dalla Committenza.</li>
                    <li style="margin-bottom: 5px;">Le tempistiche previste per le varie attività inerenti i rilievi all’esterno sono suscettibili di modifica in relazione alle condizioni atmosferico-meteoreologiche.</li>
                    <li style="margin-bottom: 5px;">Per ottimizzare le tempistiche previste per le varie attività si richiedono gli eventuali permessi necessari per il raggiungimento diretto del sito di studio e degli ambienti interni.</li>
                    <li style="margin-bottom: 5px;">Qualora venga accettato, il presente preventivo, dovrà essere perfezionato con un contratto di fornitura di servizi.</li>
                    <li style="margin-bottom: 5px;">La società SISMA srl è disponibile ad iniziare il lavoro con un preavviso minimo di giorni <b>{giorni_preavviso} (solari)</b> e in seguito al pagamento dell’anticipo che sarà contabilizzato nella percentuale del <b>{perc_anticipo}%</b> della somma totale prevista dal contratto di fornitura dei servizi.</li>
                    <li>La Società SISMA srl, qualora venisse incaricata per i sopracitati servizi, si riserverà il diritto di utilizzare gli elaborati digitali sviluppati nel corso del progetto per scopi autopromozionali, fatti ovviamente salvo i diritti della Proprietà del Bene.</li>
                </ul>
                <p style="margin-top: 15px;">Rimaniamo a vostra disposizione per eventuali chiarimenti o specifiche.</p>
            </div>

            <div style="margin-top: 50px; display: flex; justify-content: space-between; align-items: flex-end;">
                <div style="width: 45%;">
                    <p style="margin-bottom: 60px;"><b>Per Sisma SRL</b><br>In fede,</p>
                    <p style="margin: 0;"><b>{socio_firma_completo}</b></p>
                    <p style="margin: 0; font-size: 10pt;">{socio_tel}</p>
                </div>
                <div style="width: 45%; text-align: right;">
                    <p style="margin-bottom: 60px;"><b>Per accettazione</b></p>
                    <div style="margin: 0;">
                         <span style="margin-right: 10px;">Data: ....................</span>
                         <span>Firma: ....................</span>
                    </div>
                </div>
            </div>
            
            <div style="margin-top: 40px; border-top: 1px solid #0C3A47; padding-top: 10px; font-size: 8pt; color: #0C3A47;">
                <p style="text-align: center; font-weight: bold; margin: 0 0 10px 0;">SISMA – Sistemi Integrati di Monitoraggio Architettonico srl</p>
                <div style="display: flex; justify-content: space-between;">
                    <div style="text-align: left;">
                        <b>sede:</b> Piazza Togliatti, 40 – Scandicci (FI) – 50018<br>
                        <b>C.F. | P.IVA:</b> 06557660484
                    </div>
                    <div style="text-align: right;">
                        <b>e-mail | PEC:</b> info@sisma-srl.com | sisma2015@pec.cgn.it<br>
                        <b>website:</b> www.sisma-srl.com
                    </div>
                </div>
            </div>

        </div>
        </body>
        </html>
        """
        
        html_template = textwrap.dedent(raw_html)

        # --- VISUALIZZAZIONE E AZIONI ---
        with st.expander("👁️ ANTEPRIMA DOCUMENTO (Clicca per espandere)", expanded=True):
            components.html(html_template, height=800, scrolling=True)

        st.markdown("<br>", unsafe_allow_html=True)
        c_save, c_down = st.columns([1, 1])
        
        with c_save:
            if st.button("💾 SALVA IN ARCHIVIO", type="primary", use_container_width=True):
                if not cli_sel or not oggetto_prev:
                    st.error("Inserisci Cliente e Oggetto!")
                elif tot_netto == 0:
                    st.error("Inserisci almeno una voce.")
                else:
                    record = {
                        "Codice": new_code,
                        "Tipo": tipo_prev,
                        "Data": str(data_prev),
                        "Cliente": cli_sel,
                        "Oggetto": oggetto_prev,
                        "Totale Netto": tot_netto,
                        "Totale Lordo": tot_netto, # Lordo = Netto qui, non usiamo IVA nel calcolo totale finale
                        "Stato": stato_prev,
                        "Dati_JSON": json.dumps(dettagli_list)
                    }
                    salva_record(record, "Preventivi", "Codice", "new")
                    # Reset
                    st.session_state["prev_lines"] = pd.DataFrame([{"Titolo Attività": "", "Descrizione Estesa": "", "Prezzo Totale": 0.0}])
                    st.success(f"Preventivo {new_code} salvato!")
                    time.sleep(1.5)
                    st.rerun()

        with c_down:
            st.download_button(
                label="📥 SCARICA PER WORD (.html/doc)",
                data=html_template,
                file_name=f"Preventivo_{new_code.replace('/', '_')}.html",
                mime="text/html",
                use_container_width=True
            )
            st.caption("ℹ️ Il file scaricato si apre direttamente in Word mantenendo la formattazione.")

    # --- TAB 2: ARCHIVIO (INVARIATO) ---
    with tab_arch:
        df_prev = carica_dati("Preventivi")
        if df_prev.empty:
            st.info("Archivio vuoto.")
        else:
            c_f1, c_f2 = st.columns(2)
            txt_search = c_f1.text_input("🔍 Cerca preventivo")
            if txt_search:
                df_prev = df_prev[df_prev.astype(str).apply(lambda x: x.str.contains(txt_search, case=False)).any(axis=1)]
            
            st.dataframe(df_prev[["Codice", "Data", "Cliente", "Oggetto", "Totale Lordo", "Stato"]], use_container_width=True, hide_index=True)
            
            c_del1, c_del2 = st.columns([3, 1])
            sel_del = c_del1.selectbox("Seleziona da eliminare:", [""] + df_prev["Codice"].tolist())
            if c_del2.button("Elimina", type="primary"):
                if sel_del: elimina_record(sel_del, "Preventivi", "Codice")
with st.sidebar:
    st.markdown("### HOME")
    st.markdown("---")
    # Aggiunta la voce ":: PREVENTIVI" alla lista
    scelta = st.radio("PAGINE:", [
        "> DASHBOARD & ARCHIVIO", 
        "> NUOVA COMMESSA", 
        "> PREVENTIVI", 
        "> CLIENTI", 
        "> SOCIETA'"
    ], index=0)
    st.markdown("---")

# --- 9. RENDER PAGINE ---
if "> DASHBOARD" in scelta:
    render_dashboard()
elif "> NUOVA COMMESSA" in scelta:
    render_commessa_form(None)
elif "> PREVENTIVI" in scelta:
    render_preventivi_page()  # <--- Richiama la nuova funzione
elif "> CLIENTI" in scelta:
    render_clienti_page()
elif "> SOCIETA" in scelta:
    render_organigramma()









































































































































