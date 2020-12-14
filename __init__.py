from . import MultiSlice


def getMetaData():
    return {}


def register(app):
    return {"extension": MultiSlice.MultiSlicePlugin()}
