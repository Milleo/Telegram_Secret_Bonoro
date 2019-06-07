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
    u"\u2716\uFE0F" + ' Política eleita',  # X
    u"\U0001F52E" + ' Poder presidencial: Mãe de ná, ver as próximas cartas',  # crystal
    u"\U0001F50D" + ' Poder presidential: Lava-Jato, ver se é petralha ou não',  # inspection glass
    u"\U0001F52B" + ' Poder presidencial: Meter a azeitona',  # knife
    u"\U0001F608" + ' Poder presidencial: Acusar o golpe, indicar um amiguinho pra presidente',  # tie
    u"\u2692" + ' Petralhada ganhou, Pablo Vittar nas notas de R$50,00',  # dove
    u"\u2620" + ' Bonoro ganhou, #NovaEra com muito .38 e Pitú'  # skull
]


def command_simbolos(bot, update):
    cid = update.message.chat_id
    symbol_text = "Estes símbolos vão aparecer no tabuleiro: \n"
    for i in symbols:
        symbol_text += i + "\n"
    bot.send_message(cid, symbol_text)


def command_tabuleiro(bot, update):
    cid = update.message.chat_id
    if cid in GamesController.games.keys():
        if GamesController.games[cid].board:
            bot.send_message(cid, GamesController.games[cid].board.print_board())
        else:
            bot.send_message(cid, "Não tem nenhum jogo em andamento no chat. Para começar digite /comecarjogo")
    else:
        bot.send_message(cid, "Não tem nenhum jogo criado neste chat. Crie um novo jogo digitando /novojogo")


def command_start(bot, update):
    cid = update.message.chat_id
    bot.send_message(cid,
                     "Secret Bonoro é um jogo de dedução social para no mínimo 5 e até 10 jogadores onde devem descorir e parar Bonoro."
                     " A maioria dos jogadores são PeTralhas. Se eles confiarem uns nos outros, eles terão votos o suficente "
                     "para transformar o Brasil numa Venezuela e ganhar jogo. Mas alguns jogadores são bolsominions. Eles vão se utilizar "
                     "de fake news no zip zop para que o mito seja eleito, implantar a agenda anti-marxista e culpar os PeTralhas."
                     "A PeTralhada deve trabalhar junta para que juntos descubram a verdade antes que os bolsominions coloquem suas políticas em prática"
                     "e ganhar o jogo expulsando o MaisMédicos, acabando com a HéteroFobia e garantindo liberdade de expressão pro Danillo Gentilli\n\n"
                     "Adicione-me a um grupo e digite /novojogo para começar!")

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
        bot.send_message(cid, "Primeiro você tem que me adicionar a um grupo e digitar /novojogo")
    elif game:
        bot.send_message(cid, "Já existe um jogo em andamento, se você quiser finalizar digite /cancelarjogo")
    else:
        GamesController.games[cid] = Game(cid, update.message.from_user.id)
        with open(STATS, 'r') as f:
            stats = json.load(f)
        if cid not in stats.get("groups"):
            stats.get("groups").append(cid)
            with open(STATS, 'w') as f:
                json.dump(stats, f)
        bot.send_message(cid, "Novo jogo criado! Cada jogador deve mandar o comando /participar do jogo.\nQuem iniciou o jogo (ou o admin do grupo) pode, /participar também e então digitar /comecarjogo quando todos já confirmaram participação")


