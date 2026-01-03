window.addEventListener('DOMContentLoaded', () => {
  if (typeof window.ethereum !== 'undefined') {
    console.log('MetaMask is installed!');
  } else {
    alert("⚠️ Please install MetaMask to interact on-chain.");
  }
});