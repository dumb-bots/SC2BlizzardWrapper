from constants.unit_type_ids import UnitTypeIds

UNIT_DEPENDENCIES = {
    # --------------------- TERRANS ---------------------------
    # BUILDINGS -----------------------------------------------

    # No building required
    UnitTypeIds.SUPPLYDEPOT.value: [[UnitTypeIds.SCV.value]],
    UnitTypeIds.REFINERY.value: [[UnitTypeIds.SCV.value]],
    UnitTypeIds.COMMANDCENTER.value: [[UnitTypeIds.SCV.value]],

    # Supply depot dependant
    UnitTypeIds.BARRACKS.value: [[UnitTypeIds.SUPPLYDEPOT.value, UnitTypeIds.SCV.value]],

    # Command center dependent
    UnitTypeIds.ENGINEERINGBAY.value: [[UnitTypeIds.COMMANDCENTER.value, UnitTypeIds.SCV.value],
                                       [UnitTypeIds.PLANETARYFORTRESS.value, UnitTypeIds.SCV.value],
                                       [UnitTypeIds.ORBITALCOMMAND.value, UnitTypeIds.SCV.value]],

    # Engineering bay dependent
    UnitTypeIds.MISSILETURRET.value: [[UnitTypeIds.ENGINEERINGBAY.value, UnitTypeIds.SCV.value]],
    UnitTypeIds.SENSORTOWER.value: [[UnitTypeIds.ENGINEERINGBAY.value, UnitTypeIds.SCV.value]],
    UnitTypeIds.PLANETARYFORTRESS.value: [[UnitTypeIds.COMMANDCENTER.value, UnitTypeIds.ENGINEERINGBAY.value]],

    # Barracks dependent
    UnitTypeIds.BARRACKSREACTOR.value: [[UnitTypeIds.BARRACKS.value]],
    UnitTypeIds.BARRACKSTECHLAB.value: [[UnitTypeIds.BARRACKS.value]],
    UnitTypeIds.BUNKER.value: [[UnitTypeIds.BARRACKS.value, UnitTypeIds.SCV.value]],
    UnitTypeIds.ORBITALCOMMAND.value: [[UnitTypeIds.COMMANDCENTER.value, UnitTypeIds.BARRACKS.value]],
    UnitTypeIds.FACTORY.value: [[UnitTypeIds.BARRACKS.value, UnitTypeIds.SCV.value]],
    UnitTypeIds.GHOSTACADEMY.value: [[UnitTypeIds.BARRACKS.value, UnitTypeIds.SCV.value]],

    # Factory dependent
    UnitTypeIds.STARPORT.value: [[UnitTypeIds.FACTORY.value, UnitTypeIds.SCV.value]],
    UnitTypeIds.ARMORY.value: [[UnitTypeIds.FACTORY.value, UnitTypeIds.SCV.value]],
    UnitTypeIds.FACTORYREACTOR.value: [[UnitTypeIds.FACTORY.value]],
    UnitTypeIds.FACTORYTECHLAB.value: [[UnitTypeIds.FACTORY.value]],

    # Starport dependent
    UnitTypeIds.FUSIONCORE.value: [[UnitTypeIds.STARPORT.value, UnitTypeIds.SCV.value]],
    UnitTypeIds.STARPORTREACTOR.value: [[UnitTypeIds.STARPORT.value]],
    UnitTypeIds.STARPORTTECHLAB.value: [[UnitTypeIds.STARPORT.value]],

    # UNITS ---------------------------------------------------
    # Workers
    UnitTypeIds.SCV.value: [[UnitTypeIds.COMMANDCENTER.value],
                           [UnitTypeIds.PLANETARYFORTRESS.value],
                           [UnitTypeIds.ORBITALCOMMAND.value]],

    # Barrack Units
    UnitTypeIds.MARINE.value: [[UnitTypeIds.BARRACKS.value], [UnitTypeIds.BARRACKSREACTOR.value],
                               [UnitTypeIds.BARRACKSTECHLAB.value]],
    UnitTypeIds.REAPER.value: [[UnitTypeIds.BARRACKS.value], [UnitTypeIds.BARRACKSREACTOR.value],
                               [UnitTypeIds.BARRACKSTECHLAB.value]],
    UnitTypeIds.MARAUDER.value: [[UnitTypeIds.BARRACKSTECHLAB.value]],
    UnitTypeIds.GHOST.value: [[UnitTypeIds.BARRACKSTECHLAB.value, UnitTypeIds.GHOSTACADEMY.value]],

    # Factory Units
    UnitTypeIds.HELLION.value: [[UnitTypeIds.FACTORY.value], [UnitTypeIds.FACTORYREACTOR.value],
                                [UnitTypeIds.FACTORYTECHLAB.value]],
    UnitTypeIds.WIDOWMINE.value: [[UnitTypeIds.FACTORY.value], [UnitTypeIds.FACTORYREACTOR.value],
                                  [UnitTypeIds.FACTORYTECHLAB.value]],
    UnitTypeIds.CYCLONE.value: [[UnitTypeIds.FACTORY.value], [UnitTypeIds.FACTORYREACTOR.value],
                                [UnitTypeIds.FACTORYTECHLAB.value]],
    UnitTypeIds.SIEGETANK.value: [[UnitTypeIds.FACTORYTECHLAB.value]],
    UnitTypeIds.THOR.value: [[UnitTypeIds.FACTORYTECHLAB.value, UnitTypeIds.ARMORY.value]],
    # # TODO: Check Hellbat ID
    # UnitTypeIds.HELLBAT.value: [[UnitTypeIds.FACTORY.value, UnitTypeIds.ARMORY.value],
    #                             [UnitTypeIds.FACTORYREACTOR.value, UnitTypeIds.ARMORY.value],
    #                             [UnitTypeIds.FACTORYTECHLAB.value, UnitTypeIds.ARMORY.value]],

    # Starport Units
    UnitTypeIds.VIKINGFIGHTER.value: [[UnitTypeIds.STARPORT.value], [UnitTypeIds.STARPORTREACTOR.value],
                                      [UnitTypeIds.STARPORTTECHLAB.value]],
    UnitTypeIds.MEDIVAC.value: [[UnitTypeIds.STARPORT.value], [UnitTypeIds.STARPORTREACTOR.value],
                                [UnitTypeIds.STARPORTTECHLAB.value]],
    UnitTypeIds.LIBERATOR.value: [[UnitTypeIds.STARPORT.value], [UnitTypeIds.STARPORTREACTOR.value],
                                  [UnitTypeIds.STARPORTTECHLAB.value]],
    UnitTypeIds.BANSHEE.value: [[UnitTypeIds.STARPORTTECHLAB.value]],
    UnitTypeIds.RAVEN.value: [[UnitTypeIds.STARPORTTECHLAB.value]],
    UnitTypeIds.BATTLECRUISER.value: [[UnitTypeIds.STARPORTTECHLAB.value, UnitTypeIds.FUSIONCORE.value]],
}
