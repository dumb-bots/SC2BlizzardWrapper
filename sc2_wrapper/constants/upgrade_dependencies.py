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
}