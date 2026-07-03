import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Flask
    FLASK_ENV = os.getenv("FLASK_ENV", "production")
    DEBUG = os.getenv("FLASK_DEBUG", "False") == "True"
    PORT = int(os.getenv("PORT", 5000))

    # Supabase
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
    SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

    # Ollama
    OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")

    # Stripe
    STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
    STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY")
    STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
    STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID")

    # CORS
    FRONTEND_URL = os.getenv("FRONTEND_URL", "https://stockpredi.vercel.app")

config = Config()
