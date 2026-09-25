"""Rebuild the Neo4j graph from PostgreSQL: wipe the graph, then re-sync.

Run after data changes (e.g. after `python data/ingest.py`) to rebuild
Product nodes and relationships from the Postgres source of truth.

Usage:
    python scripts/rebuild_graph.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.graph import execute_query, get_graph_stats
from core.sync import sync_products, create_relationships


def wipe():
    """Delete all nodes and relationships in Neo4j."""
    print("Wiping Neo4j graph...")
    execute_query("MATCH (n) DETACH DELETE n")
    print("  Wiped.")


def main():
    wipe()
    sync_products()
    create_relationships()

    print("\nGraph statistics:")
    for s in get_graph_stats():
        print(f"  {s['label']}: {s['count']}")
    print("\nGraph rebuild complete!")


if __name__ == "__main__":
    main()
