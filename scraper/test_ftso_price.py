from ftso_price import fetch_all_feeds, get_price_for


feeds = fetch_all_feeds()
print("All feeds:", feeds)

symbol = "testETH"
price, ts = get_price_for(symbol)
print(f"{symbol} → price {price} @ {ts}")
