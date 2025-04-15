// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title DatasetAccessAgent
 * @notice This contract allows the owner to register dataset metadata on-chain and 
 *         lets users pay a fee to request access to a dataset. The off-chain AI agent/chatbot 
 *         listens to emitted events to provide download links and further information.
 */
contract DatasetAccessAgent {
    address public owner;

    struct Dataset {
        string cid;           // Content Identifier (CID) of the dataset stored on Filecoin.
        uint256 size;         // Size of the dataset (in bytes or another unit).
        string description;   // Brief description or metadata.
        uint256 price;        // Access fee (in wei) required to request the dataset.
        bool exists;          // Flag to check if dataset exists.
    }

    // Mapping from a unique dataset ID to its details.
    mapping(string => Dataset) public datasets;
    // List of dataset IDs for enumeration (helps off-chain indexing).
    string[] public datasetIds;

    // Events to signal off-chain services.
    event DatasetAdded(
        string datasetId,
        string cid,
        uint256 size,
        string description,
        uint256 price
    );
    event DatasetAccessRequested(
        string datasetId,
        address indexed requester,
        uint256 feePaid,
        uint256 timestamp
    );
    event DatasetAccessGranted(
        string datasetId,
        address indexed requester,
        string cid,
        uint256 size,
        uint256 timestamp
    );

    modifier onlyOwner() {
        require(msg.sender == owner, "Not authorized!");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    /**
     * @notice Allows the owner to add a new dataset to the registry.
     * @param datasetId A unique identifier for the dataset.
     * @param cid The Filecoin CID for the dataset.
     * @param size The size of the dataset.
     * @param description A brief description of the dataset.
     * @param price The fee required (in wei) to access this dataset.
     */
    function addDataset(
        string calldata datasetId,
        string calldata cid,
        uint256 size,
        string calldata description,
        uint256 price
    ) external onlyOwner {
        require(!datasets[datasetId].exists, "Dataset already exists");
        datasets[datasetId] = Dataset({
            cid: cid,
            size: size,
            description: description,
            price: price,
            exists: true
        });
        datasetIds.push(datasetId);
        emit DatasetAdded(datasetId, cid, size, description, price);
    }

    /**
     * @notice Users request access to a dataset by paying the required fee.
     * @param datasetId The identifier of the dataset to access.
     */
    function requestDatasetAccess(string calldata datasetId) external payable {
        Dataset memory ds = datasets[datasetId];
        require(ds.exists, "Dataset does not exist");
        require(msg.value >= ds.price, "Insufficient fee");

        // Refund any excess amount sent.
        if (msg.value > ds.price) {
            uint256 refund = msg.value - ds.price;
            payable(msg.sender).transfer(refund);
        }

        // Emit an event for the off-chain service (AI agent/chatbot) to process.
        emit DatasetAccessRequested(datasetId, msg.sender, ds.price, block.timestamp);

        // Note: In a full implementation, off-chain services will listen to this event
        // and then, after verifying criteria or signing a verification contract,
        // may call `grantDatasetAccess` to signal that access has been approved.
    }

    /**
     * @notice (Optional) Owner can mark dataset access as granted.
     *         This function can be called after off-chain verification.
     * @param datasetId The dataset for which access is granted.
     * @param requester The user who requested access.
     */
    function grantDatasetAccess(string calldata datasetId, address requester) external onlyOwner {
        Dataset memory ds = datasets[datasetId];
        require(ds.exists, "Dataset does not exist");
        emit DatasetAccessGranted(datasetId, requester, ds.cid, ds.size, block.timestamp);
    }

    /**
     * @notice Returns the total number of registered datasets.
     */
    function getDatasetCount() external view returns (uint256) {
        return datasetIds.length;
    }

    /**
     * @notice Allows the owner to withdraw collected fees.
     */
    function withdrawFunds() external onlyOwner {
        uint256 balance = address(this).balance;
        require(balance > 0, "No funds to withdraw");
        payable(owner).transfer(balance);
    }
}
