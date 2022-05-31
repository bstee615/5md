import json
import jsonpickle
from flask import Flask, request
import simple_websocket
import random

from model import ARROW, JUMP, SWORD, Game, SymbolCard
app = Flask(__name__)

game = Game()
game.init_boss("Baby Barbarian")
game.add_enemy("Slime", {SWORD: 2})
game.add_enemy("Skeleton", {ARROW: 1})

def make_hero(hero_name):
    hero = game.add_hero(hero_name)
    if hero_name == "Barbarian":
        hero.hand.append(SymbolCard({SWORD: 1}))
        hero.hand.append(SymbolCard({JUMP: 1}))
        hero.hand.append(SymbolCard({ARROW: 1}))
        hero.deck = []
        for s in [SWORD, JUMP]:
            for i in range(5):
                hero.deck.append(SymbolCard({s: 1}))
        random.shuffle(hero.deck)
    if hero_name == "Ranger":
        hero.hand.append(SymbolCard({ARROW: 1}))
        hero.hand.append(SymbolCard({ARROW: 1}))
        hero.hand.append(SymbolCard({JUMP: 1}))
        hero.deck = []
        for s in [ARROW]:
            for i in range(10):
                hero.deck.append(SymbolCard({s: 1}))
        random.shuffle(hero.deck)
    return hero

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
    data = ws.receive()
    command = json.loads(data)
    assert command["command"] == "login", f"invalid command {command}"
    hero_name = command["hero_name"]
    hero = game.heroes.get(hero_name, make_hero(hero_name))
    for i, s in enumerate(wss):
        if s is not None:
            try:
                s.send(json.dumps({
                    "actions": [{
                        "action": "player_join",
                        "hero": jsonpickle.encode(hero),
                    }],
                }))
            except ConnectionResetError:
                print("client", i, "disconnected")
                wss[i] = None
    wss.append(ws)
    try:
        while True:
            data = ws.receive()
            response, send_to_all = run_command(data)
            print(f"{response=}")
            if send_to_all:
                for i, s in enumerate(wss):
                    try:
                        if s is not None:
                            print("send to other client", i)
                            s.send(response)
                    except ConnectionResetError:
                        print("client", i, "disconnected")
            else:
                print("send to requesting client", wsi)
                ws.send(response)
    except simple_websocket.ConnectionClosed:
        pass
    wsi[wsi] = None
    return ''


if __name__ == '__main__':
    app.run()
