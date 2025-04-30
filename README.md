# Flare Twitter Sentiment Pricing Agent

An end-to-end system that scrapes tweets, analyzes them with AI, stores data on Filecoin, and uses Flare’s oracles to power on-chain sentiment feeds and composite indicators for crypto pricing and governance.

---

## 🚀 Key Features

1. **Twitter Scraper & AI Analysis**  
   • Headless Selenium scraper collects tweets for any query (e.g. “Ethereum”).  
   • AI agent (LangChain + LangGraph) computes a “deletion likelihood” score per tweet (0…1).  
   • Deduces the relevant coin, if any, and aggregates into a normalized 0–100 sentiment score per coin.  

2. **Decentralized Storage**  
   • Saves each scrape as CSV, converts to CAR, pins to IPFS via Pinata.  
   • Uses StorAcha to make a Filecoin storage deal and records metadata on-chain in `AIDatasetRegistry`.  

3. **Per-Coin FTSO Sentiment Feeds**  
   • For each coin detected in the tweets, pushes the aggregated 0–100 score to its own MockTwitterFTSO contract.  
   • Consumers can read `tweetScore()` on-chain in Solidity for trustless sentiment data.  

4. **FTSO Price Consumer**  
   • A single script fetches all Flare Time Series Oracle (FTSO) price feeds on Coston2.  
   • Extracts the current price for the coin scraped.  

5. **Strength Metric**  
   • Computes an “outreach strength” = (# tweets) × (sum of follower counts).  
   • Appended alongside `timestamp, score, price` in `FINAL_{COIN}.csv`.  

6. **Composite Sentiment Consumer**  
   • Blends social sentiment (70%) + macroeconomic proof data (30%) into a fixed-point “composite” oracle.  
   • Macro data is ingested via a verifiable JSON-API proof and submitted on-chain.  

---

## 🎯 Flare Protocol Integration

- **FTSO (Flare Time Series Oracle)**  
  • Deployed per-coin MockTwitterFTSO contracts, push our tweetScore, then read it in our CompositeSentimentConsumer.

FTSO TweetScore Feed Contract Address: 0x30E0bbC0888e691c60232843fc80514f3538645d

FTSO Price Feed Consumer Contract Address: 0x2d13826359803522cCe7a4Cfa2c1b582303DD0B4

- **IJsonApi (JSON-API Proof)**  
  • Wrap any external macro score (CPI, GDP growth) in an IJsonApi proof and call `updateComposite(...)` on-chain.  [deployed and tested but yet to be integrated into main flow]

- **CompositeSentimentConsumer**  
  • Deployed on Flare mainnet, reads our per-coin sentiment + macro proof, outputs one on-chain composite value.  
  • Use it to dynamically price our datasets, trigger governance or automated trading at thresholds.   [deployed contracts but yet to be integrated into main flow]


Additional Contracts:
DATA_STORAGE_CONTRACT_ADDR=0x8fa300Faf24b9B764B0D7934D8861219Db0626e5
TOKEN_ADDRESS=0x959e85561b3cc2E2AE9e9764f55499525E350f56
GOVERNOR_ADDRESS=0x5F8E67E37e223c571D184fe3CF4e27cae33E81fF
TIMELOCK_ADDRESS=0x62FD5Ab8b5b1d11D0902Fce5B937C856301e7bf8

---
# For Local Use:

## 🛠 Installation & Setup

1. **Clone & install dependencies**  
   ```bash
   git clone https://github.com/yourusername/flare-twitter-pricing-agent.git
   cd flare-twitter-pricing-agent
   python3 -m venv venv && source venv/bin/activate
   pip install -r requirements.txt

1. **Create .env file** 
```
# Twitter credentials
TWITTER_MAIL=you@example.com
TWITTER_USERNAME=@yourhandle
TWITTER_PASSWORD=yourpassword
HEADLESS=yes

# IPFS / Filecoin (Pinata + StorAcha)
PINATA_API_KEY=…
PINATA_API_SECRET=…
PINATA_JWT=…
W3UP_SPACE_DID=…

# OpenAI
OPEN_AI_API_KEY=…

# Flare RPC & keys
FLARE_RPC_URL=https://rpc.flare.network
FLARE_PRIVATE_KEY=…
TWITTER_FTSO_ADDR=0x30E0bbC0888e691c60232843fc80514f3538645d
FTSO_CONSUMER_ADDRESS=0xYourConsumerAddress
COSTON2_RPC_URL=https://coston2.rpc.flare.network
COMPOSITE_ADDR=0x6eDb539fa857f96c6B2cD4DDd1654e8D8e90d06F
```

## ▶️ Usage
Run the scraper, analyze tweets, push sentiment, fetch prices, and output per-coin CSVs:
Example flags:
```
python scraper/__main__.py \
  --query "Ethereum" \
  --tweets 5 \
  --headlessState yes
```
After completion you will see:
  • A raw tweet CSV in ./tweets/
  • Per-coin files FINAL_testETH.csv, FINAL_testBTC.csv, etc. containing:
```
timestamp,score,price,strength
2025-04-27T02:15:00Z,42,1850.23,3500
```

## 🏗 Architecture & Flow
### Scrape & Screenshot
Collect tweets, capture screenshot, pin to IPFS.

### AI Analysis
LangGraph agent scores each tweet & segregates by coin.

### Aggregate & Push
Group by detected coin, compute normalized sentiment, push to FTSO.

### Price Query
Fetch current price from FTSO consumer.

### Strength Calculation
(# tweets) × (sum of followers) per coin.

### Output
Append timestamp, score, price, strength in each FINAL_{coin}.csv.

### Macro Proof & Composite
(Optional) Generate macro_proof.json, call updateComposite(...), read lastComposite.

## 🔮 Future Enhancements/Additions
  • FDC Integration for real-time macro data via Flare Data Connector.

  • Multi-model Sentiment (bullish vs. bearish, topic clustering).

  • Hosted Continuous Deployment, via cron or frontend trigger. - See Frontend

  • DAO-Driven Governance triggers based on composite thresholds. - See Frontend

  • Using Collected Data + Using Model on Historical Twitter Data Paired with Pricing Data to Train Custom Predictive Model.
