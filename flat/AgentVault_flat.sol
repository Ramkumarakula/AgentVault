// Sources flattened with hardhat v2.29.1 https://hardhat.org

// SPDX-License-Identifier: MIT

// File @openzeppelin/contracts/utils/Context.sol@v5.4.0

// Original license: SPDX_License_Identifier: MIT
// OpenZeppelin Contracts (last updated v5.0.1) (utils/Context.sol)

pragma solidity ^0.8.20;

/**
 * @dev Provides information about the current execution context, including the
 * sender of the transaction and its data. While these are generally available
 * via msg.sender and msg.data, they should not be accessed in such a direct
 * manner, since when dealing with meta-transactions the account sending and
 * paying for execution may not be the actual sender (as far as an application
 * is concerned).
 *
 * This contract is only required for intermediate, library-like contracts.
 */
abstract contract Context {
    function _msgSender() internal view virtual returns (address) {
        return msg.sender;
    }

    function _msgData() internal view virtual returns (bytes calldata) {
        return msg.data;
    }

    function _contextSuffixLength() internal view virtual returns (uint256) {
        return 0;
    }
}


// File @openzeppelin/contracts/access/Ownable.sol@v5.4.0

// Original license: SPDX_License_Identifier: MIT
// OpenZeppelin Contracts (last updated v5.0.0) (access/Ownable.sol)

pragma solidity ^0.8.20;

/**
 * @dev Contract module which provides a basic access control mechanism, where
 * there is an account (an owner) that can be granted exclusive access to
 * specific functions.
 *
 * The initial owner is set to the address provided by the deployer. This can
 * later be changed with {transferOwnership}.
 *
 * This module is used through inheritance. It will make available the modifier
 * `onlyOwner`, which can be applied to your functions to restrict their use to
 * the owner.
 */
abstract contract Ownable is Context {
    address private _owner;

    /**
     * @dev The caller account is not authorized to perform an operation.
     */
    error OwnableUnauthorizedAccount(address account);

    /**
     * @dev The owner is not a valid owner account. (eg. `address(0)`)
     */
    error OwnableInvalidOwner(address owner);

    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);

    /**
     * @dev Initializes the contract setting the address provided by the deployer as the initial owner.
     */
    constructor(address initialOwner) {
        if (initialOwner == address(0)) {
            revert OwnableInvalidOwner(address(0));
        }
        _transferOwnership(initialOwner);
    }

    /**
     * @dev Throws if called by any account other than the owner.
     */
    modifier onlyOwner() {
        _checkOwner();
        _;
    }

    /**
     * @dev Returns the address of the current owner.
     */
    function owner() public view virtual returns (address) {
        return _owner;
    }

    /**
     * @dev Throws if the sender is not the owner.
     */
    function _checkOwner() internal view virtual {
        if (owner() != _msgSender()) {
            revert OwnableUnauthorizedAccount(_msgSender());
        }
    }

    /**
     * @dev Leaves the contract without owner. It will not be possible to call
     * `onlyOwner` functions. Can only be called by the current owner.
     *
     * NOTE: Renouncing ownership will leave the contract without an owner,
     * thereby disabling any functionality that is only available to the owner.
     */
    function renounceOwnership() public virtual onlyOwner {
        _transferOwnership(address(0));
    }

    /**
     * @dev Transfers ownership of the contract to a new account (`newOwner`).
     * Can only be called by the current owner.
     */
    function transferOwnership(address newOwner) public virtual onlyOwner {
        if (newOwner == address(0)) {
            revert OwnableInvalidOwner(address(0));
        }
        _transferOwnership(newOwner);
    }

    /**
     * @dev Transfers ownership of the contract to a new account (`newOwner`).
     * Internal function without access restriction.
     */
    function _transferOwnership(address newOwner) internal virtual {
        address oldOwner = _owner;
        _owner = newOwner;
        emit OwnershipTransferred(oldOwner, newOwner);
    }
}


