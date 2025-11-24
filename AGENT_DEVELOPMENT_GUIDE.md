# 🤖 Agent Development Guide - AgentHill Platform

## Indice
1. [Introduzione](#introduzione)
2. [Architettura del Sistema Agenti](#architettura-del-sistema-agenti)
3. [Quick Start: Il Tuo Primo Agente](#quick-start-il-tuo-primo-agente)
4. [Anatomia di un Agente](#anatomia-di-un-agente)
5. [Pattern e Best Practices](#pattern-e-best-practices)
6. [Esempi Completi](#esempi-completi)
7. [Testing degli Agenti](#testing-degli-agenti)
8. [Deployment e Production](#deployment-e-production)
9. [Troubleshooting](#troubleshooting)
10. [FAQ](#faq)

---

## Introduzione

**AgentHill** è il sistema di gestione agenti della piattaforma chatbot. Permette di integrare qualsiasi framework AI (LangChain, LangGraph, AutoGen, CrewAI, OpenAI SDK, Anthropic SDK, o il tuo custom framework) in modo semplice e standardizzato.

### Filosofia di Design

1. **Framework Agnostic** - Non sei legato a un singolo framework
2. **Plug & Play** - Aggiungi un agente in minuti, non ore
3. **Type Safe** - Tutto validato con Python type hints
4. **Stream First** - Supporto nativo per streaming responses
5. **Production Ready** - Gestione errori, logging, monitoring inclusi

### Cosa Puoi Fare

- ✅ Usare qualsiasi modello LLM (OpenAI, Anthropic, Google, Mistral, Llama, ecc.)
- ✅ Implementare RAG (Retrieval Augmented Generation)
- ✅ Creare agenti multi-step con tool calling
- ✅ Orchestrare team di agenti (CrewAI, AutoGen)
- ✅ Implementare memory e context management personalizzato
- ✅ Integrare API esterne e database custom

---

## Architettura del Sistema Agenti

### File Structure

```
backend/app/services/
├── __init__.py
├── agenthill.py          # ⭐ Il cuore del sistema (nuovo nome)
└── encryption.py         # Gestione API keys crittografate

backend/app/routes/
├── chat.py              # Endpoint che usano gli agenti
└── conversations.py     # Gestione conversazioni
```

### Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      FRONTEND (React)                        │
│  User seleziona: agent_type = "my_custom_agent"            │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP POST /chat/stream
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   FASTAPI ROUTES (chat.py)                   │
│  1. Autenticazione JWT                                       │
│  2. Recupera conversation dal DB                             │
│  3. Verifica ownership (security)                            │
│  4. Legge: agent_type, provider                             │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                AGENTHILL (agenthill.py)                      │
│  AgentFactory.create(                                        │
│      agent_type="my_custom_agent",                          │
│      provider="openai",                                      │
│      api_key=decrypted_key                                  │
│  )                                                           │
│  ↓                                                           │
│  Istanzia: MyCustomAgentService                             │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              YOUR AGENT (MyCustomAgentService)               │
│  async def chat(message, history):                          │
│      # Il TUO codice                                         │
│      async for chunk in your_framework.stream(message):     │
│          yield chunk                                         │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  EXTERNAL AI PROVIDER                        │
│  OpenAI API / Anthropic API / Your Custom API               │
└─────────────────────────────────────────────────────────────┘
```

### Componenti Chiave

#### 1. BaseAIService (Abstract Base Class)

```python
from abc import ABC, abstractmethod
from typing import AsyncGenerator

class BaseAIService(ABC):
    """
    Classe base per tutti gli agenti.
    OGNI agente DEVE implementare questa interfaccia.
    """

    @abstractmethod
    async def chat(
        self,
        message: str,
        history: list = None
    ) -> AsyncGenerator[str, None]:
        """
        Metodo principale per la chat.

        Args:
            message: Il messaggio corrente dell'utente
            history: Lista di messaggi precedenti
                     Formato: [{"role": "user|assistant", "content": "..."}]

        Yields:
            Chunk di testo della risposta (streaming)

        Raises:
            Exception: In caso di errori (gestiti automaticamente dal router)
        """
        pass
```

**Perché AsyncGenerator?**
- Supporta streaming nativo (chunks inviati mentre il modello genera)
- Non blocking (altre richieste possono essere processate)
- Migliore UX (l'utente vede la risposta in tempo reale)

#### 2. AgentFactory (Factory Pattern)

```python
class AgentFactory:
    """
    Factory per creare istanze di agenti.
    Centralizza la logica di creazione e configurazione.
    """

    @staticmethod
    def create(
        agent_type: str,      # Nome univoco del tuo agente
        provider: str,        # "openai", "anthropic", "custom"
        api_key: str,         # API key decriptata
        model: Optional[str] = None  # Override del modello
    ) -> BaseAIService:
        """
        Crea e ritorna un'istanza dell'agente.

        Raises:
            ValueError: Se agent_type non è riconosciuto
        """

        if agent_type == "langgraph":
            return LangGraphService(api_key, provider, model)

        elif agent_type == "your_agent_here":  # ⭐ Aggiungi qui
            return YourAgentService(api_key)

        else:
            raise ValueError(f"Unknown agent_type: {agent_type}")
```

---

## Quick Start: Il Tuo Primo Agente

### Obiettivo
Creare un agente semplice che risponde con un prefisso personalizzato.

### Step 1: Definisci la Classe

Apri `backend/app/services/agenthill.py` e aggiungi:

```python
class SimpleEchoAgent(BaseAIService):
    """
    Agente di esempio che fa echo del messaggio con un prefisso.
    Utile per testing o come template.
    """

    def __init__(self, api_key: str, prefix: str = "Echo"):
        """
        Inizializza l'agente.

        Args:
            api_key: Non usato in questo esempio, ma richiesto dall'interfaccia
            prefix: Prefisso da aggiungere ai messaggi
        """
        self.prefix = prefix

    async def chat(self, message: str, history: list = None) -> AsyncGenerator[str, None]:
        """
        Risponde con il messaggio prefissato.
        """
        # Simula streaming word-by-word
        import asyncio

        response = f"{self.prefix}: {message}"
        words = response.split()

        for word in words:
            yield word + " "
            await asyncio.sleep(0.1)  # Simula latenza
```

### Step 2: Registra nel Factory

Nello stesso file, trova `AgentFactory.create()` e aggiungi:

```python
class AgentFactory:
    @staticmethod
    def create(agent_type: str, provider: str, api_key: str, model: Optional[str] = None):

        # ... codice esistente ...

        elif agent_type == "simple_echo":  # ⭐ Nome univoco
            return SimpleEchoAgent(api_key, prefix="🤖 Bot")

        else:
            raise ValueError(f"Unknown agent_type: {agent_type}")
```

### Step 3: Testa dal Frontend

```javascript
// 1. Crea conversazione
const conv = await fetch('http://localhost:8000/conversations', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    title: "Test Simple Echo",
    agent_type: "simple_echo",  // ⭐ Il nome che hai registrato
    provider: "openai"           // Qualsiasi provider (non usato in questo esempio)
  })
}).then(r => r.json())

// 2. Invia messaggio
const response = await fetch('http://localhost:8000/chat/stream', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    conversation_id: conv.id,
    message: "Hello World"
  })
})

// 3. Ricevi streaming
// Output: "🤖 Bot: Hello World" (word by word)
```

### Step 4: Verifica nel Database

```sql
-- La conversazione è salvata con agent_type
SELECT id, title, agent_type, provider
FROM conversations
WHERE user_id = 1;

-- id | title              | agent_type   | provider
-- 1  | Test Simple Echo   | simple_echo  | openai

-- I messaggi sono salvati
SELECT role, content
FROM messages
WHERE conversation_id = 1;

-- role      | content
-- user      | Hello World
-- assistant | 🤖 Bot: Hello World
```

---

## Anatomia di un Agente

### Struttura Minima

```python
class MinimalAgent(BaseAIService):
    """Template minimo per un agente"""

    def __init__(self, api_key: str, **kwargs):
        """Inizializzazione (setup del tuo framework)"""
        self.api_key = api_key
        # Inizializza qui il tuo framework/modello

    async def chat(self, message: str, history: list = None) -> AsyncGenerator[str, None]:
        """Logica principale (genera risposta)"""
        # Il tuo codice qui
        yield "response chunk"
```

### Struttura Completa (Production Ready)

```python
import logging
from typing import AsyncGenerator, Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class ProductionReadyAgent(BaseAIService):
    """
    Agente production-ready con tutte le best practices.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4",
        temperature: float = 0.7,
        max_tokens: int = 2000,
        timeout: int = 30,
        **kwargs
    ):
        """
        Inizializza l'agente con configurazione completa.

        Args:
            api_key: API key per il provider
            model: Nome del modello da usare
            temperature: Creatività (0.0-2.0)
            max_tokens: Lunghezza massima risposta
            timeout: Timeout in secondi per le richieste
            **kwargs: Parametri aggiuntivi
        """
        logger.info(f"Initializing ProductionReadyAgent with model={model}")

        # Validazione parametri
        if not api_key:
            raise ValueError("api_key is required")

        if not 0.0 <= temperature <= 2.0:
            raise ValueError("temperature must be between 0.0 and 2.0")

        # Setup
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

        # Inizializza il tuo framework
        try:
            from your_framework import YourClient
            self.client = YourClient(
                api_key=api_key,
                timeout=timeout
            )
        except ImportError as e:
            logger.error(f"Failed to import framework: {e}")
            raise

        logger.info("Agent initialized successfully")

    async def chat(
        self,
        message: str,
        history: list = None
    ) -> AsyncGenerator[str, None]:
        """
        Genera risposta con gestione errori completa.
        """
        start_time = datetime.now()
        logger.info(f"Processing message: {message[:50]}...")

        try:
            # Validazione input
            if not message or not message.strip():
                raise ValueError("Message cannot be empty")

            # Prepara context
            context = self._prepare_context(message, history)

            # Chiama il modello
            logger.debug(f"Calling model with context length: {len(context)}")

            total_tokens = 0
            async for chunk in self._stream_response(context):
                total_tokens += 1
                yield chunk

            # Logging metriche
            duration = (datetime.now() - start_time).total_seconds()
            logger.info(
                f"Response completed: {total_tokens} tokens in {duration:.2f}s "
                f"({total_tokens/duration:.1f} tokens/s)"
            )

        except Exception as e:
            logger.error(f"Error in chat: {e}", exc_info=True)
            yield f"[Error: {str(e)}]"

    def _prepare_context(self, message: str, history: list = None) -> list:
        """
        Prepara il context per il modello.

        Returns:
            Lista di messaggi in formato standard
        """
        context = []

        # System message (opzionale)
        context.append({
            "role": "system",
            "content": "You are a helpful AI assistant."
        })

        # History
        if history:
            for msg in history[-10:]:  # Ultimi 10 messaggi
                context.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

        # Current message
        context.append({
            "role": "user",
            "content": message
        })

        return context

    async def _stream_response(self, context: list) -> AsyncGenerator[str, None]:
        """
        Streaming della risposta dal modello.
        Implementa qui la logica specifica del tuo framework.
        """
        # Esempio con framework generico
        async for chunk in self.client.stream(
            model=self.model,
            messages=context,
            temperature=self.temperature,
            max_tokens=self.max_tokens
        ):
            if chunk.content:
                yield chunk.content

    def __repr__(self) -> str:
        """Rappresentazione stringa per debugging"""
        return (
            f"ProductionReadyAgent(model={self.model}, "
            f"temperature={self.temperature})"
        )
```

### Componenti Opzionali ma Consigliati

#### 1. Context Window Management

```python
class ContextAwareAgent(BaseAIService):
    """Agente che gestisce il context window"""

    MAX_CONTEXT_LENGTH = 8000  # tokens

    def _truncate_history(self, history: list, message: str) -> list:
        """
        Tronca la history per stare nel context window.

        Strategie:
        1. Sliding window: ultimi N messaggi
        2. Summarization: riassumi messaggi vecchi
        3. Importance sampling: mantieni messaggi importanti
        """
        import tiktoken

        encoding = tiktoken.encoding_for_model(self.model)

        # Conta tokens del messaggio corrente
        current_tokens = len(encoding.encode(message))
        budget = self.MAX_CONTEXT_LENGTH - current_tokens - 500  # Safety margin

        # Aggiungi messaggi dalla più recente finché c'è spazio
        truncated = []
        total_tokens = 0

        for msg in reversed(history):
            msg_tokens = len(encoding.encode(msg["content"]))
            if total_tokens + msg_tokens > budget:
                break
            truncated.insert(0, msg)
            total_tokens += msg_tokens

        logger.info(f"Truncated history: {len(history)} → {len(truncated)} messages")
        return truncated
```

#### 2. Rate Limiting & Retry Logic

```python
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

class ResilientAgent(BaseAIService):
    """Agente con retry automatico"""

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def _call_api_with_retry(self, context: list):
        """
        Chiama API con retry automatico su errori transienti.

        Retry su:
        - Rate limit errors (429)
        - Server errors (500, 502, 503)
        - Timeout
        """
        try:
            return await self.client.call(context)
        except Exception as e:
            logger.warning(f"API call failed, retrying: {e}")
            raise
```

#### 3. Caching

```python
from functools import lru_cache
import hashlib

class CachedAgent(BaseAIService):
    """Agente con cache delle risposte"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cache = {}

    def _cache_key(self, message: str, history: list) -> str:
        """Genera cache key dal context"""
        context_str = str(history) + message
        return hashlib.md5(context_str.encode()).hexdigest()

    async def chat(self, message: str, history: list = None):
        cache_key = self._cache_key(message, history)

        # Check cache
        if cache_key in self.cache:
            logger.info("Cache hit!")
            cached_response = self.cache[cache_key]
            for chunk in cached_response.split():
                yield chunk + " "
            return

        # Miss: chiama API e salva in cache
        full_response = ""
        async for chunk in self._generate_response(message, history):
            full_response += chunk
            yield chunk

        self.cache[cache_key] = full_response
```

---

## Pattern e Best Practices

### Pattern 1: Agente con Tool Calling

```python
from typing import Callable, Dict

class ToolAgent(BaseAIService):
    """
    Agente che può usare tools/functions.
    """

    def __init__(self, api_key: str):
        super().__init__(api_key)

        # Registra tools disponibili
        self.tools = {
            "search_web": self._search_web,
            "calculate": self._calculate,
            "get_weather": self._get_weather
        }

    def _search_web(self, query: str) -> str:
        """Tool: Cerca sul web"""
        # Implementazione reale userebbe SerpAPI, Google Custom Search, ecc.
        return f"Risultati per '{query}': ..."

    def _calculate(self, expression: str) -> str:
        """Tool: Calcolatrice"""
        try:
            result = eval(expression)  # ⚠️ In prod usa ast.literal_eval
            return str(result)
        except Exception as e:
            return f"Error: {e}"

    def _get_weather(self, location: str) -> str:
        """Tool: Meteo"""
        # Implementazione reale userebbe OpenWeatherMap, ecc.
        return f"Weather in {location}: Sunny, 22°C"

    async def chat(self, message: str, history: list = None):
        """
        Chat con tool calling integrato.
        """
        from langchain.agents import AgentExecutor, create_openai_functions_agent
        from langchain.tools import Tool
        from langchain_openai import ChatOpenAI

        # Setup LLM
        llm = ChatOpenAI(api_key=self.api_key, model="gpt-4", streaming=True)

        # Converti tools in formato LangChain
        lc_tools = [
            Tool(
                name=name,
                func=func,
                description=func.__doc__ or f"Tool: {name}"
            )
            for name, func in self.tools.items()
        ]

        # Crea agent
        agent = create_openai_functions_agent(llm, lc_tools)
        executor = AgentExecutor(agent=agent, tools=lc_tools, verbose=True)

        # Stream execution
        async for chunk in executor.astream({"input": message}):
            if "output" in chunk:
                yield chunk["output"]
            elif "intermediate_steps" in chunk:
                # Mostra quale tool sta usando
                for action, observation in chunk["intermediate_steps"]:
                    yield f"\n🔧 Using tool: {action.tool}\n"
                    yield f"📊 Result: {observation}\n\n"
```

### Pattern 2: Multi-Agent System (CrewAI Style)

```python
class MultiAgentSystem(BaseAIService):
    """
    Sistema multi-agente con specializzazioni diverse.
    """

    def __init__(self, api_key: str):
        from crewai import Agent, Task, Crew
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(api_key=api_key, model="gpt-4")

        # Agente 1: Researcher
        self.researcher = Agent(
            role="Senior Researcher",
            goal="Find accurate and relevant information",
            backstory="Expert researcher with 10 years of experience",
            llm=llm,
            verbose=True
        )

        # Agente 2: Writer
        self.writer = Agent(
            role="Content Writer",
            goal="Write engaging and informative content",
            backstory="Professional writer specialized in technical content",
            llm=llm,
            verbose=True
        )

        # Agente 3: Reviewer
        self.reviewer = Agent(
            role="Quality Reviewer",
            goal="Ensure content is accurate and well-written",
            backstory="Meticulous editor with high standards",
            llm=llm,
            verbose=True
        )

        # Crew
        self.crew = Crew(
            agents=[self.researcher, self.writer, self.reviewer],
            verbose=True
        )

    async def chat(self, message: str, history: list = None):
        """
        Esegue il workflow multi-agente.
        """
        # Task 1: Research
        research_task = Task(
            description=f"Research information about: {message}",
            agent=self.researcher
        )

        # Task 2: Write
        write_task = Task(
            description="Write a comprehensive response based on research",
            agent=self.writer
        )

        # Task 3: Review
        review_task = Task(
            description="Review and improve the written content",
            agent=self.reviewer
        )

        # Execute crew
        yield "🔍 **Research Phase**\n"
        result = self.crew.kickoff(tasks=[research_task, write_task, review_task])

        yield "\n\n✍️ **Writing Phase**\n"
        yield "\n\n✅ **Review Phase**\n\n"

        # Stream final result
        for word in str(result).split():
            yield word + " "
            await asyncio.sleep(0.05)
```

### Pattern 3: RAG (Retrieval Augmented Generation)

```python
class RAGAgent(BaseAIService):
    """
    Agente con Retrieval Augmented Generation.
    """

    def __init__(self, api_key: str, vector_db_path: str = "./chroma_db"):
        from langchain_openai import ChatOpenAI, OpenAIEmbeddings
        from langchain_community.vectorstores import Chroma
        from langchain.chains import RetrievalQA
        from langchain.prompts import PromptTemplate

        # LLM
        self.llm = ChatOpenAI(
            api_key=api_key,
            model="gpt-4",
            streaming=True,
            temperature=0.3  # Più bassa per RAG (più factual)
        )

        # Embeddings
        embeddings = OpenAIEmbeddings(api_key=api_key)

        # Vector store
        self.vectorstore = Chroma(
            persist_directory=vector_db_path,
            embedding_function=embeddings
        )

        # Custom prompt per RAG
        template = """
        Use the following pieces of context to answer the question at the end.
        If you don't know the answer, just say you don't know, don't try to make up an answer.

        Context:
        {context}

        Question: {question}

        Answer with sources:
        """

        PROMPT = PromptTemplate(
            template=template,
            input_variables=["context", "question"]
        )

        # Chain
        self.qa_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=self.vectorstore.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 5}  # Top 5 documenti più rilevanti
            ),
            return_source_documents=True,
            chain_type_kwargs={"prompt": PROMPT}
        )

    async def chat(self, message: str, history: list = None):
        """
        Risponde usando RAG.
        """
        # Esegui retrieval + generation
        result = await self.qa_chain.ainvoke({"query": message})

        # Stream risposta
        answer = result["result"]
        for word in answer.split():
            yield word + " "
            await asyncio.sleep(0.03)

        # Aggiungi fonti
        sources = result.get("source_documents", [])
        if sources:
            yield "\n\n---\n**📚 Fonti:**\n"
            for i, doc in enumerate(sources, 1):
                source = doc.metadata.get("source", "Unknown")
                preview = doc.page_content[:100]
                yield f"\n{i}. {source}\n   _{preview}..._\n"

    async def add_documents(self, documents: list):
        """
        Aggiunge documenti al vector store.

        Args:
            documents: Lista di LangChain Documents
        """
        self.vectorstore.add_documents(documents)
        self.vectorstore.persist()
        logger.info(f"Added {len(documents)} documents to vector store")
```

### Pattern 4: Conversational Memory

```python
from langchain.memory import ConversationBufferWindowMemory

class MemoryAgent(BaseAIService):
    """
    Agente con memoria conversazionale gestita.
    """

    def __init__(self, api_key: str, memory_window: int = 10):
        from langchain_openai import ChatOpenAI
        from langchain.chains import ConversationChain

        # LLM
        llm = ChatOpenAI(api_key=api_key, model="gpt-4", streaming=True)

        # Memory: mantiene ultimi N turni
        self.memory = ConversationBufferWindowMemory(
            k=memory_window,
            return_messages=True
        )

        # Conversation chain
        self.chain = ConversationChain(
            llm=llm,
            memory=self.memory,
            verbose=True
        )

    async def chat(self, message: str, history: list = None):
        """
        Chat con memoria gestita da LangChain.
        """
        # Inizializza memory da history se fornita
        if history and not self.memory.chat_memory.messages:
            for msg in history:
                if msg["role"] == "user":
                    self.memory.chat_memory.add_user_message(msg["content"])
                elif msg["role"] == "assistant":
                    self.memory.chat_memory.add_ai_message(msg["content"])

        # Stream response
        async for chunk in self.chain.astream({"input": message}):
            if "response" in chunk:
                yield chunk["response"]
```

---

## Esempi Completi

### Esempio 1: Agente Code Assistant

```python
class CodeAssistantAgent(BaseAIService):
    """
    Agente specializzato in coding con:
    - Syntax highlighting
    - Code execution (sandboxed)
    - GitHub integration
    """

    def __init__(self, api_key: str):
        from langchain_openai import ChatOpenAI
        from langchain.prompts import ChatPromptTemplate

        self.llm = ChatOpenAI(
            api_key=api_key,
            model="gpt-4",
            temperature=0.2,  # Bassa per code generation
            streaming=True
        )

        # System prompt specializzato
        self.system_prompt = """
        You are an expert programming assistant.
        - Provide clear, well-commented code
        - Explain your reasoning
        - Suggest best practices
        - Format code with markdown code blocks
        """

    async def chat(self, message: str, history: list = None):
        """Generate code response"""

        # Detect programming language
        language = self._detect_language(message)

        # Prepara context
        context = [{"role": "system", "content": self.system_prompt}]
        if history:
            context.extend(history[-5:])  # Ultimi 5 messaggi
        context.append({"role": "user", "content": message})

        # Stream response
        full_response = ""
        async for chunk in self.llm.astream(context):
            if chunk.content:
                full_response += chunk.content
                yield chunk.content

        # Auto-execute code se richiesto
        if "```python" in full_response and "execute" in message.lower():
            yield "\n\n🔧 **Executing code...**\n"
            result = await self._execute_code(full_response, "python")
            yield f"\n**Output:**\n```\n{result}\n```"

    def _detect_language(self, message: str) -> str:
        """Rileva linguaggio di programmazione dal messaggio"""
        keywords = {
            "python": ["python", "def ", "import ", "class "],
            "javascript": ["javascript", "function", "const ", "let "],
            "rust": ["rust", "fn ", "impl ", "struct "],
            "go": ["golang", "go", "func ", "package "]
        }

        message_lower = message.lower()
        for lang, kws in keywords.items():
            if any(kw in message_lower for kw in kws):
                return lang
        return "unknown"

    async def _execute_code(self, response: str, language: str) -> str:
        """
        Esegue code in sandbox (SOLO per demo, in prod usa container isolati!)
        """
        import re
        import subprocess

        # Estrai code block
        pattern = f"```{language}\n(.*?)\n```"
        match = re.search(pattern, response, re.DOTALL)
        if not match:
            return "No code block found"

        code = match.group(1)

        # Execute in subprocess (⚠️ ATTENZIONE: potential security risk)
        try:
            result = subprocess.run(
                [language, "-c", code],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout or result.stderr
        except Exception as e:
            return f"Execution error: {e}"
```

### Esempio 2: Agente Customer Support

```python
class CustomerSupportAgent(BaseAIService):
    """
    Agente customer support con:
    - Sentiment analysis
    - Ticket creation
    - Knowledge base integration
    """

    def __init__(self, api_key: str, company_name: str = "YourCompany"):
        from langchain_openai import ChatOpenAI

        self.llm = ChatOpenAI(api_key=api_key, model="gpt-4", streaming=True)
        self.company_name = company_name

        # Knowledge base (in prod: database o vector store)
        self.kb = {
            "shipping": "Shipping takes 3-5 business days...",
            "returns": "Returns accepted within 30 days...",
            "pricing": "Check our pricing page at..."
        }

    async def chat(self, message: str, history: list = None):
        """
        Customer support workflow.
        """
        # 1. Sentiment analysis
        sentiment = await self._analyze_sentiment(message)

        if sentiment == "negative":
            yield f"😔 I sense you're frustrated. Let me help you right away.\n\n"

        # 2. Check knowledge base
        kb_match = self._search_kb(message)

        context = f"""
        You are a helpful customer support agent for {self.company_name}.

        Knowledge base info:
        {kb_match if kb_match else "No specific KB article found"}

        Guidelines:
        - Be empathetic and professional
        - Provide specific solutions
        - Escalate to human if needed
        """

        # 3. Generate response
        messages = [
            {"role": "system", "content": context},
            {"role": "user", "content": message}
        ]

        async for chunk in self.llm.astream(messages):
            if chunk.content:
                yield chunk.content

        # 4. Auto-create ticket se necessario
        if any(word in message.lower() for word in ["bug", "broken", "not working"]):
            yield "\n\n📋 I've created ticket #12345 for our engineering team."

    async def _analyze_sentiment(self, text: str) -> str:
        """Analizza sentiment (simplified)"""
        negative_words = ["angry", "frustrated", "terrible", "worst", "hate"]
        positive_words = ["great", "awesome", "thanks", "love", "perfect"]

        text_lower = text.lower()
        if any(word in text_lower for word in negative_words):
            return "negative"
        elif any(word in text_lower for word in positive_words):
            return "positive"
        return "neutral"

    def _search_kb(self, query: str) -> str:
        """Cerca nella knowledge base"""
        query_lower = query.lower()
        for topic, content in self.kb.items():
            if topic in query_lower:
                return content
        return ""
```

### Esempio 3: Agente Research & Analysis

```python
class ResearchAgent(BaseAIService):
    """
    Agente per ricerca e analisi con:
    - Web scraping
    - Multi-source aggregation
    - Fact-checking
    """

    def __init__(self, api_key: str):
        from langgraph.graph import StateGraph, END
        from langchain_openai import ChatOpenAI

        self.llm = ChatOpenAI(api_key=api_key, model="gpt-4")

        # Build LangGraph workflow
        workflow = StateGraph(dict)

        # Nodes
        workflow.add_node("search", self._search_node)
        workflow.add_node("analyze", self._analyze_node)
        workflow.add_node("verify", self._verify_node)
        workflow.add_node("synthesize", self._synthesize_node)

        # Edges
        workflow.set_entry_point("search")
        workflow.add_edge("search", "analyze")
        workflow.add_edge("analyze", "verify")
        workflow.add_edge("verify", "synthesize")
        workflow.add_edge("synthesize", END)

        self.graph = workflow.compile()

    def _search_node(self, state: dict) -> dict:
        """Node 1: Search information"""
        query = state["query"]

        # Simula ricerca (in prod: SerpAPI, Tavily, ecc.)
        results = [
            {"title": "Result 1", "snippet": "..."},
            {"title": "Result 2", "snippet": "..."}
        ]

        return {"search_results": results}

    def _analyze_node(self, state: dict) -> dict:
        """Node 2: Analyze results"""
        results = state["search_results"]

        # Usa LLM per analizzare
        analysis = "Analysis of search results..."

        return {"analysis": analysis}

    def _verify_node(self, state: dict) -> dict:
        """Node 3: Fact-check"""
        analysis = state["analysis"]

        # Cross-reference sources
        verified = True

        return {"verified": verified}

    def _synthesize_node(self, state: dict) -> dict:
        """Node 4: Synthesize final answer"""
        analysis = state["analysis"]
        verified = state["verified"]

        if verified:
            final = f"Verified answer: {analysis}"
        else:
            final = f"Unverified (conflicting sources): {analysis}"

        return {"final_answer": final}

    async def chat(self, message: str, history: list = None):
        """Execute research workflow"""

        yield "🔍 **Phase 1: Searching...**\n"

        # Run graph
        result = await self.graph.ainvoke({"query": message})

        yield "📊 **Phase 2: Analyzing...**\n"
        yield "✅ **Phase 3: Fact-checking...**\n"
        yield "📝 **Phase 4: Synthesizing...**\n\n"

        # Stream final answer
        final_answer = result["final_answer"]
        for word in final_answer.split():
            yield word + " "
            await asyncio.sleep(0.05)
```

---

## Testing degli Agenti

### Unit Testing

```python
# tests/test_agenthill.py

import pytest
from app.services.agenthill import SimpleEchoAgent, AgentFactory

@pytest.mark.asyncio
async def test_simple_echo_agent():
    """Test SimpleEchoAgent risponde correttamente"""
    agent = SimpleEchoAgent(api_key="fake-key", prefix="Test")

    chunks = []
    async for chunk in agent.chat("Hello"):
        chunks.append(chunk)

    response = "".join(chunks)
    assert "Test: Hello" in response

@pytest.mark.asyncio
async def test_agent_factory():
    """Test AgentFactory crea agenti corretti"""
    agent = AgentFactory.create(
        agent_type="simple_echo",
        provider="openai",
        api_key="fake-key"
    )

    assert isinstance(agent, SimpleEchoAgent)

@pytest.mark.asyncio
async def test_unknown_agent_type():
    """Test AgentFactory solleva errore per agent sconosciuto"""
    with pytest.raises(ValueError, match="Unknown agent_type"):
        AgentFactory.create(
            agent_type="non_existent",
            provider="openai",
            api_key="fake-key"
        )
```

### Integration Testing

```python
# tests/integration/test_chat_flow.py

import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_full_chat_flow(auth_token, test_db):
    """Test flow completo: crea conversazione → invia messaggio → ricevi risposta"""

    async with AsyncClient(app=app, base_url="http://test") as client:
        # 1. Crea conversazione
        response = await client.post(
            "/conversations",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "title": "Test Chat",
                "agent_type": "simple_echo",
                "provider": "openai"
            }
        )
        assert response.status_code == 201
        conversation_id = response.json()["id"]

        # 2. Invia messaggio
        response = await client.post(
            "/chat/message",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "conversation_id": conversation_id,
                "message": "Test message"
            }
        )
        assert response.status_code == 200
        assert "Test message" in response.json()["message"]

        # 3. Verifica salvataggio nel DB
        messages = test_db.query(Message).filter_by(
            conversation_id=conversation_id
        ).all()
        assert len(messages) == 2  # user + assistant
