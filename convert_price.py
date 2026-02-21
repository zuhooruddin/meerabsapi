#!/usr/bin/env python3
"""
Simple utility script to convert PKR to EUR prices.
Usage: python convert_price.py <pkr_amount> [exchange_rate]
"""
import sys

def convert_pkr_to_eur(pkr_amount, exchange_rate=0.0033):
    """
    Convert PKR to EUR.
    
    Args:
        pkr_amount: Price in Pakistani Rupees
        exchange_rate: Exchange rate (default: 0.0033, meaning 1 EUR ≈ 303 PKR)
    
    Returns:
        Price in EUR (rounded to nearest integer)
    """
    eur_amount = pkr_amount * exchange_rate
    return int(round(eur_amount))

def main():
    if len(sys.argv) < 2:
        print("Usage: python convert_price.py <pkr_amount> [exchange_rate]")
        print("Example: python convert_price.py 13800")
        print("Example: python convert_price.py 13800 0.0033")
        sys.exit(1)
    
    try:
        pkr_amount = float(sys.argv[1])
        exchange_rate = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0033
    except ValueError:
        print("Error: Please provide valid numbers")
        sys.exit(1)
    
    eur_amount = convert_pkr_to_eur(pkr_amount, exchange_rate)
    
    print(f"PKR: {pkr_amount:,.2f}")
    print(f"Exchange Rate: 1 PKR = {exchange_rate} EUR (1 EUR ≈ {1/exchange_rate:.2f} PKR)")
    print(f"EUR: {eur_amount:,}")

if __name__ == "__main__":
    main()
