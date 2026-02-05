"""
Seed gifts_catalog with all 107 Fragment gift collections.
Run:  python -m app.seeds
"""

import asyncio
import logging

from sqlalchemy import select

from app.core.database import async_session
from app.models.gift import GiftCatalog

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# slug → (human name, total_supply or None)
# Supplies filled for the most popular; rest = None (will be updated by scanner).
FRAGMENT_GIFTS: list[tuple[str, str, int | None]] = [
    ("artisanbrick", "Artisan Brick", None),
    ("astralshard", "Astral Shard", None),
    ("bdaycandle", "B-Day Candle", None),
    ("berrybox", "Berry Box", None),
    ("bigyear", "Big Year", None),
    ("blingbinky", "Bling Binky", None),
    ("bondedring", "Bonded Ring", None),
    ("bowtie", "Bow Tie", None),
    ("bunnymuffin", "Bunny Muffin", None),
    ("candycane", "Candy Cane", None),
    ("cloverpin", "Clover Pin", None),
    ("cookieheart", "Cookie Heart", None),
    ("crystalball", "Crystal Ball", None),
    ("cupidcharm", "Cupid Charm", None),
    ("deskcalendar", "Desk Calendar", None),
    ("diamondring", "Diamond Ring", None),
    ("durovscap", "Durov's Cap", 5000),
    ("easteregg", "Easter Egg", None),
    ("electricskull", "Electric Skull", None),
    ("eternalcandle", "Eternal Candle", None),
    ("eternalrose", "Eternal Rose", None),
    ("evileye", "Evil Eye", None),
    ("faithamulet", "Faith Amulet", None),
    ("flyingbroom", "Flying Broom", None),
    ("freshsocks", "Fresh Socks", None),
    ("gemsignet", "Gem Signet", None),
    ("genielamp", "Genie Lamp", None),
    ("gingercookie", "Ginger Cookie", None),
    ("hangingstar", "Hanging Star", None),
    ("happybrownie", "Happy Brownie", None),
    ("heartlocket", "Heart Locket", None),
    ("heroichelmet", "Heroic Helmet", None),
    ("hexpot", "Hex Pot", None),
    ("holidaydrink", "Holiday Drink", None),
    ("homemadecake", "Homemade Cake", None),
    ("hypnolollipop", "Hypno Lollipop", None),
    ("icecream", "Ice Cream", None),
    ("inputkey", "Input Key", None),
    ("instantramen", "Instant Ramen", None),
    ("iongem", "Ion Gem", None),
    ("ionicdryer", "Ionic Dryer", None),
    ("jackinthebox", "Jack in the Box", None),
    ("jellybunny", "Jelly Bunny", None),
    ("jesterhat", "Jester Hat", None),
    ("jinglebells", "Jingle Bells", None),
    ("jollychimp", "Jolly Chimp", None),
    ("joyfulbundle", "Joyful Bundle", None),
    ("khabibspapakha", "Khabib's Papakha", None),
    ("kissedfrog", "Kissed Frog", None),
    ("lightsword", "Light Sword", None),
    ("lolpop", "Lolpop", None),
    ("lootbag", "Loot Bag", 5000),
    ("lovecandle", "Love Candle", None),
    ("lovepotion", "Love Potion", None),
    ("lowrider", "Lowrider", None),
    ("lunarsnake", "Lunar Snake", None),
    ("lushbouquet", "Lush Bouquet", None),
    ("madpumpkin", "Mad Pumpkin", None),
    ("magicpotion", "Magic Potion", None),
    ("mightyarm", "Mighty Arm", None),
    ("minioscar", "Mini Oscar", None),
    ("moneypot", "Money Pot", None),
    ("moonpendant", "Moon Pendant", None),
    ("moussecake", "Mousse Cake", None),
    ("nailbracelet", "Nail Bracelet", None),
    ("nekohelmet", "Neko Helmet", None),
    ("partysparkler", "Party Sparkler", None),
    ("perfumebottle", "Perfume Bottle", None),
    ("petsnake", "Pet Snake", None),
    ("plushpepe", "Plush Pepe", 2321),
    ("preciouspeach", "Precious Peach", None),
    ("prettyposy", "Pretty Posy", None),
    ("recordplayer", "Record Player", None),
    ("restlessjar", "Restless Jar", None),
    ("sakuraflower", "Sakura Flower", None),
    ("santahat", "Santa Hat", None),
    ("scaredcat", "Scared Cat", None),
    ("sharptongue", "Sharp Tongue", None),
    ("signetring", "Signet Ring", None),
    ("skullflower", "Skull Flower", None),
    ("skystilettos", "Sky Stilettos", None),
    ("sleighbell", "Sleigh Bell", None),
    ("snakebox", "Snake Box", None),
    ("snoopcigar", "Snoop Cigar", None),
    ("snoopdogg", "Snoop Dogg", None),
    ("snowglobe", "Snow Globe", None),
    ("snowmittens", "Snow Mittens", None),
    ("spicedwine", "Spiced Wine", None),
    ("springbasket", "Spring Basket", None),
    ("spyagaric", "Spy Agaric", None),
    ("starnotepad", "Star Notepad", None),
    ("stellarrocket", "Stellar Rocket", None),
    ("swagbag", "Swag Bag", None),
    ("swisswatch", "Swiss Watch", None),
    ("tamagadget", "Tamagadget", None),
    ("tophat", "Top Hat", None),
    ("toybear", "Toy Bear", None),
    ("trappedheart", "Trapped Heart", None),
    ("ufcstrike", "UFC Strike", None),
    ("valentinebox", "Valentine Box", None),
    ("vintagecigar", "Vintage Cigar", None),
    ("voodoodoll", "Voodoo Doll", None),
    ("westsidesign", "Westside Sign", None),
    ("whipcupcake", "Whip Cupcake", None),
    ("winterwreath", "Winter Wreath", None),
    ("witchhat", "Witch Hat", None),
    ("xmasstocking", "Xmas Stocking", None),
]

IMAGE_URL_TPL = "https://fragment.com/file/gifts/{slug}/thumb.webp"


async def seed_gifts() -> None:
    async with async_session() as session:
        existing = await session.execute(select(GiftCatalog.slug))
        existing_slugs = set(existing.scalars().all())

        added = 0
        for slug, name, supply in FRAGMENT_GIFTS:
            if slug in existing_slugs:
                continue
            session.add(
                GiftCatalog(
                    name=name,
                    slug=slug,
                    image_url=IMAGE_URL_TPL.format(slug=slug),
                    total_supply=supply,
                )
            )
            added += 1

        if added:
            await session.commit()
        logger.info("Seeded %d new gifts (%d already existed)", added, len(existing_slugs))


if __name__ == "__main__":
    asyncio.run(seed_gifts())
