// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/security/Pausable.sol";
import "@openzeppelin/contracts/utils/structs/EnumerableSet.sol";
import { IPriceSubmitter } from "./interfaces/IPriceSubmitter.sol";
import { IFtsoRegistry }   from "./interfaces/IFtsoRegistry.sol";

contract PricePredictorOracle is AccessControl, Pausable {
    using EnumerableSet for EnumerableSet.Bytes32Set;

    /// @dev Roles
    bytes32 public constant KEEPER_ROLE = keccak256("KEEPER_ROLE");

    /// @notice Address of the FTSO price submitter on Coston 2
    address private constant PRICE_SUBMITTER =
        0x1000000000000000000000000000000000000003;

    /// @notice Maximum age of a price update before it is considered stale
    uint256 public constant MAX_STALE = 5 minutes;

    /// @notice Enforced list of active symbols (bytes32)
    EnumerableSet.Bytes32Set private _symbols;

    /// @notice Cached feeds
    struct Feed { uint256 price; uint256 ts; }
    mapping(bytes32 => Feed) private _cache;

    /// @notice Emitted when keeper updates the on-chain cache
    event CachedFeedsUpdated(bytes32[] symbols, uint256[] prices, uint256[] timestamps);

    constructor(address keeper) {
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(KEEPER_ROLE, keeper);
    }

    /// @dev Helper to fetch the registry instance
    function _registry() internal view returns (IFtsoRegistry) {
        return IFtsoRegistry(
            IPriceSubmitter(PRICE_SUBMITTER).getFtsoRegistry()
        );
    }

    /// @notice Add a new symbol to track (must be ≤32 bytes UTF-8)
    function addSymbol(bytes32 symbol) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(_symbols.add(symbol), "already tracked");
    }

    /// @notice Remove a symbol
    function removeSymbol(bytes32 symbol) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(_symbols.remove(symbol), "not tracked");
    }

    /// @notice Pause updates (e.g. emergency)
    function pause() external onlyRole(DEFAULT_ADMIN_ROLE) {
        _pause();
    }

    /// @notice Unpause
    function unpause() external onlyRole(DEFAULT_ADMIN_ROLE) {
        _unpause();
    }

    /**
     * @notice Keeper function: fetch all FTSO feeds and cache them.
     *         Reverts if any price is zero or stale.
     */
    function updateCachedFeeds() external whenNotPaused onlyRole(KEEPER_ROLE) {
        uint256 len = _symbols.length();
        require(len > 0, "no symbols");

        bytes32[] memory syms = _symbols.values();
        uint256[] memory prices = new uint256[](len);
        uint256[] memory timestamps = new uint256[](len);

        for (uint256 i = 0; i < len; i++) {
            // convert bytes32→string
            string memory s = _bytes32ToString(syms[i]);
            (uint256 rawPrice, uint256 ts, uint256 dec) =
                _registry().getCurrentPriceWithDecimals(s);

            require(rawPrice > 0, "zero price");
            require(block.timestamp - ts <= MAX_STALE, "stale price");

            // normalize → 18 decimals
            uint256 p18 = rawPrice * (10**(18 - dec));
            _cache[syms[i]] = Feed({ price: p18, ts: ts });

            prices[i] = p18;
            timestamps[i] = ts;
        }

        emit CachedFeedsUpdated(syms, prices, timestamps);
    }

    /// @notice View-only: get one symbol’s last cached price and timestamp
    function getCachedPrice(bytes32 symbol) external view returns (uint256 price, uint256 timestamp) {
        Feed storage f = _cache[symbol];
        require(f.price > 0, "never updated");
        return (f.price, f.ts);
    }

    /// @notice View-only: fetch the entire current cache
    function getAllCached() external view returns (bytes32[] memory symbols, uint256[] memory prices, uint256[] memory timestamps) {
        uint256 len = _symbols.length();
        symbols   = _symbols.values();
        prices    = new uint256[](len);
        timestamps= new uint256[](len);

        for (uint256 i = 0; i < len; i++) {
            Feed storage f = _cache[symbols[i]];
            prices[i] = f.price;
            timestamps[i] = f.ts;
        }
    }

    /// @dev Internal helper: bytes32 → string (trims zeroes)
    function _bytes32ToString(bytes32 _b) internal pure returns (string memory) {
        uint8 len = 0;
        while (len < 32 && _b[len] != 0) { len++; }
        bytes memory tmp = new bytes(len);
        for (uint8 i = 0; i < len; i++) {
            tmp[i] = _b[i];
        }
        return string(tmp);
    }
}
