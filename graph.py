from neo4j import GraphDatabase
from typing import List, Dict, Optional
from config import config

_driver = None
_connected = False

def get_driver():
    global _driver, _connected
    if _driver is None:
        try:
            _driver = GraphDatabase.driver(
                config.NEO4J_URI,
                auth=(config.NEO4J_USER, config.NEO4J_PASSWORD)
            )
            _connected = True
        except Exception as e:
            print(f"Neo4j connection error: {e}")
            _connected = False
    return _driver if _connected else None

def close_driver():
    global _driver, _connected
    if _driver:
        try:
            _driver.close()
        except:
            pass
    _driver = None
    _connected = False

def is_connected() -> bool:
    return _connected

def init_schema():
    driver = get_driver()
    if not driver:
        print("Neo4j not connected, skipping schema init")
        return
    try:
        with driver.session() as session:
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE")
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (b:BehaviorHash) REQUIRE b.hash IS UNIQUE")
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (d:DeviceHash) REQUIRE d.hash IS UNIQUE")
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (i:IPGroup) REQUIRE i.prefix IS UNIQUE")
        print("Neo4j schema initialized")
    except Exception as e:
        print(f"Neo4j schema error: {e}")

def add_user_node(user_id: str, risk_score: float = 0.0, behavior_hash: str = "", 
                  device_hash: str = "", ip_prefix: str = ""):
    driver = get_driver()
    if not driver:
        return
    
    try:
        with driver.session() as session:
            session.run(
                "MERGE (u:User {id: $user_id}) SET u.risk_score = $risk_score, u.flagged = false",
                user_id=user_id, risk_score=risk_score
            )
            
            if behavior_hash:
                session.run("MERGE (b:BehaviorHash {hash: $hash})", hash=behavior_hash)
                session.run(
                    "MATCH (u:User {id: $user_id}), (b:BehaviorHash {hash: $hash}) "
                    "MERGE (u)-[:USED_BEHAVIOR]->(b)",
                    user_id=user_id, hash=behavior_hash
                )
            
            if device_hash:
                session.run("MERGE (d:DeviceHash {hash: $hash})", hash=device_hash)
                session.run(
                    "MATCH (u:User {id: $user_id}), (d:DeviceHash {hash: $hash}) "
                    "MERGE (u)-[:SHARED_DEVICE]->(d)",
                    user_id=user_id, hash=device_hash
                )
            
            if ip_prefix:
                session.run("MERGE (i:IPGroup {prefix: $prefix})", prefix=ip_prefix)
                session.run(
                    "MATCH (u:User {id: $user_id}), (i:IPGroup {prefix: $prefix}) "
                    "MERGE (u)-[:LOGIN_FROM]->(i)",
                    user_id=user_id, prefix=ip_prefix
                )
    except Exception as e:
        print(f"Neo4j add_user_node error: {e}")

def update_user_risk(user_id: str, risk_score: float):
    driver = get_driver()
    if not driver:
        return
    try:
        with driver.session() as session:
            session.run(
                "MATCH (u:User {id: $user_id}) SET u.risk_score = $risk_score",
                user_id=user_id, risk_score=risk_score
            )
    except Exception as e:
        print(f"Neo4j update_user_risk error: {e}")

def detect_clusters_louvain() -> List[Dict]:
    driver = get_driver()
    if not driver:
        return []
    
    try:
        with driver.session() as session:
            result = session.run("""
                MATCH (u:User)-[:USED_BEHAVIOR]->(b:BehaviorHash)
                WITH u, collect(b.hash) as behaviors
                WITH collect(u) as users
                UNWIND users as u1
                UNWIND users as u2
                WITH u1, u2 WHERE u1.id < u2.id
                MATCH (u1)-[:USED_BEHAVIOR]->(b:BehaviorHash)<-[:USED_BEHAVIOR]-(u2)
                WITH u1, u2, count(b) as shared
                WHERE shared > 0
                MERGE (u1)-[:SIMILAR_TO {weight: shared}]->(u2)
            """)
            
            result = session.run("""
                MATCH (u:User)
                OPTIONAL MATCH (u)-[:SIMILAR_TO]->(peer:User)
                WITH u, count(peer) as peer_count, collect(peer.id) as peers
                RETURN u.id as user_id, u.risk_score as risk_score, 
                       peer_count as cluster_size, peers
                ORDER BY peer_count DESC
            """)
            
            clusters = []
            for record in result:
                clusters.append({
                    "user_id": record["user_id"],
                    "risk_score": record["risk_score"],
                    "cluster_size": record["cluster_size"],
                    "peers": record["peers"] or []
                })
            return clusters
    except Exception as e:
        print(f"Neo4j detect_clusters error: {e}")
        return []

