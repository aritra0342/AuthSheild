import numpy as np
from typing import Dict, List, Optional
from sklearn.ensemble import IsolationForest
from sklearn.metrics.pairwise import cosine_similarity
import pickle
import os
from config import config

_model = None
_model_path = "isolation_forest.pkl"

def get_model():
    global _model
    if _model is None:
        if os.path.exists(_model_path):
            with open(_model_path, "rb") as f:
                _model = pickle.load(f)
        else:
            _model = IsolationForest(
                contamination="auto",
                random_state=42,
                n_estimators=100
            )
    return _model

def train_model(X_train: np.ndarray):
    model = get_model()
    model.fit(X_train)
    with open(_model_path, "wb") as f:
        pickle.dump(model, f)
    return model

def calculate_anomaly_score(feature_vector: List[float]) -> float:
    model = get_model()
    X = np.array([feature_vector])
    
    try:
        decision = model.decision_function(X)[0]
        decision = float(decision)
        score = (decision + 0.5) / 1.5
        score = float(max(0.0, min(1.0, 0.5 - score)))
    except:
        score = 0.5
    
    return score

def calculate_similarity_score(feature_vector: List[float], cluster_vectors: List[List[float]]) -> float:
    if not cluster_vectors:
        return 0.0
    X = np.array([feature_vector])
    cluster = np.array(cluster_vectors)
    centroid = np.mean(cluster, axis=0).reshape(1, -1)
    similarity = cosine_similarity(X, centroid)[0][0]
    return float(max(0.0, min(1.0, similarity)))

def calculate_risk_score(
    feature_vector: List[float],
    cluster_vectors: Optional[List[List[float]]] = None,
    ip_entropy: float = 0.0,
    cluster_density: float = 0.0
) -> Dict:
    anomaly_score = calculate_anomaly_score(feature_vector)
    
    similarity_score = 0.0
    if cluster_vectors:
        similarity_score = calculate_similarity_score(feature_vector, cluster_vectors)
    
    risk_score = (
        0.40 * anomaly_score +
        0.30 * similarity_score +
        0.15 * ip_entropy +
        0.15 * cluster_density
    )
    
    risk_score = float(min(max(risk_score, 0.0), 1.0))
    
    is_suspicious = bool(risk_score > config.RISK_SCORE_THRESHOLD)
    
    return {
        "risk_score": round(float(risk_score), 4),
        "is_suspicious": is_suspicious,
        "anomaly_score": round(float(anomaly_score), 4),
        "similarity_score": round(float(similarity_score), 4),
        "ip_entropy": round(float(ip_entropy), 4),
        "cluster_density": round(float(cluster_density), 4)
    }
