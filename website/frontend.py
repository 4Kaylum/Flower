import base64
import random

from aiohttp.web import Request, RouteTableDef
from voxelbotutils import web as webutils
import aiohttp_session
from aiohttp_jinja2 import template


routes = RouteTableDef()
generated_herbiary = None
generated_herbiary_lifetime = 0


@routes.get("/")
@template("index.html.j2")
@webutils.add_discord_arguments()
async def index(request:Request):
    """
    Handle the index page for the website.
    """

    bot = request.app['bots']['bot']
    invite_link = bot.get_invite_link(**{i: True for i in bot.config['command_data']['invite_command_permissions']})
    return {
        'invite_link': invite_link,
        'vote_link': f"https://top.gg/bot/{request.app['config']['oauth']['client_id']}",
    }


@routes.get("/flowers")
@template("flowers.html.j2")
@webutils.requires_login()
@webutils.add_discord_arguments()
async def flowers(request:Request):
    """
    Show the users their flowers.
    """

    # Get the ID of the user signed in
    session = await aiohttp_session.get_session(request)
    user_id = session['user_id']

    # Grab their plants
    async with request.app['database']() as db:
        user_rows = await db("SELECT * FROM user_settings WHERE user_id=ANY($1::BIGINT[]) ORDER BY user_id DESC LIMIT 1", [user_id, 0])
        plant_rows = await db("SELECT * FROM plant_levels WHERE user_id=$1 ORDER BY plant_name ASC", user_id)
        user_inventory_rows = await db("SELECT * FROM user_inventory WHERE user_id=$1 ORDER BY item_name ASC", user_id)
    plants = [dict(i) for i in plant_rows]

    # Generate the base64 image data for each of the plants
    display_utils = request.app['bots']['bot'].get_cog("PlantDisplayUtils")
    for data in plants:
        plant_display_dict = display_utils.get_display_data(data, user_id=data['user_id'])
        display_data = display_utils.get_plant_image(**plant_display_dict)
        cropped_display_data = display_utils.crop_image_to_content(display_data)
        image_bytes = display_utils.image_to_bytes(cropped_display_data)
        data['image_data'] = base64.b64encode(image_bytes.read()).decode()

    # Fix up the inventory dictionary
    inventory = {i['item_name'].replace('_', ' ').title(): i['amount'] for i in user_inventory_rows}
    inventory.setdefault('Revival Token'.title(), 0)

    # Return data for the page
    return {
        'user': dict(user_rows[0]),
        'plants': plants,
        'inventory': inventory,
    }


@routes.get("/shop")
@template("shop.html.j2")
@webutils.requires_login()
@webutils.add_discord_arguments()
async def shop(request:Request):
    """
    Show the users their shop.
    """

    # Get the ID of the user signed in
    session = await aiohttp_session.get_session(request)
    user_id = session['user_id']

    # Grab their plants
    async with request.app['database']() as db:
        user_rows = await db("SELECT * FROM user_settings WHERE user_id=ANY($1::BIGINT[]) ORDER BY user_id DESC LIMIT 1", [user_id, 0])
        plant_rows = await db("SELECT * FROM plant_levels WHERE user_id=$1 ORDER BY plant_name ASC", user_id)
    plants = [dict(i) for i in plant_rows]

    async with request.app['database']() as db:
        user_rows = await db("SELECT * FROM user_settings WHERE user_id=ANY($1::BIGINT[]) ORDER BY user_id DESC LIMIT 1", [user_id, 0])
        if user_id:
            plant_rows = await db("SELECT * FROM plant_levels WHERE user_id=$1 ORDER BY plant_name ASC", user_id)
        else:
            plant_rows = await db("SELECT * FROM plant_levels ORDER BY RANDOM() ASC LIMIT 100")
    plants = [dict(i) for i in plant_rows]

    display_utils = request.app['bots']['bot'].get_cog("PlantDisplayUtils")
    for data in plants:
        plant_display_dict = display_utils.get_display_data(data, user_id=data['user_id'])
        display_data = display_utils.get_plant_image(**plant_display_dict)
        cropped_display_data = display_utils.crop_image_to_content(display_data)
        image_bytes = display_utils.image_to_bytes(cropped_display_data)
        data['image_data'] = base64.b64encode(image_bytes.read()).decode()

    return {
        'user': dict(user_rows[0]),
        'plants': plants,
    }


@routes.get("/herbiary")
@template("herbiary.html.j2")
@webutils.add_discord_arguments()
async def herbiary(request:Request):
    """
    Show the user the entire plant list.
    """

    global generated_herbiary
    global generated_herbiary_lifetime

    if generated_herbiary is None or generated_herbiary_lifetime >= 10:
        output = list(request.app['bots']['bot'].plants.copy().values())
        display_utils = request.app['bots']['bot'].get_cog("PlantDisplayUtils")
        for plant in output:
            plant_data = {'plant_type': plant.name, 'plant_nourishment': plant.max_nourishment_level, 'plant_pot_hue': random.randint(0, 359)}
            plant_display_dict = display_utils.get_display_data(plant_data)
            display_data = display_utils.get_plant_image(**plant_display_dict)
            cropped_display_data = display_utils.crop_image_to_content(display_data)
            image_bytes = display_utils.image_to_bytes(cropped_display_data)
            plant.image_data = base64.b64encode(image_bytes.read()).decode()
        generated_herbiary = output
        generated_herbiary_lifetime = -1
    generated_herbiary_lifetime += 1

    return {
        'plants': generated_herbiary,
    }


@routes.get("/commands")
@template("commands.html.j2")
@webutils.add_discord_arguments()
async def commands(request:Request):
    """
    Show the command list.
    """

    return {}
