#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "Julian Schrittwieser"

import json
import logging as log
import random
import re
from random import randrange
from time import sleep

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (Updater, CommandHandler, CallbackQueryHandler)

import Commands
from Constants.Cards import playerSets
from Constants.Config import TOKEN, STATS
from Boardgamebox.Game import Game
from Boardgamebox.Player import Player
import GamesController

import datetime

# Enable logging
log.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                level=log.INFO,
                filename='../logs/logging.log')

logger = log.getLogger(__name__)


def initialize_testdata():
    # Sample game for quicker tests
    testgame = Game(-1001113216265, 15771023)
    GamesController.games[-1001113216265] = testgame
    players = [Player("Александр", 320853702), Player("Gustav", 305333239), Player("Rene", 318940765), Player("Susi", 290308460), Player("Renate", 312027975)]
    for player in players:
        testgame.add_player(player.uid, player)

##
#
# Beginning of round
#
##

def start_round(bot, game):
    log.info('start_round called')
    if game.board.state.chosen_president is None:
        game.board.state.nominated_president = game.player_sequence[game.board.state.player_counter]
    else:
        game.board.state.nominated_president = game.board.state.chosen_president
        game.board.state.chosen_president = None
    bot.send_message(game.cid,
                     "O próximo presidente é %s.\n%s, por favor escolha o seu vice no chat privado!" % (
                         game.board.state.nominated_president.name, game.board.state.nominated_president.name))
    choose_chancellor(bot, game)
    # --> nominate_chosen_chancellor --> vote --> handle_voting --> count_votes --> voting_aftermath --> draw_policies
    # --> choose_policy --> pass_two_policies --> choose_policy --> enact_policy --> start_round


def choose_chancellor(bot, game):
    log.info('choose_chancellor called')
    strcid = str(game.cid)
    pres_uid = 0
    chan_uid = 0
    btns = []
    if game.board.state.president is not None:
        pres_uid = game.board.state.president.uid
    if game.board.state.chancellor is not None:
        chan_uid = game.board.state.chancellor.uid
    for uid in game.playerlist:
        # If there are only five players left in the
        # game, only the last elected Chancellor is
        # ineligible to be Chancellor Candidate; the
        # last President may be nominated.
        if len(game.player_sequence) > 5:
            if uid != game.board.state.nominated_president.uid and game.playerlist[
                uid].is_dead == False and uid != pres_uid and uid != chan_uid:
                name = game.playerlist[uid].name
                btns.append([InlineKeyboardButton(name, callback_data=strcid + "_chan_" + str(uid))])
        else:
            if uid != game.board.state.nominated_president.uid and game.playerlist[
                uid].is_dead == False and uid != chan_uid:
                name = game.playerlist[uid].name
                btns.append([InlineKeyboardButton(name, callback_data=strcid + "_chan_" + str(uid))])

    chancellorMarkup = InlineKeyboardMarkup(btns)
    bot.send_message(game.board.state.nominated_president.uid, game.board.print_board())
    bot.send_message(game.board.state.nominated_president.uid, 'Escolha o seu vice!',
                     reply_markup=chancellorMarkup)


def nominate_chosen_chancellor(bot, update):
    log.info('nominate_chosen_chancellor called')
    log.info(GamesController.games.keys())
    callback = update.callback_query
    regex = re.search("(-[0-9]*)_chan_([0-9]*)", callback.data)
    cid = int(regex.group(1))
    chosen_uid = int(regex.group(2))
    try:
        game = GamesController.games.get(cid, None)
        log.info(game)
        log.info(game.board)
        game.board.state.nominated_chancellor = game.playerlist[chosen_uid]
        log.info("President %s (%d) nominated %s (%d)" % (
            game.board.state.nominated_president.name, game.board.state.nominated_president.uid,
            game.board.state.nominated_chancellor.name, game.board.state.nominated_chancellor.uid))
        bot.edit_message_text("Você escolheu %s como vice!" % game.board.state.nominated_chancellor.name,
                              callback.from_user.id, callback.message.message_id)
        bot.send_message(game.cid,
                         "O presidente %s escolheu %s como vice. Por favor votem agora!" % (
                             game.board.state.nominated_president.name, game.board.state.nominated_chancellor.name))
        vote(bot, game)
    except AttributeError as e:
        log.error("nominate_chosen_chancellor: Game or board should not be None! Eror: " + str(e))
    except Exception as e:
        log.error("Unknown error: " + str(e))


