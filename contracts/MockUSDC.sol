// SPDX-License-Identifier: MIT
pragma solidity 0.8.28;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

/// @title MockUSDC
/// @notice !!! TEST TOKEN, NO VALUE !!! A plain 6-decimal ERC-20 used only on local networks and
///         Sepolia testnet to demonstrate AgentVault. It is NOT USDC and is not backed by anything.
///         The owner can mint unlimited amounts.
contract MockUSDC is ERC20, Ownable {
    /// @notice Deploys the test token; the deployer becomes the owner (the only minter).
    constructor() ERC20("Mock USDC", "mUSDC") Ownable(msg.sender) {}

    /// @notice Returns 6, matching real USDC's decimals so amounts look familiar.
    function decimals() public pure override returns (uint8) {
        return 6;
    }

    /// @notice Mints test tokens. TEST TOKEN, NO VALUE.
    /// @param to Recipient of the newly minted tokens.
    /// @param amount Amount in base units (6 decimals: 1 mUSDC = 1_000_000).
    function mint(address to, uint256 amount) external onlyOwner {
        _mint(to, amount);
    }
}
