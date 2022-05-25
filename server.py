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

def run_command(command):
    command_split = command.split()
    print(f"command {command_split}")
    if command_split[0] == "play_hero_card":
        result = game.play_hero_card(command_split[1], int(command_split[2]))
        return f"play_hero_card {result}"
    # elif command_split[0] == "list_cards":
    #     hero = game.heroes[command_split[1]]
    #     return f"{command_split[0]} {json.dumps([c.to_dict() for c in hero.hand])}"
    elif command_split[0] == "init":
        return jsonpickle.encode(game)
    print(game)

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