def vote(bot, game):
    log.info('vote called')
    #When voting starts we start the counter to see later with the vote/calltovote command we can see who voted.
    game.dateinitvote = datetime.datetime.now()
    strcid = str(game.cid)
    btns = [[InlineKeyboardButton("Sim", callback_data=strcid + "_Sim"),
             InlineKeyboardButton("Não", callback_data=strcid + "_Nao")]]
    voteMarkup = InlineKeyboardMarkup(btns)
    for uid in game.playerlist:
        if not game.playerlist[uid].is_dead:
            if game.playerlist[uid] is not game.board.state.nominated_president:
                # the nominated president already got the board before nominating a chancellor
                bot.send_message(uid, game.board.print_board())
            bot.send_message(uid,
                             "Do you want to elect President %s and Chancellor %s?" % (
                                 game.board.state.nominated_president.name, game.board.state.nominated_chancellor.name),
                             reply_markup=voteMarkup)


def handle_voting(bot, update):
    callback = update.callback_query
    log.info('handle_voting called: %s' % callback.data)
    regex = re.search("(-[0-9]*)_(.*)", callback.data)
    cid = int(regex.group(1))
    answer = regex.group(2)
    try:
        game = GamesController.games[cid]
        uid = callback.from_user.id
        bot.edit_message_text("Obrigado pelo seu voto para: %s presidente e %s vice %s" % (
            answer, game.board.state.nominated_president.name, game.board.state.nominated_chancellor.name), uid,
                              callback.message.message_id)
        log.info("Player %s (%d) voted %s" % (callback.from_user.first_name, uid, answer))
        if uid not in game.board.state.last_votes:
            game.board.state.last_votes[uid] = answer
        if len(game.board.state.last_votes) == len(game.player_sequence):
            count_votes(bot, game)
    except:
        log.error("handle_voting: Game or board should not be None!")


def count_votes(bot, game):
    log.info('count_votes called')
    # Voted Ended
    game.dateinitvote = None
    voting_text = ""
    voting_success = False
    for player in game.player_sequence:
        if game.board.state.last_votes[player.uid] == "Sim":
            voting_text += game.playerlist[player.uid].name + " votou Sim!\n"
        elif game.board.state.last_votes[player.uid] == "Não":
            voting_text += game.playerlist[player.uid].name + " votou Não!\n"
    if list(game.board.state.last_votes.values()).count("Sim") > (
        len(game.player_sequence) / 2):  # because player_sequence doesnt include dead
        # VOTING WAS SUCCESSFUL
        log.info("Voting successful")
        voting_text += "Parabéns ao presidente %s e ao seu vice %s!" % (
            game.board.state.nominated_president.name, game.board.state.nominated_chancellor.name)
        game.board.state.chancellor = game.board.state.nominated_chancellor
        game.board.state.president = game.board.state.nominated_president
        game.board.state.nominated_president = None
        game.board.state.nominated_chancellor = None
        voting_success = True
        bot.send_message(game.cid, voting_text)
        voting_aftermath(bot, game, voting_success)
    else:
        log.info("Voting failed")
        voting_text += "Os eleitores não curtiram essa chapa não!"
        game.board.state.nominated_president = None
        game.board.state.nominated_chancellor = None
        game.board.state.failed_votes += 1
        bot.send_message(game.cid, voting_text)
        if game.board.state.failed_votes == 3:
            do_anarchy(bot, game)
        else:
            voting_aftermath(bot, game, voting_success)


def voting_aftermath(bot, game, voting_success):
    log.info('voting_aftermath called')
    game.board.state.last_votes = {}
    if voting_success:
        if game.board.state.fascist_track >= 3 and game.board.state.chancellor.role == "Bonoro":
            # fascists win, because Hitler was elected as chancellor after 3 fascist policies
            game.board.state.game_endcode = -2
            end_game(bot, game, game.board.state.game_endcode)
        elif game.board.state.fascist_track >= 3 and game.board.state.chancellor.role != "Bonoro" and game.board.state.chancellor not in game.board.state.not_hitlers:
            game.board.state.not_hitlers.append(game.board.state.chancellor)
            draw_policies(bot, game)
        else:
            # voting was successful and Hitler was not nominated as chancellor after 3 fascist policies
            draw_policies(bot, game)
    else:
        bot.send_message(game.cid, game.board.print_board())
        start_next_round(bot, game)


