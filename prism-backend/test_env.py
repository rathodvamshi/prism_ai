from app.config import settings

def main():
    key = settings.GROQ_API_KEY if settings.GROQ_API_KEY else None
    print("Loaded key:", key)

if __name__ == "__main__":
    main()