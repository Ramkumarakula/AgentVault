// Shared helpers for deploy.js and demo.js. No secrets are read or printed here.
const { ethers, network } = require("hardhat");

const ALLOWED_CHAINS = { 31337: "hardhat", 11155111: "sepolia" };

async function assertSafeNetwork() {
  const { chainId } = await ethers.provider.getNetwork();
  const id = Number(chainId);
  if (!ALLOWED_CHAINS[id]) {
    throw new Error(`Refusing to run on chainId ${id}. This project is for local Hardhat or Sepolia testnet only.`);
  }
  return id;
}

function explorerTx(chainId, hash) {
  return chainId === 11155111 ? `https://sepolia.etherscan.io/tx/${hash}` : `(local tx ${hash})`;
}

function explorerAddr(chainId, addr) {
  return chainId === 11155111 ? `https://sepolia.etherscan.io/address/${addr}` : `(local ${addr})`;
}

const fmt = (amount) => `${ethers.formatUnits(amount, 6)} mUSDC`;

/** Best-effort decode of a custom error from an ethers v6 error. */
function decodeError(err, iface) {
  if (err && err.revert && err.revert.name) {
    return `${err.revert.name}(${err.revert.args.map(String).join(", ")})`;
  }
  const data = err?.data ?? err?.error?.data ?? err?.info?.error?.data;
  if (typeof data === "string" && data.startsWith("0x")) {
    try {
      const parsed = iface.parseError(data);
      if (parsed) return `${parsed.name}(${parsed.args.map(String).join(", ")})`;
    } catch (_) {
      /* fall through */
    }
  }
  return err?.shortMessage || err?.message || String(err);
}

module.exports = { network, assertSafeNetwork, explorerTx, explorerAddr, fmt, decodeError };