```

### Load Testing

```python
# tests/load/test_concurrent_requests.py

import asyncio
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_concurrent_chat_requests():
    """Test 100 richieste concorrenti"""

    async def send_message(client, conversation_id, message):
        return await client.post(
            "/chat/stream",
            json={
                "conversation_id": conversation_id,
                "message": message
            }
        )

    async with AsyncClient(base_url="http://localhost:8000") as client:
        # Crea 100 task concorrenti
        tasks = [
            send_message(client, 1, f"Message {i}")
            for i in range(100)
        ]

        responses = await asyncio.gather(*tasks)

        # Verifica tutti hanno risposto
        assert all(r.status_code == 200 for r in responses)
```

---

## Deployment e Production

### Environment Variables

```bash
# .env.production

# Database
MYSQL_HOST=prod-db.example.com
MYSQL_PORT=3306
MYSQL_USER=chatbot_prod
MYSQL_PASSWORD=<strong-password>
MYSQL_DATABASE=chatbot_prod

# Security
SECRET_KEY=<64-char-random-string>
ENCRYPTION_KEY=<fernet-key>

# Application
ENVIRONMENT=production
DEBUG=False

# Rate Limiting
RATE_LIMIT_PER_MINUTE=100

# Logging
LOG_LEVEL=INFO
SENTRY_DSN=https://...@sentry.io/...

