// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract CertiChain {
    struct Certificate {
        string ipfsHash;
        string recipientName;
        uint256 issueDate;
        bool exists;
    }

    mapping(bytes32 => Certificate) public certificates;
    address public owner;

    event CertificateIssued(bytes32 indexed certificateId, string recipientName, uint256 issueDate);

    constructor() {
        owner = msg.sender;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Not authorized");
        _;
    }

    function issueCertificate(
        bytes32 _certificateId,
        string memory _ipfsHash,
        string memory _recipientName
    ) public onlyOwner {
        require(!certificates[_certificateId].exists, "Certificate already exists");
        certificates[_certificateId] = Certificate(_ipfsHash, _recipientName, block.timestamp, true);
        emit CertificateIssued(_certificateId, _recipientName, block.timestamp);
    }

    function getCertificate(bytes32 _certificateId)
        public view
        returns (string memory ipfsHash, string memory recipientName, uint256 issueDate)
    {
        Certificate memory cert = certificates[_certificateId];
        return (cert.ipfsHash, cert.recipientName, cert.issueDate);
    }

    function verifyCertificate(bytes32 _certificateId) public view returns (bool) {
        return certificates[_certificateId].exists;
    }
}
