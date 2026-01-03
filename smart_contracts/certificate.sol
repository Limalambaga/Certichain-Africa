// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract CertificateRegistry {
    struct Certificate {
        string ipfsHash;
        string recipientName;
        uint256 issueDate;
        bool exists;
    }

    mapping(bytes32 => Certificate) public certificates;

    event CertificateIssued(
        bytes32 indexed certificateId,
        string ipfsHash,
        string recipientName,
        uint256 issueDate
    );

    function issueCertificate(
        bytes32 _certificateId,
        string memory _ipfsHash,
        string memory _recipientName
    ) public {
        require(!certificates[_certificateId].exists, "Certificate already exists");

        certificates[_certificateId] = Certificate({
            ipfsHash: _ipfsHash,
            recipientName: _recipientName,
            issueDate: block.timestamp,
            exists: true
        });

        emit CertificateIssued(_certificateId, _ipfsHash, _recipientName, block.timestamp);
    }

    function verifyCertificate(bytes32 _certificateId) public view returns (bool) {
        return certificates[_certificateId].exists;
    }

    function getCertificate(bytes32 _certificateId)
        public
        view
        returns (
            string memory ipfsHash,
            string memory recipientName,
            uint256 issueDate
        )
    {
        require(certificates[_certificateId].exists, "Certificate not found");
        Certificate memory cert = certificates[_certificateId];
        return (cert.ipfsHash, cert.recipientName, cert.issueDate);
    }
}