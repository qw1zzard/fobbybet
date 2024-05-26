import logging
import requests
from aiogram import types, executor
from aiogram.utils.markdown import text, bold, italic
from aiogram.types import ParseMode

from config import (
    bot,
    dp,
    database,
    WEBHOOK_URL,
    WEBHOOK_PATH,
    WEBAPP_HOST,
    WEBAPP_PORT,
)
from check import check


async def on_startup(dp):
    """Webhook startup function."""
    logging.warning('Starting webhook connection.')
    await database.connect()
    await bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True)


async def on_shutdown(dp):
    """Webhook shutdown function."""
    logging.warning('Shutting down webhook connection.')
    await database.disconnect()
    await bot.delete_webhook()


@dp.message_handler(commands=['start'])
async def process_start_command(message: types.Message):
    """
    Handle /start command. Display the welcome message.
    """

    await database.execute(
        'INSERT INTO users (user_id, coins) '
        + 'VALUES (:user_id, 1000.0)'
        + 'ON CONFLICT (user_id) DO NOTHING;',
        values={'user_id': message.from_user.id},
    )

    msg = text(
        "Hi! I'm Fobby, ",
        italic('Formula One Betting Bot'),
        ', yeah.',
        '\n',
        'Use /help to get a list of commands. ',
        'If you are just a beginner, then /check: you already ',
        'have a thousand coins, spend them wisely!',
        sep='',
    )
    await message.answer(msg, parse_mode=ParseMode.MARKDOWN)


@dp.message_handler(commands=['event'])
async def process_event_command(message: types.Message):
    """
    Handle /event command. Display information about the upcoming Grand Prix.
    """

    url = 'https://ergast.com/api/f1/current/next.json'
    response = requests.get(url, timeout=10).json()['MRData']['RaceTable']['Races'][0]

    circuit_name = response['Circuit']['circuitName']
    circuit_link = response['Circuit']['url']
    msg = text(
        response['date'],
        ' - ',
        response['raceName'],
        ' at ',
        [circuit_name],
        '(',
        circuit_link,
        ')',
        sep='',
    )
    await message.answer(msg, parse_mode=ParseMode.MARKDOWN)


@dp.message_handler(commands=['drivers'])
async def process_drivers_command(message: types.Message):
    """
    Handle /drivers command. Display information about the peloton.
    """

    url = 'https://ergast.com/api/f1/current/drivers.json'
    response = requests.get(url, timeout=10).json()['MRData']['DriverTable']['Drivers']

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


async def bet(user_id, msg) -> bool:
    """
    Make bet and enter it into the database.
    """

    msg = msg.split()
    if len(msg) != 3:
        return False

    driver_id = int(msg[1])
    bet_value = float(msg[2])

    query = 'SELECT coins FROM users WHERE user_id = :user_id;'
    user_coins = await database.fetch_all(query=query, values={'user_id': user_id})
    user_coins = float([line[0] for line in user_coins][0])

    if 0 < bet_value <= user_coins:
        url = 'https://ergast.com/api/f1/current/next.json'
        next_event = requests.get(url, timeout=10).json()['MRData']['RaceTable'][
            'Races'
        ][0]['date']

        await database.execute(
            'INSERT INTO bets (user_id, event_date, driver_id, bet_value) '
            + 'VALUES (:user_id, :event_date, :driver_id, :bet_value);',
            values={
                'user_id': user_id,
                'event_date': next_event,
                'driver_id': driver_id,
                'bet_value': bet_value,
            },
        )

        await database.execute(
            'UPDATE users SET coins = (coins - :bet_value) '
            + 'WHERE user_id = :user_id;',
            values={'user_id': user_id, 'bet_value': bet_value},
        )
        return True
    else:
        return False


@dp.message_handler(commands=['bet'])
async def process_bet_command(message: types.Message):
    """
    Handle /check command. Check bet format and reference to function above.
    """

    if await bet(message.from_user.id, message.text):
        await message.answer(
            'Sports bet accepted! You can check with the command /check.'
        )
    else:
        await message.answer(
            'Please, use the format «/bet number size», '
            + "where number - driver's number from table "
            + '/drivers and size is positive real '
            + 'value of the bet.'
        )


@dp.message_handler(commands=['check'])
async def process_check_command(message: types.Message):
    """
    Handle /check command. Reference to function Check from check.py.
    """

    msg = await check(message.from_user.id)
    await message.answer(msg, parse_mode=ParseMode.MARKDOWN)


@dp.message_handler(commands=['news'])
async def process_news_command(message: types.Message):
    """
    Handle /news command. Display development plans, update news, etc.
    """

    msg = text(
        'I recently refactored the code to meet PEP 8 standards ',
        'at least a little bit. Check out my [GitHub]',
        '(https://github.com/qw1zzard/fobbybet). ',
        'Feel free to report any bug or suggest an idea: @qw1zzard.',
        sep='',
    )
    await message.answer(msg, parse_mode=ParseMode.MARKDOWN)


@dp.message_handler(commands=['help'])
async def process_help_command(message: types.Message):
    """
    Handle /help command. Display a text menu with available options.
    """

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


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    executor.start_webhook(
        dispatcher=dp,
        webhook_path=WEBHOOK_PATH,
        skip_updates=True,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        host=WEBAPP_HOST,
        port=WEBAPP_PORT,
    )