# Agent Timeouts
AGENT_TIMEOUT_SECONDS=60
AGENT_MAX_RETRIES=3
```

### Docker Deployment

```dockerfile
# Dockerfile.agent

FROM python:3.11-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy dependency files
COPY backend/pyproject.toml backend/uv.lock ./

# Install dependencies
RUN uv sync --no-dev

# Copy application
COPY backend/app ./app

# Expose port
EXPOSE 8000

# Run
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Kubernetes Deployment

```yaml
# k8s/agent-deployment.yaml

apiVersion: apps/v1
kind: Deployment
metadata:
  name: chatbot-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: chatbot-api
  template:
    metadata:
      labels:
        app: chatbot-api
    spec:
      containers:
      - name: api
        image: your-registry/chatbot-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: MYSQL_HOST
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: host
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: api-secrets
              key: secret-key
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

### Monitoring

```python
# app/middleware/monitoring.py

import time
from prometheus_client import Counter, Histogram
from starlette.middleware.base import BaseHTTPMiddleware

# Metrics
request_count = Counter(
    "chatbot_requests_total",
    "Total requests",
    ["method", "endpoint", "status"]
)

request_duration = Histogram(
    "chatbot_request_duration_seconds",
    "Request duration",
    ["method", "endpoint"]
)

agent_tokens = Counter(
    "chatbot_agent_tokens_total",
    "Tokens generated",
    ["agent_type", "provider"]
)

class MonitoringMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start_time = time.time()

        response = await call_next(request)

        duration = time.time() - start_time

        request_count.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()

        request_duration.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(duration)

        return response

# In main.py
app.add_middleware(MonitoringMiddleware)
```

---

## Troubleshooting

### Problema 1: "Unknown agent_type" Error

**Sintomo:**
```
ValueError: Unknown agent_type: my_agent
```

**Causa:** Agent non registrato nel factory

**Soluzione:**
```python
# Verifica in agenthill.py
class AgentFactory:
    @staticmethod
    def create(agent_type: str, ...):
        # ...
        elif agent_type == "my_agent":  # ⭐ Aggiungi questo
            return MyAgent(api_key)
```

### Problema 2: Streaming Non Funziona

**Sintomo:** Frontend non riceve chunks, solo risposta completa alla fine

**Causa:** Agente non usa `async` generator

**Soluzione:**
```python
# ❌ Sbagliato
def chat(self, message: str, ...):
    response = self.llm.invoke(message)
    return response  # Ritorna tutto insieme

# ✅ Corretto
async def chat(self, message: str, ...):
    async for chunk in self.llm.astream(message):
        yield chunk.content  # Stream chunk by chunk
```

### Problema 3: "API Key Not Found" Error

**Sintomo:**
```
HTTP 400: No API key configured for openai
```

**Causa:** User non ha salvato API key per quel provider

**Soluzione (Frontend):**
```javascript
// 1. Prima salva API key
await fetch('/auth/api-keys', {
  method: 'POST',
  body: JSON.stringify({
    provider: 'openai',
    api_key: 'sk-...'
  })
})

