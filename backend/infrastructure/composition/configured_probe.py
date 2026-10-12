"""Internal configured smoke composition; the normal main default stays unchanged."""

from fastapi import FastAPI

from ... import main


def create_probe() -> FastAPI:
    return main.create_app(_readonly_probe=True)
