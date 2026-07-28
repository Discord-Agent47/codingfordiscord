from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View, Select

# Import command mentions utility for dynamic command references
from utils.command_mentions import get_command_mention


# Custom Emojis (same as vouch.py)
EMOJI_VOUCH = "<a:Laptop:1531349427338608701>"
EMOJI_CART = "<:Cart:1531349881598378045>"
EMOJI_SELLER = "<:Seller:1531349842008473772>"
EMOJI_STAR = "<:Star:1531349969741676826>"
EMOJI_COMMENT = "<:Review_Msg:1531348125275656224>"
EMOJI_SEARCH = "<:Search:1531349744021016790>"
EMOJI_TAG = "<:Tag:1531349635229028522>"
EMOJI_CLOCK = "<:Clock:1531349552194387998>"
EMOJI_ARROW = "<:Arrow:1531348396428759161>"
EMOJI_CROSS = "<:Cross:1531349206910898246>"
EMOJI_CHECK = "<:Check:1531349113566920876>"
EMOJI_SETTING = "<:Settings:1531348521024749760>"
EMOJI_RANK = "<:Rank:1531348871488471071>"
EMOJI_STATS = "<:Stats:1531348760448204871>"
EMOJI_REVIEW = "<:Vouch:1531350523209318671>"
EMOJI_IMAGE = "<:Image:1531348285762044144>"
EMOJI_REQUEST = "<:Request:1531347956043612311>"
EMOJI_TRADER = "<:Trader:1531347533601968353>"

FOOTER_TEXT = "Vouch System Help • Thank you for your valuable feedback ❤️"