// File @openzeppelin/contracts/utils/introspection/IERC165.sol@v5.4.0

// Original license: SPDX_License_Identifier: MIT
// OpenZeppelin Contracts (last updated v5.4.0) (utils/introspection/IERC165.sol)

pragma solidity >=0.4.16;

/**
 * @dev Interface of the ERC-165 standard, as defined in the
 * https://eips.ethereum.org/EIPS/eip-165[ERC].
 *
 * Implementers can declare support of contract interfaces, which can then be
 * queried by others ({ERC165Checker}).
 *
 * For an implementation, see {ERC165}.
 */
interface IERC165 {
    /**
     * @dev Returns true if this contract implements the interface defined by
     * `interfaceId`. See the corresponding
     * https://eips.ethereum.org/EIPS/eip-165#how-interfaces-are-identified[ERC section]
     * to learn more about how these ids are created.
     *
     * This function call must use less than 30 000 gas.
     */
    function supportsInterface(bytes4 interfaceId) external view returns (bool);
}


// File @openzeppelin/contracts/interfaces/IERC165.sol@v5.4.0

// Original license: SPDX_License_Identifier: MIT
// OpenZeppelin Contracts (last updated v5.4.0) (interfaces/IERC165.sol)

pragma solidity >=0.4.16;


// File @openzeppelin/contracts/token/ERC20/IERC20.sol@v5.4.0

// Original license: SPDX_License_Identifier: MIT
// OpenZeppelin Contracts (last updated v5.4.0) (token/ERC20/IERC20.sol)

pragma solidity >=0.4.16;

/**
 * @dev Interface of the ERC-20 standard as defined in the ERC.
 */
interface IERC20 {
    /**
     * @dev Emitted when `value` tokens are moved from one account (`from`) to
     * another (`to`).
     *
     * Note that `value` may be zero.
     */
    event Transfer(address indexed from, address indexed to, uint256 value);

    /**
     * @dev Emitted when the allowance of a `spender` for an `owner` is set by
     * a call to {approve}. `value` is the new allowance.
     */
    event Approval(address indexed owner, address indexed spender, uint256 value);

    /**
     * @dev Returns the value of tokens in existence.
     */
    function totalSupply() external view returns (uint256);

    /**
     * @dev Returns the value of tokens owned by `account`.
     */
    function balanceOf(address account) external view returns (uint256);

    /**
     * @dev Moves a `value` amount of tokens from the caller's account to `to`.
     *
     * Returns a boolean value indicating whether the operation succeeded.
     *
     * Emits a {Transfer} event.
     */
    function transfer(address to, uint256 value) external returns (bool);

    /**
     * @dev Returns the remaining number of tokens that `spender` will be
     * allowed to spend on behalf of `owner` through {transferFrom}. This is
     * zero by default.
     *
     * This value changes when {approve} or {transferFrom} are called.
     */
    function allowance(address owner, address spender) external view returns (uint256);

    /**
     * @dev Sets a `value` amount of tokens as the allowance of `spender` over the
     * caller's tokens.
     *
     * Returns a boolean value indicating whether the operation succeeded.
     *
     * IMPORTANT: Beware that changing an allowance with this method brings the risk
     * that someone may use both the old and the new allowance by unfortunate
     * transaction ordering. One possible solution to mitigate this race
     * condition is to first reduce the spender's allowance to 0 and set the
     * desired value afterwards:
     * https://github.com/ethereum/EIPs/issues/20#issuecomment-263524729
     *
     * Emits an {Approval} event.
     */
    function approve(address spender, uint256 value) external returns (bool);

    /**
     * @dev Moves a `value` amount of tokens from `from` to `to` using the
     * allowance mechanism. `value` is then deducted from the caller's
     * allowance.
     *
     * Returns a boolean value indicating whether the operation succeeded.
     *
     * Emits a {Transfer} event.
     */
    function transferFrom(address from, address to, uint256 value) external returns (bool);
}


