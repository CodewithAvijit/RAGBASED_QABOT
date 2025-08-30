from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import shutil
from langchain.vectorstores import Chroma
from langchain.document_loaders import PyPDFLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.prompts import PromptTemplate
from pydantic import BaseModel

# Load environment variables
load_dotenv()

# --- Configuration ---
# Use a more flexible, platform-independent path for the database and uploads
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "database")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploaded_files")

# Create directories if they don't exist
os.makedirs(DB_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ------------------------------
# Initialize embeddings with the API key from environment variables
embeddings = GoogleGenerativeAIEmbeddings(
    model="models/embedding-001",
    google_api_key=os.getenv("GEMINI_KEY")
)

# Initialize the persistent Chroma database
database = Chroma(
    persist_directory=DB_DIR,
    embedding_function=embeddings
)

# Initialize the LLM with the API key from environment variables
llm = ChatGoogleGenerativeAI(
    model="gemma-3-27b-it",
    google_api_key=os.getenv("GEMINI_KEY")
)

# ------------------------------

class QuestionRequest(BaseModel):
    """Pydantic model for the question request body."""
    question: str

# ------------------------------
# RAG chain functions with memory
class SimpleMemory:
    """A simple in-memory storage for conversation history."""
    def __init__(self, max_length=10):
        self.max_length = max_length
        self.history = []

    def add(self, question, answer):
        """Adds a new QA pair to the history, managing max length."""
        self.history.append({"question": question, "answer": answer})
        if len(self.history) > self.max_length:
            self.history.pop(0)

    def get_context(self):
        """Combines previous QA pairs into a formatted string for the prompt."""
        return "\n".join([f"Q: {h['question']}\nA: {h['answer']}" for h in self.history])

def create_rag_chain_with_memory(database, llm):
    """
    Creates a RAG chain with a simple memory component.
    Returns a callable 'ask' function that encapsulates the logic.
    """
    memory = SimpleMemory(max_length=10)

    prompt = PromptTemplate.from_template(
        """
        You are a RAG-based assistant. Use the following context from your knowledge base
        and previous conversation memory to answer the question:

        Context from knowledge base:
        <context>{context}</context>

        Previous conversation memory:
        {memory}

        Answer the question concisely using the context and memory.
        If the answer is not in the context or memory, use your general knowledge.
        Do not say "Sorry, I could not find a relevant answer."
        Provide only the answer—no extra explanations.

        Question: {input}
        """
    )

    retriever = database.as_retriever()
    chain = create_stuff_documents_chain(llm=llm, prompt=prompt)
    retriever_chain = create_retrieval_chain(retriever, chain)

    def ask(question):
        """The main function to ask a question and get an answer with memory."""
        mem_context = memory.get_context()
        response = retriever_chain.invoke({"input": question, "memory": mem_context})
        answer = response["answer"]
        memory.add(question, answer)
        return answer

    return ask

def add_knowledge(filepath):
    """Loads a document and splits it into smaller chunks."""
    splitter = RecursiveCharacterTextSplitter(chunk_size=100, chunk_overlap=10)
    if filepath.lower().endswith(".pdf"):
        loader = PyPDFLoader(filepath)
        docs = loader.load()
    elif filepath.lower().endswith(".txt"):
        loader = TextLoader(filepath)
        docs = loader.load()
    else:
        raise ValueError("Unsupported file type")
    split_docs = splitter.split_documents(docs)
    return split_docs

def add_to_database(database: Chroma, filepath: str):
    """Adds a new document to the database, checking for duplicates."""
    new_docs = add_knowledge(filepath)
    existing_docs = database.get(include=["documents"])["documents"]
    unique_docs = [doc for doc in new_docs if doc.page_content not in existing_docs]
    if unique_docs:
        database.add_documents(unique_docs)
        database.persist()
        return f"Database updated with {len(unique_docs)} new documents."
    return "No new documents to add."

# ------------------------------
# Create the RAG chain instance globally
rag_chain = create_rag_chain_with_memory(database, llm)

# ------------------------------
# FastAPI app
app = FastAPI(title="RAG Bot API", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root endpoint
@app.get("/")
def about():
    """Returns a simple message about the API."""
    return {"message": "RAG-BOT"}

# Ask question endpoint
@app.post("/ask")
async def ask_rag_bot(request: QuestionRequest):
    """Asks a question to the RAG bot and gets an answer."""
    try:
        question = request.question
        # The rag_chain object is the 'ask' function from the factory
        answer = rag_chain(question)
        return JSONResponse({"question": question, "answer": answer})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# Add knowledge endpoint
@app.post("/add-knowledge")
async def upload_file(file: UploadFile = File(...)):
    """Uploads a file (PDF or TXT) to add to the knowledge base."""
    try:
        file_location = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_location, "wb") as f:
            f.write(await file.read())
        
        result = add_to_database(database, file_location)
        return JSONResponse({"message": result})
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# View knowledge endpoint
@app.get("/view-knowledge")
def view_knowledge():
    """Returns a list of documents in the knowledge base."""
    try:
        docs = database.get(include=["documents", "metadatas"])
        knowledge_list = []
        for content, meta in zip(docs.get("documents", []), docs.get("metadatas", [])):
            knowledge_list.append({
                "content": content,
                "source": meta.get("source", "unknown")
            })
        return JSONResponse({"knowledge": knowledge_list})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# Reset knowledge base endpoint
@app.post("/reset-knowledge")
def reset_knowledge():
    """Removes all documents and re-initializes the database."""
    try:
        # The database object is a global reference
        # We don't need `global database` if we're not re-assigning it
        if os.path.exists(DB_DIR):
            shutil.rmtree(DB_DIR)
        os.makedirs(DB_DIR, exist_ok=True)
        return JSONResponse({"message": "Knowledge base has been fully reset."})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
