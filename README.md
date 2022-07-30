# Brent's cogs
Cogs made by @brenticus for use with [Red](https://discord.red).

# Installation
Run the following command on your bot:

`[p]repo add brent-cogs https://github.com/BrenTicus/brent-cogs main`

You can then run the following (replacing `cog-name` with the name of the cog you want to install) for whatever cog you want:

`[p]cog install brent-cogs cog-name
[p]load cog-name`

## Updating
To update one of the cogs, run the following command on your bot and then hit the checkmark reaction to reload the cog:

`[p]cog update cog-name`

Or omit the cog name to update everything from everywhere. It's probably safe, I don't know, use your judgment.

# Cogs
You can run `[p]help cog-name` to get most of this.

## Snitch
Notify groups of users, roles, or channels when certain phrases are said. The base command is `snitch`.
* `snitch clear` - Wipe out all config data.
* `snitch list` - Send a list of this server's people and words involved in snitching.
* `snitch clear [group]` - Remove all config data for the group. Omit the group to clear all config data for this cog.
* `snitch to [group_name] [user or role or channel...]` - Add people, roles, or channels to a notification group.
* `snitch notto [group_name] [user or role or channel...]` - Remove people, roles, or channels from a notification group.
* `snitch on [group_name] [words...]` - Add trigger words to a notification group.
* `snitch noton [group_name] [words...]` - Remove trigger words from the notification group. 
* `snitch with [group_name] "[message]"` - Change the message sent with your snitch. Use double quotes around the message.

### `with` Tokens
Put these strings in your message and they'll be replaced with appropriate values.
* `{{author}}` - The display name of the message author.
* `{{channel}} `- The channel name the message originated in.
* `{{server}}` - The server name the message originated in.
* `{{words}}` - The list of words that triggered the message.

## Recorder
Save all messages in the server to a log file. Broken up by channel and server name.

Goes into the Red data directory for your instance. On Linux the path will look something like `~/.local/share/Red-DiscordBot/data/instance/cogs/Recorder`.