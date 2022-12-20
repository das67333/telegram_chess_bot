FROM ubuntu:latest

RUN apt update
RUN apt install -y git python3 python3-pip python3-cairo
RUN pip install aiohttp asyncio cairosvg chess pyTelegramBotAPI stockfish
COPY . /telegram_chess_bot

CMD cd /telegram_chess_bot && python3 main.py
