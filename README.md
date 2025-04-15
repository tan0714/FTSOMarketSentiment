# Advanced Twitter Sentiment & Crypto Pricing Platform

This project is an advanced, modular, and interoperable platform designed to harness real-time Twitter sentiment for predicting cryptocurrency price changes. By integrating a Twitter scraper with AI-driven tweet analysis, decentralized storage on Filecoin, and on-chain data provenance via smart contracts, this project delivers a state-of-the-art solution that addresses modern challenges in data integrity, ethical data sourcing, and efficient AI deployment.

---

## Overview

The platform collects tweets using an advanced scraper, analyzes tweet content using AI agents (powered by LangChain and LangGraph), and combines the resulting sentiment data with historical crypto pricing data to predict coin price movements. The system’s output is archived as CSV files that are stored immutably on Filecoin using Storacha. On-chain smart contracts are used to record dataset metadata, ensuring transparent data provenance and fair attribution.

---

## Key Challenges Addressed

- **Data Provenance:**  
  Filecoin's immutable storage guarantees transparent lineage and verification of data authenticity. On-chain smart contracts (like AIDatasetRegistry) reinforce trust by registering dataset metadata, ensuring that the data used for AI training and market prediction remains untampered.

- **Data Sourcing & Ethics:**  
  The scraper collects high-quality Twitter data while respecting user privacy. With decentralized storage and DAOs, the project facilitates ethical sourcing and proper incentives for authentic contributions.

- **Fair Attribution:**  
  Smart contracts and decentralized data marketplaces enable transparent and fair compensation for data creators. This is crucial in an era of AI-generated content.

- **Efficient AI & Environmental Considerations:**  
  By decentralizing data storage and using advanced AI models with consistent and explainable reasoning (chain-of-thought), our architecture minimizes computational waste and lowers the environmental impact of high-energy computations.

- **Modular Architecture & Interchain Interoperability:**  
  The system is built in a modular fashion, allowing seamless upgrades and integrations across multiple blockchain networks. This open architecture supports agentic economies where autonomous agents interact to optimize resource allocation.

---

## System Architecture

### 1. Twitter Scraper & AI Analysis
- **Scraper Functionality:**  
  Built using Selenium and enhanced by headless browser automation, the scraper collects tweets based on specific queries (e.g., tweets mentioning “ethereum”).  
- **Tweet Analysis:**  
  Each tweet is passed through an AI agent that assesses its “deletion likelihood” (a proxy for controversial sentiment) using LangChain. The analysis is refined via chain-of-thought reasoning and persistent memory techniques for consistent judgment.

### 2. Decentralized Storage with Filecoin
- **CSV Generation & CAR Conversion:**  
  After scraping, tweets are saved into a CSV file. This CSV is then converted into a CAR file using IPFS tools.
- **Storacha Integration:**  
  The CAR file is uploaded to Filecoin through Storacha, ensuring that every dataset has a verifiable and immutable record.

### 3. Crypto Pricing Model
- **Historical & Sentiment Data:**  
  The enriched tweet dataset (with sentiment scores) is combined with historical market data to feed a predictive pricing model.
- **Prediction & Trading Insight:**  
  The model leverages aggregated social sentiment to forecast future price movements, providing vital insights for market analysis and trading strategies.

### 4. On-Chain Data Provenance & Governance
- **Smart Contracts:**  
  - **AIDatasetRegistry:** Registers dataset metadata (title, CID, file size, description, price, Filecoin deal ID, preview) on-chain.  
    _Deployed at:_ `0x8fa300Faf24b9B764B0D7934D8861219Db0626e5`
    
  - **DatasetAccessAgent:** Allows users to request and gain access to datasets by paying a fee, with AI agents listening to emitted events for further processing.  
    _Deployed at:_ `0xf0f994B4A8dB86A46a1eD4F12263c795b26703Ca`
    
  - **TruthToken:** A utility token that incentivizes data contributions and facilitates fair compensation.  
    _Deployed at:_ `0x959e85561b3cc2E2AE9e9764f55499525E350f56`
    
  - **MyTimelockController:** Manages secure, time-locked transactions and operations on-chain.  
    _Deployed at:_ `0x62FD5Ab8b5b1d11D0902Fce5B937C856301e7bf8`
    
  - **TruthAnchorGovernor:** Implements decentralized governance, enabling proposals (e.g., candidate Twitter handles) and voting based on collected sentiment data.  
    _Deployed at:_ `0x5F8E67E37e223c571D184fe3CF4e27cae33E81fF`

---

## Installation & Setup

### Prerequisites
- **Python 3.8+**
- **Node.js & npm** (for some auxiliary tools)
- **IPFS & ipfs-car CLI Tools** (ensure they are installed and available in your PATH)
- A properly configured **.env** file containing:
  ```ini
  TWITTER_MAIL=your_twitter_mail
  TWITTER_USERNAME=your_twitter_username
  TWITTER_PASSWORD=your_twitter_password
  HEADLESS=yes
  PINATA_API_KEY=your_pinata_api_key
  PINATA_API_SECRET=your_pinata_api_secret
  PINATA_JWT=your_pinata_jwt
  W3UP_SPACE_DID=your_space_did
  W3UP_XAUTH=your_xauth
  W3UP_AUTH=your_authorization_token
  OPEN_AI_API_KEY=your_openai_api_key


## Improving Consistency of Judgment
- **Calibrate the System Prompt:**  
  Refine the agent's prompt to include clear guidelines and examples on what constitutes controversial content.
- **Chain-of-Thought Reasoning:**  
  Update the prompt to require a brief reasoning summary (chain-of-thought) before providing the final controversy score.
- **Memory Integration:**  
  Utilize persistent memory (e.g., `ConversationBufferMemory`) to store previous analyses for consistent decisions over time.
- **Consistency Checker Subchain:**  
  Implement a subchain that cross-checks the deletion likelihood score with additional tools (e.g., sentiment analysis) to validate results.

## Advanced LangGraph Integration
- **Interactive Visualization:**  
  Leverage LangGraph's visualization API to create interactive graphs of the agent’s reasoning process.
- **Graph-Based Workflow:**  
  Break down the tweet analysis into modular nodes (e.g., content extraction, sentiment evaluation, controversy assessment) and edges that show the data flow.
- **Utilize Prebuilt Agents:**  
  Integrate LangGraph prebuilt agents (such as a ReAct agent) for multi-step reasoning and tool usage.
- **Graph Debugging Hooks:**  
  Add logging and hooks at key decision points to generate visual summaries of the chain, aiding in debugging and improvement.



# Future Roadmap
**Real-Time Crypto Pricing API Integration:**
Further integrate live market data feeds for enhanced trading insights.

**Enhanced Data Attribution & Incentive Models:**
Refine token-based incentive mechanisms through advanced DAO models to ensure fair compensation and transparency.

Some of the smart contracts have not been fully tested or fully integrated into the overall platform. With more time, we intend to build out comprehensive testing and seamless integration for these contracts. Additionally, we have collected an extensive amount of historical data and are currently working on training our own model to be used in the pricing predictor agent. These improvements will be integrated into the overall implementation to further enhance the accuracy and reliability of market predictions.