// 2. Poi crea conversazione
await fetch('/conversations', {
  method: 'POST',
  body: JSON.stringify({
    agent_type: 'my_agent',
    provider: 'openai'  // ⭐ Deve matchare con API key salvata
  })
})
```

### Problema 4: Timeout Errors

**Sintomo:**
```
TimeoutError: Request timed out after 30s
```

**Causa:** Agente impiega troppo tempo

**Soluzione:**
```python
class SlowAgent(BaseAIService):
    def __init__(self, api_key: str):
        self.client = YourClient(
            api_key=api_key,
            timeout=120  # ⭐ Aumenta timeout a 2 minuti
        )

    async def chat(self, message: str, ...):
        try:
            async for chunk in self.client.stream(message):
                yield chunk
        except TimeoutError:
            yield "[Request timed out. Try a simpler query]"
```

### Problema 5: Memory Leaks

**Sintomo:** Server usa sempre più RAM nel tempo

**Causa:** Agenti non rilasciano risorse

**Soluzione:**
```python
class ProperCleanupAgent(BaseAIService):
    def __init__(self, api_key: str):
        self.client = YourClient(api_key)
        self.cache = {}

    async def chat(self, message: str, ...):
        try:
            async for chunk in self.client.stream(message):
                yield chunk
        finally:
            # ⭐ Cleanup
            self.cache.clear()
            if hasattr(self.client, 'close'):
                await self.client.close()
