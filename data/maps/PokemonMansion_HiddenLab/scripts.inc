PokemonMansion_HiddenLab_MapScripts::
	.byte 0

PokemonMansion_HiddenLab_EventScript_FinalJournal::
	msgbox PokemonMansion_HiddenLab_Text_FinalJournal, MSGBOX_SIGN
	end

PokemonMansion_HiddenLab_EventScript_Mew::
	goto_if_questlog EventScript_ReleaseEnd
	special QuestLog_CutRecording
	lock
	faceplayer
	waitse
	playmoncry SPECIES_MEW, CRY_MODE_ENCOUNTER
	message PokemonMansion_HiddenLab_Text_Mew
	waitmessage
	waitmoncry
	delay 20
	playbgm MUS_ENCOUNTER_GYM_LEADER, 0
	waitbuttonpress
	setwildbattle SPECIES_MEW, 50
	setflag FLAG_SYS_SPECIAL_WILD_BATTLE
	special StartLegendaryBattle
	waitstate
	clearflag FLAG_SYS_SPECIAL_WILD_BATTLE
	specialvar VAR_RESULT, GetBattleOutcome
	goto_if_eq VAR_RESULT, B_OUTCOME_CAUGHT, PokemonMansion_HiddenLab_EventScript_CaughtMew
	goto_if_eq VAR_RESULT, B_OUTCOME_WON, PokemonMansion_HiddenLab_EventScript_DefeatedMew
	release
	end

PokemonMansion_HiddenLab_EventScript_CaughtMew::
	setflag FLAG_FRC_MEW_CAUGHT
	removeobject LOCALID_HIDDEN_LAB_MEW
	release
	end

@ If Mew is knocked out it disappears for the current visit only. Because the
@ persistent caught flag is not set, leaving and re-entering the room respawns it.
PokemonMansion_HiddenLab_EventScript_DefeatedMew::
	removeobject LOCALID_HIDDEN_LAB_MEW
	release
	end