def draw_policies(bot, game):
    log.info('draw_policies called')
    strcid = str(game.cid)
    game.board.state.veto_refused = False
    # shuffle discard pile with rest if rest < 3
    shuffle_policy_pile(bot, game)
    btns = []
    for i in range(3):
        game.board.state.drawn_policies.append(game.board.policies.pop(0))
    for policy in game.board.state.drawn_policies:
        btns.append([InlineKeyboardButton(policy, callback_data=strcid + "_" + policy)])

    choosePolicyMarkup = InlineKeyboardMarkup(btns)
    bot.send_message(game.board.state.president.uid,
                     "Você recebeu as 3 seguintes políticas. Qual delas você quer DESCARTAR?",
                     reply_markup=choosePolicyMarkup)


def choose_policy(bot, update):
    log.info('choose_policy called')
    callback = update.callback_query
    regex = re.search("(-[0-9]*)_(.*)", callback.data)
    cid = int(regex.group(1))
    answer = regex.group(2)

    print(answer)

    try:
        game = GamesController.games[cid]
        strcid = str(game.cid)
        uid = callback.from_user.id
        if len(game.board.state.drawn_policies) == 3:
            log.info("Player %s (%d) discarded %s" % (callback.from_user.first_name, uid, answer))
            bot.edit_message_text("A política %s será descartada!" % answer, uid,
                                  callback.message.message_id)
            # remove policy from drawn cards and add to discard pile, pass the other two policies
            for i in range(3):
                if game.board.state.drawn_policies[i] == answer:
                    game.board.discards.append(game.board.state.drawn_policies.pop(i))
                    break
            pass_two_policies(bot, game)
        elif len(game.board.state.drawn_policies) == 2:
            if answer == "veto":
                log.info("Player %s (%d) suggested a veto" % (callback.from_user.first_name, uid))
                bot.edit_message_text("Você sugeiriu veto ao presidente %s" % game.board.state.president.name, uid,
                                      callback.message.message_id)
                bot.send_message(game.cid,
                                 "O Vice %s disse que vai dar ruim e sugeriu o veto ao presidente  %s." % (
                                     game.board.state.chancellor.name, game.board.state.president.name))

                btns = [[InlineKeyboardButton("Vetado! (Aceitou a sugestão)", callback_data=strcid + "_yesveto")],
                        [InlineKeyboardButton("Não vai vetar nada! (Tacou o foda-se)", callback_data=strcid + "_noveto")]]

                vetoMarkup = InlineKeyboardMarkup(btns)
                bot.send_message(game.board.state.president.uid,
                                 "O vice %s sugeriu um veto para você. Você quer acatar ao veto (descartar essas políticas)?" % game.board.state.chancellor.name,
                                 reply_markup=vetoMarkup)
            else:
                log.info("Player %s (%d) chose a %s policy" % (callback.from_user.first_name, uid, answer))
                bot.edit_message_text("A política %s será promulgada!" % answer, uid,
                                      callback.message.message_id)
                # remove policy from drawn cards and enact, discard the other card
                for i in range(2):
                    if game.board.state.drawn_policies[i] == answer:
                        game.board.state.drawn_policies.pop(i)
                        break
                game.board.discards.append(game.board.state.drawn_policies.pop(0))
                assert len(game.board.state.drawn_policies) == 0
                enact_policy(bot, game, answer, False)
        else:
            log.error("choose_policy: drawn_policies should be 3 or 2, but was " + str(
                len(game.board.state.drawn_policies)))
    except:
        log.error("choose_policy: Game or board should not be None!")


