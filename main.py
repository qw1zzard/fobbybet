import asyncio
import logging
import sys

import requests
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from aiogram.utils.markdown import bold, italic, text

from check import check
from config import bot, database, dp


@dp.message(CommandStart())
async def process_start_command(message: Message) -> None:
    await database.execute(
        'INSERT INTO users (user_id, coins) '
        f'VALUES ({message.from_user.id}, 1000.0) '
        'ON CONFLICT(user_id) DO NOTHING;',
    )

    msg = text(
        "Hi! I'm Fobby, ",
        italic('Formula 1 Betting Bot'),
        '\n',
        'Use /help to get a list of commands. ',
        'If you are just a beginner, then /check: you already ',
        'have a thousand coins, spend them wisely!',
        sep='',
    )
    await message.answer(msg, parse_mode=ParseMode.MARKDOWN)


@dp.message(Command(commands=['event']))
async def process_event_command(message: Message) -> None:
    url = 'https://ergast.com/api/f1/current/next.json'
    response = requests.get(url, timeout=10).json()['MRData']
    response = response['RaceTable']['Races'][0]

    circuit_name = response['Circuit']['circuitName']
    circuit_link = response['Circuit']['url']
    msg = text(
        response['date'],
        ' - ',
        response['raceName'],
        ' at ',
        circuit_name,
        ' (',
        circuit_link,
        ')',
        sep='',
    )
    await message.answer(msg, parse_mode=ParseMode.MARKDOWN)


@dp.message(Command(commands=['drivers']))
async def process_drivers_command(message: Message) -> None:
    url = 'https://ergast.com/api/f1/current/drivers.json'
    response = requests.get(url, timeout=10).json()['MRData']
    response = response['DriverTable']['Drivers']

    msg = text(bold('Number'), '-', bold('Name and Surname'), ':\n', sep=' ')
    for i in response:
        msg += text(
            ' ',
            i['permanentNumber'],
            '-',
            i['givenName'],
            i['familyName'],
            '\n',
            sep=' ',
        )

    await message.answer(msg, parse_mode=ParseMode.MARKDOWN)


async def bet(user_id: int, msg: str | None) -> bool:
    msg = msg.split()
    if len(msg) != 3:
        return False

    driver_id = int(msg[1])
    bet_value = float(msg[2])

    query = f'SELECT coins FROM users WHERE user_id = {user_id};'
    user_coins = await database.fetch_all(query=query)
    user_coins = float([line['coins'] for line in user_coins][0])

    if 0 < bet_value <= user_coins:
        url = 'https://ergast.com/api/f1/current/next.json'
        next_event = requests.get(url, timeout=10).json()['MRData']
        next_event = next_event['RaceTable']['Races'][0]['date']

        await database.execute(
            'INSERT INTO bets (user_id, event_date, driver_id, bet_value) '
            f'VALUES ({user_id}, {next_event}, {driver_id}, {bet_value});',
        )

        await database.execute(
            f'UPDATE users SET coins = (coins - {bet_value}) '
            f'WHERE user_id = {user_id};',
        )
        return True
    else:
        return False


@dp.message(Command(commands=['bet']))
async def process_bet_command(message: Message) -> None:
    if await bet(message.from_user.id, message.text):
        await message.answer(
            'Sports bet accepted! You can check with the command /check.'
        )
    else:
        await message.answer(
            'Please, use the format «/bet number size», '
            "where number - driver's number from table "
            '/drivers and size is positive real '
            'value of the bet.'
        )


@dp.message(Command(commands=['check']))
async def process_check_command(message: Message) -> None:
    msg = await check(message.from_user.id)
    await message.answer(msg, parse_mode=ParseMode.MARKDOWN)


@dp.message(Command(commands=['news']))
async def process_news_command(message: Message) -> None:
    msg = text(
        'I recently refactored the code to meet PEP 8 standards ',
        'at least a little bit. Check out my [GitHub]',
        '(https://github.com/qw1zzard/fobbybet). ',
        'Feel free to report any bug or suggest an idea: @qw1zzard.',
        sep='',
    )
    await message.answer(msg, parse_mode=ParseMode.MARKDOWN)


@dp.message(Command(commands=['help']))
async def process_help_command(message: Message) -> None:
    msg = text(
        bold('I answer these commands:'),
        '/event - upcoming Grand Prix info',
        '/drivers - drivers table with their numbers',
        '/check - bet status and number of coins',
        '/bet - bet in the format «/bet number size»',
        '/news - news and development plans',
        '/help - list of commands.. that you already see',
        sep='\n',
    )
    await message.answer(msg, parse_mode=ParseMode.MARKDOWN)


async def on_startup() -> None:
    await database.connect()


async def on_shutdown() -> None:
    await database.disconnect()


async def main() -> None:
    await dp.start_polling(
        bot,
        skip_updates=True,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
    )


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