```

---

## FAQ

### Q1: Posso usare agenti sincroni (non async)?

**A:** Sì, ma devi wrapparli:

```python
import asyncio

class SyncAgent(BaseAIService):
    def __init__(self, api_key: str):
        self.sync_client = SyncLibrary(api_key)

    async def chat(self, message: str, ...):
        # Esegui codice sync in thread separato
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            self.sync_client.generate,
            message
        )
        yield response
```

### Q2: Come gestisco agenti che non supportano streaming?

**A:** Ritorna tutto in un solo yield:

```python
class NonStreamingAgent(BaseAIService):
    async def chat(self, message: str, ...):
        # Ottieni risposta completa
        full_response = self.client.generate(message)

        # Opzione 1: Ritorna tutto insieme
        yield full_response

        # Opzione 2: Simula streaming word-by-word
        # for word in full_response.split():
        #     yield word + " "
        #     await asyncio.sleep(0.05)
```

### Q3: Posso avere configurazioni diverse per lo stesso agente?

**A:** Sì, usa `agent_config`:

```python
# Modifica Conversation model
class Conversation(Base):
    # ...
    agent_config = Column(JSON, nullable=True)

# Nel factory
class AgentFactory:
    @staticmethod
    def create(agent_type: str, provider: str, api_key: str, config: dict = None):
        if agent_type == "configurable_agent":
            return ConfigurableAgent(
                api_key=api_key,
                temperature=config.get("temperature", 0.7),
                max_tokens=config.get("max_tokens", 2000)
            )
