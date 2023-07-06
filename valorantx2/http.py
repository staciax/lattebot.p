from __future__ import annotations

from typing import TYPE_CHECKING

from valorantx.enums import Region
from valorantx.http import EndpointType, HTTPClient as _HTTPClient, Route

from .auth import RiotAuth

if TYPE_CHECKING:
    from asyncio import AbstractEventLoop

    from valorantx.http import Response
    from valorantx.types import contracts, favorites, loadout, mmr, party, store

    from .auth import RiotAuth
    from .types import account_henrikdev


# fmt: off
__all__ = (
    'HTTPClient',
)
# fmt: on


class HTTPClient(_HTTPClient):
    def __init__(self, loop: AbstractEventLoop) -> None:
        super().__init__(loop, region=Region.AsiaPacific)  # default is AsiaPacific
        self.riot_auth: RiotAuth = RiotAuth()  # set riot auth to default

    def get_account(self, game_name: str, tag_line: str) -> Response[account_henrikdev.Response]:
        r = Route.from_url(
            'GET',
            'https://api.henrikdev.xyz/valorant/v1/account/{game_name}/{tag_line}',
            game_name=game_name,
            tag_line=tag_line,
        )
        return self.request(r, headers={})

    # store

    def post_store_storefront(self, *, riot_auth: RiotAuth | None = None) -> Response[store.StoreFront]:
        riot_auth = riot_auth or self.riot_auth
        headers = self.get_headers(riot_auth)
        region = self.get_region(riot_auth)
        r = Route('POST', '/store/v3/storefront/{puuid}', region, puuid=riot_auth.puuid)
        return self.request(r, headers=headers, json={})

    def get_store_storefronts_agent(self, *, riot_auth: RiotAuth | None = None) -> Response[store.AgentStoreFront]:
        riot_auth = riot_auth or self.riot_auth
        headers = self.get_headers(riot_auth)
        region = self.get_region(riot_auth)
        r = Route('GET', '/store/v1/storefronts/agent', region, EndpointType.pd)
        return self.request(r, headers=headers)

    def get_store_wallet(self, *, riot_auth: RiotAuth | None = None) -> Response[store.Wallet]:
        riot_auth = riot_auth or self.riot_auth
        headers = self.get_headers(riot_auth)
        region = self.get_region(riot_auth)
        r = Route('GET', '/store/v1/wallet/{puuid}', region, puuid=riot_auth.puuid)
        return self.request(r, headers=headers)

    # contracts

    def get_contracts(self, *, riot_auth: RiotAuth | None = None) -> Response[contracts.Contracts]:
        riot_auth = riot_auth or self.riot_auth
        headers = self.get_headers(riot_auth)
        region = self.get_region(riot_auth)
        r = Route('GET', '/contracts/v1/contracts/{puuid}', region, puuid=riot_auth.puuid)
        return self.request(r, headers=headers)

    # mmr

    def get_mmr_player(
        self,
        puuid: str | None = None,
        *,
        riot_auth: RiotAuth | None = None,
    ) -> Response[mmr.MatchmakingRating]:
        riot_auth = riot_auth or self.riot_auth
        headers = self.get_headers(riot_auth)
        puuid = puuid or riot_auth.puuid
        region = self.get_region(riot_auth)
        return self.request(Route('GET', '/mmr/v1/players/{puuid}', region, puuid=puuid), headers=headers)

    # loadout

    def get_personal_player_loadout(self, *, riot_auth: RiotAuth | None = None) -> Response[loadout.Loadout]:
        riot_auth = riot_auth or self.riot_auth
        headers = self.get_headers(riot_auth)
        region = self.get_region(riot_auth)
        r = Route('GET', '/personalization/v2/players/{puuid}/playerloadout', region, puuid=riot_auth.puuid)
        return self.request(r, headers=headers)

    # favorites

    def get_favorites(self, *, riot_auth: RiotAuth | None = None) -> Response[favorites.Favorites]:
        riot_auth = riot_auth or self.riot_auth
        headers = self.get_headers(riot_auth)
        region = self.get_region(riot_auth)
        r = Route('GET', '/favorites/v1/players/{puuid}/favorites', region, puuid=riot_auth.puuid)
        return self.request(r, headers=headers)

    # party

    def get_party_player(self, *, riot_auth: RiotAuth | None = None) -> Response[party.Player]:
        riot_auth = riot_auth or self.riot_auth
        headers = self.get_headers(riot_auth)
        region = self.get_region(riot_auth)
        r = Route('GET', '/parties/v1/players/{puuid}', region, EndpointType.glz, puuid=riot_auth.puuid)
        return self.request(r, headers=headers)

    def get_party(self, party_id: str, *, riot_auth: RiotAuth | None = None) -> Response[party.Party]:
        riot_auth = riot_auth or self.riot_auth
        headers = self.get_headers(riot_auth)
        region = self.get_region(riot_auth)
        r = Route('GET', '/parties/v1/parties/{party_id}', region, EndpointType.glz, party_id=party_id)
        return self.request(r, headers=headers)

    def post_party_invite_by_riot_id(
        self, party_id: str, name: str, tag: str, *, riot_auth: RiotAuth | None = None
    ) -> Response[party.Party]:
        riot_auth = riot_auth or self.riot_auth
        headers = self.get_headers(riot_auth)
        region = self.get_region(riot_auth)
        r = Route(
            'POST',
            '/parties/v1/parties/{party_id}/invites/name/{name}/tag/{tag}',
            region,
            EndpointType.glz,
            party_id=party_id,
            name=name,
            tag=tag,
        )
        return self.request(r, headers=headers)

    # utils

    def get_headers(self, riot_auth: RiotAuth, /) -> dict[str, str]:
        headers = {
            'Authorization': 'Bearer %s' % riot_auth.access_token,
            'X-Riot-Entitlements-JWT': riot_auth.entitlements_token,
            'X-Riot-ClientPlatform': HTTPClient.RIOT_CLIENT_PLATFORM,
            'X-Riot-ClientVersion': HTTPClient.RIOT_CLIENT_VERSION,
        }
        return headers

    def get_region(self, riot_auth: RiotAuth, /) -> Region:
        if riot_auth.region is None:
            return self.region
        return Region(riot_auth.region)
