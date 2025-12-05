# scripts/create_all_tables.py

from database import Base, engine
import models  # ここで全モデルをimportしておくことが超重要

def main() -> None:
    print("Creating all tables defined on Base.metadata ...")
    Base.metadata.create_all(bind=engine)
    print("Done.")

if __name__ == "__main__":
    main()