def pass_two_policies(bot, game):
    log.info('pass_two_policies called')
    strcid = str(game.cid)
    btns = []
    for policy in game.board.state.drawn_policies:
        btns.append([InlineKeyboardButton(policy, callback_data=strcid + "_" + policy)])
    if game.board.state.fascist_track == 5 and not game.board.state.veto_refused:
        btns.append([InlineKeyboardButton("Veto", callback_data=strcid + "_veto")])
        choosePolicyMarkup = InlineKeyboardMarkup(btns)
        bot.send_message(game.cid,
                         "O presidente %s passou duas políoticas para o vice %s." % (
                             game.board.state.president.name, game.board.state.chancellor.name))
        bot.send_message(game.board.state.chancellor.uid,
                         "O presidente %s te passou as seguintes políticas. Qual delas deve ser promulgada? Você também pode acusar o golpe e pedir veto." % game.board.state.president.name,
                         reply_markup=choosePolicyMarkup)
    elif game.board.state.veto_refused:
        choosePolicyMarkup = InlineKeyboardMarkup(btns)
        bot.send_message(game.board.state.chancellor.uid,
                         "O presidente %s te mandou caçar uma rola e rejeitou seu veto. Now you have to choose. Qual delas deve ser promulgada?" % game.board.state.president.name,
                         reply_markup=choosePolicyMarkup)
    elif game.board.state.fascist_track < 5:
        choosePolicyMarkup = InlineKeyboardMarkup(btns)
        bot.send_message(game.board.state.chancellor.uid,
                         "O presidente %s te passou as seguintes políticas. Qual delas deve ser promulgada?" % game.board.state.president.name,
                         reply_markup=choosePolicyMarkup)


def enact_policy(bot, game, policy, anarchy):
    log.info('enact_policy called')
    if policy.startswith("Esquerdista"):
        game.board.state.liberal_track += 1
    elif policy.startswith("Patriota"):
        game.board.state.fascist_track += 1
    game.board.state.failed_votes = 0  # reset counter
    if not anarchy:
        bot.send_message(game.cid,
                         "Presidente %s e o vice %s promungaram a política %s!" % (
                             game.board.state.president.name, game.board.state.chancellor.name, policy))
    else:
        bot.send_message(game.cid,
                         "A Política máxima %s foi promungada" % policy)
    sleep(3)
    bot.send_message(game.cid, game.board.print_board())
    # end of round
    if game.board.state.liberal_track == 5:
        game.board.state.game_endcode = 1
        end_game(bot, game, game.board.state.game_endcode)  # liberals win with 5 liberal policies
    if game.board.state.fascist_track == 6:
        game.board.state.game_endcode = -1
        end_game(bot, game, game.board.state.game_endcode)  # fascists win with 6 fascist policies
    sleep(3)
    # End of legislative session, shuffle if necessary 
    shuffle_policy_pile(bot, game)    
    if not anarchy:
        if policy.startswith("direita"):
            action = game.board.fascist_track_actions[game.board.state.fascist_track - 1]
            if action is None and game.board.state.fascist_track == 6:
                pass
            elif action == None:
                start_next_round(bot, game)
            elif action == "policy":
                bot.send_message(game.cid,
                                 "Poder presidencial acionado: Mãe de ná " + u"\U0001F52E" + "\nO presidente %s agora sabe quais políticas estão no baralho "
                                                                                              "O presidente pode falar quais são as políticas"
                                                                                              "(ou ser um babaca e mentir)" % game.board.state.president.name)
                action_policy(bot, game)
            elif action == "kill":
                bot.send_message(game.cid,
                                 "Poder presidencial acionado: Meter a azeitona " + u"\U0001F5E1" + "\nO presidente %s ficou 1000% pistola e quer matar alguém "
                                                                                            "vocês podem acoselhá-lo quem deve ser crivado de bala,"
                                                                                            "mas ele é que tem "
                                                                                            "a palavra final." % game.board.state.president.name)
                action_kill(bot, game)
            elif action == "inspect":
                bot.send_message(game.cid,
                                 "Poder presidencial acionado: Operação Lava-Jato " + u"\U0001F50E" + "\nCuidado que o Moro e o Japonês da PF vem aí, "
                                                                                                      "O presidente quer ver se você é PeTralha (ou não), "
                                                                                                      "só o presidente vai ficar sabendo se a pessoa é PeTralha ou não"
                                                                                                      "e ele pode mentir sobre o resultado da investigação #aGloboMente" % game.board.state.president.name)
                action_inspect(bot, game)
            elif action == "choose":
                bot.send_message(game.cid,
                                 "Poder presidencial acionado: Acusar o Golpe " + u"\U0001F454" + "\nO presidente %s se encheu dessa patifaria e vai "
                                                                                                        "indicar um amiguinho para ser presidente. "
                                                                                                        "Depois dessa palhaçada, a ordem de eleição volta ao normal." % game.board.state.president.name)
                action_choose(bot, game)
        else:
            start_next_round(bot, game)
    else:
        start_next_round(bot, game)


