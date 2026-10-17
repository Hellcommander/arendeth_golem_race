# Golem Race (arendeth_golem_race) 0.3.0

Golems are built with **Construction**. There is no separate skill: at Construction level 10 you learn **Golem Assembly**, a ritual that turns you into a golem. It is a ritual race (like Arborborn and vampires), not a character-creator race, because race data cannot add equipment slots; an entity can, so the ritual swaps your body for a golem entity that carries them.

Requires `core_2`. Enable the mod before starting a world.

## Becoming a golem

1. Reach **Construction level 10**. The milestone **Golem Assembly** unlocks the ritual and the **Assembly Cradle** recipe (8 stone + 4 clay, no tools); **Clay Golem Frame** unlocks the clay parts and Repair Putty; **Field Repair** gives a self-heal.
2. Build the cradle and craft clay parts (clay is cheap).
3. Perform **Golem Assembly** at the cradle. Your body is replaced by `arendeth_golem_Golem_Player`.

## What a golem is

| | |
|---|---|
| Race passives | **Unliving Body** (no hunger/thirst, poison immune, +15% health), **Dense Frame** (10% slower, +40 carry, +15% strength/endurance, 25% weaker to acid), **Self-Repair Matrix** (slow regeneration) |
| Tags | alive, magic, mechanical (no fatigue, cannot be transformed), golem |
| Equipment | core's golem slots (head, torso, legs, hand = item types 26-29) plus **Golem Off-Hand** (type 29, replaces Left Hand). Kept: backpack, bag, belt, amulet, 2 rings, ammo, cape. Every core golem part (Axe Hand, Armored Torso...) works too. |

## Construction milestones added

| Level | Unlock |
|---|---|
| 10 | Golem Assembly ritual + Assembly Cradle, Clay frames + Repair Putty, Field Repair (heal 25-40) |
| 12 | Stone frames |
| 14 | Hardened Core (+10% health, 25% death resist; golems only) |
| 16 | Overclock (+25% attack speed, 6 turns) |
| 20 | Bronze frames |
| 22 | Rapid Repair (more regeneration; golems only) |
| 25 | Bulwark Stance (-30% damage, 8 turns) |
| 28 | Steel frames |

No stat bonuses are granted (Construction gains none on the milestone sheet). Every part's recipe has the maximum 5 magic slots (same as core's golem parts), so each can be upgraded with magic ingredients. All of it sits below core's level-41+ golem parts. Parts (original pixel art, 5 per tier: head, torso, legs, hand weapon, off-hand guard): Clay Head/Torso/Legs/Fist/Guard; Stone Head/Torso/Legs/Maul (Bash)/Slab (Shield Slam); Bronze Head/Torso/Legs/Cleaver (Whirlwind)/Bulwark; Steel Head/Torso/Legs/Hammer (Break)/Aegis. Heads give Willpower/Intelligence, torsos Endurance, legs Dexterity/Strength; armor stays under core's Armored Torso. Repair Putty (clay, no tools) is a stackable regeneration consumable.

Golem NPCs exist as the race's `base_entities` (adult, recruit, rebel, adventurer, foreman). The race has no settlement.

## Golem townies (population), unlocked by Construction milestones

