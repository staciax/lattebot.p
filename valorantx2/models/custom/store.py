from __future__ import annotations

from typing import TYPE_CHECKING

from valorantx.models.contracts import RecruitmentProgressUpdate
from valorantx.models.store import AgentStore as _AgentStore

# fmt: off
__all__ = (
    'AgentStore',
)
# fmt: on

if TYPE_CHECKING:
    from ...auth import RiotAuth
    from ...client import Client


class AgentStore(_AgentStore):
    if TYPE_CHECKING:
        _client: Client

    async def fetch_featured_agent_recruitment_progress(
        self,
        *,
        riot_auth: RiotAuth | None = None,
    ) -> RecruitmentProgressUpdate | None:
        contracts = await self._client.fetch_contracts(riot_auth=riot_auth)
        for processed_match in sorted(
            contracts.processed_matches,
            key=lambda x: x.recruitment_progress_update.progress_after if x.recruitment_progress_update else -1,
            reverse=True,
        ):
            if processed_match.recruitment_progress_update is None:
                continue
            if processed_match.recruitment_progress_update.group_id == self.featured_agent_id:
                return processed_match.recruitment_progress_update
        return None
