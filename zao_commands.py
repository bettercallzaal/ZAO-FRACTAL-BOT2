import discord
from discord import app_commands
from discord.ext import commands
import os
import aiohttp
from dotenv import load_dotenv
import json
import pickle
from datetime import datetime
import asyncio
from typing import Optional, Dict, List, Tuple
import hashlib

# Import the ENS addresses from zao_addresses.py
from zao_addresses import KNOWN_ADDRESSES, ENS_ADDRESSES

try:
    from alchemy import Alchemy, Network
    ALCHEMY_SDK_AVAILABLE = True
except ImportError:
    ALCHEMY_SDK_AVAILABLE = False

# Load environment variables
load_dotenv()

# ZAO token contract address on Optimism
ZAO_TOKEN_ADDRESS = "0x34cE89baA7E4a4B00E17F7E4C0cb97105C216957"

# Alchemy API URL and key for Optimism (hardcoded as provided)
ALCHEMY_API_KEY = "3HPGRn6bvILV-WjQhagIky4E5I4vsLDW"
ALCHEMY_API_URL = f"https://opt-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}"

# Alchemy API URL for Ethereum mainnet (for ENS resolution)
ALCHEMY_ETH_MAINNET_URL = f"https://eth-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}"

# ENS resolution cache to avoid repeated lookups
ens_cache = {}

# Reverse cache for address to ENS name resolution
reverse_ens_cache = {}

# ENS Public Resolver ABI (minimal for name resolution)
ENS_PUBLIC_RESOLVER_ABI = [
    {
        "constant": True,
        "inputs": [
            {
                "name": "node",
                "type": "bytes32"
            }
        ],
        "name": "addr",
        "outputs": [
            {
                "name": "",
                "type": "address"
            }
        ],
        "type": "function"
    }
]

class ZAOCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.user_addresses = {}
        self.load_user_addresses()
        
    def load_user_addresses(self):
        """Load user addresses from pickle file"""
        try:
            with open('user_addresses.pkl', 'rb') as f:
                self.user_addresses = pickle.load(f)
        except FileNotFoundError:
            self.user_addresses = {}
        
    def save_user_addresses(self):
        """Save user addresses to pickle file"""
        with open('user_addresses.pkl', 'wb') as f:
            pickle.dump(self.user_addresses, f)
    
    async def resolve_ens_name(self, ens_name) -> Tuple[str, str]:
        """Resolve an ENS name to an Ethereum address using multiple methods
        
        Returns:
            Tuple[str, str]: (address, error_message). If successful, address will be returned and error_message will be None.
            If unsuccessful, address will be None and error_message will contain the error.
        """
        print(f"Attempting to resolve ENS name: {ens_name}")
        
        # Check cache first
        if ens_name in ens_cache:
            print(f"Found {ens_name} in cache: {ens_cache[ens_name]}")
            return ens_cache[ens_name], None
        
        # Ensure the ENS name is properly formatted
        if not ens_name.endswith('.eth'):
            ens_name = f"{ens_name}.eth"
        
        # First check the imported ENS_ADDRESSES dictionary for quick lookup
        if ens_name.lower() in ENS_ADDRESSES:
            address = ENS_ADDRESSES[ens_name.lower()]
            print(f"Found {ens_name} in ENS_ADDRESSES: {address}")
            ens_cache[ens_name] = address
            return address, None
        
        # Method 1: Use ENS Public Resolver directly via ethers.js style resolution
        # This is the most reliable method for ENS resolution
        try:
            # Use a direct JSON-RPC call to resolve the ENS name
            # This is similar to how ethers.js resolves ENS names
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "eth_call",
                "params": [
                    {
                        "to": "0x4976fb03c32e5b8cfe2b6ccb31c09ba78ebaba41",  # ENS Public Resolver
                        "data": f"0x3b3b57de{Web3.keccak(text=ens_name).hex()[2:].zfill(64)}"
                    },
                    "latest"
                ]
            }
            
            print(f"Resolving {ens_name} using direct ENS Public Resolver call")
            async with aiohttp.ClientSession() as session:
                async with session.post(ALCHEMY_ETH_MAINNET_URL, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        if "result" in data and data["result"] and data["result"] != "0x" and data["result"] != "0x0000000000000000000000000000000000000000000000000000000000000000":
                            # Extract the address from the result
                            address = "0x" + data["result"][26:66]
                            print(f"✅ Resolved {ens_name} to {address} using ENS Public Resolver")
                            ens_cache[ens_name] = address
                            return address, None
                        else:
                            print(f"ENS Public Resolver returned no result for {ens_name}")
        except Exception as e:
            print(f"Error using ENS Public Resolver: {str(e)}")
            
        # Method 2: Use web3.py's built-in ENS resolution
        try:
            from web3 import Web3
            w3 = Web3(Web3.HTTPProvider(ALCHEMY_ETH_MAINNET_URL))
            address = w3.ens.address(ens_name)
            if address:
                print(f"✅ Resolved {ens_name} to {address} using web3.py")
                ens_cache[ens_name] = address
                return address, None
            else:
                print(f"No address found for {ens_name} using web3.py")
        except ImportError:
            print("web3.py not installed, trying alternative methods")
        except Exception as e:
            print(f"Error resolving ENS name with web3.py: {str(e)}")
            # Continue to fallback methods
        
        # Try multiple fallback methods to resolve the ENS name
        # 1. First try Alchemy's dedicated ENS resolution endpoint
        try:
            payload = {
                "jsonrpc": "2.0",
                "method": "eth_resolveName",
                "params": [ens_name],
                "id": 1
            }
            
            print(f"Sending Alchemy API request to resolve {ens_name}")
            async with aiohttp.ClientSession() as session:
                async with session.post(ALCHEMY_ETH_MAINNET_URL, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        if "result" in data and data["result"] is not None:
                            address = data["result"]
                            print(f"✅ Resolved {ens_name} to {address} using Alchemy API")
                            ens_cache[ens_name] = address
                            return address, None
                        else:
                            print(f"Alchemy API returned no result for {ens_name}")
        except Exception as alchemy_error:
            print(f"Error using Alchemy for ENS resolution: {alchemy_error}")
            
        # 2. Try using a different Alchemy endpoint method
        try:
            # Use Alchemy's eth_call method as another approach
            ens_registry_address = "0x00000000000C2E074eC69A0dFb2997BA6C7d2e1e"  # ENS Registry contract
            # Function signature for 'resolver(bytes32)'
            resolver_sig = "0x0178b8bf"
            # Convert ENS name to namehash
            from eth_utils import keccak
            from eth_abi import encode_single
            
            # Simple implementation of namehash
            def namehash(name):
                if name == '':
                    return bytes([0] * 32)
                label, _, remainder = name.partition('.')
                return keccak(namehash(remainder) + keccak(label.encode('utf-8')))
            
            name_hash = namehash(ens_name).hex()
            
            # First get the resolver for this name
            resolver_data = resolver_sig + name_hash[2:].rjust(64, '0')
            
            resolver_payload = {
                "jsonrpc": "2.0",
                "method": "eth_call",
                "params": [{
                    "to": ens_registry_address,
                    "data": resolver_data
                }, "latest"],
                "id": 2
            }
            
            print(f"Trying alternative Alchemy method for {ens_name}")
            async with aiohttp.ClientSession() as session:
                async with session.post(ALCHEMY_ETH_MAINNET_URL, json=resolver_payload) as response:
                    if response.status == 200:
                        resolver_result = await response.json()
                        if "result" in resolver_result and resolver_result["result"] != "0x" and resolver_result["result"] != "0x0000000000000000000000000000000000000000000000000000000000000000":
                            resolver_address = "0x" + resolver_result["result"][26:66]
                            
                            # Now get the address from the resolver
                            # Function signature for 'addr(bytes32)'
                            addr_sig = "0x3b3b57de"
                            addr_data = addr_sig + name_hash[2:].rjust(64, '0')
                            
                            addr_payload = {
                                "jsonrpc": "2.0",
                                "method": "eth_call",
                                "params": [{
                                    "to": resolver_address,
                                    "data": addr_data
                                }, "latest"],
                                "id": 3
                            }
                            
                            async with session.post(ALCHEMY_ETH_MAINNET_URL, json=addr_payload) as addr_response:
                                if addr_response.status == 200:
                                    addr_result = await addr_response.json()
                                    if "result" in addr_result and addr_result["result"] != "0x" and addr_result["result"] != "0x0000000000000000000000000000000000000000000000000000000000000000":
                                        address = "0x" + addr_result["result"][26:66]
                                        print(f"✅ Resolved {ens_name} to {address} using alternative Alchemy method")
                                        ens_cache[ens_name] = address
                                        return address, None
        except Exception as alchemy_alt_error:
            print(f"Error using alternative Alchemy method: {alchemy_alt_error}")
            
        # 3. Try using ENS Graph API as another fallback
        try:
            # The Graph API endpoint for ENS
            url = "https://api.thegraph.com/subgraphs/name/ensdomains/ens"
            
            # Query to find information about this name
            query = """
            {
              domains(where: {name: "%s"}) {
                id
                name
                resolver {
                  addr {
                    id
                  }
                }
              }
            }
            """ % ens_name
            
            print(f"Trying ENS Graph API for {ens_name}")
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json={"query": query}) as response:
                    if response.status == 200:
                        graph_data = await response.json()
                        
                        if "data" in graph_data and "domains" in graph_data["data"]:
                            domains = graph_data["data"]["domains"]
                            
                            if domains and len(domains) > 0:
                                domain = domains[0]
                                if "resolver" in domain and domain["resolver"] and "addr" in domain["resolver"] and domain["resolver"]["addr"]:
                                    address = domain["resolver"]["addr"]["id"]
                                    print(f"✅ Resolved {ens_name} to {address} using Graph API")
                                    ens_cache[ens_name] = address
                                    return address, None
        except Exception as graph_error:
            print(f"Error using Graph API fallback: {graph_error}")
        
        # If we get here, we couldn't resolve the ENS name using any method
        # Add the ENS name to the list of names to add to the database
        print(f"⚠️ Could not resolve ENS name: {ens_name}. Adding to list of names to add to the database.")
        try:
            with open('ens_names_to_add.txt', 'a') as f:
                f.write(f"{ens_name}\n")
        except Exception as file_error:
            print(f"Error writing to ens_names_to_add.txt: {file_error}")
        
        return None, f"Could not resolve ENS name: {ens_name}. Please check that the name is correct and try again. This name has been added to our list for future inclusion."
    
    async def reverse_resolve_address(self, address: str) -> Tuple[str, str]:
        """Resolve an Ethereum address to an ENS name (reverse resolution) using web3.py
        
        Args:
            address: The Ethereum address to resolve
            
        Returns:
            Tuple[str, str]: (ens_name, error_message). If successful, ens_name will be returned and error_message will be None.
            If unsuccessful, ens_name will be None and error_message will contain the error.
        """
        # Check cache first
        if address.lower() in reverse_ens_cache:
            return reverse_ens_cache[address.lower()], None
            
        # Check if the address is in our known addresses list
        # This is a quick way to get a human-readable name without ENS lookup
        if address.lower() in [addr.lower() for addr in KNOWN_ADDRESSES]:
            for addr, name in KNOWN_ADDRESSES.items():
                if addr.lower() == address.lower():
                    return name, None
        
        # Check if this address is in our ENS_ADDRESSES mapping (reverse lookup)
        for ens_name, addr in ENS_ADDRESSES.items():
            if addr.lower() == address.lower():
                reverse_ens_cache[address.lower()] = ens_name
                return ens_name, None
        
        # Use web3.py's built-in ENS reverse resolution
        try:
            from web3 import Web3
            w3 = Web3(Web3.HTTPProvider(ALCHEMY_ETH_MAINNET_URL))
            ens_name = w3.ens.name(address)
            if ens_name:
                print(f"Resolved address {address} to ENS name {ens_name} using web3.py")
                reverse_ens_cache[address.lower()] = ens_name
                return ens_name, None
            else:
                print(f"No ENS name found for address {address} using web3.py")
        except ImportError:
            print("web3.py not installed, trying alternative methods")
            return None, "web3.py library not installed. Please install it with 'pip install web3'"
        except Exception as e:
            print(f"Error in reverse ENS resolution with web3.py: {e}")
            
            # Fallback to direct API call if web3.py fails
            try:
                # Use Alchemy's dedicated ENS reverse resolution endpoint
                payload = {
                    "jsonrpc": "2.0",
                    "method": "eth_getEnsName",
                    "params": [address],
                    "id": 1
                }
                
                print(f"Sending API request for reverse resolution of {address}")
                async with aiohttp.ClientSession() as session:
                    async with session.post(ALCHEMY_ETH_MAINNET_URL, json=payload) as response:
                        if response.status == 200:
                            data = await response.json()
                            if "result" in data and data["result"] is not None:
                                ens_name = data["result"]
                                print(f"Resolved address {address} to ENS name {ens_name} using API")
                                reverse_ens_cache[address.lower()] = ens_name
                                return ens_name, None
            except Exception as fallback_error:
                print(f"Error in fallback reverse ENS resolution: {fallback_error}")
        
        return None, f"No ENS name found for address: {address}"

    async def get_token_balance(self, address):
        """Get ZAO token balance for an Ethereum address using Alchemy API"""
        try:
            # Check if this is an ENS name
            if address.lower().endswith('.eth'):
                resolved_address, error = await self.resolve_ens_name(address)
                if resolved_address:
                    address = resolved_address
                else:
                    return None, error
            
            # Validate Ethereum address format
            if not address.startswith('0x') or len(address) != 42:
                return None, f"Invalid Ethereum address format: {address}"
            
            # Use Alchemy API to get token balance via JSON-RPC
            # This uses the ERC20 balanceOf method with the token contract
            
            # Function signature for balanceOf(address)
            function_signature = "0x70a08231"
            # Pad the address to 32 bytes (remove 0x prefix, then pad with zeros)
            padded_address = address[2:].rjust(64, '0')
            # Combine to create the data parameter
            data = function_signature + padded_address
            
            # Create the JSON-RPC request
            payload = {
                "jsonrpc": "2.0",
                "method": "eth_call",
                "params": [
                    {
                        "to": ZAO_TOKEN_ADDRESS,
                        "data": data
                    },
                    "latest"
                ],
                "id": 1
            }
            
            # Send the request to Alchemy
            async with aiohttp.ClientSession() as session:
                async with session.post(ALCHEMY_API_URL, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        if "result" in data:
                            # Convert hex result to integer
                            balance_wei = int(data["result"], 16)
                            # Convert from wei to tokens (assuming 18 decimals)
                            balance = balance_wei / (10 ** 18)
                            return balance, None
                        else:
                            return None, f"API Error: {data.get('error', {}).get('message', 'Unknown error')}"
                    else:
                        return None, f"HTTP Error: {response.status}"
        except Exception as e:
            return None, f"Error getting token balance: {str(e)}"
    
    @app_commands.command(name="zao", description="Check ZAO token balance for an Ethereum address or ENS name")
    async def zao_balance(self, interaction: discord.Interaction, address: str = None):
        """Check ZAO token balance for an Ethereum address or ENS name"""
        await interaction.response.defer(thinking=True)
        
        # If no address provided, check if user has a registered address
        if not address:
            user_id = str(interaction.user.id)
            if user_id in self.user_addresses:
                address = self.user_addresses[user_id]['address']
            else:
                await interaction.followup.send("Please provide an Ethereum address or ENS name, or register one with `/register_address`. Example: `/zao 0x1234...` or `/zao name.eth`")
                return
        
        original_input = address
        display_name = None
        
        # Clean up the address input - handle common typos
        if ',' in address and not address.startswith('0x'):
            # Replace comma with period (common typo in ENS names)
            fixed_address = address.replace(',', '.')
            print(f"Fixed typo in ENS name: {address} -> {fixed_address}")
            address = fixed_address
        
        # If this looks like an ENS name (ends with .eth or contains a period)
        if address.lower().endswith('.eth') or ('.' in address and not address.startswith('0x')):
            # Ensure it has the .eth suffix
            if not address.lower().endswith('.eth'):
                address = f"{address}.eth"
                print(f"Added .eth suffix: {address}")
                
            print(f"Resolving ENS name: {address}")
            resolved_address, error = await self.resolve_ens_name(address)
            if error:
                await interaction.followup.send(f"Error: {error}")
                return
            display_name = address  # Save the ENS name for display
            address = resolved_address
            print(f"Successfully resolved {display_name} to {address}")
        # If this is an Ethereum address, try to get an ENS name for display
        elif address.startswith('0x'):
            print(f"Checking for ENS name for address: {address}")
            ens_name, _ = await self.reverse_resolve_address(address)
            if ens_name:
                display_name = ens_name
                print(f"Found ENS name for {address}: {display_name}")
            else:
                print(f"No ENS name found for {address}")
        else:
            # Not a valid Ethereum address or ENS name format
            await interaction.followup.send(f"Error: Invalid input format. Please provide a valid Ethereum address (starting with 0x) or ENS name (ending with .eth). Example: `/zao 0x1234...` or `/zao name.eth`")
            return
                
        # Check if this address is in our KNOWN_ADDRESSES dictionary
        if address in KNOWN_ADDRESSES and not display_name:
            display_name = KNOWN_ADDRESSES[address]
            print(f"Found address in KNOWN_ADDRESSES: {display_name}")
            
        # Normalize the address to checksum format
        try:
            from web3 import Web3
            address = Web3.to_checksum_address(address)
        except Exception as e:
            print(f"Error converting to checksum address: {e}")
            # Continue with the address as is
        
        # Get token balance
        balance, error = await self.get_token_balance(address)
        if error:
            await interaction.followup.send(f"Error: {error}")
            return
        
        # Create embed with token balance
        embed = discord.Embed(
            title="ZAO Token Balance",
            color=0x57F287,
            timestamp=datetime.now()
        )
        
        # If we have a display name (ENS or known address), show it
        if display_name:
            if display_name.endswith('.eth'):
                embed.description = f"Balance for ENS name: **{display_name}**\n`{address}`"
                # Add ENS icon as thumbnail
                embed.set_thumbnail(url="https://ens.domains/images/ens-logo.png")
            else:
                embed.description = f"Balance for **{display_name}**\n`{address}`"
        else:
            embed.description = f"Balance for address:\n`{address}`"
        
        # Add balance field
        embed.add_field(name="Balance", value=f"**{balance:,.2f} ZAO**", inline=False)
        
        # Add links to block explorers
        embed.add_field(
            name="View on Explorer", 
            value=f"[Etherscan](https://etherscan.io/address/{address}) | [Optimism Explorer](https://optimistic.etherscan.io/address/{address}) | [ZAO Token](https://optimistic.etherscan.io/token/{ZAO_TOKEN_ADDRESS}?a={address})", 
            inline=False
        )
        
        # Add footer with instructions
        embed.set_footer(text="ZAO Fractal Bot | Use /register_address to save your address for future lookups")
        
        await interaction.followup.send(embed=embed)
    
    async def get_all_balances(self):
        """Get ZAO token balances for all known addresses and registered user addresses"""
        balances = []
        for address, name in KNOWN_ADDRESSES.items():
            balance, error = await self.get_token_balance(address)
            if not error:
                # Try to get ENS name for this address if available
                ens_name, _ = await self.reverse_resolve_address(address)
                display_name = ens_name if ens_name else name
                
                balances.append({
                    "address": address,
                    "name": display_name,
                    "balance": balance
                })
        
        # Add registered user addresses that aren't in KNOWN_ADDRESSES
        for user_id, user_data in self.user_addresses.items():
            address = user_data['address']
            name = user_data['name']
            
            # Skip if this address is already in KNOWN_ADDRESSES
            if any(addr.lower() == address.lower() for addr in KNOWN_ADDRESSES):
                continue
                
            balance, error = await self.get_token_balance(address)
            if not error:
                # Try to get ENS name for this address if available
                ens_name, _ = await self.reverse_resolve_address(address)
                display_name = ens_name if ens_name else name
                
                balances.append({
                    "address": address,
                    "name": display_name,
                    "balance": balance
                })
        
        # Sort by balance (highest first)
        balances.sort(key=lambda x: x["balance"], reverse=True)
        return balances
    
    @app_commands.command(name="my_address", description="Check your registered ZAO address")
    async def my_address(self, interaction: discord.Interaction):
        """Check your registered ZAO address"""
        await interaction.response.defer(thinking=True)
        
        user_id = str(interaction.user.id)
        
        # Check if user has a registered address
        if user_id not in self.user_addresses:
            embed = discord.Embed(
                title="No Address Registered",
                description="You don't have a registered Ethereum address. Use `/register_address` to register one.",
                color=0xFF5733,
                timestamp=datetime.now()
            )
            await interaction.followup.send(embed=embed)
            return
        
        # Get user's registered address and name
        user_data = self.user_addresses[user_id]
        address = user_data['address']
        name = user_data['name']
        
        # Try to get ENS name for this address if not already an ENS name
        ens_name, _ = await self.reverse_resolve_address(address)
        
        # Get current balance
        balance, error = await self.get_token_balance(address)
        
        # Create embed with user's address info
        embed = discord.Embed(
            title="Your Registered Address",
            description=f"Here is your registered Ethereum address for the ZAO leaderboard.",
            color=0x57F287,
            timestamp=datetime.now()
        )
        
        # Show ENS name if available
        if ens_name and ens_name != name:
            embed.add_field(
                name="ENS Name",
                value=ens_name,
                inline=False
            )
        
        embed.add_field(
            name="Address",
            value=f"`{address}`",
            inline=False
        )
        
        embed.add_field(
            name="Display Name",
            value=name,
            inline=False
        )
        
        if balance is not None and not error:
            embed.add_field(
                name="Current Balance",
                value=f"{balance:.2f} ZAO",
                inline=False
            )
        
        # Add a link to view on Optimism Explorer
        embed.add_field(
            name="View on Explorer", 
            value=f"[Optimism Explorer](https://optimistic.etherscan.io/token/{ZAO_TOKEN_ADDRESS}?a={address})",
            inline=False
        )
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="register_address", description="Register your Ethereum address or ENS name for the ZAO leaderboard")
    async def register_address(self, interaction: discord.Interaction, address: str, name: Optional[str] = None):
        """Register your Ethereum address or ENS name for the ZAO leaderboard"""
        await interaction.response.defer(thinking=True)
        
        # Save the original address input for display purposes
        original_address = address
        
        # Check if this is an ENS name
        if address.lower().endswith('.eth'):
            resolved_address, error = await self.resolve_ens_name(address)
            if resolved_address:
                address = resolved_address
            else:
                await interaction.followup.send(f"Error: {error}")
                return
        
        # Validate Ethereum address format
        if not address.startswith('0x') or len(address) != 42:
            await interaction.followup.send(f"Error: Invalid Ethereum address format: {address}")
            return
        
        # Get current balance
        balance, error = await self.get_token_balance(address)
        if error:
            balance = None
        
        # Use the provided name or the user's display name
        display_name = name if name else interaction.user.display_name
        
        # If no name was provided, try to get an ENS name for this address
        if not name and not original_address.lower().endswith('.eth'):
            ens_name, _ = await self.reverse_resolve_address(address)
            if ens_name:
                display_name = ens_name
        
        # Save user address
        self.user_addresses[str(interaction.user.id)] = {
            'address': address,
            'name': display_name
        }
        self.save_user_addresses()
        
        # Create confirmation embed
        embed = discord.Embed(
            title="Address Registered",
            description=f"Your Ethereum address has been registered for the ZAO leaderboard.",
            color=0x57F287,
            timestamp=datetime.now()
        )
        
        # Show both ENS and address if ENS was used
        if original_address.lower().endswith('.eth'):
            embed.add_field(
                name="ENS Name",
                value=original_address,
                inline=False
            )
        # If we found an ENS name through reverse lookup, show it
        elif display_name != interaction.user.display_name and not name:
            embed.add_field(
                name="ENS Name",
                value=display_name,
                inline=False
            )
            
        embed.add_field(
            name="Address",
            value=f"`{address}`",
            inline=False
        )
        
        embed.add_field(
            name="Display Name",
            value=display_name,
            inline=False
        )
        
        if balance is not None:
            embed.add_field(
                name="Current Balance",
                value=f"{balance:.2f} ZAO",
                inline=False
            )
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="zao_leaderboard", description="Show the ZAO token leaderboard")
    async def zao_leaderboard(self, interaction: discord.Interaction, top: int = 10):
        """Show the ZAO token leaderboard for known addresses"""
        await interaction.response.defer(thinking=True)
        
        # Get all balances
        balances = await self.get_all_balances()
        
        # Limit to the top N addresses
        if top > len(balances):
            top = len(balances)
        top_balances = balances[:top]
        
        # Calculate total ZAO tokens
        total_zao = sum(item["balance"] for item in balances)
        
        # Create embed for leaderboard
        embed = discord.Embed(
            title="ZAO Token Leaderboard",
            description=f"Top {top} holders of ZAO tokens",
            color=0x57F287,
            timestamp=datetime.now()
        )
        
        # Add fields for each address
        for i, item in enumerate(top_balances):
            # Add medal emoji for top 3
            medal = ""
            if i == 0:
                medal = "🥇 "
            elif i == 1:
                medal = "🥈 "
            elif i == 2:
                medal = "🥉 "
            
            # Calculate percentage of total
            percentage = (item["balance"] / total_zao) * 100 if total_zao > 0 else 0
            
            # Create a visual progress bar
            bar_length = 20
            filled_length = int(bar_length * percentage / 100) if percentage > 0 else 0
            bar = '█' * filled_length + '░' * (bar_length - filled_length)
            
            # Add field for this address
            embed.add_field(
                name=f"{medal}{i+1}. {item['name']}",
                value=f"**{item['balance']:.2f} ZAO** ({percentage:.1f}%)\n{bar}\n`{item['address']}`",
                inline=False
            )
        
        # Add footer with total tokens and instructions
        embed.set_footer(text=f"Total ZAO Tokens: {total_zao:.2f} | Use /register_address to add your address")
        
        # Add thumbnail
        embed.set_thumbnail(url="https://optimismfractal.com/images/zao-logo.png")
        
        await interaction.followup.send(embed=embed)

async def setup(bot):
    # No API key checks needed since we're using a hardcoded Alchemy API URL
    await bot.add_cog(ZAOCommands(bot))
    print("ZAO commands loaded with features:")
    print("- /zao [address|ens] - Check ZAO token balance for address or ENS name")
    print("- /zao_leaderboard [top] - Show ZAO token leaderboard")
    print("- /register_address <address> [name] - Register your address")
    print("- /my_address - Check your registered address")
