# Deploying AgentVault to Sepolia with Remix + MetaMask

This guide is **Option 1** (you deploy yourself; no private key ever leaves MetaMask).
Option 2 (`scripts/deploy.js` with a test-only key in `.env`) is in the README.

> Testnet only. MockUSDC is a **test token with no value**. Use a MetaMask account that holds only
> Sepolia test ETH.

Settings that **must** match everywhere (Hardhat config, Remix, Etherscan):

| Setting | Value |
|---|---|
| Compiler | `0.8.28` (exact: `v0.8.28+commit.7893614a`) |
| Optimization | enabled, **200** runs |
| EVM version | **cancun** |
| License | MIT |

UI labels below were checked against the Remix docs on 2026-11-17
(<https://remix-ide.readthedocs.io/en/latest/compile.html>, <https://remix-ide.readthedocs.io/en/latest/run.html>,
<https://remix-ide.readthedocs.io/en/latest/import.html>). Remix changes its UI often, so a label may differ slightly.

---

## 0. Pick a source route

**Route A - flattened files (recommended).** Paste `flat/MockUSDC_flat.sol` and `flat/AgentVault_flat.sol`
from this repo. They contain the exact OpenZeppelin 5.4.0 code the tests ran against, and you later verify
the *same* file on Etherscan as "Solidity (Single file)", so the match is exact.
(Regenerate with `npm run flatten` if you change a contract.)

**Route B - two files with npm imports.** Create `MockUSDC.sol` and `AgentVault.sol` with the code from
`contracts/`. Remix resolves `@openzeppelin/...` imports from npm via unpkg into a `.deps` folder. To get the
same OpenZeppelin version the tests used, change each import to the pinned form, e.g.

```solidity
import {ERC20} from "@openzeppelin/contracts@5.4.0/token/ERC20/ERC20.sol";
```

(The Remix import docs show this `@version` syntax with a 4.2.0 example; 5.4.0 is assumed to work the same
way - check that `.deps/npm/@openzeppelin/contracts@5.4.0` appears.) For verification in Route B, right-click
`AgentVault.sol` -> **Flatten** and use the flattened file *only if you deploy that flattened file*; otherwise
the metadata hash differs. Route A avoids this problem.

## 1. Open Remix and create the files

1. Open <https://remix.ethereum.org>.
2. In **File Explorer**, create a new blank workspace (or use the default one).
3. Create `MockUSDC_flat.sol` and paste the contents of `flat/MockUSDC_flat.sol`.
4. Create `AgentVault_flat.sol` and paste the contents of `flat/AgentVault_flat.sol`.

## 2. Compile with matching settings

1. Open the **Solidity Compiler** tab.
2. **COMPILER** dropdown: `0.8.28+commit.7893614a`.
3. Click **Advanced Configuration**:
   - tick **Enable optimization**, runs = **200**
   - **EVM** dropdown: **cancun**
4. Select `MockUSDC_flat.sol` -> **Compile**. Then `AgentVault_flat.sol` -> **Compile**.
   Both should show a green check. Warnings about multiple contracts in one file are normal.

[Insert screenshot: Remix compiler settings - 0.8.28, optimization 200, EVM cancun]

## 3. Connect MetaMask on Sepolia

1. In MetaMask, switch the network to **Sepolia** and select your test-only owner account.
2. In Remix open **Deploy & Run Transactions**.
3. **ENVIRONMENT**: choose **Browser Extension** -> MetaMask (older Remix versions call this
   **"Injected Provider - MetaMask"**). Approve the connection in MetaMask.
4. Check the network shown under Environment is **Sepolia (11155111)** and the account is the one you expect.

## 4. Deploy MockUSDC

1. **CONTRACT** dropdown: `MockUSDC` (from `MockUSDC_flat.sol`).
2. Click **Deploy**, review gas in MetaMask, **Confirm**.
3. When mined, copy from the Remix terminal / Deployed Contracts:
   - MockUSDC **address**
   - deploy **transaction hash**

[Insert screenshot: MetaMask confirm dialog for MockUSDC deploy]

## 5. Deploy AgentVault(tokenAddress)

1. **CONTRACT** dropdown: `AgentVault` (from `AgentVault_flat.sol`).
2. In the field next to **Deploy** enter the MockUSDC address from step 4 (the `token_` argument).
3. **Deploy** -> confirm in MetaMask.
4. Copy the AgentVault **address** and **transaction hash**.
5. Sanity check under Deployed Contracts: `token()` returns the MockUSDC address and `owner()` returns your account.

[Insert screenshot: Remix Deployed Contracts panel showing AgentVault token() and owner()]

## 6. Verify on Sepolia Etherscan

Do this for each contract (MockUSDC first):

1. Open `https://sepolia.etherscan.io/address/<ADDRESS>` -> **Contract** tab -> **Verify and Publish**
   (or go to <https://sepolia.etherscan.io/verifyContract>).
2. Contract Address: the deployed address.
3. Compiler Type: **Solidity (Single file)**.
4. Compiler Version: **v0.8.28+commit.7893614a**.
5. Open Source License Type: **MIT License (MIT)**. Agree to the terms, continue.
6. Paste the full flattened source (the same `*_flat.sol` you deployed).
7. Optimization: **Yes**, runs **200**. EVM version / Misc settings: **cancun**.
8. Constructor arguments (ABI-encoded):
   - MockUSDC: leave empty.
   - AgentVault: the token address left-padded to 32 bytes, i.e. 24 zeros followed by the 40 hex chars of
     the address without `0x`. You can produce it locally with
     `node -e "console.log(require('ethers').AbiCoder.defaultAbiCoder().encode(['address'],['0xTOKEN']).slice(2))"`.
     Etherscan often detects it automatically.
9. Submit; you should see "Successfully generated Bytecode and ABI".

[Insert screenshot: Etherscan "verified" page for AgentVault]

**Alternative:** if you set `ETHERSCAN_API_KEY` in `.env`, Hardhat can verify, but only for contracts
compiled from the *repo sources* (Option 2). For a Route A Remix deploy, use the web form above.

## 7. Record the results

Send me (or paste into README "Sepolia deployment") **only public data**: the two addresses and two tx hashes.
Never paste a private key or seed phrase anywhere.

Then, to run the demo against your deployment, add to your local `.env`:

```
TOKEN_ADDRESS=0x...
VAULT_ADDRESS=0x...
```

The demo also needs `DEPLOYER_PRIVATE_KEY` (the same owner account, test-only) and `AGENT_PRIVATE_KEY`
(a second throwaway account with a little Sepolia ETH) in `.env`, because the scripts must sign as both owner
and agent. If you prefer not to put the owner key in `.env` at all, deploy via Remix, then use Remix to run the
owner steps manually; the agent steps still need `AGENT_PRIVATE_KEY`.
