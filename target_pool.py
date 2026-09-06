"""A pool of 20 detailed, hard-to-replicate image prompts used to
generate target images. Each entry also carries 1-2 'banned_words' --
used only when that entry happens to land in Level 2 for a given
randomization, so the ban feels specific to that image rather than generic.
"""

TARGET_POOL = [
    {
        "label": "Astro Horse",
        "prompt": "A realistic astronaut in a full white spacesuit riding a brown horse across the grey cratered surface of the moon, Earth visible as a small blue marble in the black sky, long shadows cast by low sunlight, dust kicked up by the horse's hooves",
        "banned_words": "astronaut,horse",
        "required_words": "shadow,silence",
    },
    {
        "label": "Clockwork Owl",
        "prompt": "A steampunk mechanical owl made of brass gears and copper feathers, perched on a stack of old leather-bound books, warm candlelight glinting off the metal, faint steam rising from a small pipe on its chest",
        "banned_words": "owl,gears",
        "required_words": "warmth,pages",
    },
    {
        "label": "Neon Alley",
        "prompt": "A narrow rain-soaked alley in a cyberpunk city at night, glowing pink and cyan neon signs reflected in puddles on the ground, steam rising from a street vent, a single red umbrella walking away in the distance",
        "banned_words": "neon,rain",
        "required_words": "echo,solitary",
    },
    {
        "label": "Glass Whale",
        "prompt": "A translucent glass whale swimming through a starry night sky above a quiet mountain village, tiny galaxies visible inside its body, soft blue bioluminescent glow along its fins, snow-capped peaks below",
        "banned_words": "whale,glass",
        "required_words": "silent,drift",
    },
    {
        "label": "Desert Chess",
        "prompt": "An oversized marble chess set abandoned in the middle of a golden sand desert at sunset, half the pieces toppled and half-buried in dunes, long dramatic shadows, a single black king piece standing upright in the foreground",
        "banned_words": "chess,desert",
        "required_words": "forgotten,stillness",
    },
    {
        "label": "Coral Library",
        "prompt": "An underwater library built from coral and sunken ship wood, colorful fish swimming between floating bookshelves, shafts of sunlight piercing down through turquoise water, a sea turtle resting on an open book",
        "banned_words": "library,coral",
        "required_words": "hidden,quiet",
    },
    {
        "label": "Origami Storm",
        "prompt": "A paper origami crane caught mid-flight inside a swirling thunderstorm, lightning illuminating its folded white creases, dark storm clouds and rain streaks in the background, dramatic low-angle shot",
        "banned_words": "origami,crane",
        "required_words": "fragile,fury",
    },
    {
        "label": "Floating Teahouse",
        "prompt": "A traditional Japanese teahouse floating on a cloud above a misty mountain valley, red paper lanterns hanging from its eaves glowing warmly at dusk, cherry blossom petals drifting in the wind",
        "banned_words": "teahouse,cloud",
        "required_words": "gentle,drifting",
    },
    {
        "label": "Ice Fox",
        "prompt": "A crystalline fox made entirely of translucent blue ice standing on a frozen lake under the aurora borealis, its breath visible as a small cloud, cracks of light glowing faintly beneath the ice surface",
        "banned_words": "fox,ice",
        "required_words": "frozen,glow",
    },
    {
        "label": "Clocktower Garden",
        "prompt": "An overgrown Victorian clocktower reclaimed by nature, thick ivy and wildflowers growing through its cracked stone walls, the clock face stopped at midnight, golden late-afternoon light filtering through the vines",
        "banned_words": "clocktower,ivy",
        "required_words": "forgotten,wild",
    },
    {
        "label": "Jellyfish Balloons",
        "prompt": "A cluster of giant glowing jellyfish floating like hot air balloons above a nighttime carnival, their tentacles trailing down over ferris wheel lights, warm string lights and a crowd of tiny silhouetted people below",
        "banned_words": "jellyfish,carnival",
        "required_words": "floating,glow",
    },
    {
        "label": "Sand Dragon",
        "prompt": "A colossal dragon sculpted entirely from wet beach sand, half-collapsed by an incoming tide, small crabs crawling over its detailed scales, orange sunset light and gentle waves washing at its base",
        "banned_words": "dragon,sand",
        "required_words": "fading,ancient",
    },
    {
        "label": "Subway Forest",
        "prompt": "An abandoned subway station completely overtaken by a dense forest, tree roots breaking through the tiled floor, a single shaft of light coming down through a broken ceiling grate, moss covering an old bench",
        "banned_words": "subway,forest",
        "required_words": "abandoned,reclaimed",
    },
    {
        "label": "Paper Boat Ocean",
        "prompt": "A tiny white paper boat sailing on a vast dark stormy ocean under a crescent moon, enormous waves towering around it, a faint lighthouse beam visible far in the distance, dramatic high-contrast lighting",
        "banned_words": "boat,ocean",
        "required_words": "tiny,vast",
    },
    {
        "label": "Mushroom Village",
        "prompt": "A miniature fantasy village built inside giant red-and-white spotted mushrooms in a mossy forest, tiny lit windows carved into the mushroom stalks, fireflies glowing in the twilight air, a wooden bridge connecting two mushrooms",
        "banned_words": "mushroom,village",
        "required_words": "hidden,tiny",
    },
    {
        "label": "Marble Hands",
        "prompt": "Two enormous cracked marble statue hands rising out of calm turquoise water, cupped together as if holding something invisible, small birds perched on the fingertips, dramatic golden hour lighting and soft clouds",
        "banned_words": "marble,hands",
        "required_words": "ancient,calm",
    },
    {
        "label": "Lantern Whale Migration",
        "prompt": "A pod of ghostly humpback whales made of soft glowing paper lanterns swimming through a dark night sky above a quiet coastal town, their light reflecting on the ocean below, stars scattered above",
        "banned_words": "whale,lantern",
        "required_words": "ghostly,quiet",
    },
    {
        "label": "Cracked Teacup World",
        "prompt": "A tiny detailed fantasy island floating inside a cracked porcelain teacup, complete with miniature waterfalls pouring out through the crack, a small windmill and cottage on the island, steam rising like clouds",
        "banned_words": "teacup,island",
        "required_words": "tiny,fragile",
    },
    {
        "label": "Vinyl Record City",
        "prompt": "A miniature retro city built on top of a spinning black vinyl record, tiny illuminated skyscrapers following the record's grooves like streets, a giant record needle resting like a bridge, warm sunset color grading",
        "banned_words": "vinyl,record",
        "required_words": "spinning,miniature",
    },
    {
        "label": "Kite Whale Sky",
        "prompt": "A massive kite shaped like a koi fish flying high above a crowded beach at golden hour, its long fabric tail rippling in the wind, dozens of smaller colorful kites scattered across the sky, silhouetted people on the sand below",
        "banned_words": "kite,koi",
        "required_words": "soaring,golden",
    },
]
