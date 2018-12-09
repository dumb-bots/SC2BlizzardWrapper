import collections
from functools import reduce

from s2clientprotocol.common_pb2 import Point2D
from s2clientprotocol.raw_pb2 import ActionRawUnitCommand, ActionRaw
from s2clientprotocol.sc2api_pb2 import Action, RequestAction, Request, Response

from sc2_wrapper.api_wrapper.utils import HARVESTING_ORDERS
from sc2_wrapper.game_data import euclidean_distance


class UnitManager(list):
    """ Collection of Units with filtering and updating tools for contained units """

    AND_MODE = 1
    OR_MODE = 2
    EXCLUDE_AND_MODE = 3
    EXCLUDE_OR_MODE = 4

    def __init__(self, units):
        super().__init__(units)

    def __add__(self, manager):
        if not isinstance(manager, UnitManager):
            raise TypeError("Invalid type for UnitManager sum")
        return UnitManager(super(UnitManager, self).__add__(manager))

    def __getitem__(self, key):
        super_value = super(UnitManager, self).__getitem__(key)
        if isinstance(key, slice):
            return UnitManager(super_value)
        else:
            return super_value

    async def give_order(self, ws, ability_id, target_unit=None, target_point=None, queue_command=False):
        """ Assign units to perform an Ability (with a particular target or not)

        :param ability_id:      <int>    Ability identifier
        :param target_unit:     <int>    (Optional) Targeted unit identifier
        :param target_point:    <tuple>  (Optional) 2D Point (x, y) with targeted coordinates for ability
        :param queue_command:   <bool>   (Optional) Flag allowing to put orders in queue if units have orders
                                            default False
        :return:    No return value, orders_dict updated by reference
        """
        if target_unit is None and target_point is None:
            command = ActionRawUnitCommand(ability_id=ability_id, unit_tags=self.values('tag', flat_list=True))
        elif target_point is not None:
            command = ActionRawUnitCommand(ability_id=ability_id, target_world_space_pos=Point2D(x=target_point[0],
                                                                                                 y=target_point[1]),
                                           unit_tags=self.values('tag', flat_list=True))
        else:
            command = ActionRawUnitCommand(ability_id=ability_id, target_unit_tag=target_unit.tag,
                                           unit_tags=self.values('tag', flat_list=True))
        request = Request(action=RequestAction(actions=[Action(action_raw=ActionRaw(
            unit_command=command))]))
        await ws.send(request.SerializeToString())
        result = await ws.recv()
        result = Response.FromString(result)
        return result

    def add_calculated_values(self, **kwargs):
        """ Add unit methods calculation to Units `extra_info`
                NOTE: To access the internally calculated attributes the key is
                      `last_methodname` and the value returned will be the last value obtained from that method

        :param kwargs:  <dict>  <method_name, method_args> Methods to calculate and corresponding arguments
        :return:        No return value, units updated by reference
        """
        for method, args in kwargs.items():
            for unit in self:
                unit.extra_info_method(method, args)
        return self

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
                # Lower or equal than operator
                elif op == "lte":
                    unit_value = unit.get_attribute(attribute)
                    evaluation = unit_value <= value
                # Greater or equal than operator
                elif op == "gte":
                    unit_value = unit.get_attribute(attribute)
                    evaluation = unit_value >= value
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
                if mode == UnitManager.AND_MODE:
                    return reduce(lambda x, y: x and y, [evaluate_attribute(unit, attribute, value)
                                                         for attribute, value in kwargs.items()])
                elif mode == UnitManager.OR_MODE:
                    return reduce(lambda x, y: x or y, [evaluate_attribute(unit, attribute, value)
                                                        for attribute, value in kwargs.items()])
                elif mode == UnitManager.EXCLUDE_OR_MODE:
                    return reduce(lambda x, y: x and y, [not(evaluate_attribute(unit, attribute, value))
                                                         for attribute, value in kwargs.items()])
                elif mode == UnitManager.EXCLUDE_AND_MODE:
                    return reduce(lambda x, y: x or y, [not(evaluate_attribute(unit, attribute, value))
                                                        for attribute, value in kwargs.items()])
                return False
            except AttributeError:
                return False

        # Filter values with selected function according to mode
        return UnitManager(filter(filter_func, self))

    def sort_by(self, *attributes, reverse=False):
        """ Returned a UnitManager with units sorted by the given attributes

        :param attributes: <list>  Names of the attributes to sort by
        :param reverse:    <bool>  Determine if the list should be sorted in reverse order, default False

        :return:           <UnitManager>  Unit Manager with same units as `self` but sorted by `attributes`
        """
        return UnitManager(sorted(self, key=lambda unit: [unit.get_attribute(attribute) for attribute in attributes],
                                  reverse=reverse))