// File @openzeppelin/contracts/interfaces/IERC20.sol@v5.4.0

// Original license: SPDX_License_Identifier: MIT
// OpenZeppelin Contracts (last updated v5.4.0) (interfaces/IERC20.sol)

pragma solidity >=0.4.16;


// File @openzeppelin/contracts/interfaces/IERC1363.sol@v5.4.0

// Original license: SPDX_License_Identifier: MIT
// OpenZeppelin Contracts (last updated v5.4.0) (interfaces/IERC1363.sol)

pragma solidity >=0.6.2;


/**
 * @title IERC1363
 * @dev Interface of the ERC-1363 standard as defined in the https://eips.ethereum.org/EIPS/eip-1363[ERC-1363].
 *
 * Defines an extension interface for ERC-20 tokens that supports executing code on a recipient contract
 * after `transfer` or `transferFrom`, or code on a spender contract after `approve`, in a single transaction.
 */
interface IERC1363 is IERC20, IERC165 {
    /*
     * Note: the ERC-165 identifier for this interface is 0xb0202a11.
     * 0xb0202a11 ===
     *   bytes4(keccak256('transferAndCall(address,uint256)')) ^
     *   bytes4(keccak256('transferAndCall(address,uint256,bytes)')) ^
     *   bytes4(keccak256('transferFromAndCall(address,address,uint256)')) ^
     *   bytes4(keccak256('transferFromAndCall(address,address,uint256,bytes)')) ^
     *   bytes4(keccak256('approveAndCall(address,uint256)')) ^
     *   bytes4(keccak256('approveAndCall(address,uint256,bytes)'))
     */

    /**
     * @dev Moves a `value` amount of tokens from the caller's account to `to`
     * and then calls {IERC1363Receiver-onTransferReceived} on `to`.
     * @param to The address which you want to transfer to.
     * @param value The amount of tokens to be transferred.
     * @return A boolean value indicating whether the operation succeeded unless throwing.
     */
    function transferAndCall(address to, uint256 value) external returns (bool);

    /**
     * @dev Moves a `value` amount of tokens from the caller's account to `to`
     * and then calls {IERC1363Receiver-onTransferReceived} on `to`.
     * @param to The address which you want to transfer to.
     * @param value The amount of tokens to be transferred.
     * @param data Additional data with no specified format, sent in call to `to`.
     * @return A boolean value indicating whether the operation succeeded unless throwing.
     */
    function transferAndCall(address to, uint256 value, bytes calldata data) external returns (bool);

    /**
     * @dev Moves a `value` amount of tokens from `from` to `to` using the allowance mechanism
     * and then calls {IERC1363Receiver-onTransferReceived} on `to`.
     * @param from The address which you want to send tokens from.
     * @param to The address which you want to transfer to.
     * @param value The amount of tokens to be transferred.
     * @return A boolean value indicating whether the operation succeeded unless throwing.
     */
    function transferFromAndCall(address from, address to, uint256 value) external returns (bool);

    /**
     * @dev Moves a `value` amount of tokens from `from` to `to` using the allowance mechanism
     * and then calls {IERC1363Receiver-onTransferReceived} on `to`.
     * @param from The address which you want to send tokens from.
     * @param to The address which you want to transfer to.
     * @param value The amount of tokens to be transferred.
     * @param data Additional data with no specified format, sent in call to `to`.
     * @return A boolean value indicating whether the operation succeeded unless throwing.
     */
    function transferFromAndCall(address from, address to, uint256 value, bytes calldata data) external returns (bool);

    /**
     * @dev Sets a `value` amount of tokens as the allowance of `spender` over the
     * caller's tokens and then calls {IERC1363Spender-onApprovalReceived} on `spender`.
     * @param spender The address which will spend the funds.
     * @param value The amount of tokens to be spent.
     * @return A boolean value indicating whether the operation succeeded unless throwing.
     */
    function approveAndCall(address spender, uint256 value) external returns (bool);

