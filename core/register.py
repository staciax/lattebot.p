import asyncio
import os

import aiohttp
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv('CLIENT_ID')
DISOCRD_TOKEN = os.getenv('DISCORD_TOKEN')


async def main() -> None:
    # docs: https://discord.com/developers/docs/resources/application-role-connection-metadata

    url = f'https://discord.com/api/v10/applications/{CLIENT_ID}/role-connections/metadata'

    # fmt: off
    playload = [
        {
            'key': 'tier',
            'name': 'Tier',
            'description': 'Competitive tier this season',
            'type': 2
        },
        {
            'key': 'matches',
            'name': 'Matches',
            'description': 'Number of matches this season',
            'type': 2
        },
        {
            'key': 'winrate',
            'name': 'Win Rate',
            'description': 'Win rate this season',
            'type': 2
        },
        {
            'key': 'combat_score',
            'name': 'Combat Score',
            'description': 'Combat score this season',
            'type': 2
        },
        {
            'key': 'verified',
            'name': 'Verified',
            'description': 'Verified account',
            'type': 7
        }
    ]
    # fmt: on

    async with aiohttp.ClientSession() as session:
        async with session.put(
            url=url,
            json=playload,
            headers={'Content-Type': 'application/json', 'Authorization': f'Bot {DISOCRD_TOKEN}'},
        ) as response:
            print(f'Discord returned : {response.status} {response.reason}')
            print(await response.text())


if __name__ == '__main__':
    asyncio.run(main())
