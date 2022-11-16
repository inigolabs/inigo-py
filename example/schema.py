import datetime
import math
import json
import jwt
import graphene
import inigo_py

from ruamel.yaml import YAML
from pathlib import Path

yaml = YAML(typ='safe', pure=True)
data = yaml.load(Path('./starwars_data.yaml'))


class Version(graphene.ObjectType):
    name = graphene.String(required=True)
    version = graphene.String(required=True)
    commit = graphene.String(required=True)
    date = graphene.String(required=True)


class Person(graphene.ObjectType):
    def __init__(self, my_dict):
        for key in my_dict:
            setattr(self, key, my_dict[key])

    id = graphene.ID(required=True)
    name = graphene.String(required=True)
    ssn = graphene.String(required=True)
    birthYear = graphene.String(required=True)
    eyeColor = graphene.String(required=True)
    gender = graphene.String(required=True)
    hairColor = graphene.String(required=True)
    height = graphene.Int(required=True)
    mass = graphene.Float()
    skinColor = graphene.String()

    appeared_in = graphene.List(graphene.NonNull('schema.Film'), required=True)
    piloted_starship = graphene.List(graphene.NonNull('schema.Starship'), required=True)

    def resolve_appeared_in(root, info):
        result = []
        for index, item in enumerate(data.get('film')):
            if item.get('edges') and item.get('edges').get('has_person') and \
                    item.get('edges').get('has_person').count(root.id) > 0:
                p = Film(item)
                p.id = index
                result.append(p)

        return result

    def resolve_piloted_starship(root, info):
        result = []
        for index, item in enumerate(root.edges.get('piloted_starship')):
            v = Starship(data.get('starship')[item])
            v.id = index
            result.append(v)

        return result


class Vehicle(graphene.ObjectType):
    def __init__(self, my_dict):
        for key in my_dict:
            setattr(self, key, my_dict[key])

    id = graphene.ID(required=True)
    cargoCapacity = graphene.Int()
    consumables = graphene.String(required=True)
    costInCredits = graphene.Int(required=True)
    crew = graphene.String(required=True)
    length = graphene.Float()
    manufacturer = graphene.String(required=True)
    maxAtmospheringSpeed = graphene.String(required=True)
    model = graphene.String(required=True)
    name = graphene.String(required=True)
    passengerCapacity = graphene.Int()

    piloted_by = graphene.List(graphene.NonNull(Person), required=True)

    def resolve_piloted_by(root, info):
        result = []
        for index, person in enumerate(data.get('person')):
            if person.get('edges') and person.get('edges').get('piloted_vehicle') and \
                    person.get('edges').get('piloted_vehicle').count(root.id) > 0:
                        p = Person(person)
                        p.id = index
                        result.append(p)

        return result


class Planet(graphene.ObjectType):
    id = graphene.ID(required=True)
    climate = graphene.String(required=True)
    diameter = graphene.Int()
    gravity = graphene.String(required=True)
    name = graphene.String(required=True)
    orbital_period = graphene.String(required=True)
    population = graphene.Int()
    rotation_period = graphene.String(required=True)
    surface_water = graphene.String(required=True)
    terrain = graphene.String(required=True)


class Film(graphene.ObjectType):
    def __init__(self, my_dict):
        for key in my_dict:
            setattr(self, key, my_dict[key])

    id = graphene.ID(required=True)
    title = graphene.String(required=True)
    director = graphene.String(required=True)
    episode_id = graphene.Int(required=True)
    openingCrawl = graphene.String(required=True)
    producer = graphene.String(required=True, deprecation_reason="deprecated")

    vehicles = graphene.List(graphene.NonNull(Vehicle))
    planets = graphene.List(graphene.NonNull(Planet))

    def resolve_vehicles(root, info):
        result = []
        for index, item in enumerate(root.edges.get('has_vehicle')):
            v = Vehicle(data.get('vehicle')[item])
            v.id = index
            result.append(v)

        return result

    def resolve_planets(root, info):
        return [data.get('planet')[i] for i in root.edges.get('has_planet')]