    /**
     * @dev Sets a `value` amount of tokens as the allowance of `spender` over the
     * caller's tokens and then calls {IERC1363Spender-onApprovalReceived} on `spender`.
     * @param spender The address which will spend the funds.
     * @param value The amount of tokens to be spent.
     * @param data Additional data with no specified format, sent in call to `spender`.
     * @return A boolean value indicating whether the operation succeeded unless throwing.
     */
    function approveAndCall(address spender, uint256 value, bytes calldata data) external returns (bool);
}


// File @openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol@v5.4.0

// Original license: SPDX_License_Identifier: MIT
// OpenZeppelin Contracts (last updated v5.3.0) (token/ERC20/utils/SafeERC20.sol)

pragma solidity ^0.8.20;


/**
 * @title SafeERC20
 * @dev Wrappers around ERC-20 operations that throw on failure (when the token
 * contract returns false). Tokens that return no value (and instead revert or
 * throw on failure) are also supported, non-reverting calls are assumed to be
 * successful.
 * To use this library you can add a `using SafeERC20 for IERC20;` statement to your contract,
 * which allows you to call the safe operations as `token.safeTransfer(...)`, etc.
 */
library SafeERC20 {
    /**
     * @dev An operation with an ERC-20 token failed.
     */
    error SafeERC20FailedOperation(address token);

    /**
     * @dev Indicates a failed `decreaseAllowance` request.
     */
    error SafeERC20FailedDecreaseAllowance(address spender, uint256 currentAllowance, uint256 requestedDecrease);

    /**
     * @dev Transfer `value` amount of `token` from the calling contract to `to`. If `token` returns no value,
     * non-reverting calls are assumed to be successful.
     */
    function safeTransfer(IERC20 token, address to, uint256 value) internal {
        _callOptionalReturn(token, abi.encodeCall(token.transfer, (to, value)));
    }

    /**
     * @dev Transfer `value` amount of `token` from `from` to `to`, spending the approval given by `from` to the
     * calling contract. If `token` returns no value, non-reverting calls are assumed to be successful.
     */
    function safeTransferFrom(IERC20 token, address from, address to, uint256 value) internal {
        _callOptionalReturn(token, abi.encodeCall(token.transferFrom, (from, to, value)));
    }

    /**
     * @dev Variant of {safeTransfer} that returns a bool instead of reverting if the operation is not successful.
     */
    function trySafeTransfer(IERC20 token, address to, uint256 value) internal returns (bool) {
        return _callOptionalReturnBool(token, abi.encodeCall(token.transfer, (to, value)));
    }

    /**
     * @dev Variant of {safeTransferFrom} that returns a bool instead of reverting if the operation is not successful.
     */
    function trySafeTransferFrom(IERC20 token, address from, address to, uint256 value) internal returns (bool) {
        return _callOptionalReturnBool(token, abi.encodeCall(token.transferFrom, (from, to, value)));
    }

    /**
     * @dev Increase the calling contract's allowance toward `spender` by `value`. If `token` returns no value,
     * non-reverting calls are assumed to be successful.
     *
     * IMPORTANT: If the token implements ERC-7674 (ERC-20 with temporary allowance), and if the "client"
     * smart contract uses ERC-7674 to set temporary allowances, then the "client" smart contract should avoid using
     * this function. Performing a {safeIncreaseAllowance} or {safeDecreaseAllowance} operation on a token contract
     * that has a non-zero temporary allowance (for that particular owner-spender) will result in unexpected behavior.
     */
    function safeIncreaseAllowance(IERC20 token, address spender, uint256 value) internal {
        uint256 oldAllowance = token.allowance(address(this), spender);
        forceApprove(token, spender, oldAllowance + value);
    }

    /**
     * @dev Decrease the calling contract's allowance toward `spender` by `requestedDecrease`. If `token` returns no
     * value, non-reverting calls are assumed to be successful.
     *
     * IMPORTANT: If the token implements ERC-7674 (ERC-20 with temporary allowance), and if the "client"
     * smart contract uses ERC-7674 to set temporary allowances, then the "client" smart contract should avoid using
     * this function. Performing a {safeIncreaseAllowance} or {safeDecreaseAllowance} operation on a token contract
     * that has a non-zero temporary allowance (for that particular owner-spender) will result in unexpected behavior.
     */
    function safeDecreaseAllowance(IERC20 token, address spender, uint256 requestedDecrease) internal {
        unchecked {
            uint256 currentAllowance = token.allowance(address(this), spender);
            if (currentAllowance < requestedDecrease) {
                revert SafeERC20FailedDecreaseAllowance(spender, currentAllowance, requestedDecrease);
            }
            forceApprove(token, spender, currentAllowance - requestedDecrease);
        }
    }

    /**
     * @dev Set the calling contract's allowance toward `spender` to `value`. If `token` returns no value,
     * non-reverting calls are assumed to be successful. Meant to be used with tokens that require the approval
     * to be set to zero before setting it to a non-zero value, such as USDT.
     *
     * NOTE: If the token implements ERC-7674, this function will not modify any temporary allowance. This function
     * only sets the "standard" allowance. Any temporary allowance will remain active, in addition to the value being
     * set here.
     */
    function forceApprove(IERC20 token, address spender, uint256 value) internal {
        bytes memory approvalCall = abi.encodeCall(token.approve, (spender, value));

        if (!_callOptionalReturnBool(token, approvalCall)) {
            _callOptionalReturn(token, abi.encodeCall(token.approve, (spender, 0)));
            _callOptionalReturn(token, approvalCall);
        }
    }

    /**
     * @dev Performs an {ERC1363} transferAndCall, with a fallback to the simple {ERC20} transfer if the target has no
     * code. This can be used to implement an {ERC721}-like safe transfer that rely on {ERC1363} checks when
     * targeting contracts.
     *
     * Reverts if the returned value is other than `true`.
     */
    function transferAndCallRelaxed(IERC1363 token, address to, uint256 value, bytes memory data) internal {
        if (to.code.length == 0) {
            safeTransfer(token, to, value);
        } else if (!token.transferAndCall(to, value, data)) {
            revert SafeERC20FailedOperation(address(token));
        }
    }

    /**
     * @dev Performs an {ERC1363} transferFromAndCall, with a fallback to the simple {ERC20} transferFrom if the target
     * has no code. This can be used to implement an {ERC721}-like safe transfer that rely on {ERC1363} checks when
     * targeting contracts.
     *
     * Reverts if the returned value is other than `true`.
     */
    function transferFromAndCallRelaxed(
        IERC1363 token,
        address from,
        address to,
        uint256 value,
        bytes memory data
    ) internal {
        if (to.code.length == 0) {
            safeTransferFrom(token, from, to, value);
        } else if (!token.transferFromAndCall(from, to, value, data)) {
            revert SafeERC20FailedOperation(address(token));
        }
    }

    /**
     * @dev Performs an {ERC1363} approveAndCall, with a fallback to the simple {ERC20} approve if the target has no
     * code. This can be used to implement an {ERC721}-like safe transfer that rely on {ERC1363} checks when
     * targeting contracts.
     *
     * NOTE: When the recipient address (`to`) has no code (i.e. is an EOA), this function behaves as {forceApprove}.
     * Opposedly, when the recipient address (`to`) has code, this function only attempts to call {ERC1363-approveAndCall}
     * once without retrying, and relies on the returned value to be true.
     *
     * Reverts if the returned value is other than `true`.
     */
    function approveAndCallRelaxed(IERC1363 token, address to, uint256 value, bytes memory data) internal {
        if (to.code.length == 0) {
            forceApprove(token, to, value);
        } else if (!token.approveAndCall(to, value, data)) {
            revert SafeERC20FailedOperation(address(token));
        }
    }

    /**
     * @dev Imitates a Solidity high-level call (i.e. a regular function call to a contract), relaxing the requirement
     * on the return value: the return value is optional (but if data is returned, it must not be false).
     * @param token The token targeted by the call.
     * @param data The call data (encoded using abi.encode or one of its variants).
     *
     * This is a variant of {_callOptionalReturnBool} that reverts if call fails to meet the requirements.
     */
    function _callOptionalReturn(IERC20 token, bytes memory data) private {
        uint256 returnSize;
        uint256 returnValue;
        assembly ("memory-safe") {
            let success := call(gas(), token, 0, add(data, 0x20), mload(data), 0, 0x20)
            // bubble errors
            if iszero(success) {
                let ptr := mload(0x40)
                returndatacopy(ptr, 0, returndatasize())
                revert(ptr, returndatasize())
            }
            returnSize := returndatasize()
            returnValue := mload(0)
        }

        if (returnSize == 0 ? address(token).code.length == 0 : returnValue != 1) {
            revert SafeERC20FailedOperation(address(token));
        }
    }

    /**
     * @dev Imitates a Solidity high-level call (i.e. a regular function call to a contract), relaxing the requirement
     * on the return value: the return value is optional (but if data is returned, it must not be false).
     * @param token The token targeted by the call.
     * @param data The call data (encoded using abi.encode or one of its variants).
     *
     * This is a variant of {_callOptionalReturn} that silently catches all reverts and returns a bool instead.
     */
    function _callOptionalReturnBool(IERC20 token, bytes memory data) private returns (bool) {
        bool success;
        uint256 returnSize;
        uint256 returnValue;
        assembly ("memory-safe") {
            success := call(gas(), token, 0, add(data, 0x20), mload(data), 0, 0x20)
            returnSize := returndatasize()
            returnValue := mload(0)
        }
        return success && (returnSize == 0 ? address(token).code.length > 0 : returnValue == 1);
    }
}


