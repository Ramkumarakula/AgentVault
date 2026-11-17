const { expect } = require("chai");
const { ethers } = require("hardhat");
const { loadFixture, time } = require("@nomicfoundation/hardhat-network-helpers");

const U = (n) => ethers.parseUnits(String(n), 6); // mUSDC has 6 decimals
const DAY = 24 * 60 * 60;
const Status = { Pending: 0n, Executed: 1n, Rejected: 2n };

// Default policy used by most tests: perTx 100, daily 250, threshold 50, expiry +30 days.
const PER_TX = U(100);
const DAILY = U(250);
const THRESHOLD = U(50);

async function deployFixture() {
  const [owner, agent, payee, other, agent2] = await ethers.getSigners();
  const token = await ethers.deployContract("MockUSDC");
  const vault = await ethers.deployContract("AgentVault", [await token.getAddress()]);
  await token.mint(owner.address, U(1_000_000));
  await token.approve(await vault.getAddress(), ethers.MaxUint256);
  await vault.deposit(U(10_000));
  return { token, vault, owner, agent, payee, other, agent2 };
}

async function configuredFixture() {
  const f = await deployFixture();
  const expiry = (await time.latest()) + 30 * DAY;
  await f.vault.setAgentPolicy(f.agent.address, PER_TX, DAILY, THRESHOLD, expiry);
  await f.vault.setPayee(f.agent.address, f.payee.address, true);
  return { ...f, expiry };
}

describe("MockUSDC", function () {
  it("has name, symbol and 6 decimals", async function () {
    const { token } = await loadFixture(deployFixture);
    expect(await token.name()).to.equal("Mock USDC");
    expect(await token.symbol()).to.equal("mUSDC");
    expect(await token.decimals()).to.equal(6n);
  });

  it("only the owner can mint", async function () {
    const { token, other } = await loadFixture(deployFixture);
    await expect(token.connect(other).mint(other.address, 1n))
      .to.be.revertedWithCustomError(token, "OwnableUnauthorizedAccount")
      .withArgs(other.address);
  });
});

