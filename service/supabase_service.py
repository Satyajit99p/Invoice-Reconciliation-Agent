
from data.supabase_da import SupabaseDB
from typing import Any


class SupabaseService:
    def save_vendorInvoiceLine(data):
        try:
            payload_rows: list[dict[str, Any]] = []
            for row in data:
                tracking_number = str(row.get("TrackingNumber", "")).strip()
                if not tracking_number:
                    continue

                billed_amount = row.get("ChargeAmount")

                payload_rows.append(
                    {
                        "trackingnumber": tracking_number,
                        "invoicenumber": str(row.get("InvoiceNumber", "")).strip(),
                        "chargetype": str(row.get("ChargeType", "")).strip(),
                        "chargeamount": billed_amount
                    }
                )

            if not payload_rows:
                return 0
            
            SupabaseDB.insert("vendor_invoice_line", payload_rows)

        except Exception as e:
            print(f"Error processing rows: {e}")
            return 0
