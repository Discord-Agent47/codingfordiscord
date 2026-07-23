from __future__ import annotations

import json
import os
import time
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any, Union

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput


# Colors
SUCCESS_COLOR = discord.Color.green()
ERROR_COLOR = discord.Color.red()
VOUCH_COLOR = discord.Color.gold()

# Custom Emojis
EMOJI_VOUCH = "<a:Laptop:1529207144162005215>"
EMOJI_CART = "<:Cart:1529206909465399426>"
EMOJI_SELLER = "<:Seller:1529206906437107995>"
EMOJI_STAR = "<:Star:1529207360277577798>"
EMOJI_COMMENT = "<:Comment:1529206903962341478>"
EMOJI_SEARCH = "<:Search:1529206901831893163>"
EMOJI_TAG = "<:Tag:1529206892486721687>"
EMOJI_CLOCK = "<:Clock:1529206889844314282>"
EMOJI_ARROW = "<:Arrow_GG:1529856775103320064>"
EMOJI_CROSS = "<:Cross:1529485828672323684>"
EMOJI_CHECK = "<:Check:1529549227770908803>"
EMOJI_SETTING = "<:Setting:1529855660357980210>"
EMOJI_RANK = "<:Rank:1529733245032464454>"
EMOJI_STATS = "<:Stats:1529852489896169603>"
EMOJI_REVIEW = "<:Review:1529853305008689242>"
EMOJI_IMAGE = "<:Image:1529866936249487491>"

FOOTER_TEXT = "Thank you for your valuable feedback ❤️"

DATA_FOLDER = Path("data")
VOUCHES_FILE = DATA_FOLDER / "vouches.json"
ITEMS_FILE = DATA_FOLDER / "vouch_items.json"
CONFIG_FILE = DATA_FOLDER / "vouch_config.json"
VOUCH_HISTORY_FILE = DATA_FOLDER / "vouch_history.json"
COOLDOWNS_FILE = DATA_FOLDER / "vouch_cooldowns.json"
USER_COOLDOWNS_FILE = DATA_FOLDER / "vouch_user_cooldowns.json"

DEFAULT_ITEMS = [
    "Product A",
    "Product B",
    "Product C",
    "Product D",
    "Product E",
    "Product F",
]

def load_json(file_path: Path, default: Any = None) -> Any:
    if not file_path.exists():
        return default if default is not None else {}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return default if default is not None else {}


def save_json(file_path: Path, data: Any) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)



async def check_guild_context(interaction: discord.Interaction) -> bool:
    """Check if interaction is in a guild. Sends plain text error if in DM."""
    if interaction.guild is None:
        await interaction.response.send_message(
            "Oops! This command doesn't work in DMs.",
            ephemeral=True
        )
        return False
    return True



def get_items(guild_id: str) -> List[Dict[str, Any]]:
    """Get items for a specific guild. Returns defaults if no custom items exist.
    Returns list of dicts: [{'code': 1, 'name': 'Product A'}, ...]
    Handles migration from old string format to new dict format.
    """
    all_data = load_json(ITEMS_FILE, {})
    guild_key = str(guild_id)

    guild_items = all_data.get(guild_key, [])

    # Migration: If items are stored as strings (old format), convert to dict format
    if guild_items and isinstance(guild_items[0], str):
        migrated_items = []
        for i, name in enumerate(guild_items):
            migrated_items.append({"code": i + 1, "name": str(name)})
        all_data[guild_key] = migrated_items
        save_json(ITEMS_FILE, all_data)
        return migrated_items

    # If no custom items for this guild, return defaults with codes 1-6
    if not guild_items:
        return [{"code": i+1, "name": name} for i, name in enumerate(DEFAULT_ITEMS)]

    return guild_items


def get_next_available_code(guild_items: List[Dict[str, Any]]) -> int:
    """Find the smallest available code number (reusing vacant numbers)."""
    if not guild_items:
        return 1

    existing_codes = sorted([item['code'] for item in guild_items])

    # Find first gap
    for i, code in enumerate(existing_codes):
        if code != i + 1:
            return i + 1

    # No gaps, return next number
    return existing_codes[-1] + 1


def add_item(guild_id: str, name: str) -> Optional[int]:
    """Add an item for a specific guild. Returns the assigned code or None if exists."""
    all_data = load_json(ITEMS_FILE, {})
    guild_key = str(guild_id)

    if guild_key not in all_data:
        all_data[guild_key] = []

    # Migration: Handle old string format
    if all_data[guild_key] and isinstance(all_data[guild_key][0], str):
        migrated_items = []
        for i, item_name in enumerate(all_data[guild_key]):
            migrated_items.append({"code": i + 1, "name": str(item_name)})
        all_data[guild_key] = migrated_items

    normalized_name = name.strip()
    for item in all_data[guild_key]:
        # Handle both dict and legacy string formats
        item_name = item['name'] if isinstance(item, dict) else str(item)
        if item_name.lower() == normalized_name.lower():
            return None

    new_code = get_next_available_code(all_data[guild_key])
    new_item = {"code": new_code, "name": normalized_name}
    all_data[guild_key].append(new_item)
    save_json(ITEMS_FILE, all_data)
    return new_code


def remove_item_by_code(guild_id: str, code: int) -> bool:
    """Remove an item by its code for a specific guild."""
    all_data = load_json(ITEMS_FILE, {})
    guild_key = str(guild_id)

    if guild_key not in all_data:
        return False

    items_list = all_data[guild_key]

    # Migration: Handle old string format (shouldn't happen but safe guard)
    if items_list and isinstance(items_list[0], str):
        migrated_items = []
        for i, item_name in enumerate(items_list):
            migrated_items.append({"code": i + 1, "name": str(item_name)})
        all_data[guild_key] = migrated_items
        items_list = migrated_items

    for i, item in enumerate(items_list):
        # Handle both dict and legacy formats
        item_code = item['code'] if isinstance(item, dict) else None
        if item_code == code:
            all_data[guild_key].pop(i)
            save_json(ITEMS_FILE, all_data)
            return True

    return False


def get_item_by_code(guild_id: str, code: int) -> Optional[str]:
    """Get item name by code for a specific guild."""
    items = get_items(guild_id)
    for item in items:
        if item['code'] == code:
            return item['name']
    return None



def get_server_vouch_count(user_id: str, guild_id: str) -> int:
    """Get vouch count for a user in a specific server."""
    history = load_json(VOUCH_HISTORY_FILE, {})
    seller_key = str(user_id)
    user_history = history.get(seller_key, [])
    
    # Filter by guild_id
    filtered_history = [h for h in user_history if h.get('guild_id') == str(guild_id)]
    
    return len(filtered_history)


