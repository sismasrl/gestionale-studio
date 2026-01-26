import streamlit as st
import pandas as pd
import json
import re
from datetime import date
import io
import time

st.set_page_config(page_title="Convertitore SISMA", layout="wide")

st.markdown("# 🛠️ CONVERTITORE SCHEDE -> ARCHIVIO")
st.markdown("---")
st.info("Carica il file **SCHEDE LAVORI.xlsx** per trasformarlo nel file **Backup_SISMA.xlsx** pronto per l'importazione nella Dashboard.")

# --- FUNZIONI DI UTILITÀ ---
def clean_val(val):
    if pd.isna(val): return ""
    return str(val).strip()

def clean_money(val):
    if pd.isna(val): return 0.0
    s = str(val).replace('€', '').replace(' ', '')
    if ',' in s and '.' in s: s = s.replace('.', '').replace(',', '.')
    elif ',' in s: s = s.replace(',', '.')
    try: return float(s)
    except: return 0.0

def find_in_grid(df, keywords, col_offset=1, row_offset=0):
    for r_idx, row in df.iterrows():
        for c_idx, cell in enumerate(row):
            if isinstance(cell, str):
                cell_upper = cell.upper()
                if any(k in cell_upper for k in keywords):
                    try:
                        target_r = r_idx + row_offset
                        target_c = c_idx + col_offset
                        if target_r < len(df) and target_c < len(df.columns):
                            return clean_val(df.iloc[target_r, target_c])
                    except: pass
    return ""

# --- CARICAMENTO FILE ---
uploaded_file = st.file_uploader("Trascina qui 'SCHEDE LAVORI.xlsx'", type=["xlsx"])

if uploaded_file:
    if st.button("🚀 AVVIA CONVERSIONE", type="primary", use_container_width=True):
        with st.spinner("Lettura e conversione in corso..."):
            try:
                xls = pd.ExcelFile(uploaded_file)
                data_rows = []
                
                target_columns = [
                    "Codice", "Anno", "Nome Commessa", "Cliente", "P_IVA", "Sede", 
                    "Referente", "Tel Referente", "PM", "Portatore", "Settore", "Stato", 
                    "Totale Commessa", "Fatturato", "Portatore_Val", "Costi Società", 
                    "Utile Netto", "Data Inserimento", "Dati_JSON"
                ]

                prog_bar = st.progress(0)
                total_sheets = len(xls.sheet_names)

                for i, sheet_name in enumerate(xls.sheet_names):
                    try:
                        df = pd.read_excel(xls, sheet_name=sheet_name, header=None)
                        
                        # LOGICA DI ESTRAZIONE
                        codice_raw = sheet_name.strip()
                        match = re.search(r'(\d{1,2}-\d{2})', codice_raw)
                        if match:
                            codice_raw = match.group(1)
                            try:
                                yy = codice_raw.split("-")[1]
                                anno = f"20{yy}"
                            except: anno = str(date.today().year)
                        else:
                            anno = str(date.today().year)

                        full_text = df.to_string().upper()
                        if "ARCHEO" in full_text: 
                            settore = "ARCHEOLOGIA"
                            prefix = "ARC"
                        elif any(x in full_text for x in ["RILIEVO", "LASER", "SCANNER"]):
                            settore = "RILIEVO"
                            prefix = "RIL"
                        else:
                            settore = "INTEGRATI"
                            prefix = "INT"
                        
                        codice_finale = f"{prefix}/{anno}-{codice_raw}"

                        nome = find_in_grid(df, ["COMMESSA", "OGGETTO"], row_offset=1, col_offset=0)
                        if not nome: nome = find_in_grid(df, ["COMMESSA", "OGGETTO"], row_offset=0, col_offset=1)
                        
                        cliente = find_in_grid(df, ["DENOMINAZIONE", "CLIENTE"], col_offset=2)
                        if not cliente: cliente = find_in_grid(df, ["DENOMINAZIONE"], col_offset=1)
                        
                        piva = find_in_grid(df, ["P.IVA", "CODICE FISCALE"], col_offset=2)
                        sede = find_in_grid(df, ["INDIRIZZO", "SEDE"], col_offset=2)
                        ref = find_in_grid(df, ["REFERENTE"], col_offset=2)
                        
                        pm = find_in_grid(df, ["COORDINATORE", "PROJECT MANAGER"], col_offset=2)
                        portatore = find_in_grid(df, ["PORTATORE"], col_offset=2)
                        
                        totale = clean_money(find_in_grid(df, ["IMPORTO NETTO", "TOTALE COMMESSA"], col_offset=2))
                        
                        stato_raw = find_in_grid(df, ["STATO"], col_offset=0, row_offset=1)
                        if not stato_raw: stato_raw = find_in_grid(df, ["STATO"], col_offset=1)
                        stato = "CHIUSA" if "CHIUS" in stato_raw.upper() else "APERTA"

                        servizi_list = []
                        if "ARCHEO" in full_text: servizi_list.append("Archeologia Preventiva")
                        if "RILIEVO" in full_text: servizi_list.append("Rilievo Laser Scanner")

                        json_data = {
                            "incassi": [], "soci": [], "collab": [], "spese": [], 
                            "servizi": servizi_list,
                            "percentages": {"portatore": 10, "societa": 10}
                        }

                        row = {
                            "Codice": codice_finale, "Anno": int(anno),
                            "Nome Commessa": nome if nome else f"Commessa {codice_raw}",
                            "Cliente": cliente, "P_IVA": piva, "Sede": sede,
                            "Referente": ref, "Tel Referente": "",
                            "PM": pm, "Portatore": portatore,
                            "Settore": settore, "Stato": stato,
                            "Totale Commessa": totale,
                            "Fatturato": totale if stato == "CHIUSA" else 0.0,
                            "Portatore_Val": 0.0, "Costi Società": 0.0, "Utile Netto": 0.0,
                            "Data Inserimento": str(date.today()),
                            "Dati_JSON": json.dumps(json_data)
                        }
                        data_rows.append(row)
                    except: pass
                    prog_bar.progress((i + 1) / total_sheets)

                df_final = pd.DataFrame(data_rows)
                # Assicura tutte le colonne
                for c in target_columns:
                    if c not in df_final.columns: df_final[c] = ""
                df_final = df_final[target_columns]

                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    df_final.to_excel(writer, index=False, sheet_name='Archivio_SISMA')
                
                st.success(f"✅ Conversione completata! Estratte {len(df_final)} commesse.")
                st.download_button(
                    label="📥 SCARICA FILE COMPILATO (.xlsx)",
                    data=buffer,
                    file_name="Backup_SISMA_Compilato.xlsx",
                    mime="application/vnd.ms-excel",
                    type="primary",
                    use_container_width=True
                )

            except Exception as e:
                st.error(f"Errore: {e}")