def get_cluster_density(user_id: str) -> float:
    driver = get_driver()
    if not driver:
        return 0.0
    
    try:
        with driver.session() as session:
            result = session.run("""
                MATCH (u:User {id: $user_id})-[:USED_BEHAVIOR]->(b:BehaviorHash)<-[:USED_BEHAVIOR]-(peer:User)
                WHERE peer.id <> $user_id
                WITH collect(peer) as peers
                UNWIND range(0, size(peers)-2) as i
                UNWIND range(i+1, size(peers)-1) as j
                WITH peers[i] as p1, peers[j] as p2, size(peers) as peer_count
                OPTIONAL MATCH (p1)-[:USED_BEHAVIOR]->(:BehaviorHash)<-[:USED_BEHAVIOR]-(p2)
                WITH count(p2) as connections, peer_count
                WITH CASE WHEN peer_count > 1 THEN peer_count * (peer_count - 1) / 2.0 ELSE 1.0 END as max_connections
                RETURN CASE WHEN max_connections > 0 THEN count(*) / max_connections ELSE 0.0 END as density
            """, user_id=user_id)
            
            record = result.single()
            if record and record["density"] is not None:
                return float(record["density"])
            return 0.0
    except Exception as e:
        print(f"Neo4j get_cluster_density error: {e}")
        return 0.0

def get_flagged_users(cluster_size_threshold: int, similarity_threshold: float, 
                      risk_threshold: float) -> List[Dict]:
    driver = get_driver()
    if not driver:
        return []
    
    try:
        with driver.session() as session:
            result = session.run("""
                MATCH (u:User)-[:USED_BEHAVIOR]->(b:BehaviorHash)<-[:USED_BEHAVIOR]-(peer:User)
                WHERE peer.id <> u.id
                WITH u, count(DISTINCT peer) as cluster_size, avg(peer.risk_score) as avg_risk, u.risk_score as risk_score
                WHERE cluster_size >= $cluster_size AND risk_score >= $risk_threshold
                SET u.flagged = true
                RETURN u.id as user_id, u.risk_score as risk_score, 
                       cluster_size, avg_risk
            """, cluster_size=cluster_size_threshold, risk_threshold=risk_threshold)
            
            flagged = []
            for record in result:
                flagged.append({
                    "user_id": record["user_id"],
                    "risk_score": record["risk_score"],
                    "cluster_size": record["cluster_size"],
                    "avg_cluster_risk": record["avg_risk"]
                })
            return flagged
    except Exception as e:
        print(f"Neo4j get_flagged_users error: {e}")
        return []

def get_all_clusters() -> List[Dict]:
    driver = get_driver()
    if not driver:
        return []
    
    try:
        with driver.session() as session:
            result = session.run("""
                MATCH (u:User)-[:USED_BEHAVIOR]->(b:BehaviorHash)<-[:USED_BEHAVIOR]-(peer:User)
                WHERE u.id < peer.id
                WITH b.hash as behavior, collect(DISTINCT u.id) + collect(DISTINCT peer.id) as members
                WITH behavior, members, size(members) as size
                WHERE size > 1
                RETURN behavior, members, size
                ORDER BY size DESC
            """)
            
            clusters = []
            for record in result:
                clusters.append({
                    "behavior_hash": record["behavior"],
                    "members": record["members"],
                    "size": record["size"]
                })
            return clusters
    except Exception as e:
        print(f"Neo4j get_all_clusters error: {e}")
        return []

def get_user_cluster(user_id: str) -> Dict:
    driver = get_driver()
    if not driver:
        return {"user_id": user_id, "peers": [], "cluster_size": 0}
    
    try:
        with driver.session() as session:
            result = session.run("""
                MATCH (u:User {id: $user_id})-[:USED_BEHAVIOR]->(b:BehaviorHash)<-[:USED_BEHAVIOR]-(peer:User)
                RETURN peer.id as peer_id, peer.risk_score as risk_score
            """, user_id=user_id)
            
            peers = []
            for record in result:
                peers.append({
                    "user_id": record["peer_id"],
                    "risk_score": record["risk_score"]
                })
            return {"user_id": user_id, "peers": peers, "cluster_size": len(peers)}
    except Exception as e:
        print(f"Neo4j get_user_cluster error: {e}")
        return {"user_id": user_id, "peers": [], "cluster_size": 0}

def clear_flag(user_id: str):
    driver = get_driver()
    if not driver:
        return
    try:
        with driver.session() as session:
            session.run(
                "MATCH (u:User {id: $user_id}) SET u.flagged = false",
                user_id=user_id
            )
    except Exception as e:
        print(f"Neo4j clear_flag error: {e}")