def choose_veto(bot, update):
    log.info('choose_veto called')
    callback = update.callback_query
    regex = re.search("(-[0-9]*)_(.*)", callback.data)
    cid = int(regex.group(1))
    answer = regex.group(2)
    try:
        game = GamesController.games[cid]
        uid = callback.from_user.id
        if answer == "yesveto":
            log.info("Jogador %s (%d) aceitou o veto" % (callback.from_user.first_name, uid))
            bot.edit_message_text("Você aceitou o veto!", uid, callback.message.message_id)
            bot.send_message(game.cid,
                             "Presidente %s aceitou o veto do vice %s. Nenhuma política foi promulgada, então isso conta como uma eleição nula." % (
                                 game.board.state.president.name, game.board.state.chancellor.name))
            game.board.discards += game.board.state.drawn_policies
            game.board.state.drawn_policies = []
            game.board.state.failed_votes += 1
            if game.board.state.failed_votes == 3:
                do_anarchy(bot, game)
            else:
                bot.send_message(game.cid, game.board.print_board())
                start_next_round(bot, game)
        elif answer == "noveto":
            log.info("Jogador %s (%d) cancelou o veto" % (callback.from_user.first_name, uid))
            game.board.state.veto_refused = True
            bot.edit_message_text("Você recusou o veto!", uid, callback.message.message_id)
            bot.send_message(game.cid,
                             "O presidente %s recusou o veto do vice %s. O vice agora tem que escolher uma política!" % (
                                 game.board.state.president.name, game.board.state.chancellor.name))
            pass_two_policies(bot, game)
        else:
            log.error("choose_veto: Callback data can either be \"veto\" or \"noveto\", but not %s" % answer)
    except:
        log.error("choose_veto: Game or board should not be None!")


def do_anarchy(bot, game):
    log.info('do_anarchy called')
    bot.send_message(game.cid, game.board.print_board())
    bot.send_message(game.cid, "PETRALHICE!!! LULA LIVRE HOJE E SEMPRE")
    game.board.state.president = None
    game.board.state.chancellor = None
    top_policy = game.board.policies.pop(0)
    game.board.state.last_votes = {}
    enact_policy(bot, game, top_policy, True)


def action_policy(bot, game):
    log.info('action_policy called')
    topPolicies = ""
    # shuffle discard pile with rest if rest < 3
    shuffle_policy_pile(bot, game)
    for i in range(3):
        topPolicies += game.board.policies[i] + "\n"
    bot.send_message(game.board.state.president.uid,
                     "As três próximas políticas do baralho São:\n%s\nVocê também pode ser um arrombado e mentir pros seus coleguinhas, não sou seu pai e nem tô aqui pra te julgar." % topPolicies)
    start_next_round(bot, game)


def action_kill(bot, game):
    log.info('action_kill called')
    strcid = str(game.cid)
    btns = []
    for uid in game.playerlist:
        if uid != game.board.state.president.uid and game.playerlist[uid].is_dead == False:
            name = game.playerlist[uid].name
            btns.append([InlineKeyboardButton(name, callback_data=strcid + "_kill_" + str(uid))])

    killMarkup = InlineKeyboardMarkup(btns)
    bot.send_message(game.board.state.president.uid, game.board.print_board())
    bot.send_message(game.board.state.president.uid,
                     'Você pode dar o tiro em alguém (a pessoa vai morrer nesse processo). Converse com os demais sobre essa decisão.',
                     reply_markup=killMarkup)