def get_vouch_count(user_id: str) -> int:
    vouches = load_json(VOUCHES_FILE, {})
    return vouches.get(str(user_id), 0)


def add_vouch(user_id: str, amount: int = 1) -> int:
    vouches = load_json(VOUCHES_FILE, {})
    user_key = str(user_id)
    current_count = vouches.get(user_key, 0)
    new_count = current_count + amount
    vouches[user_key] = new_count
    save_json(VOUCHES_FILE, vouches)
    return new_count


def add_vouch_history(seller_id: str, vouch_data: Dict[str, Any]) -> None:
    """Add a detailed vouch record to history."""
    history = load_json(VOUCH_HISTORY_FILE, {})
    seller_key = str(seller_id)

    if seller_key not in history:
        history[seller_key] = []

    history[seller_key].append(vouch_data)
    save_json(VOUCH_HISTORY_FILE, history)


def get_server_vouch_history(user_id: str, guild_id: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Get recent vouch history for a user in a specific server."""
    history = load_json(VOUCH_HISTORY_FILE, {})
    seller_key = str(user_id)
    user_history = history.get(seller_key, [])

    # Filter by guild_id if stored
    filtered_history = [h for h in user_history if h.get('guild_id') == str(guild_id)]

    # If no guild-specific entries, return all (backward compatibility)
    if not filtered_history:
        filtered_history = user_history

    return list(reversed(filtered_history[-limit:]))


def calculate_server_average_rating(user_id: str, guild_id: str) -> float:
    """Calculate average rating for a user in a specific server."""
    history = load_json(VOUCH_HISTORY_FILE, {})
    seller_key = str(user_id)
    user_history = history.get(seller_key, [])

    # Filter by guild_id if stored
    filtered_history = [h for h in user_history if h.get('guild_id') == str(guild_id)]

    if not filtered_history:
        # Fallback to all history if no guild-specific entries
        filtered_history = user_history

    if not filtered_history:
        return 0.0

    total_stars = sum(entry.get('stars', 0) for entry in filtered_history)
    return round(total_stars / len(filtered_history), 2)


def get_user_vouch_history(user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Get recent vouch history for a user."""
    history = load_json(VOUCH_HISTORY_FILE, {})
    seller_key = str(user_id)
    user_history = history.get(seller_key, [])

    # Return last N entries reversed (newest first)
    return list(reversed(user_history[-limit:]))


def calculate_average_rating(user_id: str) -> float:
    """Calculate average rating based on history."""
    history = load_json(VOUCH_HISTORY_FILE, {})
    seller_key = str(user_id)
    user_history = history.get(seller_key, [])

    if not user_history:
        return 0.0

    total_stars = sum(entry.get('stars', 0) for entry in user_history)
    return round(total_stars / len(user_history), 2)



def load_config() -> Dict[str, Any]:
    return load_json(CONFIG_FILE, {})


def save_config(config: Dict[str, Any]) -> None:
    save_json(CONFIG_FILE, config)


def get_vouch_channel(guild_id: str) -> Optional[int]:
    config = load_config()
    guild_data = config.get(str(guild_id), {})
    return guild_data.get("channel")


def set_vouch_channel(guild_id: str, channel_id: int) -> None:
    config = load_config()
    if str(guild_id) not in config:
        config[str(guild_id)] = {}
    config[str(guild_id)]["channel"] = channel_id
    save_config(config)


def is_vouch_enabled(guild_id: str) -> bool:
    """Check if vouching is enabled for a specific server. Default is True (enabled)."""
    config = load_config()
    guild_data = config.get(str(guild_id), {})
    # Default to True if not set
    return guild_data.get("enabled", True)


def set_vouch_enabled(guild_id: str, enabled: bool) -> None:
    """Set vouching enabled/disabled for a specific server."""
    config = load_config()
    if str(guild_id) not in config:
        config[str(guild_id)] = {}
    config[str(guild_id)]["enabled"] = enabled
    save_config(config)


def get_server_cooldown(guild_id: str) -> int:
    """Get vouch cooldown for a specific server (default 300 seconds / 5 minutes)."""
    cooldowns = load_json(COOLDOWNS_FILE, {})
    guild_key = str(guild_id)
    # Cooldown is stored in seconds, default is 300 (5 minutes)
    cooldown = cooldowns.get(guild_key, 300)
    # Ensure minimum of 300 seconds (5 minutes)
    return max(300, cooldown)


def set_server_cooldown(guild_id: str, cooldown_minutes: int) -> None:
    """Set vouch cooldown for a specific server. Minimum is 5 minutes."""
    cooldowns = load_json(COOLDOWNS_FILE, {})
    guild_key = str(guild_id)
    # Enforce minimum of 5 minutes (300 seconds)
    cooldown_seconds = max(300, cooldown_minutes * 60)
    cooldowns[guild_key] = cooldown_seconds
    save_json(COOLDOWNS_FILE, cooldowns)


def check_user_cooldown(user_id: str, guild_id: str) -> tuple[bool, int]:
    """
    Check if user is on cooldown for vouching in a specific server.
    Returns (is_on_cooldown, remaining_seconds).
    If not on cooldown, returns (False, 0).
    """
    cooldowns = load_json(USER_COOLDOWNS_FILE, {})
    guild_key = str(guild_id)
    user_key = str(user_id)
    
    if guild_key not in cooldowns:
        cooldowns[guild_key] = {}
    
    user_last_vouch = cooldowns[guild_key].get(user_key, 0)
    current_time = int(time.time())
    server_cooldown = get_server_cooldown(guild_id)
    
    time_since_last = current_time - user_last_vouch
    
    if time_since_last < server_cooldown:
        remaining = server_cooldown - time_since_last
        return True, remaining
    
    return False, 0


def set_user_cooldown(user_id: str, guild_id: str) -> None:
    """Set the last vouch time for a user in a specific server."""
    cooldowns = load_json(USER_COOLDOWNS_FILE, {})
    guild_key = str(guild_id)
    user_key = str(user_id)
    
    if guild_key not in cooldowns:
        cooldowns[guild_key] = {}
    
    cooldowns[guild_key][user_key] = int(time.time())
    save_json(USER_COOLDOWNS_FILE, cooldowns)



def create_success_embed(title: str, description: Optional[str] = None) -> discord.Embed:
    embed = discord.Embed(title=title, description=description, color=SUCCESS_COLOR)
    return embed


def create_error_embed(title: str, description: Optional[str] = None) -> discord.Embed:
    embed = discord.Embed(title=title, description=description, color=ERROR_COLOR)
    return embed


def create_vouch_embed(
    customer: Union[discord.Member, str],
    seller: Union[discord.Member, str],
    item: str,
    stars: int,
    review: str,
    vouch_id: int,
    vouched_by_override: Optional[Union[discord.Member, str]] = None,
    timestamp_override: Optional[int] = None
) -> discord.Embed:
    star_rating = EMOJI_STAR * stars
    current_time = timestamp_override if timestamp_override else int(time.time())
    relative_timestamp = f"<t:{current_time}:R>"

    # Resolve mentions if strings are passed (for trader vouch)
    customer_mention = customer.mention if hasattr(customer, 'mention') else customer
    seller_mention = seller.mention if hasattr(seller, 'mention') else seller
    vouched_by_mention = None
    if vouched_by_override:
        vouched_by_mention = vouched_by_override.mention if hasattr(vouched_by_override, 'mention') else vouched_by_override

    embed = discord.Embed(
        title=f"{EMOJI_REVIEW} A New Review has Arrived! ",
        color=VOUCH_COLOR
    )

    # Handle avatar URL safely
    if hasattr(seller, 'display_avatar'):
        embed.set_thumbnail(url=seller.display_avatar.url)

    embed.add_field(name=f"{EMOJI_CART} Product", value=f"{EMOJI_ARROW} {item}", inline=False)
    embed.add_field(name=f"{EMOJI_SELLER} Seller", value=f"{EMOJI_ARROW} {seller_mention}", inline=False)
    embed.add_field(name=f"{EMOJI_STAR} Rating", value=f"{EMOJI_ARROW} {star_rating}", inline=False)
    embed.add_field(name=f"{EMOJI_COMMENT} COMMENT", value=f"{EMOJI_ARROW} {review if review.strip() else 'No additional comments.'}", inline=False)

    if vouched_by_override:
        vouched_by_display = vouched_by_mention
    else:
        vouched_by_display = customer_mention

    spacer = "      "
    embed.add_field(name=f"{EMOJI_SEARCH} Vouched By", value=f"{EMOJI_ARROW} {vouched_by_display}", inline=True)
    embed.add_field(name=f"{EMOJI_TAG} Vouch ID{spacer}", value=f"{EMOJI_ARROW} #{vouch_id:05d}", inline=True)
    embed.add_field(name=f"{EMOJI_CLOCK} Timestamp{spacer}", value=f"{EMOJI_ARROW} {relative_timestamp}", inline=True)

    embed.set_footer(text=FOOTER_TEXT)
    return embed


class StarButton(Button):
    def __init__(self, stars: int):
        emoji_str = EMOJI_STAR * stars
        super().__init__(style=discord.ButtonStyle.secondary, emoji=emoji_str, label=f"{stars} Star{'s' if stars > 1 else ''}")
        self.stars = stars

    async def callback(self, interaction: discord.Interaction):
        view: TraderVouchView = self.view
        if interaction.user.id != view.author.id:
            await interaction.response.send_message(
                embed=create_error_embed(f"Access Denied", "Only the designated buyer can submit this vouch."),
                ephemeral=True
            )
            return

        view.selected_stars = self.stars

        for child in view.children:
            if isinstance(child, StarButton):
                child.style = discord.ButtonStyle.success if child.stars == self.stars else discord.ButtonStyle.secondary

        await interaction.response.edit_message(view=view)

        has_comment = bool(view.comment_text)
        has_image = bool(view.image_url)

        if not has_comment and not has_image:
            embed = discord.Embed(
                title="⭐ Star Recorded",
                description=f"You selected **{self.stars} star(s)**.\n\n"
                            f"**Next Step (Optional):**\n"
                            f"You may add a review comment and/or attach a proof image, or click **Submit Vouch** to finish.",
                color=SUCCESS_COLOR
            )
        elif has_comment and not has_image:
            embed = discord.Embed(
                title=f"{EMOJI_CHECK} Rating & Review Recorded",
                description=f"Your star rating and review have both been recorded.\n\n"
                            f"**Optional Next Step:**\n"
                            f"You may attach a proof image, or click **Submit Vouch** to publish your vouch.",
                color=SUCCESS_COLOR
            )
        elif not has_comment and has_image:
            embed = discord.Embed(
                title=f"{EMOJI_CHECK} Rating & Image Recorded",
                description=f"Your star rating and proof image have both been recorded.\n\n"
                            f"**Optional Next Step:**\n"
                            f"You may add a review comment, or click **Submit Vouch** to publish your vouch.",
                color=SUCCESS_COLOR
            )
        else:
            embed = discord.Embed(
                title=f"{EMOJI_CHECK} Everything Recorded",
                description=f"Your star rating, review, and proof image have all been recorded.\n\n"
                            f"You can now click **Submit Vouch** to publish your vouch.",
                color=SUCCESS_COLOR
            )
        
        await view._send_temporary(interaction, embed=embed)


class CommentModal(Modal, title="Add Review Comment"):
    comment_input = TextInput(label="Review", placeholder="Describe your experience...", required=False, max_length=500)

    def __init__(self, view: 'TraderVouchView'):
        super().__init__()
        self.view = view

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.view.author.id:
            await interaction.response.send_message(
                embed=create_error_embed(f"Access Denied", "Only the designated buyer can add comments."),
                ephemeral=True
            )
            return

        self.view.comment_text = self.comment_input.value.strip()
        
        has_star = self.view.selected_stars is not None
        has_image = bool(self.view.image_url)

        if not has_star and not has_image:
            embed = discord.Embed(
                title="💬 Review Recorded",
                description=f"Your review has been recorded successfully.\n\n"
                            f"**Required Next Step:**\n"
                            f"Please select a **star rating** before clicking **Submit Vouch**.\n\n"
                            f"**Optional:**\n"
                            f"You may also attach a proof image.",
                color=SUCCESS_COLOR
            )
        elif has_star and not has_image:
            embed = discord.Embed(
                title=f"{EMOJI_CHECK} Rating & Review Recorded",
                description=f"Your review and star rating have both been recorded.\n\n"
                            f"**Optional Next Step:**\n"
                            f"You may attach a proof image, or click **Submit Vouch** to publish your vouch.",
                color=SUCCESS_COLOR
            )
        elif not has_star and has_image:
            embed = discord.Embed(
                title=f"🖼️ Review & Image Recorded",
                description=f"Your review and proof image have both been recorded.\n\n"
                            f"**Required Next Step:**\n"
                            f"Please select a **star rating** before clicking **Submit Vouch**.",
                color=SUCCESS_COLOR
            )
        else:
            embed = discord.Embed(
                title=f"{EMOJI_CHECK} Everything Recorded",
                description=f"Your review, star rating, and proof image have all been recorded.\n\n"
                            f"You can now click **Submit Vouch** to publish your vouch.",
                color=SUCCESS_COLOR
            )
        
        await self.view._send_temporary(interaction, embed=embed)


def create_vouch_settings_embed(guild_id: str) -> discord.Embed:
    """Create a fresh vouch settings embed from current configuration."""
    current_cooldown_minutes = get_server_cooldown(guild_id) // 60
    vouch_enabled = is_vouch_enabled(guild_id)
    enabled_status = f"{EMOJI_CHECK} Enabled" if vouch_enabled else f"{EMOJI_CROSS} Disabled"
    
    embed = discord.Embed(
        title=f"{EMOJI_CART} Vouch Settings",
        description=f"Manage your server's vouch items and cooldown using the buttons below.\n\n{EMOJI_CLOCK} **Current Cooldown:** {current_cooldown_minutes} minutes\n{EMOJI_SETTING} **Vouch System:** {enabled_status}",
        color=VOUCH_COLOR
    )
    total_items = len(get_items(guild_id))
    embed.set_footer(text=f"📦 Registered Items: {total_items}")
    return embed


class CooldownModal(Modal, title="Set Vouch Cooldown"):
    def __init__(self, guild_id: str, setting_view: Optional[VouchSettingView] = None):
        super().__init__()
        self.guild_id = guild_id
        self.setting_view = setting_view
        current_cooldown_minutes = get_server_cooldown(guild_id) // 60
        self.cooldown_input = TextInput(
            label="Cooldown (minutes)",
            placeholder=f"Enter cooldown in minutes (minimum 5, current: {current_cooldown_minutes})",
            required=True,
            max_length=10,
            default=str(current_cooldown_minutes)
        )
        self.add_item(self.cooldown_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            cooldown_minutes = int(self.cooldown_input.value.strip())
        except ValueError:
            await interaction.response.send_message(
                embed=create_error_embed(f"{EMOJI_CROSS} Invalid Value", "Please enter a valid number."),
                ephemeral=True
            )
            return

        if cooldown_minutes < 5:
            await interaction.response.send_message(
                embed=create_error_embed(f"{EMOJI_CROSS} Minimum Cooldown", "The cooldown cannot be set below 5 minutes."),
                ephemeral=True
            )
            return

        set_server_cooldown(self.guild_id, cooldown_minutes)
        
        # Update the settings embed by regenerating it from fresh data
        if self.setting_view and self.setting_view.original_message:
            new_embed = create_vouch_settings_embed(self.guild_id)
            await self.setting_view.original_message.edit(embed=new_embed, view=self.setting_view)
        
        # Send ephemeral confirmation message
        confirm_embed = discord.Embed(
            title=f"{EMOJI_CHECK} Cooldown Updated",
            description=f"The cooldown has been updated to {cooldown_minutes} minutes.",
            color=SUCCESS_COLOR
        )
        await interaction.response.send_message(embed=confirm_embed, ephemeral=True)


class VouchSettingView(View):
    def __init__(self, guild_id: str, original_message: Optional[discord.Message] = None):
        super().__init__(timeout=300.0)  # 5 minutes timeout
        self.guild_id = guild_id
        self.original_message = original_message
        
        # Set initial button style based on current vouch status
        vouch_enabled = is_vouch_enabled(guild_id)
        self.toggle_vouch_btn.style = discord.ButtonStyle.green if vouch_enabled else discord.ButtonStyle.red

    @discord.ui.button(label="Add Item", style=discord.ButtonStyle.green, emoji=EMOJI_CART)
    async def add_item_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(AddItemModal(self.guild_id, self))

    @discord.ui.button(label="Remove Item", style=discord.ButtonStyle.red, emoji=EMOJI_TAG)
    async def remove_item_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(RemoveItemModal(self.guild_id, self))

    @discord.ui.button(label="Set Cooldown", style=discord.ButtonStyle.blurple, emoji=EMOJI_CLOCK)
    async def set_cooldown_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(CooldownModal(self.guild_id, self))

    @discord.ui.button(label="Toggle Vouching", style=discord.ButtonStyle.green)
    async def toggle_vouch_btn(self, interaction: discord.Interaction, button: Button):
        current_enabled = is_vouch_enabled(self.guild_id)
        new_state = not current_enabled
        set_vouch_enabled(self.guild_id, new_state)
        
        # Update button appearance immediately
        button.style = discord.ButtonStyle.green if new_state else discord.ButtonStyle.red
        
        # Regenerate the settings embed from fresh data to avoid sync issues
        if self.original_message:
            new_embed = create_vouch_settings_embed(self.guild_id)
            await self.original_message.edit(embed=new_embed, view=self)
        
        # Send ephemeral confirmation message
        action_text = "Enabled" if new_state else "Disabled"
        confirm_embed = discord.Embed(
            title=f"{EMOJI_CHECK} Vouch System Updated",
            description=f"Vouching has been {action_text} successfully.",
            color=SUCCESS_COLOR
        )
        await interaction.response.send_message(embed=confirm_embed, ephemeral=True)


class AddItemModal(Modal, title="Add New Item"):
    def __init__(self, guild_id: str, setting_view: Optional[VouchSettingView] = None):
        super().__init__()
        self.guild_id = guild_id
        self.setting_view = setting_view
        self.item_name_input = TextInput(
            label="Item Name",
            placeholder="Enter the item name...",
            required=True,
            max_length=100
        )
        self.add_item(self.item_name_input)

    async def on_submit(self, interaction: discord.Interaction):
        item_name = self.item_name_input.value.strip()
        code = add_item(self.guild_id, item_name)
        if code is not None:
            embed = discord.Embed(
                title=f"{EMOJI_CHECK} Item Added",
                description="The item has been successfully registered.",
                color=SUCCESS_COLOR
            )
            embed.add_field(
                name=f"{EMOJI_TAG} Item Code",
                value=f"#{code:03d}",
                inline=False
            )
            embed.add_field(
                name=f"{EMOJI_CART} Item Name",
                value=item_name,
                inline=False
            )
            
            # Update the settings embed by regenerating from fresh data
            if self.setting_view and self.setting_view.original_message:
                new_embed = create_vouch_settings_embed(self.guild_id)
                await self.setting_view.original_message.edit(embed=new_embed, view=self.setting_view)
                await interaction.response.send_message(
                    embed=embed,
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    embed=embed,
                    ephemeral=True
                )
        else:
            embed = discord.Embed(
                title="⚠️ Duplicate Item",
                description="An item with this name is already registered in the server catalog.",
                color=ERROR_COLOR
            )
            await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )


class RemoveItemModal(Modal, title="Remove Item"):
    def __init__(self, guild_id: str, setting_view: Optional[VouchSettingView] = None):
        super().__init__()
        self.guild_id = guild_id
        self.setting_view = setting_view
        self.item_code_input = TextInput(
            label="Item Code",
            placeholder="Enter the item code number...",
            required=True,
            max_length=10
        )
        self.add_item(self.item_code_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            code = int(self.item_code_input.value.strip())
        except ValueError:
            await interaction.response.send_message(
                embed=create_error_embed(f"{EMOJI_CROSS} Invalid Code", "Please enter a valid numeric code."),
                ephemeral=True
            )
            return

        items = get_items(self.guild_id)
        item_name = None
        for item in items:
            if item['code'] == code:
                item_name = item['name']
                break

        if item_name is None:
            embed = discord.Embed(
                title="🔍 Item Not Found",
                description=f"No registered item was found with code **#{code:03d}**.",
                color=ERROR_COLOR
            )
            await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )
            return

        if remove_item_by_code(self.guild_id, code):
            embed = discord.Embed(
                title=f"{EMOJI_CHECK} Item Removed",
                description="The item has been successfully removed from the server.",
                color=SUCCESS_COLOR
            )
            embed.add_field(
                name=f"🏷️ Item Code",
                value=f"#{code:03d}",
                inline=False
            )
            embed.add_field(
                name=f"📦 Item Name",
                value=item_name,
                inline=False
            )
            
            # Update the settings embed by regenerating from fresh data
            if self.setting_view and self.setting_view.original_message:
                new_embed = create_vouch_settings_embed(self.guild_id)
                await self.setting_view.original_message.edit(embed=new_embed, view=self.setting_view)
                await interaction.response.send_message(
                    embed=embed,
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    embed=embed,
                    ephemeral=True
                )
        else:
            embed = discord.Embed(
                title="⚠️ Removal Failed",
                description="The item couldn't be removed. Please try again or contact the bot administrator if the issue persists.",
                color=ERROR_COLOR
            )
            await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )


