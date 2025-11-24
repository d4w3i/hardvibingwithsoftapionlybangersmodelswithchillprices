# Architettura del Progetto Chatbot Platform

## Indice
1. [Visione Generale](#visione-generale)
2. [Stack Tecnologico e Motivazioni](#stack-tecnologico-e-motivazioni)
3. [Architettura del Database](#architettura-del-database)
4. [Architettura Backend](#architettura-backend)
5. [Sistema di Sicurezza](#sistema-di-sicurezza)
6. [Pattern di Design Utilizzati](#pattern-di-design-utilizzati)
7. [Flussi Principali](#flussi-principali)
8. [Estendibilità e Scalabilità](#estendibilità-e-scalabilità)

---

## Visione Generale

### Obiettivo del Progetto
Creare una piattaforma chatbot multi-utente dove:
- Ogni utente porta la propria API key (OpenAI/Anthropic)
- Nessun costo per il proprietario della piattaforma
- Supporto per multipli framework AI (LangGraph, LangChain, OpenAI SDK, ecc.)
- Persistenza delle conversazioni
- Sicurezza delle credenziali utente

### Principi Architetturali
1. **Separation of Concerns** - Ogni componente ha una responsabilità specifica
2. **Framework Agnostic** - Possibilità di aggiungere qualsiasi framework AI
3. **Security First** - API keys crittografate, autenticazione JWT
4. **Scalabilità** - Architettura a livelli che permette crescita
5. **Developer Experience** - Codice leggibile, ben documentato, facile da estendere

---

## Stack Tecnologico e Motivazioni

### Backend: FastAPI (Python)

**Scelta:** FastAPI invece di Flask, Django, Express.js, ecc.

**Motivazioni:**
1. **Performance eccezionali** - Basato su Starlette e Pydantic, è uno dei framework Python più veloci
2. **Async nativo** - Supporto nativo per `async/await`, fondamentale per lo streaming AI
3. **Validazione automatica** - Pydantic valida automaticamente input/output
4. **Documentazione automatica** - Genera Swagger UI e ReDoc senza configurazione
5. **Type hints** - Sfrutta i type hints Python per sicurezza del codice
6. **Dependency Injection** - Sistema DI integrato per gestire DB, auth, ecc.

**Esempio del vantaggio:**
```python
# Con FastAPI
class Message(BaseModel):
    content: str
    role: str

@app.post("/chat")
def chat(message: Message):  # ✅ Validazione automatica
    return {"received": message.content}

# Senza FastAPI (Flask)
@app.post("/chat")
def chat():
    data = request.json
    if not data or "content" not in data:  # ❌ Validazione manuale
        return {"error": "Invalid input"}, 400
    # ... più codice boilerplate
```

### Database: MySQL + SQLAlchemy

**Scelta:** MySQL invece di PostgreSQL, MongoDB, SQLite

**Motivazioni:**
1. **Relazioni complesse** - Abbiamo users → conversations → messages (relazioni 1:N)
2. **ACID compliance** - Transazioni affidabili per dati critici (API keys, messaggi)
3. **Maturità** - MySQL è estremamente stabile e ben supportato
4. **SQLAlchemy ORM** - Ci permette di scrivere Python invece di SQL

**Perché non NoSQL?**
- MongoDB non ha foreign keys native (relazioni più complesse da gestire)
- I nostri dati sono fortemente relazionali (user ↔ conversations ↔ messages)
- Necessitiamo di transazioni ACID per garantire integrità

**SQLAlchemy come ORM:**
```python
# Invece di scrivere SQL
cursor.execute("SELECT * FROM users WHERE email = ?", (email,))

# Scriviamo Python
user = db.query(User).filter(User.email == email).first()
```

### Package Manager: uv

**Scelta:** uv invece di pip, poetry, conda

**Motivazioni:**
1. **Velocità estrema** - Scritto in Rust, 10-100x più veloce di pip
2. **Gestione automatica venv** - Non serve creare manualmente virtual environment
3. **Lock file** - Dipendenze riproducibili (come package-lock.json in npm)
4. **Comando unico** - `uv run` esegue nel venv senza attivarlo manualmente

**Confronto:**
```bash
# Con pip (vecchio modo)
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py

# Con uv (nuovo modo)
uv sync
uv run python main.py
```

### AI Frameworks: LangChain + LangGraph + SDK nativi

**Scelta:** Supporto multiplo invece di un solo framework

**Motivazioni:**
1. **Flessibilità** - L'utente sceglie il framework preferito
2. **Feature specifiche** - LangGraph per workflow complessi, SDK per semplicità
3. **Futuro-proof** - Nuovi framework possono essere aggiunti facilmente
4. **Best tool for the job** - Ogni agente può usare lo stack più adatto

**Architettura a plugin:**
```python
# Aggiungere un nuovo framework è triviale
class NewFrameworkService(BaseAIService):
    async def chat(self, message: str):
        # Implementazione specifica
        pass

# Registrazione nel factory
elif agent_type == "new_framework":
    return NewFrameworkService(api_key)
```

---

## Architettura del Database

### Schema Completo

```
┌─────────────────────────┐
│       users             │
├─────────────────────────┤
│ id (PK)                 │
│ email (UNIQUE)          │
│ name                    │
│ hashed_password         │
│ created_at              │
│ updated_at              │
└───────┬─────────────────┘
        │
        │ 1:N
        │
        ├──────────────────────────────────┐
        │                                  │
        ▼                                  ▼
┌─────────────────────────┐    ┌─────────────────────────┐
│   conversations         │    │      api_keys           │
├─────────────────────────┤    ├─────────────────────────┤
│ id (PK)                 │    │ id (PK)                 │
│ user_id (FK)            │    │ user_id (FK)            │
│ title                   │    │ provider (ENUM)         │
│ agent_type ⭐          │    │ encrypted_key ⭐       │
│ provider (ENUM) ⭐      │    │ created_at              │
│ created_at              │    │ updated_at              │
│ updated_at              │    └─────────────────────────┘
└───────┬─────────────────┘
        │
        │ 1:N
        │
        ▼
┌─────────────────────────┐
│      messages           │
├─────────────────────────┤
│ id (PK)                 │
│ conversation_id (FK)    │
│ role (ENUM)             │
│ content (TEXT)          │
│ created_at              │
└─────────────────────────┘
```

### Tabella: users

**Scopo:** Gestire gli account utente

**Campi chiave:**
- `email` - UNIQUE constraint per evitare duplicati
- `hashed_password` - Password **mai** in chiaro, solo hash bcrypt
- Timestamp per audit trail

**Decisioni di design:**
- **Perché bcrypt per le password?**
  - Algoritmo specifico per password (lento di proposito contro brute force)
  - Salt automatico incluso
  - Configurabile con "rounds" per aumentare sicurezza

```python
# Hashing sicuro
hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
# Verifica
valid = bcrypt.checkpw(password.encode(), hashed)
```

### Tabella: conversations

**Scopo:** Rappresentare una chat tra utente e AI

**Campi innovativi:**
- `agent_type` ⭐ - Quale framework AI usare ("langgraph", "openai_direct", ecc.)
- `provider` ⭐ - Quale LLM backend ("openai", "anthropic")

**Perché questi campi?**

**Problema senza agent_type:**
```python
# Senza flag, come sappiamo quale agente usare?
conversation = db.query(Conversation).get(1)
# ❌ Non sappiamo se è LangGraph, OpenAI SDK, o altro
```

**Soluzione con agent_type:**
```python
conversation = db.query(Conversation).get(1)
if conversation.agent_type == "langgraph":
    service = LangGraphService(...)
elif conversation.agent_type == "openai_direct":
    service = OpenAIDirectService(...)
# ✅ Ogni conversazione "ricorda" il suo agente
```

**Benefici:**
1. **Persistenza delle scelte** - Riaprendo una chat dopo giorni, usa lo stesso agente
2. **Analytics** - "Quale agente è più usato?"
3. **UI migliore** - Possiamo mostrare badge "LangGraph • GPT-4"
4. **Debugging** - Sappiamo esattamente quale stack ha generato ogni risposta

**Perché ENUM per provider?**
```python
provider = Column(Enum("openai", "anthropic"), nullable=False)
```
- **Validazione DB-level** - MySQL rifiuta valori non validi
- **Type safety** - Pydantic valida automaticamente
- **Documentazione** - Chiaro quali sono i valori possibili

### Tabella: messages

**Scopo:** Storico completo della conversazione

**Campi:**
- `role` - ENUM("user", "assistant", "system")
- `content` - TEXT per messaggi lunghi (fino a 65,535 caratteri)

**Perché role come ENUM?**
- Compatibile con API OpenAI/Anthropic (usano stesso formato)
- Possiamo passare direttamente al modello:

```python
# Recupera storico
messages = db.query(Message).filter(...)

# Converte per OpenAI (formato identico!)
openai_messages = [
    {"role": msg.role.value, "content": msg.content}
    for msg in messages
]
```

**Decisione: TEXT vs VARCHAR**
- TEXT: fino a 65KB, sufficiente per la maggior parte dei messaggi
- Se servisse di più, potremmo usare LONGTEXT (4GB)
- VARCHAR(255) sarebbe troppo limitante per risposte AI

### Tabella: api_keys

**Scopo:** Salvare in modo sicuro le API key degli utenti

**Campo critico:** `encrypted_key`

**Decisione cruciale: Crittografia invece di plaintext**

```python
# ❌ PESSIMA IDEA (plaintext)
api_key = "sk-proj-abc123..."
db.execute("INSERT INTO api_keys VALUES (?)", api_key)

# ✅ CORRETTO (encrypted)
encrypted = encrypt_api_key("sk-proj-abc123...")  # Fernet encryption
db.execute("INSERT INTO api_keys VALUES (?)", encrypted)
```

**Constraint:** `UNIQUE(user_id, provider)`
- Un utente può avere **1 sola** chiave per provider
- Può avere sia OpenAI che Anthropic, ma non 2 chiavi OpenAI

**Perché?**
- Semplifica la logica (non serve scegliere quale chiave usare)
- Se l'utente aggiorna la chiave, sovrascrive quella esistente

**Relazione con conversations:**
```python
# Quando l'utente chatta
conversation = db.query(Conversation).get(1)  # provider="openai"
api_key = db.query(ApiKey).filter(
    ApiKey.user_id == user.id,
    ApiKey.provider == conversation.provider  # ✅ Match automatico
).first()
```

### Decisioni CASCADE

```python
ForeignKey("users.id", ondelete="CASCADE")
```

**Significato:** Se elimini un utente, elimina automaticamente:
- Tutte le sue conversazioni
- Tutti i messaggi nelle conversazioni
- Tutte le sue API keys

**Perché CASCADE?**
- **GDPR compliance** - "Diritto all'oblio" (un comando elimina tutto)
- **Integrità** - Non rimangono "orfani" (conversazioni senza utente)
- **Semplificazione** - Non serve cancellare manualmente ogni tabella

**Alternativa evitata:** RESTRICT
```python
# Con RESTRICT
user.delete()  # ❌ ERROR: Foreign key constraint
# Dovremmo fare:
for conv in user.conversations:
    for msg in conv.messages:
        msg.delete()
    conv.delete()
user.api_keys.delete()
user.delete()  # ✅ Solo ora funziona
```

---

## Architettura Backend

### Struttura a Livelli

```
┌─────────────────────────────────────────────┐
│              PRESENTATION LAYER              │
│  app/routes/ (auth.py, chat.py, conv.py)   │
│  - Riceve HTTP requests                     │
│  - Valida input con Pydantic                │
│  - Chiama business logic                    │
│  - Ritorna HTTP responses                   │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│            BUSINESS LOGIC LAYER             │
│         app/services/ (ai_service.py)       │
│  - Logica applicativa                       │
│  - Orchestrazione agenti AI                 │
│  - Crittografia/decrittografia             │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│              DATA ACCESS LAYER              │
│     app/models.py + app/database.py         │
│  - ORM SQLAlchemy                           │
│  - Query database                           │
│  - Gestione sessioni                        │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│                 DATABASE                    │
│                  MySQL                      │
└─────────────────────────────────────────────┘
```

### File: app/config.py

**Scopo:** Centralizzare tutta la configurazione

**Tecnologia:** Pydantic Settings

**Decisione chiave:** Settings class invece di variabili globali

```python
# ❌ Approccio vecchio
import os
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))  # Conversione manuale

# ✅ Approccio moderno
class Settings(BaseSettings):
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306  # Type hint = conversione automatica
```

**Vantaggi:**
1. **Validazione automatica** - Pydantic valida che PORT sia int
2. **Type safety** - IDE sa che `settings.MYSQL_PORT` è int
3. **Defaults** - Valori di default chiari
4. **Documentazione** - Tutti i settings in un posto

**Feature: @property per database_url**
```python
@property
def database_url(self) -> str:
    return f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}..."
```

**Perché?**
- Evita duplicazione (URL costruito da componenti)
- Logica centralizzata
- Cambio password → URL si aggiorna automaticamente

**Pattern Singleton:**
```python
settings = Settings()  # Istanza globale
```
Tutti importano la stessa istanza (non ricrea ad ogni import).

### File: app/database.py

**Scopo:** Gestire connessione al database

**Componenti:**

1. **Engine** - Il "motore" SQLAlchemy
```python
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,      # Verifica connessione prima di usarla
    pool_recycle=3600,       # Ricrea connessioni dopo 1h
    echo=settings.DEBUG      # Log SQL in development
)
```

**Decisioni:**
- `pool_pre_ping=True` - Evita "MySQL has gone away" error
- `pool_recycle=3600` - MySQL chiude connessioni idle dopo 8h, noi le rinnoviamo prima
- `echo=DEBUG` - Vediamo SQL in dev, spento in production

2. **SessionLocal** - Factory per creare sessioni
```python
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```

**Perché autocommit=False?**
- Controllo esplicito delle transazioni
- Possiamo raggruppare più operazioni in una transazione

3. **get_db() Dependency**
```python
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**Pattern: Dependency Injection**

FastAPI chiama automaticamente `get_db()` e passa il risultato:
```python
@app.get("/users")
def get_users(db: Session = Depends(get_db)):
    return db.query(User).all()
```

**Vantaggi:**
- **Auto-cleanup** - `finally` garantisce chiusura connessione
- **Testabilità** - Possiamo sostituire con mock DB nei test
- **Niente global state** - Ogni richiesta ha la sua sessione

### File: app/models.py

**Scopo:** Definire schema database come classi Python (ORM)

**Pattern: Active Record via SQLAlchemy**

```python
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    conversations = relationship("Conversation", back_populates="user")
```

**Decisioni di design:**

1. **Enums per valori fissi**
```python
class ProviderEnum(str, enum.Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
```

**Vantaggi:**
- Autocomplete nell'IDE
- Validazione Python-level
- Serializzazione automatica in JSON

2. **Relationships bidirezionali**
```python
# In User
conversations = relationship("Conversation", back_populates="user")

# In Conversation
user = relationship("User", back_populates="conversations")
```

**Beneficio:**
```python
user = db.query(User).first()
user.conversations  # ✅ Accesso diretto alle conversazioni (lazy-loaded)

conversation = db.query(Conversation).first()
conversation.user  # ✅ Accesso diretto all'utente
```

3. **Cascade deletes**
```python
messages = relationship("Message", cascade="all, delete-orphan")
```

**Significato:**
- `all` - Propaga tutte le operazioni
- `delete-orphan` - Se rimuovi un messaggio dalla lista, viene cancellato dal DB

4. **Timestamps automatici**
```python
created_at = Column(DateTime, default=datetime.utcnow)
updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

**Vantaggi:**
- Audit trail automatico
- Ordinamenti per "più recente"

### File: app/main.py

**Scopo:** Entry point dell'applicazione

**Struttura:**

1. **Creazione app**
```python
app = FastAPI(
    title="Chatbot Platform API",
    description="...",
    version="0.1.0"
)
```
Questi metadati appaiono in Swagger UI!

2. **CORS Middleware**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
```

**Perché CORS?**

**Problema senza CORS:**
```
Frontend (localhost:3000) → API (localhost:8000)
❌ Browser blocca: "CORS policy: No 'Access-Control-Allow-Origin' header"
```

**Soluzione:**
Backend dice: "Accetto richieste da localhost:3000"

**Perché allow_credentials=True?**
Permette invio di cookies e header Authorization (JWT).

3. **Startup Event**
```python
@app.on_event("startup")
async def startup_event():
    init_db()
```

**Scopo:** Crea tabelle se non esistono

**Alternativa evitata:** Alembic migrations
- Per un MVP, `init_db()` è sufficiente
- In produzione useremmo Alembic per migrazioni controllate

4. **Router Registration**
```python
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
```

**Pattern: Modular Routing**

Invece di tutto in `main.py`:
```python
@app.post("/auth/register")  # ❌ Difficile da mantenere
@app.post("/auth/login")
@app.post("/chat/stream")
# ... 50 endpoint
```

Dividiamo per dominio:
```python
# auth.py ha i suoi endpoint
# chat.py ha i suoi endpoint
# main.py li include
```

---

## Sistema di Sicurezza

### 1. Autenticazione: JWT (JSON Web Tokens)

**Scelta:** JWT invece di session cookies

**Motivazioni:**
- **Stateless** - Server non salva sessioni (scalabile)
- **Mobile-friendly** - Funziona su app native
- **Microservices-ready** - Token può essere validato da altri servizi

**Flow completo:**

```
1. Registrazione/Login
   ↓
   User invia: { email, password }
   ↓
   Backend:
   - Verifica credenziali
   - Crea JWT token con user_id
   ↓
   Ritorna: { access_token: "eyJhbG..." }

2. Richieste successive
   ↓
   User invia: Header "Authorization: Bearer eyJhbG..."
   ↓
   Backend:
   - Decodifica JWT
   - Estrae user_id
   - Carica utente dal DB
   ↓
   Esegue operazione come quell'utente
```

**Implementazione:**
```python
def create_access_token(user_id: int) -> str:
    expire = datetime.utcnow() + timedelta(minutes=10080)  # 7 giorni
    to_encode = {"sub": str(user_id), "exp": expire}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
```

**Token contiene:**
- `sub` (subject) - ID utente
- `exp` (expiration) - Scadenza

**Non contiene:**
- Password (mai!)
- API keys
- Dati sensibili

**Validazione:**
```python
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = jwt.decode(token, settings.SECRET_KEY)
    user_id = payload.get("sub")
    return db.query(User).get(user_id)
```

**Dependency Pattern:**
```python
@app.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    # FastAPI chiama get_current_user automaticamente
    # Se token non valido → 401 Unauthorized
    # Se valido → current_user contiene l'utente
    return current_user
```

### 2. Password Hashing: bcrypt

**Scelta:** bcrypt invece di SHA256, MD5, PBKDF2

**Motivazioni:**
- **Specifico per password** - Progettato per questo uso
- **Adaptive** - "Rounds" configurabili (più rounds = più lento = più sicuro)
- **Salt automatico** - Incluso nell'hash

**Confronto:**
```python
# ❌ SHA256 (troppo veloce, attaccabile con GPU)
import hashlib
hash = hashlib.sha256(password.encode()).hexdigest()

# ✅ bcrypt (lento di proposito, salt incluso)
import bcrypt
hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
```

**Come funziona:**
```python
# Registrazione
password = "MySecret123"
hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
# Salva: $2b$12$L6Bc/AlGoO8vUvCyVO8Lhu.VVmjoJV/GhPOZMDNNH6QgP56sNWS1W
#        ^^^^ ^^^^                                            ^^^^^^^^^^^^^^
#        alg  rounds           salt                           hash

# Login
user_input = "MySecret123"
stored_hash = "$2b$12$L6Bc/..."
valid = bcrypt.checkpw(user_input.encode(), stored_hash)  # True
```

**Perché non salvare password in chiaro?**

**Scenario 1: Database breach**
```
Attaccante ottiene dump del DB:
- Con plaintext → Ha tutte le password
- Con bcrypt → Hash inutilizzabili (bcrack richiederebbe anni)
```

**Scenario 2: Password riutilizzate**
```
User usa stessa password su Gmail e sul nostro sito:
- Con plaintext → Attaccante accede anche a Gmail
- Con bcrypt → Non può risalire alla password originale
```

### 3. API Keys Encryption: Fernet

**Scelta:** Fernet (symmetric encryption) invece di hashing

**Motivazione:** Dobbiamo **decifrare** (usiamo la chiave per chiamare OpenAI)

**Hashing vs Encryption:**
```python
# Hashing (one-way)
hashed = bcrypt.hashpw(password)
# ❌ Non possiamo ottenere "password" da "hashed"
# ✅ Va bene per password (verifichiamo solo se è corretta)

# Encryption (two-way)
encrypted = fernet.encrypt(api_key)
decrypted = fernet.decrypt(encrypted)
# ✅ Possiamo recuperare api_key originale
# ✅ Va bene per API keys (dobbiamo usarle)
```

**Implementazione:**
```python
from cryptography.fernet import Fernet

# Generazione chiave (una volta sola)
encryption_key = Fernet.generate_key()  # Salvato in .env

# Encryption
def encrypt_api_key(api_key: str) -> str:
    fernet = Fernet(settings.ENCRYPTION_KEY)
    encrypted_bytes = fernet.encrypt(api_key.encode())
    return encrypted_bytes.decode()

# Decryption
def decrypt_api_key(encrypted_key: str) -> str:
    fernet = Fernet(settings.ENCRYPTION_KEY)
    decrypted_bytes = fernet.decrypt(encrypted_key.encode())
    return decrypted_bytes.decode()
```

**Flusso completo:**
```
1. User inserisce API key
   "sk-proj-abc123xyz..."
   ↓
2. Backend cripta
   "gAAAAABf3x9kL7mQ..." ← Salvato nel DB
   ↓
3. User invia messaggio
   ↓
4. Backend:
   - Legge "gAAAAABf3x9kL7mQ..." dal DB
   - Decripta → "sk-proj-abc123xyz..."
   - Chiama OpenAI con chiave decifrata
   ↓
5. Risposta AI → User
```

**Sicurezza multi-layer:**

1. **Database breach**
   - Attaccante ottiene: `encrypted_key = "gAAAAAB..."`
   - Serve `ENCRYPTION_KEY` per decifrare (non nel DB, ma in `.env` sul server)

2. **Server compromise**
   - Attaccante ottiene `.env` → Può decifrare
   - **Mitigazione:** `.env` su server separato, env variables di sistema

3. **Best practice:**
   ```bash
   # .env (non committare su git!)
   ENCRYPTION_KEY=5w5tjhtsQvTLuo22coWI9FbNDp9kHToFBye5mfpLsm8=

   # .gitignore
   .env
   ```

### 4. Autorizzazione: Row-Level Security

**Pattern:** Verifica che l'utente possa accedere solo ai suoi dati

**Esempio:**
```python
@router.get("/conversations/{conversation_id}")
def get_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id  # ⭐ Fondamentale
    ).first()

    if not conversation:
        raise HTTPException(status_code=404)
```

**Perché importante?**

**Scenario senza verifica:**
```python
# ❌ Vulnerability
conversation = db.query(Conversation).get(conversation_id)
# User A può accedere alle chat di User B cambiando ID nell'URL!
```

**Scenario con verifica:**
```python
# ✅ Sicuro
conversation = db.query(Conversation).filter(
    Conversation.id == conversation_id,
    Conversation.user_id == current_user.id
).first()
# User A vede solo le sue chat
```

**Applicato ovunque:**
- Conversazioni
- Messaggi
- API keys
- Qualsiasi risorsa dell'utente

---

## Pattern di Design Utilizzati

### 1. Factory Pattern (AgentFactory)

**Scopo:** Creare oggetti senza specificare la classe esatta

**Implementazione:**
```python
class AgentFactory:
    @staticmethod
    def create(agent_type: str, provider: str, api_key: str):
        if agent_type == "langgraph":
            return LangGraphService(api_key, provider)
        elif agent_type == "openai_direct":
            return OpenAIDirectService(api_key)
        # ...
```

**Vantaggi:**
1. **Centralizzazione** - Logica creazione in un posto
2. **Estendibilità** - Aggiungere agente = aggiungere elif
3. **Loose coupling** - Client non conosce classi concrete

**Uso:**
```python
# Client non sa quale classe viene istanziata
service = AgentFactory.create(conversation.agent_type, ...)
response = await service.chat(message)
```

### 2. Strategy Pattern (BaseAIService)

**Scopo:** Algoritmi intercambiabili

**Implementazione:**
```python
class BaseAIService(ABC):
    @abstractmethod
    async def chat(self, message: str) -> AsyncGenerator[str, None]:
        pass

class LangGraphService(BaseAIService):
    async def chat(self, message: str):
        # Implementazione LangGraph
        pass

class OpenAIDirectService(BaseAIService):
    async def chat(self, message: str):
        # Implementazione OpenAI
        pass
```

**Vantaggi:**
1. **Polimorfismo** - Tutti hanno `.chat()` ma implementazione diversa
2. **Testabilità** - Possiamo creare MockService per test
3. **Estendibilità** - Nuovi servizi implementano BaseAIService

**Uso:**
```python
def process_message(service: BaseAIService, message: str):
    # Funziona con qualsiasi servizio
    async for chunk in service.chat(message):
        yield chunk
```

### 3. Dependency Injection

**Scopo:** Fornire dipendenze invece di crearle internamente

**Implementazione FastAPI:**
```python
# Dipendenza
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Utilizzo
@app.get("/users")
def get_users(db: Session = Depends(get_db)):
    return db.query(User).all()
```

**Vantaggi:**
1. **Testabilità:**
```python
# Test
def mock_get_db():
    yield MockDatabase()

app.dependency_overrides[get_db] = mock_get_db
# Ora i test usano MockDatabase
```

2. **Separation of Concerns** - Endpoint non sa come creare DB
3. **Riutilizzo** - Stessa dependency per tutti gli endpoint

### 4. Repository Pattern (implicito in SQLAlchemy)

**Scopo:** Astrazione accesso dati

**Implementazione:**
```python
# Invece di SQL grezzo
cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))

# SQLAlchemy è un repository
user = db.query(User).filter(User.id == user_id).first()
```

**Vantaggi:**
- Cambio DB (MySQL → PostgreSQL) senza cambiare codice
- Query type-safe
- Relazioni gestite automaticamente

### 5. DTO (Data Transfer Objects) con Pydantic

**Scopo:** Validazione e serializzazione dati

**Implementazione:**
```python
class ConversationCreate(BaseModel):
    title: Optional[str] = None
    agent_type: str
    provider: ProviderEnum

@app.post("/conversations")
def create(conv_data: ConversationCreate):
    # conv_data è già validato
    # Se JSON malformato → 422 automatico
```

**Vantaggi:**
1. **Validazione automatica:**
```python
# Request: { "agent_type": 123 }
# ❌ 422 Unprocessable Entity: agent_type must be string
```

2. **Documentazione automatica:**
Swagger UI mostra esattamente quali campi servono

3. **Type safety:**
```python
conv_data.agent_type  # IDE sa che è string
```

---

## Flussi Principali

### Flusso 1: Registrazione Utente

```
1. Frontend → POST /auth/register
   Body: { "email": "user@email.com", "name": "Mario", "password": "Secret123" }
   ↓
2. FastAPI valida con Pydantic
   - Email formato valido?
   - Password fornita?
   ↓
3. auth.py: register()
   - Query DB: email già esistente?
   - Se sì → 400 "Email already registered"
   - Se no → Continua
   ↓
4. Hash password con bcrypt
   hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
   ↓
5. Crea User nel DB
   user = User(email=..., name=..., hashed_password=...)
   db.add(user)
   db.commit()
   ↓
6. Crea JWT token
   token = create_access_token(user.id)
   ↓
7. Risposta → Frontend
   { "access_token": "eyJhbG...", "token_type": "bearer" }
```

### Flusso 2: Aggiunta API Key

```
1. Frontend → POST /auth/api-keys
   Headers: { "Authorization": "Bearer eyJhbG..." }
   Body: { "provider": "openai", "api_key": "sk-proj-abc123..." }
   ↓
2. FastAPI chiama get_current_user dependency
   - Decodifica JWT
   - Carica User dal DB
   - Se token invalido/scaduto → 401 Unauthorized
   ↓
3. auth.py: create_api_key()
   - Check se già esiste chiave per quel provider
   ↓
4. Cripta API key
   encrypted = encrypt_api_key("sk-proj-abc123...")
   # Risultato: "gAAAAABf3x9kL7mQ..."
   ↓
5. Salva nel DB
   api_key = ApiKey(
       user_id=current_user.id,
       provider="openai",
       encrypted_key=encrypted
   )
   db.add(api_key)
   db.commit()
   ↓
6. Risposta → Frontend
   { "id": 1, "provider": "openai", "created_at": "..." }
   # Nota: NON ritorna la chiave (sicurezza)
```

### Flusso 3: Creazione Conversazione

```
1. Frontend → POST /conversations
   Headers: { "Authorization": "Bearer ..." }
   Body: {
     "title": "Help with FastAPI",
     "agent_type": "langgraph",
     "provider": "openai"
   }
   ↓
2. Autenticazione (get_current_user dependency)
   ↓
3. conversations.py: create_conversation()
   - Se title vuoto → Auto-genera "New Chat - 2024-01-15 10:30"
   ↓
4. Crea Conversation nel DB
   conversation = Conversation(
       user_id=current_user.id,
       title="Help with FastAPI",
       agent_type="langgraph",  # ⭐ Salvato
       provider="openai"         # ⭐ Salvato
   )
   db.add(conversation)
   db.commit()
   ↓
5. Risposta → Frontend
   {
     "id": 1,
     "title": "Help with FastAPI",
     "agent_type": "langgraph",
     "provider": "openai",
     "created_at": "2024-01-15T10:30:00"
   }
```

### Flusso 4: Invio Messaggio (STREAMING)

**Il flusso più complesso ma fondamentale:**

```
1. Frontend → POST /chat/stream
   Headers: { "Authorization": "Bearer ..." }
   Body: { "conversation_id": 1, "message": "Come uso FastAPI?" }
   ↓
2. Autenticazione
   current_user = get_current_user(token)
   ↓
3. chat.py: chat_stream()
   ↓
4. Verifica ownership conversation
   conversation = db.query(Conversation).filter(
       Conversation.id == 1,
       Conversation.user_id == current_user.id  # ⭐ Sicurezza
   ).first()

   if not conversation → 404 Not Found
   ↓
5. Recupera API key utente
   api_key_record = db.query(ApiKey).filter(
       ApiKey.user_id == current_user.id,
       ApiKey.provider == conversation.provider  # "openai"
   ).first()

   if not api_key_record → 400 "No API key configured"
   ↓
6. Decripta API key
   api_key = decrypt_api_key(api_key_record.encrypted_key)
   # "sk-proj-abc123..."
   ↓
7. Carica storico conversazione
   history_messages = db.query(Message).filter(
       Message.conversation_id == 1
   ).order_by(Message.created_at.desc()).limit(20).all()

   history = [
       {"role": msg.role.value, "content": msg.content}
       for msg in reversed(history_messages)
   ]
   ↓
8. Salva messaggio utente
   user_message = Message(
       conversation_id=1,
       role="user",
       content="Come uso FastAPI?"
   )
   db.add(user_message)
   db.commit()
   ↓
9. Crea AI service
   service = AgentFactory.create(
       agent_type="langgraph",  # Da conversation
       provider="openai",        # Da conversation
       api_key=api_key           # Decriptato
   )
   ↓
10. Stream risposta
    async def generate():
        full_response = ""

        async for chunk in service.chat(message, history):
            full_response += chunk
            yield f"data: {chunk}\n\n"  # Server-Sent Events format

        yield "data: [DONE]\n\n"

        # Salva risposta completa
        assistant_message = Message(
            conversation_id=1,
            role="assistant",
            content=full_response
        )
        db.add(assistant_message)
        db.commit()
    ↓
11. Ritorna StreamingResponse
    return StreamingResponse(generate(), media_type="text/event-stream")
```

**Frontend riceve:**
```
data: FastAPI
data:  è
data:  un
data:  framework
data: ...
data: [DONE]
```

### Flusso 5: Recupero Conversazioni

```
1. Frontend → GET /conversations
   Headers: { "Authorization": "Bearer ..." }
   ↓
2. Autenticazione
   ↓
3. conversations.py: list_conversations()
   ↓
4. Query conversazioni utente
   conversations = db.query(Conversation).filter(
       Conversation.user_id == current_user.id
   ).order_by(
       Conversation.updated_at.desc()  # Più recenti prima
   ).limit(50).all()
   ↓
5. Per ogni conversazione, conta messaggi
   for conv in conversations:
       message_count = db.query(Message).filter(
           Message.conversation_id == conv.id
       ).count()
   ↓
6. Risposta → Frontend
   [
     {
       "id": 1,
       "title": "Help with FastAPI",
       "agent_type": "langgraph",
       "provider": "openai",
       "message_count": 10,
       "updated_at": "2024-01-15T10:30:00"
     },
     {
       "id": 2,
       "title": "Debug SQL query",
       "agent_type": "openai_direct",
       "provider": "openai",
       "message_count": 5,
       "updated_at": "2024-01-14T15:20:00"
     }
   ]
```

---

## Estendibilità e Scalabilità

### Aggiungere un Nuovo Agente

**Esempio:** Vogliamo aggiungere supporto per "Gemini" di Google

**Step 1:** Crea service
```python
# app/services/ai_service.py

class GeminiService(BaseAIService):
    def __init__(self, api_key: str, model: str = "gemini-pro"):
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)

    async def chat(self, message: str, history: list = None):
        response = self.model.generate_content(message)
        yield response.text
```

**Step 2:** Aggiungi al factory
```python
# app/services/ai_service.py

class AgentFactory:
    @staticmethod
    def create(agent_type: str, provider: str, api_key: str):
        # ... existing code ...
        elif agent_type == "gemini":
            return GeminiService(api_key)
```

**Step 3:** Aggiungi provider al DB
```python
# app/models.py

class ProviderEnum(str, enum.Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"  # ⭐ Nuovo
```

**Step 4:** FATTO! ✅

Frontend può ora:
```javascript
POST /conversations
{
  "title": "Test Gemini",
  "agent_type": "gemini",
  "provider": "google"
}
```

### Aggiungere un Nuovo Endpoint

**Esempio:** Endpoint per cercare nelle conversazioni

```python
# app/routes/conversations.py

@router.get("/search")
def search_conversations(
    query: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Search conversations by title or message content"""
    # Search in titles
    conversations = db.query(Conversation).filter(
        Conversation.user_id == current_user.id,
        Conversation.title.contains(query)
    ).all()

    # Search in messages
    messages = db.query(Message).join(Conversation).filter(
        Conversation.user_id == current_user.id,
        Message.content.contains(query)
    ).all()

    return {
        "conversations": conversations,
        "messages": messages
    }
```

**Automaticamente disponibile su:**
- `GET /conversations/search?query=FastAPI`
- Documentato in `/docs`

### Scalabilità Orizzontale

**Architettura attuale:**
```
┌──────────┐
│ Frontend │
└─────┬────┘
      │
      ▼
┌──────────┐     ┌──────────┐
│ FastAPI  │────▶│  MySQL   │
└──────────┘     └──────────┘
```

**Scalabilità futura:**
```
┌──────────┐
│ Frontend │
└─────┬────┘
      │
      ▼
┌─────────────┐
│ Load Balance│
└──────┬──────┘
       │
   ┌───┴───┬────────┬────────┐
   ▼       ▼        ▼        ▼
┌────┐  ┌────┐  ┌────┐  ┌────┐
│API1│  │API2│  │API3│  │API4│  (Multiple instances)
└──┬─┘  └──┬─┘  └──┬─┘  └──┬─┘
   │       │       │       │
   └───┬───┴───┬───┴───┬───┘
       ▼       ▼       ▼
   ┌──────┐ ┌──────┐ ┌──────┐
   │MySQL │ │Redis │ │S3    │
   │Master│ │Cache │ │Files │
   └───┬──┘ └──────┘ └──────┘
       │
   ┌───┴───┐
   ▼       ▼
┌──────┐ ┌──────┐
│MySQL │ │MySQL │ (Read replicas)
│Slave1│ │Slave2│
└──────┘ └──────┘
```

**Modifiche necessarie:**

1. **Session storage in Redis** (invece di JWT stateless)
2. **Read replicas MySQL** per query pesanti
3. **CDN per assets** statici
4. **Message queue** (Celery/RabbitMQ) per operazioni async

**Ma:** Architettura attuale è pronta per questo (stateless, no global state).

### Aggiungere Features Avanzate

**1. Rate Limiting per utente**
```python
# app/middleware/rate_limit.py

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/chat/stream")
@limiter.limit("20/minute")  # ⭐ Max 20 messaggi/minuto
async def chat_stream(...):
    ...
```

**2. Websockets per real-time**
```python
# app/routes/chat.py

@router.websocket("/ws/{conversation_id}")
async def websocket_chat(websocket: WebSocket, conversation_id: int):
    await websocket.accept()
    while True:
        message = await websocket.receive_text()
        # Process and stream back
        async for chunk in service.chat(message):
            await websocket.send_text(chunk)
```

**3. File uploads per RAG**
```python
@router.post("/conversations/{id}/upload")
async def upload_file(
    id: int,
    file: UploadFile,
    current_user: User = Depends(get_current_user)
):
    # Save to S3/storage
    # Create vector embeddings
    # Attach to conversation
    pass
```

**4. Shared conversations**
```python
# Nuovo modello
class ConversationShare(Base):
    __tablename__ = "conversation_shares"
    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    shared_with_user_id = Column(Integer, ForeignKey("users.id"))
    permission = Column(Enum("read", "write"))
```

---

## Conclusioni

### Punti di Forza dell'Architettura

1. **Sicurezza multi-layer**
   - JWT authentication
   - bcrypt password hashing
   - Fernet API key encryption
   - Row-level authorization

2. **Flessibilità**
   - Supporto multi-framework AI
   - Facile aggiungere nuovi agenti
   - Provider intercambiabili

3. **Manutenibilità**
   - Codice ben organizzato (layers)
   - Type hints ovunque
   - Documentazione automatica

4. **Scalabilità**
   - Stateless (JWT)
   - Database relazionale ottimizzato
   - Pronto per load balancing

5. **Developer Experience**
   - uv per gestione dipendenze veloce
   - FastAPI auto-documentation
   - SQLAlchemy ORM
   - Type safety con Pydantic

### Trade-offs Consapevoli

1. **MySQL vs NoSQL**
   - ✅ Relazioni complesse gestite bene
   - ❌ Meno flessibile per schema changes

2. **JWT vs Sessions**
   - ✅ Stateless, scalabile
   - ❌ Token non revocabile (serve lista nera)

3. **Fernet vs Asymmetric encryption**
   - ✅ Più veloce
   - ❌ Se leak ENCRYPTION_KEY → tutte le chiavi compromesse

4. **Sync DB queries in async endpoints**
   - ❌ Potenziale bottleneck
   - **Fix futuro:** SQLAlchemy async + asyncpg

### Prossimi Step Consigliati

1. **Testing**
   - Unit tests per services
   - Integration tests per endpoints
   - Coverage >80%

2. **Observability**
   - Logging strutturato (structured logging)
   - Metrics (Prometheus)
   - Tracing (OpenTelemetry)

3. **CI/CD**
   - GitHub Actions per tests
   - Docker build automatico
   - Deploy su staging/production

4. **Production Hardening**
   - Rate limiting robusto
   - Input sanitization
   - SQL injection prevention audit
   - HTTPS only
   - Secrets management (Vault/AWS Secrets Manager)

---

**Questa architettura è pronta per:**
- MVP development ✅
- Production deployment ✅
- Team collaboration ✅
- Future scaling ✅

**Documentazione aggiornata:** 2024-01-15
