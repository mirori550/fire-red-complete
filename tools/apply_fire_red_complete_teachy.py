#!/usr/bin/env python3
"""Add the Agatha vs. Oak archival battle to the Teachy TV.

The recording extends FireRed's existing POKé DUDE scripted-battle controller,
so it is watch-only but still uses the real battle renderer, move animations,
HP bars, status icons, switching, and fainting logic.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def write(path, text):
    p = ROOT / path
    if p.read_text(encoding="utf-8") != text:
        p.write_text(text, encoding="utf-8")


def patch_teachy_header():
    path = "include/teachy_tv.h"
    text = read(path)
    old = """    TTVSCR_TMS,
    TTVSCR_REGISTER
};
"""
    new = """    TTVSCR_TMS,
    TTVSCR_REGISTER,
    TTVSCR_OAK_AGATHA
};
"""
    if old in text:
        text = text.replace(old, new, 1)
    elif "TTVSCR_OAK_AGATHA" not in text:
        raise RuntimeError("Could not extend Teachy TV script enum")
    write(path, text)


def patch_strings():
    path = "src/data/text/teachy_tv.h"
    text = read(path)
    if "gTeachyTvString_OakAgathaBattle" not in text:
        marker = 'const u8 gTeachyTvString_Cancel[] = _("CANCEL");\n'
        extra = r'''const u8 gTeachyTvString_OakAgathaBattle[] = _("Agatha vs. Oak Battle");
const u8 gTeachyTvText_OakAgathaScript1[] = _(
    "ARCHIVE FOOTAGE - KANTO LEAGUE\p"
    "A young SAMUEL OAK enters the\n"
    "CHAMPION's room.\p"
    "AGATHA: Sammy, good to see you\n"
    "became CHAMPION.\p"
    "Too bad you're too late! I already\n"
    "became CHAMPION a few minutes ago!\p"
    "Their final battle begins...");
const u8 gTeachyTvText_OakAgathaScript2[] = _(
    "AGATHA: ...You actually beat me.\p"
    "SAMUEL: Looks like I'm the CHAMPION\n"
    "now.\p"
    "AGATHA: Don't get used to it, Sammy.\p"
    "ARCHIVE FOOTAGE ENDS.");
'''
        if marker not in text:
            raise RuntimeError("Teachy TV string insertion point not found")
        text = text.replace(marker, marker + extra, 1)
    write(path, text)

    path = "include/strings.h"
    text = read(path)
    if "gTeachyTvString_OakAgathaBattle" not in text:
        marker = "extern const u8 gTeachyTvString_Cancel[];\n"
        extra = (
            "extern const u8 gTeachyTvString_OakAgathaBattle[];\n"
            "extern const u8 gTeachyTvText_OakAgathaScript1[];\n"
            "extern const u8 gTeachyTvText_OakAgathaScript2[];\n"
        )
        if marker not in text:
            raise RuntimeError("strings.h Teachy TV insertion point not found")
        text = text.replace(marker, marker + extra, 1)
    write(path, text)


def patch_teachy_menu_and_flow():
    path = "src/teachy_tv.c"
    text = read(path)

    if ".label = gTeachyTvString_OakAgathaBattle" not in text:
        # Add the archive program immediately before CANCEL in both menu lists.
        cancel_block = """    {
        .label = gTeachyTvString_Cancel,
        .index = -2
    },
"""
        history_block = """    {
        .label = gTeachyTvString_OakAgathaBattle,
        .index = TTVSCR_OAK_AGATHA
    },