class TraderVouchView(View):
    def __init__(self, bot: commands.Bot, seller: discord.Member, item: str, author: discord.Member):
        super().__init__(timeout=300.0)
        self.bot = bot
        self.seller = seller
        self.item = item
        self.author = author
        self.selected_stars: Optional[int] = None
        self.comment_text: str = ""
        self.image_url: Optional[str] = None
        self.message: Optional[discord.Message] = None
        self.submitted = False
        self._lock = asyncio.Lock()
        
        for i in range(1, 6):
            self.add_item(StarButton(i))

    async def _send_temporary(self, interaction: discord.Interaction, content: Optional[str] = None, embed: Optional[discord.Embed] = None):
        """Send an ephemeral message that auto-deletes after 5 seconds."""
        if not interaction.response.is_done():
            if content is not None:
                await interaction.response.send_message(content, ephemeral=True)
            elif embed is not None:
                await interaction.response.send_message(embed=embed, ephemeral=True)
            msg = await interaction.original_response()
        else:
            if content is not None:
                msg = await interaction.followup.send(content, ephemeral=True)
            elif embed is not None:
                msg = await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                return
        try:
            await asyncio.sleep(5)
            await msg.delete()
        except discord.HTTPException:
            pass

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author.id:
            await interaction.response.send_message(
                embed=create_error_embed(f"Access Denied", "Only the designated buyer can interact with this session."),
                ephemeral=True
            )
            return False
        return True

    async def on_timeout(self) -> None:
        if self.message and not self.submitted:
            try:
                for child in self.children:
                    child.disabled = True
                await self.message.edit(
                    view=self,
                    content="**⚠️ This vouch session has expired.**\nNo vouch was recorded."
                )
            except discord.HTTPException:
                pass

    @discord.ui.button(label="Add Comment", style=discord.ButtonStyle.blurple, emoji=EMOJI_COMMENT, row=1)
    async def add_comment_btn(self, interaction: discord.Interaction, button: Button):
        if self.submitted:
            await self._send_temporary(interaction, content="This session is already completed.")
            return
        await interaction.response.send_modal(CommentModal(self))

    @discord.ui.button(label="Add Image Proof", style=discord.ButtonStyle.secondary, emoji=EMOJI_IMAGE, row=1)
    async def add_image_btn(self, interaction: discord.Interaction, button: Button):
        if self.submitted:
            await self._send_temporary(interaction, embed=create_error_embed(f"{EMOJI_CROSS} Session Completed", "This session is already completed."))
            return
        
        await self._send_temporary(interaction, embed=discord.Embed(
                title="🖼️ Upload Proof Image",
                description="Please upload **one image attachment** in this channel within **5 minutes**.\n\n"
                            "• Only image files are allowed.\n"
                            "• Maximum of one image.\n"
                            "• Your uploaded image will be attached to your review as proof.\n"
                            "• If you upload another file type, it will be rejected.\n"
                            "• If no image is uploaded before timeout, you may still submit your review without one.",
                color=SUCCESS_COLOR
            ))
        
        try:
            message = await self.bot.wait_for(
                "message",
                check=lambda m: m.author.id == self.author.id and m.channel.id == interaction.channel.id,
                timeout=300.0
            )
            
            if len(message.attachments) != 1:
                error_title = f"{EMOJI_CROSS} Too Many Attachments" if len(message.attachments) > 1 else f"{EMOJI_CROSS} No Attachment Found"
                error_desc = "Please upload exactly one image." if len(message.attachments) > 1 else "No attachment was found. Please click on **Add Image Proof** button and upload image file."
                await self._send_temporary(interaction, embed=create_error_embed(error_title, error_desc))
                return
            
            attachment = message.attachments[0]
            if not (attachment.content_type and attachment.content_type.startswith("image/")):
                await self._send_temporary(interaction, embed=create_error_embed(
                        f"{EMOJI_CROSS} Invalid Attachment",
                        "Please upload one valid image file (PNG, JPG, JPEG, or WEBP)."
                    ))
                return
            
            self.image_url = attachment.url
            
            has_star = self.selected_stars is not None
            has_comment = bool(self.comment_text)
            
            if not has_star and not has_comment:
                embed = discord.Embed(
                    title="🖼️ Proof Image Recorded",
                    description="Your proof image has been attached successfully.\n\n"
                                "**Required Next Step:**\n"
                                "Please select a star rating before submitting your vouch.\n\n"
                                "**Optional:**\n"
                                "You may also add a review comment describing your experience.",
                    color=SUCCESS_COLOR
                )
            elif has_star and not has_comment:
                embed = discord.Embed(
                    title=f"{EMOJI_CHECK} Rating & Image Recorded",
                    description="Your star rating and proof image have both been recorded.\n\n"
                                "**Optional Next Step:**\n"
                                "You may add a review comment, or click **Submit Vouch** to finish.",
                    color=SUCCESS_COLOR
                )
            elif not has_star and has_comment:
                embed = discord.Embed(
                    title="🖼️ Review & Image Recorded",
                    description="Your review and proof image have both been recorded.\n\n"
                                "**Required Next Step:**\n"
                                "Please select a star rating before clicking **Submit Vouch**.",
                    color=SUCCESS_COLOR
                )
            else:
                embed = discord.Embed(
                    title=f"{EMOJI_CHECK} Rating, Review & Image Recorded",
                    description="Your star rating, review, and proof image have all been recorded.\n\n"
                                "You can now click **Submit Vouch** to publish your vouch.",
                    color=SUCCESS_COLOR
                )
            
            await self._send_temporary(interaction, embed=embed)
            
        except asyncio.TimeoutError:
            await self._send_temporary(interaction, embed=create_error_embed(
                    f"{EMOJI_CLOCK} Image Upload Timed Out",
                    "No image was uploaded within 5 minutes.\n\n"
                    "You may still complete and submit your vouch without attaching a proof image."
                ))

    @discord.ui.button(label="Submit Vouch", style=discord.ButtonStyle.green, emoji=EMOJI_VOUCH, row=1)
    async def submit_btn(self, interaction: discord.Interaction, button: Button):
        async with self._lock:
            if self.submitted:
                await self._send_temporary(interaction, embed=create_error_embed(f"Already Submitted", "This vouch has already been processed."))
                return

            if self.selected_stars is None:
                await self._send_temporary(interaction, embed=create_error_embed(f"Missing Rating", "Please select a star rating before submitting."))
                return

            self.submitted = True

            guild = interaction.guild
            if not guild:
                return

            vouch_channel_id = get_vouch_channel(str(guild.id))
            if not vouch_channel_id:
                self.submitted = False
                await self._send_temporary(interaction, embed=create_error_embed(f"Not Configured", "Vouch channel not configured."))
                return

            vouch_channel = guild.get_channel(vouch_channel_id)
            if not vouch_channel:
                self.submitted = False
                await self._send_temporary(interaction, embed=create_error_embed(f"Channel Missing", "Configured channel not found."))
                return

            vouch_id = get_server_vouch_count(str(self.seller.id), str(guild.id)) + 1
            add_vouch(str(self.seller.id), 1)

            add_vouch_history(str(self.seller.id), {
                "vouch_id": vouch_id,
                "customer": str(self.author.id),
                "item": self.item,
                "stars": self.selected_stars,
                "review": self.comment_text,
                "timestamp": int(time.time()),
                "guild_id": str(guild.id)
            })

            vouch_embed = create_vouch_embed(
                customer=self.author,
                seller=self.seller,
                item=self.item,
                stars=self.selected_stars,
                review=self.comment_text,
                vouch_id=vouch_id
            )
            
            if self.image_url:
                vouch_embed.set_image(url=self.image_url)

            try:
                await vouch_channel.send(embed=vouch_embed)

                for child in self.children:
                    child.disabled = True

                success_msg = f"**{EMOJI_CHECK} Vouch Submitted Successfully!**"
                if self.message:
                    await self.message.edit(view=self, content=success_msg)

                await interaction.response.send_message(
                    embed=create_success_embed(f"Success", "The vouch has been posted to the vouch channel."),
                    ephemeral=True
                )

            except discord.Forbidden:
                self.submitted = False
                await self._send_temporary(interaction, embed=create_error_embed(f"{EMOJI_CROSS} Permission Error", "Cannot send messages in vouch channel."))
            except discord.HTTPException:
                self.submitted = False
                await self._send_temporary(interaction, embed=create_error_embed(f"Send Error", "Failed to send message."))


