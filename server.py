import json
import jsonpickle
from flask import Flask, request
import simple_websocket
import random

from model import *

app = Flask(__name__)


def make_hero(hero_name):
    hero = Hero(hero_name)
    print(hero.id)
    deck = []
    if hero_name == "Barbarian":
        for s in [SWORD, JUMP]:
            for _ in range(5):
                deck.append(SymbolCard({s: 1}))
    if hero_name == "Ranger":
        for _ in range(10):
            deck.append(SymbolCard({ARROW: 1}))
    random.shuffle(deck)
    return {
        "id": hero,
        "deck": deck,
        "hand": [SymbolCard({SWORD: 1}), SymbolCard({JUMP: 1}), SymbolCard({ARROW: 1})],
        "discard": [],
    }


ranger = make_hero("Ranger")
barb = make_hero("Barbarian")
hcps = HeroCardPositionSystem([ranger, barb])
new_card = SymbolCard({ARROW: 1})
hcps.play_area.append(new_card.id)
hcps.card_hero[new_card.id] = ranger["id"].id
hcps.hero_card[ranger["id"].id].append(new_card.id)
eds = EnemyDeckSystem(
    [
        EnemyCard("Slime", {SWORD: 2}),
        # EnemyCard("Bear", {ARROW: 1}),
        EnemyCard("Skeleton", {JUMP: 1}),
    ],
    BossCard("Baby Barbarian", {SWORD: 2, ARROW: 2, JUMP: 3}),
    hcps,
)
ees = EchoEmitSystem("server")

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


@app.route("/game", websocket=True)
def run_game():
    ws = simple_websocket.Server(request.environ)
    es = EmitSystem(lambda m: ws.send(json.dumps(m)), "server")
    wsi = len(wss)
    data = ws.receive()
    message = json.loads(data)
    assert message["message"] == "login", f"invalid command {message}"
    hero_name = message["hero_name"]
    for i, s in enumerate(wss):
        if s is not None:
            try:
                s.send(
                    json.dumps(
                        {
                            "actions": [
                                {
                                    "action": "player_join",
                                    "hero": hero_name,
                                }
                            ],
                        }
                    )
                )
            except (ConnectionResetError, simple_websocket.ConnectionClosed) as e:
                print("client", i, "disconnected")
                wss[i] = None
    ws.send(
        json.dumps(
            {
                "type": "init",
                "game": jsonpickle.encode(
                    {
                        "HeroCardPositionSystem": hcps,
                        "EnemyDeckSystem": eds,
                        "Entity": Entity.serialize(),
                        "System": System.serialize(),
                    }
                ),
            }
        )
    )
    wss.append(ws)
    try:
        while True:
            data = ws.receive()
            message = json.loads(data)
            print(message)
            System.inject(message)
            # print(f"{response=}")
            # if send_to_all:
            #     for i, s in enumerate(wss):
            #         try:
            #             if s is not None:
            #                 print("send to other client", i)
            #                 s.send(response)
            #         except ConnectionResetError:
            #             print("client", i, "disconnected")
            # else:
            #     print("send to requesting client", wsi)
            #     ws.send(response)
            System.update_all()
    except simple_websocket.ConnectionClosed:
        # TODO: handle rejoin
        pass
    wsi[wsi] = None
    return ""


if __name__ == "__main__":
    app.run()
