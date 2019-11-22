##### A basic bot #####
# note that this file is not intended to run, but to show how things work
import chatbot

bot = chatbot.Bot("!") # requires one argument, the prefix.

def Init():
    bot.init(Parent) # this is really the only place you need to have Parent, the rest of the time you can use chatbot.parent,
    # to ease your linters anger.
def Unload():
    # You MUST delete your bot instance. ironpython does something weird where it will keep the instance alive through reloads,
    # and reuse your bot instance. to prevent this, you must delete it by removing all alive references.
    global bot
    bot = None

@bot.command()
def hello(msg):
    """
    this command takes no parameters.
    """
    msg.reply("hi! Im a robot! I can see that you are {0} and have {1} {2}".format(msg.author.name, msg.author.points, msg.bot.currencyname))
    # you can access your settings through bot.settings, it will automatically pull data from your UI_Config,
    # and settings.json . see the notes at the bottom about settings and streamlabs events.
    some_setting = msg.bot.settings.mysetting
    msg.reply("your setting: "+some_setting)


#### using settings to define a command name ####
# here, it will pull from your UI_Config.json, and find the setting with the name youve given.
# if the output_file doesnt exist, it will set the name to the default given in the UI_Config

# lets imagine we have a UI_Config with a textbox named "welcome_command". note that this is NOT the textbox name.

@bot.command("settings:welcome_command")
def welcome_command(msg):
    msg.reply(msg.command.name)


#### here we start working with arguments ####

@bot.command()
def some_command(msg, firstarg=str, secondarg=int, rest=chatbot.RestOfInput(str)):
    # arguments are split by spaces, multi-word input can be given by "quoting it".
    # each argument MUST have a default, as the bot will convert each argument, and will fail to add the command
    # if defaults are missing. if you miss a default, it will do something like:
    # def thing(msg, argument=str, anotherargument, somethingelse=bool):
    # will become
    # def thing(msg, argument=str, anotherargument=bool, somethingelse=error raised!):
    msg.reply(firstarg)

#this expects input as such:
#!some_command first_argument 5 anything past the number goes to the third argument!
#passing a non-number to the number will raise an error. we will go over error handling later
#!some_command hi hello otherstuff
#will raise ConversionError, which subclasses UserInputError


#### cooldowns and permissions ####

# adding a per-user cooldown

@chatbot.user_cooldown(1, per=5)
@bot.command()
def cooldown_example(msg):
    """
    a user can trigger me once every 5 seconds!
    """
    pass

# adding a global cooldown

@chatbot.global_cooldown(1, per=5)
@bot.command()
def global_cooldown_example(msg):
    """
    i can be triggered once every 5 seconds!
    """
    pass

# requiring permissions

@chatbot.check_editor()
@bot.command("editor_required")
def thingy(msg):
    """
    you must be an editor to use me!
    """
    pass

@chatbot.settings_permission("permissionSetting")
def changable_permission(msg):
    pass

# custom checks
@chatbot.check(lambda msg: return msg.author.name != "test_dummy")
@bot.command()
def check_example(msg):
    """
    if the checks fail (including permissions checks), ChecksFailed will be raised, and will need handling (see below)
    """

#### error handling ####
# there are 2 different error handlers. on_error and on_command_error
# they are both events, and cannot have listeners (more than one function that recieves the event)

# command_error takes 2 arguments, the message object, and the error that was raised.

@bot.event
def on_command_error(msg, error):
    if isinstance(error, chatbot.UserInputError):
        return msg.reply("Bad Input!")
    if isinstance(error, chatbot.ChecksFailed):
        return msg.reply("You do not have permission to use this command!")
    if isinstance(error, chatbot.CommandOnCooldown):
        return msg.reply("This command is still on cooldown for {0} more seconds!".format(error.retry_after))
    if isinstance(error, chatbot.CommandError): #other error messages
        return msg.reply(error.message)

# error takes 1 argument, the error. this is for errors that happen anywhere other than commands.

@bot.event
def on_error(error):
    bot.log(ScriptName, "error! "+error.message)


### events ####
# all of the twitch events can be recieved through the bot.
# on_raid will always be recievable, as it is done via twitch IRC parsing (thanks for the regex, Kruiser8!).
# but all others; on_streak_sub, on_resub, on_sub ,on_follow, on_bits, on_donation
# are done through the streamlabs event socket, and require your user to have their stremalabs token in the settings.json,
# the textbox MUST be named StreamlabsEventToken for the bot to detect it.
# all events recieved through the event socket will be sent to on_event_recieve as well as their individual handlers.

# events can be set 2 ways. bot.event and bot.listener(). you can have multiple listeners, but there can only be one event function.

@bot.event
def on_sub(username):
    bot.stream.send(username + " has just subscribed!")

# this is a full list of the events that exist right now, plus the ones listed above
# on_init ()
# on_unload ()
# on_settings_reload (dict)
# on_tick ()
# on_message (data)
