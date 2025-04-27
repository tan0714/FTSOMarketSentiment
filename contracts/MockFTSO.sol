// SPDX-License-Identifier: MIT
pragma solidity ^0.8.25;

/// exactly your ITwitterFTSO interface
interface ITwitterFTSO {
    function tweetScore() external view returns (uint256);
}

/// a very simple “FTSO”
/// – owner (keeper) can call setTweetScore to push a new 0–100 value  
/// – anyone can read tweetScore()
contract MockTwitterFTSO is ITwitterFTSO {
    uint256 private _tweetScore;
    address public keeper;

    modifier onlyKeeper() {
        require(msg.sender == keeper, "MockTwitterFTSO: not keeper");
        _;
    }

    constructor(address _keeper) {
        keeper = _keeper;
    }

    /// @notice keeper sets new sentiment score in 0–100
    function setTweetScore(uint256 s) external onlyKeeper {
        require(s <= 100, "out of range");
        _tweetScore = s;
    }

    /// @notice read the latest score
    function tweetScore() external view override returns (uint256) {
        return _tweetScore;
    }
}
