"""
ZAO Addresses Data File

This file contains the known Ethereum addresses and ENS names for the ZAO token leaderboard.
"""

# Known addresses mapped to display names for the leaderboard
KNOWN_ADDRESSES = {
    # Core team and known community members
    "0x7234c36A71ec237c2Ae7698e8916e0735001E9Af": "Zaal (Founder)",
    "0x65284960d4eAdaf45e923430A59B7D3Bf34dB641": "Prizem (Community)",
    "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045": "Vitalik Buterin",
    "0xb8c2C29ee19D8307cb7255e1Cd9CbDE883A267d5": "Nick Johnson (ENS)",
    "0x983110309620D911731Ac0932219af06091b6744": "Brantly Millegan (ENS)",
    "0x5555763613a12D8F3e73be831DFf8598089d3dCa": "Richard Moore (ethers.js)",
    "0x8ba1f109551bD432803012645Ac136ddd64DBA72": "Optimism Multisig",
    "0x2431CBdc0792F5485c4cb0a9bEf06C4f21541D52": "Songbird (Community)",
    "0xFCf77aC2CeF5eB373d8eb9163f518126ccE44f47": "Songs of Eden",
    "0xf15Dab6530100a1e26Ad41cEB4C18d869B594Cb1": "Optimism Foundation",
    "0x1a9C8182C09F50C8318d769245beA52c32BE35BC": "Uniswap",
    
    # Add more known addresses here as needed
}

# ENS names mapped to addresses (for quick lookup)
ENS_ADDRESSES = {
    # Original ENS names
    "zaal.eth": "0x7234c36A71ec237c2Ae7698e8916e0735001E9Af",
    "vitalik.eth": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
    "nick.eth": "0xb8c2C29ee19D8307cb7255e1Cd9CbDE883A267d5",
    "brantly.eth": "0x983110309620D911731Ac0932219af06091b6744",
    "ricmoo.eth": "0x5555763613a12D8F3e73be831DFf8598089d3dCa",
    
    # Prizem's ENS names
    "earlygirl.eth": "0x65284960d4eAdaf45e923430A59B7D3Bf34dB641",
    "prizem.eth": "0x65284960d4eAdaf45e923430A59B7D3Bf34dB641",
    
    # Songs of Eden ENS name
    "songsofeden.eth": "0xFCf77aC2CeF5eB373d8eb9163f518126ccE44f47",
    
    # Additional popular ENS names
    "optimism.eth": "0xf15Dab6530100a1e26Ad41cEB4C18d869B594Cb1",
    "uniswap.eth": "0x1a9C8182C09F50C8318d769245beA52c32BE35BC"
}
