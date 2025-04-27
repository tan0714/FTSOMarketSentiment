from ai_coin_identifier import identify_coin

sample_texts = [
    "I’m all in on $ETH, the future of finance!",
    "Ethereum 2.0 staking yields look great.",
    "Just bought more ETH today 🚀"
]

coin = identify_coin(sample_texts)
print("Detected coin symbol:", coin)
