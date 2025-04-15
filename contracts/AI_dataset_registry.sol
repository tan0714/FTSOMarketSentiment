// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

/**
 * @title AIDatasetRegistry
 * @notice This contract allows the owner to register AI dataset metadata on-chain,
 *         including a title, description, file size, CID, price, Filecoin deal ID, and a preview.
 *         It also lets users pay a fee to request access to a dataset.
 */
contract AIDatasetRegistry {
    address public owner;

    struct Dataset {
        string title;         // Title of the dataset.
        string cid;           // Content Identifier (CID) of the dataset stored on Filecoin/IPFS.
        uint256 size;         // Size of the dataset (in bytes).
        string description;   // Detailed description or metadata.
        uint256 price;        // Access fee (in wei) required to request the dataset.
        uint256 filecoinDealId; // Filecoin deal ID associated with the dataset.
        string preview;       // Preview information (e.g., key headers or summary).
        bool exists;          // Flag indicating if the dataset is registered.
    }

    // Group the input parameters to avoid too many function arguments.
    struct DataInput {
        string title;
        string cid;
        uint256 size;
        string description;
        uint256 price;
        uint256 filecoinDealId;
        string preview;
    }

    // Mapping from a unique dataset ID to its details.
    mapping(string => Dataset) public datasets;
    // Array of dataset IDs for enumeration.
    string[] public datasetIds;

    // Events to signal off-chain services.
    event DatasetAdded(
        string datasetId,
        string title,
        string cid,
        uint256 size,
        string description,
        uint256 price,
        uint256 filecoinDealId,
        string preview
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
     * @param input A struct containing the title, cid, size, description, price, filecoinDealId, and preview.
     */
    function addDataset(string calldata datasetId, DataInput calldata input) external onlyOwner {
        require(!datasets[datasetId].exists, "Dataset already exists");

        // Write directly to storage to avoid extra local variables.
        datasets[datasetId] = Dataset(
            input.title,
            input.cid,
            input.size,
            input.description,
            input.price,
            input.filecoinDealId,
            input.preview,
            true
        );
        datasetIds.push(datasetId);

        // Read from storage (only one local pointer) for event emission.
        Dataset storage ds = datasets[datasetId];
        emit DatasetAdded(datasetId, ds.title, ds.cid, ds.size, ds.description, ds.price, ds.filecoinDealId, ds.preview);
    }

    /**
     * @notice Users request access to a dataset by paying the required fee.
     * @param datasetId The identifier of the dataset to access.
     */
    function requestDatasetAccess(string calldata datasetId) external payable {
        Dataset memory ds = datasets[datasetId];
        require(ds.exists, "Dataset does not exist");
        require(msg.value >= ds.price, "Insufficient fee");

        // Refund any excess amount.
        if (msg.value > ds.price) {
            uint256 refund = msg.value - ds.price;
            payable(msg.sender).transfer(refund);
        }
        emit DatasetAccessRequested(datasetId, msg.sender, ds.price, block.timestamp);
    }

    /**
     * @notice (Optional) Allows the owner to mark dataset access as granted.
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