"""
        # There are exactly two lists with a cancel entry.
        text = text.replace(cancel_block, history_block + cancel_block, 2)

        text = text.replace(".totalItems = 7,\n    .maxShowed = 6,", ".totalItems = 8,\n    .maxShowed = 6,", 1)
        text = text.replace("gMultiuseListMenuTemplate.totalItems = 5;\n        gMultiuseListMenuTemplate.maxShowed = 5;",
                            "gMultiuseListMenuTemplate.totalItems = 6;\n        gMultiuseListMenuTemplate.maxShowed = 6;", 1)

    # One extra return state for the recording: resume at its outro text.
    old = """static const u8 sWhereToReturnToFromBattle[] = 
{
    12,
    12,
    12,
    12,
     9,
     9
};
"""
    new = """static const u8 sWhereToReturnToFromBattle[] = 
{
    12,
    12,
    12,
    12,
     9,
     9,
     4
};
"""
    if old in text:
        text = text.replace(old, new, 1)

    if "sOakAgathaScript[]" not in text:
        marker = "static void (* const sRegisterKeyItemScript[])(u8) = \n{"
        idx = text.find(marker)
        if idx < 0:
            raise RuntimeError("Teachy TV script-array insertion point not found")
        end = text.find("\n};", idx) + 4
        archive = r'''

static void TTVcmd_OakAgathaArchiveIntro(u8 taskId)
{
    s16 *data = gTasks[taskId].data;
    TeachyTvInitTextPrinter(gTeachyTvText_OakAgathaScript1);
    ++data[3];
}

static void (* const sOakAgathaScript[])(u8) =
{
    TTVcmd_OakAgathaArchiveIntro,
    TTVcmd_IdleIfTextPrinterIsActive2,
    TTVcmd_EraseTextWindowIfKeyPressed,
    TTVcmd_TaskBattleOrFadeByOptionChosen,
    TTVcmd_TextPrinterSwitchStringByOptionChosen2,
    TTVcmd_IdleIfTextPrinterIsActive2,
    TTVcmd_EraseTextWindowIfKeyPressed,
    TTVcmd_End,
};
'''
        text = text[:end] + archive + text[end:]

    # Function is used by the archive intro before its definition.
    if "static void TTVcmd_OakAgathaArchiveIntro(u8 taskId);" not in text:
        marker = "static void TTVcmd_TaskBattleOrFadeByOptionChosen(u8 taskId);\n"
        text = text.replace(marker, marker + "static void TTVcmd_OakAgathaArchiveIntro(u8 taskId);\n", 1)

    # Add recording cluster to the dispatch table.
    old = """            sTMsScript,
            sRegisterKeyItemScript,
        };
"""
    new = """            sTMsScript,
            sRegisterKeyItemScript,
            sOakAgathaScript,
        };
"""
    if old in text:
        text = text.replace(old, new, 1)

    # Recording intro/outro strings bypass the standard Poké Dude texts.
    old = """        gTeachyTvText_TMsScript1,
        gTeachyTvText_RegisterScript1,
    };
"""
    new = """        gTeachyTvText_TMsScript1,
        gTeachyTvText_RegisterScript1,
        gTeachyTvText_OakAgathaScript1,
    };
"""
    if old in text:
        text = text.replace(old, new, 1)
    old = """        gTeachyTvText_TMsScript2,
        gTeachyTvText_RegisterScript2,
    };
"""
    new = """        gTeachyTvText_TMsScript2,
        gTeachyTvText_RegisterScript2,
        gTeachyTvText_OakAgathaScript2,
    };
"""
    if old in text:
        text = text.replace(old, new, 1)

    # The historical recording launches the same real battle renderer as the
    # four normal Teachy TV battle demonstrations.
    old = """    case TTVSCR_CATCHING:
        TeachyTvPrepBattle(taskId);
        break;
"""
    new = """    case TTVSCR_CATCHING:
    case TTVSCR_OAK_AGATHA:
        TeachyTvPrepBattle(taskId);
        break;
"""
    if old in text:
        text = text.replace(old, new, 1)

    old = """    case TTVSCR_CATCHING:
        TeachyTvSetSpriteCoordsAndSwitchFrame(data[1], 0x78, 0x38, 0);
"""
    new = """    case TTVSCR_CATCHING:
        TeachyTvSetSpriteCoordsAndSwitchFrame(data[1], 0x78, 0x38, 0);
"""
    # No visible Poké Dude host for the archive recording; object starts hidden.
    setup_marker = """    case TTVSCR_TMS:
    case TTVSCR_REGISTER:
        TeachyTvSetSpriteCoordsAndSwitchFrame(data[1], 0x78, 0x38, 0);
        break;
