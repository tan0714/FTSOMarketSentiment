// SPDX-License-Identifier: MIT
pragma solidity ^0.8.22;

import "@openzeppelin/contracts/governance/TimelockController.sol";

contract MyTimelockController is TimelockController {
    /**
     * @notice Constructor for the TimelockController.
     * @param minDelay The minimum delay before an operation can be executed.
     * @param proposers The list of addresses that can propose operations.
     * @param executors The list of addresses that can execute operations.
     */
    constructor(
        uint256 minDelay,
        address[] memory proposers,
        address[] memory executors
    )
        TimelockController(minDelay, proposers, executors, msg.sender)
    {}
}
