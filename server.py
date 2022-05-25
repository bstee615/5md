import json
import jsonpickle
from flask import Flask, request
import simple_websocket

from model import Game, SymbolCard, Symbols
app = Flask(__name__)

game = Game()
game.init_boss("Baby Barbarian")
hero = game.add_hero("Ranger")
hero.hand.append(SymbolCard({Symbols.SWORD: 1}))
hero.hand.append(SymbolCard({Symbols.SWORD: 1}))
hero.hand.append(SymbolCard({Symbols.ARROW: 1}))
game.add_enemy("Slime", {Symbols.SWORD: 2})
print(game)

def run_command(data):
    command = jsonpickle.decode(data)
    if command["command"] == "play_hero_card":
        result = game.play_hero_card(command["hero_name"], int(command["card_index"]))
        ret = {
            "command": "play_hero_card",
            "result": result,
            "game": jsonpickle.encode(game),
        }
    # elif command_split[0] == "list_cards":
    #     hero = game.heroes[command_split[1]]
    #     return f"{command_split[0]} {json.dumps([c.to_dict() for c in hero.hand])}"
    elif command["command"] == "init":
        ret = {
            "command": command,
            "game": jsonpickle.encode(game)
        }
    ret = json.dumps(ret)
    print(ret)
    return ret

@app.route('/game', websocket=True)
def run_game():
    ws = simple_websocket.Server(request.environ)
    try:
        while True:
            data = ws.receive()
            response = run_command(data)
            print(f"{response=}")
            ws.send(response)
    except simple_websocket.ConnectionClosed:
        pass
    return ''

if __name__ == '__main__':
    app.run()
