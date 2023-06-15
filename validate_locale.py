import json
import os

from discord.app_commands.commands import validate_context_menu_name, validate_name

for file in os.listdir('locales'):
    if file.endswith('.json'):
        with open(f'locales/{file}', 'r', encoding='utf-8') as f:
            data = json.load(f)

            # app commands
            for cog_name, cog_data in data['app_commands'].items():
                for app_cmd in cog_data.values():
                    try:
                        validate_name(app_cmd['name'])
                    except ValueError:
                        print(f'Invalid name: {app_cmd["name"]!r} in {cog_name} for {file}')

                    if app_cmd['description'] != '...':
                        if len(app_cmd['description']) < 1 or len(app_cmd['description']) > 100:
                            print(f'Invalid description: {app_cmd["description"]!r} in {cog_name} for {file}')

            # context menus
            for cog_name, cog_data in data['context_menus'].items():
                for ctx_menu in cog_data.values():
                    try:
                        validate_context_menu_name(ctx_menu['name'])
                    except ValueError:
                        print(f'Invalid name: {ctx_menu["name"]!r} in {cog_name} for {file}')

print('process finished')
