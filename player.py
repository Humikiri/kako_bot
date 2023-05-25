import discord

class Player:
    queue = []

    def __init__(self, user: discord.User, time: str):
        self.user = user
        self.time = time