class HelpSelect(Select):
    """Dropdown selection for help topics."""

    def __init__(self):
        options = [
            discord.SelectOption(
                label="Vouch Command",
                description="Submit a vouch for a service",
                emoji=EMOJI_VOUCH,
                value="vouch"
            ),
            discord.SelectOption(
                label="Vouch Stats",
                description="View vouch statistics for a user",
                emoji=EMOJI_STATS,
                value="vouchstats"
            ),
            discord.SelectOption(
                label="Trader Vouch",
                description="Admin tool to facilitate a vouch",
                emoji=EMOJI_REQUEST,
                value="tradervouch"
            ),
            discord.SelectOption(
                label="Vouch Setup",
                description="Configure the vouch channel",
                emoji=EMOJI_TAG,
                value="vouchsetup"
            ),
            discord.SelectOption(
                label="Vouch Settings",
                description="Manage server items & cooldown",
                emoji=EMOJI_SETTING,
                value="vouchsetting"
            ),
            discord.SelectOption(
                label="List Items",
                description="View all registered items",
                emoji=EMOJI_CART,
                value="listitems"
            ),
        ]
        super().__init__(
            placeholder="Select a command to learn more...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="help_select"
        )

    async def callback(self, interaction: discord.Interaction):
        selected = self.values[0]

        if selected == "vouch":
            embed = self.create_vouch_embed()
        elif selected == "vouchstats":
            embed = self.create_vouchstats_embed()
        elif selected == "tradervouch":
            embed = self.create_tradervouch_embed()
        elif selected == "vouchsetup":
            embed = self.create_vouchsetup_embed()
        elif selected == "vouchsetting":
            embed = self.create_vouchsetting_embed()
        elif selected == "listitems":
            embed = self.create_listitems_embed()
        else:
            embed = self.create_main_embed()

        await interaction.response.edit_message(embed=embed, view=self.view)

    def create_main_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=f"{EMOJI_STAR} Vouch System - Command Guide",
            description=(
                f"Welcome to the **Vouch System**!\n\n"
                f"This system allows users to submit reviews and ratings for sellers, "
                f"helping build trust within the community.\n\n"
                f"{EMOJI_ARROW} **Select a command from the dropdown below** to learn more about it.\n\n"
                f"**Available Commands:**\n"
                f"{EMOJI_VOUCH} `/vouch` - Submit a vouch for a service\n"
                f"{EMOJI_STATS} `/vouchstats` - View vouch statistics\n"
                f"{EMOJI_REQUEST} `/tradervouch` - Admin facilitated vouch\n"
                f"{EMOJI_TAG} `/vouchsetup` - Configure vouch channel\n"
                f"{EMOJI_SETTING} `/vouchsetting` - Manage server settings\n"
                f"{EMOJI_CART} `/listitems` - View registered items"
            ),
            color=discord.Color.gold()
        )
        embed.set_footer(text=FOOTER_TEXT)
        return embed

    def create_vouch_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=f"{EMOJI_VOUCH} {get_command_mention('vouch')} - Submit a Vouch",
            description=(
                f"Submit a vouch/review for a service or product you received from a seller.\n\n"
                f"{EMOJI_STAR} **Command Usage:**\n"
                f"`/vouch <seller> <item> <stars> [vouched_by] [review] [image]`\n\n"
                f"{EMOJI_ARROW} **Parameters:**\n"
            ),
            color=discord.Color.gold()
        )

        embed.add_field(
            name=f"{EMOJI_SELLER} Seller",
            value="The member who provided the service/product *(Required)*",
            inline=False
        )
        embed.add_field(
            name=f"{EMOJI_CART} Item",
            value="The item or service purchased *(Required)*\nUse autocomplete to select from registered items",
            inline=False
        )
        embed.add_field(
            name=f"{EMOJI_STAR} Stars",
            value=f"Rating from 1 to 5 stars *(Required)*\nChoices: {EMOJI_STAR}, {EMOJI_STAR}{EMOJI_STAR}, {EMOJI_STAR}{EMOJI_STAR}{EMOJI_STAR}, {EMOJI_STAR}{EMOJI_STAR}{EMOJI_STAR}{EMOJI_STAR}, {EMOJI_STAR}{EMOJI_STAR}{EMOJI_STAR}{EMOJI_STAR}{EMOJI_STAR}",
            inline=False
        )
        embed.add_field(
            name=f"{EMOJI_TAG} Vouched_by",
            value="Submit on behalf of another member *(Optional)*\nDisplay only, doesn't affect stats",
            inline=False
        )
        embed.add_field(
            name=f"{EMOJI_COMMENT} Review",
            value="Optional review or comment *(Optional)*\nMax 500 characters",
            inline=False
        )
        embed.add_field(
            name=f"{EMOJI_IMAGE} Image",
            value="Optional proof image *(Optional)*\nAccepted: PNG, JPG, JPEG, WEBP",
            inline=False
        )

        embed.add_field(
            name=f"{EMOJI_CLOCK} Cooldown",
            value="There is a server-configured cooldown between vouch submissions.\nCheck with admins for the current cooldown time.",
            inline=False
        )

        embed.add_field(
            name=f"{EMOJI_CROSS} Restrictions",
            value=(
                "• You cannot vouch for yourself\n"
                "• Vouching must be enabled on the server\n"
                "• A vouch channel must be configured"
            ),
            inline=False
        )

        embed.set_footer(text=FOOTER_TEXT)
        return embed

    def create_vouchstats_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=f"{EMOJI_STATS} {get_command_mention('vouchstats')} - View Statistics",
            description=(
                f"View vouch statistics for any user including total vouches, average rating, and recent history.\n\n"
                f"{EMOJI_STAR} **Command Usage:**\n"
                f"`/vouchstats [member]`\n\n"
                f"{EMOJI_ARROW} **Parameters:**\n"
            ),
            color=discord.Color.gold()
        )

        embed.add_field(
            name=f"{EMOJI_RANK} Member",
            value="The member to view stats for *(Optional)*\nDefaults to yourself if not specified",
            inline=False
        )

        embed.add_field(
            name=f"{EMOJI_STAR} Statistics Displayed",
            value=(
                "• **Total Vouches** - Number of vouches received\n"
                "• **Average Rating** - Average star rating (out of 5.0)\n"
                "• **Recent Vouches** - Last 5 vouch entries with details"
            ),
            inline=False
        )

        embed.add_field(
            name=f"{EMOJI_STAR} Notes",
            value=(
                "• Stats are server-specific\n"
                "• Only shows vouches from this server\n"
                "• Anyone can use this command"
            ),
            inline=False
        )

        embed.set_footer(text=FOOTER_TEXT)
        return embed

    def create_tradervouch_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=f"{EMOJI_REQUEST} {get_command_mention('tradervouch')} - Facilitated Vouch",
            description=(
                f"Admin tool to facilitate a vouch session with interactive buttons.\n"
                f"The buyer receives a message with buttons to submit their review.\n\n"
                f"{EMOJI_SETTING} **Permission Required:** Administrator **OR** configured Trader Role\n\n"
                f"{EMOJI_STAR} **Command Usage:**\n"
                f"`/tradervouch <seller> <buyer> <item>`\n\n"
                f"{EMOJI_ARROW} **Parameters:**\n"
            ),
            color=discord.Color.gold()
        )

        embed.add_field(
            name=f"{EMOJI_SELLER} Seller",
            value="The seller receiving the vouch *(Required)*",
            inline=False
        )
        embed.add_field(
            name=f"{EMOJI_CART} Buyer",
            value="The buyer who made the purchase *(Required)*\nThey will receive the feedback request",
            inline=False
        )
        embed.add_field(
            name=f"{EMOJI_TAG} Item",
            value="The item sold *(Required)*\nUse autocomplete to select from registered items",
            inline=False
        )

        embed.add_field(
            name=f"{EMOJI_CHECK} How It Works",
            value=(
                "1. Admin or user with Trader Role runs the command with seller, buyer, and item\n"
                "2. Buyer receives a message with interactive buttons\n"
                "3. Buyer selects star rating and can add comments/images\n"
                "4. Vouch is submitted to the configured channel\n"
                "5. Session expires after 5 minutes if unused"
            ),
            inline=False
        )

        embed.add_field(
            name=f"{EMOJI_CROSS} Restrictions",
            value=(
                "• Seller and buyer cannot be the same person\n"
                "• Only administrators or users with configured Trader Role can use this command\n"
                "• Vouching must be enabled on the server\n"
                "• A vouch channel must be configured"
            ),
            inline=False
        )

        embed.set_footer(text=FOOTER_TEXT)
        return embed

    def create_vouchsetup_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=f"{EMOJI_TAG} {get_command_mention('vouchsetup')} - Configure Channel",
            description=(
                f"Set up the channel where all vouches will be posted.\n\n"
                f"{EMOJI_SETTING} **Permission Required:** Administrator\n\n"
                f"{EMOJI_STAR} **Command Usage:**\n"
                f"`/vouchsetup <channel>`\n\n"
                f"{EMOJI_ARROW} **Parameters:**\n"
            ),
            color=discord.Color.gold()
        )

        embed.add_field(
            name=f"{EMOJI_TAG} Channel",
            value="The text channel for vouches *(Required)*\nAll vouches will be posted here",
            inline=False
        )

        embed.add_field(
            name=f"{EMOJI_CHECK} What This Does",
            value=(
                "• Sets the designated channel for vouch submissions\n"
                "• Required before any vouch commands will work\n"
                "• Can be changed at any time by running again"
            ),
            inline=False
        )

        embed.add_field(
            name=f"{EMOJI_STAR} Tips",
            value=(
                "• Create a dedicated #vouches or #reviews channel\n"
                "• Make sure the bot has send permissions in that channel\n"
                "• Consider making it read-only for regular members"
            ),
            inline=False
        )

        embed.set_footer(text=FOOTER_TEXT)
        return embed

    def create_vouchsetting_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=f"{EMOJI_SETTING} {get_command_mention('vouchsetting')} - Server Settings",
            description=(
                f"Manage server-specific vouch settings with interactive buttons.\n\n"
                f"{EMOJI_SETTING} **Permission Required:** Administrator\n\n"
                f"{EMOJI_STAR} **Command Usage:**\n"
                f"`/vouchsetting`\n\n"
                f"No parameters required - opens an interactive panel!\n\n"
                f"{EMOJI_ARROW} **Settings Available:**\n"
            ),
            color=discord.Color.gold()
        )

        embed.add_field(
            name=f"{EMOJI_CART} Add Item",
            value="Add custom items/services to the autocomplete list\nMembers can then select these when submitting vouches",
            inline=False
        )
        embed.add_field(
            name=f"{EMOJI_CROSS} Remove Item",
            value="Remove an item from the registered items list\nFrees up the code number for reuse",
            inline=False
        )
        embed.add_field(
            name=f"{EMOJI_CLOCK} Set Vouch Cooldown",
            value="Configure the cooldown time between vouch submissions\nPrevents spam and ensures quality reviews",
            inline=False
        )
        embed.add_field(
            name=f"{EMOJI_CHECK} Toggle Vouch",
            value="Enable or disable the entire vouch system\nWhen disabled, no vouches can be submitted",
            inline=False
        )
        embed.add_field(
            name=f"{EMOJI_TRADER} Set Trader Role",
            value="Assign a role that gains permission to use `/tradervouch`\nUsers with this role can facilitate vouches without admin perms",
            inline=False
        )
        embed.add_field(
            name=f"{EMOJI_CROSS} Remove Trader Role",
            value="Remove the configured Trader Role\nReverts `/tradervouch` access to Admins only",
            inline=False
        )

        embed.add_field(
            name=f"{EMOJI_STAR} Default Items",
            value=(
                "If no custom items are added, these defaults are available:\n"
                "• Product A, Product B, Product C\n"
                "• Product D, Product E, Product F"
            ),
            inline=False
        )

        embed.set_footer(text=FOOTER_TEXT)
        return embed

    def create_listitems_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=f"{EMOJI_CART} {get_command_mention('listitems')} - View Registered Items",
            description=(
                f"View all registered items/services for this server.\n"
                f"Shows items in a paginated view with navigation buttons.\n\n"
                f"{EMOJI_SETTING} **Permission Required:** Administrator\n\n"
                f"{EMOJI_STAR} **Command Usage:**\n"
                f"`/listitems`\n\n"
                f"No parameters required - displays the item list!\n\n"
                f"{EMOJI_ARROW} **Features:**\n"
            ),
            color=discord.Color.gold()
        )

        embed.add_field(
            name=f"{EMOJI_TAG} Item Codes",
            value=(
                "Each item has a unique code number\n"
                "Codes can be reused when items are deleted\n"
                "Used internally for item management"
            ),
            inline=False
        )
        embed.add_field(
            name=f"{EMOJI_SEARCH} Pagination",
            value=(
                "• Shows 10 items per page\n"
                "• Navigate with Previous/Next buttons\n"
                "• Displays total item count"
            ),
            inline=False
        )
        embed.add_field(
            name=f"{EMOJI_SETTING} Managing Items",
            value=(
                "To add/remove items, use `/vouchsetting`\n"
                "This command is view-only for convenience"
            ),
            inline=False
        )

        embed.set_footer(text=FOOTER_TEXT)
        return embed


