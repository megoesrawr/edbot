import configparser
import asyncio
import logging
from datetime import datetime

import discord

# import plugin modules
from edbot.plugins.help import help
from edbot.plugins.flip import flip
from edbot.plugins.gif import gif
from edbot.plugins.joke import joke
from edbot.plugins.range import range as prange
from edbot.plugins.rpg import rpg
from edbot.plugins.school import school
from edbot.plugins.server import server
from edbot.plugins.stats import stats

# rpg2 plugin
from edbot.plugins.rpg_v2 import rpg2

# from edbot.plugins.member_join import member_join

# setup logging system for logging to console/file
# create a timestamp when program starts
timestamp = datetime.now().strftime("%Y-%m-%d %H-%M-%S")
time = datetime.strptime(timestamp, "%Y-%m-%d %H-%M-%S")

# setup base logger var
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# create formatter used before every log entry
formatter = logging.Formatter('%(asctime)s | %(levelname)s --- %(message)s')

# create file handler with unique name on startup
fh = logging.FileHandler("logs/{}.log".format(str(timestamp)))
fh.setLevel(logging.DEBUG)
fh.setFormatter(formatter)
logger.addHandler(fh)

# create stream handler. put logger info into console as well as file created.
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(formatter)
logger.addHandler(ch)

# setup configparser
config_file = configparser.ConfigParser()
try:
    config_file.read('config/config.ini')
except configparser.Error as cperr:
    logger.error("Error while trying to read config.ini: [{}]".format(str(cperr)))

# create base client variable
client = discord.Client()


# when client connects and bot is ready
@client.event
@asyncio.coroutine
def on_ready():
    logger.info("LOGGED IN AS USER: {} | ID: {}".format(client.user.name, client.user.id))


