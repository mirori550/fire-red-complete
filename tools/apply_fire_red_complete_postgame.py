#!/usr/bin/env python3
"""Apply FireRed Complete's first Professor Oak/Champion Samuel pass.

This pass repurposes FireRed's unused Professor Oak trainer slot, adds the
postgame challenge in Oak's Lab, guarantees the requested base prize money,
and randomizes Ditto among Oak's middle four party slots while keeping Tauros
first and Nidoking last.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    p = ROOT / path
    if p.read_text(encoding="utf-8") != text:
        p.write_text(text, encoding="utf-8")


def patch_flags() -> None:
    path = "include/constants/flags.h"
    text = read(path)
    if "FLAG_FRC_OAK_DEFEATED_ONCE" not in text:
        marker = "#define FLAG_0x335               0x335\n"
        replacement = (
            "#define FLAG_FRC_OAK_DEFEATED_ONCE 0x335\n"
            "#define FLAG_FRC_OAK_BACKSTORY_TOLD 0x336\n"
            "#define FLAG_FRC_MEW_CAUGHT         0x337\n"
            "#define FLAG_FRC_AGATHA_REACTED     0x338\n"
        )
        if marker not in text:
            raise RuntimeError("Could not reserve FireRed Complete flags")
        text = text.replace(marker, replacement, 1)
        # Remove the now-aliased generic flag lines so there are no duplicate
        # human-facing names for our reserved values.
        text = text.replace("#define FLAG_0x336               0x336\n", "", 1)
        text = text.replace("#define FLAG_0x337               0x337\n", "", 1)
        text = text.replace("#define FLAG_0x338               0x338\n", "", 1)
    write(path, text)


def patch_oak_party() -> None:
    path = "src/data/trainer_parties.h"
    text = read(path)
    old = "static const struct TrainerMonNoItemDefaultMoves sParty_PkmnProfProfOak[] = {DUMMY_TRAINER_MON};"
    new = r'''static const struct TrainerMonNoItemCustomMoves sParty_PkmnProfProfOak[] = {
    {
        .iv = 250,
        .lvl = 66,
        .species = SPECIES_TAUROS,
        .moves = {MOVE_TAKE_DOWN, MOVE_EARTHQUAKE, MOVE_SURF, MOVE_REST},
    },
    {
        .iv = 250,
        .lvl = 68,
        .species = SPECIES_POLIWRATH,
        .moves = {MOVE_HYDRO_PUMP, MOVE_FOCUS_PUNCH, MOVE_BLIZZARD, MOVE_TOXIC},
    },
    {
        .iv = 250,
        .lvl = 67,
        .species = SPECIES_GENGAR,
        .moves = {MOVE_HYPER_BEAM, MOVE_SHADOW_BALL, MOVE_SLUDGE_BOMB, MOVE_REST},
    },
    {
        .iv = 250,
        .lvl = 65,
        .species = SPECIES_DITTO,
        .moves = {MOVE_TRANSFORM, MOVE_NONE, MOVE_NONE, MOVE_NONE},
    },
    {
        .iv = 250,
        .lvl = 69,
        .species = SPECIES_SNORLAX,
        .moves = {MOVE_HYPER_BEAM, MOVE_SOLAR_BEAM, MOVE_REST, MOVE_SHADOW_BALL},
    },
    {
        .iv = 250,
        .lvl = 70,
        .species = SPECIES_NIDOKING,
        .moves = {MOVE_FOCUS_PUNCH, MOVE_EARTHQUAKE, MOVE_HYPER_BEAM, MOVE_TOXIC},
    },
};'''
    if old in text:
        text = text.replace(old, new, 1)
    elif "sParty_PkmnProfProfOak[]" not in text or "SPECIES_NIDOKING" not in text:
        raise RuntimeError("Could not replace unused Oak trainer party")
    write(path, text)


def patch_oak_trainer() -> None:
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
    if ".trainerName = _(\"SAMUEL\")" not in text:
        text, count = pattern.subn(replacement, text, count=1)
        if count != 1:
            raise RuntimeError("Could not replace unused Oak trainer metadata")
    write(path, text)


def patch_oak_ditto_order() -> None:
    path = "src/battle_main.c"
    text = read(path)
    helper_name = "RandomizeFireRedCompleteOakDitto"
    if f"static void {helper_name}(" not in text:
        marker = "\nstatic u8 CreateNPCTrainerParty(struct Pokemon *party, u16 trainerNum)\n{"
        if marker not in text:
            raise RuntimeError("Could not find CreateNPCTrainerParty for Oak randomization")
        helper = r'''
static void RandomizeFireRedCompleteOakDitto(struct Pokemon *party, u16 trainerNum)
{
    s8 dittoIndex = -1;
    u8 targetIndex;
    u8 i;
    struct Pokemon ditto;

    if (trainerNum != TRAINER_PKMN_PROF_PROF_OAK)
        return;

    for (i = 1; i < PARTY_SIZE - 1; i++)
    {
        if (GetMonData(&party[i], MON_DATA_SPECIES) == SPECIES_DITTO)
        {
            dittoIndex = i;
            break;
        }
    }

    if (dittoIndex < 0)
        return;

    targetIndex = 1 + (Random() % 4);
    if (targetIndex == dittoIndex)
        return;

    ditto = party[dittoIndex];
    if (dittoIndex < targetIndex)
    {
        for (i = dittoIndex; i < targetIndex; i++)
            party[i] = party[i + 1];
    }
    else
    {
        for (i = dittoIndex; i > targetIndex; i--)
            party[i] = party[i - 1];
    }
    party[targetIndex] = ditto;
}
'''
        text = text.replace(marker, "\n" + helper + marker.lstrip("\n"), 1)

    call = "    RandomizeFireRedCompleteOakDitto(party, trainerNum);\n"
    if call not in text:
        rival_call = "    ApplyFireRedCompleteRivalMoves(party, trainerNum);\n\n"
        if rival_call in text:
            text = text.replace(rival_call, rival_call.rstrip("\n") + "\n" + call + "\n", 1)
        else:
            old = "    return gTrainers[trainerNum].partySize;\n}"
            if old not in text:
                raise RuntimeError("Could not insert Oak party randomization call")
            text = text.replace(old, call + "\n" + old, 1)
    write(path, text)


def patch_oak_money() -> None:
    path = "src/battle_script_commands.c"
    text = read(path)
    if '#include "constants/opponents.h"' not in text:
        marker = '#include "constants/maps.h"\n'
        if marker not in text:
            raise RuntimeError("Could not add opponents include for Oak reward")
        text = text.replace(marker, marker + '#include "constants/opponents.h"\n', 1)

    if "gTrainerBattleOpponent_A == TRAINER_PKMN_PROF_PROF_OAK" not in text:
        old = """        if (gTrainerBattleOpponent_A == TRAINER_SECRET_BASE)
        {
            moneyReward = gBattleResources->secretBase->party.levels[0] * 20 * gBattleStruct->moneyMultiplier;
        }
        else
        {
"""
        new = """        if (gTrainerBattleOpponent_A == TRAINER_SECRET_BASE)
        {
            moneyReward = gBattleResources->secretBase->party.levels[0] * 20 * gBattleStruct->moneyMultiplier;
        }
        else if (gTrainerBattleOpponent_A == TRAINER_PKMN_PROF_PROF_OAK)
        {
            // Champion Samuel awards a base ₽30,000; Amulet Coin still works normally.
            moneyReward = 30000 * gBattleStruct->moneyMultiplier;
        }
        else
        {
"""
        if old not in text:
            raise RuntimeError("Could not insert Champion Samuel prize money")
        text = text.replace(old, new, 1)
    write(path, text)


def patch_oak_lab_battle() -> None:
    path = "data/maps/PalletTown_ProfessorOaksLab/scripts.inc"
    text = read(path)
    if "FireRedComplete_EventScript_OakFirstBattle" not in text:
        old = """PalletTown_ProfessorOaksLab_EventScript_ProfOak::
\tlock
\tfaceplayer
\tgoto_if_set SHOWED_OAK_COMPLETE_DEX, PalletTown_ProfessorOaksLab_EventScript_OakJustShownCompleteDex
"""
        new = """PalletTown_ProfessorOaksLab_EventScript_ProfOak::
\tlock
\tfaceplayer
\tgoto_if_set FLAG_FRC_OAK_DEFEATED_ONCE, FireRedComplete_EventScript_ProfOakVanilla
\tgoto_if_set FLAG_SYS_GAME_CLEAR, FireRedComplete_EventScript_OakFirstBattle

FireRedComplete_EventScript_ProfOakVanilla::
\tgoto_if_set SHOWED_OAK_COMPLETE_DEX, PalletTown_ProfessorOaksLab_EventScript_OakJustShownCompleteDex
"""
        if old not in text:
            raise RuntimeError("Could not hook first Champion Samuel battle into Oak's Lab")
        text = text.replace(old, new, 1)

        scripts = """

FireRedComplete_EventScript_OakFirstBattle::
\tmsgbox FireRedComplete_Text_OakFirstBattleIntro
\tclosemessage
\ttrainerbattle_no_intro TRAINER_PKMN_PROF_PROF_OAK, FireRedComplete_Text_OakBattleDefeat
\tsetflag FLAG_FRC_OAK_DEFEATED_ONCE
\tmsgbox FireRedComplete_Text_OakFirstVictory
\trelease
\tend
"""
        text += scripts
    write(path, text)

    text_path = "data/maps/PalletTown_ProfessorOaksLab/text.inc"
    text = read(text_path)
    if "FireRedComplete_Text_OakFirstBattleIntro::" not in text:
        text += r'''

FireRedComplete_Text_OakFirstBattleIntro::
    .string "OAK: Hey, {PLAYER}, how many GYM\n"
    .string "BADGES do you have?\p"
    .string "What? You already beat the\n"
    .string "ELITE FOUR?\p"
    .string "Let's check out how strong your\n"
    .string "POKéMON really are!$"

FireRedComplete_Text_OakBattleDefeat::
    .string "OAK: Impressive, {PLAYER}!$"

FireRedComplete_Text_OakFirstVictory::
    .string "OAK: Congratulations, {PLAYER}!\n"
    .string "You are now the true CHAMPION!\p"
    .string "Go explore the KANTO region,\n"
    .string "and don't forget...\p"
    .string "You still need to complete the\n"
    .string "POKéDEX!$"
'''
    write(text_path, text)


def main() -> None:
    patch_flags()
    patch_oak_party()
    patch_oak_trainer()
    patch_oak_ditto_order()
    patch_oak_money()
    patch_oak_lab_battle()
    print("FireRed Complete Champion Samuel pass applied.")


if __name__ == "__main__":
    main()
