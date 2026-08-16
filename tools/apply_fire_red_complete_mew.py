#!/usr/bin/env python3
"""Apply FireRed Complete's fixed Kanto Mew event and remove beast roaming."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    p = ROOT / path
    if p.read_text(encoding="utf-8") != text:
        p.write_text(text, encoding="utf-8")


def add_hidden_lab_to_map_groups() -> None:
    path = ROOT / "data/maps/map_groups.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    dungeons = data["gMapGroup_Dungeons"]
    if "PokemonMansion_HiddenLab" not in dungeons:
        idx = dungeons.index("PokemonMansion_B1F") + 1
        dungeons.insert(idx, "PokemonMansion_HiddenLab")
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def include_hidden_lab_scripts_and_text() -> None:
    path = "data/event_scripts.s"
    text = read(path)

    script_include = '\t.include "data/maps/PokemonMansion_HiddenLab/scripts.inc"\n'
    if script_include not in text:
        marker = '\t.include "data/maps/PokemonMansion_B1F/scripts.inc"\n'
        if marker not in text:
            raise RuntimeError("Could not find Pokémon Mansion script include")
        text = text.replace(marker, marker + script_include, 1)

    text_include = '\t.include "data/maps/PokemonMansion_HiddenLab/text.inc"\n'
    if text_include not in text:
        marker = '\t.include "data/maps/PokemonMansion_B1F/text.inc"\n'
        if marker not in text:
            # Some source revisions order Mansion text separately.  Insert next
            # to another guaranteed Cinnabar indoor text include instead.
            marker = '\t.include "data/maps/CinnabarIsland_PokemonLab_ExperimentRoom/text.inc"\n'
        if marker not in text:
            raise RuntimeError("Could not find a location for hidden-lab text include")
        text = text.replace(marker, marker + text_include, 1)

    write(path, text)


def patch_mansion_diary_entry() -> None:
    path = "data/maps/PokemonMansion_B1F/scripts.inc"
    text = read(path)
    old = """PokemonMansion_B1F_EventScript_DiarySep1st::
\tmsgbox PokemonMansion_B1F_Text_MewtwoIsFarTooPowerful, MSGBOX_SIGN
\tend
"""
    new = """PokemonMansion_B1F_EventScript_DiarySep1st::
\tgoto_if_set FLAG_SYS_GAME_CLEAR, FireRedComplete_PokemonMansion_EventScript_OpenHiddenLab
\tmsgbox PokemonMansion_B1F_Text_MewtwoIsFarTooPowerful, MSGBOX_SIGN
\tend

FireRedComplete_PokemonMansion_EventScript_OpenHiddenLab::
\tlockall
\tmsgbox FireRedComplete_PokemonMansion_Text_HiddenLabDiary
\tclosemessage
\tplayse SE_UNLOCK
\twaitse
\tdelay 20
\twarp MAP_POKEMON_MANSION_HIDDEN_LAB, 7, 8
\twaitstate
\treleaseall
\tend
"""
    if "FireRedComplete_PokemonMansion_EventScript_OpenHiddenLab" not in text:
        if old not in text:
            raise RuntimeError("Could not hook postgame Mansion diary")
        text = text.replace(old, new, 1)
    write(path, text)

    text_path = "data/maps/PokemonMansion_B1F/text.inc"
    text = read(text_path)
    if "FireRedComplete_PokemonMansion_Text_HiddenLabDiary::" not in text:
        text += r'''

FireRedComplete_PokemonMansion_Text_HiddenLabDiary::
    .string "Diary: Sept. 5\p"
    .string "The MEW project has been moved to\n"
    .string "the sealed laboratory below.\p"
    .string "Access is hidden behind this shelf.\n"
    .string "A panel clicks open...$"
'''
    write(text_path, text)


def disable_legendary_beast_roamer() -> None:
    path = "src/roamer.c"
    text = read(path)
    old = """void InitRoamer(void)
{
    ClearRoamerData();
    CreateInitialRoamerMon();
}
"""
    new = """void InitRoamer(void)
{
    // FireRed Complete removes Raikou/Entei/Suicune roaming entirely.
    // Mew is instead a fixed postgame encounter in Pokémon Mansion.
    ClearRoamerData();
}
"""
    if old in text:
        text = text.replace(old, new, 1)
    elif "FireRed Complete removes Raikou/Entei/Suicune" not in text:
        raise RuntimeError("Could not disable the legendary-beast roamer")
    write(path, text)


def make_mew_obedient() -> None:
    # Vanilla FRLG deliberately makes non-event Mew disobey.  Our Mansion Mew
    # is a legitimate in-game encounter, so it should obey like a normal
    # postgame Pokémon.  Keep Deoxys' original event restriction unchanged.
    path = "src/battle_util.c"
    text = read(path)
    old = """    if (GetMonData(&gPlayerParty[gBattlerPartyIndexes[battlerId]], MON_DATA_SPECIES, NULL) != SPECIES_DEOXYS
        && GetMonData(&gPlayerParty[gBattlerPartyIndexes[battlerId]], MON_DATA_SPECIES, NULL) != SPECIES_MEW)
            return TRUE;
"""
    new = """    if (GetMonData(&gPlayerParty[gBattlerPartyIndexes[battlerId]], MON_DATA_SPECIES, NULL) != SPECIES_DEOXYS)
        return TRUE;
"""
    if old in text:
        text = text.replace(old, new, 1)
    elif new not in text:
        raise RuntimeError("Could not update Mew obedience handling")
    write(path, text)


def main() -> None:
    add_hidden_lab_to_map_groups()
    include_hidden_lab_scripts_and_text()
    patch_mansion_diary_entry()
    disable_legendary_beast_roamer()
    make_mew_obedient()
    print("FireRed Complete Mew event pass applied.")


if __name__ == "__main__":
    main()