"""
    if "case TTVSCR_OAK_AGATHA:\n        break;" not in text:
        repl = setup_marker + "    case TTVSCR_OAK_AGATHA:\n        break;\n"
        if setup_marker not in text:
            raise RuntimeError("Teachy TV post-battle switch insertion point not found")
        text = text.replace(setup_marker, repl, 1)

    # Use a classic white-bar transition for the archival Champion battle.
    old = """    if (sStaticResources.whichScript == TTVSCR_BATTLE)
        data[6] = B_TRANSITION_WHITE_BARS_FADE;
    else
        data[6] = B_TRANSITION_SLICE;
"""
    new = """    if (sStaticResources.whichScript == TTVSCR_BATTLE || sStaticResources.whichScript == TTVSCR_OAK_AGATHA)
        data[6] = B_TRANSITION_WHITE_BARS_FADE;
    else
        data[6] = B_TRANSITION_SLICE;
"""
    if old in text:
        text = text.replace(old, new, 1)

    write(path, text)


def patch_pokedude_history_battle():
    path = "src/battle_controller_pokedude.c"
    text = read(path)

    # Deterministic move choices for the recording. Each side has an independent
    # cursor through the same timeline. The final repeated choice is slot 1:
    # Nidoking's Earthquake vs Gengar's Psychic, guaranteeing the intended
    # climactic matchup once both aces are last.
    if "sInputScripts_ChooseAction_OakAgatha" not in text:
        marker = "static const struct PokedudeInputScript *const sInputScripts_ChooseAction[] =\n{"
        idx = text.find(marker)
        if idx < 0:
            raise RuntimeError("Pokedude action pointer table not found")
        archive_actions = r'''
static const struct PokedudeInputScript sInputScripts_ChooseAction_OakAgatha[] =
{
    { .cursorPos = {0, 0}, .delay = {36, 36} },
    { .cursorPos = {0, 0}, .delay = {36, 36} },
    { .cursorPos = {0, 0}, .delay = {36, 36} },
    { .cursorPos = {0, 0}, .delay = {36, 36} },
    { .cursorPos = {0, 0}, .delay = {36, 36} },
    { .cursorPos = {0, 0}, .delay = {36, 36} },
    { .cursorPos = {0, 0}, .delay = {36, 36} },
    { .cursorPos = {0, 0}, .delay = {36, 36} },
    { .cursorPos = {0, 0}, .delay = {36, 36} },
    { .cursorPos = {0, 0}, .delay = {36, 36} },
    { .cursorPos = {0, 0}, .delay = {36, 36} },
    { .cursorPos = {0, 0}, .delay = {36, 36} },
    { .cursorPos = {0, 0}, .delay = {36, 36} },
    { .cursorPos = {0, 0}, .delay = {36, 36} },
    { .cursorPos = {0, 0}, .delay = {36, 36} },
    { .cursorPos = {0, 0}, .delay = {36, 36} },
    { .cursorPos = {0, 0}, .delay = {36, 36} },
    { .cursorPos = {0, 0}, .delay = {36, 36} },
    { .cursorPos = {0, 0}, .delay = {36, 36} },
    { .cursorPos = {0, 0}, .delay = {36, 36} },
    { .cursorPos = {4, 4}, .delay = {0, 0} },
};

'''
        text = text[:idx] + archive_actions + text[idx:]

        old = """    [TTVSCR_MATCHUPS] = sInputScripts_ChooseAction_Matchups,
    [TTVSCR_CATCHING] = sInputScripts_ChooseAction_Catching,
};
"""
        new = """    [TTVSCR_MATCHUPS]  = sInputScripts_ChooseAction_Matchups,
    [TTVSCR_CATCHING]  = sInputScripts_ChooseAction_Catching,
    [TTVSCR_OAK_AGATHA] = sInputScripts_ChooseAction_OakAgatha,
};
"""
        if old not in text:
            raise RuntimeError("Could not extend action script pointer table")
        text = text.replace(old, new, 1)

    if "sInputScripts_ChooseMove_OakAgatha" not in text:
        marker = "static const struct PokedudeInputScript *const sInputScripts_ChooseMove[] =\n{"
        idx = text.find(marker)
        if idx < 0:
            raise RuntimeError("Pokedude move pointer table not found")
        # Timeline move-slot choices. Player side is young Oak; opponent is Agatha.
        archive_moves = r'''
static const struct PokedudeInputScript sInputScripts_ChooseMove_OakAgatha[] =
{
    { .cursorPos = {1, 3}, .delay = {36, 36} }, // EQ / Toxic (Tauros vs Victreebel)
    { .cursorPos = {0, 1}, .delay = {36, 36} }, // Take Down / SolarBeam
    { .cursorPos = {1, 0}, .delay = {36, 36} },
    { .cursorPos = {1, 3}, .delay = {36, 36} },
    { .cursorPos = {0, 1}, .delay = {36, 36} },
    { .cursorPos = {2, 0}, .delay = {36, 36} },
    { .cursorPos = {1, 3}, .delay = {36, 36} },
    { .cursorPos = {0, 0}, .delay = {36, 36} },
    { .cursorPos = {1, 1}, .delay = {36, 36} },
    { .cursorPos = {3, 0}, .delay = {36, 36} },
    { .cursorPos = {1, 3}, .delay = {36, 36} },
    { .cursorPos = {0, 1}, .delay = {36, 36} },
    { .cursorPos = {1, 0}, .delay = {36, 36} },
    { .cursorPos = {0, 2}, .delay = {36, 36} },
    { .cursorPos = {3, 3}, .delay = {36, 36} },
    { .cursorPos = {0, 1}, .delay = {36, 36} },
    { .cursorPos = {1, 0}, .delay = {36, 36} },
    { .cursorPos = {0, 2}, .delay = {36, 36} },
    { .cursorPos = {1, 1}, .delay = {36, 36} },
    { .cursorPos = {1, 1}, .delay = {36, 36} },
    { .cursorPos = {255, 255}, .delay = {0, 0} },
};

'''
        text = text[:idx] + archive_moves + text[idx:]
        old = """    [TTVSCR_MATCHUPS] = sInputScripts_ChooseMove_Matchups,
    [TTVSCR_CATCHING] = sInputScripts_ChooseMove_Catching,
};
"""
        new = """    [TTVSCR_MATCHUPS]   = sInputScripts_ChooseMove_Matchups,
    [TTVSCR_CATCHING]   = sInputScripts_ChooseMove_Catching,
    [TTVSCR_OAK_AGATHA] = sInputScripts_ChooseMove_OakAgatha,
};
"""
        if old not in text:
            raise RuntimeError("Could not extend move script pointer table")
        text = text.replace(old, new, 1)

    # The archival battle does not need Poké Dude voiceover interceptions.
    if "sPokedudeTextScripts_OakAgatha" not in text:
        marker = "static const struct PokedudeTextScriptHeader *const sPokedudeTextScripts[] =\n{"
        idx = text.find(marker)
        if idx < 0:
            raise RuntimeError("Pokedude text pointer table not found")
        dummy = r'''static const struct PokedudeTextScriptHeader sPokedudeTextScripts_OakAgatha[] =
{
    { .btlcmd = 0xFF, .side = 0xFF, .stringid = 0xFFFF, .callback = NULL },
};

'''
        text = text[:idx] + dummy + text[idx:]
        old = """    [TTVSCR_MATCHUPS] = sPokedudeTextScripts_Matchups,
    [TTVSCR_CATCHING] = sPokedudeTextScripts_Catching,
};
"""
        new = """    [TTVSCR_MATCHUPS]   = sPokedudeTextScripts_Matchups,
    [TTVSCR_CATCHING]   = sPokedudeTextScripts_Catching,
    [TTVSCR_OAK_AGATHA] = sPokedudeTextScripts_OakAgatha,
};
"""
        if old not in text:
            raise RuntimeError("Could not extend text script pointer table")
        text = text.replace(old, new, 1)

    if "sParties_OakAgatha" not in text:
        marker = "static const struct PokedudeBattlePartyInfo *const sPokedudeBattlePartyPointers[] =\n{"
        idx = text.find(marker)
        if idx < 0:
            raise RuntimeError("Pokedude party pointer table not found")
        parties = r'''static const struct PokedudeBattlePartyInfo sParties_OakAgatha[] =
{
    { .side = B_SIDE_PLAYER, .level = 53, .species = SPECIES_TAUROS,
      .moves = {MOVE_TAKE_DOWN, MOVE_EARTHQUAKE, MOVE_SURF, MOVE_REST}, .nature = NATURE_BRAVE, .gender = MALE },
    { .side = B_SIDE_PLAYER, .level = 54, .species = SPECIES_POLIWRATH,
      .moves = {MOVE_HYDRO_PUMP, MOVE_FOCUS_PUNCH, MOVE_BLIZZARD, MOVE_TOXIC}, .nature = NATURE_BRAVE, .gender = MALE },
    { .side = B_SIDE_PLAYER, .level = 54, .species = SPECIES_GENGAR,
      .moves = {MOVE_HYPER_BEAM, MOVE_SHADOW_BALL, MOVE_SLUDGE_BOMB, MOVE_REST}, .nature = NATURE_MODEST, .gender = MALE },
    { .side = B_SIDE_PLAYER, .level = 53, .species = SPECIES_DITTO,
      .moves = {MOVE_TRANSFORM, MOVE_NONE, MOVE_NONE, MOVE_NONE}, .nature = NATURE_SERIOUS, .gender = GENDERLESS },
    { .side = B_SIDE_PLAYER, .level = 56, .species = SPECIES_SNORLAX,
      .moves = {MOVE_HYPER_BEAM, MOVE_SOLAR_BEAM, MOVE_REST, MOVE_SHADOW_BALL}, .nature = NATURE_BRAVE, .gender = MALE },
    { .side = B_SIDE_PLAYER, .level = 58, .species = SPECIES_NIDOKING,
      .moves = {MOVE_FOCUS_PUNCH, MOVE_EARTHQUAKE, MOVE_HYPER_BEAM, MOVE_TOXIC}, .nature = NATURE_ADAMANT, .gender = MALE },

    { .side = B_SIDE_OPPONENT, .level = 53, .species = SPECIES_VICTREEBEL,
      .moves = {MOVE_SLUDGE_BOMB, MOVE_SOLAR_BEAM, MOVE_SECRET_POWER, MOVE_TOXIC}, .nature = NATURE_MODEST, .gender = FEMALE },
    { .side = B_SIDE_OPPONENT, .level = 54, .species = SPECIES_MUK,
      .moves = {MOVE_SLUDGE_BOMB, MOVE_BRICK_BREAK, MOVE_GIGA_DRAIN, MOVE_ACID_ARMOR}, .nature = NATURE_CAREFUL, .gender = FEMALE },
    { .side = B_SIDE_OPPONENT, .level = 54, .species = SPECIES_GOLBAT,
      .moves = {MOVE_AERIAL_ACE, MOVE_SHADOW_BALL, MOVE_STEEL_WING, MOVE_CONFUSE_RAY}, .nature = NATURE_JOLLY, .gender = FEMALE },
    { .side = B_SIDE_OPPONENT, .level = 53, .species = SPECIES_HAUNTER,
      .moves = {MOVE_SHADOW_BALL, MOVE_PSYCHIC, MOVE_GIGA_DRAIN, MOVE_HYPNOSIS}, .nature = NATURE_MODEST, .gender = FEMALE },
    { .side = B_SIDE_OPPONENT, .level = 56, .species = SPECIES_ARBOK,
      .moves = {MOVE_SLUDGE_BOMB, MOVE_EARTHQUAKE, MOVE_IRON_TAIL, MOVE_GLARE}, .nature = NATURE_ADAMANT, .gender = FEMALE },
    { .side = B_SIDE_OPPONENT, .level = 58, .species = SPECIES_GENGAR,
      .moves = {MOVE_SHADOW_BALL, MOVE_PSYCHIC, MOVE_THUNDERBOLT, MOVE_HYPNOSIS}, .nature = NATURE_MODEST, .gender = FEMALE },
    {0xFF}
};

'''
        text = text[:idx] + parties + text[idx:]
        old = """    [TTVSCR_MATCHUPS] = sParties_Matchups,
    [TTVSCR_CATCHING] = sParties_Catching,
};
"""
        new = """    [TTVSCR_MATCHUPS]   = sParties_Matchups,
    [TTVSCR_CATCHING]   = sParties_Catching,
    [TTVSCR_OAK_AGATHA] = sParties_OakAgatha,
};
"""
        if old not in text:
            raise RuntimeError("Could not extend party pointer table")
        text = text.replace(old, new, 1)

    # Automatically choose the next living Pokémon in the watch-only 6v6,
    # instead of opening the player's party menu.
    old = """static void PokedudeHandleChoosePokemon(void)
{
    s32 i;

    gBattleControllerData[gActiveBattler] = CreateTask(TaskDummy, 0xFF);
"""
    new = """static void PokedudeHandleChoosePokemon(void)
{
    s32 i;

    if (gSpecialVar_0x8004 == TTVSCR_OAK_AGATHA)
    {
        struct Pokemon *party = GetBattlerSide(gActiveBattler) == B_SIDE_PLAYER ? gPlayerParty : gEnemyParty;
        for (i = 0; i < PARTY_SIZE; i++)
        {
            if (i != gBattlerPartyIndexes[gActiveBattler]
             && GetMonData(&party[i], MON_DATA_SPECIES) != SPECIES_NONE
             && GetMonData(&party[i], MON_DATA_HP) != 0)
            {
                BtlController_EmitChosenMonReturnValue(1, i, gBattlePartyCurrentOrder);
                PokedudeBufferExecCompleted();
                return;
            }
        }
        PokedudeBufferExecCompleted();
        return;
    }

    gBattleControllerData[gActiveBattler] = CreateTask(TaskDummy, 0xFF);
"""
    if old in text:
        text = text.replace(old, new, 1)
    elif "gSpecialVar_0x8004 == TTVSCR_OAK_AGATHA" not in text:
        raise RuntimeError("Could not add automatic archival switching")

    # Avoid the voiceover system indexing beyond its normal explanatory arrays.
    old = """static bool8 HandlePokedudeVoiceoverEtc(void)
{
    const struct PokedudeTextScriptHeader *header_p = sPokedudeTextScripts[gBattleStruct->pdScriptNum];
"""
    new = """static bool8 HandlePokedudeVoiceoverEtc(void)
{
    const struct PokedudeTextScriptHeader *header_p;

    if (gBattleStruct->pdScriptNum == TTVSCR_OAK_AGATHA)
        return FALSE;

    header_p = sPokedudeTextScripts[gBattleStruct->pdScriptNum];
"""
    if old in text:
        text = text.replace(old, new, 1)

    write(path, text)


def patch_historical_gengar_ability():
    path = "src/battle_script_commands.c"
    text = read(path)
    old = """    gBattleMons[gActiveBattler].ability = GetAbilityBySpecies(gBattleMons[gActiveBattler].species, gBattleMons[gActiveBattler].abilityNum);

    // check knocked off item
"""
    new = """    gBattleMons[gActiveBattler].ability = GetAbilityBySpecies(gBattleMons[gActiveBattler].species, gBattleMons[gActiveBattler].abilityNum);

    // In the Teachy TV archival battle only, Agatha's final Gengar predates
    // Levitate for story purposes so Samuel's Nidoking can finish it with Earthquake.
    if ((gBattleTypeFlags & BATTLE_TYPE_POKEDUDE)
     && gSpecialVar_0x8004 == TTVSCR_OAK_AGATHA
     && GetBattlerSide(gActiveBattler) == B_SIDE_OPPONENT
     && gBattleMons[gActiveBattler].species == SPECIES_GENGAR)
        gBattleMons[gActiveBattler].ability = ABILITY_NONE;

    // check knocked off item
"""
    if old in text:
        text = text.replace(old, new, 1)
    elif "Agatha's final Gengar predates" not in text:
        raise RuntimeError("Could not patch historical Gengar ability")
    write(path, text)


def main():
    patch_teachy_header()
    patch_strings()
    patch_teachy_menu_and_flow()
    patch_pokedude_history_battle()
    patch_historical_gengar_ability()
    print("FireRed Complete Teachy TV archival battle pass applied.")


if __name__ == "__main__":
    main()
