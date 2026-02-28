import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN", "your-tenant.auth0.com")
    AUTH0_CLIENT_ID = os.getenv("AUTH0_CLIENT_ID", "")
    AUTH0_CLIENT_SECRET = os.getenv("AUTH0_CLIENT_SECRET", "")
    AUTH0_AUDIENCE = os.getenv("AUTH0_AUDIENCE", f"https://{AUTH0_DOMAIN}/api/v2/")
    
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    MONGO_DB = os.getenv("MONGO_DB", "authshield")
    
    NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")
    
    CLUSTER_SIZE_THRESHOLD = int(os.getenv("CLUSTER_SIZE_THRESHOLD", "5"))
    SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.85"))
    RISK_SCORE_THRESHOLD = float(os.getenv("RISK_SCORE_THRESHOLD", "0.7"))
    
    AUTOENCODER_THRESHOLD = float(os.getenv("AUTOENCODER_THRESHOLD", "0.1"))

config = Config()
