import requests
from aiogram.utils.markdown import text, bold, italic
from aiogram.types import ParseMode

from config import database




async def Check(user_id):
    """
        Display the status of the last and current bets, available balance.
    """

    url = 'https://ergast.com/api/f1/current/next.json'
    next_event = requests.get(url).json()['MRData']['RaceTable']['Races'][0]['date']
    query = 'SELECT driver_id, bet_value FROM bets WHERE event_date = :next_event AND user_id = :user_id;'
    next_result = await database.fetch_all(query=query, values={'next_event': next_event, 'user_id': user_id})
    next_driver_id = str([line[0] for line in next_result])
    next_bet = sum([line[1] for line in next_result])

    if next_result:
        msg = text(bold('The bet on the upcoming Grand Prix: '), next_bet,
                ' coins, it was placed on the pilot with the number: ', next_driver_id, '.\n', sep='')
    else:
        msg = 'There were no bets on the upcoming Grand Prix.\n'


    url = 'https://ergast.com/api/f1/current/last.json'
    last_event = requests.get(url).json()['MRData']['RaceTable']['Races'][0]['date']
    query = 'SELECT driver_id, bet_value, payout_flag FROM bets WHERE event_date = :last_event AND user_id = :user_id;'
    last_result = await database.fetch_all(query=query, values={'last_event': last_event, 'user_id': user_id})
    last_driver_id = str([line[0] for line in last_result][0])
    last_bet = sum([line[1] for line in last_result])
    payout_flag = str([line[2] for line in last_result][0])

    if last_result:
        msg += text(bold('The bet on the past Grand Prix: '), last_bet,
                ' coins, it was placed on the pilot with the number: ', last_driver_id, '.\n', sep='')
    else:
        msg += 'There were no bets on the past Grand Prix.\n'


    url = 'https://ergast.com/api/f1/current/last/results/1.json'
    winner_id = requests.get(url).json()['MRData']['RaceTable']['Races'][0]['Results'][0]['Driver']['permanentNumber']

    if last_driver_id == winner_id and payout_flag == 'True':
        query = 'SELECT bet_value, driver_id FROM bets WHERE event_date = :last_event AND user_id != :user_id;'
        last_result = await database.fetch_all(query=query, values={'last_event': last_event, 'user_id': user_id})
        loser_bets = sum([line[0] for line in last_result if str(line[1]) != winner_id])
        all_bets = sum([line[0] for line in last_result])
        prize = last_bet / (last_bet + all_bets - loser_bets) * loser_bets + last_bet

        await database.execute('UPDATE users SET coins = (coins + :prize) WHERE user_id = :user_id;',
            values={'user_id': user_id, 'prize': prize})

    query = 'UPDATE bets SET payout_flag = FALSE WHERE user_id = :user_id AND event_date = :last_event;'
    await database.execute(query=query, values={'user_id': user_id, 'last_event': last_event})

    query = 'SELECT coins FROM users WHERE user_id = :user_id;'
    user_coins = await database.fetch_all(query=query, values={'user_id': user_id})
    user_coins = int([line[0] for line in user_coins][0])

    msg += text(bold('Your current balance is: '), user_coins, ' coins.',sep='')

    return msg