def choose_kill(bot, update):
    log.info('choose_kill called')
    callback = update.callback_query
    regex = re.search("(-[0-9]*)_kill_(.*)", callback.data)
    cid = int(regex.group(1))
    answer = int(regex.group(2))
    try:
        game = GamesController.games[cid]
        chosen = game.playerlist[answer]
        chosen.is_dead = True
        if game.player_sequence.index(chosen) <= game.board.state.player_counter:
            game.board.state.player_counter -= 1
        game.player_sequence.remove(chosen)
        game.board.state.dead += 1
        log.info("Jogador %s (%d) deu uma porrada de tiro em  %s (%d)" % (
            callback.from_user.first_name, callback.from_user.id, chosen.name, chosen.uid))
        bot.edit_message_text("Você matou o %s!" % chosen.name, callback.from_user.id, callback.message.message_id)
        if chosen.role == "Bonoro":
            bot.send_message(game.cid, "O presidente " + game.board.state.president.name + " matou " + chosen.name + ". ")
            end_game(bot, game, 2)
        else:
            bot.send_message(game.cid,
                             "O presidente %s matou %s que não era o Bonoro. %s, agora você morreu e morto não fala, então fica na maciota ai!" % (
                                 game.board.state.president.name, chosen.name, chosen.name))
            bot.send_message(game.cid, game.board.print_board())
            start_next_round(bot, game)
    except:
        log.error("choose_kill: Game or board should not be None!")


def action_choose(bot, game):
    log.info('action_choose called')
    strcid = str(game.cid)
    btns = []

    for uid in game.playerlist:
        if uid != game.board.state.president.uid and game.playerlist[uid].is_dead == False:
            name = game.playerlist[uid].name
            btns.append([InlineKeyboardButton(name, callback_data=strcid + "_choo_" + str(uid))])

    inspectMarkup = InlineKeyboardMarkup(btns)
    bot.send_message(game.board.state.president.uid, game.board.print_board())
    bot.send_message(game.board.state.president.uid,
                     'Escolhe seu amiguinho aí pra ser candidato a presidente',
                     reply_markup=inspectMarkup)


def choose_choose(bot, update):
    log.info('choose_choose called')
    callback = update.callback_query
    regex = re.search("(-[0-9]*)_choo_(.*)", callback.data)
    cid = int(regex.group(1))
    answer = int(regex.group(2))
    try:
        game = GamesController.games[cid]
        chosen = game.playerlist[answer]
        game.board.state.chosen_president = chosen
        log.info(
            "O jogador %s (%d) escolheu %s (%d) como próximo presidente" % (
                callback.from_user.first_name, callback.from_user.id, chosen.name, chosen.uid))
        bot.edit_message_text("Você escolheu %s como próximo presidente!" % chosen.name, callback.from_user.id,
                              callback.message.message_id)
        bot.send_message(game.cid,
                         "O presidente %s escolheu %s como sucessor." % (
                             game.board.state.president.name, chosen.name))
        start_next_round(bot, game)
    except:
        log.error("choose_choose: Game or board should not be None!")


def action_inspect(bot, game):
    log.info('action_inspect called')
    strcid = str(game.cid)
    btns = []
    for uid in game.playerlist:
        if uid != game.board.state.president.uid and game.playerlist[uid].is_dead == False:
            name = game.playerlist[uid].name
            btns.append([InlineKeyboardButton(name, callback_data=strcid + "_insp_" + str(uid))])

    inspectMarkup = InlineKeyboardMarkup(btns)
    bot.send_message(game.board.state.president.uid, game.board.print_board())
    bot.send_message(game.board.state.president.uid,
                     'Aqui você pode ver se o jogador é um comunista safado ou se ele é cidadão de bem. De quem você quer saber?',
                     reply_markup=inspectMarkup)


def choose_inspect(bot, update):
    log.info('choose_inspect called')
    callback = update.callback_query
    regex = re.search("(-[0-9]*)_insp_(.*)", callback.data)
    cid = int(regex.group(1))
    answer = int(regex.group(2))
    try:
        game = GamesController.games[cid]
        chosen = game.playerlist[answer]
        log.info(
            "O Presidente %s (%d) investogou, com a ajuda do Excelentissimo Sr. Sergio Moro, %s (%d)'s e ele é um (%s)" % (
                callback.from_user.first_name, callback.from_user.id, chosen.name, chosen.uid,
                chosen.party))
        bot.edit_message_text("O %s é %s" % (chosen.name, chosen.party),
                              callback.from_user.id,
                              callback.message.message_id)
        bot.send_message(game.cid, "Presidente %s investigou, com a ajuda do Excelentissimo Sr. Sergio Moro, %s." % (game.board.state.president.name, chosen.name))
        start_next_round(bot, game)
    except:
        log.error("choose_inspect: Game or board should not be None!")


