from constants.unit_type_ids import UnitTypeIds

UNIT_DEPENDENCIES = {
    # --------------------- ZERG ---------------------------
    # BUILDINGS -----------------------------------------------

    # No building required
    UnitTypeIds.EXTRACTOR.value: [[UnitTypeIds.DRONE.value]],
    UnitTypeIds.HATCHERY.value: [[UnitTypeIds.DRONE.value]],

    # Hatchery dependant
    UnitTypeIds.EVOLUTIONCHAMBER.value: [[UnitTypeIds.HATCHERY.value, UnitTypeIds.DRONE.value]],
    UnitTypeIds.SPAWNINGPOOL.value: [[UnitTypeIds.HATCHERY.value, UnitTypeIds.DRONE.value]],

    # Evolution chamber dependent
    UnitTypeIds.SPORECRAWLER.value: [[UnitTypeIds.EVOLUTIONCHAMBER.value, UnitTypeIds.DRONE.value]],

    # Spawning pool dependent
    UnitTypeIds.LAIR.value: [[UnitTypeIds.SPAWNINGPOOL.value, UnitTypeIds.DRONE.value]],
    UnitTypeIds.ROACHWARREN.value: [[UnitTypeIds.SPAWNINGPOOL.value, UnitTypeIds.DRONE.value]],
    UnitTypeIds.BANELINGNEST.value: [[UnitTypeIds.SPAWNINGPOOL.value, UnitTypeIds.DRONE.value]],
    UnitTypeIds.SPINECRAWLER.value: [[UnitTypeIds.SPAWNINGPOOL.value, UnitTypeIds.DRONE.value]],

    # Lair dependent
    UnitTypeIds.HYDRALISKDEN.value: [[UnitTypeIds.LAIR.value, UnitTypeIds.DRONE.value]],
    UnitTypeIds.INFESTATIONPIT.value: [[UnitTypeIds.LAIR.value, UnitTypeIds.DRONE.value]],
    UnitTypeIds.SPIRE.value: [[UnitTypeIds.LAIR.value, UnitTypeIds.DRONE.value]],
    UnitTypeIds.NYDUSNETWORK.value: [[UnitTypeIds.LAIR.value, UnitTypeIds.DRONE.value]],

    # Infestation pit dependent
    UnitTypeIds.HIVE.value: [[UnitTypeIds.INFESTATIONPIT.value, UnitTypeIds.DRONE.value]],

    # Factory dependent
    UnitTypeIds.ULTRALISKCAVERN.value: [[UnitTypeIds.HIVE.value, UnitTypeIds.DRONE.value]],
    UnitTypeIds.GREATERSPIRE.value: [[UnitTypeIds.HIVE.value, UnitTypeIds.DRONE.value]],

    # UNITS ---------------------------------------------------
    # Workers
    UnitTypeIds.DRONE.value: [[UnitTypeIds.HATCHERY.value]],

    UnitTypeIds.OVERLORD.value: [[UnitTypeIds.HATCHERY.value]],

    # Spawning pool units
    UnitTypeIds.ZERGLING.value: [[UnitTypeIds.SPAWNINGPOOL.value]], 
    UnitTypeIds.QUEEN.value: [[UnitTypeIds.SPAWNINGPOOL.value]],

    # Roach warren unit
    UnitTypeIds.ROACH.value: [[UnitTypeIds.ROACHWARREN.value]],

    # Baneling nest unit
    UnitTypeIds.BANELING.value: [[UnitTypeIds.BANELINGNEST.value]],

    # Hydralisk den unit
    UnitTypeIds.HYDRALISK.value: [[UnitTypeIds.HYDRALISKDEN.value]],

    # Infestation pit unit
    UnitTypeIds.INFESTOR.value: [[UnitTypeIds.INFESTATIONPIT.value]],

    # Spire unit
    UnitTypeIds.MUTALISK.value: [[UnitTypeIds.SPIRE.value]],
    UnitTypeIds.CORRUPTOR.value: [[UnitTypeIds.SPIRE.value]],

    # Nydus network unit
    #UnitTypeIds.NYDUSWORM.value: [[UnitTypeIds.NYDUSNETWORK.value]],

    # Ultralisk cavern unit
    UnitTypeIds.ULTRALISK.value: [[UnitTypeIds.ULTRALISKCAVERN.value]],

    # Greater spire unit
    UnitTypeIds.BROODLORD.value: [[UnitTypeIds.GREATERSPIRE.value]],

    # LARVA, BANELING, OVERSEER, NYDUS WORM, SWARM HOST, VIPER, RAVAGER, LURKER
    UnitTypeIds.LARVA.value: [[UnitTypeIds.HATCHERY.value]],

    UnitTypeIds.BANELING.value: [[UnitTypeIds.ZERGLING.value, UnitTypeIds.BANELINGNEST.value]],

    UnitTypeIds.OVERSEER.value: [[UnitTypeIds.OVERLORD.value, UnitTypeIds.LAIR.value]],

    UnitTypeIds.SWARMHOSTMP.value: [[UnitTypeIds.INFESTATIONPIT.value]],

    UnitTypeIds.VIPER.value: [[UnitTypeIds.HIVE.value]],

    UnitTypeIds.RAVAGER.valule: [[UnitTypeIds.ROACHWARREN.value]],

    UnitTypeIds.LURKER.value: [[UnitTypeIds.LURKERDENMP.value],[UnitTypeIds.LURKERDEN.value]],

    UnitTypeIds.LURKERMP.value: [[UnitTypeIds.LURKERDENMP.value],[UnitTypeIds.LURKERDEN.value]],
}
