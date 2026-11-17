// End-to-end AgentVault demo: owner funds a vault and sets an agent policy; the AGENT then tries
// four payments and the contract enforces the policy.
//   Local:   npx hardhat run scripts/demo.js
//   Sepolia: npx hardhat run scripts/demo.js --network sepolia
//            (needs DEPLOYER_PRIVATE_KEY = owner and AGENT_PRIVATE_KEY = throwaway agent in .env;
//             optional TOKEN_ADDRESS / VAULT_ADDRESS to attach instead of deploying fresh contracts)
const hre = require("hardhat");
const { ethers } = hre;
const { assertSafeNetwork, explorerTx, explorerAddr, fmt, decodeError } = require("./lib");

const U = (n) => ethers.parseUnits(String(n), 6);
const POLICY = { perTx: U(100), daily: U(250), threshold: U(50), days: 7 };
const STATUS = ["Pending", "Executed", "Rejected"];

let chainId;
const tally = { executed: 0, rejected: 0, approved: 0 };
const line = (s = "") => console.log(s);
const hr = () => line("-".repeat(72));

async function send(label, txPromise) {
  const tx = await txPromise;
  const rc = await tx.wait();
  line(`  ✓ ${label}`);
  line(`      tx ${explorerTx(chainId, tx.hash)}  (gas used ${rc.gasUsed})`);
  return rc;
}

