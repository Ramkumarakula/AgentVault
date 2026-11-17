# Security notes

> AgentVault is a student project for a course. It has **not been audited**, is **not production-ready**
> and must only be used on testnets. This document lists what was checked and, more importantly, what was not.

## 1. What was checked

### Unit + property tests (Hardhat, chai, network helpers)
`npx hardhat test` -> **53 passing** (full output in `report/test_output.txt`). Covered:
constructor checks, deposit, withdraw (owner only, works while paused), setAgentPolicy validation, payee
allowlist (per agent, zero / vault address rejected), per-tx limit (incl. amounts > uint128), daily limit,
window reset after 24h (time travel), expiry boundary (`== expiry` allowed, `> expiry` rejected),
revoke, pause/unpause, auto-execute under threshold, threshold boundary, pending -> approve -> executed,
reject, approval re-checks (revoked, expired, payee removed, perTx lowered, window used up, balance),
access control on every owner function, event arguments, insufficient balance, lowering dailyLimit below
already-spent (no underflow), a malicious token re-entering `pay()` during `pay()` and `withdraw()`, and a
seeded random test of 300 payments/approvals with random time jumps that checks, from on-chain state *and*
by replaying events, that the executed total per window never exceeds `dailyLimit`.

### Coverage (`npx hardhat coverage`, solidity-coverage 0.8.17)

| File | Stmts | Branch | Funcs | Lines |
|---|---|---|---|---|
| AgentVault.sol | 100 % | 96.81 % | 100 % | 100 % |
| MockUSDC.sol | 100 % | 100 % | 100 % | 100 % |
| **All** | **100 %** | **96.88 %** | **100 %** | **100 %** |

The 3 uncovered branches are the "already entered" branch of `nonReentrant` on `deposit`, `withdraw` and
`approveRequest` (the reentrancy test re-enters `pay()` only). `contracts/test/ReentrantToken.sol` is a
test-only helper and is excluded from coverage via `.solcover.js`. Coverage measures executed code, not correctness.

### Static analysis - Slither 0.9.3
`slither . --filter-paths "node_modules|contracts/test"` -> 85 detectors, **8 results** (raw output in
`report/slither_output.txt`):

| Finding | Count | Assessment |
|---|---|---|
| `timestamp` - uses `block.timestamp` for comparisons (`setAgentPolicy`, `remainingInWindow`, `_checkAgent`, `_consumeWindow`, `_pendingRequest`) | 5 | Intended: expiry and the 24h window are time-based. Validators can shift timestamps only by seconds, negligible against a 24h window. The `_pendingRequest` hit (`id >= requests.length`) is a false positive - it isn't a timestamp comparison. |
| `solc-version` - 0.8.28 "too recent to be trusted" / not recommended | 3 | Informational. 0.8.28 is kept because the Remix and Etherscan settings must match. Should be re-checked against the Solidity known-bugs list before any real use. |

No high/medium findings were reported. Absence of findings is not proof of safety.

### Compiler known-bugs check (solc 0.8.28)
The official list (<https://docs.soliditylang.org/en/latest/bugs.html>, machine-readable `bugs_by_version.json`,
checked 2026-11-17) shows **7 known bugs affecting 0.8.28**. This build uses the legacy code generator
(no `viaIR`), optimizer on, EVM cancun:

| Bug | Severity | Fixed in | Applies here? |
|---|---|---|---|
| TransientStorageClearingHelperCollision | high | 0.8.34 | No - needs `viaIR` |
| UnsoundSpillInMutualRecursion | medium | 0.8.36 | No - needs `viaIR` |
| SpillSlotCollisionAcrossMutualRecursion | low/medium | 0.8.37 | No - needs `viaIR` |
| MisorderedNamedParametersInRequireWithCustomErrors | very low | 0.8.37 | No - needs `viaIR` |
| MemoryByteArrayElementDeleteClearsWholeWord | low/medium | 0.8.37 | No - no `delete` on memory `bytes` elements in the code (checked the flattened source) |
| YulOptimizerKnowledgeBaseStaleBookkeeping | low | 0.8.38 | **Not ruled out** - optimizer is on and OpenZeppelin SafeERC20 contains inline assembly |
| LostStorageArrayWriteOnSlotOverflow | low | 0.8.32 | **Not ruled out formally**; needs an array straddling the end of storage, which is not practically reachable for `requests[]` |

