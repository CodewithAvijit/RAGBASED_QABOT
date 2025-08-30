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

load_dotenv()  # load GEMINI_KEY first

# ------------------------------
# Initialize embeddings
embeddings = GoogleGenerativeAIEmbeddings(
    model="models/embedding-001",
    google_api_key=os.getenv("GEMINI_KEY")
)

# Initialize database
database = Chroma(
    persist_directory=r"C:\Users\Avijit\Desktop\RAG_BASEDBOT\database2",
    embedding_function=embeddings
)

# Initialize LLM
llm = ChatGoogleGenerativeAI(
    model="gemma-3-27b-it",
    google_api_key=os.getenv("GEMINI_KEY")
)

# ------------------------------
from langchain.vectorstores import Chroma
from langchain.document_loaders import PyPDFLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from pydantic import BaseModel


# Add knowledge from PDF or TXT
def add_knowledge(filepath):
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

# Add documents to database
def add_to_database(database: Chroma, filepath: str):
    new_docs = add_knowledge(filepath)

    # Get existing documents as strings
    existing_docs = database.get(include=["documents"])["documents"]

    # Keep only new docs
    unique_docs = [doc for doc in new_docs if doc.page_content not in existing_docs]

    if unique_docs:
        database.add_documents(unique_docs)
        database.persist()
        return f"Database updated with {len(unique_docs)} new documents"

    return "No new documents to add"
# RAG chain functions
def create_rag_chain(database, llm):
    prompt = PromptTemplate.from_template(
        """
        You are a RAG who can only answer from this {context}.
        If the information is not present, say 'I don't have any information'.
        Question: {input}
        """
    )
    retriever = database.as_retriever()
    chain = create_stuff_documents_chain(llm=llm, prompt=prompt)
    retriever_chain = create_retrieval_chain(retriever, chain)
    return retriever_chain

def ask_question(rag_chain, question):
    return rag_chain.invoke({"input": question})["answer"]

# ------------------------------
# Create RAG chain
rag_chain = create_rag_chain(database, llm)

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
class QuestionRequest(BaseModel):
    question: str
# Root endpoint
@app.get("/")
def about():
    return {"message": "RAG-BOT"}

# Ask question endpoint
@app.post("/ask")
async def ask_rag_bot(request: QuestionRequest):
    try:
        question = request.question
        answer = ask_question(rag_chain, question)
        return JSONResponse({"question": question, "answer": answer})
    except Exception as e:
        return JSONResponse({"error": str(e)})
# Add knowledge endpoint
@app.post("/add-knowledge")
async def upload_file(file: UploadFile = File(...)):
    try:
        # Save uploaded file temporarily
        file_location = f"C:\\Users\\Avijit\\Desktop\\RAG_BASEDBOT\\pdftext\\{file.filename}"
        with open(file_location, "wb") as f:
            f.write(await file.read())
        
        # Add to database
        result = add_to_database(database, file_location)
        return JSONResponse({"message": result})
    except Exception as e:
        return JSONResponse({"error": str(e)})

# View knowledge endpoint
@app.get("/view-knowledge")
def view_knowledge():
    try:
        # Get documents and metadatas
        docs = database.get(include=["documents", "metadatas"])
        knowledge_list = []
        for content, meta in zip(docs["documents"], docs["metadatas"]):
            knowledge_list.append({
                "content": content,
                "source": meta.get("source", "unknown")
            })
        return JSONResponse({"knowledge": knowledge_list})
    except Exception as e:
        return JSONResponse({"error": str(e)})
# Reset knowledge base endpoint
@app.post("/reset-knowledge")
@app.post("/reset-knowledge")
def reset_knowledge():
    try:
        global database  # reference the current Chroma instance
        # Close the database
        database._client.close()  # forcibly close sqlite connection

        db_path = r"C:\Users\Avijit\Desktop\RAG_BASEDBOT\database2"
        shutil.rmtree(db_path)
        os.makedirs(db_path, exist_ok=True)

        # Re-initialize the database
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        from langchain.vectorstores import Chroma

        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",
            google_api_key=os.getenv("GEMINI_KEY")
        )
        database = Chroma(
            persist_directory=db_path,
            embedding_function=embeddings
        )

        return JSONResponse({"message": "Knowledge base has been fully reset."})
    except Exception as e:
        return JSONResponse({"error": str(e)})