class Starship(graphene.ObjectType):
    id = graphene.ID(required=True)
    cargoCapacity = graphene.Int()
    consumables = graphene.String(required=True)
    costInCredits = graphene.Int(required=True)
    crew = graphene.String(required=True)
    hyperdriveRating = graphene.String(required=True)
    length = graphene.Float(required=True)
    manufacturer = graphene.String(required=True)
    maxAtmospheringSpeed = graphene.String(required=True)
    maximumMegalights = graphene.String()
    model = graphene.String(required=True)
    name = graphene.String(required=True)
    passengerCapacity = graphene.Int()

    piloted_by = graphene.List(graphene.NonNull(Person), required=True)

    def resolve_piloted_by(root, info):
        result = []
        for index, person in enumerate(data.get('person')):
            if person.get('edges') and person.get('edges').get('piloted_starship') and \
                    person.get('edges').get('piloted_starship').count(root.id) > 0:
                p = Person(person)
                p.id = index
                result.append(p)

        return result


class PlanetInput(graphene.InputObjectType):
    climate = graphene.String(required=True)
    diameter = graphene.Int()
    gravity = graphene.String(required=True)
    name = graphene.String(required=True)
    orbital_period = graphene.String(required=True)
    population = graphene.Int()
    rotation_period = graphene.String(required=True)
    surface_water = graphene.String(required=True)
    terrain = graphene.String(required=True)


class FilmInput(graphene.InputObjectType):
    director = graphene.String(required=True)
    producer = graphene.String(required=True)
    episodeId = graphene.Int(required=True)
    openingCrawl = graphene.String(required=True)
    planets = graphene.List(graphene.NonNull(PlanetInput, required=True))


class Query(graphene.ObjectType):
    version = graphene.Field(Version, required=True)

    login = graphene.Field(graphene.String, username=graphene.NonNull(graphene.String), password=graphene.NonNull(graphene.String))
    logout = graphene.Field(graphene.Boolean, required=True)

    film = graphene.Field(Film, title=graphene.String(required=True))
    films = graphene.Field(graphene.List(graphene.NonNull(Film)), required=True)

    starships = graphene.Field(graphene.List(graphene.NonNull(Starship)), required=True)

    def resolve_version(root, info):
        return json.loads(inigo_py.get_version())

    def resolve_login(root, info, username, password):
        users = list(filter(lambda item: item['username'] == username, data.get('user')))
        if len(users) == 1:
            user = users[0]
            if password == user.get('password'):
                now = int(datetime.datetime.now().strftime("%Y%m%d%H%M%S"))

                iat = math.floor(now / 1000)
                exp = iat + (60 * 60 * 24)

                token = jwt.encode(
                    payload={
                        'iat': iat,
                        'exp': exp,
                        'user_profile': user.get('profile'),
                        'user_roles': user.get('roles'),
                        'user_id': user.get('id'),
                        'user_name': user.get('username'),
                        'token': "2317d727-8b5d-403c-953d-8c80af72cac9",
                    },
                    key="Iloveinigo!"
                )
                return token

    def resolve_logout(root, info):
        return True

    def resolve_film(root, info, title):
        for index, film in enumerate(data.get('film')):
            if film.get('title') == title:
                f = Film(film)
                f.id = index
                return Film(film)

    def resolve_films(root, info):
        result = []
        for index, item in enumerate(data.get('film')):
            v = Film(item)
            v.id = index
            result.append(v)

        return result

    def resolve_starships(root, info):
        result = []
        for index, item in enumerate(data.get('starship')):
            v = Starship(item)
            v.id = index
            result.append(v)

        return result


class Mutation(graphene.ObjectType):
    film_add = graphene.Field(graphene.String, title=graphene.NonNull(graphene.String), input=graphene.NonNull(FilmInput))

    def resolve_film_add(root, info, title, input: FilmInput):
        planetsIds = []

        for planet in input.planets:
            planetsIds.append(len(data.get('planet')))

            data.get('planet').append({
                'climate': planet.climate,
                'diameter': planet.diameter,
                'gravity': planet.gravity,
                'name': planet.name,
                'orbital_period': planet.orbital_period,
                'population': planet.population,
                'rotation_period': planet.rotation_period,
                'surface_water': planet.surface_water,
                'terrain': planet.terrain
            })

        data.get('film').append({
            'title': title,
            'director': input.director,
            'episode_id': input.episodeId,
            'opening_crawl': input.openingCrawl,
            'producer': input.producer,
            'edges': {
                'has_planet': planetsIds
            }

        })

        return title


schema = graphene.Schema(query=Query, mutation=Mutation)
