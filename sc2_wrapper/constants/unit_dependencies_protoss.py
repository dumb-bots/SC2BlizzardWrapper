from  constants.unit_type_ids import UnitTypeIds

UNIT_DEPENDENCIES = {
    # --------------------- PROTOSS ---------------------------
    # BUILDINGS -----------------------------------------------

    # No building required
    UnitTypeIds.PYLON.value: [[UnitTypeIds.PROBE.value]],
    UnitTypeIds.ASSIMILATOR.value: [[UnitTypeIds.PROBE.value]],
    UnitTypeIds.NEXUS.value: [[UnitTypeIds.PROBE.value]],

    # Nexus dependant
    UnitTypeIds.FORGE.value: [[UnitTypeIds.NEXUS.value, UnitTypeIds.PROBE.value]],
    UnitTypeIds.GATEWAY.value: [[UnitTypeIds.NEXUS.value, UnitTypeIds.PROBE.value]],

    # Forge dependent
    UnitTypeIds.PHOTONCANNON.value: [[UnitTypeIds.FORGE.value, UnitTypeIds.PROBE.value]],

    # Gateway dependent
    UnitTypeIds.CYBERNETICSCORE.value: [[UnitTypeIds.GATEWAY.value, UnitTypeIds.PROBE.value]],

    # Cybernetics core dependant
    UnitTypeIds.TWILIGHTCOUNCIL.value: [[UnitTypeIds.CYBERNETICSCORE.value, UnitTypeIds.PROBE.value]],
    UnitTypeIds.STARGATE.value: [[UnitTypeIds.CYBERNETICSCORE.value, UnitTypeIds.PROBE.value]],
    UnitTypeIds.ROBOTICSFACILITY.value: [[UnitTypeIds.CYBERNETICSCORE.value, UnitTypeIds.PROBE.value]],

    # Twilight council dependent
    UnitTypeIds.TEMPLARARCHIVE.value: [[UnitTypeIds.TWILIGHTCOUNCIL.value, UnitTypeIds.PROBE.value]],
    UnitTypeIds.DARKSHRINE.value: [[UnitTypeIds.TWILIGHTCOUNCIL.value, UnitTypeIds.PROBE.value]],

    # Stargate dependent
    UnitTypeIds.FLEETBEACON.value: [[UnitTypeIds.STARGATE.value, UnitTypeIds.PROBE.value]],

    # Robotics facility dependent
    UnitTypeIds.ROBOTICSBAY.value: [[UnitTypeIds.ROBOTICSFACILITY.value, UnitTypeIds.PROBE.value]],
    
    # UNITS ---------------------------------------------------
    # Workers
    UnitTypeIds.PROBE.value: [[UnitTypeIds.NEXUS.value]],

    # Gateway units
    UnitTypeIds.ZEALOT.value: [[UnitTypeIds.GATEWAY.value]],
  
    # Cybernetics core units
    UnitTypeIds.STALKER.value: [[UnitTypeIds.CYBERNETICSCORE.value]],
    UnitTypeIds.SENTRY.value: [[UnitTypeIds.CYBERNETICSCORE.value]],

    # Stargate units
    UnitTypeIds.PHOENIX.value: [[UnitTypeIds.STARGATE.value]],
    UnitTypeIds.VOIDRAY.value: [[UnitTypeIds.STARGATE.value]],

    # Robotics Facilty units
    UnitTypeIds.OBSERVER.value: [[UnitTypeIds.ROBOTICSFACILITY.value]],
    UnitTypeIds.WARPPRISM.value: [[UnitTypeIds.ROBOTICSFACILITY.value]],
    UnitTypeIds.IMMORTAL.value: [[UnitTypeIds.ROBOTICSFACILITY.value]],

    # Templar archives units
    UnitTypeIds.HIGHTEMPLAR.value: [[UnitTypeIds.TEMPLARARCHIVE.value]],
    UnitTypeIds.ARCHON.value: [[UnitTypeIds.TEMPLARARCHIVE.value]],

    # Dark shrine unit
    UnitTypeIds.DARKTEMPLAR.value: [[UnitTypeIds.DARKSHRINE.value]],

    # Fleet beacon units
    UnitTypeIds.CARRIER.value: [[UnitTypeIds.FLEETBEACON.value]],
    UnitTypeIds.MOTHERSHIP.value: [[UnitTypeIds.FLEETBEACON.value]],

    # Robotics bay unit
    UnitTypeIds.COLOSSUS.value: [[UnitTypeIds.ROBOTICSBAY.value]],

    # faltan ORACLE, MOTHERSHIPCORE, TEMPEST, ADEPT, DISRUPTOR
    UnitTypeIds.ORACLE.value: [[UnitTypeIds.STARGATE.value]],

    UnitTypeIds.MOTHERSHIPCORE.value: [[UnitTypeIds.NEXUS.value, UnitTypeIds.CYBERNETICSCORE.value]],

    UnitTypeIds.TEMPEST.value: [[UnitTypeIds.STARGATE.value, UnitTypeIds.FLEETBEACON.value]],

    UnitTypeIds.ADEPT.value: [[UnitTypeIds.GATEWAY.value, UnitTypeIds.CYBERNETICSCORE.value]],

    UnitTypeIds.DISRUPTOR.value: [[UnitTypeIds.ROBOTICSFACILITY.value, UnitTypeIds.ROBOTICSBAY.value]],
}
