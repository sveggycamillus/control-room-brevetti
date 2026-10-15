import streamlit as st
from supabase import create_client, Client

# --- 1. CONNESSIONE ---
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

# LA TUA EMAIL AMMINISTRATORE (Modifica questa riga!)
EMAIL_ADMIN = "sveva@studio.it" 

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Control Room Brevetti", layout="wide")

if 'utente_loggato' not in st.session_state:
    st.session_state.utente_loggato = False

if st.session_state.utente_loggato and 'access_token' in st.session_state:
    supabase.auth.set_session(st.session_state.access_token, st.session_state.refresh_token)

# --- 2. SCHERMATA DI ACCESSO ---
if not st.session_state.utente_loggato:
    st.title("Area Riservata Studio 🔐")
    st.divider()
    
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        tasto_login = st.form_submit_button("Accedi")
        
        if tasto_login:
            try:
                risposta = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.utente_loggato = True
                st.session_state.user_id = risposta.user.id
                st.session_state.email = email # <-- Salviamo l'email per capire chi è!
                st.session_state.access_token = risposta.session.access_token
                st.session_state.refresh_token = risposta.session.refresh_token
                st.rerun() 
            except Exception as e:
                st.error("Accesso negato. Email o password errati.")

# --- 3. CONTROL ROOM ---
else:
    col_titolo, col_esci = st.columns([8, 1])
    with col_titolo:
        st.title("Control Room Operativa ⚙️")
    with col_esci:
        if st.button("Esci 🚪"):
            supabase.auth.sign_out()
            st.session_state.utente_loggato = False
            st.session_state.pop('access_token', None)
            st.session_state.pop('refresh_token', None)
            st.session_state.pop('email', None)
            st.rerun()
            
    st.divider()

    # --- MODULO INSERIMENTO (VISIBILE SOLO ALL'AMMINISTRATORE) ---
    if st.session_state.email == EMAIL_ADMIN:
        st.subheader("➕ Registra Nuova Invenzione")
        with st.form("modulo_nuovo_brevetto", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                titolo = st.text_input("Titolo Provvisorio")
                # L'admin ora assegna la pratica inserendo l'ID del cliente
                cliente_assegnato = st.text_input("ID Cliente (UID da Supabase)") 
            with col2:
                riferimento = st.text_input("Rif. Interno (es. PRJ-001)")
                file_allegato = st.file_uploader("Allega Relazione o Disegno Tecnico (PDF, JPG, PNG)", type=['pdf', 'png', 'jpg'])
                
            pulsante_salva = st.form_submit_button("Salva nel Database")
            
            if pulsante_salva:
                if titolo and riferimento and cliente_assegnato:
                    try:
                        nuovi_dati = {
                            "provisional_title": titolo,
                            "internal_ref": riferimento,
                            "client_id": cliente_assegnato # Ora il file si lega al cliente giusto!
                        }
                        supabase.table("inventions").insert(nuovi_dati).execute()
                        
                        if file_allegato:
                            nome_file_storage = f"{riferimento}_{file_allegato.name}"
                            file_bytes = file_allegato.getvalue()
                            supabase.storage.from_("documenti").upload(nome_file_storage, file_bytes)
                            
                        st.success("✅ Pratica assegnata e documenti salvati!")
                    except Exception as e:
                        st.error(f"Errore: {e}")
                else:
                    st.warning("⚠️ Titolo, Riferimento e ID Cliente sono obbligatori.")
        st.divider()

    # --- ARCHIVIO PRATICHE (DINAMICO) ---
    st.subheader("📚 Archivio Pratiche")
    try:
        if st.session_state.email == EMAIL_ADMIN:
            # L'admin vede tutto
            st.caption("👀 Visualizzazione: **Amministratore (Tutte le pratiche)**")
            risposta = supabase.table("inventions").select("*").order("created_at", desc=True).execute()
        else:
            # Il cliente vede solo i suoi brevetti
            st.caption(f"👀 Visualizzazione: **Cliente** ({st.session_state.email})")
            risposta = supabase.table("inventions").select("*").eq("client_id", st.session_state.user_id).order("created_at", desc=True).execute()
            
        if len(risposta.data) > 0:
            st.dataframe(risposta.data, use_container_width=True)
        else:
            st.info("Nessuna pratica trovata.")
    except Exception as e:
        st.error(f"Errore di lettura: {e}")

    # --- 4. AREA DOWNLOAD DOCUMENTI ---
    st.divider()
    st.subheader("📂 Documenti Tecnici Allegati")
    try:
        lista_file = supabase.storage.from_("documenti").list()
        file_veri = [f for f in lista_file if f['name'] != '.emptyFolderPlaceholder']
        
        if len(file_veri) > 0:
            for file in file_veri:
                col_nome, col_tasto = st.columns([3, 1])
                with col_nome:
                    st.write(f"📄 **{file['name']}**")
                with col_tasto:
                    dati_file = supabase.storage.from_("documenti").download(file['name'])
                    st.download_button(label="⬇️ Scarica", data=dati_file, file_name=file['name'], key=file['name'])
        else:
            st.info("Nessun documento archiviato al momento.")
    except Exception as e:
        st.error(f"Errore storage: {e}")