// File @openzeppelin/contracts/utils/Pausable.sol@v5.4.0

// Original license: SPDX_License_Identifier: MIT
// OpenZeppelin Contracts (last updated v5.3.0) (utils/Pausable.sol)

pragma solidity ^0.8.20;

/**
 * @dev Contract module which allows children to implement an emergency stop
 * mechanism that can be triggered by an authorized account.
 *
 * This module is used through inheritance. It will make available the
 * modifiers `whenNotPaused` and `whenPaused`, which can be applied to
 * the functions of your contract. Note that they will not be pausable by
 * simply including this module, only once the modifiers are put in place.
 */
abstract contract Pausable is Context {
    bool private _paused;

    /**
     * @dev Emitted when the pause is triggered by `account`.
     */
    event Paused(address account);

    /**
     * @dev Emitted when the pause is lifted by `account`.
     */
    event Unpaused(address account);

    /**
     * @dev The operation failed because the contract is paused.
     */
    error EnforcedPause();

    /**
     * @dev The operation failed because the contract is not paused.
     */
    error ExpectedPause();

    /**
     * @dev Modifier to make a function callable only when the contract is not paused.
     *
     * Requirements:
     *
     * - The contract must not be paused.
     */
    modifier whenNotPaused() {
        _requireNotPaused();
        _;
    }

    /**
     * @dev Modifier to make a function callable only when the contract is paused.
     *
     * Requirements:
     *
     * - The contract must be paused.
     */
    modifier whenPaused() {
        _requirePaused();
        _;
    }

    /**
     * @dev Returns true if the contract is paused, and false otherwise.
     */
    function paused() public view virtual returns (bool) {
        return _paused;
    }

    /**
     * @dev Throws if the contract is paused.
     */
    function _requireNotPaused() internal view virtual {
        if (paused()) {
            revert EnforcedPause();
        }
    }

    /**
     * @dev Throws if the contract is not paused.
     */
    function _requirePaused() internal view virtual {
        if (!paused()) {
            revert ExpectedPause();
        }
    }

    /**
     * @dev Triggers stopped state.
     *
     * Requirements:
     *
     * - The contract must not be paused.
     */
    function _pause() internal virtual whenNotPaused {
        _paused = true;
        emit Paused(_msgSender());
    }

    /**
     * @dev Returns to normal state.
     *
     * Requirements:
     *
     * - The contract must be paused.
     */
    function _unpause() internal virtual whenPaused {
        _paused = false;
        emit Unpaused(_msgSender());
    }
}


