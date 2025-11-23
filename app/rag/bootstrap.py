import asyncio
from .store import index_documents
from .seed_data import SAMPLE_DOCS


async def main():
    await index_documents(SAMPLE_DOCS)


if __name__ == "__main__":
    asyncio.run(main())
