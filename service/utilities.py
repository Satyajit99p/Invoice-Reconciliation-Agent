from service.supabase_service import SupabaseService
import pandas as pd

class Utility:

    def ingest_vendor_excel(file_path):
        if str(file_path).lower().endswith(".csv"):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
        
        #convert the dataframe into a list of dictionaries
        records = df.to_dict(orient='records')

        SupabaseService.save_vendorInvoiceLine(records)

        total = df["ChargeAmount"].fillna(0).sum()

        return total
    
    def select_tool(query: str) -> str:
        pass