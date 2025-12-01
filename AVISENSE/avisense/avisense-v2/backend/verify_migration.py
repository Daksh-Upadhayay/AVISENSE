import os
from supabase import create_client
from dotenv import load_dotenv

# Load env vars
load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not url or not key:
    print("❌ Error: Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
    exit(1)

try:
    supabase = create_client(url, key)
    
    # Check for source column
    print("🔍 Checking for 'source' column...")
    response = supabase.table("predictions").select("source").limit(1).execute()
    print("✅ 'source' column exists!")
    
    # Get latest prediction with all details
    print("\n🔍 Fetching latest prediction...")
    response = supabase.table("predictions").select("*").order("created_at", desc=True).limit(1).execute()
    
    if response.data and len(response.data) > 0:
        latest = response.data[0]
        print("\n✅ Latest Prediction in DB:")
        print(f"   ID: {latest.get('id')}")
        print(f"   Created At: {latest.get('created_at')}")
        print(f"   Engine ID: {latest.get('engine_id')}")
        print(f"   Prediction: {latest.get('prediction')}")
        print(f"   Source: {latest.get('source')}")
        print(f"   Model Version: {latest.get('model_version')}")
        print(f"   Anomaly Score: {latest.get('anomaly_score')}")
        print(f"   Risk Percent: {latest.get('risk_percent')}")
    else:
        print("\n⚠️ No predictions found in database.")

except Exception as e:
    print(f"\n❌ Operation failed: {e}")
