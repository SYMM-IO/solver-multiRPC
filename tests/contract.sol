// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.9;

contract Mapping {
    mapping(address => uint256) public map;

    function set(uint256 value) public {
        // Revert if the input is exactly one byte of 0x00
        require(
            value >= 10,
            "Error: 10 < value is not allowed."
        );

        map[msg.sender] = value;
    }
}