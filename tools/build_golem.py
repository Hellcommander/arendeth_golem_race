"""Builds the Golem race mod: python tools/build_golem.py   (needs Pillow + numpy)

The golem is a RITUAL race, like Arborborn / vampires: at Construction level 10 you learn Golem Assembly, build an
Assembly Cradle and perform it, which swaps your body (`replace_entity`) for one that carries the golem equipment slots.
Race data cannot add equipment slots, so they live on the entity (`equipment.custom_slots`).

Everything below the REGISTRY block is generated; edit the registry and rebuild.
Idempotent: it rewrites entities/, abilities/, milestones/, npc/, assets/ and the top-level json.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import golem_art as A  # noqa: E402

P = "arendeth_golem_"
RACE = P + "Golem"
TAG = P + "tag"
SKILL = "core_2_construction"  # everything unlocks through core Construction milestones
CORE_SLOTS = {"head": "core_2_golem_head", "torso": "core_2_golem_torso", "legs": "core_2_golem_legs", "hand": "core_2_golem_hand"}
OFFHAND_SLOT = P + "offhand"
CELL = 32  # glyph / item / icon cell size (the game's own item sheets are 32px pixel art)
A.OW_MUL = 1.8

# ----------------------------------------------------------------------------- REGISTRY
STAT_KEYS = ("dexterity", "endurance", "intelligence", "strength", "willpower")
DMG_KEYS = ("acid", "death", "electricity", "fire", "frost", "holy", "parry", "physical", "poison", "thorns")

TIERS = {  # tier -> Construction level that unlocks the recipes, recipe tools, economy
    "Clay": dict(level=10, tools=[], value=800, minimap=(184, 112, 74), blurb="shaped by hand from wet clay"),
    "Stone": dict(level=12, tools=[6], value=2400, minimap=(132, 134, 142), blurb="hewn from quarried stone"),
    "Bronze": dict(level=20, tools=[1], value=6500, minimap=(186, 130, 56), blurb="cast and riveted from bronze"),
    "Steel": dict(level=28, tools=[1], value=13000, minimap=(124, 140, 166), blurb="forged and bolted from steel"),
}

# slot -> tier -> (name, armor, stat (key, amount), weight, time, recipe resources, recipe resource_types, weapon)
# weapon = (dmg_min, dmg_max, weapon_type, usable ability)
PARTS = {
    "head": {
        "Clay": ("Clay Head", dict(physical=1, fire=1), ("willpower", 1), 2.0, 30, [("2004", 2)], [], None),
        "Stone": ("Stone Head", dict(physical=3, frost=2, poison=2), ("willpower", 2), 3.0, 60, [], [(6, 3)], None),
        "Bronze": ("Bronze Head", dict(physical=4, fire=2, electricity=1), ("intelligence", 3), 2.5, 70, [("2114", 2)], [(2, 1)], None),
        "Steel": ("Steel Head", dict(physical=5, fire=3, electricity=2, frost=1), ("intelligence", 5), 2.5, 80, [("149", 3)], [(2, 1)], None),
    },
    "torso": {
        "Clay": ("Clay Torso", dict(physical=2, fire=2), ("endurance", 2), 6.0, 45, [("2004", 4)], [], None),
        "Stone": ("Stone Torso", dict(physical=5, frost=3, fire=2), ("endurance", 3), 9.0, 80, [], [(6, 6)], None),
        "Bronze": ("Bronze Torso", dict(physical=7, fire=3, frost=1), ("endurance", 4), 7.5, 90, [("2114", 4)], [(2, 1)], None),
        "Steel": ("Steel Torso", dict(physical=8, fire=4, frost=2, electricity=1), ("endurance", 6), 7.0, 100, [("149", 5)], [(2, 1)], None),
    },
    "legs": {
        "Clay": ("Clay Legs", dict(physical=1, fire=1), ("dexterity", 1), 4.0, 35, [("2004", 3)], [], None),
        "Stone": ("Stone Legs", dict(physical=3, frost=2), ("strength", 2), 6.0, 70, [], [(6, 4)], None),
        "Bronze": ("Bronze Legs", dict(physical=4, fire=1), ("dexterity", 3), 4.5, 80, [("2114", 3)], [(2, 1)], None),
        "Steel": ("Steel Legs", dict(physical=5, fire=2, electricity=1), ("dexterity", 5), 4.5, 90, [("149", 4)], [(2, 1)], None),
    },
    "hand": {
        "Clay": ("Clay Fist", dict(), None, 3.0, 35, [("2004", 2)], [], (2, 5, 6, None)),
        "Stone": ("Stone Maul", dict(), None, 5.0, 75, [], [(6, 4)], (4, 9, 2, "8")),
        "Bronze": ("Bronze Cleaver", dict(), None, 3.5, 80, [("2114", 3)], [(2, 1)], (6, 11, 0, "28")),
        "Steel": ("Steel Hammer", dict(), None, 4.5, 95, [("149", 4)], [(2, 1)], (8, 15, 2, "93")),
    },
    "guard": {
        "Clay": ("Clay Guard", dict(physical=1, parry=1), None, 3.0, 35, [("2004", 3)], [], (0, 2, 8, None)),
        "Stone": ("Stone Slab", dict(physical=3, parry=2, frost=1), None, 5.0, 70, [], [(6, 5)], (0, 3, 8, "36")),
        "Bronze": ("Bronze Bulwark", dict(physical=4, parry=3, fire=1), None, 4.0, 80, [("2114", 3)], [(2, 1)], (0, 3, 8, "36")),
        "Steel": ("Steel Aegis", dict(physical=5, parry=4, fire=2, electricity=1), None, 4.0, 90, [("149", 4)], [(2, 1)], (0, 4, 8, "36")),
    },
}
ITEM_TYPE = {"head": 26, "torso": 27, "legs": 28, "hand": 29, "guard": 29}
SLOT_BLURB = {"head": "A golem's head", "torso": "A golem's torso", "legs": "A pair of golem's legs", "hand": "A golem's hand",
              "guard": "A golem's hand shaped into a guard"}
EXTRA = {
    ("hand", "Clay"): "Heavy knuckles, no trick to it. Equip it in either hand slot.",
    ("hand", "Stone"): "Swings like a quarry hammer and can stun.",
    ("hand", "Bronze"): "Whirls about to hit everything around you.",
    ("hand", "Steel"): "A piston hammer that can also break down obstacles.",
    ("guard", "Clay"): "Little more than a thick palm held up in front of you.",
    ("guard", "Stone"): "Slam it into a foe to knock them back.",
    ("guard", "Bronze"): "A round plate that slams foes away.",
    ("guard", "Steel"): "A kite plate with a glowing seal. Slam it to knock foes back.",
}
SPRITE_TIER = {"adult": "Clay", "recruit": "Stone", "leader": "Steel", "adventurer": "Bronze", "rebel": "Stone"}

NPC_ROLES = {  # role -> (display name, occupation, level, health, weapon dmg, speed, stat ranges)
    "adult": ("Golem", "None", 1, 60, (2, 5), 1.0, dict(dexterity=(5, 8), endurance=(12, 16), intelligence=(6, 9), strength=(12, 16), willpower=(10, 14))),
    "recruit": ("Golem Recruit", "Recruit", 1, 160, (4, 9), 1.0, dict(dexterity=(10, 14), endurance=(18, 22), intelligence=(8, 11), strength=(24, 28), willpower=(14, 18))),
    "rebel": ("Golem Rebel", "Rebel", 2, 180, (4, 9), 1.0, dict(dexterity=(10, 14), endurance=(20, 26), intelligence=(8, 11), strength=(20, 24), willpower=(16, 22))),
    "adventurer": ("Golem Adventurer", "Adventuring", 1, 260, (6, 12), 1.0, dict(dexterity=(18, 22), endurance=(28, 34), intelligence=(12, 15), strength=(28, 32), willpower=(24, 28))),
    "leader": ("Golem Foreman", "Leader", 0, 600, (12, 22), 0.9, dict(dexterity=(24, 28), endurance=(55, 59), intelligence=(15, 19), strength=(58, 63), willpower=(41, 45))),
}

NAMES = """Adobe Alum Basalt Beryl Brick Brindle Cairn Chalk Cinder Clinker Cobble Corbel Cornice Dolmen Dross Flagstone
Flint Forge Furnace Gabbro Gneiss Gravel Grit Hearth Ingot Jasper Keystone Kiln Lintel Loam Lode Marl Mason Mortar
Obsidian Ochre Onyx Pavis Pestle Pillar Plinth Pumice Quarry Quartz Rampart Rivet Rubble Rune Sandstone Schist Shale
Slag Slate Sluice Smelt Sprocket Stele Tallow Tamp Tessera Tuff Umber Vault Wedge Whetstone""".split()

# slots: 0 backpack 1 head_armor 2 head_cloth 3 amulet 4 cape 5 ammo 6 torso_armor 7 torso_cloth 8 left_hand 9 right_hand
#        10 gloves 11 ring1 12 ring2 13 belt 14 legs_armor 15 legs_cloth 16 boots 17 second_right 18 second_left 19 bag
# Golems keep: backpack, amulet, ammo, rings, belt, bag. Head/torso/legs/both hands are golem part slots.
GOLEM_DISABLED = [1, 2, 4, 6, 7, 8, 9, 10, 14, 15, 16, 17, 18]

# ability icons (abilities sheet index), passive icons (passive_skills sheet index)
ABILITY_ICONS = ["wrench", "putty", "bolt", "shield"]
PASSIVE_ICONS = ["core", "block", "gearplus", "heartcore", "gear"]


# ----------------------------------------------------------------------------- helpers
def dump(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent="\t", sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def stat_block(key=None, amount=0):
    return {k: [amount if k == key else 0, amount if k == key else 0] for k in STAT_KEYS}


def armor_block(vals):
    return {k: vals.get(k, 0) for k in DMG_KEYS}


def glyph(index):
    return {"frames": [{"color": [255, 255, 255], "delay": 0, "index": index}], "random_frame_start": False}


def part_id(slot, tier):
    return P + PARTS[slot][tier][0].replace(" ", "_")


def sheet(tiles, cell, path):
    out = Image.new("RGBA", (cell * len(tiles), cell), (0, 0, 0, 0))
    for i, im in enumerate(tiles):
        out.alpha_composite(im, (i * cell, 0))
    path.parent.mkdir(parents=True, exist_ok=True)
    out.save(path)
    return len(tiles)


def px(img, *tiers, outline_tier=None):
    t = outline_tier or tiers[0]
    return A.pixelize(img, CELL, A.tier_palette(*tiers), outline=A.PAL[t]["dk"])


# ----------------------------------------------------------------------------- art sheets
def build_sprites():
    glyph_tiles, item_tiles, glyph_idx, item_idx = [], [], {}, {}

    def add(key, im, glyph_too=True):
        item_idx[key] = len(item_tiles)
        item_tiles.append(im)
        if glyph_too:
            glyph_idx[key] = len(glyph_tiles)
            glyph_tiles.append(im)

    for slot in PARTS:
        for tier in TIERS:
            add(part_id(slot, tier), px(A.part_icon(slot, tier), tier))
    add(P + "Repair_Putty", px(A.putty(), "Clay", "Steel", outline_tier="Clay"))
    for role, tier in SPRITE_TIER.items():
        glyph_idx[P + "Golem_" + role.capitalize()] = len(glyph_tiles)
        glyph_tiles.append(px(A.figure(role), tier, "Bronze", "Clay", outline_tier=tier))
    glyph_idx[P + "Golem_Player"] = glyph_idx[P + "Golem_Adult"]
    glyph_idx[P + "Assembly_Cradle"] = len(glyph_tiles)
    glyph_tiles.append(px(A.cradle(), "Stone", "Steel", "Clay", outline_tier="Stone"))

    ng = sheet(glyph_tiles, CELL, ROOT / "assets" / "glyphs.png")
    ni = sheet(item_tiles, CELL, ROOT / "assets" / "items.png")
    na = sheet([A.emblem(k, CELL) for k in ABILITY_ICONS], CELL, ROOT / "assets" / "abilities.png")
    npas = sheet([A.emblem(k, CELL) for k in PASSIVE_ICONS], CELL, ROOT / "assets" / "passive_skills.png")
    return glyph_idx, item_idx, dict(glyph32=ng, items=ni, abilities=na, passive_skills=npas)


# ----------------------------------------------------------------------------- entities
def build_parts(glyph_idx, item_idx):
    ids = {}
    for slot, by_tier in PARTS.items():
        for tier, (name, armor, stat, wt, time, res, rtypes, weapon) in by_tier.items():
            t = TIERS[tier]
            eid = part_id(slot, tier)
            ids[(slot, tier)] = eid
            comps = ["craftable", "glyph", "item", "minimap_pixel", "name", "position_2d", "value", "weight"]
            ent = {
                "craftable": {"backgrounds": [], "biomes": [], "magic_slots": 5,
                              "resource_types": [{"amount": a, "id": i} for i, a in rtypes],
                              "resources": [{"amount": a, "id": i} for i, a in res], "time": time, "tools": list(t["tools"])},
                "glyph": glyph(glyph_idx[eid]),
                "id": eid,
                "item": {"image": item_idx[eid], "type": ITEM_TYPE[slot]},
                "minimap_pixel": list(t["minimap"]),
                "name": name,
                "value": int(t["value"] * (1.1 if slot in ("hand", "guard") else 1.0)),
                "weight": wt,
            }
            desc = f"{SLOT_BLURB[slot]}, {t['blurb']}."
            if (slot, tier) in EXTRA:
                desc += " " + EXTRA[(slot, tier)]
            ent["description"] = desc
            if slot != "hand":
                comps.append("armor")
                ent["armor"] = armor_block(armor)
            if stat:
                comps.append("statistics")
                ent["statistics"] = stat_block(*stat)
            if weapon:
                lo, hi, wtype, ability = weapon
                comps.append("weapon")
                ent["weapon"] = {"attack_speed": 1.0, "critical_hit": 0.0, "damage": [{"dmg_max": hi, "dmg_min": lo, "dmg_type": "physical"}],
                                 "hands": 1, "hit_bonus": 0, "parry_bonus": 0, "range": 1, "type": wtype}
                if ability:
                    comps.append("usable")
                    ent["usable"] = {"ability": ability, "recipe": ""}
            ent["components"] = sorted(comps)
            dump(ROOT / "entities" / (eid[len(P):] + ".json"), ent)
    return ids


def build_items(glyph_idx, item_idx):
    putty = P + "Repair_Putty"
    dump(ROOT / "entities" / "Repair_Putty.json", {
        "components": ["craftable", "glyph", "item", "minimap_pixel", "name", "position_2d", "stackable", "usable", "value", "weight"],
        "craftable": {"magic_slots": 0, "resources": [{"amount": 1, "id": "2004"}], "time": 10, "tools": []},
        "description": "A pot of glowing, self-hardening putty. Slap it over a crack and it knits the damage shut over time.",
        "glyph": glyph(glyph_idx[putty]), "id": putty, "item": {"image": item_idx[putty], "type": 17},
        "minimap_pixel": [160, 170, 120], "name": "Repair Putty",
        "usable": {"ability": P + "Putty_Patch", "recipe": ""}, "value": 600, "weight": 0.3,
    })
    return putty


def npc_entity(role, eid, name, occ, lvl, hp, dmg, speed, stats, allies):
    comps = ["actor", "artificial_intelligence", "collidable", "equipment", "fighter", "glyph", "health", "humanoid", "minimap_pixel",
             "moveable", "name", "persona", "position_2d", "sight", "stamina", "statistics", "tags", "weapon"]
    ent = {
        "artificial_intelligence": {"allies": allies, "allow_production": [], "behaviors": [], "enemies": []},
        "corpse": "2747",
        "description": "A person of clay, stone and metal, assembled rather than born. Their parts can be swapped out.",
        "equipment": {"custom_slots": [CORE_SLOTS["hand"], CORE_SLOTS["head"], CORE_SLOTS["legs"], CORE_SLOTS["torso"], OFFHAND_SLOT],
                      "disabled_slots": GOLEM_DISABLED},
        "fighter": {"attackNames": ["Punch", "Slam"]},
        "health": hp, "humanoid": {"race": RACE}, "id": eid, "minimap_pixel": [149, 165, 101],
        "moveable": {"speed": speed}, "name": name, "persona": {"occupation": occ},
        "sight": {"ignore_infra_penalty": False, "infravision": False, "range": 10, "threesixty": False},
        "stamina": {"fatigue": 100, "stamina": 100, "stamina_regen": 0.0},
        "statistics": {k: list(v) for k, v in stats.items()},
        "tags": ["9", "3", "32", TAG],
        "weapon": {"attack_speed": 1.0, "critical_hit": 0.0, "damage": [{"dmg_max": dmg[1], "dmg_min": dmg[0], "dmg_type": "physical"}],
                   "hands": 1, "hit_bonus": 0, "parry_bonus": 0, "range": 1, "type": 6},
    }
    if lvl:
        comps.append("experience_gainer")
        ent["experience_gainer"] = {"exp": 5 * lvl, "level": lvl}
    ent["components"] = comps
    return ent


def build_npcs(glyph_idx):
    out = {}
    dialogues = {"adventurer": ["1043"], "rebel": ["987"], "recruit": ["550", "551"]}
    for role, (name, occ, lvl, hp, dmg, speed, stats) in NPC_ROLES.items():
        eid = P + "Golem_" + role.capitalize()
        ent = npc_entity(role, eid, name, occ, lvl, hp, dmg, speed, stats, [] if role == "adventurer" else [TAG])
        ent["glyph"] = glyph(glyph_idx[eid])
        if role in dialogues:
            ent["components"].append("dialogues")
            ent["dialogues"] = dialogues[role]
        ent["components"] = sorted(ent["components"])
        dump(ROOT / "entities" / (eid[len(P):] + ".json"), ent)
        out[role] = eid
    return out


def build_ritual(glyph_idx):
    body = P + "Golem_Player"
    ent = npc_entity("player", body, "Golem", "None", 1, 120, (2, 5), 1.0,
                     dict(dexterity=(10, 14), endurance=(16, 20), intelligence=(10, 14), strength=(16, 20), willpower=(12, 16)), ["5"])
    ent["glyph"] = glyph(glyph_idx[body])
    ent["components"] = sorted(set(ent["components"]) | {"dialogues"})
    ent["dialogues"] = []
    ent["experience_gainer"] = {"exp": 0, "level": 1}
    if "experience_gainer" not in ent["components"]:
        ent["components"] = sorted(ent["components"] + ["experience_gainer"])
    dump(ROOT / "entities" / "Golem_Player.json", ent)
    cradle = P + "Assembly_Cradle"
    dump(ROOT / "entities" / "Assembly_Cradle.json", {
        "category_id": 6,
        "components": ["collidable", "craftable", "glyph", "height", "minimap_pixel", "name", "position_2d", "producer"],
        "craftable": {"backgrounds": [], "biomes": [], "magic_slots": 0, "resource_types": [{"amount": 8, "id": 6}],
                      "resources": [{"amount": 4, "id": "2004"}], "time": 120, "tools": []},
        "description": ("A stone cradle with iron clamps and an empty heart socket, built from stone and clay. Perform the Golem Assembly "
                        "ritual here to leave your flesh behind and be rebuilt as a golem. Unlocked by Construction level 10."),
        "glyph": glyph(glyph_idx[cradle]), "height": 0, "id": cradle, "minimap_pixel": [132, 134, 142], "name": "Assembly Cradle",
        "producer": {"products": {P + "become_golem": [{"amount": [0, 0], "id": "", "percent_chance": 0}]}, "time": 60},
    })
    return {
        "animation": "core_2_Become_Vampire", "askey": -1,
        "description": ("Become a Golem: leave your flesh behind and be assembled anew. You gain golem part slots (head, torso, legs, both "
                        "hands), never hunger or tire, and keep your skills. This cannot be undone.\n\nLearned at Construction level 10. "
                        "It may only be used at an Assembly Cradle."),
        "force_single_item": True, "id": P + "become_golem", "image": 92, "key": "", "name": "Golem Assembly",
        "required_tool": -1, "require_unlock": True, "restrict_default": True,
        "sound": "data/mods/core_2/assets/sfx/inventory/drop_other_1.ogg",
        "time_statistic_multiplier": 0.1, "time_statistic_scale": 4, "time_weight_scale": 0, "replace_entity": body,
    }


# ----------------------------------------------------------------------------- data files
def build_json(part_ids, putty_id, npc_ids, ritual_action):
    race = {
        "ages": {"adult": 25, "child": 0, "elder": 500},
        "base_entities": {"adult": npc_ids["adult"], "child": npc_ids["adult"], "leader": npc_ids["leader"],
                          "recruit": npc_ids["recruit"], "rebel": npc_ids["rebel"], "adventurer": npc_ids["adventurer"]},
        "description": ("Golems are made, not born: people of clay, stone and metal, woken by a heart and a name. They never hunger, thirst or "
                        "tire, shrug off poison and wear no clothes. Their head, torso, legs and both hands are swappable golem parts."),
        "id": RACE, "image": 46, "items": [], "name": "Golem",
        "names": {"female": "npc/names/golem_female.txt", "male": "npc/names/golem_male.txt"},
        "orphan_surname": "of the Foundry",
        "passives": [P + "unliving_body", P + "dense_frame", P + "self_repair_matrix"],
        "playable": False, "recipes": [],
        "statistics": {"endurance": 3, "strength": 2, "willpower": 1},
        "tags": ["9", "3", "32", TAG],
    }
    dump(ROOT / "character.json", {
        "custom_eq_slots": [{"icon": 23, "id": OFFHAND_SLOT, "item_types": [29], "name": "Golem Off-Hand", "replace": "left_hand"}],
        "production_actions": [ritual_action],
        "races": [race],
        "tags": [{"id": TAG, "name": "golem", "options": []}],
    })

    only = [TAG]
    passives = [
        {"id": P + "unliving_body", "name": "Unliving Body", "image": 0,
         "effects": [{"effect": "disable_consumer"}, {"effect": "immunity", "value": "poison_effect"}, {"effect": "health_bonus_percent", "value": 0.15}]},
        {"id": P + "dense_frame", "name": "Dense Frame", "image": 1,
         "effects": [{"effect": "move_speed", "value": 0.1}, {"effect": "carry_capacity", "value": 40},
                     {"effect": "statistic_percent", "value": "strength", "secondary_value": 0.15},
                     {"effect": "statistic_percent", "value": "endurance", "secondary_value": 0.15},
                     {"effect": "damage_type_reduction", "value": "acid", "secondary_value": -0.25}]},
        {"id": P + "self_repair_matrix", "name": "Self-Repair Matrix", "image": 2,
         "effects": [{"effect": "regeneration", "value": 0.5}]},
        {"id": P + "hardened_core", "name": "Hardened Core", "image": 3, "restrict_tags": only,
         "effects": [{"effect": "health_bonus_percent", "value": 0.1}, {"effect": "damage_type_reduction", "value": "death", "secondary_value": 0.25}]},
        {"id": P + "rapid_repair", "name": "Rapid Repair", "image": 4, "restrict_tags": only,
         "effects": [{"effect": "regeneration", "value": 0.5}, {"effect": "health_tick", "value": 0.33}]},
    ]
    dump(ROOT / "passives.json", passives)

    abilities = {
        "Field_Repair": {"animation": "core_2_Better_bandage", "cast_time": 1.0, "cooldown": 30.0, "cost": {"health": 0, "stamina": 20},
                         "description": "Patch your cracks with whatever you can reach. Restore ::heal health.", "duration": 0.0,
                         "effects": {"heal": [25, 40]}, "id": P + "Field_Repair", "image": 0, "name": "Field Repair", "range": 0,
                         "skill": SKILL, "slots": {"utility": 2}, "target": "self"},
        "Putty_Patch": {"animation": "core_2_Better_bandage", "cast_time": 1.0, "cooldown": 0.0, "cost": {"health": 0, "stamina": 0},
                        "description": "Repair putty hardens over your wounds, restoring ::regeneration health periodically for ::duration turns.",
                        "duration": 100.0, "effects": {"regeneration": 6.0}, "id": P + "Putty_Patch", "image": 1, "name": "Putty Patch",
                        "range": 0, "skill": "", "target": "self"},
        "Overclock": {"animation": "core_2_Frenzy", "cast_time": 0.2, "cooldown": 30.0, "cost": {"health": 0, "stamina": 25},
                      "description": "Run your joints hot, increasing your attack speed by ::attack_speed for ::duration turns.", "duration": 6.0,
                      "effects": {"attack_speed": -0.25}, "id": P + "Overclock", "image": 2, "name": "Overclock", "range": 0,
                      "skill": SKILL, "slots": {"offensive": 2, "utility": 1}, "target": "self"},
        "Bulwark_Stance": {"animation": "core_2_Better_bandage", "cast_time": 0.2, "cooldown": 40.0, "cost": {"health": 0, "stamina": 20},
                           "description": "Plant your feet and harden your plating, reducing damage you take by ::damage_reduce_percent% for ::duration turns.",
                           "duration": 8.0, "effects": {"damage_reduce_percent": 0.3}, "id": P + "Bulwark_Stance", "image": 3,
                           "name": "Bulwark Stance", "range": 0, "skill": SKILL, "slots": {"defensive": 2, "utility": 1}, "target": "self"},
    }
    for k, v in abilities.items():
        dump(ROOT / "abilities" / f"{k}.json", v)

    def ms(name, key, level, rewards):
        dump(ROOT / "milestones" / "construction" / f"{level:02d}_Golem_{key}.json", {
            "id": P + key, "name": name, "requirements": {"milestones": [], "skill": level}, "rewards": rewards,
            "skill_id": SKILL, "steps": [], "steps_type": 0})

    def recipes(tier):
        return [{"recipe": part_ids[(s, tier)]} for s in PARTS]

    ms("Golem Assembly", "assembly", 10, [{"production_action": P + "become_golem"}, {"recipe": P + "Assembly_Cradle"}])
    ms("Clay Golem Frame", "clay_frame", 10, recipes("Clay") + [{"recipe": putty_id}])
    ms("Field Repair", "field_repair", 10, [{"ability": P + "Field_Repair"}])
    ms("Stone Golem Frame", "stone_frame", 12, recipes("Stone"))
    ms("Hardened Core", "hardened_core", 14, [{"passive": P + "hardened_core"}])
    ms("Overclock", "overclock", 16, [{"ability": P + "Overclock"}])
    ms("Bronze Golem Frame", "bronze_frame", 20, recipes("Bronze"))
    ms("Rapid Repair", "rapid_repair", 22, [{"passive": P + "rapid_repair"}])
    ms("Bulwark Stance", "bulwark_stance", 25, [{"ability": P + "Bulwark_Stance"}])
    ms("Steel Golem Frame", "steel_frame", 28, recipes("Steel"))

    (ROOT / "npc" / "names").mkdir(parents=True, exist_ok=True)
    for gender in ("male", "female"):
        (ROOT / "npc" / "names" / f"golem_{gender}.txt").write_text("\n".join(NAMES) + "\n", encoding="utf-8")


def build_assets_json(counts):
    tiles = [("abilities", [counts["abilities"], 1], "assets/abilities.png"),
             ("passive_skills", [counts["passive_skills"], 1], "assets/passive_skills.png"),
             ("glyph32", [counts["glyph32"], 1], "assets/glyphs.png"), ("items", [counts["items"], 1], "assets/items.png")]
    dump(ROOT / "assets.json", {"graphics": {"tilesheets": [{"name": n, "tiles": t, "file": f} for n, t, f in tiles]}})


def build_branding():
    font_path = Path(r"C:\Windows\Fonts\georgiab.ttf")

    def font(size):
        try:
            return ImageFont.truetype(str(font_path), size)
        except Exception:
            return ImageFont.load_default()

    def backdrop(w, h):
        img = Image.new("RGBA", (w, h), (24, 26, 34, 255))
        d = ImageDraw.Draw(img)
        for y in range(h):
            k = y / h
            d.line((0, y, w, y), fill=(int(40 - 16 * k), int(34 - 12 * k), int(36 - 8 * k), 255))
        return img

    def big(role, scale):
        return px(A.figure(role), SPRITE_TIER[role], "Bronze", "Clay").resize((CELL * scale, CELL * scale), Image.NEAREST)

    icon = backdrop(256, 256)
    icon.alpha_composite(big("leader", 7), (16, 16))
    icon.convert("RGB").save(ROOT / "icon.png")
    th = backdrop(800, 600)
    d = ImageDraw.Draw(th)
    for i, role in enumerate(("adult", "recruit", "adventurer")):
        th.alpha_composite(big(role, 8), (30 + i * 260, 190))
    for i, tier in enumerate(("Clay", "Stone", "Bronze", "Steel")):
        th.alpha_composite(px(A.part_icon("head", tier), tier).resize((96, 96), Image.NEAREST), (70 + i * 175, 470))
    d.text((400, 80), "GOLEM RACE", font=font(84), fill=(236, 216, 168, 255), anchor="mm")
    d.text((400, 140), "Construction 10: become the construct", font=font(26), fill=(176, 186, 198, 255), anchor="mm")
    th.convert("RGB").save(ROOT / "thumbnail.png")


def main():
    for sub in ("entities", "abilities", "milestones", "portraits", "npc", "assets"):
        shutil.rmtree(ROOT / sub, ignore_errors=True)
    glyph_idx, item_idx, counts = build_sprites()
    part_ids = build_parts(glyph_idx, item_idx)
    putty_id = build_items(glyph_idx, item_idx)
    npc_ids = build_npcs(glyph_idx)
    ritual = build_ritual(glyph_idx)
    build_json(part_ids, putty_id, npc_ids, ritual)
    build_assets_json(counts)
    build_branding()
    dump(ROOT / "mod.json", {
        "author": "Arendeth",
        "description": ("Golem Race: at Construction level 10 learn Golem Assembly, build an Assembly Cradle and perform it to become a golem. Golems never hunger, "
                        "thirst or tire, wear no clothes, and use swappable golem parts (clay, stone, bronze, steel) in the head, torso, legs "
                        "and both hand slots. Credits: Arendeth (design); built with Claude (Anthropic); Soulash 2 and core_2 by Wizards of the Code."),
        "game_required": "0.10.0", "icon": "icon.png", "mods_required": ["core_2"], "name": "Golem Race",
        "thumbnail": "thumbnail.png", "version": "0.3.0",
    })
    print(counts, "parts", len(part_ids))


if __name__ == "__main__":
    main()
