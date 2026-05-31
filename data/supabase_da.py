import os
from typing import Any, List, Dict
from supabase import create_client, Client


class SupabaseDB:
    def __init__(self):
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")

        if not url or not key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set")

        self.client: Client = create_client(url, key)

    def insert(self, table: str, rows: List[Dict[str, Any]]):
        if not rows:
            return []

        response = self.client.table(table).insert(rows).execute()

        if hasattr(response, "data"):
            return response.data

        return response