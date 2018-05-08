class Action:
    def __init__(self, id, ability_id, require_target=False):
        self.id = id
        self.ability_id = ability_id
        self.require_target = require_target
    def __repr__(self):
        return "%s do %d someone is Required? %s" % (self.id, self.ability_id, self.require_target)