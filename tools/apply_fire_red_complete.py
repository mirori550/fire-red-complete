#!/usr/bin/env python3
"""Apply the large, mechanical FireRed Complete source edits.

The script is intentionally idempotent.  Small map changes that are clearer as
normal source edits live directly in the repository; this file handles the
large/repetitive edits (Oak's Lab, all rival parties, and paired FR/LG wild
encounter tables) without replacing thousands of vanilla lines by hand.
"""

from __future__ import annotations

import copy
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    p = ROOT / path
    if p.read_text(encoding="utf-8") != text:
        p.write_text(text, encoding="utf-8")


def replace_required(text: str, old: str, new: str, name: str) -> str:
    if new in text:
        return text
    if old not in text:
        raise RuntimeError(f"Could not find expected {name} source text")
    return text.replace(old, new, 1)


def patch_oaks_lab() -> None:
    path = "data/maps/PalletTown_ProfessorOaksLab/scripts.inc"
    text = read(path)

    # No matter which ball the player chooses, Blue's starter is Pikachu.
    text = text.replace(
        "\tsetvar RIVAL_STARTER_SPECIES, SPECIES_CHARMANDER\n",
        "\tsetvar RIVAL_STARTER_SPECIES, SPECIES_PIKACHU\n",
    )
    text = text.replace(
        "\tsetvar RIVAL_STARTER_SPECIES, SPECIES_BULBASAUR\n",
        "\tsetvar RIVAL_STARTER_SPECIES, SPECIES_PIKACHU\n",
    )
    text = text.replace(
        "\tsetvar RIVAL_STARTER_SPECIES, SPECIES_SQUIRTLE\n",
        "\tsetvar RIVAL_STARTER_SPECIES, SPECIES_PIKACHU\n",
    )

    old_remove = "\thidemonpic\n\tremoveobject VAR_LAST_TALKED\n\tmsgbox PalletTown_ProfessorOaksLab_Text_OakThisMonIsEnergetic\n"
    new_remove = (
        "\thidemonpic\n"
        "\tremoveobject LOCALID_BULBASAUR_BALL\n"
        "\tremoveobject LOCALID_SQUIRTLE_BALL\n"
        "\tremoveobject LOCALID_CHARMANDER_BALL\n"
        "\tsetflag FLAG_HIDE_BULBASAUR_BALL\n"
        "\tsetflag FLAG_HIDE_SQUIRTLE_BALL\n"
        "\tsetflag FLAG_HIDE_CHARMANDER_BALL\n"
        "\tmsgbox PalletTown_ProfessorOaksLab_Text_OakThisMonIsEnergetic\n"
    )
    text = replace_required(text, old_remove, new_remove, "starter-ball removal")

    old_give = "\tgivemon PLAYER_STARTER_SPECIES, 5\n\tcopyvar VAR_STARTER_MON, PLAYER_STARTER_NUM\n"
    new_give = (
        "\tgivemon PLAYER_STARTER_SPECIES, 5\n"
        "\tcall_if_eq PLAYER_STARTER_NUM, 0, FireRedComplete_EventScript_GiveOtherStartersBulbasaur\n"
        "\tcall_if_eq PLAYER_STARTER_NUM, 1, FireRedComplete_EventScript_GiveOtherStartersSquirtle\n"
        "\tcall_if_eq PLAYER_STARTER_NUM, 2, FireRedComplete_EventScript_GiveOtherStartersCharmander\n"
        "\tcopyvar VAR_STARTER_MON, PLAYER_STARTER_NUM\n"
    )
    text = replace_required(text, old_give, new_give, "three-starter gift")

    # Replace the vanilla 'walk to the counter-pick ball' sequence with Oak
    # explaining that all three balls are empty and giving Blue Pikachu.
    rival_pick_pattern = re.compile(
        r"PalletTown_ProfessorOaksLab_EventScript_RivalPicksStarter::\n.*?"
        r"(?=\nPalletTown_ProfessorOaksLab_EventScript_RivalWalksToCharmander::)",
        re.S,
    )
    new_rival_pick = """PalletTown_ProfessorOaksLab_EventScript_RivalPicksStarter::
\tclosemessage
\ttextcolor NPC_TEXT_COLOR_MALE
\tmsgbox PalletTown_ProfessorOaksLab_Text_OakNoPokemonLeftExceptPikachu
\ttextcolor NPC_TEXT_COLOR_NEUTRAL
\tsetvar RIVAL_STARTER_SPECIES, SPECIES_PIKACHU
\tbufferspeciesname STR_VAR_1, RIVAL_STARTER_SPECIES
\tmessage PalletTown_ProfessorOaksLab_Text_RivalReceivedMonFromOak
\twaitmessage
\tplayfanfare MUS_OBTAIN_KEY_ITEM
\twaitfanfare
\tsetvar VAR_MAP_SCENE_PALLET_TOWN_PROFESSOR_OAKS_LAB, 3
\tcall_if_set FLAG_OPENED_START_MENU, PalletTown_ProfessorOaksLab_EventScript_ReadyEndSignLadyScene
\trelease
\tend
"""
    if "PalletTown_ProfessorOaksLab_Text_OakNoPokemonLeftExceptPikachu" not in text:
        text, count = rival_pick_pattern.subn(new_rival_pick.rstrip("\n"), text, count=1)
        if count != 1:
            raise RuntimeError("Could not replace rival starter-pick scene")

    helpers = """

@ FireRed Complete: the chosen Pokémon is still the player's main starter,
@ but Oak also gives the other two so the Kanto Pokédex is solo-completable.
FireRedComplete_EventScript_GiveOtherStartersBulbasaur::
\tgivemon SPECIES_CHARMANDER, 5
\tgivemon SPECIES_SQUIRTLE, 5
\treturn

FireRedComplete_EventScript_GiveOtherStartersSquirtle::
\tgivemon SPECIES_BULBASAUR, 5
\tgivemon SPECIES_CHARMANDER, 5
\treturn

FireRedComplete_EventScript_GiveOtherStartersCharmander::
\tgivemon SPECIES_BULBASAUR, 5
\tgivemon SPECIES_SQUIRTLE, 5
\treturn
"""
    if "FireRedComplete_EventScript_GiveOtherStartersBulbasaur::" not in text:
        text += helpers

    write(path, text)

    text_path = "data/maps/PalletTown_ProfessorOaksLab/text.inc"
    text_data = read(text_path)
    dialogue = """

PalletTown_ProfessorOaksLab_Text_OakNoPokemonLeftExceptPikachu::
    .string "OAK: {RIVAL}, I have no POKéMON\\n"
    .string "left, except for this ELECTRIC-type\\n"
    .string "POKéMON named PIKACHU.$"
"""
    if "PalletTown_ProfessorOaksLab_Text_OakNoPokemonLeftExceptPikachu::" not in text_data:
        text_data += dialogue
    write(text_path, text_data)


