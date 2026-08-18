#!/usr/bin/env python3
"""Make Champion Samuel repeatable with the Vs. Seeker after catching all 151."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def write(path, text):
    p = ROOT / path
    if p.read_text(encoding="utf-8") != text:
        p.write_text(text, encoding="utf-8")


def patch_oak_rematch_script():
    path = "data/maps/PalletTown_ProfessorOaksLab/scripts.inc"
    text = read(path)
    if "FireRedComplete_EventScript_OakRematch::" not in text:
        text += r'''

@ FireRed Complete: after catching the complete Kanto Pokédex, using the
@ Vs. Seeker inside Oak's Lab calls this repeatable Champion Samuel battle.
FireRedComplete_EventScript_OakRematch::
	lockall
	faceplayer
	msgbox FireRedComplete_Text_OakRematchIntro
	closemessage
	trainerbattle_no_intro TRAINER_PKMN_PROF_PROF_OAK, FireRedComplete_Text_OakBattleDefeat
	goto_if_set FLAG_FRC_OAK_BACKSTORY_TOLD, FireRedComplete_EventScript_OakLaterRematchWin
	setflag FLAG_FRC_OAK_BACKSTORY_TOLD
	msgbox FireRedComplete_Text_OakAgathaBackstory
	releaseall
	end

FireRedComplete_EventScript_OakLaterRematchWin::
	msgbox FireRedComplete_Text_OakExperimentNow
	releaseall
	end
'''
    write(path, text)

    path = "data/maps/PalletTown_ProfessorOaksLab/text.inc"
    text = read(path)
    if "FireRedComplete_Text_OakRematchIntro::" not in text:
        text += r'''

FireRedComplete_Text_OakRematchIntro::
    .string "OAK: So, {PLAYER}, you completed the\n"
    .string "KANTO POKéDEX.\p"
    .string "That deserves another battle!$"

FireRedComplete_Text_OakAgathaBackstory::
    .string "OAK: You know what? I feel like I\n"
    .string "should explain what I meant when I\n"
    .string "talked about Agatha.\p"
    .string "You see, she and I used to be\n"
    .string "rivals, just like you and {RIVAL}.\p"
    .string "Both of us were CHAMPIONS, and in\n"
    .string "our last battle... I won.\p"
    .string "Ever since we got into POKéMON, we\n"
    .string "went down different paths.\p"
    .string "I study POKéMON, while she is part\n"
    .string "of the ELITE FOUR.\p"
    .string "Anyway, I'd better get back to my\n"
    .string "experiment.$"

FireRedComplete_Text_OakExperimentNow::
    .string "OAK: Better get to my experiment\n"
    .string "now.$"
'''
    write(path, text)


def patch_vs_seeker_use():
    path = "src/item_use.c"
    text = read(path)

    if '#include "pokedex.h"' not in text:
        marker = '#include "party_menu.h"\n'
        if marker not in text:
            raise RuntimeError("Could not add pokedex include to item_use.c")
        text = text.replace(marker, marker + '#include "pokedex.h"\n', 1)
    if '#include "constants/flags.h"' not in text:
        marker = '#include "constants/field_weather.h"\n'
        if marker not in text:
            raise RuntimeError("Could not add flags include to item_use.c")
        text = text.replace(marker, marker + '#include "constants/flags.h"\n', 1)

    if "FireRedComplete_EventScript_OakRematch[]" not in text:
        marker = "static EWRAM_DATA void (*sItemUseOnFieldCB)(u8 taskId) = NULL;\n"
        decl = "\nextern const u8 FireRedComplete_EventScript_OakRematch[];\n"
        if marker not in text:
            raise RuntimeError("Could not declare Oak rematch script")
        text = text.replace(marker, marker + decl, 1)

    if "Task_FireRedCompleteOakVsSeeker" not in text:
        marker = "static void Task_UseRepel(u8 taskId);\n"
        if marker not in text:
            raise RuntimeError("Could not declare Oak Vs Seeker task")
        text = text.replace(marker, marker + "static void Task_FireRedCompleteOakVsSeeker(u8 taskId);\n", 1)

        helper_marker = "void FieldUseFunc_VsSeeker(u8 taskId)\n{\n"
        helper = r'''static void Task_FireRedCompleteOakVsSeeker(u8 taskId)
{
    DestroyTask(taskId);
    ScriptContext_SetupScript(FireRedComplete_EventScript_OakRematch);
}

'''
        if helper_marker not in text:
            raise RuntimeError("Could not insert Oak Vs Seeker task")
        text = text.replace(helper_marker, helper + helper_marker, 1)

    old = """void FieldUseFunc_VsSeeker(u8 taskId)
{
    if ((gMapHeader.mapType != MAP_TYPE_ROUTE
"""
    new = """void FieldUseFunc_VsSeeker(u8 taskId)
{
    // FireRed Complete's one indoor exception: after the first Samuel battle
    // and after catching all 151 Kanto species, the Vs. Seeker can challenge
    // Oak again in his lab.
    if (gSaveBlock1Ptr->location.mapGroup == MAP_GROUP(MAP_PALLET_TOWN_PROFESSOR_OAKS_LAB)
     && gSaveBlock1Ptr->location.mapNum == MAP_NUM(MAP_PALLET_TOWN_PROFESSOR_OAKS_LAB)
     && FlagGet(FLAG_FRC_OAK_DEFEATED_ONCE)
     && GetKantoPokedexCount(FLAG_GET_CAUGHT) >= 151)
    {
        sItemUseOnFieldCB = Task_FireRedCompleteOakVsSeeker;
        SetUpItemUseOnFieldCallback(taskId);
        return;
    }

    if ((gMapHeader.mapType != MAP_TYPE_ROUTE
"""
    if old in text:
        text = text.replace(old, new, 1)
    elif "GetKantoPokedexCount(FLAG_GET_CAUGHT) >= 151" not in text:
        raise RuntimeError("Could not hook Vs Seeker for Oak rematches")

    write(path, text)


def main():
    patch_oak_rematch_script()
    patch_vs_seeker_use()
    print("FireRed Complete Oak Vs. Seeker rematch pass applied.")


if __name__ == "__main__":
    main()
