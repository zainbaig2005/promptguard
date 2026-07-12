class PromptGuardError(Exception):
    pass


class ValidationError(PromptGuardError):
    pass


class AdapterError(PromptGuardError):
    pass