def command_participar(bot, update):
    groupName = update.message.chat.title
    cid = update.message.chat_id
    groupType = update.message.chat.type
    game = GamesController.games.get(cid, None)
    fname = update.message.from_user.first_name

    if groupType not in ['group', 'supergroup']:
        bot.send_message(cid, "Primeiro você tem que me adicionar a um grupo e digitar /novojogo")
    elif not game:
        bot.send_message(cid, "Não tem nenhum jogo em andamento no chat. Para começar digite /novojogo")
    elif game.board:
        bot.send_message(cid, "O jogo já começou, espera o próximo.")
    elif update.message.from_user.id in game.playerlist:
        bot.send_message(game.cid, "Você já está participando do jogo, %s, seu arrombado!" % fname)
    elif len(game.playerlist) >= 10:
        bot.send_message(game.cid, "Esse jogo já está com capacidade máxima, para começar digite /comecarjogo!")
    else:
        uid = update.message.from_user.id
        player = Player(fname, uid)
        try:
            bot.send_message(uid, "Você está participando de um jogo em %s. Logo vou falar seu papel." % groupName)
            game.add_player(uid, player)
        except Exception:
            bot.send_message(game.cid,
                             fname + ", Eu não consigo te mandar uma mensagem privada, abra um chat com @SecretBonoroBot e clique em \"start\".\nDepois envie neste chat /participar de novo")
        else:
            log.info("%s (%d) joined a game in %d" % (fname, uid, game.cid))
            if len(game.playerlist) > 4:
                bot.send_message(game.cid, fname + " está participando do jogo. Digite /comecarjogo se você quiser começar o jogo com %d jogadores!" % len(game.playerlist))
            elif len(game.playerlist) == 1:
                bot.send_message(game.cid, "%s está participando do jogo. Por enquanto temos %d jogadores participando, e precisamos de 5 a 10 jogadores." % (fname, len(game.playerlist)))
            else:
                bot.send_message(game.cid, "%s está participando do jogo. Por enquanto temos %d jogadores participando, e precisamos de 5 a 10 jogadores." % (fname, len(game.playerlist)))


def command_comecarjogo(bot, update):
    log.info('command_startgame called')
    cid = update.message.chat_id
    game = GamesController.games.get(cid, None)
    if not game:
        bot.send_message(cid, "Não há nenhum jogo neste chat. Crie um novo jogo com /novojogo")
    elif game.board:
        bot.send_message(cid, "O jogo já começou!")
    elif update.message.from_user.id != game.initiator and bot.getChatMember(cid, update.message.from_user.id).status not in ("administrator", "creator"):
            bot.send_message(cid, "Só quem começou o jogo ou o admin do grupo podem comecar o jogo com /comecarjogo, o resto é golpe")
    elif len(game.playerlist) < 5:
        bot.send_message(game.cid, "Não têm jogadores o suficiente na partida (min. 5, máx. 10). Entre no jogo com /participar")
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
        bot.send_message(cid, "Não há nenhum jogo neste chat. Crie um novo jogo com /novojogo")


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
                bot.send_message(cid, "Ainda não começou o período eleitoral, sossega aí")
            else:
                #If there is a time, compare it and send history of votes.
                start = game.dateinitvote
                stop = datetime.datetime.now()
                elapsed = stop - start
                if elapsed > datetime.timedelta(minutes=1):
                    history_text = "Histórico de votação para o presidente %s e o vice %s:\n\n" % (game.board.state.nominated_president.name, game.board.state.nominated_chancellor.name)
                    for player in game.player_sequence:
                        # If the player is in the last_votes (He voted), mark him as he registered a vote
                        if player.uid in game.board.state.last_votes:
                            history_text += "%s votou.\n" % (game.playerlist[player.uid].name)
                        else:
                            history_text += "%s ainda não votou.\n" % (game.playerlist[player.uid].name)
                    bot.send_message(cid, history_text)
                else:
                    bot.send_message(cid, "A apuração dos votos só está disponível depois de 5 minutos")
        else:
            bot.send_message(cid, "Não há nenhum jogo neste chat. Crie um novo jogo com /novojogo")
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
                bot.send_message(cid, "Ainda não começou o período eleitoral, sossega aí")
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
                            history_text += "#VemPraUrna [%s](tg://user?id=%d).\n" % (game.playerlist[player.uid].name, player.uid)
                    bot.send_message(cid, text=history_text, parse_mode=ParseMode.MARKDOWN)
                else:
                    bot.send_message(cid, "A apuração dos votos só está disponível depois de 5 minutos")
        else:
            bot.send_message(cid, "Não há nenhum jogo neste chat. Crie um novo jogo com /novojogo")
    except Exception as e:
        bot.send_message(cid, str(e))
