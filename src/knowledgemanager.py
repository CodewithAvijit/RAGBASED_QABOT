from langchain.vectorstores import Chroma
from langchain.document_loaders import PyPDFLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

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
    
    # Split and add source metadata
    split_docs = splitter.split_documents(docs)
    for doc in split_docs:
        doc.metadata["source"] = filepath  # <-- add source info
    return split_docs

def add_to_database(database: Chroma, filepath: str):
    new_docs = add_knowledge(filepath)
    
    # Get existing content strings
    existing_docs = database.get(include=["documents"], include_metadata=True)["documents"]
    existing_texts = [doc["page_content"] for doc in existing_docs]

    # Keep only new docs
    unique_docs = [doc for doc in new_docs if doc.page_content not in existing_texts]

    if unique_docs:
        database.add_documents(unique_docs)
        database.persist()
        return f"Database updated with {len(unique_docs)} new documents"
    
    return "No new documents to add"