STARTER_FAMILIES = {
    "BULBASAUR", "IVYSAUR", "VENUSAUR",
    "CHARMANDER", "CHARMELEON", "CHARIZARD",
    "SQUIRTLE", "WARTORTLE", "BLASTOISE",
}


def patch_rival_parties() -> None:
    path = "src/data/trainer_parties.h"
    text = read(path)

    party_re = re.compile(
        r"(static const struct [^\n]+ sParty_Rival[A-Za-z0-9_]*\[\] = \{\n)(.*?)(\n\};)",
        re.S,
    )
    mon_re = re.compile(
        r"(?P<prefix>\.lvl\s*=\s*(?P<level>\d+),\s*\n\s*\.species\s*=\s*)"
        r"SPECIES_(?P<species>[A-Z0-9_]+)"
    )

    changed_parties = 0

    def patch_party(match: re.Match[str]) -> str:
        nonlocal changed_parties
        body = match.group(2)

        def patch_mon(mon: re.Match[str]) -> str:
            species = mon.group("species")
            if species not in STARTER_FAMILIES:
                return mon.group(0)
            level = int(mon.group("level"))
            replacement = "RAICHU" if level >= 40 else "PIKACHU"
            return mon.group("prefix") + "SPECIES_" + replacement

        new_body = mon_re.sub(patch_mon, body)
        if new_body != body:
            changed_parties += 1
        return match.group(1) + new_body + match.group(3)

    text = party_re.sub(patch_party, text)
    if changed_parties == 0 and "sParty_RivalOaksLabBulbasaur" in text:
        # Idempotent reruns are allowed; make sure a known party is already patched.
        known = re.search(
            r"sParty_RivalOaksLabBulbasaur\[\].*?SPECIES_PIKACHU",
            text,
            re.S,
        )
        if not known:
            raise RuntimeError("No rival starter party entries were patched")
    write(path, text)