def start_next_round(bot, game):
    log.info('start_next_round called')
    # start next round if there is no winner (or /cancel)
    if game.board.state.game_endcode == 0:
        # start new round
        sleep(5)
        # if there is no special elected president in between
        if game.board.state.chosen_president is None:
            increment_player_counter(game)
        start_round(bot, game)


##
#
# End of round
#
##

def end_game(bot, game, game_endcode):
    log.info('end_game called')
    ##
    # game_endcode:
    #   -2  fascists win by electing Hitler as chancellor
    #   -1  fascists win with 6 fascist policies
    #   0   not ended
    #   1   liberals win with 5 liberal policies
    #   2   liberals win by killing Hitler
    #   99  game cancelled
    #
    with open(STATS, 'r') as f:
        stats = json.load(f)

    if game_endcode == 99:
        if GamesController.games[game.cid].board is not None:
            bot.send_message(game.cid,
                             "Jogo cancelado!\n\n%s" % game.print_roles())
            # bot.send_message(ADMIN, "Game of Secret Hitler canceled in group %d" % game.cid)
            stats['cancelled'] = stats['cancelled'] + 1
        else:
            bot.send_message(game.cid, "Jogo cancelado!")
    else:
        if game_endcode == -2:
            bot.send_message(game.cid,
                             "Brasil, ame-o ou deixe-o! Os Patriotas venceram elegendo o Bonoro como vice!\n\n%s" % game.print_roles())
            stats['fascwin_hitler'] = stats['fascwin_hitler'] + 1
        if game_endcode == -1:
            bot.send_message(game.cid,
                             "Brasil, ame-o ou deixe-o! Todas as 6 políticas em favor da família foram promungadas!\n\n%s" % game.print_roles())
            stats['fascwin_policies'] = stats['fascwin_policies'] + 1
        if game_endcode == 1:
            bot.send_message(game.cid,
                             "LACROU! Todas as 5 políticas esquerdistas gayzistas comunistas foram promungadas!\n\n%s" % game.print_roles())
            stats['libwin_policies'] = stats['libwin_policies'] + 1
        if game_endcode == 2:
            bot.send_message(game.cid,
                             "Meu deus do céu! Os esquerdistas ganharam dando uma facada no Bonoro! #PequenoDia\n\n%s" % game.print_roles())
            stats['libwin_kill'] = stats['libwin_kill'] + 1

            # bot.send_message(ADMIN, "Game of Secret Hitler ended in group %d" % game.cid)

    with open(STATS, 'w') as f:
        json.dump(stats, f)
    del GamesController.games[game.cid]


def inform_players(bot, game, cid, player_number):
    log.info('inform_players called')
    bot.send_message(cid,
                     "Vamos começar o jogo com %d jogadores!\n%s\nVê lá no chat privado qual o seu papel!" % (
                         player_number, print_player_info(player_number)))
    available_roles = list(playerSets[player_number]["roles"])  # copy not reference because we need it again later
    for uid in game.playerlist:
        random_index = randrange(len(available_roles))
        role = available_roles.pop(random_index)
        party = get_membership(role)
        game.playerlist[uid].role = role
        game.playerlist[uid].party = party
        bot.send_message(uid, "O seu papel é: %s\nO seu partido é: %s" % (role, party))


def print_player_info(player_number):
    if player_number == 5:
        return "Têm 3 esquerdistas safados, 1 patriota e o Bonoro Mito. O Bonoro sabe quem são os patriotas."
    elif player_number == 6:
        return "Têm 4 esquerdistas safados, 1 patriota e o Bonoro Mito. O Bonoro sabe quem são os patriotas."
    elif player_number == 7:
        return "Têm 4 esquerdistas safados, 2 patriota e o Bonoro Mito. O Bonoro não sabe quem são os patriotas."
    elif player_number == 8:
        return "Têm 5 esquerdistas safados, 2 patriota e o Bonoro Mito. O Bonoro não sabe quem são os patriotas."
    elif player_number == 9:
        return "Têm 5 esquerdistas safados, 3 patriota e o Bonoro Mito. O Bonoro não sabe quem são os patriotas."
    elif player_number == 10:
        return "Têm 6 esquerdistas safados, 3 patriota e o Bonoro Mito. O Bonoro não sabe quem são os patriotas."


