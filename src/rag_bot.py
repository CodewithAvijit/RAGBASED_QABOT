from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.prompts import PromptTemplate

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
