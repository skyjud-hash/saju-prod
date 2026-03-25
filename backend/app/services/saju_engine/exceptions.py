class SajuEngineError(Exception):
    pass


class RuleVersionNotFoundError(SajuEngineError):
    pass


class SolarTermNotFoundError(SajuEngineError):
    pass


class TimezoneDataNotFoundError(SajuEngineError):
    pass
