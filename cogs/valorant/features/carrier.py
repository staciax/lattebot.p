# class SelectMatchHistory(ui.Select['CarrierView']):
#     def __init__(self, *, options: list[discord.SelectOption], locale: discord.Locale) -> None:
#         super().__init__(
#             options=options or [discord.SelectOption(label=_('No Match History', locale), value='0')],
#             placeholder=_('Select Match to see details', locale),
#             row=1,
#             disabled=not options,
#         )
#         self.locale = locale

#     @classmethod
#     def from_match_history(
#         cls,
#         *,
#         match_history: MatchHistory,
#         locale: discord.Locale,
#     ) -> Self:
#         options = []
#         for match in match_history.match_details:
#             me = match.get_player(match_history.subject)
#             if me is None:
#                 continue

#             # find match score
#             left_team_score, right_team_score = find_match_score_by_player(match, me)  # type: ignore

#             # build option
#             option = discord.SelectOption(
#                 label=f'{left_team_score} - {right_team_score}',
#                 value=match.match_info.match_id,
#             )

#             # add emoji
#             if me.agent is not None:
#                 option.emoji = getattr(me.agent, 'emoji', None)

#             # add description
#             game_mode = match.match_info.game_mode
#             match_map = match.match_info.map
#             if match_map is not None and game_mode is not None:
#                 option.description = '{map} - {gamemode}'.format(
#                     map=match_map.display_name.from_locale(locale_converter.to_valorant(locale)),
#                     gamemode=game_mode.display_name.from_locale(locale_converter.to_valorant(locale)),
#                 )
#             options.append(option)
#         return cls(options=options, locale=discord.Locale.american_english)

#     def clear(self) -> None:
#         self.options.clear()

#     def add_dummy(self) -> None:
#         assert self.view is not None
#         self.clear()
#         self.add_option(label=_('No Match History', self.view.locale), value='0', emoji='📭')
#         self.disabled = True

#     async def callback(self, interaction: discord.Interaction[LatteMaid]) -> None:
#         assert self.view is not None
#         # async with self.view.lock:
#         #     value = self.values[0]

#         #     await interaction.response.defer()

#         #     if self.puuid == '':
#         #         return

#         #     if value not in self._source:
#         #         return

#         #     # build source
#         #     source = MatchDetailsPageSource(self._source[value], self.puuid, locale_converter.to_valorant(self.view.locale))
#         #     self.match_details_view.source = source

#         #     # set message
#         #     if self.match_details_view.message is None and self.view.message is not None:
#         #         self.match_details_view.message = self.view.message

#         #     # start view
#         #     await self.match_details_view.start()


# class CarrierView(BaseView, LattePages):
#     def __init__(
#         self,
#         interaction: discord.Interaction[LatteMaid],
#         queue_id: str | None = None,
#     ) -> None:
#         super().__init__(interaction=interaction)
#         self.queue_id: str | None = queue_id
#         self.embeds: list[Embed] = []

#     def fill_items(self) -> None:
#         super().fill_items()
#         self.remove_item(self.stop_pages)
#         self.remove_item(self.numbered_page)

#     async def set_source(self) -> None:
#         assert self.account_manager is not None
#         assert self.current_puuid is not None
#         match_history = await self.valorant_client.fetch_match_history(
#             puuid=self.current_puuid,
#             queue=self.queue_id,
#             with_details=True,
#         )
#         self.add_item(
#             SelectMatchHistory.from_match_history(match_history=match_history, locale=self.locale),
#         )
#         self.source = CarrierPageSource(puuid=riot_auth.puuid, data=match_history.match_details)  # type: ignore

#     async def start_valorant(self) -> None:
#         await self.interaction.response.defer()
#         await self._init()
#         await self.set_source()
#         await self.start()


# class MatchDetailsPageSource(ListPageSource):
#     def __init__(self, match_details: MatchDetails, puuid: str, locale: discord.Locale) -> None:
#         self.puuid = puuid
#         self.locale = locale
#         self.match_embed = e.MatchDetailsEmbed(match_details)  # type: ignore
#         super().__init__(self.build_entries(locale), per_page=1)

#     def build_entries(self, locale: discord.Locale) -> list[tuple[Embed, Embed]]:
#         entries = []
#         try:
#             desktops, mobiles = self.match_embed.build(self.puuid, locale=locale_converter.to_valorant(locale))
#         except Exception as exc:
#             _log.error(f'failed to build match details embed for {self.puuid}', exc_info=exc)
#         else:
#             for dt, mb in zip(desktops, mobiles):
#                 entries.append((dt, mb))
#         return entries

#     def format_page(self, menu: MatchDetailsView, entries: tuple[Embed, Embed]) -> Embed:
#         desktops, mobiles = entries

#         # locale changed
#         if menu.locale != self.locale:
#             self.locale = menu.locale
#             self.entries = self.build_entries(self.locale)
#             desktops, mobiles = self.entries[menu.current_page]

#         return mobiles if menu.is_on_mobile() else desktops


# class MatchDetailsView(ViewAuthor, LattePages):
#     __view_on_mobile__: bool = False

#     def __init__(self, interaction: discord.Interaction[LatteMaid]) -> None:
#         super().__init__(interaction)
#         self.compact = True
#         # self.source = source
#         # self.carrier_view: Optional[CarrierView] = carrier_view
#         # self.valorant_locale: ValorantLocale = locale_converter.to_valorant(interaction.locale)
#         # self.back_to_home.label = _('Back', self.locale)

#     def fill_items(self) -> None:
#         # if self.carrier_view is not None:
#         #     self.add_item(self.back_to_home)
#         super().fill_items()
#         self.remove_item(self.go_to_last_page)
#         self.remove_item(self.go_to_first_page)
#         self.remove_item(self.stop_pages)
#         self.go_to_next_page.label = self.go_to_last_page.label
#         self.go_to_previous_page.label = self.go_to_first_page.label
#         # self.add_item(self.toggle_ui)

#     def is_on_mobile(self) -> bool:
#         return self.__view_on_mobile__

#     # @ui.button(emoji='📱', style=ButtonStyle.green)
#     # async def toggle_ui(self, interaction: discord.Interaction[LatteMaid], button: ui.Button) -> None:
#     #     button.emoji = '📱' if self.is_on_mobile() else '💻'
#     #     self.__view_on_mobile__ = not self.is_on_mobile()
#     #     await self.show_checked_page(interaction, self.current_page)

#     # @ui.button(label=_('Back'), style=ButtonStyle.gray, custom_id='home_button')
#     # async def back_to_home(self, interaction: discord.Interaction[LatteMaid], button: ui.Button) -> None:
#     #     # assert self.carrier_view is not None
#     #     await interaction.response.defer()

#     #     if self.carrier_view is None:
#     #         return

#     #     if self.message is None:
#     #         return

#     #     self.carrier_view.reset_timeout()

#     #     await self.safe_edit_message(self.message, embeds=self.carrier_view.embeds, view=self.carrier_view)
