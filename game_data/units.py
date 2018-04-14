import collections
from functools import reduce


class UnitManager(list):
    """ Collection of Units with filtering and updating tools for contained units """

    AND_MODE = 1
    OR_MODE = 2
    EXCLUDE_AND_MODE = 3
    EXCLUDE_OR_MODE = 4

    def __init__(self, units):
        super().__init__(units)

    def give_order(self, ability_id, orders_dict, target_unit=None, target_point=None):
        """ Assign units to perform an Ability (with a particular target or not)

        :param ability_id:      <int>    Ability identifier
        :param orders_dict:     <dict>   Orders dictionary from this game iteration, updated by reference
        :param target_unit:     <int>    (Optional) Targeted unit identifier
        :param target_point:    <tuple>  (Optional) 2D Point (x, y) with targeted coordinates for ability
        :return:    No return value, orders_dict updated by reference
        """
        tuple_key = (ability_id, target_unit, target_point)
        orders_dict.setdefault(tuple_key, []).extend(self.values("tag", flat_list=True))

    def values(self, *args, flat_list=False):
        """ Get tuples of values of the units inside the UnitManager.
                Can get a flat list of values in case it's one attribute and flat_list is set to True

        :param args:        <list>   Attributes specified to obtain from the UnitManager's units
        :param flat_list:   <bool>   Flag to get a flat list of attributes in case only one attribute is specified

        :return:            <list>   List of tuples with the attributes specified in the args / List of values in case
                                        on attribute specified and flat_list set to True
        """
        if flat_list and len(args) == 1:
            return [unit.get_values_attribute(args[0]) for unit in self]
        else:
            return [tuple(unit.get_values_attribute(arg) for arg in args) for unit in self]

    def filter(self, mode=AND_MODE, **kwargs):
        """ Return subgroup of UnitManager with the items matching the specified arguments for the selected mode

        :param mode:    <int>   Filtering mode:
                                    AND_MODE:           filter method returns all units matching all conditions
                                    OR_MODE:            filter method returns all units matching at least one of the
                                                            conditions
                                    EXCLUDE_AND_MODE:   filter method returns all the units not matching any of the
                                                            conditions
                                    EXCLUDE_OR_MODE:    filter method returns all the units not matching at least one
                                                            of the conditions
        :param kwargs:  <dict>  Filtering arguments, pairs <key: value> where the `key` is the selected attribute and
                                    `value` is the expected value for the attribute.
                                Examples:
                                    attribute: value    ->   Unit's `attribute` must match `value` exactly
                                    attribute__in: list ->   Unit's `attribute` must be inside `list`
                                    att1__att2: value   ->   Unit's `att1` is an object or list which should match
                                                                the given value

        :return:        <UnitManager> UnitManager with the subroup of selected units
        """

        def evaluate_attribute(unit, attribute, value):

            # Argument with operator
            if "__" in attribute:
                att_split = attribute.split("__")
                attribute, op = att_split[0], att_split[1]

                # In operator
                if op == "in":
                    unit_value = unit.get_attribute(attribute)
                    evaluation = unit_value in value

                # Composed attribute filter
                else:
                    unit_value = unit.get_attribute(attribute)
                    # If op attribute is "int" consider the list as a list of ints (for `attributes` list)
                    if op == "int":
                        evaluation = value in unit_value

                    elif op == "attlength":
                        evaluation = len(unit_value) == value

                    # If internal attribute is a list of objects, check if any matches the given condition
                    elif isinstance(unit_value, collections.Iterable):
                        try:
                            evaluation = list(filter(lambda obj: obj.__getattribute__(op) == value, unit_value))
                        except AttributeError:
                            evaluation = False

                    # If internal attribute is an object, check if it matches the given condition
                    else:
                        try:
                            evaluation = unit_value.__getattribute__(op) == value
                        except AttributeError:
                            evaluation = False

                # Return statement depending on mode
                return evaluation

            # Standard attribute filter
            else:
                unit_value = unit.get_attribute(attribute)
                return unit_value == value

        def filter_func(unit):
            """ Filter function with the given **kwargs according to specified mode

            :param unit:  <Unit>   Unit object from the Manager list to filter
            :return:      <bool>   Bool indicating if unit matches the conditions specified for the filter operation
            """

            try:
                and_func = lambda x, y: x and y
                or_func = lambda x, y: x or y

                if mode == UnitManager.AND_MODE:
                    return reduce(and_func, [evaluate_attribute(unit, attribute, value)
                                             for attribute, value in kwargs.items()])
                elif mode == UnitManager.OR_MODE:
                    func = lambda x, y: x or y
                    return reduce(or_func, [evaluate_attribute(unit, attribute, value)
                                            for attribute, value in kwargs.items()])
                elif mode == UnitManager.EXCLUDE_OR_MODE:
                    return reduce(and_func, [not(evaluate_attribute(unit, attribute, value))
                                             for attribute, value in kwargs.items()])
                elif mode == UnitManager.EXCLUDE_AND_MODE:
                    return reduce(or_func, [not(evaluate_attribute(unit, attribute, value))
                                            for attribute, value in kwargs.items()])
                return False
            except AttributeError:
                return False

        # Filter values with selected function according to mode
        return UnitManager(filter(filter_func, self))