# =============================================================================
# UI COMPONENTS FOR ITEM LIST PAGINATION
# =============================================================================

class ItemListView(View):
    def __init__(self, guild_id: str, items_per_page: int = 10):
        super().__init__(timeout=300.0)
        self.guild_id = guild_id
        self.items_per_page = items_per_page
        self.current_page = 0
        self.items = get_items(guild_id)
        self.total_pages = max(1, (len(self.items) + self.items_per_page - 1) // self.items_per_page)

        self.update_buttons()

    def update_buttons(self):
        self.prev_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page >= self.total_pages - 1

    def get_page_embed(self) -> discord.Embed:
        start_idx = self.current_page * self.items_per_page
        end_idx = min(start_idx + self.items_per_page, len(self.items))
        page_items = self.items[start_idx:end_idx]

        embed = discord.Embed(
            title=f"{EMOJI_CART} Server Registered Item List",
            description=f"{EMOJI_CART} Registered Items",
            color=VOUCH_COLOR
        )

        if not page_items:
            embed.add_field(name="No Items", value="No custom items registered yet.", inline=False)
        else:
            items_text = ""
            for item in page_items:
                items_text += f"{EMOJI_TAG} Item #{item['code']:03d}\n{item['name']}\n\n"
            embed.description = f"{EMOJI_CART} Registered Items\n\n{items_text}"

        # Add separator and footer info
        total_items = len(self.items)
        footer_text = f"━━━━━━━━━━━━━━━━━━━━\n\n📦 Registered Items: {total_items}\n\n💡 Manage your item list anytime through `/vouchsettings`.\n\nPage {self.current_page + 1}/{self.total_pages}"
        
        embed.set_footer(text=footer_text)
        return embed

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.gray, emoji="⬅️")
    async def prev_button(self, interaction: discord.Interaction, button: Button):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.get_page_embed(), view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.gray, emoji="➡️")
    async def next_button(self, interaction: discord.Interaction, button: Button):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.get_page_embed(), view=self)


