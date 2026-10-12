from pathlib import Path
from datetime import datetime
import shutil

path = Path("templates/index.html")

if not path.exists():
    raise SystemExit("ERROR: templates/index.html was not found.")

html = path.read_text(encoding="utf-8")

marker = "PAYSTACK_RETURN_VERIFICATION_V1"

if marker in html:
    print("The Paystack return verification fix is already present.")
    raise SystemExit(0)

closing = "</body>"
if closing not in html.lower():
    raise SystemExit("ERROR: Could not find the closing body tag. No changes made.")

backup = path.with_name(
    path.name + ".before_paystack_fix_" +
    datetime.now().strftime("%Y%m%d_%H%M%S") + ".bak"
)
shutil.copy2(path, backup)

script = r"""
<script>
/* PAYSTACK_RETURN_VERIFICATION_V1 */
(async function () {
    const params = new URLSearchParams(window.location.search);

    if (params.get("payment") !== "return") return;

    const reference = params.get("reference") || params.get("trxref");

    if (!reference) {
        alert(
            "Payment return detected, but no transaction reference was supplied. " +
            "Please contact the church finance office to confirm your payment."
        );
        return;
    }

    const storageKey = "paystack_verified_" + reference;

    if (sessionStorage.getItem(storageKey) === "done") return;

    try {
        const response = await fetch(
            "/api/payment/verify/" + encodeURIComponent(reference),
            {
                method: "GET",
                headers: { "Accept": "application/json" },
                cache: "no-store"
            }
        );

        const result = await response.json();

        if (response.ok && result.paid === true) {
            sessionStorage.setItem(storageKey, "done");
            alert(
                "Payment successful! Reference: " + reference +
                "\nAmount: ₦" + Number(result.amount).toLocaleString("en-NG") +
                "\nStatus: PAID"
            );
        } else if (response.ok && result.paid === false) {
            alert(
                "Paystack has not confirmed this payment as successful yet. " +
                "Current status: " + (result.status || "Pending") +
                ". Please allow verification to complete before trying to pay again."
            );
        } else {
            alert(
                "We could not confirm your payment automatically. " +
                (result.error || "Please contact the church finance office.") +
                "\nKeep your payment reference: " + reference
            );
        }
    } catch (error) {
        alert(
            "Your payment return was received, but verification could not be completed. " +
            "Please do not pay again yet. Keep this reference for confirmation: " +
            reference
        );
    }
})();
</script>
"""

position = html.lower().rfind(closing)
html = html[:position] + script + "\n" + html[position:]
path.write_text(html, encoding="utf-8")

print("SUCCESS: Paystack return verification added to templates/index.html")
print("Backup saved to:", backup)
