from constants.unit_type_ids import UnitTypeIds

UNIT_DEPENDENCIES = {
    UnitTypeIds.MARINE.value: [[UnitTypeIds.BARRACKS.value], [UnitTypeIds.BARRACKSREACTOR.value],
                               [UnitTypeIds.BARRACKSTECHLAB.value]],
    UnitTypeIds.BARRACKS.value: [[UnitTypeIds.SUPPLYDEPOT.value, UnitTypeIds.SCV.value]],
    UnitTypeIds.SUPPLYDEPOT.value: [[UnitTypeIds.SCV.value]],
    UnitTypeIds.SCV.value: [[UnitTypeIds.COMMANDCENTER]]
}