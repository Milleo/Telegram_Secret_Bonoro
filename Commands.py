# coding: utf-8

import json
import logging as log

import datetime



from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode


import MainController
import GamesController
from Constants.Config import STATS
from Boardgamebox.Board import Board
from Boardgamebox.Game import Game
from Boardgamebox.Player import Player
from Constants.Config import ADMIN

# Enable logging
log.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                level=log.INFO,
                filename='logs/logging.log')

logger = log.getLogger(__name__)

commands = [  # command description used in the "help" command
    '/ajuda - Informações de todos os comandos do bot',
    '/start - Um pequeno guia sobre o secret bonoro',
    '/simbolos - Mostra todos os ícones do tabuleiro',
    '/regras - Link para o PDF oficial do Secret Hitler',
    '/novojogo - Cria um novo jogo',
    '/participar - Participa do jogo criado',
    '/comecarjogo - Começa um jogo assim que todos os jogadores já marcaram para participar',
    '/cancelarjogo - Cancela o jogo em andamento.',
    '/tabuleiro - Mostra a situação atual: ordem de presidentes, políticas eleitas e etc.',
    '/votos - Mostra quem já votou',
    '/vempraurna - Chama os jogadores para votar'
]

symbols = [
    u"\u25FB\uFE0F" + ' Nada, porra nenhuma ',
    u"\u2716\uFE0F" + ' Carta',  # X
    u"\U0001F52E" + ' Poder presidencial: Mãe de ná, ver as próximas cartas',  # crystal
    u"\U0001F468" + ' Poder presidential: Lava-Jato, ver se é petralha ou não',  # inspection glass
    u"\U0001F52B" + ' Poder presidencial: Meter a azeitona',  # knife
    u"\U0001F9DB" + ' Poder presidencial: Acusar o golpe, indicar um amiguinho pra presidente',  # tie
    u"\u2692" + ' Petralhada ganhou, Pablo Vittar nas notas de R$50,00',  # dove
    u"\u2620" + ' Bonoro ganhou, #NovaEra'  # skull
]


def command_symbols(bot, update):
    cid = update.message.chat_id
    symbol_text = "Estes símbolos vão aparecer no tabuleiro: \n"
    for i in symbols:
        symbol_text += i + "\n"
    bot.send_message(cid, symbol_text)


def command_board(bot, update):
    cid = update.message.chat_id
    if cid in GamesController.games.keys():
        if GamesController.games[cid].board:
            bot.send_message(cid, GamesController.games[cid].board.print_board())
        else:
            bot.send_message(cid, "Não tem nenhum jogo em andamento no chat. Para começar digite /iniciarjogo")
    else:
        bot.send_message(cid, "Não tem nenhum jogo criado neste chat. Crie um novo jogo digitando /novojogo")


def command_start(bot, update):
    cid = update.message.chat_id
    bot.send_message(cid,
                     "\"Secret Hitler is a social deduction game for 5-10 people about finding and stopping the Secret Hitler."
                     " The majority of players are liberals. If they can learn to trust each other, they have enough "
                     "votes to control the table and win the game. But some players are fascists. They will say whatever "
                     "it takes to get elected, enact their agenda, and blame others for the fallout. The liberals must "
                     "work together to discover the truth before the fascists install their cold-blooded leader and win "
                     "the game.\"\n- official description of Secret Hitler\n\nAdd me to a group and type /newgame to create a game!")
    command_ajuda(bot, update)


def command_regras(bot, update):
    cid = update.message.chat_id
    btn = [[InlineKeyboardButton("Rules", url="http://www.secrethitler.com/assets/Secret_Hitler_Rules.pdf")]]
    rulesMarkup = InlineKeyboardMarkup(btn)
    bot.send_message(cid, "Leia as regras oficiais do Secret Hitler:", reply_markup=rulesMarkup)


# pings the bot
def command_ping(bot, update):
    cid = update.message.chat_id
    bot.send_message(cid, 'pong - v0.4')


