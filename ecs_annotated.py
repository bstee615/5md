"""
simple ECS by mvanga
https://gist.github.com/mvanga/4b01cc085d9d16c3da68d289496e773f
https://www.reddit.com/r/roguelikedev/comments/9ug11a/entitycomponentsystem_implementation_in_less_than/
"""

import uuid
import json


# Returns a python dictionary given a file containing a JSON-based
# component definition. Every definition *must* contain a 'type'
# and 'schema' field inside a top-level dictionary. Here is an
# example of a simple schema file that defines a 'meta' component
# containing a 'name' field.
#
#     // Contents of meta.json
#     {
#         "type": "meta",
#         "schema": {
#             "name": ""
#         }
#     }
def Component(filename):
    with open(filename + '.json', 'r') as f:
        return json.load(f)


# The Entity class defines a single entity in our system composed
# of multiple components. At its heart, an Entity object is simply
# an empty bucket associated with a unique ID.
#
# This class provides exactly one relevant function: a way to
# attach a component dictionary to the entity. This function
# simply takes the dictionary loaded using the Component()
# function above, instantiates a new class on-the-fly, and
# sets a class attribute. Here is an example of how to attach
# our 'meta' object from above to an entity:
#
#     >>> e = Entity()
#     >>> e.__dict__
#     {'id': '5afec678-4c4e-44a9-be74-8764f62b61fd', 'components': []}
#     >>>
#     >>> e.attach(Component('meta'))
#     >>> pprint.pprint(e.__dict__)
#     {'components': ['meta'],
#      'id': '5afec678-4c4e-44a9-be74-8764f62b61fd',
#      'meta': <ecs.Component object at 0x108a1e400>}
#     >>> e.meta.name = 'Player'
#
# The attach() function also takes a namespace argument for
# renaming longer component names when creating the attribute:
#
#     >> e = Entity()
#     >> e.attach(Component('meta'), namespace='m')
#     >> e.m.name = 'Player'
#
# We also do some housekeeping: the 'components' object variable
# keeps track of all components attached to this entity:
#
#     >>> e = Entity()
#     >>> e.attach(Component('meta')
#     >>> e.components
#     ['meta']
#
# Note that namespacing maintains the original class name inside
# the components array:
#
#     >>> e = Entity()
#     >>> e.attach(Component('meta'), namespace='m')
#     >>> e.components
#     ['meta']
#
# Finally, we also track two reverse mappings: (i) to go from a
# given entity ID to an entity object, and (ii) to go from a
# component type to a list of entity objects. Both these are
# implemented as class methods so no instantiated object is needed
# to retrieve them.
#
# The first is useful in many cases where you want to reference a
# particular entity and use it in a system. For example, an attack
# component can simply store the ID of the entity being attacked.
# The damage-calculation system simply looks up the entity using
# this reverse index.
#
#     target = Entity.get('47d78b7e-8c5c-417b-8f46-be0de7c0b62d')
#
# The second index is used in implementing systems that deal with
# all entities having a particular component attached. For example,
# a MovementSystem can easily grab all entities containing a
# movement component:
#
#     entities = Entity.filter('movement')
#
class Entity(object):
    eindex = {}  # Index mapping entity IDs to entity objects
    cindex = {}  # Index mapping component names to entity objects

    def __init__(self):
        self.id = str(uuid.uuid4())
        self.components = []
        self.eindex[self.id] = self  # Assumes ID's never collide

    def attach(self, component, namespace=None):
        # Append component name to list of components
        self.components.append(component['type'])
        # Create a raw 'Component' object based on the JSON schema
        key = namespace if namespace else component['type']
        self.__dict__[key] = type('Component', (), component['schema'])()
        # Add to component index
        if component['type'] not in self.cindex:
            self.cindex[component['type']] = []
        self.cindex[component['type']].append(self)

    @classmethod
    def filter(cls, component):
        entities = cls.cindex.get(component)
        return entities if entities is not None else []

    @classmethod
    def get(cls, eid):
        return cls.eindex.get(eid)


# The final class that completes our ECS implementation is the System
# class for defining systems that update the world.
#
# The class is designed as a simple pub-sub system where each system
# decides which game events it wants to be notified of. This is done
# using the `subscribe()` method, which takes an event type (string)
# as a parameter.
#
# Each System object contains its own list of pending events and
# a class method, inject(), allows for injecting game events into the
# entire set of systems. This function it basically looks up all
# subscribers of that given event and simply appends the event into
# each of their event lists. Note that at this point, the event has
# not yet been handled, but simply registered as pending by appending
# into each subscriber's events list.
#
# The reason the inject() function is a class method and not an object
# level method is so that external parts of the game, such as the
# input system, can freely inject events into systems.
#
# Finally, the update() function can be overridden by subclasses to
# define their own custom game loop logic. The `pending()` function
# can be used here to retrieve (and clear) all pending events in the
# system, and the Entity.filter() function can be called to get a
# filtered list of entities relevant to this system. Here is a very
# simple example of how to implement a system:
#
#     class MovementSystem(System):
#         def __init__(self):
#             super().__init__()
#             self.subscribe('move')
#
#         def update(self):
#             # Get list of pending events and clear current event queue
#             events = self.pending()
#             # Filter entities by type. Fast because we use component_index.
#             entities = Entity.filter('movement')
#
#             # Do something here that modifies state or generates events
#
#             # Inject any new events at the end
#             self.inject({'type': 'move', 'data': randstr(10)})
#
# Note that above, the update() function first gets all pending events,
# runs some processing code, and finally, if needed, emits a new set of
# events that get picked up in the next round by other systems.
#
# Note that there is also no restriction on which entities you access in
# the update() function inside a System object. Above, I show an example
# of picking entities having a single component ('movement'), but you can
# instead easily choose to pick out different sets, apply any kind of
# set operators, etc. before arriving at the entities you need and
# continuing with the loop.
# 
# Here's a made-up example that illustrates how to do this using Python's
# built-in set operations:
# 
#     def update(self):
#         ent_with_move = set(Entity.filter('movement'))
#         ent_with_pos = set(Entity.filter('position'))
#         ent_with_ai = set(Entity.filter('ai'))
#         entities = list((ent_with_move& ent_with_pos) | ent_with_ai)
#     
#         # Rest of the loop goes here and uses 'entities'
#
class System(object):
    systems = []
    subscriptions = {}

    def __init__(self):
        self.events = []
        self.systems.append(self)

    def subscribe(self, event_type):
        if event_type not in self.subscriptions:
            self.subscriptions[event_type] = []
        self.subscriptions[event_type].append(self)

    def pending(self):
        # Get pending events and clear queue
        ret = self.events
        self.events = []
        return ret

    @classmethod
    def inject(cls, event):
        # All events must be dicts with a 'type' field
        event_type = event['type']
        if event_type not in cls.subscriptions:
            return
        for subscriber in cls.subscriptions[event_type]:
            subscriber.events.append(event)

    def update(self):
        pass

    @classmethod
    def update_all(cls):
        for system in cls.systems:
            system.update()