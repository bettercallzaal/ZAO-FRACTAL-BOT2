import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional
import aiohttp
import json
from web3 import Web3

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

    def cog_unload(self):
        """Clean up when cog is unloaded."""
        if not self.session.closed:
            asyncio.create_task(self.session.close())

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
        """Resolve an ENS name to an Ethereum address using Alchemy."""
        try:
            async with self.session.get(
                f"https://eth-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}/resolveName",
                params={"name": name}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("result")
                return None
        except Exception as e:
            self.logger.error(f"Error resolving ENS name {name}", exc_info=e)
            return None

    async def _get_ens_details(self, name: str) -> Optional[dict]:
        """Get additional details about an ENS name using Alchemy."""
        try:
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
            
            return details
            
        except Exception as e:
            self.logger.error(f"Error getting ENS details for {name}", exc_info=e)
            return None

    async def _get_ens_names(self, address: str) -> list[str]:
        """Get ENS names owned by an address using Alchemy."""
        try:
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
                    return result.get("result", [])
                return []
        except Exception as e:
            self.logger.error(f"Error getting ENS names for address {address}", exc_info=e)
            return []

async def setup(bot: commands.Bot):
    """Add the ENS cog to the bot."""
    await bot.add_cog(ENSCog(bot))
