// V2 Contract for Filecoin Testnet (TFIL)!  
// TFIL deposits tracked & logged for backend execution—NO direct swaps!!!  
// Users deposit TFIL, backend handles item payout post-validation.  

// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract FileFindTFIL {
    address public owner;

    /// @notice Logs TFIL deposits! Backend listens to this event.
    /// @param tfilAmount Amount deposited.
    /// @param depositor Who deposited.
    /// @param recipient Where ARB should go.
    /// @param proof Extra security parameter (optional).
    event DepositProcessed(
        uint256 tfilAmount,
        address indexed depositor,
        address indexed recipient,
        bytes proof
    );

    modifier onlyOwner() {
        require(msg.sender == owner, "Not authorized!");
        _;
    }

    /// @notice Contract initialized with owner.
    constructor() {
        owner = msg.sender;
    }

    /// @notice Users deposit TFIL—backend listens to the event logs.
    /// @param recipient Where send item should go.
    /// @param proof Extra validation data (optional).
    function depositTFIL(address recipient, bytes calldata proof) external payable {
        require(msg.value > 0, "Invalid amount!");
        require(recipient != address(0), "Invalid recipient!");

        // Emit event so backend can process the deposit.
        emit DepositProcessed(msg.value, msg.sender, recipient, proof);
    }

    /// @notice Allows the owner to withdraw any TFIL stuck in the contract.
    function withdrawFunds() external onlyOwner {
        uint256 balance = address(this).balance;
        require(balance > 0, "No funds to withdraw!");

        // Send TFIL to the owner.
        (bool success, ) = owner.call{value: balance}("");
        require(success, "TFIL transfer failed!");
    }

    /// @notice Enables the contract to receive TFIL.
    receive() external payable {}
}