def inform_fascists(bot, game, player_number):
    log.info('inform_fascists called')

    for uid in game.playerlist:
        role = game.playerlist[uid].role
        if role.startswith("Bolsominion"):
            fascists = game.get_fascists()
            if player_number > 6:
                fstring = ""
                for f in fascists:
                    if f.uid != uid:
                        fstring += f.name + ", "
                fstring = fstring[:-2]
                bot.send_message(uid, "Seus companheiros patriotas são: %s" % fstring)
            hitler = game.get_hitler()
            bot.send_message(uid, "O Bonoro é: %s" % hitler.name)
        elif role == "Bonoro":
            if player_number <= 6:
                fascists = game.get_fascists()
                bot.send_message(uid, "Seus companheiros patriotas são: %s" % fascists[0].name)
        elif role.startswith("PeTralha"):
            pass
        else:
            log.error("inform_fascists: can\'t handle the role %s" % role)


def get_membership(role):
    log.info('get_membership called')
    if role.startswith("Bolsominion") or role == "Bonoro":
        return "Patriota"
    elif role.startswith("PeTralha"):
        return "Petralha"
    else:
        return None


def increment_player_counter(game):
    log.info('increment_player_counter called')
    if game.board.state.player_counter < len(game.player_sequence) - 1:
        game.board.state.player_counter += 1
    else:
        game.board.state.player_counter = 0


def shuffle_policy_pile(bot, game):
    log.info('shuffle_policy_pile called')
    if len(game.board.policies) < 3:
        game.board.discards += game.board.policies
        game.board.policies = random.sample(game.board.discards, len(game.board.discards))
        game.board.discards = []
        bot.send_message(game.cid,
                         "Tá faltando carta no baralho, eu vou embaralhar aqui com as que já foram descartadas do baralho")


def error(bot, update, error):
    logger.warning('Update "%s" caused error "%s"' % (update, error))


def main():
    GamesController.init() #Call only once
    #initialize_testdata()

    updater = Updater(TOKEN)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", Commands.command_start))
    dp.add_handler(CommandHandler("ajuda", Commands.command_ajuda))
    dp.add_handler(CommandHandler("tabuleiro", Commands.command_tabuleiro))
    dp.add_handler(CommandHandler("regras", Commands.command_regras))
    dp.add_handler(CommandHandler("ping", Commands.command_ping))
    dp.add_handler(CommandHandler("simbolos", Commands.command_simbolos))
    dp.add_handler(CommandHandler("stats", Commands.command_stats))
    dp.add_handler(CommandHandler("novojogo", Commands.command_novojogo))
    dp.add_handler(CommandHandler("comecarjogo", Commands.command_comecarjogo))
    dp.add_handler(CommandHandler("cancelarjogo", Commands.command_cancelarjogo))
    dp.add_handler(CommandHandler("participar", Commands.command_participar))
    dp.add_handler(CommandHandler("votos", Commands.command_votos))
    dp.add_handler(CommandHandler("vempraurna", Commands.command_vempraurna))

    dp.add_handler(CallbackQueryHandler(pattern="(-[0-9]*)_chan_(.*)", callback=nominate_chosen_chancellor))
    dp.add_handler(CallbackQueryHandler(pattern="(-[0-9]*)_insp_(.*)", callback=choose_inspect))
    dp.add_handler(CallbackQueryHandler(pattern="(-[0-9]*)_choo_(.*)", callback=choose_choose))
    dp.add_handler(CallbackQueryHandler(pattern="(-[0-9]*)_kill_(.*)", callback=choose_kill))
    dp.add_handler(CallbackQueryHandler(pattern="(-[0-9]*)_(yesveto|noveto)", callback=choose_veto))
    dp.add_handler(CallbackQueryHandler(pattern="(-[0-9]*)_(liberal|fascist|veto)", callback=choose_policy))
    dp.add_handler(CallbackQueryHandler(pattern="(-[0-9]*)_(Sim|Nao)", callback=handle_voting))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until the you presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
