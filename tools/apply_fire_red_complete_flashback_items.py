#!/usr/bin/env python3
"""Give both sides five Full Restores in the playable Oak/Agatha flashback."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def write(path, text):
    p = ROOT / path
    if p.read_text(encoding="utf-8") != text:
        p.write_text(text, encoding="utf-8")


def patch_trainer_item_limit():
    path = "include/battle.h"
    text = read(path)
    if "#define MAX_TRAINER_ITEMS 5" not in text:
        if "#define MAX_TRAINER_ITEMS 4" not in text:
            raise RuntimeError("Could not find trainer item limit")
        text = text.replace("#define MAX_TRAINER_ITEMS 4", "#define MAX_TRAINER_ITEMS 5", 1)
    write(path, text)


def patch_champion_samuel_metadata():
    """Ensure Oak's custom-moves party uses the matching trainer-party type."""
    path = "src/data/trainers.h"
    text = read(path)
    pattern = re.compile(
        r"    \[TRAINER_PKMN_PROF_PROF_OAK\] = \{\n.*?\n    \},",
        re.S,
    )
    replacement = r'''    [TRAINER_PKMN_PROF_PROF_OAK] = {
        .trainerClass = TRAINER_CLASS_CHAMPION,
        .encounterMusic_gender = TRAINER_ENCOUNTER_MUSIC_MALE,
        .trainerPic = TRAINER_PIC_PROFESSOR_OAK,
        .trainerName = _("SAMUEL"),
        .items = {},
        .doubleBattle = FALSE,
        .aiFlags = AI_SCRIPT_CHECK_BAD_MOVE | AI_SCRIPT_TRY_TO_FAINT | AI_SCRIPT_CHECK_VIABILITY,
        .party = NO_ITEM_CUSTOM_MOVES(sParty_PkmnProfProfOak),
    },'''
    match = pattern.search(text)
    if match is None:
        raise RuntimeError("Could not find Champion Samuel trainer metadata")
    if ".party = NO_ITEM_CUSTOM_MOVES(sParty_PkmnProfProfOak)" not in match.group(0):
        text = text[:match.start()] + replacement + text[match.end():]
    write(path, text)


def patch_archive_agatha_metadata():
    """Repurpose an unused Hoenn dummy slot so present-day Agatha is untouched."""
    path = "src/data/trainers.h"
    text = read(path)
    pattern = re.compile(
        r"    \[TRAINER_ELITE_FOUR_PHOEBE\] = \{\n.*?\n    \},",
        re.S,
    )
    replacement = r'''    [TRAINER_ELITE_FOUR_PHOEBE] = {
        .trainerClass = TRAINER_CLASS_ELITE_FOUR,
        .encounterMusic_gender = TRAINER_ENCOUNTER_MUSIC_ELITE_FOUR,
        .trainerPic = TRAINER_PIC_ELITE_FOUR_AGATHA,
        .trainerName = _("AGATHA"),
        .items = {ITEM_FULL_RESTORE, ITEM_FULL_RESTORE, ITEM_FULL_RESTORE, ITEM_FULL_RESTORE, ITEM_FULL_RESTORE},
        .doubleBattle = FALSE,
        .aiFlags = AI_SCRIPT_CHECK_BAD_MOVE | AI_SCRIPT_TRY_TO_FAINT | AI_SCRIPT_CHECK_VIABILITY,
        .party = NO_ITEM_DEFAULT_MOVES(sParty_EliteFourPhoebe),
    },'''
    if "ITEM_FULL_RESTORE, ITEM_FULL_RESTORE, ITEM_FULL_RESTORE, ITEM_FULL_RESTORE, ITEM_FULL_RESTORE" not in text:
        text, count = pattern.subn(replacement, text, count=1)
        if count != 1:
            raise RuntimeError("Could not repurpose archive Agatha trainer slot")
    write(path, text)


def patch_playable_flashback_inventory():
    path = "src/teachy_tv.c"
    text = read(path)

    # The original player's Full Restore quantity is restored exactly after the
    # flashback. During the archival battle, young Samuel starts with five.
    if "sOakAgathaSavedFullRestores" not in text:
        marker = "static EWRAM_DATA struct TeachyTvBuf * sResources = NULL;\n"
        if marker not in text:
            raise RuntimeError("Could not add flashback inventory backup")
        text = text.replace(
            marker,
            marker + "static EWRAM_DATA u16 sOakAgathaSavedFullRestores = 0;\n",
            1,
        )

    old = """    ZeroPlayerPartyMons();
    ZeroEnemyPartyMons();
    for (i = 0; i < PARTY_SIZE; i++)
"""
    new = """    sOakAgathaSavedFullRestores = BagGetQuantityByItemId(ITEM_FULL_RESTORE);
    if (sOakAgathaSavedFullRestores != 0)
        RemoveBagItem(ITEM_FULL_RESTORE, sOakAgathaSavedFullRestores);
    AddBagItem(ITEM_FULL_RESTORE, 5);

    ZeroPlayerPartyMons();
    ZeroEnemyPartyMons();
    for (i = 0; i < PARTY_SIZE; i++)
"""
    if old in text:
        text = text.replace(old, new, 1)
    elif "AddBagItem(ITEM_FULL_RESTORE, 5);" not in text:
        raise RuntimeError("Could not give young Samuel five Full Restores")

    # Use the dedicated archive Agatha metadata slot. Her actual six-Pokemon
    # party is still created directly by SetupPlayableOakAgathaBattle.
    text = text.replace(
        "    gTrainerBattleOpponent_A = TRAINER_ELITE_FOUR_AGATHA;\n",
        "    gTrainerBattleOpponent_A = TRAINER_ELITE_FOUR_PHOEBE;\n",
        1,
    )

    old = """static void TeachyTvRestorePlayerPartyCallback(void)
{
    LoadPlayerParty();
"""
    new = """static void TeachyTvRestorePlayerPartyCallback(void)
{
    if (sStaticResources.whichScript == TTVSCR_OAK_AGATHA)
    {
        u16 currentFullRestores = BagGetQuantityByItemId(ITEM_FULL_RESTORE);
        if (currentFullRestores != 0)
            RemoveBagItem(ITEM_FULL_RESTORE, currentFullRestores);
        if (sOakAgathaSavedFullRestores != 0)
            AddBagItem(ITEM_FULL_RESTORE, sOakAgathaSavedFullRestores);
        sOakAgathaSavedFullRestores = 0;
    }

    LoadPlayerParty();
"""
    if old in text:
        text = text.replace(old, new, 1)
    elif "currentFullRestores = BagGetQuantityByItemId" not in text:
        raise RuntimeError("Could not restore the player's Full Restore inventory")

    write(path, text)


def main():
    patch_trainer_item_limit()
    patch_champion_samuel_metadata()
    patch_archive_agatha_metadata()
    patch_playable_flashback_inventory()
    print("Applied five Full Restores and finalized Champion Samuel metadata")


if __name__ == "__main__":
    main()
