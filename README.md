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
| Equipment | core's golem slots (head, torso, legs, hand = item types 26-29) plus **Golem Off-Hand** (type 29, replaces Left Hand). Kept: backpack, bag, belt, amulet, 2 rings, ammo. Every core golem part (Axe Hand, Armored Torso...) works too. |

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

## Rebuilding

`python tools/build_golem.py` regenerates everything (entities, pixel-art sheets, json) from the registry at the top. Needs Pillow and numpy. Art is drawn procedurally at 256px, area-downsampled to 32px, snapped to a small palette and outlined (the game's item style).

## Not verified in game (please check)

1. The `replace_entity` ritual: golem slots on the new body, and whether level/skills are kept (stats and level come from `Golem_Player`, see `build_ritual`).
2. A milestone granting a production action (`production_action` reward, `require_unlock: true`, same as Become Vampire) from a mod.
3. Race passives apply to the replaced body (vampires work this way); `restrict_tags` with the custom tag; negative `damage_type_reduction`; `regeneration` scale.
4. The Golem Off-Hand custom slot and `usable.ability` hands in the off-hand.
5. Ritual `animation`/`image` reuse the vampire ritual's.
