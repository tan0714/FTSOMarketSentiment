// SPDX-License-Identifier: MIT
pragma solidity ^0.8.22;

import {Governor} from "@openzeppelin/contracts/governance/Governor.sol";
import {GovernorCountingSimple} from "@openzeppelin/contracts/governance/extensions/GovernorCountingSimple.sol";
import {GovernorSettings} from "@openzeppelin/contracts/governance/extensions/GovernorSettings.sol";
import {GovernorTimelockControl} from "@openzeppelin/contracts/governance/extensions/GovernorTimelockControl.sol";
import {GovernorVotes} from "@openzeppelin/contracts/governance/extensions/GovernorVotes.sol";
import {GovernorVotesQuorumFraction} from "@openzeppelin/contracts/governance/extensions/GovernorVotesQuorumFraction.sol";
import {IVotes} from "@openzeppelin/contracts/governance/utils/IVotes.sol";
import {TimelockController} from "@openzeppelin/contracts/governance/TimelockController.sol";

contract TruthAnchorGovernor is Governor, GovernorSettings, GovernorCountingSimple, GovernorVotes, GovernorVotesQuorumFraction, GovernorTimelockControl {

    // Struct to store the Twitter handle and vote counts
    struct TwitterProposal {
        string twitterHandle;
        uint256 forVotes;
        uint256 againstVotes;
        uint256 abstainVotes;
    }

    // Mapping from proposal ID to our TwitterProposal details
    mapping(uint256 => TwitterProposal) public twitterProposals;

    constructor(IVotes _token, TimelockController _timelock)
        Governor("TruthAnchorGovernor")
        GovernorSettings(21600 /* 3 days */, 50400 /* 1 week */, 5e18)
        GovernorVotes(_token)
        GovernorVotesQuorumFraction(50)
        GovernorTimelockControl(_timelock)
    {}

    // A no-op function that serves as the target of our dummy call.
    // This is necessary because the Governor's propose() function requires at least one action.
    function noop() external pure {}

    /**
     * @notice Propose a new Twitter handle.
     * @param _twitterHandle The Twitter handle (as a string) proposed for people to follow.
     * @return proposalId The ID of the created proposal.
     */
    function proposeTwitterHandle(string memory _twitterHandle) public returns (uint256) {
        // Prepare a single dummy action calling our no-op function.
        address[] memory targets = new address[](1);
        targets[0] = address(this);
        uint256[] memory values = new uint256[](1);
        values[0] = 0;
        bytes[] memory calldatas = new bytes[](1);
        calldatas[0] = abi.encodeWithSelector(this.noop.selector);
        
        // Create a description that includes the Twitter handle.
        string memory description = string(abi.encodePacked("Proposal for Twitter handle: ", _twitterHandle));
        
        // Create the proposal using the inherited propose() function.
        uint256 proposalId = propose(targets, values, calldatas, description);

        // Store the Twitter handle and initialize vote counts.
        twitterProposals[proposalId] = TwitterProposal(_twitterHandle, 0, 0, 0);

        return proposalId;
    }

    /**
     * @dev Override _countVote so we can update our mapping with the vote weights.
     * The parent's _countVote now expects an extra parameter `params` and returns a uint256.
     */
    function _countVote(
        uint256 proposalId,
        address account,
        uint8 support,
        uint256 weight,
        bytes memory params
    ) internal override(Governor, GovernorCountingSimple) returns (uint256) {
        // Call the parent function to update internal vote count.
        super._countVote(proposalId, account, support, weight, params);

        // Update our TwitterProposal vote counts.
        if (support == 0) { // Against vote
            twitterProposals[proposalId].againstVotes += weight;
        } else if (support == 1) { // For vote
            twitterProposals[proposalId].forVotes += weight;
        } else if (support == 2) { // Abstain vote
            twitterProposals[proposalId].abstainVotes += weight;
        }
        // Return a value to satisfy the parent's return type. Adjust if needed.
        return 0;
    }

    // ------------------ Standard Governor overrides ------------------

    function votingDelay()
        public
        view
        override(Governor, GovernorSettings)
        returns (uint256)
    {
        return super.votingDelay();
    }

    function votingPeriod()
        public
        view
        override(Governor, GovernorSettings)
        returns (uint256)
    {
        return super.votingPeriod();
    }

    function quorum(uint256 blockNumber)
        public
        view
        override(Governor, GovernorVotesQuorumFraction)
        returns (uint256)
    {
        return super.quorum(blockNumber);
    }

    function state(uint256 proposalId)
        public
        view
        override(Governor, GovernorTimelockControl)
        returns (ProposalState)
    {
        return super.state(proposalId);
    }

    function proposalNeedsQueuing(uint256 proposalId)
        public
        view
        override(Governor, GovernorTimelockControl)
        returns (bool)
    {
        return super.proposalNeedsQueuing(proposalId);
    }

    function proposalThreshold()
        public
        view
        override(Governor, GovernorSettings)
        returns (uint256)
    {
        return super.proposalThreshold();
    }

    function _queueOperations(
        uint256 proposalId,
        address[] memory targets,
        uint256[] memory values,
        bytes[] memory calldatas,
        bytes32 descriptionHash
    )
        internal
        override(Governor, GovernorTimelockControl)
        returns (uint48)
    {
        return super._queueOperations(proposalId, targets, values, calldatas, descriptionHash);
    }

    function _executeOperations(
        uint256 proposalId,
        address[] memory targets,
        uint256[] memory values,
        bytes[] memory calldatas,
        bytes32 descriptionHash
    )
        internal
        override(Governor, GovernorTimelockControl)
    {
        super._executeOperations(proposalId, targets, values, calldatas, descriptionHash);
    }

    function _cancel(
        address[] memory targets,
        uint256[] memory values,
        bytes[] memory calldatas,
        bytes32 descriptionHash
    )
        internal
        override(Governor, GovernorTimelockControl)
        returns (uint256)
    {
        return super._cancel(targets, values, calldatas, descriptionHash);
    }

    function _executor()
        internal
        view
        override(Governor, GovernorTimelockControl)
        returns (address)
    {
        return super._executor();
    }
}