# prints statistics, only ADMIN
def command_stats(bot, update):
    cid = update.message.chat_id
    if cid == ADMIN:
        with open(STATS, 'r') as f:
            stats = json.load(f)
        stattext = "+++ Estatísticas +++\n" + \
                    "Petralhas Ganharam (políticas): " + str(stats.get("libwin_policies")) + "\n" + \
                    "Petralhas Ganharam (esfaquearam o Bonoro): " + str(stats.get("libwin_kill")) + "\n" + \
                    "Fapistas Ganharam (politicas): " + str(stats.get("fascwin_policies")) + "\n" + \
                    "Fapistas Ganharam (Bonoro Presidento): " + str(stats.get("fascwin_hitler")) + "\n" + \
                    "Moiaram o jogo: " + str(stats.get("cancelled")) + "\n\n" + \
                    "Quantidade de grupos: " + str(len(stats.get("groups"))) + "\n" + \
                    "Jogos rolando agora: "
        bot.send_message(cid, stattext)


# help page
def command_ajuda(bot, update):
    cid = update.message.chat_id
    help_text = "Comandos:\n"
    for i in commands:
        help_text += i + "\n"
    bot.send_message(cid, help_text)


def command_novojogo(bot, update):
    cid = update.message.chat_id
    game = GamesController.games.get(cid, None)
    groupType = update.message.chat.type
    if groupType not in ['group', 'supergroup']:
        bot.send_message(cid, "You have to add me to a group first and type /newgame there!")
    elif game:
        bot.send_message(cid, "There is currently a game running. If you want to end it please type /cancelgame!")
    else:
        GamesController.games[cid] = Game(cid, update.message.from_user.id)
        with open(STATS, 'r') as f:
            stats = json.load(f)
        if cid not in stats.get("groups"):
            stats.get("groups").append(cid)
            with open(STATS, 'w') as f:
                json.dump(stats, f)
        bot.send_message(cid, "New game created! Each player has to /join the game.\nThe initiator of this game (or the admin) can /join too and type /startgame when everyone has joined the game!")


def command_participar(bot, update):
    groupName = update.message.chat.title
    cid = update.message.chat_id
    groupType = update.message.chat.type
    game = GamesController.games.get(cid, None)
    fname = update.message.from_user.first_name

    if groupType not in ['group', 'supergroup']:
        bot.send_message(cid, "You have to add me to a group first and type /newgame there!")
    elif not game:
        bot.send_message(cid, "There is no game in this chat. Create a new game with /newgame")
    elif game.board:
        bot.send_message(cid, "The game has started. Please wait for the next game!")
    elif update.message.from_user.id in game.playerlist:
        bot.send_message(game.cid, "You already joined the game, %s!" % fname)
    elif len(game.playerlist) >= 10:
        bot.send_message(game.cid, "You have reached the maximum amount of players. Please start the game with /startgame!")
    else:
        uid = update.message.from_user.id
        player = Player(fname, uid)
        try:
            bot.send_message(uid, "You joined a game in %s. I will soon tell you your secret role." % groupName)
            game.add_player(uid, player)
        except Exception:
            bot.send_message(game.cid,
                             fname + ", I can\'t send you a private message. Please go to @thesecrethitlerbot and click \"Start\".\nYou then need to send /join again.")
        else:
            log.info("%s (%d) joined a game in %d" % (fname, uid, game.cid))
            if len(game.playerlist) > 4:
                bot.send_message(game.cid, fname + " has joined the game. Type /startgame if this was the last player and you want to start with %d players!" % len(game.playerlist))
            elif len(game.playerlist) == 1:
                bot.send_message(game.cid, "%s has joined the game. There is currently %d player in the game and you need 5-10 players." % (fname, len(game.playerlist)))
            else:
                bot.send_message(game.cid, "%s has joined the game. There are currently %d players in the game and you need 5-10 players." % (fname, len(game.playerlist)))