def patch_rival_moves() -> None:
    path = "src/battle_main.c"
    text = read(path)
    helper_name = "ApplyFireRedCompleteRivalMoves"

    if f"static void {helper_name}(" not in text:
        marker = "\nstatic u8 CreateNPCTrainerParty(struct Pokemon *party, u16 trainerNum)\n{"
        if marker not in text:
            raise RuntimeError("Could not find CreateNPCTrainerParty definition")
        helper = r'''
static void ApplyFireRedCompleteRivalMoves(struct Pokemon *party, u16 trainerNum)
{
    u8 i;
    u8 trainerPic = gTrainers[trainerNum].trainerPic;

    if (trainerPic != TRAINER_PIC_RIVAL_EARLY
     && trainerPic != TRAINER_PIC_RIVAL_LATE
     && trainerPic != TRAINER_PIC_CHAMPION_RIVAL)
        return;

    for (i = 0; i < gTrainers[trainerNum].partySize; i++)
    {
        u16 species = GetMonData(&party[i], MON_DATA_SPECIES);
        u8 level = GetMonData(&party[i], MON_DATA_LEVEL);
        u16 moves[MAX_MON_MOVES] = {MOVE_NONE, MOVE_NONE, MOVE_NONE, MOVE_NONE};
        u8 j;

        if (species != SPECIES_PIKACHU && species != SPECIES_RAICHU)
            continue;

        if (level <= 5)
        {
            moves[0] = MOVE_GROWL;
            moves[1] = MOVE_THUNDER_SHOCK;
        }
        else if (level <= 9)
        {
            moves[0] = MOVE_GROWL;
            moves[1] = MOVE_TAIL_WHIP;
            moves[2] = MOVE_THUNDER_SHOCK;
        }
        else if (level <= 18)
        {
            moves[0] = MOVE_THUNDER_SHOCK;
            moves[1] = MOVE_THUNDER_WAVE;
            moves[2] = MOVE_TAIL_WHIP;
            moves[3] = MOVE_QUICK_ATTACK;
        }
        else if (level <= 25)
        {
            moves[0] = MOVE_THUNDER_SHOCK;
            moves[1] = MOVE_THUNDER_WAVE;
            moves[2] = MOVE_SLAM;
            moves[3] = MOVE_DOUBLE_TEAM;
        }
        else if (level <= 40)
        {
            moves[0] = MOVE_THUNDERBOLT;
            moves[1] = MOVE_AGILITY;
            moves[2] = MOVE_SLAM;
            moves[3] = MOVE_DOUBLE_TEAM;
        }
        else if (level <= 53)
        {
            moves[0] = MOVE_THUNDERBOLT;
            moves[1] = MOVE_AGILITY;
            moves[2] = MOVE_IRON_TAIL;
            moves[3] = MOVE_FOCUS_PUNCH;
        }
        else
        {
            moves[0] = MOVE_THUNDER;
            moves[1] = MOVE_AGILITY;
            moves[2] = MOVE_IRON_TAIL;
            moves[3] = MOVE_FOCUS_PUNCH;
        }

        for (j = 0; j < MAX_MON_MOVES; j++)
            SetMonMoveSlot(&party[i], moves[j], j);
    }
}
'''
        text = text.replace(marker, "\n" + helper + marker.lstrip("\n"), 1)

    call = "    ApplyFireRedCompleteRivalMoves(party, trainerNum);\n\n"
    if call not in text:
        old = "        gBattleTypeFlags |= gTrainers[trainerNum].doubleBattle;\n    }\n\n    return gTrainers[trainerNum].partySize;\n}"
        new = "        gBattleTypeFlags |= gTrainers[trainerNum].doubleBattle;\n    }\n\n" + call + "    return gTrainers[trainerNum].partySize;\n}"
        if old not in text:
            raise RuntimeError("Could not find end of CreateNPCTrainerParty")
        text = text.replace(old, new, 1)

    write(path, text)


