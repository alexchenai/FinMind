from __future__ import annotations
from collections import defaultdict
from datetime import date, timedelta
from app.models import db, Expense

# Keywords that indicate subscription services
_SUBSCRIPTION_KEYWORDS = [
    "netflix", "spotify", "hulu", "disney", "amazon prime", "apple music",
    "youtube premium", "icloud", "dropbox", "adobe", "microsoft 365",
    "office 365", "slack", "zoom", "notion", "github", "heroku",
    "aws", "gcp", "azure", "digitalocean", "linode", "cloudflare",
    "vpn", "antivirus", "grammarly", "chatgpt", "claude", "subscription",
    "monthly", "annual", "yearly", "plan", "premium",
]

def _normalize(text: str) -> str:
    return text.lower().strip()

def detect_subscriptions(uid: int, months: int = 6) -> dict:
    """
    Auto-detect subscriptions from recurring charges.
    Groups expenses by note/merchant and looks for monthly recurrence patterns.
    """
    cutoff = date.today() - timedelta(days=30 * months)
    expenses = db.session.query(Expense).filter(
        Expense.user_id == uid, Expense.date >= cutoff
    ).order_by(Expense.date).all()

    # Group by normalized note
    groups: dict[str, list] = defaultdict(list)
    for e in expenses:
        note = _normalize(getattr(e, "note", "") or "")
        if note:
            groups[note].append(e)

    detected = []
    for note, exps in groups.items():
        if len(exps) < 2:
            continue
        
        # Check if any keyword matches
        is_known = any(k in note for k in _SUBSCRIPTION_KEYWORDS)
        
        # Check recurrence: sort by date and check gaps
        exps_sorted = sorted(exps, key=lambda e: e.date)
        amounts = [float(e.amount or 0) for e in exps_sorted]
        dates = [e.date for e in exps_sorted]
        
        # Calculate gaps in days
        gaps = [(dates[i+1] - dates[i]).days for i in range(len(dates)-1)]
        if not gaps:
            continue
        avg_gap = sum(gaps) / len(gaps)
        
        # Monthly (25-35 days) or yearly (355-375 days)
        is_monthly = 25 <= avg_gap <= 35
        is_yearly = 355 <= avg_gap <= 375
        
        if not (is_monthly or is_yearly or is_known):
            continue
        
        avg_amount = sum(amounts) / len(amounts)
        frequency = "monthly" if is_monthly else ("yearly" if is_yearly else "unknown")
        
        detected.append({
            "merchant": note,
            "frequency": frequency,
            "avg_amount": round(avg_amount, 2),
            "occurrences": len(exps),
            "last_charge": dates[-1].isoformat(),
            "next_expected": (dates[-1] + timedelta(days=int(avg_gap))).isoformat(),
            "annual_cost": round(avg_amount * (12 if is_monthly else 1), 2),
            "is_known_service": is_known,
        })

    # Sort by annual cost descending
    detected.sort(key=lambda x: x["annual_cost"], reverse=True)
    total_monthly = sum(
        d["avg_amount"] for d in detected if d["frequency"] == "monthly"
    )
    total_annual = sum(d["annual_cost"] for d in detected)

    return {
        "subscriptions": detected,
        "count": len(detected),
        "total_monthly_cost": round(total_monthly, 2),
        "total_annual_cost": round(total_annual, 2),
    }
