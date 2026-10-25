"""Internal configured smoke composition; the normal main default stays unchanged."""

from fastapi import FastAPI

import backend.main as main


def create_probe() -> FastAPI:
    return main.create_app(_readonly_probe=True)