0.8.28 is kept because the course setup (Remix + Etherscan) was fixed to it. Before any real use, recompile with
the latest 0.8.x (0.8.38 at the time of checking) and re-run all tests.

### Other checks
* Flattened sources (`flat/*.sol`) compile with solc-js 0.8.28 to the same runtime bytecode as the Hardhat
  build (excluding the metadata hash).
* `npm audit` reports 39 advisories (16 low, 11 moderate, 12 high) in **dev dependencies** (Hardhat toolchain).
  They don't ship in the contracts but matter on the developer's machine; not individually triaged.

## 2. Known limitations (by design or not yet addressed)

1. **Owner is a single EOA with full control.** A stolen owner key can withdraw everything. Future: multisig
   (e.g. Safe) or timelock as owner.
2. **Fixed, not rolling, window.** Up to 2 x `dailyLimit` can be spent around a window boundary.
3. **Pending-request spam.** An agent can create unlimited Pending requests (only costs it gas). They move no
   funds but clutter `requests[]` and the owner's review queue. No expiry on requests.
4. **Approval may fail later.** A Pending request isn't reserved against the window or balance; it may revert at
   approval time (`ExceedsDailyLimit`, `InsufficientVaultBalance`) and must be retried or rejected.
5. **Approval is not bound to a time.** The owner can approve a days-old request as long as the re-checks pass.
6. **Memo is public and unvalidated.** Anything the agent writes is stored permanently on-chain; it must not
   contain secrets or personal data, and off-chain UIs must escape it.
7. **Non-standard tokens are out of scope.** Fee-on-transfer, rebasing, or blocklisting tokens (USDC itself has
   a blocklist) could make accounting or transfers behave differently. Only MockUSDC was tested.
8. **Payee allowlist trusts the owner.** If the owner allowlists a malicious or compromised service, the agent
   can drain up to its limits to it.
9. **Agent key handling is off-chain.** The demo keeps the agent key in `.env`; a real agent would need a KMS /
   enclave. Out of scope.
10. **No upgradeability.** Bugs require redeploying and moving funds (`withdraw`).
11. **`pause` stops `approveRequest`.** Intended, but means approvals wait until `unpause`.

## 3. What still needs human review

- [ ] Manual line-by-line review of `AgentVault.sol` by someone other than the author.
- [ ] Confirm the two "not ruled out" compiler bugs above don't affect the generated bytecode, or move to a fixed solc.
- [ ] Hardhat 2 is reaching end of life (per the Hardhat 2 docs); plan a move to Hardhat 3.
- [ ] Decide whether pending requests should expire or be capped per agent.
- [ ] Gas review of storing `memo` strings on-chain.
- [ ] Triage `npm audit` advisories in the dev toolchain.
- [ ] Review that Sepolia-deployed bytecode is verified and matches this repo (Etherscan "verified" badge).
- [ ] Any real-money use would need a professional audit, a multisig owner and a tested incident plan.

## 4. Secrets handling

* No keys in code. `hardhat.config.js` reads `SEPOLIA_RPC_URL`, `DEPLOYER_PRIVATE_KEY`, `AGENT_PRIVATE_KEY`,
  `ETHERSCAN_API_KEY` from a local `.env`, which is git-ignored. `.env.example` has placeholders only.
* Scripts never print keys, only public addresses and tx hashes.
* The Hardhat local network uses Hardhat's publicly known default dev accounts; they must never hold real funds.
