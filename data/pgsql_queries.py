MISSING_PARCELS = """
SELECT
                    vil.invoicenumber,
                    COUNT(*) AS missing_count
                FROM vendorinvoiceline vil
                LEFT JOIN invoiceline il
                    ON vil.trackingnumber = il.trackingnumber
                    AND vil.invoicenumber = il.invoiceid
                WHERE vil.invoicenumber = %s
                AND il.trackingnumber IS NULL
                GROUP BY vil.invoicenumber;
"""

DUPLICATE_PARCELS = """
SELECT
                    il.invoiceid,
                    il.invoicelinestatus,
                    il.invoicelinestatusmsg,
                    il.chargetype,
                    COUNT(*) AS duplicate_count
                FROM invoiceline il
                JOIN vendorinvoiceline vil
                    ON vil.trackingnumber = il.trackingnumber
                    AND vil.invoicenumber = il.invoiceid
                    AND vil.chargetype = il.chargetype
                WHERE vil.invoicenumber = %s
                GROUP BY
                    il.invoiceid,
                    il.invoicelinestatus,
                    il.invoicelinestatusmsg,
                    il.chargetype,
                    il.trackingnumber
                HAVING COUNT(*) > 1;
"""

MISMATCHED_PARCELS = """
SELECT
                    il.invoiceid,
                    il.invoicelinestatus,
                    il.invoicelinestatusmsg,
                    COUNT(*) AS count_lines
                FROM vendorinvoiceline vil
                JOIN invoiceline il
                    ON vil.trackingnumber = il.trackingnumber
                    AND vil.invoicenumber = il.invoiceid
                    AND vil.chargetype = il.chargetype
                WHERE vil.invoicenumber = %s
                GROUP BY
                    il.invoiceid,
                    il.invoicelinestatus,
                    il.invoicelinestatusmsg;
"""

FAILED_PARCELS = """
 SELECT
                    il.invoiceid,
                    il.invoicelinestatusmsg,
                    COUNT(*) AS failed_count
                FROM invoiceline il
                JOIN vendorinvoiceline vil
                    ON vil.trackingnumber = il.trackingnumber
                    AND vil.invoicenumber = il.invoiceid
                    AND vil.chargetype = il.chargetype
                WHERE vil.invoicenumber = %s
                AND il.invoicelinestatus = 'REJECTED'
                GROUP BY il.invoiceid, il.invoicelinestatusmsg;
"""

TOTAL_AMOUNT = """
                SELECT SUM("chargeamount")
                FROM invoiceline
                WHERE "invoiceid" = %s;
                """