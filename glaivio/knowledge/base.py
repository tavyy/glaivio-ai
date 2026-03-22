from pathlib import Path


class Knowledge:
    """
    Auto-indexes files into a vector store for semantic search.
    Supports: .txt, .md, .pdf

    Usage:
        agent = Agent(
            instructions="You are a helpful assistant.",
            knowledge=Knowledge(["./faqs.md", "./pricing.pdf"]),
        )

    The agent will automatically search knowledge when answering questions.

    Requires:
        pip install glaivio[knowledge]
    """

    def __init__(self, sources: list[str], persist_dir: str = ".glaivio/knowledge"):
        self.sources = [Path(s) for s in sources]
        self.persist_dir = persist_dir
        self._retriever = None

    def _load_documents(self):
        """Load all source files into Langchain documents."""
        try:
            from langchain_community.document_loaders import (
                TextLoader,
                UnstructuredMarkdownLoader,
                PyPDFLoader,
            )
            from langchain_text_splitters import RecursiveCharacterTextSplitter
        except ImportError:
            raise ImportError(
                "Knowledge requires additional dependencies.\n"
                "Install with: pip install glaivio[knowledge]"
            )

        docs = []
        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)

        for path in self.sources:
            if not path.exists():
                print(f"[Glaivio] Warning: knowledge file not found: {path}")
                continue

            suffix = path.suffix.lower()
            if suffix == ".pdf":
                loader = PyPDFLoader(str(path))
            elif suffix == ".md":
                loader = UnstructuredMarkdownLoader(str(path))
            else:
                loader = TextLoader(str(path))

            raw = loader.load()
            chunks = splitter.split_documents(raw)
            docs.extend(chunks)
            print(f"[Glaivio] Indexed {len(chunks)} chunks from {path.name}")

        return docs

    def build_retriever(self):
        """Build and return a retriever tool the agent can use."""
        try:
            from langchain_chroma import Chroma
            from langchain_community.embeddings import SentenceTransformerEmbeddings
            from langchain.tools.retriever import create_retriever_tool
        except ImportError:
            raise ImportError(
                "Knowledge requires additional dependencies.\n"
                "Install with: pip install glaivio[knowledge]"
            )

        embeddings = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")

        docs = self._load_documents()
        if not docs:
            print("[Glaivio] Warning: no knowledge documents loaded.")
            return None

        vectorstore = Chroma.from_documents(
            documents=docs,
            embedding=embeddings,
            persist_directory=self.persist_dir,
        )

        retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

        return create_retriever_tool(
            retriever,
            name="search_knowledge",
            description="Search the knowledge base to answer questions about policies, FAQs, pricing, and other information. Always use this before saying you don't know.",
        )
