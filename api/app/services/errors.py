# 领域错误。状态码只在 routes 里映射。


class AppError(Exception):
    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


class AuthError(AppError):
    pass


class NotFoundError(AppError):
    pass


class ConflictError(AppError):
    pass


class RejectedError(AppError):
    pass


class NotConfiguredError(AppError):
    pass


class InternalError(AppError):
    pass
