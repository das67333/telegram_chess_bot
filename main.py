import asyncio
import cairosvg
import chess
import chess.svg
import random
import stockfish
import telebot.async_telebot


TIME_MS_PER_MOVE = 200
BOARD_IMAGE_RESOLUTION = 640

with open('/telegram_chess_bot/token.cfg') as file:
    token = file.read().strip()
bot = telebot.async_telebot.AsyncTeleBot(token)

board, color, engine = None, None, None


def default_init():
    global board, color, engine
    board = chess.Board()
    color = chess.WHITE
    engine_path = '/telegram_chess_bot/stockfish-15.1'
    engine = stockfish.Stockfish(path=engine_path)


async def send_board_png(chat_id):
    image_svg = chess.svg.board(board,
                                orientation=color,
                                size=BOARD_IMAGE_RESOLUTION)
    cairosvg.svg2png(bytestring=image_svg, write_to='temp.png')
    with open('temp.png', 'rb') as file:
        await bot.send_photo(chat_id, file)


async def make_and_send_engine_move(chat_id):
    move = engine.get_best_move_time(TIME_MS_PER_MOVE)
    engine.make_moves_from_current_position([move])
    board.push_uci(move)
    await bot.send_message(chat_id, f'My move is {move}')


async def send_game_result(chat_id):
    winner = board.outcome().winner
    message = 'Draw'
    if winner == chess.WHITE:
        message = 'White won'
    if winner == chess.BLACK:
        message = 'Black won'
    await bot.send_message(chat_id, f'Game over! {message}')


@bot.message_handler(commands=['start', 'help'])
async def send_help(message):
    await bot.send_message(
        message.chat.id,
        'Hi! I know how to play chess.\n'
        'To start a new game, print "/new_game"\n'
        'To make a move, print it in UCI notation, e.g. "e2e4"\n'
        'To analyse the current position, print "/analyse"\n'
        'To ask me about the best move, print, "/best_move"\n'
        'To see all legal moves, print "/legal_moves"\n'
        'To change my skill level, print "/set_skill <n>", n in [0,20]\n'
        'To get help, print "/help"')


@bot.message_handler(commands=['new_game'])
async def start_new_game(message):
    markup = telebot.types.ReplyKeyboardMarkup(
        resize_keyboard=True, one_time_keyboard=True)
    item1 = telebot.types.KeyboardButton('Random')
    item2 = telebot.types.KeyboardButton('White')
    item3 = telebot.types.KeyboardButton('Black')
    markup.add(item1, item2, item3)
    await bot.send_message(
        message.chat.id, 'Which color do you prefer?',
        reply_markup=markup)
    default_init()
    global color
    color = None


@bot.message_handler(func=lambda message:
                     message.text in ('Random', 'White', 'Black'))
async def select_color(message):
    global color
    if color is not None:
        await bot.send_message(
            message.chat.id,
            'You cannot change your color during the game. '
            'Print "/new_game"')
        return
    if message.text == 'Random':
        message.text = random.choice(('White', 'Black'))
    if message.text == 'White':
        color = chess.WHITE
    if message.text == 'Black':
        color = chess.BLACK
        await make_and_send_engine_move(message.chat.id)
    await send_board_png(message.chat.id)


@bot.message_handler(regexp='[a-h][1-8][a-h][1-8]')
async def receive_move(message):
    if board.is_game_over():
        await bot.send_message(
            message.chat.id,
            'The game has already ended! '
            'You can start another one by printing "/new_game"')
        return
    move = message.text
    if chess.Move.from_uci(move) not in board.legal_moves:
        await bot.send_message(
            message.chat.id,
            'This move is not legal! Try again')
        return
    board.push_uci(move)
    engine.make_moves_from_current_position([move])
    if board.is_game_over():
        await send_game_result(message.chat.id)
        return
    await make_and_send_engine_move(message.chat.id)
    await send_board_png(message.chat.id)
    if board.is_game_over():
        await send_game_result(message.chat.id)


@bot.message_handler(commands=['analyse'])
async def send_wdl(message):
    if board.is_game_over():
        await bot.send_message(
            message.chat.id,
            'The game has already ended! '
            'You can start another one by printing "/new_game"')
        return
    w, d, l = map(lambda x: x / 10, engine.get_wdl_stats())
    await bot.send_message(
        message.chat.id,
        f'Probabilities:\n'
        f'Win: {w:.1f}%    Draw: {d:.1f}%    Lose: {l:.1f}%')


@bot.message_handler(commands=['best_move'])
async def send_best_move(message):
    if board.is_game_over():
        await bot.send_message(
            message.chat.id,
            'The game has already ended! '
            'You can start another one by printing "/new_game"')
        return
    move = engine.get_best_move_time(TIME_MS_PER_MOVE)
    await bot.send_message(
        message.chat.id,
        f'The best move in current position is {move}')


@bot.message_handler(commands=['legal_moves'])
async def send_legal_moves(message):
    if board.is_game_over():
        await bot.send_message(
            message.chat.id,
            'The game has already ended! '
            'You can start another one by printing "/new_game"')
        return
    moves = list(map(lambda x: x.uci(), board.legal_moves))
    await bot.send_message(
        message.chat.id,
        f'Legal moves are:\n{moves}'.replace("'", '"'))


@bot.message_handler(commands=['set_skill'])
async def set_skill_level(message):
    try:
        n = int(message.text.split()[1])
        if n < 0 or n > 20:
            raise RuntimeError('Wrong input')
        engine.set_skill_level(n)
        text = f'Set my skill level to {n}'
    except Exception:
        text = 'Wrong input! Try "/help"'
    await bot.send_message(message.chat.id, text)

if __name__ == '__main__':
    default_init()
    asyncio.run(bot.infinity_polling())