class Unit:
    """ Game's unit representation, contains sc2-proto objects with its raw data and basic processing properties and
            functions.

        Raw data for `proto_unit` specified in (from https://github.com/Blizzard/s2client-proto/ raw.proto doc)
        Raw data for `proto_unit_data` specified in (from https://github.com/Blizzard/s2client-proto/ data.proto doc)

    """

    def __init__(self, proto_unit, game_data):
        self.proto_unit = proto_unit
        self.proto_unit_data = game_data.units[proto_unit.unit_type]

    @property
    def tag(self):
        return self.proto_unit.tag

    @property
    def name(self):
        return self.proto_unit_data.name

    @property
    def alliance(self):
        return self.proto_unit.alliance

    @property
    def owner(self):
        return self.proto_unit.owner

    @property
    def health(self):
        return self.proto_unit.health, self.proto_unit.health_max

    @property
    def shield(self):
        return self.proto_unit.shield, self.proto_unit.shield_max

    @property
    def energy(self):
        return self.proto_unit.energy, self.proto_unit.energy_max

    def __repr__(self):
        return "<Unit {} {}>".format(self.name, self.tag)

    def get_values_attribute(self, attribute):
        if "__" not in attribute:
            return self.get_attribute(attribute)
        else:
            attribute_elements = attribute.split("__")
            unit_attribute = self.get_attribute(attribute_elements[0])
            if isinstance(unit_attribute, collections.Iterable):
                return [elem.__getattribute__(attribute_elements[1]) for elem in unit_attribute]
            else:
                return unit_attribute.__getattribute__(attribute_elements[1])

    def get_attribute(self, attribute):
        try:
            return self.__getattribute__(attribute)
        except AttributeError:
            # Not directly related
            pass

        # Try internal objects
        try:
            return self.proto_unit.__getattribute__(attribute)
        except AttributeError:
            # If attribute not in internal proto_unit_data raise AttributeError
            return self.proto_unit_data.__getattribute__(attribute)

    def to_dict(self):
        return {
            "unit_type_name": self.name,
            "display_type": self.proto_unit.display_type,
            "alliance": self.proto_unit.alliance,
            "tag": self.proto_unit.tag,
            "unit_type": self.proto_unit.unit_type,
            "owner": self.proto_unit.owner,
            "pos": (self.proto_unit.pos.x, self.proto_unit.pos.y, self.proto_unit.pos.z),
            "facing": self.proto_unit.facing,
            "radius": self.proto_unit.radius,
            "build_progress": self.proto_unit.build_progress,
            "cloak": self.proto_unit.cloak,
            "is_selected": self.proto_unit.is_selected,
            "is_on_screen": self.proto_unit.is_on_screen,
            "is_blip": self.proto_unit.is_blip,
            "health": self.proto_unit.health,
            "health_max": self.proto_unit.health_max,
            "shield": self.proto_unit.shield,
            "energy": self.proto_unit.energy,
            "is_flying": self.proto_unit.is_flying,
            "is_burrowed": self.proto_unit.is_burrowed,
            "shield_max": self.proto_unit.shield_max,
            "energy_max": self.proto_unit.energy_max,
        }