LG_KANTO_EXCLUSIVES = {
    "SPECIES_SANDSHREW", "SPECIES_SANDSLASH",
    "SPECIES_VULPIX", "SPECIES_NINETALES",
    "SPECIES_BELLSPROUT", "SPECIES_WEEPINBELL", "SPECIES_VICTREEBEL",
    "SPECIES_SLOWPOKE", "SPECIES_SLOWBRO",
    "SPECIES_STARYU", "SPECIES_STARMIE",
    "SPECIES_PINSIR", "SPECIES_MAGMAR",
}

FR_KANTO_EXCLUSIVES = {
    "SPECIES_EKANS", "SPECIES_ARBOK",
    "SPECIES_ODDISH", "SPECIES_GLOOM", "SPECIES_VILEPLUME",
    "SPECIES_PSYDUCK", "SPECIES_GOLDUCK",
    "SPECIES_GROWLITHE", "SPECIES_ARCANINE",
    "SPECIES_SHELLDER", "SPECIES_CLOYSTER",
    "SPECIES_SCYTHER", "SPECIES_ELECTABUZZ",
}

ENCOUNTER_FIELDS = ("land_mons", "water_mons", "rock_smash_mons", "fishing_mons")


def merge_leafgreen_exclusives() -> None:
    path = ROOT / "src/data/wild_encounters.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    changed = False

    for group in data["wild_encounter_groups"]:
        encounters = group.get("encounters")
        if not encounters:
            continue

        by_map: dict[str, dict[str, dict]] = {}
        for encounter in encounters:
            label = encounter.get("base_label", "")
            if label.endswith("_FireRed"):
                version = "fr"
            elif label.endswith("_LeafGreen"):
                version = "lg"
            else:
                continue
            by_map.setdefault(encounter["map"], {})[version] = encounter

        for pair in by_map.values():
            if "fr" not in pair or "lg" not in pair:
                continue
            fr = pair["fr"]
            lg = pair["lg"]

            for field in ENCOUNTER_FIELDS:
                if field not in lg:
                    continue
                if field not in fr:
                    fr[field] = copy.deepcopy(lg[field])
                    changed = True
                    continue

                fr_mons = fr[field].get("mons", [])
                lg_mons = lg[field].get("mons", [])
                if not fr_mons or not lg_mons:
                    continue

                wanted = []
                for mon in lg_mons:
                    species = mon["species"]
                    if species in LG_KANTO_EXCLUSIVES and species not in wanted:
                        wanted.append(species)

                present = {mon["species"] for mon in fr_mons}
                for species in wanted:
                    if species in present:
                        continue
                    lg_mon = next(mon for mon in lg_mons if mon["species"] == species)
                    counts = Counter(mon["species"] for mon in fr_mons)

                    candidate = None
                    # Prefer a low-probability duplicate slot, preserving every
                    # existing FireRed-exclusive species in the map.
                    for idx in range(len(fr_mons) - 1, -1, -1):
                        current = fr_mons[idx]["species"]
                        if current in FR_KANTO_EXCLUSIVES:
                            continue
                        if counts[current] > 1:
                            candidate = idx
                            break
                    if candidate is None:
                        for idx in range(len(fr_mons) - 1, -1, -1):
                            if fr_mons[idx]["species"] not in FR_KANTO_EXCLUSIVES:
                                candidate = idx
                                break
                    if candidate is None:
                        raise RuntimeError(
                            f"No safe encounter slot for {species} in {fr['map']} {field}"
                        )

                    fr_mons[candidate] = copy.deepcopy(lg_mon)
                    present.add(species)
                    changed = True

    if changed:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    patch_oaks_lab()
    patch_rival_parties()
    patch_rival_moves()
    merge_leafgreen_exclusives()
    print("FireRed Complete source transformations applied.")


if __name__ == "__main__":
    main()
