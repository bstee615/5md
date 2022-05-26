import json
import jsonpickle
from flask import Flask, request
import simple_websocket
import random

from model import ARROW, JUMP, SWORD, Game, SymbolCard
app = Flask(__name__)

game = Game()
game.init_boss("Baby Barbarian")
hero = game.add_hero("Ranger")
hero.hand.append(SymbolCard({SWORD: 1}))
hero.hand.append(SymbolCard({SWORD: 1}))
hero.hand.append(SymbolCard({ARROW: 1}))
hero.deck = []
for s in [SWORD, ARROW, JUMP]:
    for i in range(10):
        hero.deck.append(SymbolCard({s: 1}))
random.shuffle(hero.deck)
game.add_enemy("Slime", {SWORD: 2})
game.add_enemy("Skeleton", {ARROW: 1})
print(game)

"""
List of websockets.
Each item should be an active websocket or None.
TODO: This approach is not thread-safe and the websocket library may not be thread-safe,
so we should use a wrapper class for the collection and for access to the websockets.
The websocket should be deactivated after it quits out.

For messages that should be broadcasted to all clients, the endpoint handler will
loop through this collection to send the message.
"""
wss = []


def run_command(data):
    command = jsonpickle.decode(data)
    send_to_all = False
    if command["command"] == "play_hero_card":
        result, actions = game.play_hero_card(
            command["hero_name"], int(command["card_index"]))
        ret = {
            "command": "play_hero_card",
            "result": result,
            "actions": actions,
        }
        send_to_all = result != "error"
    elif command["command"] == "init":
        ret = {
            "command": command,
            "game": jsonpickle.encode(game)
        }
    ret = json.dumps(ret)
    print(ret)
    return ret, send_to_all


@app.route('/game', websocket=True)
def run_game():
    ws = simple_websocket.Server(request.environ)
    wsi = len(wss)
    try:
        while True:
            data = ws.receive()
            response, send_to_all = run_command(data)
            print(f"{response=}")
            if send_to_all:
                for s in wss:
                    if s is not None:
                        s.send(response)
            else:
                ws.send(response)
    except simple_websocket.ConnectionClosed:
        pass
    wsi[wsi] = None
    return ''


if __name__ == '__main__':
    app.run()