# =============================================================================
# COG DEFINITION
# =============================================================================

class Vouch(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        DATA_FOLDER.mkdir(parents=True, exist_ok=True)

        if not ITEMS_FILE.exists():
            save_json(ITEMS_FILE, {})
        if not VOUCHES_FILE.exists():
            save_json(VOUCHES_FILE, {})
        if not CONFIG_FILE.exists():
            save_json(CONFIG_FILE, {})
        if not VOUCH_HISTORY_FILE.exists():
            save_json(VOUCH_HISTORY_FILE, {})

    async def item_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        if not interaction.guild_id:
            return []

        guild_id = str(interaction.guild_id)
        items = get_items(guild_id)
        current_lower = current.lower()

        matching_items = []
        for item in items:
            item_name = item['name'] if isinstance(item, dict) else item
            item_code = str(item.get('code', '')) if isinstance(item, dict) else ''

            # Search by name or code
            if current_lower in item_name.lower() or current_lower in item_code:
                matching_items.append(item)

            if len(matching_items) >= 25:
                break

        choices = []
        for item in matching_items:
            if isinstance(item, dict):
                # Display: "1: Product A"
                display_name = f"{item['code']}: {item['name']}"
                # Ensure display_name doesn't exceed 100 characters (Discord API limit)
                if len(display_name) > 100:
                    display_name = display_name[:97] + "..."
                # Value: "Product A" (Code stripped here)
                value = item['name']
            else:
                display_name = item
                value = item

            # Double-check length constraint
            if len(display_name) > 100:
                display_name = display_name[:97] + "..."
            if len(value) > 100:
                value = value[:100]

            choices.append(app_commands.Choice(name=display_name, value=value))

        return choices

    @app_commands.command(name="vouch", description="Submit a vouch for a service")
    @app_commands.describe(
        seller="The member who provided the service",
        item="The item or service purchased",
        vouched_by="Submit on behalf of another member (optional, display only)",
        stars="Rating from 1 to 5 stars",
        review="Optional review or comment (max 500 characters)",
        image="Optional proof image (PNG, JPG, JPEG, WEBP)"
    )
    @app_commands.choices(stars=[
        app_commands.Choice(name="1 Star", value=1),
        app_commands.Choice(name="2 Stars", value=2),
        app_commands.Choice(name="3 Stars", value=3),
        app_commands.Choice(name="4 Stars", value=4),
        app_commands.Choice(name="5 Stars", value=5),
    ])
    @app_commands.autocomplete(item=item_autocomplete)
    async def vouch_command(
        self,
        interaction: discord.Interaction,
        seller: discord.Member,
        item: str,
        stars: int,
        vouched_by: Optional[discord.Member] = None,
        review: Optional[str] = None,
        image: Optional[discord.Attachment] = None
    ) -> None:
        if not await check_guild_context(interaction):
            return

        guild = interaction.guild
        if guild is None:
            return

        # Prevent self-vouching
        if interaction.user.id == seller.id:
            await interaction.response.send_message(
                embed=create_error_embed(
                    f"{EMOJI_CROSS} Self-Vouch Not Allowed",
                    "You cannot submit a vouch for yourself. Please select another seller."
                ),
                ephemeral=True
            )
            return

        # Validate image attachment if provided
        image_url = None
        if image is not None:
            if not (image.content_type and image.content_type.startswith("image/")):
                await interaction.response.send_message(
                    embed=create_error_embed(
                        f"{EMOJI_CROSS} Invalid Attachment",
                        "Invalid attachment. Please upload a valid image file (PNG, JPG, JPEG, WEBP)."
                    ),
                    ephemeral=True
                )
                return
            image_url = image.url

        # Check if vouching is enabled for this server
        if not is_vouch_enabled(str(guild.id)):
            await interaction.response.send_message(
                embed=create_error_embed(
                    f"{EMOJI_CROSS} Vouch System Disabled",
                    "The vouching system is currently **disabled** for this server.\n\nPlease contact the server administrator if you have any questions."
                ),
                ephemeral=True
            )
            return

        # Check user cooldown for this server
        is_on_cooldown, remaining_seconds = check_user_cooldown(str(interaction.user.id), str(guild.id))
        if is_on_cooldown:
            mins = remaining_seconds // 60
            secs = remaining_seconds % 60
            await interaction.response.send_message(
                embed=create_error_embed(
                    f"Cooldown Active",
                    f"You are on cooldown. Please wait **{mins}m {secs}s** before submitting another vouch."
                ),
                ephemeral=True
            )
            return

        vouch_channel_id = get_vouch_channel(str(guild.id))
        if vouch_channel_id is None:
            await interaction.response.send_message(
                embed=create_error_embed(f"{EMOJI_CROSS} Not Configured", "No vouch channel configured. Contact the Server Administrator"),
                ephemeral=True
            )
            return

        vouch_channel = guild.get_channel(vouch_channel_id)
        if vouch_channel is None:
            await interaction.response.send_message(
                embed=create_error_embed(f"{EMOJI_CROSS} Channel Missing", "Configured channel not found."),
                ephemeral=True
            )
            return

        review_text = review.strip() if review else "No additional comments."
        if len(review_text) > 500:
            review_text = review_text[:500]

        vouch_id = get_server_vouch_count(str(seller.id), str(guild.id)) + 1
        add_vouch(str(seller.id), 1)

        # Save history with guild_id
        add_vouch_history(str(seller.id), {
            "vouch_id": vouch_id,
            "customer": str(interaction.user.id),
            "item": item.strip(),
            "stars": stars,
            "review": review_text,
            "timestamp": int(time.time()),
            "guild_id": str(guild.id)
        })

        # Set user cooldown after successful vouch
        set_user_cooldown(str(interaction.user.id), str(guild.id))

        vouch_embed = create_vouch_embed(
            customer=interaction.user,
            seller=seller,
            item=item,
            stars=stars,
            review=review_text,
            vouch_id=vouch_id,
            vouched_by_override=vouched_by
        )
        
        if image_url:
            vouch_embed.set_image(url=image_url)

        try:
            await vouch_channel.send(embed=vouch_embed)
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=create_error_embed(f"{EMOJI_CROSS} Permission Error", "No permission to send in vouch channel."),
                ephemeral=True
            )
            return
        except discord.HTTPException:
            await interaction.response.send_message(
                embed=create_error_embed(f"{EMOJI_CROSS} Send Error", "Failed to send message."),
                ephemeral=True
            )
            return

        success_embed = create_success_embed(
            title=f"Success",
            description=f"Your vouch has been submitted successfully."
        )

        await interaction.response.send_message(embed=success_embed, ephemeral=True)

    @vouch_command.error
    async def vouch_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, commands.MissingPermissions):
             await interaction.response.send_message(
                embed=create_error_embed(f"{EMOJI_CROSS} Permission Denied", "Missing permissions."),
                ephemeral=True
            )

    @app_commands.command(name="vouchstats", description="View vouch statistics for a user")
    @app_commands.describe(member="The member to view stats for (defaults to you)")
    async def vouchstats_command(
        self,
        interaction: discord.Interaction,
        member: Optional[discord.Member] = None
    ) -> None:
        if not await check_guild_context(interaction):
            return

        if member is None:
            member = interaction.user

        guild = interaction.guild
        if guild is None:
            return

        # Get server-specific vouch count and stats
        total_vouches = get_server_vouch_count(str(member.id), str(guild.id))
        avg_rating = calculate_server_average_rating(str(member.id), str(guild.id))
        history = get_server_vouch_history(str(member.id), str(guild.id), limit=5)

        embed = discord.Embed(
            title=f"{EMOJI_STATS} Vouch Statistics",
            description=f"Stats for {member.mention}",
            color=VOUCH_COLOR
        )
        embed.set_thumbnail(url=member.display_avatar.url)

        embed.add_field(name=f"{EMOJI_STAR} Total Vouches", value=str(total_vouches), inline=True)
        embed.add_field(name=f"{EMOJI_STAR} Average Rating", value=f"{avg_rating}/5.0" if avg_rating > 0 else "N/A", inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)

        if history:
            history_text = ""
            for h in history:
                stars_display = EMOJI_STAR * h['stars'] + "☆" * (5 - h['stars'])
                entry = f"{EMOJI_TAG} `#{h['vouch_id']:05d}`\n{EMOJI_STAR} Rating: {stars_display}\n{EMOJI_CART} {h['item']}\n\n"
                # Check if adding this entry would exceed Discord's 1024 char limit
                if len(history_text) + len(entry) > 1024:
                    break
                history_text += entry

            embed.add_field(name=f"{EMOJI_REVIEW} Recent Vouches", value=history_text or "None", inline=False)
        else:
            embed.add_field(name=f"{EMOJI_REVIEW} Recent Vouches", value="No vouch history found.", inline=False)

        embed.set_footer(text=FOOTER_TEXT)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="tradervouch", description="Admin tool to facilitate a vouch with buttons")
    @app_commands.describe(
        seller="The seller receiving the vouch",
        buyer="The buyer who made the purchase",
        item="The item sold"
    )
    @app_commands.autocomplete(item=item_autocomplete)
    async def tradervouch_command(
        self,
        interaction: discord.Interaction,
        seller: discord.Member,
        buyer: discord.Member,
        item: str
    ) -> None:
        if not await check_guild_context(interaction):
            return

        # Check if user is server administrator
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                embed=create_error_embed(f"{EMOJI_CROSS} Permission Denied", "This command is reserved for server administrators only."),
                ephemeral=True
            )
            return

        guild = interaction.guild
        if not guild:
            return

        # Check if vouching is enabled for this server
        if not is_vouch_enabled(str(guild.id)):
            await interaction.response.send_message(
                embed=create_error_embed(
                    f"{EMOJI_CROSS} Vouch System Disabled",
                    "The vouching system is currently **disabled** for this server.\n\nPlease contact the server administrator if you have any questions."
                ),
                ephemeral=True
            )
            return

        vouch_channel_id = get_vouch_channel(str(guild.id))
        if not vouch_channel_id:
            await interaction.response.send_message(
                embed=create_error_embed(f"Not Configured", "Please run `/vouchsetup` first."),
                ephemeral=True
            )
            return

        view = TraderVouchView(self.bot, seller, item.strip(), buyer)

        embed = discord.Embed(
            title=f"{EMOJI_CART} Customer Feedback Request",
            description=f"Facilitated by {interaction.user.mention}\n\n"
                        f"**Seller:** {seller.mention}\n"
                        f"**Item:** {item}\n\n"
                        f"⭐ Rate your experience below and leave a review comment (optional).",
            color=VOUCH_COLOR
        )
        embed.set_footer(text="This session expires in 5 minutes")

        # Mention buyer outside the embed so they get notified
        await interaction.response.send_message(
            content=f"{buyer.mention}",
            embed=embed,
            view=view
        )

        # Fix: Get the message properly after sending
        view.message = await interaction.original_response()

    @tradervouch_command.error
    async def tradervouch_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, commands.MissingPermissions):
            await interaction.response.send_message(
                embed=create_error_embed(f"{EMOJI_CROSS} Permission Denied", "Administrators only."),
                ephemeral=True
            )

    @app_commands.command(name="vouchsetup", description="Configure the vouch channel")
    @app_commands.describe(channel="The channel for vouches")
    async def vouchsetup_command(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        if not await check_guild_context(interaction):
            return

        if not interaction.guild:
            return

        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                embed=create_error_embed(f"{EMOJI_CROSS} Permission Denied", "This command is reserved for server administrators only."),
                ephemeral=True
            )
            return

        set_vouch_channel(str(interaction.guild.id), channel.id)
        await interaction.response.send_message(
            embed=create_success_embed(f"Updated", f"Vouch channel set to {channel.mention}"),
            ephemeral=True
        )

    @app_commands.command(name="vouchsetting", description="Manage server items and cooldown with buttons")
    async def vouchsetting_command(self, interaction: discord.Interaction) -> None:
        if not await check_guild_context(interaction):
            return

        if not interaction.guild:
            return

        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                embed=create_error_embed(f"{EMOJI_CROSS} Permission Denied", "This command is reserved for server administrators only."),
                ephemeral=True
            )
            return

        guild_id = str(interaction.guild.id)
        
        embed = create_vouch_settings_embed(guild_id)

        view = VouchSettingView(guild_id)
        await interaction.response.send_message(embed=embed, view=view)
        # Store reference to the original message for in-place edits
        view.original_message = await interaction.original_response()


    @app_commands.command(name="listitems", description="View all registered items for this server")
    async def listitems_command(self, interaction: discord.Interaction) -> None:
        if not await check_guild_context(interaction):
            return

        if not interaction.guild:
            return

        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                embed=create_error_embed(f"{EMOJI_CROSS} Permission Denied", "This command is reserved for server administrators only."),
                ephemeral=True
            )
            return

        guild_id = str(interaction.guild.id)
        view = ItemListView(guild_id, items_per_page=10)
        embed = view.get_page_embed()

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Vouch(bot))
