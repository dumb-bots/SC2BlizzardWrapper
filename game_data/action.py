class Action:
    def __init__(self, unit, ability_id, require_target=False):
        self.unit = unit
        self.ability_id = ability_id
        self.require_target = require_target
    def __repr__(self):
        return "%s do %d someone is Required? %s" % (self.unit, self.ability_id, self.require_target)