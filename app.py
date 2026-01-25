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

# --- 0. CONFIGURAZIONE TEMA (CORREZIONE COLORE ROSSO) ---
# Questa funzione crea il file di configurazione per forzare il colore Petrolio al posto del Rosso
def setup_config_toml():
    config_dir = ".streamlit"
    config_path = os.path.join(config_dir, "config.toml")
    if not os.path.exists(config_dir): 
        os.makedirs(config_dir)
    
    # Definisce il tema Petrolio
    config_content = """
[theme]
primaryColor = "#427e72"
backgroundColor = "#000000"
secondaryBackgroundColor = "#111111"
textColor = "#FFFFFF"
font = "sans serif"
[server]
runOnSave = true
"""
    if not os.path.exists(config_path):
        with open(config_path, "w") as f:
            f.write(config_content)

# Eseguiamo il setup del tema PRIMA di tutto
setup_config_toml()

# --- 1. SETUP PAGINA ---
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
    
    /* BUTTONS */
    div.stButton > button {{
        background-color: {COL_DEEP} !important; color: #FFFFFF !important; 
        border: 1px solid {COL_ACCENT} !important; border-radius: 4px; 
    }}

    /* TOTALI BOX */
    .total-box-standard {{
        background-color: #0c3a47; border: 1px solid #427e72;
        text-align: center; padding: 10px; border-radius: 5px; margin-bottom: 5px; 
    }}
    .total-box-desat {{
        background-color: #1f2629; border: 1px solid #333333;
        text-align: center; padding: 10px; border-radius: 5px; margin-bottom: 5px; 
    }}
    .total-label {{ font-size: 11px; color: #ccc; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 2px; }}
    .total-value {{ font-size: 18px; color: #fff; font-weight: bold; font-family: 'Courier New', monospace; }}
    
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
    /* CORREZIONE ALTEZZA: Rimosso height:480px fisso, messo min-height più piccolo */
    .card-mid {{
        background-color: #111111; border: 1px solid #333; border-top: 3px solid {COL_DEEP}; 
        border-radius: 4px; padding: 25px 20px; min-height: 250px;            
        display: flex; flex-direction: column; align-items: center; justify-content: flex-start;
    }}
    .org-row {{
        display: block; width: 100%; margin-bottom: 15px; text-align: center;
        border-bottom: 1px solid #222; padding-bottom: 10px;
    }}
    .org-row:last-child {{ border-bottom: none; margin-bottom: 0; padding-bottom: 0; }}
    .role-label {{ 
        color: {COL_ACCENT}; font-size: 16px; text-transform: uppercase; font-weight: bold; 
        display: block; margin-bottom: 5px; letter-spacing: 0.5px;
    }}
    .card-subtitle {{ 
        font-size: 18px; color: #FFFFFF; font-weight: bold; text-transform: uppercase; 
        margin-bottom: 15px; width: 100%; text-align: center; line-height: 1.2;
    }}
    .name-text {{ font-size: 20px; color: #DDD; font-weight: 500; margin-bottom: 5px; display: block; }}
    
    .logo-container {{ display: flex; justify-content: center; padding-bottom: 30px; border-bottom: 1px solid #333333; margin-bottom: 30px; }}
    .logo-container img {{ width: 100%; max-width: 500px; }}
    </style>
""", unsafe_allow_html=True)

LOGO_URL = "https://drive.google.com/thumbnail?id=1xKRvfMtlXd4vRpk_OlFE4MmkC3S7mZ4H&sz=w1000"
st.markdown(f'<div class="logo-container"><img src="{LOGO_URL}"></div>', unsafe_allow_html=True)

# --- 2. GESTIONE DATI (GSPREAD - CONNESSIONE ROBUSTA) ---
SHEET_ID = "1vfcB5CJ6J7Vgmw7JcDleR4MDEmw_kJTm4nXak1Lsg8E" 

def get_worksheet(sheet_name="Foglio1"):
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = None
    
    # 1. CLOUD (SECRETS)
    if "GCP_CREDENTIALS" in st.secrets:
        try:
            json_str = st.secrets["GCP_CREDENTIALS"].strip()
            # Parsing con tolleranza
            try:
                creds_dict = json.loads(json_str, strict=False)
            except json.JSONDecodeError:
                # Fallback estremo per caratteri strani
                creds_dict = json.loads(json_str.replace('\n', '\\n'), strict=False)

            if "private_key" in creds_dict:
                creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

            creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        except Exception as e:
            print(f"Errore lettura Secrets: {e}")

    # 2. LOCALE (FILE)
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

# --- 3. FORM COMMESSA ---
def render_commessa_form(data=None):
    is_edit = data is not None
    if "form_cliente" not in st.session_state: st.session_state["form_cliente"] = ""
    if "form_piva" not in st.session_state: st.session_state["form_piva"] = ""
    if "form_sede" not in st.session_state: st.session_state["form_sede"] = ""
    if "form_ref" not in st.session_state: st.session_state["form_ref"] = ""
    if "form_tel" not in st.session_state: st.session_state["form_tel"] = ""
    if "perc_portatore" not in st.session_state: st.session_state["perc_portatore"] = 10
    if "perc_societa" not in st.session_state: st.session_state["perc_societa"] = 10

    df_clienti = carica_dati("Clienti")
    lista_clienti = []
    if not df_clienti.empty and "Denominazione" in df_clienti.columns:
        if "Attivo" in df_clienti.columns:
             clienti_attivi = df_clienti[df_clienti["Attivo"].astype(str).str.upper() == "TRUE"]
             lista_clienti = sorted(clienti_attivi["Denominazione"].unique().tolist())
        else:
             lista_clienti = sorted(df_clienti["Denominazione"].unique().tolist())

    if is_edit:
        val_codice = data["Codice"]
        val_anno = int(data.get("Anno", 2024))
        val_oggetto = data.get("Nome Commessa", "") 
        val_servizi = []
        try:
            if "Dati_JSON" in data and data["Dati_JSON"]:
                jdata = json.loads(data["Dati_JSON"])
                val_servizi = jdata.get("servizi", [])
                if "percentages" in jdata:
                    st.session_state["perc_portatore"] = int(jdata["percentages"].get("portatore", 10))
                    st.session_state["perc_societa"] = int(jdata["percentages"].get("societa", 10))
        except: val_servizi = []

        if st.session_state.get("last_loaded_code") != val_codice:
            st.session_state["form_cliente"] = data.get("Cliente", "") 
            st.session_state["form_piva"] = data.get("P_IVA", "")
            st.session_state["form_sede"] = data.get("Sede", "")
            st.session_state["form_ref"] = data.get("Referente", "")
            st.session_state["form_tel"] = data.get("Tel Referente", "")
            st.session_state["last_loaded_code"] = val_codice
            if "stato_incassi" in st.session_state: del st.session_state["stato_incassi"]
    else:
        val_codice = ""
        val_anno = date.today().year
        val_oggetto = ""
        val_servizi = []
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
        with c1:
            mappa_settori = {"RILIEVO": "RIL", "ARCHEOLOGIA": "ARC", "INTEGRATI": "INT"}
            if is_edit: codice = st.text_input("Codice", value=val_codice, disabled=True)
            else: codice = st.text_input("Codice", value=f"{mappa_settori[settore]}/{anno}-001")
        with c4:
            idx_stato = ["APERTA", "CHIUSA", "IN ATTESA"].index(data["Stato"]) if is_edit and "Stato" in data else 0
            stato_header = st.selectbox("Stato Commessa ▼", ["APERTA", "CHIUSA", "IN ATTESA"], index=idx_stato)
        
        st.markdown("<br>", unsafe_allow_html=True)
        nome_commessa = st.text_input("Nome Commessa", value=val_oggetto, placeholder="Es. Rilievo Chiesa...")
        st.markdown("<br>", unsafe_allow_html=True)
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

        sel_val = st.selectbox("Seleziona Cliente esistente o Nuovo ▼", display_list, index=idx_cli, key="sel_cliente_box", on_change=on_cliente_change)
        if sel_val == "➕ NUOVO CLIENTE":
            nome_cliente_manuale = st.text_input("Inserisci Nome Nuovo Cliente *", value="")
            nome_cliente_finale = nome_cliente_manuale
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
        idx_pm = SOCI_OPZIONI.index(data.get("PM", SOCI_OPZIONI[0])) if is_edit and data.get("PM") in SOCI_OPZIONI else 0
        coordinatore = c1.selectbox("Project Manager ▼", SOCI_OPZIONI, index=idx_pm)
        idx_soc = SOCI_OPZIONI.index(data.get("Portatore", SOCI_OPZIONI[0])) if is_edit and data.get("Portatore") in SOCI_OPZIONI else 0
        portatore = c2.selectbox("Socio Portatore ▼", SOCI_OPZIONI, index=idx_soc)

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
    
    df_soci_def = pd.DataFrame([{"Socio": SOCI_OPZIONI[0], "Mansione": "Coordinamento", "Importo": 0.0, "Stato": "Da pagare", "Note": ""}])
    df_collab_def = pd.DataFrame([{"Collaboratore": "Esterno", "Mansione": "Rilievo", "Importo": 0.0, "Stato": "Da pagare", "Note": ""}])
    df_spese_def = pd.DataFrame([{"Voce": "Varie", "Importo": 0.0, "Stato": "Da pagare", "Note": ""}])

    if is_edit and "Dati_JSON" in data and data["Dati_JSON"]:
        try:
            jdata = json.loads(data["Dati_JSON"])
            if "soci" in jdata: 
                df_temp = pd.DataFrame(jdata["soci"])
                if "Ruolo" in df_temp.columns: df_temp = df_temp.rename(columns={"Ruolo": "Mansione"})
                expected = ["Socio", "Mansione", "Importo", "Stato", "Note"]
                for c in expected:
                     if c not in df_temp.columns: df_temp[c] = "" if c != "Importo" else 0.0
                df_soci_def = df_temp[expected]
            if "collab" in jdata: 
                df_temp = pd.DataFrame(jdata["collab"])
                if "Nome" in df_temp.columns: df_temp = df_temp.rename(columns={"Nome": "Collaboratore"})
                expected = ["Collaboratore", "Mansione", "Importo", "Stato", "Note"]
                for c in expected:
                     if c not in df_temp.columns: df_temp[c] = "" if c != "Importo" else 0.0
                df_collab_def = df_temp[expected]
            if "spese" in jdata: 
                df_temp = pd.DataFrame(jdata["spese"])
                expected = ["Voce", "Importo", "Stato", "Note"]
                for c in expected:
                     if c not in df_temp.columns: df_temp[c] = "" if c != "Importo" else 0.0
                df_spese_def = df_temp[expected]
        except: pass

    with st.expander("04 // PIANO ECONOMICO", expanded=True):
        col_cfg = {
            "Voce": st.column_config.SelectboxColumn("Voce ▼", options=["Acconto", "Saldo"], required=True, width="medium"),
            "Importo netto €": st.column_config.NumberColumn("Importo netto €", format="€ %.2f", required=True, width="small"),
            "IVA %": st.column_config.SelectboxColumn("IVA % ▼", options=[0, 22], required=True, width="small"),
            "Importo lordo €": st.column_config.NumberColumn("Importo lordo €", format="€ %.2f", disabled=True, width="small"),
            "Stato": st.column_config.SelectboxColumn("Stato ▼", options=["Previsto", "Fatturato"], required=True, width="small"),
            "Data": st.column_config.DateColumn("Data", format="DD/MM/YYYY", width="small"),
            "Note": st.column_config.TextColumn("Note", width="large")
        }
        edited_incassi = st.data_editor(st.session_state["stato_incassi"], num_rows="dynamic", column_config=col_cfg, use_container_width=True, key="ed_inc")
        
        ricalcolo = edited_incassi.copy()
        ricalcolo["Importo lordo €"] = ricalcolo["Importo netto €"] * (1 + (ricalcolo["IVA %"] / 100))
        diff = False
        try:
            if not ricalcolo["Importo lordo €"].equals(st.session_state["stato_incassi"]["Importo lordo €"]): diff = True
            if not ricalcolo["Importo netto €"].equals(st.session_state["stato_incassi"]["Importo netto €"]): diff = True
        except: diff = True
        if diff:
            st.session_state["stato_incassi"] = ricalcolo
            st.rerun()

        tot_net = st.session_state["stato_incassi"]["Importo netto €"].sum()
        tot_lordo = st.session_state["stato_incassi"]["Importo lordo €"].sum()
        fatturato_netto = st.session_state["stato_incassi"][st.session_state["stato_incassi"]['Stato'] == 'Fatturato']['Importo netto €'].sum()

        k1, k2 = st.columns(2)
        with k1: st.markdown(f"<div class='total-box-standard'><div class='total-label'>Totale Netto</div><div class='total-value'>{fmt_euro(tot_net)}</div></div>", unsafe_allow_html=True)
        with k2: st.markdown(f"<div class='total-box-standard'><div class='total-label'>Totale Lordo</div><div class='total-value'>{fmt_euro(tot_lordo)}</div></div>", unsafe_allow_html=True)

    with st.expander("05 // COSTI & RETRIBUZIONI", expanded=True):
        top_metrics = st.container()
        st.markdown("### SOCI")
        soci_cfg = {
            "Socio": st.column_config.SelectboxColumn("Socio ▼", options=SOCI_OPZIONI, required=True, width="medium"),
            "Mansione": st.column_config.TextColumn("Mansione", width="medium"),
            "Importo": st.column_config.NumberColumn("Importo €", format="€ %.2f", required=True, width="small"),
            "Stato": st.column_config.SelectboxColumn("Stato ▼", options=["Da pagare", "Conteggiato", "Fatturato"], required=True, width="small"),
            "Note": st.column_config.TextColumn("Note", width="medium")
        }
        edited_soci = st.data_editor(df_soci_def, num_rows="dynamic", column_config=soci_cfg, use_container_width=True, key="ed_soc")

        st.markdown("### COLLABORATORI")
        collab_cfg = {
            "Collaboratore": st.column_config.TextColumn("Collaboratore", width="medium"),
            "Mansione": st.column_config.TextColumn("Mansione", width="medium"),
            "Importo": st.column_config.NumberColumn("Importo €", format="€ %.2f", required=True, width="small"),
            "Stato": st.column_config.SelectboxColumn("Stato ▼", options=["Da pagare", "Fatturato"], required=True, width="small"),
            "Note": st.column_config.TextColumn("Note", width="medium")
        }
        edited_collab = st.data_editor(df_collab_def, num_rows="dynamic", column_config=collab_cfg, use_container_width=True, key="ed_col")

        st.markdown("### SPESE VARIE")
        spese_cfg = {
            "Voce": st.column_config.TextColumn("Voce", width="large"), 
            "Importo": st.column_config.NumberColumn("Importo €", format="€ %.2f", required=True, width="small"),
            "Stato": st.column_config.SelectboxColumn("Stato ▼", options=["Da pagare", "Pagato"], required=True, width="small"),
            "Note": st.column_config.TextColumn("Note", width="medium")
        }
        edited_spese = st.data_editor(df_spese_def, num_rows="dynamic", column_config=spese_cfg, use_container_width=True, key="ed_sp")
        
        sum_soci = edited_soci["Importo"].sum()
        sum_collab = edited_collab["Importo"].sum()
        sum_spese = edited_spese["Importo"].sum()
        
        with top_metrics:
            b1, b2, b3, b4 = st.columns(4, gap="small")
            with b1:
                val_portatore = tot_net * (st.session_state["perc_portatore"] / 100.0)
                st.markdown(f"<div class='total-box-desat'><div class='total-label'>PORTATORE</div><div class='total-value'>{fmt_euro(val_portatore)}</div></div>", unsafe_allow_html=True)
                new_perc_port = st.number_input("Perc. %", 0, 100, int(st.session_state["perc_portatore"]), step=1, format="%d", key="num_port", label_visibility="collapsed")
                if new_perc_port != st.session_state["perc_portatore"]:
                    st.session_state["perc_portatore"] = new_perc_port
                    st.rerun()
            with b2:
                val_societa = tot_net * (st.session_state["perc_societa"] / 100.0)
                st.markdown(f"<div class='total-box-desat'><div class='total-label'>SOCIETA'</div><div class='total-value'>{fmt_euro(val_societa)}</div></div>", unsafe_allow_html=True)
                new_perc_soc = st.number_input("Perc. %", 0, 100, int(st.session_state["perc_societa"]), step=1, format="%d", key="num_soc", label_visibility="collapsed")
                if new_perc_soc != st.session_state["perc_societa"]:
                    st.session_state["perc_societa"] = new_perc_soc
                    st.rerun()
            val_iva = tot_lordo - tot_net
            with b3: 
                st.markdown(f"<div class='total-box-desat'><div class='total-label'>IVA</div><div class='total-value'>{fmt_euro(val_iva)}</div></div>", unsafe_allow_html=True)
            val_utili = tot_net - (sum_soci + sum_collab + sum_spese)
            color_utili = "#ff4b4b" if val_utili < 0 else "#ffffff"
            with b4: 
                st.markdown(f"<div class='total-box-desat'><div class='total-label'>UTILI NETTI COMMESSA</div><div class='total-value' style='color: {color_utili};'>{fmt_euro(val_utili)}</div></div>", unsafe_allow_html=True)

    st.markdown("---")
    if st.button("SALVA / AGGIORNA SCHEDA", use_container_width=True):
        if not nome_cliente_finale or not nome_commessa: 
            st.error("Nome Commessa e Nome Cliente sono obbligatori")
        else:
            if nome_cliente_finale not in lista_clienti:
                st.toast(f"Nuovo cliente: aggiungo '{nome_cliente_finale}' alla rubrica...", icon="👤")
                rec_cliente = {
                    "Denominazione": nome_cliente_finale, "P_IVA": p_iva, "Sede": indirizzo,
                    "Referente": referente, "Telefono": tel_ref, "Attivo": "TRUE", "Settore": "ALTRO", "Note": "Auto-generato"
                }
                salva_record(rec_cliente, "Clienti", "Denominazione", "new")
            
            json_data = json.dumps({
                "incassi": st.session_state["stato_incassi"].to_dict('records'), 
                "soci": edited_soci.to_dict('records'),
                "collab": edited_collab.to_dict('records'), 
                "spese": edited_spese.to_dict('records'),
                "servizi": servizi_scelti,
                "percentages": { "portatore": st.session_state["perc_portatore"], "societa": st.session_state["perc_societa"] }
            }, default=str)
            
            tot_uscite_reali = val_portatore + val_societa + sum_soci + sum_collab + sum_spese
            utile_netto_reale = tot_net - tot_uscite_reali

            rec = {
                "Codice": codice, "Anno": anno, "Nome Commessa": nome_commessa, "Cliente": nome_cliente_finale,
                "P_IVA": p_iva, "Sede": indirizzo, "Referente": referente, "Tel Referente": tel_ref,
                "PM": coordinatore, "Portatore": portatore, "Settore": settore, "Stato": stato_header, 
                "Totale Commessa": tot_net, "Fatturato": fatturato_netto,
                "Portatore_Val": val_portatore, "Costi Società": val_societa, "Utile Netto": utile_netto_reale,
                "Data Inserimento": str(date.today()), "Dati_JSON": json_data
            }
            salva_record(rec, "Foglio1", "Codice", "update" if is_edit else "new")
            if is_edit: st.rerun()

    if is_edit:
        with st.expander("⚠️ ZONA PERICOLO"):
            if st.button("ELIMINA DEFINITIVAMENTE", key="btn_del"): elimina_record(codice, "Foglio1", "Codice")

# --- 4. CLIENTI PAGE ---
def render_clienti_page():
    st.markdown("<h2 style='text-align: center;'>ARCHIVIO CLIENTI</h2>", unsafe_allow_html=True)
    st.markdown("---")
    c_form, c_list = st.columns([1, 2], gap="large")
    with c_form:
        st.markdown("<h3 style='text-align: center;'>GESTIONE</h3>", unsafe_allow_html=True)
        df = carica_dati("Clienti")
        nomi = sorted(df["Denominazione"].tolist()) if not df.empty else []
        sel = st.selectbox("Modifica:", [""] + nomi)
        d = df[df["Denominazione"] == sel].iloc[0].to_dict() if sel and not df.empty else {}
        
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
            idx_cont = SOCI_OPZIONI.index(d.get("Contatto_SISMA")) + 1 if d.get("Contatto_SISMA") in SOCI_OPZIONI else 0
            cont = c5.selectbox("Contatto SISMA", [""] + SOCI_OPZIONI, index=idx_cont)
            sets = ["ARCHEOLOGIA", "RILIEVO", "INTEGRATI", "ALTRO"]
            idx_set = sets.index(d.get("Settore")) if d.get("Settore") in sets else 3
            sett = c6.selectbox("Settore", sets, index=idx_set)
            st.markdown("<br>", unsafe_allow_html=True)
            c_att, c_dis = st.columns(2)
            curr_active = str(d.get("Attivo", "TRUE")).upper() == "TRUE"
            chk_active = c_att.checkbox("Attivo", value=curr_active)
            chk_inactive = c_dis.checkbox("Non Attivo", value=not curr_active)
            note = st.text_area("Note", value=d.get("Note", ""))
            if st.form_submit_button("SALVA"):
                if not den: st.error("Nome obbligatorio")
                else:
                    final_state = "FALSE" if chk_inactive else ("TRUE" if chk_active else "FALSE")
                    rec = {"Denominazione": den, "P_IVA": piva, "Sede": sede, "Referente": ref, "Telefono": tel, "Email": mail, "Contatto_SISMA": cont, "Settore": sett, "Attivo": final_state, "Note": note}
                    salva_record(rec, "Clienti", "Denominazione", "update" if sel else "new")
                    st.rerun()
        if sel and st.button("ELIMINA CLIENTE"): elimina_record(sel, "Clienti", "Denominazione")

    with c_list:
        st.markdown("<h3 style='text-align: center;'>RUBRICA</h3>", unsafe_allow_html=True)
        if not df.empty:
            df_view = df.copy()
            df_view["Attivo"] = df_view["Attivo"].astype(str).str.upper() == "TRUE"
            df_view["Non Attivo"] = ~df_view["Attivo"] 
            target_cols = ["Denominazione", "P_IVA", "Sede", "Referente", "Telefono", "Email", "Settore", "Attivo"]
            final_cols = [c for c in target_cols if c in df_view.columns]
            st.dataframe(df_view[final_cols], column_config={"Attivo": st.column_config.CheckboxColumn(disabled=True)}, use_container_width=True, hide_index=True)
            
            buffer_cli = io.BytesIO()
            with pd.ExcelWriter(buffer_cli, engine='xlsxwriter') as writer_cli:
                df_view.to_excel(writer_cli, index=False, sheet_name='Rubrica')
            st.download_button(label="📥 BACKUP CLIENTI", data=buffer_cli, file_name=f"Rubrica_Clienti_{date.today()}.xlsx", mime="application/vnd.ms-excel")

# --- 5. DASHBOARD & IMPORT ---
def render_dashboard():
    df = carica_dati("Foglio1")
    st.markdown("<h2 style='text-align: center;'>DASHBOARD ANALITICA</h2>", unsafe_allow_html=True)
    if df.empty: st.info("Nessun dato.")
    else:
        df["Totale Commessa"] = pd.to_numeric(df["Totale Commessa"], errors='coerce').fillna(0)
        palette = ["#14505f", "#1d6677", "#287d8f"]
        cols = st.columns(3)
        for i, (nome, col) in enumerate(zip(["RILIEVO", "ARCHEOLOGIA", "INTEGRATI"], cols)):
            d_s = df[df["Settore"].astype(str).str.upper() == nome]
            with col:
                st.markdown(f"""
                <div style="background-color:{palette[i]}; padding:20px; border:1px solid {COL_ACCENT}; border-radius:4px; text-align:center;">
                    <div style="color:#FFF; font-weight:bold;">{nome}</div>
                    <div style="font-size:24px; color:white; font-weight:bold;">€ {d_s['Totale Commessa'].sum():,.0f}</div>
                    <div style="font-size:12px; color:#ccece6;">{len(d_s)} Commesse</div>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("<h2 style='text-align: center;'>GESTIONE COMMESSE</h2>", unsafe_allow_html=True)
    
    if not df.empty:
        opts = []
        for _, row in df.iterrows():
             nome_show = str(row["Nome Commessa"])
             cli_show = str(row["Cliente"]) if row["Cliente"] else "N/D"
             opts.append(f"{row['Codice']} | {cli_show} - {nome_show}")
        sel = st.selectbox("Seleziona per Modifica:", [""] + opts)
        if sel:
            cod = sel.split(" | ")[0]
            render_commessa_form(df[df["Codice"].astype(str) == cod].iloc[0].to_dict())
            return

    st.markdown("<br>", unsafe_allow_html=True)
    c_title, c_actions = st.columns([1, 1], gap="large")
    with c_title: st.markdown("<h3 style='text-align: left; margin-top:0;'>ARCHIVIO COMPLETO</h3>", unsafe_allow_html=True)
    with c_actions:
        tab_backup, tab_import = st.tabs(["📤 ESPORTA / BACKUP", "📥 IMPORTA DA EXCEL"])
        with tab_backup:
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Archivio_SISMA')
            st.download_button("SCARICA EXCEL COMPLETO", data=buffer, file_name=f"Backup_SISMA_{date.today()}.xlsx", mime="application/vnd.ms-excel", use_container_width=True)
        with tab_import:
            st.info("Formato richiesto: Codice, Anno, Nome Commessa, Cliente, Totale Commessa...", icon="ℹ️")
            template_df = pd.DataFrame(columns=["Codice", "Anno", "Nome Commessa", "Cliente", "P_IVA", "Sede", "Referente", "Tel Referente", "PM", "Portatore", "Settore", "Stato", "Totale Commessa", "Fatturato"])
            buf_tpl = io.BytesIO()
            with pd.ExcelWriter(buf_tpl, engine='xlsxwriter') as writer: template_df.to_excel(writer, index=False, sheet_name='Template')
            st.download_button("1. Scarica Modello Vuoto", data=buf_tpl, file_name="Template_SISMA.xlsx", use_container_width=True)
            uploaded_file = st.file_uploader("2. Carica Excel compilato", type=["xlsx", "xls"])
            if uploaded_file and st.button("AVVIA IMPORTAZIONE", type="primary", use_container_width=True):
                importa_excel_batch(uploaded_file)

    if not df.empty:
        cols_to_show = ["Codice", "Stato", "Anno", "Cliente", "Nome Commessa", "Settore", "Totale Commessa", "Fatturato"]
        actual_cols = [c for c in cols_to_show if c in df.columns]
        st.dataframe(df[actual_cols], use_container_width=True, height=500)

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
    c_left, c_chart, c_right = st.columns([1, 2, 1])
    with c_chart:
        petrol_palette = ['#082a33', '#0c3a47', '#14505f', '#1d6677', '#287d8f', '#3695a7', '#46adbf']
        chart = alt.Chart(df_s).mark_arc(innerRadius=70, outerRadius=110).encode(
            theta=alt.Theta("Quota", stack=True),
            color=alt.Color("Nome", legend=None, scale=alt.Scale(range=petrol_palette)),
            tooltip=["Nome", "Quota", "Perc"]
        ).properties(height=350).configure(background='#000000').configure_view(strokeWidth=0)
        st.altair_chart(chart, use_container_width=True)

    c_cda, c_op, c_cs = st.columns(3, gap="medium")
    with c_cda: 
        st.markdown("""<div class="card-mid"><div class="card-subtitle">CONSIGLIO DI<br>AMMINISTRAZIONE</div>
        <div class="org-row"><span class="role-label">Presidente</span><div class="name-text">LORENZO MARASCO</div></div>
        <div class="org-row"><span class="role-label">Consigliere</span><div class="name-text">ANDREA ARRIGHETTI</div></div>
        <div class="org-row"><span class="role-label">Consigliere</span><div class="name-text">MARCO REPOLE</div></div></div>""", unsafe_allow_html=True)
    with c_op: 
        st.markdown("""<div class="card-mid"><div class="card-subtitle">COMITATO<br>ESECUTIVO</div>
        <div class="org-row"><span class="role-label">ARCHEOLOGIA</span><div class="name-text">ARRIGHETTI / MARASCO</div></div>
        <div class="org-row"><span class="role-label">RILIEVO</span><div class="name-text">LUMINI / REPOLE</div></div></div>""", unsafe_allow_html=True)
    with c_cs:
         st.markdown("""<div class="card-mid"><div class="card-subtitle">COMITATO<br>SCIENTIFICO</div>
        <div class="org-row"><span class="role-label">Membro</span><div class="name-text">STEFANO BERTOCCI</div></div>
        <div class="org-row"><span class="role-label">Membro</span><div class="name-text">GIOVANNI MINUTOLI</div></div>
        <div class="org-row"><span class="role-label">Membro</span><div class="name-text">GIOVANNI PANCANI</div></div></div>""", unsafe_allow_html=True)

    st.markdown("<div class='org-header'>LIVELLO 2: GESTIONALE</div>", unsafe_allow_html=True)
    st.markdown("""<div style="display:flex; justify-content:center; margin-bottom:20px; width:100%;">
            <div class="org-card" style="width: 400px; padding: 30px;">
                <span class="role-label">DIREZIONE GENERALE</span><div class="name-text" style="font-weight:bold;">LORENZO MARASCO</div>
            </div></div>""", unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3)
    with c1: st.markdown('<div class="org-card"><span class="role-label">CONTABILITA\' & HR</span><div class="name-text">ANDREA LUMINI</div></div>', unsafe_allow_html=True)
    with c2: st.markdown('<div class="org-card"><span class="role-label">BUSINESS & R&D</span><div class="name-text">ANDREA ARRIGHETTI</div></div>', unsafe_allow_html=True)
    with c3: st.markdown('<div class="org-card"><span class="role-label">GARE & MARKETING</span><div class="name-text">MARCO REPOLE</div></div>', unsafe_allow_html=True)

    # --- REINSERITO LIVELLO 3 ---
    st.markdown("<div class='org-header'>LIVELLO 3: OPERATIVO</div>", unsafe_allow_html=True)
    c_op1, c_op2, c_op3 = st.columns(3)
    with c_op1: st.markdown('<div class="org-card"><span class="role-label">RESPONSABILE SICUREZZA</span><div class="name-text">GIOVANNI PANCANI</div></div>', unsafe_allow_html=True)
    with c_op2: st.markdown('<div class="org-card"><span class="role-label">RESPONSABILE RESTITUZIONE</span><div class="name-text">STEFANO BERTOCCI</div></div>', unsafe_allow_html=True)
    with c_op3: st.markdown('<div class="org-card"><span class="role-label">RESPONSABILE DIAGNOSTICA</span><div class="name-text">GIOVANNI MINUTOLI</div></div>', unsafe_allow_html=True)

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