class Unit:
    """ Game's unit representation, contains sc2-proto objects with its raw data and basic processing properties and
            functions.

        Raw data for `proto_unit` specified in (from https://github.com/Blizzard/s2client-proto/ raw.proto doc)
        Raw data for `proto_unit_data` specified in (from https://github.com/Blizzard/s2client-proto/ data.proto doc)

    """

    def __init__(self, proto_unit, game_data):
        self.proto_unit = proto_unit
        self.proto_unit_data = None
        for data in game_data.units:
            if data.unit_id == proto_unit.unit_type:
                self.proto_unit_data = data
                break
        self.extra_info = {}

    def __repr__(self):
        return "<Unit {} {}>".format(self.name, self.tag)

    def __getattribute__(self, attribute):
        try:
            return super(Unit, self).__getattribute__(attribute)
        except AttributeError:
            # Not directly related
            pass

        # Try internal objects
        try:
            return self.proto_unit.__getattribute__(attribute)
        except AttributeError:
            # Not in proto's unit
            pass

        # Try unit data information
        try:
            # If attribute not in internal proto_unit_data raise AttributeError
            return self.proto_unit_data.__getattribute__(attribute)
        except AttributeError:
            # Not in proto's unit data
            pass

        # Check extra calculated info
        try:
            return self.extra_info[attribute]
        except KeyError:
            raise AttributeError("Unit has no attribute {}".format(attribute))

    @property
    def tag(self):
        return self.proto_unit.tag

    @property
    def name(self):
        if self.proto_unit_data:
            return self.proto_unit_data.name
        else:
            return None

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

    @property
    def display(self):
        return self.proto_unit.display_type

    def extra_info_method(self, method, method_kwargs):
        """ Set an internal method execution's result as extra info for manager's queries
            NOTE: To access the internally calculated attributes the key is
                      `last_methodname` and the value returned will be the last value obtained from that method

        :param method:          <str>   Name of the method called
        :param method_kwargs:   <dict>  Keyword arguments of method called
        :return:                No return value, unit's extra_info updated
        """
        try:
            method_result = self.__getattribute__(method)(**method_kwargs)
            self.extra_info["last_" + method] = method_result
        except AttributeError:
            return

    def distance_to(self, unit=None, pos=None, distance_calc=None):
        """ Calculate unit's distance to target unit/point in the map

        :param unit:            <Unit>      Another unit in the map
        :param pos:             <tuple>     Point in the map (x,y,z)
        :param distance_calc:   <function>  Function to use to calculate distance, if not provided, uses euclidean dist

        :return:                <float>     Distance to target
        """
        position = []

        if unit is not None:
            pos = unit.get_attribute("pos")

        if distance_calc is None:
            distance_calc = euclidean_distance

        # Define position dimensions
        if pos is not None and not(isinstance(pos, tuple) or isinstance(pos, list)):
            position.append(pos.x)
            position.append(pos.y)
            try:
                position.append(pos.z)
            except AttributeError:
                pass
        elif pos is not None:
            position = pos
        else:
            return None

        self_pos = self.get_attribute("pos")
        position_0 = (self_pos.x, self_pos.y, self_pos.z)
        return distance_calc(position_0, position)

    def unit_availability(self):
        # Harvesting ability
        orders_abilities = [order.ability_id for order in self.orders]

        # Determine availability
        if not self.orders:
            availability_level = 0
        elif set(orders_abilities) & set(HARVESTING_ORDERS):
            availability_level = 1
        else:
            availability_level = 2
        return availability_level

    def available_abilities(self):
        available_abilities = self.extra_info.get('last_available_abilities')
        if available_abilities is None:
            # available_abilities = api_wrapper.request_available_abilities(self.tag)
            available_abilities = None
        return available_abilities

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
        return self.__getattribute__(attribute)

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

