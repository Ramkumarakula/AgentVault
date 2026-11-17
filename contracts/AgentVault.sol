// SPDX-License-Identifier: MIT
pragma solidity 0.8.28;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {Pausable} from "@openzeppelin/contracts/utils/Pausable.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/// @title AgentVault
/// @author Ramkumar (RK) - B.Tech CSE course project "Smart Contract and Development"
/// @notice An on-chain spending-policy wallet for AI agents. A human owner funds the vault with a
///         single ERC-20 token and registers agent addresses with a policy (per-payment limit, limit
///         per fixed 24h window, approval threshold, expiry, payee allowlist). The contract - not the
///         agent's prompt - enforces the policy. Payments above the approval threshold are stored as
///         Pending and only move funds after the owner approves them (human-in-the-loop).
/// @dev    Educational testnet project. NOT audited and NOT production-ready; see docs/SECURITY.md.
///         Assumes a standard ERC-20 (no fee-on-transfer / rebasing behaviour).
contract AgentVault is Ownable, Pausable, ReentrancyGuard {
    using SafeERC20 for IERC20;

    // ------------------------------------------------------------------
    // Types
    // ------------------------------------------------------------------

    /// @notice Spending policy for one agent address.
    struct AgentPolicy {
        bool active;
        uint128 perTxLimit; // max per single payment
        uint128 dailyLimit; // max total executed per fixed 24h window
        uint128 approvalThreshold; // amount > threshold => needs owner approval
        uint64 expiry; // unix time after which the agent can't spend
        uint128 spentInWindow; // executed amount in the current window
        uint64 windowStart; // start of the current fixed window
    }

    /// @notice Lifecycle of a payment request.
    enum Status {
        Pending,
        Executed,
        Rejected
    }

    /// @notice A payment made or requested by an agent.
    struct PaymentRequest {
        address agent;
        address to;
        uint128 amount;
        Status status;
        uint64 createdAt;
        string memo;
    }

    // ------------------------------------------------------------------
    // Constants / storage
    // ------------------------------------------------------------------

    /// @notice Length of the fixed spending window.
    uint256 public constant WINDOW_DURATION = 1 days;

    /// @notice Maximum memo length in bytes.
    uint256 public constant MAX_MEMO_LENGTH = 140;

    /// @notice The only token this vault holds and pays out.
    IERC20 public immutable token;

    /// @notice Policy per agent address.
    mapping(address => AgentPolicy) public policies;

    /// @notice agent => payee => allowed.
    mapping(address => mapping(address => bool)) public isPayeeAllowed;

    /// @notice Every payment (executed immediately, pending, or rejected), indexed by request id.
    PaymentRequest[] public requests;

    // ------------------------------------------------------------------
    // Errors
    // ------------------------------------------------------------------

    error ZeroAddress();
    error ZeroAmount();
    error InvalidLimits(uint128 approvalThreshold, uint128 perTxLimit, uint128 dailyLimit);
    error ExpiryNotInFuture(uint64 expiry, uint256 nowTs);
    error InvalidPayee(address payee);
    error AgentNotActive(address agent);
    error AgentExpired(address agent, uint64 expiry);
    error PayeeNotAllowed(address agent, address payee);
    error ExceedsPerTxLimit(uint256 amount, uint128 perTxLimit);
    error ExceedsDailyLimit(uint256 amount, uint256 remaining);
    error MemoTooLong(uint256 length, uint256 maxLength);
    error InsufficientVaultBalance(uint256 available, uint256 required);
    error RequestNotFound(uint256 id);
    error RequestNotPending(uint256 id, Status status);
    error RenounceDisabled();

    // ------------------------------------------------------------------
    // Events
    // ------------------------------------------------------------------

    event AgentPolicySet(
        address indexed agent,
        uint128 perTxLimit,
        uint128 dailyLimit,
        uint128 approvalThreshold,
        uint64 expiry
    );
    event AgentRevoked(address indexed agent);
    event PayeeSet(address indexed agent, address indexed payee, bool allowed);
    event Deposited(address indexed from, uint256 amount);
    event Withdrawn(address indexed to, uint256 amount);
    event PaymentExecuted(uint256 indexed id, address indexed agent, address indexed to, uint256 amount, string memo);
    event PaymentRequested(uint256 indexed id, address indexed agent, address indexed to, uint256 amount, string memo);
    event PaymentApproved(uint256 indexed id, address indexed approver);
    event PaymentRejected(uint256 indexed id, address indexed rejecter);

    // ------------------------------------------------------------------
    // Constructor
    // ------------------------------------------------------------------

    /// @notice Creates a vault for `token_`; the deployer becomes the owner.
    /// @param token_ The ERC-20 token the vault holds (must not be the zero address).
    constructor(IERC20 token_) Ownable(msg.sender) {
        if (address(token_) == address(0)) revert ZeroAddress();
        token = token_;
    }

    // ------------------------------------------------------------------
    // Owner: policy management
    // ------------------------------------------------------------------

    /// @notice Creates or updates the policy of `agent` and marks it active.
    /// @dev Requires approvalThreshold <= perTxLimit <= dailyLimit, perTxLimit > 0 and expiry in the
    ///      future. Updating an existing agent keeps its current window usage (spentInWindow /
    ///      windowStart) so that an update cannot silently hand out a fresh daily allowance.
    /// @param agent The agent address (must not be zero).
    /// @param perTxLimit Max amount of a single payment.
    /// @param dailyLimit Max total executed amount per fixed 24h window.
    /// @param approvalThreshold Payments strictly above this need owner approval.
    /// @param expiry Unix timestamp after which the agent can no longer spend.
    function setAgentPolicy(
        address agent,
        uint128 perTxLimit,
        uint128 dailyLimit,
        uint128 approvalThreshold,
        uint64 expiry
    ) external onlyOwner {
        if (agent == address(0)) revert ZeroAddress();
        if (perTxLimit == 0 || approvalThreshold > perTxLimit || perTxLimit > dailyLimit) {
            revert InvalidLimits(approvalThreshold, perTxLimit, dailyLimit);
        }
        if (expiry <= block.timestamp) revert ExpiryNotInFuture(expiry, block.timestamp);

        AgentPolicy storage p = policies[agent];
        bool isNew = p.windowStart == 0;
        p.active = true;
        p.perTxLimit = perTxLimit;
        p.dailyLimit = dailyLimit;
        p.approvalThreshold = approvalThreshold;
        p.expiry = expiry;
        if (isNew) {
            p.windowStart = uint64(block.timestamp);
            p.spentInWindow = 0;
        }

        emit AgentPolicySet(agent, perTxLimit, dailyLimit, approvalThreshold, expiry);
    }

    /// @notice Deactivates `agent`; it can no longer pay and its pending requests can't be approved.
    /// @param agent The agent to revoke (must currently be active).
    function revokeAgent(address agent) external onlyOwner {
        AgentPolicy storage p = policies[agent];
        if (!p.active) revert AgentNotActive(agent);
        p.active = false;
        emit AgentRevoked(agent);
    }

    /// @notice Adds or removes `payee` from the allowlist of `agent`.
    /// @param agent The agent whose allowlist changes (must not be zero).
    /// @param payee The recipient (must not be zero or this vault).
    /// @param allowed True to allow, false to remove.
    function setPayee(address agent, address payee, bool allowed) external onlyOwner {
        if (agent == address(0)) revert ZeroAddress();
        if (payee == address(0) || payee == address(this)) revert InvalidPayee(payee);
        isPayeeAllowed[agent][payee] = allowed;
        emit PayeeSet(agent, payee, allowed);
    }

    /// @notice Pauses all agent payments and approvals (emergency stop). Withdraw still works.
    function pause() external onlyOwner {
        _pause();
    }

    /// @notice Lifts the emergency stop.
    function unpause() external onlyOwner {
        _unpause();
    }

    /// @notice Disabled: renouncing ownership would permanently lock funds and pending requests.
    function renounceOwnership() public view override onlyOwner {
        revert RenounceDisabled();
    }

    // ------------------------------------------------------------------
    // Funding
    // ------------------------------------------------------------------

    /// @notice Pulls `amount` tokens from the caller into the vault. Anyone may fund the vault.
    /// @dev Caller must first `approve` this vault on the token contract.
    /// @param amount Amount in token base units (> 0).
    function deposit(uint256 amount) external nonReentrant {
        if (amount == 0) revert ZeroAmount();
        emit Deposited(msg.sender, amount);
        token.safeTransferFrom(msg.sender, address(this), amount);
    }

    /// @notice Sends `amount` vault tokens to `to`. Owner only; works even while paused.
    /// @param to Recipient (must not be zero).
    /// @param amount Amount (> 0, <= vault balance).
    function withdraw(address to, uint256 amount) external onlyOwner nonReentrant {
        if (to == address(0)) revert ZeroAddress();
        if (amount == 0) revert ZeroAmount();
        uint256 bal = token.balanceOf(address(this));
        if (amount > bal) revert InsufficientVaultBalance(bal, amount);
        emit Withdrawn(to, amount);
        token.safeTransfer(to, amount);
    }

    // ------------------------------------------------------------------
    // Agent: payments
    // ------------------------------------------------------------------

    /// @notice Called by an agent to pay `to`. Small payments execute immediately; payments above
    ///         the agent's approval threshold are stored as Pending for the owner to approve.
    /// @param to Recipient; must be on the caller's payee allowlist.
    /// @param amount Amount in token base units (> 0, <= perTxLimit).
    /// @param memo Free-text reason (max 140 bytes), stored on-chain and emitted in events.
    /// @return requestId Index of the new entry in `requests`.
    function pay(address to, uint256 amount, string calldata memo)
        external
        whenNotPaused
        nonReentrant
        returns (uint256 requestId)
    {
        if (bytes(memo).length > MAX_MEMO_LENGTH) revert MemoTooLong(bytes(memo).length, MAX_MEMO_LENGTH);
        if (amount == 0) revert ZeroAmount();

        AgentPolicy storage p = policies[msg.sender];
        _checkAgent(msg.sender, p, to);
        if (amount > p.perTxLimit) revert ExceedsPerTxLimit(amount, p.perTxLimit);
        // Safe: amount <= perTxLimit, which is a uint128.
        uint128 amt = uint128(amount);

        requestId = requests.length;

        if (amt > p.approvalThreshold) {
            // Needs human approval: record only, move nothing.
            requests.push(PaymentRequest(msg.sender, to, amt, Status.Pending, uint64(block.timestamp), memo));
            emit PaymentRequested(requestId, msg.sender, to, amt, memo);
            return requestId;
        }

        // Effects
        _consumeWindow(p, amt);
        _checkBalance(amt);
        requests.push(PaymentRequest(msg.sender, to, amt, Status.Executed, uint64(block.timestamp), memo));
        emit PaymentExecuted(requestId, msg.sender, to, amt, memo);

        // Interaction
        token.safeTransfer(to, amt);
    }

    // ------------------------------------------------------------------
    // Owner: approvals
    // ------------------------------------------------------------------

    /// @notice Approves and executes pending request `id`. The agent's policy is RE-CHECKED now:
    ///         agent active, not expired, payee still allowed, amount <= current perTxLimit,
    ///         fits in the current window's remaining limit, and the vault has enough balance.
    /// @param id The request id.
    function approveRequest(uint256 id) external onlyOwner whenNotPaused nonReentrant {
        PaymentRequest storage r = _pendingRequest(id);
        AgentPolicy storage p = policies[r.agent];

        _checkAgent(r.agent, p, r.to);
        if (r.amount > p.perTxLimit) revert ExceedsPerTxLimit(r.amount, p.perTxLimit);

        // Effects
        _consumeWindow(p, r.amount);
        _checkBalance(r.amount);
        r.status = Status.Executed;
        emit PaymentApproved(id, msg.sender);
        emit PaymentExecuted(id, r.agent, r.to, r.amount, r.memo);

        // Interaction
        token.safeTransfer(r.to, r.amount);
    }

    /// @notice Rejects pending request `id`. No funds move. Works even while paused.
    /// @param id The request id.
    function rejectRequest(uint256 id) external onlyOwner {
        PaymentRequest storage r = _pendingRequest(id);
        r.status = Status.Rejected;
        emit PaymentRejected(id, msg.sender);
    }

    // ------------------------------------------------------------------
    // Views
    // ------------------------------------------------------------------

    /// @notice Number of payment requests ever created.
    function requestCount() external view returns (uint256) {
        return requests.length;
    }

    /// @notice Amount `agent` can still have executed in its current window (0 if inactive/expired).
    /// @param agent The agent address.
    function remainingInWindow(address agent) external view returns (uint256) {
        AgentPolicy storage p = policies[agent];
        if (!p.active || block.timestamp > p.expiry) return 0;
        if (block.timestamp >= uint256(p.windowStart) + WINDOW_DURATION) return p.dailyLimit;
        return _remaining(p);
    }

    // ------------------------------------------------------------------
    // Internal helpers
    // ------------------------------------------------------------------

    /// @dev Reverts unless `agent` is active, not expired, and `to` is on its allowlist.
    function _checkAgent(address agent, AgentPolicy storage p, address to) private view {
        if (!p.active) revert AgentNotActive(agent);
        if (block.timestamp > p.expiry) revert AgentExpired(agent, p.expiry);
        if (!isPayeeAllowed[agent][to]) revert PayeeNotAllowed(agent, to);
    }

    /// @dev Rolls the FIXED 24h window if it has elapsed, then adds `amount` to spentInWindow.
    ///      This is a fixed window (resets when now >= windowStart + 1 day), not a rolling window.
    function _consumeWindow(AgentPolicy storage p, uint128 amount) private {
        if (block.timestamp >= uint256(p.windowStart) + WINDOW_DURATION) {
            p.windowStart = uint64(block.timestamp);
            p.spentInWindow = 0;
        }
        uint256 remaining = _remaining(p);
        if (amount > remaining) revert ExceedsDailyLimit(amount, remaining);
        p.spentInWindow += amount;
    }

    /// @dev dailyLimit - spentInWindow, clamped at 0 (the owner may lower dailyLimit mid-window).
    function _remaining(AgentPolicy storage p) private view returns (uint256) {
        return p.dailyLimit > p.spentInWindow ? uint256(p.dailyLimit) - p.spentInWindow : 0;
    }

    /// @dev Reverts if the vault holds less than `amount`.
    function _checkBalance(uint256 amount) private view {
        uint256 bal = token.balanceOf(address(this));
        if (amount > bal) revert InsufficientVaultBalance(bal, amount);
    }

    /// @dev Returns request `id`, reverting if it doesn't exist or isn't Pending.
    function _pendingRequest(uint256 id) private view returns (PaymentRequest storage r) {
        if (id >= requests.length) revert RequestNotFound(id);
        r = requests[id];
        if (r.status != Status.Pending) revert RequestNotPending(id, r.status);
    }
}
