def get_content_tier_emoji(key: str, *, old: bool = False) -> str:
    key = f'old_{key}' if old else key
    emojis = {
        'deluxe': '<:new_content_tier_deluxe:1083077781295992902>',
        'exclusive': '<:new_content_tier_exclusive:1083077759586283614>',
        'premium': '<:new_content_tier_premium:1083077743945728132>',
        'select': '<:new_content_tier_select:1083077724022788166>',
        'ultra': '<:new_content_tier_ultra:1083077703638458400>',
        'old_deluxe': '<:content_tier_deluxe:1042810257426108557>',
        'old_exclusive': '<:content_tier_exclusive:1042810259317735434>',
        'old_premium': '<:content_tier_premium:1042810261289050224>',
        'old_select': '<:content_tier_select:1042810263361036360>',
        'old_ultra': '<:content_tier_ultra:1042810265906991104>',
    }
    return emojis.get(key.lower(), '')


def get_tier_emoji(key: str) -> str:
    emojis = {
        'love': '<:love:1056499604033642578>',
        'radiant': '<:tier_radiant:1043967005956509760>',
        'immortal_3': '<:tier_immortal_3:1043966994665443398>',
        'immortal_2': '<:tier_immortal_2:1043966983068209243>',
        'immortal_1': '<:tier_immortal_1:1043966961782112316>',
        'immortal': '<:tier_immortal_3:1043966994665443398>',
        'ascendant_3': '<:tier_ascendant_3:1043966927468503111>',
        'ascendant_2': '<:tier_ascendant_2:1043966916865310751>',
        'ascendant_1': '<:tier_ascendant_1:1043966907180646521>',
        'diamond_3': '<:tier_diamond_3:1043966895201718453>',
        'diamond_2': '<:tier_diamond_2:1043966882518151260>',
        'diamond_1': '<:tier_diamond_1:1043966868756635708>',
        'platinum_3': '<:tier_platinum_3:1043966856983228418>',
        'platinum_2': '<:tier_platinum_2:1043966847139196999>',
        'platinum_1': '<:tier_platinum_1:1043966836498235452>',
        'gold_3': '<:tier_gold_3:1043966825815355443>',
        'gold_2': '<:tier_gold_2:1043966814301999205>',
        'gold_1': '<:tier_gold_1:1043966803023511602>',
        'silver_3': '<:tier_silver_3:1043966751643275324>',
        'silver_2': '<:tier_silver_2:1043966739773411338>',
        'silver_1': '<:tier_silver_1:1043966727081427105>',
        'bronze_3': '<:tier_bronze_3:1043966716222394428>',
        'bronze_2': '<:tier_bronze_2:1043966705875034182>',
        'bronze_1': '<:tier_bronze_1:1043966695527694497>',
        'iron_3': '<:tier_iron_3:1043966681032183908>',
        'iron_2': '<:tier_iron_2:1043966668298260550>',
        'iron_1': '<:tier_iron_1:1043966655753113680>',
        'unranked': '<:tier_unranked:1043966640674574366>',
    }
    return emojis.get(key.replace(' ', '_').lower(), '')