def command_comecarjogo(bot, update):
    log.info('command_startgame called')
    cid = update.message.chat_id
    game = GamesController.games.get(cid, None)
    if not game:
        bot.send_message(cid, "There is no game in this chat. Create a new game with /newgame")
    elif game.board:
        bot.send_message(cid, "The game is already running!")
    elif update.message.from_user.id != game.initiator and bot.getChatMember(cid, update.message.from_user.id).status not in ("administrator", "creator"):
        bot.send_message(game.cid, "Only the initiator of the game or a group admin can start the game with /startgame")
    elif len(game.playerlist) < 5:
        bot.send_message(game.cid, "There are not enough players (min. 5, max. 10). Join the game with /join")
    else:
        player_number = len(game.playerlist)
        MainController.inform_players(bot, game, game.cid, player_number)
        MainController.inform_fascists(bot, game, player_number)
        game.board = Board(player_number, game)
        log.info(game.board)
        log.info("len(games) Command_startgame: " + str(len(GamesController.games)))
        game.shuffle_player_sequence()
        game.board.state.player_counter = 0
        bot.send_message(game.cid, game.board.print_board())
        #group_name = update.message.chat.title
        #bot.send_message(ADMIN, "Game of Secret Hitler started in group %s (%d)" % (group_name, cid))
        MainController.start_round(bot, game)

def command_cancelarjogo(bot, update):
    log.info('command_cancelgame called')
    cid = update.message.chat_id
    if cid in GamesController.games.keys():
        game = GamesController.games[cid]
        status = bot.getChatMember(cid, update.message.from_user.id).status
        if update.message.from_user.id == game.initiator or status in ("administrator", "creator"):
            MainController.end_game(bot, game, 99)
        else:
            bot.send_message(cid, "Só quem começou o jogo ou o admin do grupo podem cancelar o jogo com /cancelgame, o resto é golpe")
    else:
        bot.send_message(cid, "Não há nenhum jogo neste chat. Crie um novo jogo com /newgame")


def command_votos(bot, update):
    try:
        #Send message of executing command
        cid = update.message.chat_id
        #bot.send_message(cid, "Looking for history...")
        #Check if there is a current game
        if cid in GamesController.games.keys():
            game = GamesController.games.get(cid, None)
            if not game.dateinitvote:
                # If date of init vote is null, then the voting didnt start
                bot.send_message(cid, "The voting didn't start yet.")
            else:
                #If there is a time, compare it and send history of votes.
                start = game.dateinitvote
                stop = datetime.datetime.now()
                elapsed = stop - start
                if elapsed > datetime.timedelta(minutes=1):
                    history_text = "Vote history for President %s and Chancellor %s:\n\n" % (game.board.state.nominated_president.name, game.board.state.nominated_chancellor.name)
                    for player in game.player_sequence:
                        # If the player is in the last_votes (He voted), mark him as he registered a vote
                        if player.uid in game.board.state.last_votes:
                            history_text += "%s registered a vote.\n" % (game.playerlist[player.uid].name)
                        else:
                            history_text += "%s didn't register a vote.\n" % (game.playerlist[player.uid].name)
                    bot.send_message(cid, history_text)
                else:
                    bot.send_message(cid, "Five minutes must pass to see the votes")
        else:
            bot.send_message(cid, "There is no game in this chat. Create a new game with /newgame")
    except Exception as e:
        bot.send_message(cid, str(e))


def command_vempraurna(bot, update):
    try:
        #Send message of executing command
        cid = update.message.chat_id
        #bot.send_message(cid, "Looking for history...")
        #Check if there is a current game
        if cid in GamesController.games.keys():
            game = GamesController.games.get(cid, None)
            if not game.dateinitvote:
                # If date of init vote is null, then the voting didnt start
                bot.send_message(cid, "The voting didn't start yet.")
            else:
                #If there is a time, compare it and send history of votes.
                start = game.dateinitvote
                stop = datetime.datetime.now()
                elapsed = stop - start
                if elapsed > datetime.timedelta(minutes=1):
                    # Only remember to vote to players that are still in the game
                    history_text = ""
                    for player in game.player_sequence:
                        # If the player is not in last_votes send him reminder
                        if player.uid not in game.board.state.last_votes:
                            history_text += "It's time to vote [%s](tg://user?id=%d).\n" % (game.playerlist[player.uid].name, player.uid)
                    bot.send_message(cid, text=history_text, parse_mode=ParseMode.MARKDOWN)
                else:
                    bot.send_message(cid, "Five minutes must pass to see call to vote")
        else:
            bot.send_message(cid, "There is no game in this chat. Create a new game with /newgame")
    except Exception as e:
        bot.send_message(cid, str(e))
