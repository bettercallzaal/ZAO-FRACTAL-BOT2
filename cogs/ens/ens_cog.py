import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional, Dict, Tuple
import aiohttp
import json
import asyncio
import time
from web3 import Web3
from datetime import datetime, timedelta

from cogs.base import BaseCog
from config.config import (
    ALCHEMY_API_KEY,
    ENS_RESOLVER_ADDRESS,
    ERROR_MESSAGES,
    SUCCESS_MESSAGES,
    COLORS
)

# ENS Public Resolver ABI (only the functions we need)
ENS_RESOLVER_ABI = [
    {
        "inputs": [{"name": "name", "type": "string"}],
        "name": "addr",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"name": "name", "type": "string"}],
        "name": "text",
        "outputs": [{"name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function"
    }
]

class ENSCog(BaseCog):
    """Cog for ENS name resolution and Ethereum address lookups."""
    
    def __init__(self, bot: commands.Bot):
        super().__init__(bot)
        self.w3 = Web3(Web3.HTTPProvider(f"https://eth-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}"))
        self.resolver = self.w3.eth.contract(
            address=ENS_RESOLVER_ADDRESS,
            abi=ENS_RESOLVER_ABI
        )
        self.session = aiohttp.ClientSession()
        
        # Cache for ENS resolution
        # Structure: {"name": ("address", timestamp)}
        self.ens_cache: Dict[str, Tuple[str, float]] = {}
        
        # Cache for address lookups
        # Structure: {"address": (["name1", "name2"], timestamp)}
        self.address_cache: Dict[str, Tuple[list, float]] = {}
        
        # Cache for ENS details
        # Structure: {"name": (details_dict, timestamp)}
        self.details_cache: Dict[str, Tuple[dict, float]] = {}
        
        # Cache expiration time (24 hours)
        self.cache_expiry = 24 * 60 * 60
        
        # Start cache cleanup task
        self.cache_cleanup_task = self.bot.loop.create_task(self.cleanup_cache())

    def cog_unload(self):
        """Clean up when cog is unloaded."""
        if not self.session.closed:
            asyncio.create_task(self.session.close())
        # Cancel cache cleanup task
        if hasattr(self, 'cache_cleanup_task') and not self.cache_cleanup_task.done():
            self.cache_cleanup_task.cancel()
    
    async def cleanup_cache(self):
        """Periodically clean up expired cache entries."""
        try:
            while True:
                # Wait for 1 hour before cleaning up
                await asyncio.sleep(3600)
                
                current_time = time.time()
                expired_names = []
                expired_addresses = []
                expired_details = []
                
                # Find expired entries
                for name, (_, timestamp) in self.ens_cache.items():
                    if current_time - timestamp > self.cache_expiry:
                        expired_names.append(name)
                        
                for address, (_, timestamp) in self.address_cache.items():
                    if current_time - timestamp > self.cache_expiry:
                        expired_addresses.append(address)
                        
                for name, (_, timestamp) in self.details_cache.items():
                    if current_time - timestamp > self.cache_expiry:
                        expired_details.append(name)
                
                # Remove expired entries
                for name in expired_names:
                    del self.ens_cache[name]
                    
                for address in expired_addresses:
                    del self.address_cache[address]
                    
                for name in expired_details:
                    del self.details_cache[name]
                    
                self.logger.info(f"Cleaned up cache: removed {len(expired_names)} ENS entries, "
                               f"{len(expired_addresses)} address entries, and {len(expired_details)} details entries")
                
        except asyncio.CancelledError:
            self.logger.info("Cache cleanup task cancelled")
        except Exception as e:
            self.logger.error("Error in cache cleanup task", exc_info=e)

    @app_commands.command(
        name="ens",
        description="Resolve an ENS name to its Ethereum address"
    )
    @app_commands.describe(
        name="The ENS name to resolve (e.g., vitalik.eth)",
        details="Show additional details about the ENS name"
    )
    async def resolve_ens(
        self,
        interaction: discord.Interaction,
        name: str,
        details: bool = False
    ):
        """Resolve an ENS name using the ENS Public Resolver."""
        try:
            await interaction.response.defer(thinking=True)
            
            # Add .eth suffix if not present
            if not name.endswith('.eth'):
                name = f"{name}.eth"
            
            try:
                # Get the Ethereum address
                address = await self._resolve_address(name)
                if not address or address == "0x0000000000000000000000000000000000000000":
                    raise ValueError("ENS name not found")
                
                # Create response embed
                embed = discord.Embed(
                    title=f"ENS Resolution: {name}",
                    color=COLORS['success']
                )
                
                embed.add_field(
                    name="Ethereum Address",
                    value=f"`{address}`",
                    inline=False
                )
                
                if details:
                    # Get additional ENS details from Alchemy
                    details = await self._get_ens_details(name)
                    if details:
                        for key, value in details.items():
                            if value and value != "":
                                embed.add_field(
                                    name=key.title(),
                                    value=value,
                                    inline=True
                                )
                
                await interaction.followup.send(embed=embed)
                self.logger.info(f"Resolved ENS name {name} to {address}")
                
            except ValueError as e:
                await interaction.followup.send(
                    embed=discord.Embed(
                        title="❌ Resolution Failed",
                        description=str(e),
                        color=COLORS['error']
                    )
                )
                
        except Exception as e:
            await self.handle_error(interaction, e)

    @app_commands.command(
        name="address",
        description="Look up an Ethereum address's ENS names"
    )
    @app_commands.describe(
        address="The Ethereum address to look up"
    )
    async def lookup_address(
        self,
        interaction: discord.Interaction,
        address: str
    ):
        """Look up ENS names associated with an Ethereum address."""
        try:
            await interaction.response.defer(thinking=True)
            
            # Validate address format
            if not Web3.is_address(address):
                await interaction.followup.send(
                    embed=discord.Embed(
                        title="❌ Invalid Address",
                        description="Please provide a valid Ethereum address.",
                        color=COLORS['error']
                    )
                )
                return
            
            # Normalize address
            address = Web3.to_checksum_address(address)
            
            try:
                # Get ENS names from Alchemy
                names = await self._get_ens_names(address)
                
                if not names:
                    await interaction.followup.send(
                        embed=discord.Embed(
                            title="No ENS Names Found",
                            description=f"No ENS names found for address `{address}`",
                            color=COLORS['warning']
                        )
                    )
                    return
                
                # Create response embed
                embed = discord.Embed(
                    title=f"ENS Names for {address[:6]}...{address[-4:]}",
                    color=COLORS['success']
                )
                
                embed.add_field(
                    name="ENS Names",
                    value="\n".join(f"• {name}" for name in names),
                    inline=False
                )
                
                await interaction.followup.send(embed=embed)
                self.logger.info(f"Found ENS names for address {address}: {', '.join(names)}")
                
            except Exception as e:
                await interaction.followup.send(
                    embed=discord.Embed(
                        title="❌ Lookup Failed",
                        description=str(e),
                        color=COLORS['error']
                    )
                )
                
        except Exception as e:
            await self.handle_error(interaction, e)

    async def _resolve_address(self, name: str) -> Optional[str]:
        """Resolve an ENS name to an Ethereum address using Alchemy with caching."""
        # Check cache first
        if name in self.ens_cache:
            address, timestamp = self.ens_cache[name]
            # If cache entry is still valid
            if time.time() - timestamp < self.cache_expiry:
                self.logger.info(f"Cache hit for ENS name {name}")
                return address
        
        try:
            self.logger.info(f"Cache miss for ENS name {name}, resolving with Alchemy API")
            async with self.session.get(
                f"https://eth-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}/resolveName",
                params={"name": name}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    address = result.get("result")
                    if address:
                        # Cache the result
                        self.ens_cache[name] = (address, time.time())
                    return address
                return None
        except Exception as e:
            self.logger.error(f"Error resolving ENS name {name}", exc_info=e)
            return None

    async def _get_ens_details(self, name: str) -> Optional[dict]:
        """Get additional details about an ENS name using Alchemy with caching."""
        # Check cache first
        if name in self.details_cache:
            details, timestamp = self.details_cache[name]
            # If cache entry is still valid
            if time.time() - timestamp < self.cache_expiry:
                self.logger.info(f"Cache hit for ENS details of {name}")
                return details
        
        try:
            self.logger.info(f"Cache miss for ENS details of {name}, resolving with Alchemy API")
            # Get text records
            records = ["avatar", "description", "url", "twitter", "github"]
            details = {}
            
            for record in records:
                try:
                    result = await self.resolver.functions.text(
                        name,
                        record
                    ).call()
                    if result:
                        details[record] = result
                except Exception:
                    continue
            
            # Cache the result
            self.details_cache[name] = (details, time.time())
            return details
            
        except Exception as e:
            self.logger.error(f"Error getting ENS details for {name}", exc_info=e)
            return None

    async def _get_ens_names(self, address: str) -> list[str]:
        """Get ENS names owned by an address using Alchemy with caching."""
        # Check cache first
        if address in self.address_cache:
            names, timestamp = self.address_cache[address]
            # If cache entry is still valid
            if time.time() - timestamp < self.cache_expiry:
                self.logger.info(f"Cache hit for address {address}")
                return names
        
        try:
            self.logger.info(f"Cache miss for address {address}, resolving with Alchemy API")
            async with self.session.post(
                f"https://eth-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}",
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "alchemy_getEnsNames",
                    "params": [{"address": address}]
                }
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    names = result.get("result", [])
                    # Cache the result
                    self.address_cache[address] = (names, time.time())
                    return names
                return []
        except Exception as e:
            self.logger.error(f"Error getting ENS names for address {address}", exc_info=e)
            return []

async def setup(bot: commands.Bot):
    """Add the ENS cog to the bot."""
    await bot.add_cog(ENSCog(bot))
    bot.logger.info("ENS cog loaded with caching support")