async function main() {
  chainId = await assertSafeNetwork();
  const signers = await ethers.getSigners();
  if (signers.length < 2) {
    throw new Error("Need two accounts: DEPLOYER_PRIVATE_KEY (owner) and AGENT_PRIVATE_KEY (agent) in .env.");
  }
  const [owner, agent] = signers;
  const isLocal = chainId === 31337;
  // Payee and "stranger" only receive tokens; they never sign, so random addresses are fine.
  const payee = process.env.PAYEE_ADDRESS && !isLocal ? process.env.PAYEE_ADDRESS : (signers[2]?.address ?? ethers.Wallet.createRandom().address);
  const stranger = ethers.Wallet.createRandom().address;

  line("=".repeat(72));
  line(" AgentVault demo - on-chain spending policy for an AI agent");
  line("=".repeat(72));
  line(`Network : ${hre.network.name} (chainId ${chainId})`);
  line(`Owner   : ${owner.address}  (human)`);
  line(`Agent   : ${agent.address}  (AI agent hot key)`);
  line(`Payee   : ${payee}  (allowlisted service)`);
  line(`Stranger: ${stranger}  (NOT allowlisted)`);
  if (!isLocal) {
    const agentEth = await ethers.provider.getBalance(agent.address);
    line(`Agent ETH balance for gas: ${ethers.formatEther(agentEth)} ETH`);
    if (agentEth === 0n) throw new Error("Agent account has no Sepolia ETH for gas.");
  }

  // ---------------------------------------------------------------- setup
  hr();
  line("SETUP (owner)");
  let token, vault;
  if (process.env.TOKEN_ADDRESS && process.env.VAULT_ADDRESS && !isLocal) {
    token = await ethers.getContractAt("MockUSDC", process.env.TOKEN_ADDRESS, owner);
    vault = await ethers.getContractAt("AgentVault", process.env.VAULT_ADDRESS, owner);
    line(`  attached to MockUSDC ${await token.getAddress()}`);
    line(`  attached to AgentVault ${await vault.getAddress()}`);
    if ((await vault.owner()) !== owner.address) throw new Error("DEPLOYER account is not the vault owner.");
    if ((await vault.token()) !== (await token.getAddress())) throw new Error("Vault token != TOKEN_ADDRESS.");
  } else {
    token = await ethers.deployContract("MockUSDC", owner);
    await token.waitForDeployment();
    vault = await ethers.deployContract("AgentVault", [await token.getAddress()], owner);
    await vault.waitForDeployment();
    line(`  ✓ deployed MockUSDC   ${await token.getAddress()}`);
    line(`  ✓ deployed AgentVault ${await vault.getAddress()}`);
  }
  const vaultAddr = await vault.getAddress();

  const funding = U(1000);
  if ((await token.balanceOf(owner.address)) < funding) {
    await send(`mint ${fmt(funding)} test tokens to owner (TEST TOKEN, NO VALUE)`, token.mint(owner.address, funding));
  }
  if ((await token.allowance(owner.address, vaultAddr)) < funding) {
    await send(`approve vault to pull ${fmt(funding)}`, token.approve(vaultAddr, funding));
  }
  await send(`deposit ${fmt(funding)} into vault`, vault.deposit(funding));

  const latest = await ethers.provider.getBlock("latest");
  const expiry = latest.timestamp + POLICY.days * 24 * 3600;
  await send(
    `setAgentPolicy(perTx ${fmt(POLICY.perTx)}, daily ${fmt(POLICY.daily)}, approval > ${fmt(POLICY.threshold)}, expires in ${POLICY.days} days)`,
    vault.setAgentPolicy(agent.address, POLICY.perTx, POLICY.daily, POLICY.threshold, expiry)
  );
  await send(`setPayee(agent, payee, true)`, vault.setPayee(agent.address, payee, true));

  const balances = async (title) => {
    line(`  [${title}] vault ${fmt(await token.balanceOf(vaultAddr))} | payee ${fmt(await token.balanceOf(payee))} | stranger ${fmt(await token.balanceOf(stranger))} | agent window left ${fmt(await vault.remainingInWindow(agent.address))}`);
  };
  hr();
  await balances("before");

  const asAgent = vault.connect(agent);
  const iface = vault.interface;

  // Expected-to-fail attempts are simulated with staticCall first, so no gas is wasted on Sepolia
  // and the custom error is decoded from the revert data.
  async function attemptRejected(label, to, amount, memo) {
    line(`\n${label}`);
    try {
      await asAgent.pay.staticCall(to, amount, memo);
      line("  ✗ UNEXPECTED: call would succeed");
      process.exitCode = 1;
    } catch (e) {
      tally.rejected++;
      line(`  ✓ rejected by contract: ${decodeError(e, iface)}`);
    }
  }

  // (1) small allowed payment
  line(`\n(1) Agent pays ${fmt(U(20))} to the allowlisted payee (<= threshold, auto-executes)`);
  const rc1 = await send("pay() mined", asAgent.pay(payee, U(20), "API credits for weather data"));
  const ev1 = rc1.logs.map((l) => { try { return iface.parseLog(l); } catch { return null; } }).find((e) => e && e.name === "PaymentExecuted");
  tally.executed++;
  line(`      event PaymentExecuted(id=${ev1.args.id}, amount=${fmt(ev1.args.amount)}, memo="${ev1.args.memo}")`);

  // (2) non-allowlisted payee
  await attemptRejected(`(2) Agent tries to pay ${fmt(U(10))} to a NON-allowlisted address`, stranger, U(10), "send to attacker");

  // (3) over per-tx limit
  await attemptRejected(`(3) Agent tries to pay ${fmt(U(150))} (> perTx limit ${fmt(POLICY.perTx)})`, payee, U(150), "too big");

  // (4) over threshold -> pending -> owner approves
  line(`\n(4) Agent requests ${fmt(U(80))} (> approval threshold ${fmt(POLICY.threshold)})`);
  const rc4 = await send("pay() mined", asAgent.pay(payee, U(80), "GPU rental, 2 hours"));
  const ev4 = rc4.logs.map((l) => { try { return iface.parseLog(l); } catch { return null; } }).find((e) => e && e.name === "PaymentRequested");
  const id = ev4.args.id;
  line(`      event PaymentRequested(id=${id}) -> status ${STATUS[Number((await vault.requests(id)).status)]}, nothing transferred yet`);
  await balances("while pending");
  line(`    Human owner reviews request #${id} and approves it (policy is re-checked on-chain)`);
  await send(`approveRequest(${id})`, vault.approveRequest(id));
  tally.executed++;
  tally.approved++;
  line(`      request #${id} status -> ${STATUS[Number((await vault.requests(id)).status)]}`);

  hr();
  await balances("after");
  line(`  requests stored on-chain: ${await vault.requestCount()}`);
  if (!isLocal) {
    line(`\nVault on Etherscan: ${explorerAddr(chainId, vaultAddr)}`);
  }
  line("=".repeat(72));
  line(` Demo finished: ${tally.executed} payments executed, ${tally.rejected} rejected by policy, ${tally.approved} needed human approval.`);
  line("=".repeat(72));
}

main().catch((e) => {
  console.error(e.message || e);
  process.exitCode = 1;
});