class HelpView(View):
    """View containing the help dropdown."""

    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(HelpSelect())


class VouchHelp(commands.Cog):
    """Cog providing help documentation for the Vouch system."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="vouchhelp", description="Get help with vouch commands")
    async def vouchhelp_command(self, interaction: discord.Interaction) -> None:
        """Display the help menu for vouch commands."""
        if not await self._check_guild_context(interaction):
            return

        embed = self._create_main_embed()
        view = HelpView()

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    async def _check_guild_context(self, interaction: discord.Interaction) -> bool:
        """Check if interaction is in a guild."""
        if interaction.guild is None:
            await interaction.response.send_message(
                f"{EMOJI_CROSS} This command only works in servers, not in DMs.",
                ephemeral=True
            )
            return False
        return True

    def _create_main_embed(self) -> discord.Embed:
        """Create the main help embed."""
        embed = discord.Embed(
            title=f"{EMOJI_STAR} Vouch System - Command Guide",
            description=(
                f"Welcome to the **Vouch System**!\n\n"
                f"This system allows users to submit reviews and ratings for sellers, "
                f"helping build trust within the community.\n\n"
                f"{EMOJI_ARROW} **Select a command from the dropdown below** to learn more about it.\n\n"
                f"**Available Commands:**\n"
                f"{EMOJI_VOUCH} `/vouch` - Submit a vouch for a service\n"
                f"{EMOJI_STATS} `/vouchstats` - View vouch statistics\n"
                f"{EMOJI_REQUEST} `/tradervouch` - Admin facilitated vouch\n"
                f"{EMOJI_TAG} `/vouchsetup` - Configure vouch channel\n"
                f"{EMOJI_SETTING} `/vouchsetting` - Manage server settings\n"
                f"{EMOJI_CART} `/listitems` - View registered items"
            ),
            color=discord.Color.gold()
        )
        embed.set_footer(text=FOOTER_TEXT)
        return embed


async def setup(bot: commands.Bot) -> None:
    """Load the VouchHelp cog."""
    await bot.add_cog(VouchHelp(bot))