Core already lets you craft golem companions (Construction 40), but they are not population. These are golem **townies**: persona entities like Astral Magic's `Civilized_*` ones, added to your settlement's population. Each Construction milestone grants a `craft_persona` passive (the same milestone -> passive -> craft_persona chain as Astral's Wisp/Elemental crafting); crafting the persona consumes the listed resource and adds the golem to your town. They work their trade, eat nothing (`core_2_disable_consumption`), keep normal hands for their tool and wear golem parts on head, torso and legs.

| Construction | Townie (occupation) | Consumes |
|---|---|---|
| 15 | **Golem Stonemason** | 20 clay |
| 20 | **Golem Miner** | 25 stone |
| 25 | **Golem Guard** | 8 bronze ingots |
| 30 | **Golem Smelter** | 10 iron ingots |
| 36 | **Golem Engineer** (construction + trap recipes) | 12 steel ingots |

## Construction capstones (unlockable recipes, levels 48-50)

Other crafting trees end on a unique item with a big active ability; Construction ended on slightly better golem parts. These are crafted at an anvil (5 magic slots) and unlocked as recipes by Construction milestones, the way Astral Magic unlocks its crafted items:

| Level | Item(s) | Active ability |
|---|---|---|
| 48 | **Mason's Mantle** (cape; adamantine + ancient cloth + leather) | **Collapse the Hall**: 3-tile ceiling collapse, 25-45 physical, stun and knockback, 25 turn cooldown |
| 49 | **Architect's Crown** (head; mithril + gems) / **Architect's Visage** (golem head; mithril + Golem's Heart) | **Raise the Citadel**: summon 3 Stone Sentinels (350 HP) for 40 turns, 90 turn cooldown |
| 50 | **Colossus Plate** (torso; adamantine + obsidian + gem) / **Colossus Heart-Plate** (golem torso; adamantine + 2 Golem's Hearts) | **Colossus Form**: become a 1400 HP stone titan (armor 10, ~64 strength, own Colossus Stomp) for 30 turns, 120 turn cooldown |

The head and torso come in a golem-slot variant (normal armor slots are disabled for golems); the cape works for everyone (golems keep the cape slot).

## Golem villagers (like necromancy's undead)

The golem race has a `settlement` block modelled on the skeleton/vampire/bone wraith races: `single_family`, `birth_cost` (40 stone-type resources per golem, e.g. clay or blocks, up to 100 population) and the tag option `ritual_birth`. Once you are a golem and control a settlement, golems can be created as villagers from the Settlement screen's "create beings" action, join your family, eat no settlement food (Unliving Body) and can serve as recruits. Golem Recruit, Rebel and Adventurer entities, name pools (settlements, states, surnames) and idle/fight barks (`dialogues.json`) exist for them. `start_spawn_rate` is 0 so worldgen never founds golem towns.

Limit: like skeletons, golem villagers are not mapped into the workplace occupations of core's buildings (`occupation_per_race` is per building, ~90 buildings), so they fill the population and military rather than jobs.
## Rebuilding

`python tools/build_golem.py` regenerates everything (entities, pixel-art sheets, json) from the registry at the top. Needs Pillow and numpy. Art is drawn procedurally at 256px, area-downsampled to 32px, snapped to a small palette and outlined (the game's item style).

## Not verified in game (please check)

1. The `replace_entity` ritual: golem slots on the new body, and whether level/skills are kept (stats and level come from `Golem_Player`, see `build_ritual`).
2. A milestone granting a production action (`production_action` reward, `require_unlock: true`, same as Become Vampire) from a mod.
3. Race passives apply to the replaced body (vampires work this way); `restrict_tags` with the custom tag; negative `damage_type_reduction`; `regeneration` scale.
4. The Golem Off-Hand custom slot and `usable.ability` hands in the off-hand.
5. Capstones: `transform` into `Colossus_Form` (same mechanism as Arborborn forms), `summon_count` 3 sentinels, armor items with `usable.ability` (core's Phasewalker pattern) and the balance of the numbers.
6. Golem townies: `craft_persona` with `third_value` (resource count) as in core's Skeleton/Bone Wraith crafting; workers using their tool from the right-hand slot.
7. Ritual `animation`/`image` reuse the vampire ritual's.
6. The settlement block (`center_id` 204 Golem's Tower, birth cost, `ritual_birth`): whether the Settlement screen offers creating golems and how many it creates.

## Credits

- **Design and direction:** Arendeth.
- **Implementation:** built with Claude (Anthropic) using the generator in `tools/`.
- **Art:** all sprites, icons and the thumbnail are original, drawn procedurally by `tools/golem_art.py`; no core_2 art is copied into this mod.
- **Soulash 2 and core_2:** Wizards of the Code. This mod reuses core_2's golem equipment slots (`core_2_golem_*`), the Construction skill, existing abilities (Bash, Whirlwind, Break, Shield Slam), the Golem Corpse, and the vampire ritual's animation, all by reference only.
- **Pattern reference:** the ritual (`replace_entity` at an altar) follows the Arborborn mod's Heartwood Altar and core's Become Vampire.
