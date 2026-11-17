require("@nomicfoundation/hardhat-toolbox");
require("dotenv").config();

// All secrets come from the local, git-ignored .env file. Nothing is hardcoded.
const { SEPOLIA_RPC_URL, DEPLOYER_PRIVATE_KEY, AGENT_PRIVATE_KEY, ETHERSCAN_API_KEY } = process.env;

const isHexKey = (k) => typeof k === "string" && /^(0x)?[0-9a-fA-F]{64}$/.test(k.trim());
const sepoliaAccounts = [DEPLOYER_PRIVATE_KEY, AGENT_PRIVATE_KEY].filter(isHexKey).map((k) => k.trim());

/** @type import('hardhat/config').HardhatUserConfig */
module.exports = {
  // Keep these settings identical to the Remix deploy + Etherscan verification.
  solidity: {
    version: "0.8.28",
    settings: {
      optimizer: { enabled: true, runs: 200 },
      evmVersion: "cancun",
    },
  },
  networks: {
    hardhat: {},
    ...(SEPOLIA_RPC_URL
      ? {
          sepolia: {
            url: SEPOLIA_RPC_URL,
            chainId: 11155111,
            accounts: sepoliaAccounts,
          },
        }
      : {}),
  },
  etherscan: {
    // Etherscan API v2 uses a single key for all chains.
    apiKey: ETHERSCAN_API_KEY || "",
  },
  sourcify: { enabled: false },
  gasReporter: { enabled: process.env.REPORT_GAS === "true" },
};