```

### Q4: Come debuggo un agente in locale?

**A:** Usa logging + breakpoints:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

class DebugAgent(BaseAIService):
    async def chat(self, message: str, history: list = None):
        logger.debug(f"Message: {message}")
        logger.debug(f"History: {history}")

        # Breakpoint per debugging
        import pdb; pdb.set_trace()

        async for chunk in self._generate(message):
            logger.debug(f"Chunk: {chunk}")
            yield chunk
```

### Q5: Come limito i costi delle API?

**A:** Implementa rate limiting + token counting:

```python
from collections import defaultdict
from datetime import datetime, timedelta
import tiktoken

class CostLimitedAgent(BaseAIService):
    # Limite: $10/giorno per utente
    DAILY_LIMIT_USD = 10.0
    COST_PER_1K_TOKENS = 0.03  # GPT-4

    def __init__(self, api_key: str, user_id: int):
        self.user_id = user_id
        self.usage_tracker = defaultdict(int)
        self.encoding = tiktoken.encoding_for_model("gpt-4")

    async def chat(self, message: str, ...):
        # Check budget
        today = datetime.now().date()
        tokens_used_today = self.usage_tracker[today]
        cost_today = (tokens_used_today / 1000) * self.COST_PER_1K_TOKENS

        if cost_today >= self.DAILY_LIMIT_USD:
            yield f"[Daily limit reached: ${cost_today:.2f}/${self.DAILY_LIMIT_USD}]"
            return

        # Count tokens
        message_tokens = len(self.encoding.encode(message))

        # Stream response
        total_tokens = message_tokens
        async for chunk in self.llm.astream(message):
            total_tokens += len(self.encoding.encode(chunk.content))
            yield chunk.content

        # Update tracker
        self.usage_tracker[today] += total_tokens
```

---

## Conclusione

AgentHill ti permette di:
- ✅ Integrare **qualsiasi framework AI** in minuti
- ✅ Mantenere **codice pulito e manutenibile**
- ✅ Scalare facilmente aggiungendo nuovi agenti
- ✅ Testare e debuggare efficacemente

**Next Steps:**
1. Leggi [ARCHITECTURE.md](ARCHITECTURE.md) per capire il sistema completo
2. Studia gli esempi in questo documento
3. Crea il tuo primo agente
4. Testa in locale
5. Deploy in production

**Risorse:**
- [FastAPI Docs](https://fastapi.tiangolo.com)
- [LangChain Docs](https://python.langchain.com)
- [LangGraph Docs](https://langchain-ai.github.io/langgraph/)

**Contribuire:**
Hai creato un agente interessante? Condividilo con la community!

---

**Documento aggiornato:** 2024-01-15
**Versione AgentHill:** 1.0.0
