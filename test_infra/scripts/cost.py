#!/usr/bin/env python3
"""Check AWS costs for the current billing period."""

import json
import subprocess
import sys
from datetime import datetime, date


def get_billing_period():
    """Get the current billing period (month to date)."""
    today = date.today()
    start = today.replace(day=1)
    # End is tomorrow (Cost Explorer is exclusive on end date)
    if today.month == 12:
        end = today.replace(year=today.year + 1, month=1, day=1)
    else:
        end = today.replace(month=today.month + 1, day=1)
    return start, end


def get_costs():
    """Query AWS Cost Explorer for current period costs."""
    start, end = get_billing_period()
    
    result = subprocess.run(
        [
            "aws", "ce", "get-cost-and-usage",
            "--time-period", f"Start={start},End={end}",
            "--granularity", "MONTHLY",
            "--metrics", "UnblendedCost",
        ],
        capture_output=True,
        text=True,
    )
    
    if result.returncode != 0:
        return None, result.stderr
    
    return json.loads(result.stdout), None


def main():
    """Display AWS costs for the current billing period."""
    start, end = get_billing_period()
    
    print(f"AWS Costs for Current Billing Period")
    print(f"=" * 40)
    print(f"Period: {start} to {end - 1}")
    print()
    
    data, error = get_costs()
    
    if error:
        print(f"Error fetching costs: {error}")
        sys.exit(1)
    
    if not data or not data.get("ResultsByTime"):
        print("No cost data available")
        sys.exit(0)
    
    result = data["ResultsByTime"][0]
    period = result["TimePeriod"]
    total = result["Total"]["UnblendedCost"]
    
    amount = total.get("Amount", "0.00")
    unit = total.get("Unit", "USD")
    
    print(f"Total Cost: {amount} {unit}")
    print()
    
    # Show breakdown by service if available
    if "Groups" in result:
        print("Breakdown by Service:")
        print("-" * 40)
        for group in result["Groups"]:
            service = group["Keys"][0]
            cost = group["Metrics"]["UnblendedCost"]
            print(f"  {service}: {cost['Amount']} {cost['Unit']}")


if __name__ == "__main__":
    main()
