// SPDX-License-Identifier: MIT
pragma solidity 0.8.28;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";

interface IAgentVaultPay {
    function pay(address to, uint256 amount, string calldata memo) external returns (uint256);
}

/// @title ReentrantToken (TEST ONLY - NOT DEPLOYED)
/// @notice Malicious ERC-20 used in tests to prove AgentVault's nonReentrant guard works. When armed,
///         every transfer() out of the vault tries to call vault.pay() again (this contract is registered
///         as an agent in the test), which must revert with ReentrancyGuardReentrantCall.
contract ReentrantToken is ERC20 {
    address public vault;
    address public reenterTo;
    bool public armed;

    constructor() ERC20("Reentrant", "RE") {
        _mint(msg.sender, 1e24);
    }

    function arm(address vault_, address to_) external {
        vault = vault_;
        reenterTo = to_;
        armed = true;
    }

    function transfer(address to, uint256 value) public override returns (bool) {
        bool ok = super.transfer(to, value);
        if (armed && msg.sender == vault) {
            armed = false;
            IAgentVaultPay(vault).pay(reenterTo, 1, "reenter");
        }
        return ok;
    }
}
