### Examples (revised for V0.3.0)
# note that you should always have a unique name for your extension folder.
# here, i will assume its called "extension_example"
import sys, os
sys.path.append(os.path.dirname(__file__)) # add your folder to sys.path
import extension_example as ext

bot = ext.Bot()
# note that the bot injects the required Tick, Init, and Execute functions, plus SettingsReload. Do not include these in your script yourself.

# Bot takes quite a few keyword arguments.
# you can pass a custom Settings class with (more on settings at the bottom)
class MySettings(ext.Settings):
    mysetting = "hi"

ext.Bot(settings=MySettings) # note that you do not initialize the class

# pass a different prefix by doing (defaults to !)
ext.Bot(command_prefix="?")

# enable debug on the bot (gives info on event dispatches and the like. also enables a special "dev" command group)
ext.Bot(enable_debug=True)

# the dev command group can be used by doing `!dev {subcommand}` in your chat.
# the dev command currently has the `sudo` command, which runs another command, bypassing all checks and cooldowns
# and the `su` command, which can be used to run a command as someone else.

##########

# bot allows you to "listen" to events, such as on_init, on_message, etc (a full list can be found at further down.
# as mentioned above, the bot injects the required Init, Tick, and Execute functions, plus SettingsReload. DO NOT implement them yourself!!
# But for this to work properly, you must have at least *one* listener in your main script.
@bot.listen()
def on_init():
    # do init stuff here
    pass

@bot.listen()
def on_message(data):
    # do message stuff here, but dont do commands here!
    pass


##########

# Bot also allows for commands, with full parameter parsing and cooldown support
# by default the command is named after your function

@bot.command()
def hello(msg): # triggered with !hello
    pass

# you can change this by doing

@bot.command("hello")
def something(msg): # still triggered with !hello
    pass

# you can apply cooldowns by doing
@bot.command()
@ext.user_cooldown(5, 1) # each user can only trigger this command once every 5 seconds
def mycommand(msg):
    pass

# or
@bot.command()
@ext.global_cooldown(5, 1) #this can only be triggered once every 5 seconds
def mycommand(msg):
    pass

# commands must take at least one argument (excluding `self` if in a class), this is the ext.Message object.
# it contains some info on the user that ran the command, where it was invoked, etc
@bot.command()
def reply(msg):
    msg.reply("I'm Alive!") # replies to where the command was invoked from

# commands can also take parameters
# all parameters must have defaults, as that is how they are processed.
# parameters will be converted to the default's type, IE

@bot.command()
def parameters(msg, arg1=str, arg2=bool): # doing arg1="", arg2=True) etc. will also work
    msg.reply(arg1 + str(arg2))

@bot.command()
def moreparameters(msg, arg1=ext.User, arg2=ext.Optional[str]):
    # defaulting to ext.User means that the bot will attempt to find a viewer with the given name, otherwise it will raise an error (see: error handling)
    # using the ext.Optional default will try to give you the given type (in this case a string), but it if cannot be converted, it will become None.
    pass

@bot.command()
def evenmoreparameters(msg, arg1=ext.Union[ext.User, str], arg2=ext.RestOfInput):
    # the Union default can be passed multiple values, it will try, in order, to convert it to one of the given options,
    # otherwise will raise UnionConversionError.
    # the RestOfInput default *must* be the last argument, as it will be given the rest of the input from the user
    pass

#######

# error handling

# there are two types of error handlers in this library, on_error, and on_command_error.
# on_error will be called when a listener raises an error.
# on_command_error will be called when a command raises an error (including during parsing)

@bot.listen()
def on_error(error, traceback):
    # do things with the exception and traceback
    pass

@bot.listen()
def on_command_error(msg, error, tb):
    # do things with the Message object, the error, and the traceback
    import traceback
    tb = "".join(traceback.format_exception(type(error), error, tb))
    bot.log("error while running command {0}: {1}".format(msg.command.qualified_name, tb))
    msg.reply("whoops! something happened!")

############

# stream events

# stream events can be accessed by having a StreamlabsEventToken textbox in your UI_Config.json, which, when a token is passed,
# will enable the event listener. here are the events it will produce

@bot.listen()
def on_event_connect():
    # dispatched when the socket connects
    pass

@bot.listen()
def on_event_disconnect():
    # dispatched when the socket disconnects
    pass

@bot.listen()
def on_follow(user):
    # takes an ext.User as its only argument
    pass

@bot.listen()
def on_cheer(user, message, amount):
    # its not rocket science
    pass

@bot.listen()
def on_gift_sub(user, gifter):
    # gifter could be None
    pass

@bot.listen()
def on_streak_sub(user, months, streak_months):
    # still not rocket science
    pass

@bot.listen()
def on_resub(user, months, tier):
    # tier is either 1000, 2000, or 3000 (#blametwitch)
    pass

@bot.listen()
def on_sub(user, tier):
    pass

@bot.listen()
def on_donation(user, amount, currency):
    # amount is a float, unsure what currency is (i cant test it as im not affilate nor do i have a viewerbase)
    pass

@bot.listen()
def on_raid(raider_name, count):
    # note that raider_name is the users name, not a User object
    # also note that raids are parsed via IRC, not the socket
    pass

@bot.listen()
def on_event_receive(sender, args):
    # the direct websocket info, dispatched whenever an event is received from the websocket
    pass


#### other events

# on_init()
# on_message(data)
# on_tick()
# on_settings_reload(settings)
# on_raw_receive(irc_data)


### settings

# settings are automatically pulled from your UI_Config.json/settings.json (or whatever your output_file is set to)
# you can access them via
bot.settings.FieldName
# where FieldName is the key in your UI_Config

#### nodes

# nodes can be created to make your code nicer, or to have commands in other files and batch load them into your bot

class MyNode(ext.Node):
    def __init__(self, bot):
        self.bot = bot
        ext.Node.__init__(self)

    @ext.command() # note that you do not use the bot.command decorator here
    def mycommand(self, msg, parameters=str):
        # do stuff
        pass

# and can be added to the bot using
bot.add_node(MyNode(bot))
