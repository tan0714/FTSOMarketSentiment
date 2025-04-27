// scripts/query.js
const fs = require("fs");
const path = require("path");
const hre = require("hardhat");

async function main() {
  const consumerAddress = "0x431ac67aCC345d42F27e2119aC92B4f6dAd69Ed4";
  const consumer = await hre.ethers.getContractAt(
    "FTSOConsumer",
    consumerAddress
  );

  // Fetch current snapshot
  const [indices, symbols, prices, decimals, timestamps] =
    await consumer.fetchAllFeeds();

  // Build row objects
  const rows = indices.map((idx, i) => ({
    index:     Number(idx),
    symbol:    symbols[i],
    price:     prices[i].toString(),
    decimals:  Number(decimals[i]),
    timestamp: new Date(Number(timestamps[i]) * 1000).toISOString()
  }));

  // Prepare CSV file path
  const csvPath = path.resolve(__dirname, "feeds-snapshot.csv");
  const fileExists = fs.existsSync(csvPath);

  // Build CSV header and rows
  const header = "index,symbol,price,decimals,timestamp\n";
  const csvRows = rows
    .map(r => `${r.index},${r.symbol},${r.price},${r.decimals},${r.timestamp}`)
    .join("\n") + "\n";

  // Write or append to CSV
  if (!fileExists) {
    fs.writeFileSync(csvPath, header + csvRows, "utf-8");
    console.log(`Created ${csvPath} with header and ${rows.length} rows.`);
  } else {
    fs.appendFileSync(csvPath, csvRows, "utf-8");
    console.log(`Appended ${rows.length} rows to ${csvPath}.`);
  }
}

main()
  .catch(err => {
    console.error(err);
    process.exit(1);
  });