# main on_message method, when a message is sent to the discord server, it is parsed and checked to see
# if the content in the message starts with, or matches the logic below.
# many of the methods called are done so from the 'plugins' library.
@client.event
@asyncio.coroutine
def on_message(message):

    ################
    # FUN COMMANDS #
    ################

    # if message is ed.flip
    if message.content == 'ed.flip':
        current_flip = flip.coin_flip(logger, message.author.name)
        yield from client.send_message(message.channel, current_flip)
        stats.set_stat('flip', config_file)

    # if message starts with ed.range
    elif message.content.startswith('ed.range'):
        yield from client.send_message(message.channel, prange.pick_number(message.content, logger))
        stats.set_stat('range', config_file)

    # if message is ed.joke
    elif message.content == 'ed.joke':
        yield from client.send_message(message.channel, joke.get_joke(logger))
        stats.set_stat('joke', config_file)

    elif message.content.startswith('ed.gif'):
        yield from client.send_message(message.channel, gif.get_gif_url(message.content, logger, message.author))
        stats.set_stat('gif', config_file)

    # early version of rpg plugin
    # if message is ed.rpg
    elif message.content == 'ed.rpg':
        yield from client.send_message(message.channel, embed=rpg.generate_character(message.author))
        stats.set_stat('rpg', config_file)

    # if message is ed.school
    elif message.content == 'ed.school':
        yield from client.send_message(message.channel, school.school_start())
        stats.set_stat('school', config_file)

    ########################
    # INFORMATION COMMANDS #
    ########################

    # if message is ed.server
    elif message.content == 'ed.server':
        yield from client.send_message(message.channel, embed=server.get_server_information(message.server))
        stats.set_stat('server', config_file)

    # if message is ed.help
    elif message.content == 'ed.help':
        em = help.create_help_embed(client.user.avatar_url)
        yield from client.send_message(message.author, embed=em)
        stats.set_stat('help', config_file)

    elif message.content == 'ed.stats':
        stats.set_stat('stat', config_file)
        yield from client.send_message(message.channel,
                                       embed=stats.get_stats(config_file, client.user.avatar_url, time))

    ###################
    # RPG V2 COMMANDS #
    ###################

    # if message is ed.rpg2
    # this is the main rpg2 plugin command, if a author has a character currently, it will display there player
    # if they do not have a character, generate a random one for them
    elif message.content == 'ed.rpg2':
        # first check if the user already has a character currently
        auth = rpg2.config(logger)
        exists = rpg2.check_for_existing_char(rpg2.db_connect(logger, auth), message.author.id)

        # if a character exists in the database already with the same message.author.id, user already has a
        # generated character, create embeddable message for this specific character.
        if exists:
            em = rpg2.embed_existing_character(rpg2.db_connect(logger, auth), message.author.id)
            yield from client.send_message(message.channel, embed=em)

        # if a player does not exist in the database with the same message.author.id, user has no character,
        # generate one for them, and make it embeddable.
        else:
            # generate a player for the message senders unique id, adding it to the database
            rpg2.generate_new_character(rpg2.db_connect(logger, auth), message.author.id, message.author,
                                        message.server.name, logger)

            yield from client.send_message(message.channel,
                                           "You don't have a character yet, I've generated one for you!")

            # create embeddable message containing all information about the player created for message author
            em = rpg2.embed_existing_character(rpg2.db_connect(logger, auth), message.author.id)
            yield from client.send_message(message.channel, embed=em)

    # if message is ed.rpg2.fight
    # generate a random enemy for the author's character to fight, if the player is killed, their player is
    # permanently deleted, but stored separately to track fallen heroes
    elif message.content == 'ed.rpg2.fight':
        # first check if the user has character already created
        auth = rpg2.config(logger)
        exists = rpg2.check_for_existing_char(rpg2.db_connect(logger, auth), message.author.id)

        if exists:
            msg = rpg2.fight_monster(rpg2.db_connect(logger, auth), message.author.id)
            yield from client.send_message(message.channel, msg)
        else:
            yield from client.send_message(message.channel, "You don't seem to have a character yet, type ed.rpg2 to"
                                                            " generate one!")

    # if message is ed.rpg2.potion
    # attempt to heal the player by using one of their potions
    elif message.content == 'ed.rpg2.potion':
        # first check if the user has character already created
        auth = rpg2.config(logger)
        exists = rpg2.check_for_existing_char(rpg2.db_connect(logger, auth), message.author.id)

        if exists:
            msg = rpg2.use_potion(rpg2.db_connect(logger, auth), message.author.id)
            yield from client.send_message(message.channel, msg)
        else:
            yield from client.send_message(message.channel, "You can't use a potion because you don't have a character!"
                                                            " Type ed.rpg to generate one.")
    # if message is ed.rpg2.freepotion
    # check the timer on author free potion field in db, if it has surpassed the current time, give them 1 free potion
    elif message.content == 'ed.rpg2.freepotion':
        # first check if the user has character already created
        auth = rpg2.config(logger)
        exists = rpg2.check_for_existing_char(rpg2.db_connect(logger, auth), message.author.id)

        if exists:
            msg = rpg2.get_free_potion(rpg2.db_connect(logger, auth), message.author.id)
            yield from client.send_message(message.channel, msg)
        else:
            yield from client.send_message(message.channel, "You can't use a potion because you don't have a character!"
                                                            " Type ed.rpg to generate one.")

    # if message is ed.epg2.leaders
    # display the current leader boards for all characters still alive
    elif message.content == 'ed.rpg2.leaders':
        auth = rpg2.config(logger)
        em = rpg2.gen_leader_embeds(rpg2.db_connect(logger, auth))
        yield from client.send_message(message.channel, embed=em)

    # if message is ed.epg2.fallen
    # display the current leader boards for all characters that have been defeated
    elif message.content == 'ed.rpg2.fallen':
        auth = rpg2.config(logger)
        em = rpg2.gen_fallen_heroes_embed(rpg2.db_connect(logger, auth))
        yield from client.send_message(message.channel, embed=em)

    # if message starts with ed.rpg2.duel
    # attempt to fight another player the exists
    elif message.content.startswith('ed.rpg2.duel'):
        # first check if the user has character already created
        auth = rpg2.config(logger)

        # check if author has a character before doing anything else
        exists = rpg2.check_for_existing_char(rpg2.db_connect(logger, auth), message.author.id)
        if exists:
            # check now if the target also has a character to fight
            target_id = rpg2.get_target_id(message)
            # if the author is trying to fight there own character
            if target_id == message.author.id:
                yield from client.send_message(message.channel, "You can't duel yourself!")
                return
            target_exists = rpg2.check_for_existing_char(rpg2.db_connect(logger, auth), target_id)
            if target_exists:
                em = rpg2.fight_player(rpg2.db_connect(logger, auth), message.author.id, message)
                yield from client.send_message(message.channel, embed=em)
                return
            else:
                msg = rpg2.fight_player(rpg2.db_connect(logger, auth), message.author.id, message)
                yield from client.send_message(message.channel, msg)
                return
        else:
            yield from client.send_message(message.channel, "You don't have a character to duel anyone at the moment!"
                                                            " Type ed.rpg2 to generate one.")
            return


# attempt to connect client to discord using the discord token located in config.ini file
try:
    client.run(config_file.get('Discord', 'token'))
# in case any error is thrown, log the error
except client.on_error as coeerr:
    logger.error("client.run error: [{}]".format(str(coeerr)))

