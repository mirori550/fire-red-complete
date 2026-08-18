#!/usr/bin/env python3
"""Add a playable young Samuel Oak vs. Agatha flashback to the Teachy TV.

The player temporarily controls Samuel's six-Pokemon party in a normal FireRed
trainer battle. The real player party is restored when the flashback ends.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def write(path, text):
    p = ROOT / path
    if p.read_text(encoding="utf-8") != text:
        p.write_text(text, encoding="utf-8")


def patch_header():
    path = "include/teachy_tv.h"
    text = read(path)
    old = """    TTVSCR_TMS,\n    TTVSCR_REGISTER\n};\n"""
    new = """    TTVSCR_TMS,\n    TTVSCR_REGISTER,\n    TTVSCR_OAK_AGATHA\n};\n"""
    if old in text:
        text = text.replace(old, new, 1)
    elif "TTVSCR_OAK_AGATHA" not in text:
        raise RuntimeError("Could not extend Teachy TV enum")
    write(path, text)


def patch_strings():
    path = "src/data/text/teachy_tv.h"
    text = read(path)
    if "gTeachyTvString_OakAgathaBattle" not in text:
        marker = 'const u8 gTeachyTvString_Cancel[] = _("CANCEL");\n'
        extra = r'''const u8 gTeachyTvString_OakAgathaBattle[] = _("Agatha vs. Oak Battle");
const u8 gTeachyTvText_OakAgathaScript1[] = _(
    "ARCHIVE FOOTAGE - KANTO LEAGUE\p"
    "You will play as a young SAMUEL OAK.\p"
    "AGATHA: Sammy, good to see you\n"
    "became CHAMPION.\p"
    "Too bad you're too late! I already\n"
    "became CHAMPION a few minutes ago!\p"
    "Their final battle begins...");
const u8 gTeachyTvText_OakAgathaScript2[] = _(
    "The archived battle has ended.\p"
    "History remembers this as SAMUEL\n"
    "OAK's final victory over AGATHA.\p"
    "ARCHIVE FOOTAGE ENDS.");
'''
        if marker not in text:
            raise RuntimeError("Teachy TV text insertion point not found")
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
            raise RuntimeError("strings.h insertion point not found")
        text = text.replace(marker, marker + extra, 1)
    write(path, text)


def patch_teachy_tv():
    path = "src/teachy_tv.c"
    text = read(path)

    if ".label = gTeachyTvString_OakAgathaBattle" not in text:
        cancel = """    {\n        .label = gTeachyTvString_Cancel,\n        .index = -2\n    },\n"""
        entry = """    {\n        .label = gTeachyTvString_OakAgathaBattle,\n        .index = TTVSCR_OAK_AGATHA\n    },\n"""
        text = text.replace(cancel, entry + cancel, 2)
        text = text.replace(".totalItems = 7,\n    .maxShowed = 6,", ".totalItems = 8,\n    .maxShowed = 6,", 1)
        text = text.replace(
            "gMultiuseListMenuTemplate.totalItems = 5;\n        gMultiuseListMenuTemplate.maxShowed = 5;",
            "gMultiuseListMenuTemplate.totalItems = 6;\n        gMultiuseListMenuTemplate.maxShowed = 6;",
            1,
        )

    marker = "static void TTVcmd_TaskBattleOrFadeByOptionChosen(u8 taskId);\n"
    decls = (
        "static void TTVcmd_OakAgathaArchiveIntro(u8 taskId);\n"
        "static void SetupPlayableOakAgathaBattle(void);\n"
    )
    if "static void SetupPlayableOakAgathaBattle(void);" not in text:
        if marker not in text:
            raise RuntimeError("Teachy TV declaration point not found")
        text = text.replace(marker, marker + decls, 1)

    if "sOakAgathaScript[]" not in text:
        marker = "static void (* const sRegisterKeyItemScript[])(u8) = \n{"
        idx = text.find(marker)
        if idx < 0:
            raise RuntimeError("Register script array not found")
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

    old = """            sTMsScript,\n            sRegisterKeyItemScript,\n        };\n"""
    new = """            sTMsScript,\n            sRegisterKeyItemScript,\n            sOakAgathaScript,\n        };\n"""
    if old in text:
        text = text.replace(old, new, 1)

    old = """        gTeachyTvText_TMsScript1,\n        gTeachyTvText_RegisterScript1,\n    };\n"""
    new = """        gTeachyTvText_TMsScript1,\n        gTeachyTvText_RegisterScript1,\n        gTeachyTvText_OakAgathaScript1,\n    };\n"""
    if old in text:
        text = text.replace(old, new, 1)
    old = """        gTeachyTvText_TMsScript2,\n        gTeachyTvText_RegisterScript2,\n    };\n"""
    new = """        gTeachyTvText_TMsScript2,\n        gTeachyTvText_RegisterScript2,\n        gTeachyTvText_OakAgathaScript2,\n    };\n"""
    if old in text:
        text = text.replace(old, new, 1)

    old = """static const u8 sWhereToReturnToFromBattle[] = \n{\n    12,\n    12,\n    12,\n    12,\n     9,\n     9\n};\n"""
    new = """static const u8 sWhereToReturnToFromBattle[] = \n{\n    12,\n    12,\n    12,\n    12,\n     9,\n     9,\n     4\n};\n"""
    if old in text:
        text = text.replace(old, new, 1)

    setup_marker = """    case TTVSCR_TMS:\n    case TTVSCR_REGISTER:\n        TeachyTvSetSpriteCoordsAndSwitchFrame(data[1], 0x78, 0x38, 0);\n        break;\n"""
    if "case TTVSCR_OAK_AGATHA:\n        break;" not in text and setup_marker in text:
        text = text.replace(setup_marker, setup_marker + "    case TTVSCR_OAK_AGATHA:\n        break;\n", 1)

    old = """    case TTVSCR_CATCHING:\n        TeachyTvPrepBattle(taskId);\n        break;\n"""
    new = """    case TTVSCR_CATCHING:\n    case TTVSCR_OAK_AGATHA:\n        TeachyTvPrepBattle(taskId);\n        break;\n"""
    if old in text:
        text = text.replace(old, new, 1)

    old = """    SavePlayerParty();\n    InitPokedudePartyAndOpponent();\n    PlayMapChosenOrBattleBGM(MUS_DUMMY);\n"""
    new = """    SavePlayerParty();\n    if (sStaticResources.whichScript == TTVSCR_OAK_AGATHA)\n        SetupPlayableOakAgathaBattle();\n    else\n        InitPokedudePartyAndOpponent();\n    PlayMapChosenOrBattleBGM(MUS_DUMMY);\n"""
    if old in text:
        text = text.replace(old, new, 1)

    old = """    if (sStaticResources.whichScript == TTVSCR_BATTLE)\n        data[6] = B_TRANSITION_WHITE_BARS_FADE;\n    else\n        data[6] = B_TRANSITION_SLICE;\n"""
    new = """    if (sStaticResources.whichScript == TTVSCR_BATTLE || sStaticResources.whichScript == TTVSCR_OAK_AGATHA)\n        data[6] = B_TRANSITION_WHITE_BARS_FADE;\n    else\n        data[6] = B_TRANSITION_SLICE;\n"""
    if old in text:
        text = text.replace(old, new, 1)

    if "static void SetupPlayableOakAgathaBattle(void)\n{" not in text:
        marker = "static void TeachyTvPreBattleAnimAndSetBattleCallback(u8 taskId)\n{"
        idx = text.find(marker)
        if idx < 0:
            raise RuntimeError("Could not insert playable flashback setup")
        helper = r'''
static void SetArchiveMon(struct Pokemon *mon, u16 species, u8 level, const u16 moves[MAX_MON_MOVES])
{
    u8 i;
    CreateMon(mon, species, level, USE_RANDOM_IVS, FALSE, 0, OT_ID_PLAYER_ID, 0);
    for (i = 0; i < MAX_MON_MOVES; i++)
        SetMonMoveSlot(mon, moves[i], i);
}

static void SetupPlayableOakAgathaBattle(void)
{
    static const u16 oakMoves[PARTY_SIZE][MAX_MON_MOVES] =
    {
        { MOVE_TAKE_DOWN, MOVE_EARTHQUAKE, MOVE_SURF, MOVE_REST },
        { MOVE_HYDRO_PUMP, MOVE_FOCUS_PUNCH, MOVE_BLIZZARD, MOVE_TOXIC },
        { MOVE_HYPER_BEAM, MOVE_SHADOW_BALL, MOVE_SLUDGE_BOMB, MOVE_REST },
        { MOVE_TRANSFORM, MOVE_NONE, MOVE_NONE, MOVE_NONE },
        { MOVE_HYPER_BEAM, MOVE_SOLAR_BEAM, MOVE_REST, MOVE_SHADOW_BALL },
        { MOVE_FOCUS_PUNCH, MOVE_EARTHQUAKE, MOVE_HYPER_BEAM, MOVE_TOXIC },
    };
    static const u16 agathaMoves[PARTY_SIZE][MAX_MON_MOVES] =
    {
        { MOVE_SLUDGE_BOMB, MOVE_SOLAR_BEAM, MOVE_SECRET_POWER, MOVE_TOXIC },
        { MOVE_SLUDGE_BOMB, MOVE_BRICK_BREAK, MOVE_GIGA_DRAIN, MOVE_ACID_ARMOR },
        { MOVE_AERIAL_ACE, MOVE_SHADOW_BALL, MOVE_STEEL_WING, MOVE_CONFUSE_RAY },
        { MOVE_SHADOW_BALL, MOVE_PSYCHIC, MOVE_GIGA_DRAIN, MOVE_HYPNOSIS },
        { MOVE_SLUDGE_BOMB, MOVE_EARTHQUAKE, MOVE_IRON_TAIL, MOVE_GLARE },
        { MOVE_SHADOW_BALL, MOVE_PSYCHIC, MOVE_THUNDERBOLT, MOVE_HYPNOSIS },
    };
    static const u16 oakSpecies[PARTY_SIZE] =
    {
        SPECIES_TAUROS, SPECIES_POLIWRATH, SPECIES_GENGAR,
        SPECIES_DITTO, SPECIES_SNORLAX, SPECIES_NIDOKING
    };
    static const u16 agathaSpecies[PARTY_SIZE] =
    {
        SPECIES_VICTREEBEL, SPECIES_MUK, SPECIES_GOLBAT,
        SPECIES_HAUNTER, SPECIES_ARBOK, SPECIES_GENGAR
    };
    static const u8 levels[PARTY_SIZE] = {53, 54, 54, 53, 56, 58};
    u8 i;

    ZeroPlayerPartyMons();
    ZeroEnemyPartyMons();
    for (i = 0; i < PARTY_SIZE; i++)
    {
        SetArchiveMon(&gPlayerParty[i], oakSpecies[i], levels[i], oakMoves[i]);
        SetArchiveMon(&gEnemyParty[i], agathaSpecies[i], levels[i], agathaMoves[i]);
    }

    gTrainerBattleOpponent_A = TRAINER_ELITE_FOUR_AGATHA;
    gBattleTypeFlags = BATTLE_TYPE_TRAINER;
}

'''
        text = text[:idx] + helper + text[idx:]

    write(path, text)


def patch_historical_gengar():
    path = "src/battle_script_commands.c"
    text = read(path)
    if '#include "teachy_tv.h"' not in text:
        marker = '#include "battle_scripts.h"\n'
        if marker in text:
            text = text.replace(marker, marker + '#include "teachy_tv.h"\n', 1)

    old = """    gBattleMons[gActiveBattler].ability = GetAbilityBySpecies(gBattleMons[gActiveBattler].species, gBattleMons[gActiveBattler].abilityNum);\n"""
    new = old + """    if (gSpecialVar_0x8004 == TTVSCR_OAK_AGATHA\n        && GetBattlerSide(gActiveBattler) == B_SIDE_OPPONENT\n        && gBattleMons[gActiveBattler].species == SPECIES_GENGAR)\n        gBattleMons[gActiveBattler].ability = ABILITY_NONE;\n"""
    if new not in text:
        if old not in text:
            raise RuntimeError("Could not patch historical Gengar ability")
        text = text.replace(old, new, 1)
    write(path, text)


def main():
    patch_header()
    patch_strings()
    patch_teachy_tv()
    patch_historical_gengar()
    print("Applied playable Oak vs Agatha Teachy TV flashback")


if __name__ == "__main__":
    main()
