// Deploys MockUSDC + AgentVault to the selected network.
//   Local:   npx hardhat run scripts/deploy.js
//   Sepolia: npx hardhat run scripts/deploy.js --network sepolia
// Sepolia needs SEPOLIA_RPC_URL + DEPLOYER_PRIVATE_KEY in the local, git-ignored .env.
// If ETHERSCAN_API_KEY is set, the contracts are verified on Sepolia Etherscan afterwards.
const fs = require("fs");
const path = require("path");
const hre = require("hardhat");
const { ethers } = hre;
const { assertSafeNetwork, explorerTx, explorerAddr } = require("./lib");

async function main() {
  const chainId = await assertSafeNetwork();
  const signers = await ethers.getSigners();
  if (signers.length === 0) {
    throw new Error("No deployer account. Set DEPLOYER_PRIVATE_KEY in your local .env (never commit it).");
  }
  const deployer = signers[0];
  const bal = await ethers.provider.getBalance(deployer.address);
  console.log(`Network:  ${hre.network.name} (chainId ${chainId})`);
  console.log(`Deployer: ${deployer.address}  (balance ${ethers.formatEther(bal)} ETH)`);
  if (bal === 0n) throw new Error("Deployer has no ETH for gas.");

  const confirmations = chainId === 31337 ? 1 : 2;

  const token = await ethers.deployContract("MockUSDC", deployer);
  const tokenTx = token.deploymentTransaction();
  await tokenTx.wait(confirmations);
  const tokenAddr = await token.getAddress();
  console.log(`\nMockUSDC   ${tokenAddr}\n  tx: ${explorerTx(chainId, tokenTx.hash)}`);

  const vault = await ethers.deployContract("AgentVault", [tokenAddr], deployer);
  const vaultTx = vault.deploymentTransaction();
  await vaultTx.wait(confirmations);
  const vaultAddr = await vault.getAddress();
  console.log(`AgentVault ${vaultAddr}\n  tx: ${explorerTx(chainId, vaultTx.hash)}`);

  const record = {
    network: hre.network.name,
    chainId,
    deployer: deployer.address,
    deployedAt: new Date().toISOString(),
    compiler: { version: "0.8.28", optimizer: { enabled: true, runs: 200 }, evmVersion: "cancun" },
    MockUSDC: { address: tokenAddr, tx: tokenTx.hash, explorer: explorerAddr(chainId, tokenAddr) },
    AgentVault: {
      address: vaultAddr,
      tx: vaultTx.hash,
      constructorArgs: [tokenAddr],
      explorer: explorerAddr(chainId, vaultAddr),
    },
  };
  if (chainId !== 31337) {
    const dir = path.join(__dirname, "..", "deployments");
    fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(path.join(dir, `${hre.network.name}.json`), JSON.stringify(record, null, 2) + "\n");
    console.log(`\nSaved deployments/${hre.network.name}.json (public addresses only).`);
  }

  if (chainId === 11155111 && process.env.ETHERSCAN_API_KEY) {
    console.log("\nVerifying on Sepolia Etherscan (waiting a few blocks first)...");
    await vaultTx.wait(5);
    for (const [address, args] of [
      [tokenAddr, []],
      [vaultAddr, [tokenAddr]],
    ]) {
      try {
        await hre.run("verify:verify", { address, constructorArguments: args });
      } catch (e) {
        console.log(`  verify ${address}: ${e.message.split("\n")[0]}`);
      }
    }
  }

  console.log("\nNext: put these in .env to run the demo against them:");
  console.log(`  TOKEN_ADDRESS=${tokenAddr}\n  VAULT_ADDRESS=${vaultAddr}`);
}

main().catch((e) => {
  console.error(e.message || e);
  process.exitCode = 1;
});