// File @openzeppelin/contracts/utils/ReentrancyGuard.sol@v5.4.0

// Original license: SPDX_License_Identifier: MIT
// OpenZeppelin Contracts (last updated v5.1.0) (utils/ReentrancyGuard.sol)

pragma solidity ^0.8.20;

/**
 * @dev Contract module that helps prevent reentrant calls to a function.
 *
 * Inheriting from `ReentrancyGuard` will make the {nonReentrant} modifier
 * available, which can be applied to functions to make sure there are no nested
 * (reentrant) calls to them.
 *
 * Note that because there is a single `nonReentrant` guard, functions marked as
 * `nonReentrant` may not call one another. This can be worked around by making
 * those functions `private`, and then adding `external` `nonReentrant` entry
 * points to them.
 *
 * TIP: If EIP-1153 (transient storage) is available on the chain you're deploying at,
 * consider using {ReentrancyGuardTransient} instead.
 *
 * TIP: If you would like to learn more about reentrancy and alternative ways
 * to protect against it, check out our blog post
 * https://blog.openzeppelin.com/reentrancy-after-istanbul/[Reentrancy After Istanbul].
 */
abstract contract ReentrancyGuard {
    // Booleans are more expensive than uint256 or any type that takes up a full
    // word because each write operation emits an extra SLOAD to first read the
    // slot's contents, replace the bits taken up by the boolean, and then write
    // back. This is the compiler's defense against contract upgrades and
    // pointer aliasing, and it cannot be disabled.

    // The values being non-zero value makes deployment a bit more expensive,
    // but in exchange the refund on every call to nonReentrant will be lower in
    // amount. Since refunds are capped to a percentage of the total
    // transaction's gas, it is best to keep them low in cases like this one, to
    // increase the likelihood of the full refund coming into effect.
    uint256 private constant NOT_ENTERED = 1;
    uint256 private constant ENTERED = 2;

    uint256 private _status;

    /**
     * @dev Unauthorized reentrant call.
     */
    error ReentrancyGuardReentrantCall();

    constructor() {
        _status = NOT_ENTERED;
    }

    /**
     * @dev Prevents a contract from calling itself, directly or indirectly.
     * Calling a `nonReentrant` function from another `nonReentrant`
     * function is not supported. It is possible to prevent this from happening
     * by making the `nonReentrant` function external, and making it call a
     * `private` function that does the actual work.
     */
    modifier nonReentrant() {
        _nonReentrantBefore();
        _;
        _nonReentrantAfter();
    }

    function _nonReentrantBefore() private {
        // On the first call to nonReentrant, _status will be NOT_ENTERED
        if (_status == ENTERED) {
            revert ReentrancyGuardReentrantCall();
        }

        // Any calls to nonReentrant after this point will fail
        _status = ENTERED;
    }

    function _nonReentrantAfter() private {
        // By storing the original value once again, a refund is triggered (see
        // https://eips.ethereum.org/EIPS/eip-2200)
        _status = NOT_ENTERED;
    }

    /**
     * @dev Returns true if the reentrancy guard is currently set to "entered", which indicates there is a
     * `nonReentrant` function in the call stack.
     */
    function _reentrancyGuardEntered() internal view returns (bool) {
        return _status == ENTERED;
    }
}


// File contracts/AgentVault.sol

// Original license: SPDX_License_Identifier: MIT
pragma solidity 0.8.28;
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
