import os
from supabase import create_client, Client

supabase: Client = create_client(
    os.environ.get("SUPABASE_URL", "your_supabase_url_here"),
    os.environ.get("SUPABASE_KEY", "your_supabase_anon_key_here")
)