describe("AgentVault", function () {
  describe("deployment", function () {
    it("sets token and owner", async function () {
      const { token, vault, owner } = await loadFixture(deployFixture);
      expect(await vault.token()).to.equal(await token.getAddress());
      expect(await vault.owner()).to.equal(owner.address);
      expect(await vault.MAX_MEMO_LENGTH()).to.equal(140n);
      expect(await vault.WINDOW_DURATION()).to.equal(BigInt(DAY));
      expect(await vault.requestCount()).to.equal(0n);
    });

    it("rejects the zero token address", async function () {
      const Vault = await ethers.getContractFactory("AgentVault");
      await expect(Vault.deploy(ethers.ZeroAddress)).to.be.revertedWithCustomError(Vault, "ZeroAddress");
    });

    it("renounceOwnership is disabled (would lock funds)", async function () {
      const { vault, other } = await loadFixture(deployFixture);
      await expect(vault.renounceOwnership()).to.be.revertedWithCustomError(vault, "RenounceDisabled");
      await expect(vault.connect(other).renounceOwnership()).to.be.revertedWithCustomError(
        vault,
        "OwnableUnauthorizedAccount"
      );
    });
  });

  describe("deposit", function () {
    it("anyone can deposit; emits Deposited and moves tokens", async function () {
      const { token, vault, owner, other } = await loadFixture(deployFixture);
      await token.mint(other.address, U(500));
      await token.connect(other).approve(await vault.getAddress(), U(500));
      const tx = await vault.connect(other).deposit(U(500));
      await expect(tx)
        .to.emit(vault, "Deposited")
        .withArgs(other.address, U(500));
      await expect(tx).to.changeTokenBalances(token, [other, vault], [-U(500), U(500)]);
      expect(await token.balanceOf(await vault.getAddress())).to.equal(U(10_500));
      void owner;
    });

    it("rejects zero amount", async function () {
      const { vault } = await loadFixture(deployFixture);
      await expect(vault.deposit(0)).to.be.revertedWithCustomError(vault, "ZeroAmount");
    });

    it("reverts without allowance", async function () {
      const { token, vault, other } = await loadFixture(deployFixture);
      await token.mint(other.address, U(1));
      await expect(vault.connect(other).deposit(U(1))).to.be.revertedWithCustomError(
        token,
        "ERC20InsufficientAllowance"
      );
    });
  });

  describe("withdraw", function () {
    it("owner can withdraw; emits Withdrawn", async function () {
      const { token, vault, other } = await loadFixture(deployFixture);
      const tx = await vault.withdraw(other.address, U(1_000));
      await expect(tx)
        .to.emit(vault, "Withdrawn")
        .withArgs(other.address, U(1_000));
      await expect(tx).to.changeTokenBalances(token, [vault, other], [-U(1_000), U(1_000)]);
    });

    it("non-owner cannot withdraw", async function () {
      const { vault, other } = await loadFixture(deployFixture);
      await expect(vault.connect(other).withdraw(other.address, 1n))
        .to.be.revertedWithCustomError(vault, "OwnableUnauthorizedAccount")
        .withArgs(other.address);
    });

    it("validates recipient, amount and balance", async function () {
      const { vault, other } = await loadFixture(deployFixture);
      await expect(vault.withdraw(ethers.ZeroAddress, 1n)).to.be.revertedWithCustomError(vault, "ZeroAddress");
      await expect(vault.withdraw(other.address, 0)).to.be.revertedWithCustomError(vault, "ZeroAmount");
      await expect(vault.withdraw(other.address, U(10_001)))
        .to.be.revertedWithCustomError(vault, "InsufficientVaultBalance")
        .withArgs(U(10_000), U(10_001));
    });

    it("still works while paused (owner rescue)", async function () {
      const { vault, other } = await loadFixture(deployFixture);
      await vault.pause();
      await expect(vault.withdraw(other.address, U(1))).to.emit(vault, "Withdrawn");
    });
  });

  describe("setAgentPolicy", function () {
    it("stores the policy and emits AgentPolicySet", async function () {
      const { vault, agent } = await loadFixture(deployFixture);
      const expiry = (await time.latest()) + DAY;
      await expect(vault.setAgentPolicy(agent.address, PER_TX, DAILY, THRESHOLD, expiry))
        .to.emit(vault, "AgentPolicySet")
        .withArgs(agent.address, PER_TX, DAILY, THRESHOLD, expiry);
      const p = await vault.policies(agent.address);
      expect(p.active).to.equal(true);
      expect(p.perTxLimit).to.equal(PER_TX);
      expect(p.dailyLimit).to.equal(DAILY);
      expect(p.approvalThreshold).to.equal(THRESHOLD);
      expect(p.expiry).to.equal(BigInt(expiry));
      expect(p.spentInWindow).to.equal(0n);
      expect(p.windowStart).to.equal(BigInt(await time.latest()));
    });

    it("rejects zero agent", async function () {
      const { vault } = await loadFixture(deployFixture);
      const expiry = (await time.latest()) + DAY;
      await expect(
        vault.setAgentPolicy(ethers.ZeroAddress, PER_TX, DAILY, THRESHOLD, expiry)
      ).to.be.revertedWithCustomError(vault, "ZeroAddress");
    });

    it("rejects threshold > perTx, perTx > daily, perTx == 0", async function () {
      const { vault, agent } = await loadFixture(deployFixture);
      const expiry = (await time.latest()) + DAY;
      await expect(vault.setAgentPolicy(agent.address, U(10), U(100), U(11), expiry))
        .to.be.revertedWithCustomError(vault, "InvalidLimits")
        .withArgs(U(11), U(10), U(100));
      await expect(vault.setAgentPolicy(agent.address, U(101), U(100), U(1), expiry))
        .to.be.revertedWithCustomError(vault, "InvalidLimits")
        .withArgs(U(1), U(101), U(100));
      await expect(vault.setAgentPolicy(agent.address, 0, U(100), 0, expiry)).to.be.revertedWithCustomError(
        vault,
        "InvalidLimits"
      );
    });

    it("accepts equal limits (threshold == perTx == daily)", async function () {
      const { vault, agent } = await loadFixture(deployFixture);
      const expiry = (await time.latest()) + DAY;
      await expect(vault.setAgentPolicy(agent.address, U(5), U(5), U(5), expiry)).to.emit(vault, "AgentPolicySet");
    });

    it("rejects expiry in the past or now", async function () {
      const { vault, agent } = await loadFixture(deployFixture);
      const now = await time.latest();
      await expect(vault.setAgentPolicy(agent.address, PER_TX, DAILY, THRESHOLD, now)).to.be.revertedWithCustomError(
        vault,
        "ExpiryNotInFuture"
      );
    });

    it("non-owner cannot set a policy", async function () {
      const { vault, agent, other } = await loadFixture(deployFixture);
      const expiry = (await time.latest()) + DAY;
      await expect(
        vault.connect(other).setAgentPolicy(agent.address, PER_TX, DAILY, THRESHOLD, expiry)
      ).to.be.revertedWithCustomError(vault, "OwnableUnauthorizedAccount");
    });

    it("updating a policy keeps current window usage (no free reset)", async function () {
      const { vault, agent, payee, expiry } = await loadFixture(configuredFixture);
      await vault.connect(agent).pay(payee.address, U(40), "a");
      await vault.setAgentPolicy(agent.address, PER_TX, DAILY, THRESHOLD, expiry + DAY);
      expect((await vault.policies(agent.address)).spentInWindow).to.equal(U(40));
    });

    it("lowering dailyLimit below spent blocks further spending (no underflow)", async function () {
      const { vault, agent, payee, expiry } = await loadFixture(configuredFixture);
      await vault.connect(agent).pay(payee.address, U(50), "a");
      await vault.connect(agent).pay(payee.address, U(50), "b");
      await vault.setAgentPolicy(agent.address, U(20), U(30), U(10), expiry);
      expect(await vault.remainingInWindow(agent.address)).to.equal(0n);
      await expect(vault.connect(agent).pay(payee.address, U(1), "c"))
        .to.be.revertedWithCustomError(vault, "ExceedsDailyLimit")
        .withArgs(U(1), 0n);
    });
  });

  describe("payee allowlist", function () {
    it("setPayee emits PayeeSet and toggles the mapping", async function () {
      const { vault, agent, other } = await loadFixture(configuredFixture);
      await expect(vault.setPayee(agent.address, other.address, true))
        .to.emit(vault, "PayeeSet")
        .withArgs(agent.address, other.address, true);
      expect(await vault.isPayeeAllowed(agent.address, other.address)).to.equal(true);
      await vault.setPayee(agent.address, other.address, false);
      expect(await vault.isPayeeAllowed(agent.address, other.address)).to.equal(false);
    });

    it("rejects zero agent, zero payee and the vault itself", async function () {
      const { vault, agent, other } = await loadFixture(configuredFixture);
      await expect(vault.setPayee(ethers.ZeroAddress, other.address, true)).to.be.revertedWithCustomError(
        vault,
        "ZeroAddress"
      );
      await expect(vault.setPayee(agent.address, ethers.ZeroAddress, true)).to.be.revertedWithCustomError(
        vault,
        "InvalidPayee"
      );
      await expect(vault.setPayee(agent.address, await vault.getAddress(), true))
        .to.be.revertedWithCustomError(vault, "InvalidPayee")
        .withArgs(await vault.getAddress());
    });

    it("non-owner cannot set payees", async function () {
      const { vault, agent, other } = await loadFixture(configuredFixture);
      await expect(vault.connect(agent).setPayee(agent.address, other.address, true)).to.be.revertedWithCustomError(
        vault,
        "OwnableUnauthorizedAccount"
      );
    });

    it("pay to a non-allowlisted address reverts", async function () {
      const { vault, agent, other } = await loadFixture(configuredFixture);
      await expect(vault.connect(agent).pay(other.address, U(1), "x"))
        .to.be.revertedWithCustomError(vault, "PayeeNotAllowed")
        .withArgs(agent.address, other.address);
    });

    it("allowlists are per agent", async function () {
      const { vault, agent2, payee } = await loadFixture(configuredFixture);
      const expiry = (await time.latest()) + DAY;
      await vault.setAgentPolicy(agent2.address, PER_TX, DAILY, THRESHOLD, expiry);
      await expect(vault.connect(agent2).pay(payee.address, U(1), "x")).to.be.revertedWithCustomError(
        vault,
        "PayeeNotAllowed"
      );
    });
  });

  describe("pay: under threshold (auto-execute)", function () {
    it("executes immediately, records request, emits PaymentExecuted", async function () {
      const { token, vault, agent, payee } = await loadFixture(configuredFixture);
      const tx = await vault.connect(agent).pay(payee.address, U(50), "api call #1");
      await expect(tx)
        .to.emit(vault, "PaymentExecuted")
        .withArgs(0n, agent.address, payee.address, U(50), "api call #1");
      await expect(tx).to.changeTokenBalances(token, [vault, payee], [-U(50), U(50)]);
      const r = await vault.requests(0);
      expect(r.agent).to.equal(agent.address);
      expect(r.to).to.equal(payee.address);
      expect(r.amount).to.equal(U(50));
      expect(r.status).to.equal(Status.Executed);
      expect(r.memo).to.equal("api call #1");
      expect(r.createdAt).to.equal(BigInt(await time.latest()));
      expect((await vault.policies(agent.address)).spentInWindow).to.equal(U(50));
      expect(await vault.remainingInWindow(agent.address)).to.equal(DAILY - U(50));
    });

    it("returns the request id (static call)", async function () {
      const { vault, agent, payee } = await loadFixture(configuredFixture);
      expect(await vault.connect(agent).pay.staticCall(payee.address, U(1), "")).to.equal(0n);
      await vault.connect(agent).pay(payee.address, U(1), "");
      expect(await vault.connect(agent).pay.staticCall(payee.address, U(1), "")).to.equal(1n);
    });

    it("rejects zero amount and too-long memo; accepts exactly 140 bytes", async function () {
      const { vault, agent, payee } = await loadFixture(configuredFixture);
      await expect(vault.connect(agent).pay(payee.address, 0, "")).to.be.revertedWithCustomError(vault, "ZeroAmount");
      await expect(vault.connect(agent).pay(payee.address, U(1), "a".repeat(141)))
        .to.be.revertedWithCustomError(vault, "MemoTooLong")
        .withArgs(141n, 140n);
      await expect(vault.connect(agent).pay(payee.address, U(1), "a".repeat(140))).to.emit(vault, "PaymentExecuted");
    });

    it("reverts when the vault balance is insufficient", async function () {
      const { vault, agent, payee, other } = await loadFixture(configuredFixture);
      await vault.withdraw(other.address, U(10_000) - U(10));
      await expect(vault.connect(agent).pay(payee.address, U(20), "x"))
        .to.be.revertedWithCustomError(vault, "InsufficientVaultBalance")
        .withArgs(U(10), U(20));
    });
  });

  describe("pay: limits", function () {
    it("per-transaction limit", async function () {
      const { vault, agent, payee } = await loadFixture(configuredFixture);
      await expect(vault.connect(agent).pay(payee.address, PER_TX + 1n, "x"))
        .to.be.revertedWithCustomError(vault, "ExceedsPerTxLimit")
        .withArgs(PER_TX + 1n, PER_TX);
    });

    it("huge amounts (> uint128) revert cleanly with ExceedsPerTxLimit", async function () {
      const { vault, agent, payee } = await loadFixture(configuredFixture);
      await expect(vault.connect(agent).pay(payee.address, ethers.MaxUint256, "x")).to.be.revertedWithCustomError(
        vault,
        "ExceedsPerTxLimit"
      );
    });

    it("daily limit", async function () {
      const { vault, agent, payee } = await loadFixture(configuredFixture);
      for (let i = 0; i < 5; i++) await vault.connect(agent).pay(payee.address, U(50), "x"); // 250 = daily
      await expect(vault.connect(agent).pay(payee.address, 1n, "x"))
        .to.be.revertedWithCustomError(vault, "ExceedsDailyLimit")
        .withArgs(1n, 0n);
    });

    it("window resets after 24h (time travel)", async function () {
      const { vault, agent, payee } = await loadFixture(configuredFixture);
      for (let i = 0; i < 5; i++) await vault.connect(agent).pay(payee.address, U(50), "x");
      const start = (await vault.policies(agent.address)).windowStart;
      // Just before the window ends it still reverts
      await time.increaseTo(start + BigInt(DAY) - 2n);
      await expect(vault.connect(agent).pay(payee.address, 1n, "x")).to.be.revertedWithCustomError(
        vault,
        "ExceedsDailyLimit"
      );
      await time.increaseTo(start + BigInt(DAY));
      expect(await vault.remainingInWindow(agent.address)).to.equal(DAILY);
      await expect(vault.connect(agent).pay(payee.address, U(50), "x")).to.emit(vault, "PaymentExecuted");
      const p = await vault.policies(agent.address);
      expect(p.spentInWindow).to.equal(U(50));
      expect(p.windowStart).to.equal(BigInt(await time.latest()));
    });
  });

  describe("expiry, revoke, pause", function () {
    it("agent cannot spend after expiry (time travel)", async function () {
      const { vault, agent, payee, expiry } = await loadFixture(configuredFixture);
      await time.setNextBlockTimestamp(expiry); // block.timestamp == expiry: still allowed
      await expect(vault.connect(agent).pay(payee.address, U(1), "x")).to.emit(vault, "PaymentExecuted");
      await expect(vault.connect(agent).pay(payee.address, U(1), "x"))
        .to.be.revertedWithCustomError(vault, "AgentExpired")
        .withArgs(agent.address, expiry);
      expect(await vault.remainingInWindow(agent.address)).to.equal(0n);
    });

    it("revoked agent cannot pay; revoke emits; double revoke reverts", async function () {
      const { vault, agent, payee } = await loadFixture(configuredFixture);
      await expect(vault.revokeAgent(agent.address)).to.emit(vault, "AgentRevoked").withArgs(agent.address);
      await expect(vault.connect(agent).pay(payee.address, U(1), "x"))
        .to.be.revertedWithCustomError(vault, "AgentNotActive")
        .withArgs(agent.address);
      await expect(vault.revokeAgent(agent.address)).to.be.revertedWithCustomError(vault, "AgentNotActive");
      expect(await vault.remainingInWindow(agent.address)).to.equal(0n);
    });

    it("non-owner cannot revoke", async function () {
      const { vault, agent } = await loadFixture(configuredFixture);
      await expect(vault.connect(agent).revokeAgent(agent.address)).to.be.revertedWithCustomError(
        vault,
        "OwnableUnauthorizedAccount"
      );
    });

    it("unknown address is not an agent", async function () {
      const { vault, other, payee } = await loadFixture(configuredFixture);
      await expect(vault.connect(other).pay(payee.address, U(1), "x"))
        .to.be.revertedWithCustomError(vault, "AgentNotActive")
        .withArgs(other.address);
    });

    it("pause blocks pay; unpause restores; only owner can pause", async function () {
      const { vault, agent, payee } = await loadFixture(configuredFixture);
      await expect(vault.connect(agent).pause()).to.be.revertedWithCustomError(vault, "OwnableUnauthorizedAccount");
      await vault.pause();
      await expect(vault.connect(agent).pay(payee.address, U(1), "x")).to.be.revertedWithCustomError(
        vault,
        "EnforcedPause"
      );
      await expect(vault.connect(agent).unpause()).to.be.revertedWithCustomError(vault, "OwnableUnauthorizedAccount");
      await vault.unpause();
      await expect(vault.connect(agent).pay(payee.address, U(1), "x")).to.emit(vault, "PaymentExecuted");
    });
  });

  describe("approval flow (human-in-the-loop)", function () {
    async function pendingFixture() {
      const f = await configuredFixture();
      await f.vault.connect(f.agent).pay(f.payee.address, U(80), "GPU rental");
      return f;
    }

    it("over threshold -> Pending, no transfer, emits PaymentRequested", async function () {
      const { token, vault, agent, payee } = await loadFixture(configuredFixture);
      const tx = await vault.connect(agent).pay(payee.address, U(80), "GPU rental");
      await expect(tx)
        .to.emit(vault, "PaymentRequested")
        .withArgs(0n, agent.address, payee.address, U(80), "GPU rental");
      await expect(tx).to.changeTokenBalances(token, [vault, payee], [0n, 0n]);
      expect((await vault.requests(0)).status).to.equal(Status.Pending);
      expect((await vault.policies(agent.address)).spentInWindow).to.equal(0n);
    });

    it("threshold boundary: amount == threshold executes immediately", async function () {
      const { vault, agent, payee } = await loadFixture(configuredFixture);
      await expect(vault.connect(agent).pay(payee.address, THRESHOLD, "x")).to.emit(vault, "PaymentExecuted");
      await expect(vault.connect(agent).pay(payee.address, THRESHOLD + 1n, "x")).to.emit(vault, "PaymentRequested");
    });

    it("owner approves -> Executed, tokens move, events emitted", async function () {
      const { token, vault, owner, agent, payee } = await loadFixture(pendingFixture);
      const tx = await vault.approveRequest(0);
      await expect(tx)
        .to.emit(vault, "PaymentApproved")
        .withArgs(0n, owner.address)
        .and.to.emit(vault, "PaymentExecuted")
        .withArgs(0n, agent.address, payee.address, U(80), "GPU rental");
      await expect(tx).to.changeTokenBalances(token, [vault, payee], [-U(80), U(80)]);
      expect((await vault.requests(0)).status).to.equal(Status.Executed);
      expect((await vault.policies(agent.address)).spentInWindow).to.equal(U(80));
    });

    it("cannot approve twice, approve a rejected one, or a missing id", async function () {
      const { vault } = await loadFixture(pendingFixture);
      await vault.approveRequest(0);
      await expect(vault.approveRequest(0))
        .to.be.revertedWithCustomError(vault, "RequestNotPending")
        .withArgs(0n, Status.Executed);
      await expect(vault.approveRequest(99)).to.be.revertedWithCustomError(vault, "RequestNotFound").withArgs(99n);
      await expect(vault.rejectRequest(99)).to.be.revertedWithCustomError(vault, "RequestNotFound");
    });

    it("owner rejects -> Rejected, no transfer; cannot approve after", async function () {
      const { token, vault, owner, payee } = await loadFixture(pendingFixture);
      const tx = await vault.rejectRequest(0);
      await expect(tx)
        .to.emit(vault, "PaymentRejected")
        .withArgs(0n, owner.address);
      await expect(tx).to.changeTokenBalance(token, payee, 0n);
      expect((await vault.requests(0)).status).to.equal(Status.Rejected);
      await expect(vault.approveRequest(0))
        .to.be.revertedWithCustomError(vault, "RequestNotPending")
        .withArgs(0n, Status.Rejected);
      await expect(vault.rejectRequest(0)).to.be.revertedWithCustomError(vault, "RequestNotPending");
    });

    it("only the owner can approve or reject", async function () {
      const { vault, agent, other } = await loadFixture(pendingFixture);
      await expect(vault.connect(agent).approveRequest(0)).to.be.revertedWithCustomError(
        vault,
        "OwnableUnauthorizedAccount"
      );
      await expect(vault.connect(other).rejectRequest(0)).to.be.revertedWithCustomError(
        vault,
        "OwnableUnauthorizedAccount"
      );
    });

    it("re-check at approval: agent revoked after request", async function () {
      const { vault, agent } = await loadFixture(pendingFixture);
      await vault.revokeAgent(agent.address);
      await expect(vault.approveRequest(0))
        .to.be.revertedWithCustomError(vault, "AgentNotActive")
        .withArgs(agent.address);
      await expect(vault.rejectRequest(0)).to.emit(vault, "PaymentRejected"); // owner can still clean up
    });

    it("re-check at approval: agent expired", async function () {
      const { vault, agent, expiry } = await loadFixture(pendingFixture);
      await time.increaseTo(expiry + 1);
      await expect(vault.approveRequest(0)).to.be.revertedWithCustomError(vault, "AgentExpired");
      void agent;
    });

    it("re-check at approval: payee removed from allowlist", async function () {
      const { vault, agent, payee } = await loadFixture(pendingFixture);
      await vault.setPayee(agent.address, payee.address, false);
      await expect(vault.approveRequest(0))
        .to.be.revertedWithCustomError(vault, "PayeeNotAllowed")
        .withArgs(agent.address, payee.address);
    });

    it("re-check at approval: perTxLimit lowered", async function () {
      const { vault, agent, expiry } = await loadFixture(pendingFixture);
      await vault.setAgentPolicy(agent.address, U(60), DAILY, U(10), expiry);
      await expect(vault.approveRequest(0))
        .to.be.revertedWithCustomError(vault, "ExceedsPerTxLimit")
        .withArgs(U(80), U(60));
    });

    it("re-check at approval: daily window already used up", async function () {
      const { vault, agent, payee } = await loadFixture(pendingFixture);
      for (let i = 0; i < 4; i++) await vault.connect(agent).pay(payee.address, U(50), "x"); // 200 spent
      await expect(vault.approveRequest(0))
        .to.be.revertedWithCustomError(vault, "ExceedsDailyLimit")
        .withArgs(U(80), U(50));
      // after the window resets, the same request can be approved
      await time.increase(DAY);
      await expect(vault.approveRequest(0)).to.emit(vault, "PaymentApproved");
    });

    it("re-check at approval: insufficient vault balance", async function () {
      const { vault, other } = await loadFixture(pendingFixture);
      await vault.withdraw(other.address, U(10_000));
      await expect(vault.approveRequest(0))
        .to.be.revertedWithCustomError(vault, "InsufficientVaultBalance")
        .withArgs(0n, U(80));
    });

    it("approve is blocked while paused; reject still works", async function () {
      const { vault } = await loadFixture(pendingFixture);
      await vault.pause();
      await expect(vault.approveRequest(0)).to.be.revertedWithCustomError(vault, "EnforcedPause");
      await expect(vault.rejectRequest(0)).to.emit(vault, "PaymentRejected");
    });
  });

  describe("reentrancy", function () {
    it("a malicious token re-entering pay() during transfer is blocked by nonReentrant", async function () {
      const [owner, payee] = await ethers.getSigners();
      const evil = await ethers.deployContract("ReentrantToken");
      const vault = await ethers.deployContract("AgentVault", [await evil.getAddress()]);
      const evilAddr = await evil.getAddress();
      await evil.approve(await vault.getAddress(), U(1000));
      await vault.deposit(U(1000));
      const expiry = (await time.latest()) + DAY;
      // The token contract itself is an agent (so its callback passes the agent checks).
      await vault.setAgentPolicy(evilAddr, PER_TX, DAILY, THRESHOLD, expiry);
      await vault.setAgentPolicy(owner.address, PER_TX, DAILY, THRESHOLD, expiry);
      await vault.setPayee(evilAddr, payee.address, true);
      await vault.setPayee(owner.address, payee.address, true);
      await evil.arm(await vault.getAddress(), payee.address);
      await expect(vault.pay(payee.address, U(1), "outer")).to.be.revertedWithCustomError(
        vault,
        "ReentrancyGuardReentrantCall"
      );
      // Same for withdraw
      await evil.arm(await vault.getAddress(), payee.address);
      await expect(vault.withdraw(payee.address, U(1))).to.be.revertedWithCustomError(
        vault,
        "ReentrancyGuardReentrantCall"
      );
    });
  });

  describe("property-style: random amounts never exceed dailyLimit per window", function () {
    it("300 random payments/approvals across random time jumps", async function () {
      this.timeout(300_000);
      const { token, vault, agent, payee } = await loadFixture(configuredFixture);
      // Deterministic PRNG (mulberry32) so a failure is reproducible.
      let seed = 0xa6e17;
      const rand = () => {
        seed |= 0;
        seed = (seed + 0x6d2b79f5) | 0;
        let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
        t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
        return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
      };

      let windowStart = (await vault.policies(agent.address)).windowStart;
      let executedInWindow = 0n;
      let executedTotal = 0n;
      let maxSeen = 0n;
      let reverts = 0;
      const payeeStart = await token.balanceOf(payee.address);

      for (let i = 0; i < 300; i++) {
        // occasionally jump time forward 1 min .. 30 h
        if (rand() < 0.15) await time.increase(60 + Math.floor(rand() * 30 * 3600));
        // amounts from 1 base unit to 120 mUSDC (some above perTx 100)
        const amount = BigInt(1 + Math.floor(rand() * Number(U(120))));
        try {
          const tx = await vault.connect(agent).pay(payee.address, amount, "fuzz");
          const rc = await tx.wait();
          const ev = rc.logs.map((l) => vault.interface.parseLog(l)).find((e) => e && e.name.startsWith("Payment"));
          if (ev.name === "PaymentRequested" && rand() < 0.7) {
            try {
              await vault.approveRequest(ev.args.id);
            } catch (e) {
              expect(e.message).to.match(/ExceedsDailyLimit/);
              reverts++;
            }
          }
        } catch (e) {
          expect(e.message).to.match(/ExceedsPerTxLimit|ExceedsDailyLimit/);
          reverts++;
        }
        // Invariant check against on-chain state
        const p = await vault.policies(agent.address);
        if (p.windowStart !== windowStart) {
          windowStart = p.windowStart;
          executedInWindow = 0n;
        }
        executedInWindow = p.spentInWindow;
        expect(p.spentInWindow).to.be.lte(DAILY);
        if (executedInWindow > maxSeen) maxSeen = executedInWindow;
      }

      // Cross-check: sum of Executed requests equals tokens received by the payee.
      const n = await vault.requestCount();
      for (let id = 0n; id < n; id++) {
        const r = await vault.requests(id);
        expect(r.amount).to.be.lte(PER_TX);
        if (r.status === Status.Executed) executedTotal += r.amount;
      }
      expect((await token.balanceOf(payee.address)) - payeeStart).to.equal(executedTotal);

      // Independent per-window check from events: group executions by window start.
      const evs = await vault.queryFilter(vault.filters.PaymentExecuted());
      const blocks = await Promise.all(evs.map((e) => e.getBlock()));
      let wStart = null;
      let wSum = 0n;
      const policyStart = Number((await vault.queryFilter(vault.filters.AgentPolicySet()))[0].blockNumber);
      wStart = (await ethers.provider.getBlock(policyStart)).timestamp;
      for (let k = 0; k < evs.length; k++) {
        const ts = blocks[k].timestamp;
        if (ts >= wStart + DAY) {
          wStart = ts;
          wSum = 0n;
        }
        wSum += evs[k].args.amount;
        expect(wSum).to.be.lte(DAILY);
      }
      expect(maxSeen).to.be.lte(DAILY);
      expect(reverts).to.be.greaterThan(0); // the limits were actually exercised
    });
  });
});
