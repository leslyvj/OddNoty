"""CLI Key Health Dashboard.

Prints a formatted table of all API keys showing usage, limits,
percentage, and status with emoji indicators.
"""

import time
import logging

logger = logging.getLogger("oddnoty.dashboard")


def print_key_health(pool_manager) -> None:
    """Print a formatted key pool health table to stdout.

    Args:
        pool_manager: KeyPoolManager instance
    """
    status = pool_manager.get_pool_status()

    print("\n" + "═" * 78)
    print(f"  🚨 OddNoty Key Pool Health — {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("═" * 78)

    for group, keys in status.items():
        group_label = group.upper().replace("_", " ")
        print(f"\n  [{group_label}]")
        print(f"  {'ID':<22} {'Provider':<18} {'Used':<8} {'Limit':<8} {'Usage':<16} {'Status'}")
        print(f"  {'─' * 72}")

        for k in keys:
            pct = k["pct"]
            bar_filled = int(pct / 10)
            bar = "█" * bar_filled + "░" * (10 - bar_filled)

            status_icon = {
                "active": "🟢",
                "limited": "🟡",
                "exhausted": "🔴",
                "dead": "💀",
            }.get(k["status"], "❓")

            print(
                f"  {k['id']:<22} {k['provider']:<18} "
                f"{k['used']:<8} {k['limit']:<8} "
                f"[{bar}] {pct:>5.1f}%  "
                f"{status_icon} {k['status']}"
            )

    # Summary line
    totals = {}
    for group in status:
        totals[group] = pool_manager.total_remaining(group)

    print(f"\n  Remaining capacity: {totals}")
    print("═" * 78 + "\n")


def format_key_health_compact(pool_manager) -> str:
    """Return a compact single-line health summary for logging.

    Example: "score: 588/1200 (49%) | odds: 999077/999999 (99%)"
    """
    parts = []
    for group in pool_manager.get_all_groups():
        status_keys = pool_manager.get_pool_status().get(group, [])
        total_used = sum(k["used"] for k in status_keys)
        total_limit = sum(k["limit"] for k in status_keys)
        pct = round(total_used / max(total_limit, 1) * 100, 1)
        remaining = pool_manager.total_remaining(group)
        parts.append(f"{group}: {remaining} remaining ({pct}% used)")
    return " | ".join(parts)


if __name__ == "__main__":
    # Demo with a mock pool manager for testing the display
    from key_pool import KeyPoolManager

    print("Loading key pool for dashboard demo...")
    try:
        pool = KeyPoolManager(config_path="goaledge_keys.yaml")
        print_key_health(pool)
    except Exception as e:
        print(f"Could not load key pool: {e}")
        print("Create goaledge_keys.yaml first — see docs/PRODUCT_SPEC.md")
