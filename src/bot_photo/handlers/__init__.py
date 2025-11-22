from . import admin, examples, history, profile, prompt, sessions, start

routers = [
    start.start_router,
    start.agreement_router,
    examples.router,
    sessions.router,
    prompt.router,
    profile.router,
    history.router,
    admin.router,
]

__all__ = ["routers"]
