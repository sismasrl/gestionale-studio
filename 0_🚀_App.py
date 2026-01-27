Hai ragione, scusami. Ho fatto confusione mandandoti solo il pezzo finale e creando un "puzzle" difficile da incollare. Inoltre, ho lasciato delle icone nel codice precedente che non volevi.

Ecco il codice **INTERO, UNICO e COMPLETO**.

Ho fatto queste operazioni:

1. **Unito tutto**: Non devi incollare nulla, questo codice sostituisce completamente quello che hai.
2. **Rimosso le icone**: Ho tolto emoji (🚀, 🔒, 👤, ✅, 🗑️, ⚠️, ecc.) da pulsanti, titoli, toast e menu laterale. È tutto testo pulito.
3. **Corretto la fine**: Ho sistemato la funzione `render_clienti_page` che nel tuo messaggio era tagliata a metà.

Copia e incolla questo blocco intero nel tuo file:

```python
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
        st.markdown("### ACCESSO RISERVATO STUDIO")
        st.text_input("Inserisci Password:", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.markdown("### ACCESSO RISERVATO STUDIO")
        st.text_input("Inserisci Password:", type="password", on_change=password_entered, key="password")
        st.error("Password errata")
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
    div[data-testid="column"] button p {{
        font-size: 12px !important;
    }}
    div[data-testid="column"] button {{
        min-height: 0px !important;
        height: 35px !important;
        padding-top: 0px !important;
        padding-bottom: 0px !important;
    }}

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
        st.error("ERRORE CREDENZIALI: Controlla Secrets o file locale.")
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
    st.toast("SALVATAGGIO RIUSCITO")

def elimina_record(valore_chiave, sheet_name="Foglio1", key_field="Codice"):
    wks = get_worksheet(sheet_name)
    df = carica_dati(sheet_name)
    if not df.empty and key_field in df.columns:
        df_final = df[df[key_field].astype(str) != str(valore_chiave)]
        wks.clear()
        wks.update([df_final.columns.values.tolist()] + df_final.values.tolist())
        st.toast(f"ELEMENTO ELIMINATO")
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
            settore = st.selectbox("Settore", settori, index=val_sett, key="f_settore")
        with c1:
            mappa_settori = {"RILIEVO": "RIL", "ARCHEOLOGIA": "ARC", "INTEGRATI": "INT"}
            if is_edit: codice = st.text_input("Codice", value=val_codice, disabled=True)
            else: codice = st.text_input("Codice", value=f"{mappa_settori[settore]}/{anno}-001")
        with c4:
            idx_stato = ["APERTA", "CHIUSA", "IN ATTESA"].index(data["Stato"]) if is_edit and "Stato" in data else 0
            stato_header = st.selectbox("Stato Commessa", ["APERTA", "CHIUSA", "IN ATTESA"], index=idx_stato)
        
        st.markdown("<br>", unsafe_allow_html=True)
        nome_commessa = st.text_input("Nome Commessa", value=val_oggetto, placeholder="Es. Rilievo Chiesa...")
        st.markdown("<br>", unsafe_allow_html=True)
        servizi_scelti = st.multiselect("Servizi Richiesti", SERVIZI_LIST, default=val_servizi)

    with st.expander("02 // COMMITTENZA", expanded=True):
        def on_cliente_change():
            sel = st.session_state["sel_cliente_box"]
            if sel and sel != "NUOVO CLIENTE" and sel in lista_clienti:
                row = df_clienti[df_clienti["Denominazione"] == sel].iloc[0]
                st.session_state["form_piva"] = row["P_IVA"]
                st.session_state["form_sede"] = row["Sede"]
                st.session_state["form_ref"] = row["Referente"]
                st.session_state["form_tel"] = str(row.get("Telefono", ""))
            elif sel == "NUOVO CLIENTE":
                st.session_state["form_piva"] = ""
                st.session_state["form_sede"] = ""
                st.session_state["form_ref"] = ""
                st.session_state["form_tel"] = ""

        try:
            current_cli = st.session_state.get("form_cliente", "")
            display_list = ["NUOVO CLIENTE"] + lista_clienti
            if current_cli and current_cli not in display_list: display_list.append(current_cli)
            idx_cli = display_list.index(current_cli) if current_cli in display_list else 0
        except: idx_cli = 0

        sel_val = st.selectbox("Seleziona Cliente esistente o Nuovo", display_list, index=idx_cli, key="sel_cliente_box", on_change=on_cliente_change)
        if sel_val == "NUOVO CLIENTE":
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
        coordinatore = c1.selectbox("Project Manager", SOCI_OPZIONI, index=idx_pm)
        idx_soc = SOCI_OPZIONI.index(data.get("Portatore", SOCI_OPZIONI[0])) if is_edit and data.get("Portatore") in SOCI_OPZIONI else 0
        portatore = c2.selectbox("Socio Portatore", SOCI_OPZIONI, index=idx_soc)

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
            "Voce": st.column_config.SelectboxColumn("Voce", options=["Acconto", "Saldo"], required=True, width="medium"),
            "Importo netto €": st.column_config.NumberColumn("Importo netto €", format="€ %.2f", required=True, width="small"),
            "IVA %": st.column_config.SelectboxColumn("IVA %", options=[0, 22], required=True, width="small"),
            "Importo lordo €": st.column_config.NumberColumn("Importo lordo €", format="€ %.2f", disabled=True, width="small"),
            "Stato": st.column_config.SelectboxColumn("Stato", options=["Previsto", "Fatturato"], required=True, width="small"),
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
            "Socio": st.column_config.SelectboxColumn("Socio", options=SOCI_OPZIONI, required=True, width="medium"),
            "Mansione": st.column_config.TextColumn("Mansione", width="medium"),
            "Importo": st.column_config.NumberColumn("Importo €", format="€ %.2f", required=True, width="small"),
            "Stato": st.column_config.SelectboxColumn("Stato", options=["Da pagare", "Conteggiato", "Fatturato"], required=True, width="small"),
            "Note": st.column_config.TextColumn("Note", width="medium")
        }
        edited_soci = st.data_editor(df_soci_def, num_rows="dynamic", column_config=soci_cfg, use_container_width=True, key="ed_soc")

        st.markdown("### COLLABORATORI")
        collab_cfg = {
            "Collaboratore": st.column_config.TextColumn("Collaboratore", width="medium"),
            "Mansione": st.column_config.TextColumn("Mansione", width="medium"),
            "Importo": st.column_config.NumberColumn("Importo €", format="€ %.2f", required=True, width="small"),
            "Stato": st.column_config.SelectboxColumn("Stato", options=["Da pagare", "Fatturato"], required=True, width="small"),
            "Note": st.column_config.TextColumn("Note", width="medium")
        }
        edited_collab = st.data_editor(df_collab_def, num_rows="dynamic", column_config=collab_cfg, use_container_width=True, key="ed_col")

        st.markdown("### SPESE VARIE")
        spese_cfg = {
            "Voce": st.column_config.TextColumn("Voce", width="large"), 
            "Importo": st.column_config.NumberColumn("Importo €", format="€ %.2f", required=True, width="small"),
            "Stato": st.column_config.SelectboxColumn("Stato", options=["Da pagare", "Pagato"], required=True, width="small"),
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
                st.toast(f"Nuovo cliente: aggiungo '{nome_cliente_finale}' alla rubrica...")
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
        with st.expander("ZONA PERICOLO"):
            if st.button("ELIMINA DEFINITIVAMENTE", key="btn_del"): elimina_record(codice, "Foglio1", "Codice")

# --- 4. CLIENTI PAGE ---
def render_clienti_page():
    st.markdown("<h2 style='text-align: center;'>ARCHIVIO CLIENTI</h2>", unsafe_allow_html=True)
    st.markdown("---")
    c_form, c_list = st.columns([1, 2], gap="large")
    with c_form:
        st.markdown("<h3 style='text-align: center;'>GESTIONE</h3>", unsafe_allow_html=True)
        df = carica_dati("Clienti")
        
        if not df.empty and "Denominazione" in df.columns:
            nomi = sorted(df["Denominazione"].unique().tolist())
        else:
            nomi = []

        sel_cli = st.selectbox("Seleziona Cliente", ["NUOVO CLIENTE"] + nomi)

        if sel_cli == "NUOVO CLIENTE":
            denominazione = st.text_input("Denominazione *")
            p_iva = st.text_input("P.IVA / CF")
            sede = st.text_input("Sede Legale")
            ref = st.text_input("Referente")
            tel = st.text_input("Telefono")
            settore_cli = st.selectbox("Settore", ["PUBBLICO", "PRIVATO", "ALTRO"])
            note_cli = st.text_area("Note")
            attivo = st.checkbox("Attivo", value=True)
            
            if st.button("SALVA NUOVO CLIENTE"):
                if denominazione:
                    rec = {
                        "Denominazione": denominazione, "P_IVA": p_iva, "Sede": sede,
                        "Referente": ref, "Telefono": tel, "Settore": settore_cli, 
                        "Note": note_cli, "Attivo": str(attivo).upper()
                    }
                    salva_record(rec, "Clienti", "Denominazione", "new")
                    st.rerun()
        else:
            # Modifica esistente
            row = df[df["Denominazione"] == sel_cli].iloc[0]
            denominazione = st.text_input("Denominazione *", value=row["Denominazione"], disabled=True)
            p_iva = st.text_input("P.IVA / CF", value=row["P_IVA"])
            sede = st.text_input("Sede Legale", value=row["Sede"])
            ref = st.text_input("Referente", value=row["Referente"])
            tel = st.text_input("Telefono", value=str(row["Telefono"]))
            
            curr_sett = row.get("Settore", "ALTRO")
            opts_sett = ["PUBBLICO", "PRIVATO", "ALTRO"]
            idx_sett = opts_sett.index(curr_sett) if curr_sett in opts_sett else 2
            settore_cli = st.selectbox("Settore", opts_sett, index=idx_sett)
            
            note_cli = st.text_area("Note", value=row.get("Note", ""))
            is_active = True if str(row.get("Attivo", "TRUE")).upper() == "TRUE" else False
            attivo = st.checkbox("Attivo", value=is_active)

            c_btn1, c_btn2 = st.columns(2)
            if c_btn1.button("AGGIORNA CLIENTE"):
                rec = {
                    "Denominazione": row["Denominazione"], "P_IVA": p_iva, "Sede": sede,
                    "Referente": ref, "Telefono": tel, "Settore": settore_cli, 
                    "Note": note_cli, "Attivo": str(attivo).upper()
                }
                salva_record(rec, "Clienti", "Denominazione", "update")
                st.rerun()
            
            if c_btn2.button("ELIMINA CLIENTE"):
                elimina_record(row["Denominazione"], "Clienti", "Denominazione")

    with c_list:
        st.markdown("<h3 style='text-align: center;'>RUBRICA</h3>", unsafe_allow_html=True)
        if not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("Nessun cliente in archivio.")

# --- 5. ORGANIGRAMMA / SOCIETA PAGE ---
def render_societa_page():
    st.markdown("<h2 style='text-align: center;'>ORGANIGRAMMA STUDIO</h2>", unsafe_allow_html=True)
    st.markdown("---")
    
    # Esempio statico basato sui nomi forniti
    c1, c2, c3 = st.columns(3)
    with c1: st.info("BERTOCCI STEFANO\n(Socio)")
    with c2: st.info("PANCANI GIOVANNI\n(Socio)")
    with c3: st.info("MINUTOLI GIOVANNI\n(Socio)")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    c4, c5, c6, c7 = st.columns(4)
    with c4: st.success("ARRIGHETTI ANDREA\n(Socio)")
    with c5: st.success("LUMINI ANDREA\n(Socio)")
    with c6: st.success("MARASCO LORENZO\n(Socio)")
    with c7: st.success("REPOLE MARCO\n(Socio)")

# --- MAIN: MENU E NAVIGAZIONE ---
menu_scelta = st.sidebar.radio(
    "NAVIGAZIONE",
    ["DASHBOARD & ARCHIVIO", "NUOVA COMMESSA", "CLIENTI", "SOCIETA'"]
)

if "edit_code" not in st.session_state: st.session_state["edit_code"] = None

if st.session_state["edit_code"]:
    st.sidebar.markdown("---")
    if st.sidebar.button("TORNA ALLA DASHBOARD"):
        st.session_state["edit_code"] = None
        st.rerun()
    
    df = carica_dati("Foglio1")
    row_data = df[df["Codice"].astype(str) == str(st.session_state["edit_code"])]
    if not row_data.empty:
        render_commessa_form(row_data.iloc[0].to_dict())
    else:
        st.error("Commessa non trovata.")
        st.session_state["edit_code"] = None

else:
    if menu_scelta == "DASHBOARD & ARCHIVIO":
        st.markdown("## DASHBOARD COMMESSE")
        st.markdown("---")
        
        df = carica_dati("Foglio1")
        if df.empty:
            st.info("Nessuna commessa presente.")
        else:
            c_search, c_filter = st.columns([3, 1])
            search_txt = c_search.text_input("Cerca (Nome, Codice, Cliente)...")
            filter_stat = c_filter.multiselect("Stato", ["APERTA", "CHIUSA", "IN ATTESA"], default=["APERTA"])
            
            dff = df.copy()
            if filter_stat:
                dff = dff[dff["Stato"].isin(filter_stat)]
            if search_txt:
                dff = dff[dff.astype(str).apply(lambda x: x.str.contains(search_txt, case=False)).any(axis=1)]
            
            st.markdown(f"**Trovate {len(dff)} commesse**")
            
            h1, h2, h3, h4, h5 = st.columns([1.5, 3, 2, 1.5, 1])
            h1.markdown("**CODICE**")
            h2.markdown("**COMMESSA**")
            h3.markdown("**CLIENTE**")
            h4.markdown("**IMPORTO**")
            h5.markdown("**AZIONI**")
            st.divider()
            
            for idx, row in dff.iterrows():
                c1, c2, c3, c4, c5 = st.columns([1.5, 3, 2, 1.5, 1])
                c1.text(row["Codice"])
                c2.markdown(f"**{row['Nome Commessa']}**")
                c3.text(row["Cliente"])
                c4.text(fmt_euro(row["Totale Commessa"]))
                
                if c5.button("APRI", key=f"btn_{row['Codice']}"):
                    st.session_state["edit_code"] = row["Codice"]
                    st.rerun()
                st.markdown("---")

    elif menu_scelta == "NUOVA COMMESSA":
        render_commessa_form(None)

    elif menu_scelta == "CLIENTI":
        render_clienti_page()

    elif menu_scelta == "SOCIETA'":
        render_societa_page()

```
