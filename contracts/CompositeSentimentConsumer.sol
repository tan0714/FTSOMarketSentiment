// SPDX-License-Identifier: MIT
pragma solidity ^0.8.25;

import {ContractRegistry} from "@flarenetwork/flare-periphery-contracts/coston/ContractRegistry.sol";
import {IJsonApi}        from "@flarenetwork/flare-periphery-contracts/coston/IJsonApi.sol";

interface ITwitterFTSO {
    function tweetScore() external view returns (uint256);  // 0–100 scale
}

contract CompositeSentimentConsumer {
    ITwitterFTSO public immutable twitterOracle;
    uint256 public lastComposite;  // 18-decimals fixed

    constructor(ITwitterFTSO _twitterOracle) {
        twitterOracle = _twitterOracle;
    }

    /// @param macroData abi.encode(uint256 macroScore) where 0–100 scale
    function updateComposite(IJsonApi.Proof calldata macroData) external {
        require(_verifyJson(macroData), "Invalid macro proof");

        uint256 tweetScore = twitterOracle.tweetScore();      // [0,100]
        uint256 macroScore = abi.decode(macroData.data.responseBody.abi_encoded_data, (uint256)); // [0,100]

        // Example weighting: 70% social, 30% macro
        uint256 weighted = (tweetScore * 70 + macroScore * 30) / 100;

        // Scale to 1e18
        lastComposite = weighted * 1e16;

        emit CompositeUpdated(tweetScore, macroScore, lastComposite);
    }

    event CompositeUpdated(uint256 tweetScore, uint256 macroScore, uint256 composite);
    
    function _verifyJson(IJsonApi.Proof calldata proof) internal view returns (bool) {
        return ContractRegistry.auxiliaryGetIJsonApiVerification().verifyJsonApi(proof);
    }
}
