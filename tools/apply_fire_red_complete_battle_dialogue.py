#!/usr/bin/env python3
"""Add FireRed Complete's one-time mid-battle Oak/Agatha dialogue."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def write(path, text):
    p = ROOT / path
    if p.read_text(encoding="utf-8") != text:
        p.write_text(text, encoding="utf-8")


def patch_battle_scripts_header():
    path = "include/battle_scripts.h"
    text = read(path)
    marker = "#endif // GUARD_BATTLE_SCRIPTS_H"
    decl = """
extern const u8 BattleScript_FireRedCompleteAgathaReaction[];
extern const u8 BattleScript_FireRedCompleteOakNidokingLine[];

"""
    if "BattleScript_FireRedCompleteAgathaReaction" not in text:
        if marker not in text:
            raise RuntimeError("battle_scripts.h footer not found")
        text = text.replace(marker, decl + marker, 1)
    write(path, text)


def patch_battle_script_data():
    path = "data/battle_scripts_1.s"
    text = read(path)
    if "BattleScript_FireRedCompleteAgathaReaction::" not in text:
        text += r'''

@ FireRed Complete story dialogue.  These are pushed from the normal
@ switch-in command, so all ordinary battle UI/status handling remains intact.
BattleScript_FireRedCompleteAgathaReaction::
	printstring STRINGID_DUMMY288
	waitmessage 0x40
	return

BattleScript_FireRedCompleteOakNidokingLine::
	printstring STRINGID_DUMMY289
	waitmessage 0x40
	return
'''
    write(path, text)


def patch_battle_messages():
    path = "src/battle_message.c"
    text = read(path)
    marker = 'static const u8 sText_Empty1[] = _("\\0");'
    # Source revisions use _(""), not necessarily _("\\0").
    if marker not in text:
        marker = 'static const u8 sText_Empty1[] = _("\");'
    # Avoid depending on the exact empty-string spelling; insert before the
    # first trainer lose text, which is stable in the decompilation.
    insertion_marker = 'static const u8 sText_Trainer1LoseText[] = _("{B_TRAINER1_LOSE_TEXT}");'
    strings = r'''static const u8 sText_FireRedCompleteAgathaReaction[] = _("AGATHA: Wait a minute, isn't that\nSammy's POKéMON?\pGreat! Now I can have a rematch!");
static const u8 sText_FireRedCompleteOakNidokingLine[] = _("SAMUEL: By the way, how was your\nbattle with Agatha?\pWhy? No reason.");
'''
    if "sText_FireRedCompleteAgathaReaction" not in text:
        if insertion_marker not in text:
            raise RuntimeError("battle message insertion point not found")
        text = text.replace(insertion_marker, strings + insertion_marker, 1)

    text = text.replace(
        "[STRINGID_DUMMY288 - BATTLESTRINGS_TABLE_START]                      = sText_Empty1,",
        "[STRINGID_DUMMY288 - BATTLESTRINGS_TABLE_START]                      = sText_FireRedCompleteAgathaReaction,",
    )
    text = text.replace(
        "[STRINGID_DUMMY289 - BATTLESTRINGS_TABLE_START]                      = sText_Empty1,",
        "[STRINGID_DUMMY289 - BATTLESTRINGS_TABLE_START]                      = sText_FireRedCompleteOakNidokingLine,",
    )
    if "STRINGID_DUMMY288 - BATTLESTRINGS_TABLE_START]                      = sText_FireRedCompleteAgathaReaction" not in text:
        raise RuntimeError("Could not repurpose DUMMY288 battle string")
    if "STRINGID_DUMMY289 - BATTLESTRINGS_TABLE_START]                      = sText_FireRedCompleteOakNidokingLine" not in text:
        raise RuntimeError("Could not repurpose DUMMY289 battle string")
    write(path, text)


def patch_switch_in_hook():
    path = "src/battle_script_commands.c"
    text = read(path)
    for inc in ('#include "constants/maps.h"\n',):
        if '#include "constants/flags.h"' not in text:
            text = text.replace(inc, inc + '#include "constants/flags.h"\n#include "constants/trainers.h"\n', 1)

    if "ResetFireRedCompleteBattleDialogue" not in text:
        marker = "extern const u8 *const gBattleScriptsForMoveEffects[];\n"
        helper = r'''

static bool8 sFireRedCompleteAgathaReacted;
static bool8 sFireRedCompleteOakNidokingSaid;

void ResetFireRedCompleteBattleDialogue(void)
{
    sFireRedCompleteAgathaReacted = FALSE;
    sFireRedCompleteOakNidokingSaid = FALSE;
}

static bool8 IsFireRedCompleteAgathaRecognizedSpecies(u16 species)
{
    switch (species)
    {
    case SPECIES_BULBASAUR:
    case SPECIES_IVYSAUR:
    case SPECIES_VENUSAUR:
    case SPECIES_CHARMANDER:
    case SPECIES_CHARMELEON:
    case SPECIES_CHARIZARD:
    case SPECIES_SQUIRTLE:
    case SPECIES_WARTORTLE:
    case SPECIES_BLASTOISE:
    case SPECIES_NIDORAN_M:
    case SPECIES_NIDORINO:
    case SPECIES_NIDOKING:
        return TRUE;
    default:
        return FALSE;
    }
}

static const u8 *TryFireRedCompleteSwitchInDialogue(u8 battler)
{
    if (!(gBattleTypeFlags & BATTLE_TYPE_TRAINER) || gBattleTypeFlags & BATTLE_TYPE_LINK)
        return NULL;

    if (!sFireRedCompleteAgathaReacted
     && gTrainers[gTrainerBattleOpponent_A].trainerPic == TRAINER_PIC_ELITE_FOUR_AGATHA
     && GetBattlerSide(battler) == B_SIDE_PLAYER
     && IsFireRedCompleteAgathaRecognizedSpecies(gBattleMons[battler].species))
    {
        sFireRedCompleteAgathaReacted = TRUE;
        return BattleScript_FireRedCompleteAgathaReaction;
    }

    if (!sFireRedCompleteOakNidokingSaid
     && gTrainerBattleOpponent_A == TRAINER_PKMN_PROF_PROF_OAK
     && !FlagGet(FLAG_FRC_OAK_DEFEATED_ONCE)
     && GetBattlerSide(battler) == B_SIDE_OPPONENT
     && gBattleMons[battler].species == SPECIES_NIDOKING)
    {
        sFireRedCompleteOakNidokingSaid = TRUE;
        return BattleScript_FireRedCompleteOakNidokingLine;
    }

    return NULL;
}
'''
        if marker not in text:
            raise RuntimeError("battle_script_commands helper insertion point not found")
        text = text.replace(marker, marker + helper, 1)

    old = """    BtlController_EmitSwitchInAnim(BUFFER_A, gBattlerPartyIndexes[gActiveBattler], gBattlescriptCurrInstr[2]);
    MarkBattlerForControllerExec(gActiveBattler);

    gBattlescriptCurrInstr += 3;
}
"""
    new = """    BtlController_EmitSwitchInAnim(BUFFER_A, gBattlerPartyIndexes[gActiveBattler], gBattlescriptCurrInstr[2]);
    MarkBattlerForControllerExec(gActiveBattler);

    {
        const u8 *fireRedCompleteScript = TryFireRedCompleteSwitchInDialogue(gActiveBattler);
        if (fireRedCompleteScript != NULL)
        {
            BattleScriptPush(gBattlescriptCurrInstr + 3);
            gBattlescriptCurrInstr = fireRedCompleteScript;
        }
        else
        {
            gBattlescriptCurrInstr += 3;
        }
    }
}
"""
    if old in text:
        text = text.replace(old, new, 1)
    elif "TryFireRedCompleteSwitchInDialogue(gActiveBattler)" not in text:
        raise RuntimeError("Cmd_switchinanim hook not found")
    write(path, text)


def patch_battle_reset():
    path = "src/battle_main.c"
    text = read(path)
    if "extern void ResetFireRedCompleteBattleDialogue(void);" not in text:
        # Put this near the normal forward declarations/includes without needing
        # to alter a public header for one project-local hook.
        marker = "#include \"constants/union_room.h\"\n"
        if marker not in text:
            # Fallback: immediately before the first table/constant section.
            marker = "// This is a factor in how much money you get for beating a trainer.\n"
            if marker not in text:
                raise RuntimeError("battle_main reset declaration insertion point not found")
            text = text.replace(marker, "extern void ResetFireRedCompleteBattleDialogue(void);\n\n" + marker, 1)
        else:
            text = text.replace(marker, marker + "\nextern void ResetFireRedCompleteBattleDialogue(void);\n", 1)

    old = """void CB2_InitBattle(void)
{
    MoveSaveBlocks_ResetHeap();
"""
    new = """void CB2_InitBattle(void)
{
    ResetFireRedCompleteBattleDialogue();
    MoveSaveBlocks_ResetHeap();
"""
    if old in text:
        text = text.replace(old, new, 1)
    elif "ResetFireRedCompleteBattleDialogue();" not in text:
        raise RuntimeError("CB2_InitBattle reset hook not found")
    write(path, text)


def main():
    patch_battle_scripts_header()
    patch_battle_script_data()
    patch_battle_messages()
    patch_switch_in_hook()
    patch_battle_reset()
    print("FireRed Complete mid-battle dialogue pass applied.")


if __name__ == "__main__":
    main()
