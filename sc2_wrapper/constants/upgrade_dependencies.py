from sc2_wrapper.constants.upgrade_ids import UpgradeIds
from sc2_wrapper.constants.unit_type_ids import UnitTypeIds


UPGRADE_DEPENDENCIES = {
    # --------------------- TERRANS ---------------------------
    # Engineering bay upgrades
    UpgradeIds.TERRANINFANTRYWEAPONSLEVEL1.value: {
        'upgrade': None,
        'buildings': [
            UnitTypeIds.ENGINEERINGBAY.value,
        ]
    },
    UpgradeIds.TERRANINFANTRYWEAPONSLEVEL2.value: {
        'upgrade': UpgradeIds.TERRANINFANTRYWEAPONSLEVEL1.value,
        'buildings': [
            UnitTypeIds.ARMORY.value,
            UnitTypeIds.ENGINEERINGBAY.value,
        ]
    },
    UpgradeIds.TERRANINFANTRYWEAPONSLEVEL3.value: {
        'upgrade': UpgradeIds.TERRANINFANTRYWEAPONSLEVEL2.value,
        'buildings': [
            UnitTypeIds.ARMORY.value,
            UnitTypeIds.ENGINEERINGBAY.value,
        ]
    },

    UpgradeIds.TERRANINFANTRYARMORSLEVEL1.value: {
        'upgrade': None,
        'buildings': [
            UnitTypeIds.ENGINEERINGBAY.value,
        ]
    },
    UpgradeIds.TERRANINFANTRYARMORSLEVEL2.value: {
        'upgrade': UpgradeIds.TERRANINFANTRYARMORSLEVEL1.value,
        'buildings': [
            UnitTypeIds.ARMORY.value,
            UnitTypeIds.ENGINEERINGBAY.value,
        ]
    },
    UpgradeIds.TERRANINFANTRYARMORSLEVEL3.value: {
        'upgrade': UpgradeIds.TERRANINFANTRYARMORSLEVEL2.value,
        'buildings': [
            UnitTypeIds.ARMORY.value,
            UnitTypeIds.ENGINEERINGBAY.value,
        ]
    },
    UpgradeIds.HISECAUTOTRACKING.value: {
        'upgrade': None,
        'buildings': [
            UnitTypeIds.ENGINEERINGBAY.value,
        ]
    },
    UpgradeIds.TERRANBUILDINGARMOR.value: {
        'upgrade': None,
        'buildings': [
            UnitTypeIds.ENGINEERINGBAY.value,
        ]
    },
    UpgradeIds.NEOSTEELFRAME.value: {
        'upgrade': None,
        'buildings': [
            UnitTypeIds.ENGINEERINGBAY.value,
        ]
    },

    # Armory upgrades
    UpgradeIds.TERRANVEHICLEWEAPONSLEVEL1.value: {
        'upgrade': None,
        'buildings': [
            UnitTypeIds.ARMORY.value,
        ]
    },
    UpgradeIds.TERRANVEHICLEWEAPONSLEVEL2.value: {
        'upgrade': UpgradeIds.TERRANVEHICLEWEAPONSLEVEL1.value,
        'buildings': [
            UnitTypeIds.ARMORY.value,
        ]
    },
    UpgradeIds.TERRANVEHICLEWEAPONSLEVEL3.value: {
        'upgrade': UpgradeIds.TERRANVEHICLEWEAPONSLEVEL2.value,
        'buildings': [
            UnitTypeIds.ARMORY.value,
        ]
    },

    UpgradeIds.TERRANVEHICLEARMORSLEVEL1.value: {
        'upgrade': None,
        'buildings': [
            UnitTypeIds.ARMORY.value,
        ]
    },
    UpgradeIds.TERRANVEHICLEARMORSLEVEL2.value: {
        'upgrade': UpgradeIds.TERRANVEHICLEARMORSLEVEL1.value,
        'buildings': [
            UnitTypeIds.ARMORY.value,
        ]
    },
    UpgradeIds.TERRANVEHICLEARMORSLEVEL3.value: {
        'upgrade': UpgradeIds.TERRANVEHICLEARMORSLEVEL2.value,
        'buildings': [
            UnitTypeIds.ARMORY.value,
        ]
    },
    UpgradeIds.TERRANSHIPWEAPONSLEVEL1.value: {
        'upgrade': None,
        'buildings': [
            UnitTypeIds.ARMORY.value,
        ]
    },
    UpgradeIds.TERRANSHIPWEAPONSLEVEL2.value: {
        'upgrade': UpgradeIds.TERRANSHIPWEAPONSLEVEL1.value,
        'buildings': [
            UnitTypeIds.ARMORY.value,
        ]
    },
    UpgradeIds.TERRANSHIPWEAPONSLEVEL3.value: {
        'upgrade': UpgradeIds.TERRANSHIPWEAPONSLEVEL2.value,
        'buildings': [
            UnitTypeIds.ARMORY.value,
        ]
    },

    UpgradeIds.TERRANSHIPARMORSLEVEL1.value: {
        'upgrade': None,
        'buildings': [
            UnitTypeIds.ARMORY.value,
        ]
    },
    UpgradeIds.TERRANSHIPARMORSLEVEL2.value: {
        'upgrade': UpgradeIds.TERRANSHIPARMORSLEVEL1.value,
        'buildings': [
            UnitTypeIds.ARMORY.value,
        ]
    },
    UpgradeIds.TERRANSHIPARMORSLEVEL3.value: {
        'upgrade': UpgradeIds.TERRANSHIPARMORSLEVEL2.value,
        'buildings': [
            UnitTypeIds.ARMORY.value,
        ]
    },

    UpgradeIds.TERRANVEHICLEANDSHIPARMORSLEVEL1.value: {
        'upgrade': None,
        'buildings': [
            UnitTypeIds.ARMORY.value,
        ]
    },
    UpgradeIds.TERRANVEHICLEANDSHIPARMORSLEVEL2.value: {
        'upgrade': UpgradeIds.TERRANVEHICLEANDSHIPARMORSLEVEL1.value,
        'buildings': [
            UnitTypeIds.ARMORY.value,
        ]
    },
    UpgradeIds.TERRANVEHICLEANDSHIPARMORSLEVEL3.value: {
        'upgrade': UpgradeIds.TERRANVEHICLEANDSHIPARMORSLEVEL2.value,
        'buildings': [
            UnitTypeIds.ARMORY.value,
        ]
    },
    UpgradeIds.TERRANVEHICLEANDSHIPWEAPONSLEVEL1.value: {
        'upgrade': None,
        'buildings': [
            UnitTypeIds.ARMORY.value,
        ]
    },
    UpgradeIds.TERRANVEHICLEANDSHIPWEAPONSLEVEL2.value: {
        'upgrade': UpgradeIds.TERRANVEHICLEANDSHIPWEAPONSLEVEL1.value,
        'buildings': [
            UnitTypeIds.ARMORY.value,
        ]
    },
    UpgradeIds.TERRANVEHICLEANDSHIPWEAPONSLEVEL3.value: {
        'upgrade': UpgradeIds.TERRANVEHICLEANDSHIPWEAPONSLEVEL2.value,
        'buildings': [
            UnitTypeIds.ARMORY.value,
        ]
    },
    # Barrack tech lab upgrades
    UpgradeIds.STIMPACK.value: {
        'upgrade': None,
        'buildings': [
            UnitTypeIds.BARRACKSTECHLAB.value,
        ]
    },
    UpgradeIds.SHIELDWALL.value: {
        'upgrade': None,
        'buildings': [
            UnitTypeIds.BARRACKSTECHLAB.value,
        ]
    },
    UpgradeIds.PUNISHERGRENADES.value: {
        'upgrade': None,
        'buildings': [
            UnitTypeIds.BARRACKSTECHLAB.value,
        ]
    },
    UpgradeIds.REAPERSPEED.value: {
        'upgrade': None,
        'buildings': [
            UnitTypeIds.BARRACKSTECHLAB.value,
        ]
    },

    # Factory tech lab upgrades
    UpgradeIds.DRILLCLAWS.value: {
        'upgrade': None,
        'buildings': [
            UnitTypeIds.FACTORYTECHLAB.value,
        ]
    },
    UpgradeIds.INFERNALPREIGNITERS.value: {
        'upgrade': None,
        'buildings': [
            UnitTypeIds.FACTORYTECHLAB.value,
        ]
    },
    UpgradeIds.TRANSFORMATIONSERVOS.value: {
        'upgrade': None,
        'buildings': [
            UnitTypeIds.FACTORYTECHLAB.value,
        ]
    },

    # Starport tech lag upgrades
    UpgradeIds.BANSHEECLOAK.value: {
        'upgrade': None,
        'buildings': [
            UnitTypeIds.STARPORTTECHLAB.value,
        ]
    },
    UpgradeIds.RAVENCORVIDREACTOR.value: {
        'upgrade': None,
        'buildings': [
            UnitTypeIds.STARPORTTECHLAB.value,
        ]
    },
    UpgradeIds.MEDIVACCADUCEUSREACTOR.value: {
        'upgrade': None,
        'buildings': [
            UnitTypeIds.STARPORTTECHLAB.value,
        ]
    },
    UpgradeIds.DURABLEMATERIALS.value: {
        'upgrade': None,
        'buildings': [
            UnitTypeIds.STARPORTTECHLAB.value,
        ]
    },
    UpgradeIds.LIBERATORAGRANGEUPGRADE.value: {
        'upgrade': None,
        'buildings': [
            UnitTypeIds.FUSIONCORE.value,
            UnitTypeIds.STARPORTTECHLAB.value,
        ]
    },
    UpgradeIds.BANSHEESPEED.value: {
        'upgrade': None,
        'buildings': [
            UnitTypeIds.STARPORTTECHLAB.value,
        ]
    },

    # Ghost academy upgrades
    UpgradeIds.PERSONALCLOAKING.value: {
        'upgrade': None,
        'buildings': [
            UnitTypeIds.GHOSTACADEMY.value,
        ]
    },
    UpgradeIds.GHOSTMOEBIUSREACTOR.value: {
        'upgrade': None,
        'buildings': [
            UnitTypeIds.GHOSTACADEMY.value,
        ]
    },

    # Fusion core upgrades
    UpgradeIds.BATTLECRUISERBEHEMOTHREACTOR.value: {
        'upgrade': None,
        'buildings': [
            UnitTypeIds.FUSIONCORE.value,
        ]
    },
    UpgradeIds.BATTLECRUISERENABLESPECIALIZATIONS.value: {
        'upgrade': None,
        'buildings': [
            UnitTypeIds.FUSIONCORE.value,
        ]
    },
}