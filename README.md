HOW TO USE

1. Installing Dependencies
 Go to treenan bot\dependencies. 
 1.1 Download and install python from a shortcut
 1.2 Run dependencies.bat 
  if doesn't work, open command prompt and run
  pip install discord
  pip install requests
  pip install asyncio

2. Make the application.
 Go to discord's developer portal: https://discord.com/developers/
 2.1 Create a new application, customize it to your liking.
 2.2 Go to bot tab, reset your token and ENABLE all 3 INTENTS.
 2.3 Invite the bot to your server using this link: https://discord.com/api/oauth2/authorize?client_id=YOUR_BOT_ID&permissions=8&scope=bot%20applications.commands

3. Setting up the bot.
 Go to treenan bot\bot 
 3.1 Open the environment (.env) in any editor that works for you (DO NOT RENAME IT!!!)
 Replace every variable with yours
  Notable: TRUSTED_ROLE_ID - id of an admin role or whatever role u want to allow to start events
           RESULTS_CHANNEL_ID - channel id of where the tournament results will go
           GEXP_CHANNEL_ID - ur commands channel id
           HYPIXEL_API_KEY - use if u want to include -gexp, -membergexp, -link commands. You can still use -link with some changes, 
           but it wont check if the member actually owns the account (e.g. I can do -link Dewier and it will work)
 3.2 Once you finished editing the environment, open the start.bat file IN AN EDITOR, replace line 4 with:
           C:\Users\your\bot\directory\ (e.g. C:\Users\you\Desktop\Projects\Bots\treenan bot\bot). MAKE SURE IT ENDS WITH BOT, NOT TREENAN BOT,
 then save the file.

4. Running the bot.
 Run the start.bat file every time you start your PC, if youre hosting it on a server, you probably know what ur doing so do that.

* if u wanna use the key refresher script I made, follow the same instructions. idk if it even works but if it does - nice!!!
